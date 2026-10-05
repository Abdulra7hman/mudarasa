"""Throwaway (prep, 2 Oct): informal 10-question check of Gemma 4 E4B on باب المياه.

Two setups on the same questions (questions.jsonl, drafted by the model, NOT the specialist's test set):
  rag    : BM25 over the four books' باب المياه passages -> top 8 -> Gemma answers in JSON, one quote per sentence
  closed : no passages; Gemma answers from memory and must still give book/volume/page citations

Automatic checks: scope decision, evidence status, citation page hit (±1), quote exists verbatim (after normalising)
in the cited passage, latency, tokens. Raw outputs -> results/*.json, table -> results/summary.md.
"""
import json
import math
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "step2_extraction"))
import analyse as A  # noqa: E402  (normalise, load_pages, split_notes, strip_markup)

MODEL = "gemma4:e4b-it-qat"
TOP_K = 8
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
BOOK_NAMES = {1679: "الروض المربع (ط الرسالة)", 147658: "الروض المربع (ط ركائز)", 12216: "حاشية الروض المربع لابن قاسم", 10649: "الشرح الممتع لابن عثيمين"}


# ---------- passages ----------
def build_passages():
    """Body paragraphs and footnotes of باب المياه as passages. Ibn Qasim's body is a reprint of the Rawd, so only his notes are used."""
    out = []
    for bid in (1679, 147658, 12216, 10649):
        for p in A.load_pages(bid):
            meta = {"book_id": bid, "book": BOOK_NAMES[bid], "vol": p["meta"]["vol"], "page": p["meta"]["page"]}
            if bid != 12216:
                for line in A.strip_markup(p["body"]).split("\n"):
                    if len(A.normalise(line)) > 30:
                        out.append({**meta, "kind": "text", "text": line.strip()})
            for n, note in A.split_notes(p["notes"]).items():
                if len(A.normalise(note)) > 30:
                    out.append({**meta, "kind": f"note {n}", "text": note.strip()})
    for i, p in enumerate(out):
        p["norm"] = A.normalise(p["text"])
        p["tokens"] = p["norm"].split()
    return out


STOP = set(A.normalise("ما هل في من على عن الى او و ثم اذا ان هو هي هذا هذه التي الذي كم لماذا كيف قال حكم عند").split())


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avg = sum(len(d) for d in docs) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def scores(self, q):
        res = []
        for d in self.docs:
            tf, s = Counter(d), 0.0
            for t in q:
                if t in tf:
                    s += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            res.append(s)
        return res


def retrieve(question, passages, bm25):
    q = [t for t in A.normalise(question).split() if t not in STOP]
    sc = bm25.scores(q)
    ranked = sorted(range(len(passages)), key=lambda i: -sc[i])
    return [passages[i] for i in ranked[:TOP_K] if sc[i] > 0]


