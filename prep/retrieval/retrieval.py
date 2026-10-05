"""Prep (2 Oct): hybrid retrieval for باب المياه, replacing the plain BM25 of step 3.

Changes, each measured in retrieval_test.py:
  1. light Arabic stemming: strip و ف ب ل ك and ال (الطاهر -> طاهر, والطهور -> طهور)
  2. question-frame words (ما، هل، الفرق، معنى…) removed from the keyword query
  3. pure hadith-referencing footnotes («رواه البخاري…», «انظر…») ranked lower
  4. dense search with BGE-M3 (Ollama), embeddings cached to disk
  5. hybrid: reciprocal-rank fusion of keyword and dense rankings
"""
import hashlib
import json
import math
import pathlib
import re
import subprocess
import sys
from collections import Counter

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "step2_extraction"))
import analyse as A  # noqa: E402  (normalise, load_pages, split_notes, strip_markup)

BOOK_NAMES = {1679: "الروض المربع (ط الرسالة)", 147658: "الروض المربع (ط ركائز)",
              12216: "حاشية الروض المربع لابن قاسم", 10649: "الشرح الممتع لابن عثيمين"}
EMBED_MODEL = "bge-m3"
CACHE = HERE / "cache_embeddings.json"
RRF_K = 60

# ---------- text ----------
PREFIXES = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك")


def stem(tok: str) -> str:
    """Strip one conjunction/preposition prefix and the article; keep at least 2 letters."""
    for p in PREFIXES:
        if tok.startswith(p) and len(tok) - len(p) >= 2:
            tok = tok[len(p):]
            break
    if tok.startswith("ال") and len(tok) > 3:
        tok = tok[2:]
    return tok


def tokens(text: str, query: bool = False):
    toks = [stem(t) for t in A.normalise(text).split()]
    if query:
        toks = [t for t in toks if t not in QUESTION_WORDS]
    return [t for t in toks if len(t) > 1]


QUESTION_WORDS = {stem(t) for t in A.normalise(
    "ما ماذا هل هو هي كم كيف لماذا متى اين من في على عن الى او ثم اذا ان هذا هذه التي الذي عند "
    "الفرق بين معنى حكم يقول قال قول ذكر").split()}
TAKHRIJ = re.compile(r"^\s*(\(\^?[٠-٩0-9]+\)\s*)?(رواه|أخرجه|اخرجه|انظر|ينظر|سبق تخريجه|تقدم)")


# ---------- passages ----------
def build_passages():
    out = []
    for bid in (1679, 147658, 12216, 10649):
        for p in A.load_pages(bid):
            meta = {"book_id": bid, "book": BOOK_NAMES[bid], "vol": p["meta"]["vol"], "page": p["meta"]["page"], "pg": p["pg"]}
            if bid != 12216:  # Ibn Qasim's body reprints the Rawd; use his notes only
                for line in A.strip_markup(p["body"]).split("\n"):
                    if len(A.normalise(line)) > 30:
                        out.append({**meta, "kind": "text", "text": line.strip()})
            for n, note in A.split_notes(p["notes"]).items():
                if len(A.normalise(note)) > 30:
                    out.append({**meta, "kind": f"حاشية {n}", "text": note.strip()})
    out += toc_passages()
    for p in out:
        p["norm"] = A.normalise(p["text"])
        p["tokens"] = tokens(p["text"])
        # a footnote that only references sources (no explanation) is down-weighted
        p["weight"] = 0.3 if p["kind"] != "text" and TAKHRIJ.match(p["text"]) and len(p["tokens"]) < 60 else 1.0
    return out


def toc_passages(bid=1679, upto_page=80):
    """The anchor's own table of contents (headings with printed pages), for questions about the book's structure."""
    meta = json.loads((HERE.parent / f"step1_sources/raw/book_{bid}.json").read_text(encoding="utf-8"), strict=False)
    pmap = meta["indexes"]["page_map"]
    items = []
    for h in meta["indexes"]["headings"]:
        if h["level"] <= 2 and h["page"] <= upto_page:
            vol, page = pmap[h["page"] - 1].split(",")
            items.append(f"{h['title']} (ج{vol} ص{page})")
    text = "فهرس الكتاب، أوله: " + "، ثم ".join(items)
    first = pmap[0].split(",")
    return [{"book_id": bid, "book": BOOK_NAMES[bid], "vol": first[0], "page": int(pmap[5].split(",")[1]), "pg": 6,
             "kind": "فهرس الكتاب", "text": text}]


# ---------- keyword ----------
class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avg = sum(len(d) for d in docs) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.tf = [Counter(d) for d in docs]

    def scores(self, q):
        out = []
        for d, tf in zip(self.docs, self.tf):
            s = 0.0
            for t in q:
                if t in tf:
                    s += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            out.append(s)
        return np.array(out)


# ---------- dense ----------
def embed(texts):
    body = {"model": EMBED_MODEL, "input": texts}
    r = subprocess.run(["curl", "-s", "-m", "600", "http://localhost:11434/api/embed", "-d", json.dumps(body)], capture_output=True)
    v = np.array(json.loads(r.stdout)["embeddings"], dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def passage_vectors(passages):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    keys = [hashlib.sha1(p["text"].encode()).hexdigest() for p in passages]
    missing = [i for i, k in enumerate(keys) if k not in cache]
    for start in range(0, len(missing), 32):
        batch = missing[start:start + 32]
        for i, v in zip(batch, embed([passages[i]["text"] for i in batch])):
            cache[keys[i]] = v.round(5).tolist()
    if missing:
        CACHE.write_text(json.dumps(cache))
    return np.array([cache[k] for k in keys], dtype=np.float32)


# ---------- retriever ----------
class Retriever:
    def __init__(self, passages=None, dense=True):
        self.passages = passages or build_passages()
        self.bm25 = BM25([p["tokens"] for p in self.passages])
        self.weights = np.array([p["weight"] for p in self.passages])
        self.vecs = passage_vectors(self.passages) if dense else None

    def keyword_rank(self, q):
        s = self.bm25.scores(tokens(q, query=True)) * self.weights
        return [i for i in np.argsort(-s) if s[i] > 0]

    def dense_rank(self, q):
        s = (self.vecs @ embed([q])[0]) * np.where(self.weights < 1, 0.9, 1.0)
        return list(np.argsort(-s))

    def search(self, q, k=8, mode="hybrid"):
        if mode == "keyword":
            order = self.keyword_rank(q)
        elif mode == "dense":
            order = self.dense_rank(q)
        else:
            fused = Counter()
            for ranking in (self.keyword_rank(q), self.dense_rank(q)):
                for r, i in enumerate(ranking[:100]):
                    fused[i] += 1 / (RRF_K + r + 1)
            order = [i for i, _ in fused.most_common()]
        return [self.passages[i] for i in order[:k]]
