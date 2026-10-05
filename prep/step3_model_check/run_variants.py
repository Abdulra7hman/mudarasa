"""Throwaway (prep, 2 Oct): two variants after run 1.
  rag_v2      : quotes first, then answer sentences, status last (evidence before verdict).
  closed_fair : the plain model as a student would use it without Mudarasa: answer and cite book/vol/page; no refusal rules.
Outputs -> results/raw_v2.json
"""
import json, pathlib
import run_check as R

HERE = pathlib.Path(__file__).resolve().parent
SCHEMA_V2 = {
    "type": "object",
    "properties": {
        "scope": R.SCHEMA["properties"]["scope"],
        "premise_correct": {"type": "boolean"},
        "evidence": {"type": "array", "items": {"type": "object", "properties": {
            "passage": {"type": "string"}, "quote": {"type": "string"}}, "required": ["passage", "quote"]}},
        "sentences": R.SCHEMA["properties"]["sentences"],
        "status": R.SCHEMA["properties"]["status"],
    },
    "required": ["scope", "premise_correct", "evidence", "sentences", "status"],
}
RULES_V2 = R.RULES + """
طريقة العمل:
أ. حدّد scope أولًا.
ب. في evidence انسخ حرفيًّا كل عبارة من النصوص تتعلق بالسؤال، مع رقم مقطعها. اقرأ المقاطع كلها، وكذلك الحواشي.
ج. اكتب sentences: جواب السؤال نفسه فقط، كل جملة مع اقتباسها ورقم مقطعها. لا تذكر ما لا يتعلق بالسؤال.
د. أخيرًا status: supported إن أجابت النصوص؛ differing فقط إن نقلت النصوص قولين مختلفين في المسألة نفسها؛ not_found إن كانت evidence فارغة."""
CLOSED_FAIR = "أنت مساعد في الفقه الحنبلي. أجب عن سؤال الطالب، واذكر لكل جملة الكتاب والجزء والصفحة التي يوجد فيها الكلام ونصًّا مقتبسًا منه.\nاجعل scope = answerable و status = supported إن أجبت."

def main():
    P = R.build_passages(); bm = R.BM25([p["tokens"] for p in P])
    qs = [json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = []
    for q in qs:
        shown = R.retrieve(q["question"], P, bm)
        ctx = "\n\n".join(f"[P{i}] {p['book']}، ج{p['vol']} ص{p['page']} ({'حاشية' if p['kind'] != 'text' else 'متن وشرح'}):\n{p['text']}" for i, p in enumerate(shown, 1))
        ans, st = R.ask(f"{RULES_V2}\n\nالنصوص:\n{ctx}\n\nالسؤال: {q['question']}\n\nاكتب passage برقم المقطع مثل P3.", SCHEMA_V2)
        rows = R.score_rag(q, ans, shown)
        out.append({"system": "rag_v2", "id": q["id"], "question": q["question"], "answer": ans, "checks": rows, **st, "summary": R.summarise(q, ans, rows)})
        print("rag_v2", q["id"], st, out[-1]["summary"], flush=True)
        ans, st = R.ask(f"{CLOSED_FAIR}\n\nالسؤال: {q['question']}", R.SCHEMA_CLOSED)
        rows = R.score_closed(q, ans)
        out.append({"system": "closed_fair", "id": q["id"], "question": q["question"], "answer": ans, "checks": rows, **st, "summary": R.summarise(q, ans, rows)})
        print("closed_fair", q["id"], st, out[-1]["summary"], flush=True)
        (HERE / "results/raw_v2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main()
