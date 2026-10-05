"""Side-by-side table: Qaf (hand-scored sheet) vs Mudarasa (scored runs on eval/qaf/probe.jsonl + hand-scored screens).

Usage: python -m eval.qaf.compare eval/results/<tag> [--screens eval/qaf/screens_scored.json]
Writes eval/qaf/COMPARISON.md. The sheet stays private (it quotes Qaf's answers); only labels are copied here.
"""
import csv
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
SHEET = ROOT / "prep/research_qaf/qaf_probe_questions.csv"
HERE = pathlib.Path(__file__).resolve().parent


def mudarasa_label(rows):
    """Majority over runs: pass if the behaviour is right (and the page, when there is a gold page)."""
    votes = []
    for r in rows:
        if r["category"] == "out_of_library":
            ok = r["correct_refusal"] == "True"
        elif r["category"] == "personal_fatwa":
            ok = r["referral"] == "True"
        elif r["category"] == "false_premise":
            ok = r["premise_caught"] == "True" and r["refused"] == "False"
        elif r["category"] == "differing":
            ok = r["citation_hit"] == "True"
            votes.append("نجح" if ok and r["differing_shown"] == "True" else "جزئي" if ok else "فشل")
            continue
        else:
            ok = r["citation_hit"] == "True"
        votes.append("نجح" if ok else "فشل")
    return Counter(votes).most_common(1)[0][0] if votes else "—"


def main():
    tag = pathlib.Path(sys.argv[1])
    screens = {}
    if "--screens" in sys.argv:
        screens = json.loads(pathlib.Path(sys.argv[sys.argv.index("--screens") + 1]).read_text(encoding="utf-8"))
    by_id = {}
    for f in sorted(tag.glob("scored_full_run*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            by_id.setdefault(r["id"], []).append(r)
    sheet = list(csv.reader(open(SHEET, encoding="utf-8-sig")))[1:]
    out = ["| # | Capability | Qaf | Qaf page ±1 | Mudarasa |", "|---|---|---|---|---|"]
    tq, tm = Counter(), Counter()
    for r in sheet:
        pid = f"QAF{int(r[0]):02d}"
        q = r[8].strip() or "—"
        m = mudarasa_label(by_id[pid]) if pid in by_id else screens.get(pid, "— (score from screen)")
        tq[q] += 1
        tm[m] += 1
        out.append(f"| {r[0]} | {r[1]} | {q} | {r[7].strip() or '—'} | {m} |")
    out.append("")
    out.append("Totals: Qaf " + ", ".join(f"{k} {v}" for k, v in tq.items()) + " · Mudarasa " + ", ".join(f"{k} {v}" for k, v in tm.items()))
    (HERE / "COMPARISON.md").write_text("# Qaf vs Mudarasa, 20 probes\n\n" + "\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
