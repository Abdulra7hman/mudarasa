"""Error log draft: every item that failed in a run of the full system, with what happened.

Causes and fixing commits are filled in by hand in eval/ERRORS.md (failure -> cause -> fix), as the plan requires.
Usage: python -m eval.errors eval/results/<tag> [--set eval/testset.jsonl]   -> prints Markdown rows
"""
import csv
import json
import pathlib
import sys
from collections import defaultdict


def main():
    tag = pathlib.Path(sys.argv[1])
    set_path = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "eval/testset.jsonl"
    items = {i["id"]: i for i in (json.loads(l) for l in open(set_path, encoding="utf-8") if l.strip())}
    fails = defaultdict(list)
    runs = sorted(tag.glob("scored_full_run*.csv"))
    for f in runs:
        for r in csv.DictReader(open(f, encoding="utf-8")):
            why = []
            if r["error"] == "True":
                why.append("error")
            if r["false_refusal"] == "True":
                why.append("false refusal")
            if r["citation_hit"] == "False":
                why.append("no gold page cited")
            if r["correct_refusal"] == "False":
                why.append("answered instead of refusing")
            if r["premise_caught"] == "False":
                why.append("premise not caught")
            if r["referral"] == "False":
                why.append("no referral")
            if r["differing_shown"] == "False":
                why.append(f"disagreement not shown (status {r['status']})")
            if r["critical_pass"] == "False":
                why.append("CRITICAL")
            if why:
                fails[r["id"]].append(", ".join(why))
    print(f"| Item | Category | Question | Failed in runs | What happened | Cause | Fix |\n|---|---|---|---|---|---|---|")
    for iid in sorted(fails, key=lambda i: (-len(fails[i]), i)):
        it = items[iid]
        what = "; ".join(sorted(set(fails[iid])))
        print(f"| {iid}{' ⚠' if it.get('critical') else ''} | {it['category']} | {it['question'][:60]} | {len(fails[iid])}/{len(runs)} | {what} |  |  |")


if __name__ == "__main__":
    main()
