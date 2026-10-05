"""Assemble eval/REPORT.md from the result folders, the retrieval check, the additions checks and the Qaf comparison.

Usage: python -m eval.make_report
Every number in the report comes from a file in eval/results/ (or eval/RETRIEVAL.md, eval/ADDITIONS.md, eval/qaf/COMPARISON.md).
"""
import json
import pathlib

from eval import report

HERE = pathlib.Path(__file__).resolve().parent
R = HERE / "results"

SECTIONS = [
    ("main_v3_live", "Main result: Mudarasa as deployed (Azure gpt-5-mini) vs the same model without retrieval",
     "`full` = the whole pipeline with the live settings (single-pass answers, medium answer effort, low judge effort, 12 passages). "
     "`no_verify` = the same answers before the quote check and the judge (no extra calls). "
     "`no_retrieval` = the same model with no library, citing from memory. 100 items × 3 runs; mean (min–max over runs)."),
    ("main_v2_gpt5mini", "Earlier settings: evidence list first, medium judge effort, 8 passages (3 runs)",
     "The same pipeline before the speed comparison below."),
    ("v1_before_fixes", "Before the fixes of 5 Oct night (1 run)",
     "The first full run, kept to show what the fixes in eval/ERRORS.md changed."),
]


def main():
    out = ["# Evaluation report", "",
           "Reproduce: `make eval RUNS=3` (needs `.env`), then `python -m eval.make_report`. "
           "Each results folder has `meta.json` with the commit, models, reasoning effort and prices.", "",
           "**Test set:** `eval/testset.jsonl`, 100 items, model-drafted from the texts. Gold pages were verified by text search; "
           "no specialist has reviewed it yet (`eval/TESTSET_NOTES.md`).", "",
           "| Category | Items |", "|---|---|",
           "| Answerable | 50 |", "| Differing positions | 15 |", "| Out of library | 15 |",
           "| False premise | 10 |", "| Personal fatwa | 10 |", "",
           "10 items are critical. Scoring: page ±1, refusal and referral detection, evidence status, verified-sentence share, "
           "latency, tokens, cost (`eval/score.py`).", ""]
    for tag, title, note in SECTIONS:
        d = R / tag
        if not list(d.glob("scored_*.csv")):
            continue
        meta, agg = report.summarise(d)
        out += [f"## {title}", "", note, "", report.table(meta, agg), ""]
    speed = [("speed_A_current", "Evidence list first, answer medium, judge medium"), ("speed_B_fast", "Single pass, answer low, judge low"),
             ("speed_C_medium_nolist", "Single pass, answer medium, judge low (chosen)")]
    if all(list((R / t).glob("scored_*.csv")) for t, _ in speed):
        rows = ["## Speed settings compared (30 mixed items, 1 run)", "",
                "| Setting | Median s | p95 s | Gold page cited | False refusal | Status match | Premise caught | Critical |", "|---|---|---|---|---|---|---|---|"]
        for t, label in speed:
            _, agg = report.summarise(R / t)
            a = agg["full"]
            f = lambda k: f"{100 * a[k]['mean']:.0f}%" if a[k]["mean"] is not None else "–"
            rows.append(f"| {label} | {a['latency_median_s']['mean']:.1f} | {a['latency_p95_s']['mean']:.1f} | {f('citation_hit')} | "
                        f"{f('false_refusal')} | {f('status_ok')} | {f('premise_caught')} | {f('critical_pass')} |")
        out += rows + ["", "The fast setting loses a critical false-premise item, so the middle one is used.", ""]
    for name, title in (("RETRIEVAL.md", "Retrieval"), ("ADDITIONS.md", "Additions (small checks)"),
                        ("qaf/COMPARISON.md", "Head-to-head with Qaf")):
        f = HERE / name
        if f.exists():
            body = f.read_text(encoding="utf-8").split("\n", 1)
            out += [f"## {title}", "", body[1] if body[0].startswith("#") else f.read_text(encoding="utf-8"), ""]
    errs = HERE / "ERRORS.md"
    if errs.exists():
        out += ["## Errors and fixes", "", "See [ERRORS.md](ERRORS.md): failure → cause → fixing commit.", ""]
    out += ["## Limits", "",
            "- The test set is model-drafted; a specialist has not reviewed it. One chapter group (three chapters of كتاب الطهارة).",
            "- Correctness is scored on cited pages, refusals, status and premise, not by a human reading every answer.",
            "- gpt-5-mini both answers and judges (other models had no quota). Judges are models; they reduce unsupported sentences but do not guarantee their absence.",
            "- GPT-5 models take no temperature, so runs vary. Hence 3 runs, with the range.",
            "- Small samples for the additions; five users at most for the user test.", ""]
    (HERE / "REPORT.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out[:60]))


if __name__ == "__main__":
    main()
