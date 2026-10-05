"""Re-score every run against the current questions.jsonl and write results/summary.md."""
import json, pathlib, re, statistics
import run_check as R
HERE = pathlib.Path(__file__).resolve().parent
Q = {q["id"]: q for q in (json.loads(l) for l in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
P = R.build_passages(); bm = R.BM25([p["tokens"] for p in P])
runs = json.loads((HERE / "results/raw.json").read_text(encoding="utf-8")) + json.loads((HERE / "results/raw_v2.json").read_text(encoding="utf-8"))
rows = []
for r in runs:
    q = Q[r["id"]]
    if r["system"].startswith("rag"):
        checks = R.score_rag(q, r["answer"], R.retrieve(q["question"], P, bm))
    else:
        checks = R.score_closed(q, r["answer"])
    s = R.summarise(q, r["answer"], checks)
    s.update(system=r["system"], id=r["id"], wall_s=r["wall_s"], out_tok=r["output_tokens"], cat=q["category"],
             quotes=sum(1 for c in checks if c["quote_in_passage"]), n=len(checks))
    rows.append(s)
systems = ["closed", "closed_fair", "rag", "rag_v2"]
ans_ids = [i for i, q in Q.items() if q["expected_scope"] == "answerable"]
ref_ids = [i for i, q in Q.items() if q["expected_scope"] != "answerable"]
def pick(sys_, ids): return [x for x in rows if x["system"] == sys_ and x["id"] in ids]
lines = ["| Metric | " + " | ".join(systems) + " |", "|---" * (len(systems) + 1) + "|"]
def add(name, f): lines.append(f"| {name} | " + " | ".join(f(s) for s in systems) + " |")
add("Answered with a correct page (±1), of 7 answerable", lambda s: str(sum(1 for x in pick(s, ans_ids) if x["any_page_hit"])))
add("False refusals, of 7 answerable", lambda s: str(sum(x["false_refusal"] for x in pick(s, ans_ids))))
add("Correct decline/referral, of 3 out-of-scope", lambda s: str(sum(1 for x in pick(s, ref_ids) if x["status"] == "not_found" and not x["invented_on_refusal"])))
add("Scope decision correct, of 10", lambda s: str(sum(x["scope_ok"] for x in pick(s, Q))))
add("Evidence status correct, of 10", lambda s: str(sum(x["status_ok"] for x in pick(s, Q))))
add("False premise caught (Q08)", lambda s: str(pick(s, ["Q08"])[0]["premise_caught"]))
add("Quotes found verbatim in the cited passage", lambda s: f"{sum(x['quotes'] for x in pick(s, Q))}/{sum(x['n'] for x in pick(s, Q))}" if s.startswith("rag") else "n/a (no passages)")
add("Median seconds per question", lambda s: str(statistics.median(x["wall_s"] for x in pick(s, Q))))
(HERE / "results/summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
json.dump(rows, open(HERE / "results/scored.json", "w"), ensure_ascii=False, indent=1)
print("\n".join(lines))
