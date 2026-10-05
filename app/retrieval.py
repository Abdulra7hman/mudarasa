"""Hybrid retrieval over the ingested library: stemmed BM25 + dense embeddings, fused by reciprocal rank.

Adapted from prep/retrieval/retrieval.py (stem, tokens, QUESTION_WORDS, TAKHRIJ, BM25, RRF, table of contents).
Changes: passages come from data/build/study.json and carry the anchor paragraph they belong to (the open paragraph's
own commentary is put first); embeddings come from Azure (text-embedding-3-large) or local BGE-M3, cached on disk;
if the embedding service fails, search falls back to keywords only.
"""
import hashlib
import json
import math
import re
from collections import Counter

import numpy as np
import requests

from . import books as B
from . import config as C
from .textnorm import normalise

RRF_K = 60
PREFIXES = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك")
KIND = {1679: "متن وشرح", 12216: "حاشية ابن قاسم", 10649: "الشرح الممتع", 147658: "حاشية ط ركائز (تخريج وفروق نسخ)"}


def stem(tok: str) -> str:
    for p in PREFIXES:
        if tok.startswith(p) and len(tok) - len(p) >= 2:
            tok = tok[len(p):]
            break
    if tok.startswith("ال") and len(tok) > 3:
        tok = tok[2:]
    return tok


QUESTION_WORDS = {stem(t) for t in normalise(
    "ما ماذا هل هو هي كم كيف لماذا متى اين من في على عن الى او ثم اذا ان هذا هذه التي الذي عند "
    "الفرق بين معنى حكم يقول قال قول ذكر").split()}
TAKHRIJ = re.compile(r"^\s*(\(\^?[٠-٩0-9]+\)\s*)?(رواه|أخرجه|اخرجه|انظر|ينظر|سبق تخريجه|تقدم)")


def tokens(text: str, query: bool = False):
    toks = [stem(t) for t in normalise(text).split()]
    if query:
        toks = [t for t in toks if t not in QUESTION_WORDS]
    return [t for t in toks if len(t) > 1]


def _p(bid, pg, text, para, chapter, kind=None, extra=None):
    pr = B.page(bid, pg)
    d = {"book_id": bid, "book": B.BOOK_NAMES[bid], "vol": pr["vol"], "page": pr["page"], "pg": pg, "kind": kind or KIND[bid],
         "text": text.strip(), "para": para, "chapter": chapter, "link": B.turath_link(bid, pg)}
    d["id"] = f"{bid}:{pg}:" + hashlib.sha1(d["text"].encode()).hexdigest()[:8]
    return {**d, **(extra or {})}


def build_passages(study):
    out = []
    units_by_para = {}
    for u in study["units"].values():
        units_by_para.setdefault(u["para"], []).append(u)
    for pid, p in study["paras"].items():
        ch = p["chapter"]
        # the Rawd, unit by unit (a matn phrase and its explanation): long paragraphs hide specific issues from search
        buf, pg0 = "", None
        for u in units_by_para.get(pid, []):
            buf, pg0 = (buf + " " + u["text"].strip()).strip(), pg0 or u["pg"]
            if len(normalise(buf)) > 120:
                out.append(_p(1679, pg0, buf, pid, ch))
                buf, pg0 = "", None
        if buf:
            out.append(_p(1679, pg0, buf, pid, ch))
        if pid not in units_by_para:
            out.append(_p(1679, p["pg"], p["text"], pid, ch))
        for n in p["iq"]:
            if len(normalise(n["text"])) > 20:
                out.append(_p(12216, n["pg"], n["text"], pid, ch, extra={"note": n["n"]}))
        for s in p["mumti"]:
            buf, pg0 = "", None
            for ln in s["lines"]:  # short lines are merged into the next one
                buf, pg0 = (buf + " " + ln["text"]).strip(), pg0 or ln["pg"]
                if len(normalise(buf)) > 60:
                    out.append(_p(10649, pg0, buf, pid, ch, extra={"heading": s["heading"]}))
                    buf, pg0 = "", None
            if buf:
                out.append(_p(10649, pg0, buf, pid, ch, extra={"heading": s["heading"]}))
        for n in p["rakaiz_notes"]:
            if len(normalise(n["text"])) > 20:
                out.append(_p(147658, n["pg"], n["text"], pid, ch, extra={"note": n["n"]}))
    out.append(toc_passage())
    for p in out:
        p["norm"] = normalise(p["text"])
        p["tokens"] = tokens(p["text"])
        p["weight"] = 0.3 if p["book_id"] != 1679 and TAKHRIJ.match(p["text"]) and len(p["tokens"]) < 60 else 1.0
    return out


