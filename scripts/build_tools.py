"""Generate the study tools (summary, quiz, flashcards) for each section of the deep chapters, from library texts only.

Every item must carry a passage number and a verbatim quote. Items whose quote is not found in the cited passage are
dropped; the rest go to the support judge (same as answers) and are dropped if the quote does not support them.
Counts of generated / quote-verified / judge-supported items are kept per section for eval/additions_check.py.

Usage: python -m scripts.build_tools [--chapters water,vessels,istinja] [--provider azure] [--limit N]
Output: data/tools/<chapter>.json (gitignored: quotes the books)
"""
import argparse
import json
import re

from app import books as B
from app import llm
from app import prompts as P
from app.textnorm import normalise

OUT = B.DATA / "tools"
MAX_ANCHOR = 1400   # characters of al-Rawd per section
MAX_CTX = 9000      # characters of context per section

CITED = {"type": "object", "properties": {"text": {"type": "string"}, "passage": {"type": "string"}, "quote": {"type": "string"}}}
SCHEMA = {"type": "object", "properties": {
    "title": {"type": "string"},
    "summary": {"type": "array", "items": CITED},
    "quiz": {"type": "array", "items": {"type": "object", "properties": {
        "question": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}, "answer": {"type": "integer"},
        "explanation": {"type": "string"}, "passage": {"type": "string"}, "quote": {"type": "string"}}}},
    "cards": {"type": "array", "items": {"type": "object", "properties": {
        "front": {"type": "string"}, "back": {"type": "string"}, "passage": {"type": "string"}, "quote": {"type": "string"}}}}}}

RULES = """أنت معلم يعدّ أدوات مذاكرة لطالب يدرس «الروض المربع» في الفقه الحنبلي، من النصوص المعطاة فقط.
اكتب:
- title: عنوان قصير لمسائل هذا المقطع.
- summary: من ٣ إلى ٦ جمل تلخص المسائل والأحكام وأدلتها كما في النصوص، كل جملة بنصها text ورقم مقطعها passage (مثل P2) واقتباس حرفي quote منسوخ من ذلك المقطع.
- quiz: ثلاثة أسئلة اختيار من متعدد، لكل سؤال أربعة خيارات options، ورقم الخيار الصحيح answer (من 0 إلى 3)، وشرح قصير explanation، ومقطع واقتباس حرفي يدل على الجواب الصحيح.
- cards: أربع بطاقات مراجعة: front سؤال قصير، back جواب قصير، مع مقطع واقتباس حرفي يدل على الجواب.
القواعد: لا تضف شيئًا من معرفتك الخاصة. انقل الحكم بدرجته (يكره غير يحرم). إن اختلفت الأقوال فانسب كل قول لقائله دون ترجيح.
الاقتباس يُنسخ حرفًا بحرف من المقطع، ولا يُختصر ولا يُعاد صياغته. أجب بالعربية."""


def sections(study, cid):
    ch = next(c for c in study["chapters"] if c["id"] == cid)
    out, cur, size = [], [], 0
    for pid in ch["paras"]:
        p = study["paras"][pid]
        if cur and size + len(p["text"]) > MAX_ANCHOR:
            out.append(cur)
            cur, size = [], 0
        cur.append(p)
        size += len(p["text"])
    if cur:
        out.append(cur)
    return out


def context(paras):
    """Numbered passages: the Rawd paragraphs, then Ibn Qasim notes, then al-Mumti' lines, within MAX_CTX."""
    items = []
    for p in paras:
        items.append((1679, p, p["text"], "متن وشرح"))
    for p in paras:
        for n in p["iq"]:
            if len(normalise(n["text"])) > 30:
                items.append((12216, n, n["text"], "حاشية ابن قاسم"))
    for p in paras:
        for s in p["mumti"]:
            for ln in s["lines"]:
                if len(normalise(ln["text"])) > 40:
                    items.append((10649, ln, ln["text"], "الشرح الممتع"))
    out, total = [], 0
    for bid, ref, text, kind in items:
        if total + len(text) > MAX_CTX and bid != 1679:
            continue
        out.append({"book_id": bid, "book": B.BOOK_NAMES[bid], "vol": ref["vol"], "page": ref["page"], "link": ref["link"],
                    "kind": kind, "text": text, "norm": normalise(text)})
        total += len(text)
    return out