# ---------- model ----------
SCHEMA = {
    "type": "object",
    "properties": {
        "scope": {"type": "string", "enum": ["answerable", "other_madhhab", "contemporary", "personal_fatwa", "not_in_library"]},
        "premise_correct": {"type": "boolean"},
        "status": {"type": "string", "enum": ["supported", "partial", "differing", "not_found"]},
        "sentences": {"type": "array", "items": {"type": "object", "properties": {
            "text": {"type": "string"}, "passage": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["text", "passage", "quote"]}},
    },
    "required": ["scope", "premise_correct", "status", "sentences"],
}
SCHEMA_CLOSED = {
    "type": "object",
    "properties": {
        "scope": SCHEMA["properties"]["scope"], "premise_correct": {"type": "boolean"}, "status": SCHEMA["properties"]["status"],
        "sentences": {"type": "array", "items": {"type": "object", "properties": {
            "text": {"type": "string"}, "book": {"type": "string"}, "vol": {"type": "string"}, "page": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["text", "book", "vol", "page", "quote"]}},
    },
    "required": ["scope", "premise_correct", "status", "sentences"],
}

RULES = """أنت شريك دراسة لطالب علم يدرس «الروض المربع» في المذهب الحنبلي.
القواعد:
1. صنّف السؤال في scope: answerable إن كان عن مسائل الكتاب ومذهب الحنابلة؛ other_madhhab إن سأل عن مذهب آخر؛ contemporary إن كان نازلة معاصرة؛ personal_fatwa إن سأل عن حالته هو؛ not_in_library إن لم يكن في النصوص ما يجيب.
2. إن كان في السؤال نسبة قول إلى المؤلف لم يقله فاجعل premise_correct = false وصحّح ذلك من النص.
3. كل جملة فيها حكم أو دليل أو نسبة قول أو حكم على حديث يجب أن تُوثَّق باقتباس حرفي منسوخ كما هو من النص (quote).
4. لا تذكر شيئًا من معرفتك الخاصة. إن لم تجد نصًّا فاجعل status = not_found ولا تكتب جملًا.
5. إن اختلفت الأقوال فاذكر كل قول منسوبًا لقائله، ولا ترجّح، واجعل status = differing.
6. لا تُفتِ في الحالات الشخصية.
أجب بالعربية."""


def ask(prompt, schema):
    body = {"model": MODEL, "prompt": prompt, "stream": False, "think": False, "format": schema,
            "options": {"temperature": 0, "num_ctx": 8192, "seed": 1}}
    t = time.time()
    r = subprocess.run(["curl", "-s", "-m", "900", "http://localhost:11434/api/generate", "-d", json.dumps(body)], capture_output=True)
    d = json.loads(r.stdout)
    try:
        ans = json.loads(d.get("response", ""))
    except json.JSONDecodeError:
        ans = {"_unparsed": d.get("response", "")}
    return ans, {"wall_s": round(time.time() - t, 1), "prompt_tokens": d.get("prompt_eval_count"), "output_tokens": d.get("eval_count")}


# ---------- scoring ----------
def page_hit(book_id, page, gold):
    return any(book_id == g[0] and abs(int(page) - g[1]) <= 1 for g in gold)


def score_rag(q, ans, shown):
    sents = ans.get("sentences", []) or []
    rows = []
    for s in sents:
        m = re.search(r"\d+", str(s.get("passage", "")))
        p = shown[int(m.group()) - 1] if m and 0 < int(m.group()) <= len(shown) else None
        qn = A.normalise(s.get("quote", ""))
        rows.append({"passage_ok": p is not None, "quote_in_passage": bool(p and qn and qn in p["norm"]),
                     "page_hit": bool(p and page_hit(p["book_id"], p["page"], q["gold"])),
                     "cite": f"{p['book_id']} {p['vol']}/{p['page']}" if p else None})
    return rows


def score_closed(q, ans):
    rows = []
    ids = {"الروض": 1679, "حاشية": 12216, "ابن قاسم": 12216, "الممتع": 10649}
    for s in ans.get("sentences", []) or []:
        bid = next((v for k, v in ids.items() if k in str(s.get("book", ""))), None)
        pg = re.search(r"\d+", str(s.get("page", "")).translate(A.AR_DIGITS))
        rows.append({"quote_in_passage": None, "page_hit": bool(bid and pg and page_hit(bid, int(pg.group()), q["gold"])),
                     "cite": f"{s.get('book')} {s.get('vol')}/{s.get('page')}"})
    return rows


def summarise(q, ans, rows):
    expected_refuse = q["expected_scope"] != "answerable"
    return {
        "scope": ans.get("scope"), "scope_ok": ans.get("scope") == q["expected_scope"],
        "status": ans.get("status"), "status_ok": ans.get("status") == q["expected_status"],
        "premise_caught": (ans.get("premise_correct") is False) if q.get("premise_false") else None,
        "sentences": len(rows), "quotes_verified": sum(r["quote_in_passage"] for r in rows if r["quote_in_passage"] is not None),
        "any_page_hit": any(r["page_hit"] for r in rows) if q["gold"] else None,
        "false_refusal": (not expected_refuse) and (ans.get("status") == "not_found" or not rows),
        "invented_on_refusal": expected_refuse and q["expected_scope"] != "personal_fatwa" and len(rows) > 0,
    }


def main():
    passages = build_passages()
    bm25 = BM25([p["tokens"] for p in passages])
    qs = [json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"{len(passages)} passages", flush=True)
    results = []
    for q in qs:
        shown = retrieve(q["question"], passages, bm25)
        ctx = "\n\n".join(f"[P{i}] {p['book']}، ج{p['vol']} ص{p['page']} ({'حاشية' if p['kind'] != 'text' else 'متن وشرح'}):\n{p['text']}" for i, p in enumerate(shown, 1))
        ans, stats = ask(f"{RULES}\n\nالنصوص:\n{ctx}\n\nالسؤال: {q['question']}\n\nاكتب passage برقم المقطع مثل P3.", SCHEMA)
        rows = score_rag(q, ans, shown)
        results.append({"system": "rag", "id": q["id"], "question": q["question"], "answer": ans, "checks": rows, **stats,
                        "retrieved": [f"{p['book_id']} {p['vol']}/{p['page']} {p['kind']}" for p in shown],
                        "retrieval_hit": any(page_hit(p["book_id"], p["page"], q["gold"]) for p in shown) if q["gold"] else None,
                        "summary": summarise(q, ans, rows)})
        print("rag", q["id"], stats, results[-1]["summary"], flush=True)

        ans, stats = ask(f"{RULES}\n\nلا توجد نصوص مرفقة؛ أجب من معرفتك، واذكر لكل جملة الكتاب والجزء والصفحة ونصًّا مقتبسًا.\n\nالسؤال: {q['question']}", SCHEMA_CLOSED)
        rows = score_closed(q, ans)
        results.append({"system": "closed", "id": q["id"], "question": q["question"], "answer": ans, "checks": rows, **stats,
                        "summary": summarise(q, ans, rows)})
        print("closed", q["id"], stats, results[-1]["summary"], flush=True)
        (OUT / "raw.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