def toc_passage(bid=1679, upto_pg=80):
    """The anchor's own table of contents, for questions about the book's structure (from prep)."""
    m = B.meta(bid)["indexes"]
    pmap = m["page_map"]
    items = []
    for h in m["headings"]:
        if h["level"] <= 2 and h["page"] <= upto_pg:
            vol, page = pmap[h["page"] - 1].split(",")
            items.append(f"{h['title']} (ج{vol} ص{page})")
    p = _p(bid, 6, "فهرس الكتاب، أوله: " + "، ثم ".join(items), None, None, kind="فهرس الكتاب")
    return p


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avg = sum(len(d) for d in docs) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.tf = [Counter(d) for d in docs]

    def scores(self, q):
        out = np.zeros(len(self.docs))
        for i, (d, tf) in enumerate(zip(self.docs, self.tf)):
            s = 0.0
            for t in q:
                if t in tf:
                    s += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            out[i] = s
        return out


# ---------- embeddings ----------
def embed(texts, provider=None):
    provider = provider or C.EMBED_PROVIDER
    if provider == "azure":
        from .llm import client
        r = client("azure").embeddings.create(model=C.MODEL_EMBED, input=texts, dimensions=C.EMBED_DIM)
        v = np.array([d.embedding for d in r.data], dtype=np.float32)
    elif provider == "ollama":
        r = requests.post(f"{C.OLLAMA_URL}/api/embed", json={"model": C.OLLAMA_EMBED_MODEL, "input": texts}, timeout=600)
        v = np.array(r.json()["embeddings"], dtype=np.float32)
    else:
        raise RuntimeError("no embedding provider")
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def cache_path(provider):
    name = C.MODEL_EMBED if provider == "azure" else C.OLLAMA_EMBED_MODEL
    return B.DATA / "build" / f"emb_{provider}_{name}.json"


def passage_vectors(passages, provider):
    path = cache_path(provider)
    cache = json.loads(path.read_text()) if path.exists() else {}
    keys = [hashlib.sha1(p["text"].encode()).hexdigest() for p in passages]
    missing = [i for i, k in enumerate(keys) if k not in cache]
    for s in range(0, len(missing), 32):
        batch = missing[s:s + 32]
        for i, v in zip(batch, embed([passages[i]["text"][:6000] for i in batch], provider)):
            cache[keys[i]] = v.round(5).tolist()
    if missing:
        path.write_text(json.dumps(cache))
    return np.array([cache[k] for k in keys], dtype=np.float32)


class Retriever:
    def __init__(self, passages=None, provider=None):
        if passages is None:
            passages = build_passages(json.loads((B.DATA / "build/study.json").read_text(encoding="utf-8")))
        self.passages = passages
        self.provider = provider or C.EMBED_PROVIDER
        self.bm25 = BM25([p["tokens"] for p in passages])
        self.weights = np.array([p["weight"] for p in passages])
        self.vecs = None
        if self.provider != "none":
            try:
                self.vecs = passage_vectors(passages, self.provider)
            except Exception as e:  # keyword-only mode
                print("dense retrieval disabled:", e)

    def keyword_rank(self, q):
        s = self.bm25.scores(tokens(q, query=True)) * self.weights
        return [int(i) for i in np.argsort(-s) if s[i] > 0]

    def dense_rank(self, q):
        if self.vecs is None:
            return []
        try:
            qv = embed([q], self.provider)[0]
        except Exception:
            return []
        s = (self.vecs @ qv) * np.where(self.weights < 1, 0.9, 1.0)
        return [int(i) for i in np.argsort(-s)]

    def search(self, q, k=8, mode="hybrid", para=None, chapter=None):
        if mode == "keyword":
            order = self.keyword_rank(q)
        elif mode == "dense":
            order = self.dense_rank(q)
        else:
            kw, dn = self.keyword_rank(q), self.dense_rank(q)
            fused = Counter()
            for ranking in (kw, dn):
                for r, i in enumerate(ranking[:100]):
                    fused[i] += 1 / (RRF_K + r + 1)
            # a strong match on a rare word (e.g. «زمزم») must not be diluted by passages that are only fair in both lists:
            # the top 3 keyword and top 2 dense results keep a guaranteed place, the fusion fills the rest
            sure = list(dict.fromkeys(kw[:3] + dn[:2]))
            order = [i for i, _ in fused.most_common()]
        if chapter:
            order = [i for i in order if self.passages[i]["chapter"] in (chapter, None)]
        if para:  # the open paragraph's own text and commentary first
            own = [i for i in order if self.passages[i]["para"] == para][:4]
            order = own + [i for i in order if i not in own]
        top = order[:k]
        if mode == "hybrid":  # keep the fused order, but make sure the strongest single-list hits are inside the top k
            for i in sure:
                if i not in top:
                    drop = next((j for j in reversed(top) if j not in sure), None)
                    if drop is not None:
                        top[top.index(drop)] = i
        return [self.passages[i] for i in top]