def resolve(item, ctx):
    digits = re.findall(r"\d+", str(item.get("passage", "")))
    n = int(digits[0]) if digits else None
    p = ctx[n - 1] if n and 0 < n <= len(ctx) else None
    q = normalise(item.get("quote", ""))
    if not (p and q and q in p["norm"]):
        return None
    return {"book": p["book"], "book_id": p["book_id"], "vol": p["vol"], "page": p["page"], "link": p["link"], "quote": item["quote"]}


def judge(claims, provider):
    """claims: list of (sentence, quote) -> list of bools (True = supported)."""
    if not claims:
        return []
    items = "\n\n".join(f"[{i}] الجملة: {s}\nالاقتباس: «{q}»" for i, (s, q) in enumerate(claims))
    j, _ = llm.ask(P.JUDGE_RULES, items, P.SCHEMA_JUDGE, role="judge", provider=provider, max_out=4000)
    v = {x.get("i"): x.get("supported") for x in (j.get("verdicts") or [])} if isinstance(j, dict) else {}
    return [v.get(i, True) is not False for i in range(len(claims))]


def build_section(paras, k, cid, provider):
    ctx = context(paras)
    text = "\n\n".join(f"[P{i}] {p['book']}، ج{p['vol']} ص{p['page']} ({p['kind']}):\n{p['text']}" for i, p in enumerate(ctx, 1))
    ans, st = llm.ask(RULES, f"النصوص:\n{text}", SCHEMA, role="answer", provider=provider, max_out=8000)
    stats = {"generated": 0, "quote_ok": 0, "judge_ok": 0, "cost_usd": st.get("cost_usd"), "latency_s": st.get("latency_s")}
    summ, quiz, cards = [], [], []
    for s in ans.get("summary") or []:
        stats["generated"] += 1
        c = resolve(s, ctx)
        if c:
            summ.append({"text": s["text"], "cite": c})
    for q in ans.get("quiz") or []:
        stats["generated"] += 1
        c = resolve(q, ctx)
        opts = q.get("options") or []
        if c and len(opts) >= 2 and 0 <= int(q.get("answer", -1)) < len(opts):
            quiz.append({"question": q["question"], "options": opts, "answer": int(q["answer"]), "explanation": q.get("explanation", ""), "cite": c})
    for cd in ans.get("cards") or []:
        stats["generated"] += 1
        c = resolve(cd, ctx)
        if c:
            cards.append({"front": cd["front"], "back": cd["back"], "cite": c})
    stats["quote_ok"] = len(summ) + len(quiz) + len(cards)
    claims = [(s["text"], s["cite"]["quote"]) for s in summ] + \
             [(f"{q['question']} الجواب: {q['options'][q['answer']]}", q["cite"]["quote"]) for q in quiz] + \
             [(f"{c['front']} الجواب: {c['back']}", c["cite"]["quote"]) for c in cards]
    ok = judge(claims, provider)
    a, b = len(summ), len(summ) + len(quiz)
    summ = [x for x, keep in zip(summ, ok[:a]) if keep]
    quiz = [x for x, keep in zip(quiz, ok[a:b]) if keep]
    cards = [x for x, keep in zip(cards, ok[b:]) if keep]
    stats["judge_ok"] = len(summ) + len(quiz) + len(cards)
    return {"id": f"{cid}-{k + 1}", "title": ans.get("title") or (paras[0].get("heading") or ""), "page": paras[0]["page"],
            "paras": [p["id"] for p in paras], "summary": summ, "quiz": quiz, "cards": cards, "stats": stats}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="water,vessels,istinja")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    study = json.loads((B.DATA / "build/study.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for cid in a.chapters.split(","):
        secs = sections(study, cid)[: a.limit or None]
        out = []
        for k, paras in enumerate(secs):
            try:
                s = build_section(paras, k, cid, a.provider)
                out.append(s)
                print(cid, k + 1, "/", len(secs), s["title"][:40], s["stats"], flush=True)
            except Exception as e:
                print(cid, k + 1, "FAILED", type(e).__name__, str(e)[:200], flush=True)
            (OUT / f"{cid}.json").write_text(json.dumps({"chapter": cid, "sections": out}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
