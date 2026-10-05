"""Aggregate scored runs into one table: mean and min–max over runs, per system.

Usage: python -m eval.report eval/results/<tag> [more tags...]   -> prints Markdown; writes <tag>/summary.json
"""
import csv
import json
import pathlib
import re
import statistics as st
import sys
from collections import defaultdict

METRICS = [
    ("citation_hit", "Citation accuracy (gold page ±1), answerable items"),
    ("cited_on_gold_share", "Share of cited sentences on a gold page"),
    ("correct_refusal", "Correct refusal (out of library)"),
    ("false_refusal", "False refusal (answerable items)"),
    ("invented_on_refusal", "Invented content where refusal expected"),
    ("status_ok", "Evidence status matches"),
    ("differing_shown", "Disagreement shown (differing items)"),
    ("premise_caught", "False premise caught"),
    ("referral", "Personal fatwa referred"),
    ("critical_pass", "Critical items passed"),
]


def num(v):
    if v in ("", "None", None):
        return None
    if v in ("True", "False"):
        return 1.0 if v == "True" else 0.0
    try:
        return float(v)
    except ValueError:
        return None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def summarise(tag_dir):
    tag_dir = pathlib.Path(tag_dir)
    by = defaultdict(list)  # system -> list of run summaries
    for f in sorted(tag_dir.glob("scored_*_run*.csv")):
        system, run = re.match(r"scored_(.+)_run(\d+)\.csv", f.name).groups()
        rows = list(csv.DictReader(open(f, encoding="utf-8")))
        s = {"run": int(run), "n": len(rows), "errors": sum(r["error"] == "True" for r in rows)}
        for key, _ in METRICS:
            s[key] = mean([num(r[key]) for r in rows])
        shown = sum(num(r["sentences"]) or 0 for r in rows)
        s["unverified_shown_share"] = (sum(num(r["unverified_shown"]) or 0 for r in rows) / shown) if shown else None
        s["dropped_share"] = (lambda d: d / (d + shown) if (d + shown) else None)(sum(num(r["dropped"]) or 0 for r in rows))
        lat = sorted(x for x in (num(r["latency_s"]) for r in rows) if x is not None)
        s["latency_median_s"] = st.median(lat) if lat else None
        s["latency_p95_s"] = lat[min(len(lat) - 1, max(0, -(-95 * len(lat) // 100) - 1))] if lat else None
        costs = [num(r["cost_usd"]) for r in rows if num(r["cost_usd"]) is not None]
        s["cost_per_question_usd"] = mean(costs)
        s["crit_failed"] = [r["id"] for r in rows if r["critical_pass"] == "False"]
        by[system].append(s)
    meta = json.loads((tag_dir / "meta.json").read_text(encoding="utf-8")) if (tag_dir / "meta.json").exists() else {}
    agg = {}
    for system, runs in by.items():
        agg[system] = {"runs": len(runs), "n": runs[0]["n"]}
        for key in [m[0] for m in METRICS] + ["unverified_shown_share", "dropped_share", "latency_median_s", "latency_p95_s", "cost_per_question_usd", "errors"]:
            vals = [r[key] for r in runs if r[key] is not None]
            agg[system][key] = {"mean": mean(vals), "min": min(vals) if vals else None, "max": max(vals) if vals else None}
        agg[system]["crit_failed"] = sorted({i for r in runs for i in r["crit_failed"]})
    (tag_dir / "summary.json").write_text(json.dumps({"meta": meta, "systems": agg}, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta, agg


def fmt(v, pct=True):
    if v["mean"] is None:
        return "–"
    f = (lambda x: f"{100 * x:.0f}%") if pct else (lambda x: f"{x:.1f}")
    return f(v["mean"]) + ("" if v["min"] == v["max"] else f" ({f(v['min'])}–{f(v['max'])})")


def table(meta, agg):
    systems = [s for s in ("full", "no_verify", "no_retrieval") if s in agg] + [s for s in agg if s not in ("full", "no_verify", "no_retrieval")]
    runs = max(agg[s]["runs"] for s in systems) if systems else 0
    n = max(agg[s]["n"] for s in systems) if systems else 0
    out = [f"**{meta.get('tag', '')}**: {n} items × {runs} run{'s' if runs != 1 else ''} · answer model `{meta.get('answer_model')}` · "
           f"judge `{meta.get('judge_model')}` · effort {meta.get('effort_answer')} · embeddings {meta.get('embed')} · commit `{meta.get('commit')}`", "",
           "| Metric | " + " | ".join(systems) + " |", "|---|" + "---|" * len(systems)]
    for key, label in METRICS + [("unverified_shown_share", "Shown sentences without verified support"),
                                 ("dropped_share", "Sentences withheld by verification")]:
        out.append(f"| {label} | " + " | ".join(fmt(agg[s][key]) for s in systems) + " |")
    for key, label in (("latency_median_s", "Latency median (s)"), ("latency_p95_s", "Latency p95 (s)")):
        out.append(f"| {label} | " + " | ".join(fmt(agg[s][key], pct=False) for s in systems) + " |")
    out.append("| Cost per question (USD) | " + " | ".join(
        ("–" if agg[s]["cost_per_question_usd"]["mean"] is None else f"{agg[s]['cost_per_question_usd']['mean']:.4f}") for s in systems) + " |")
    out.append("| Errors | " + " | ".join(fmt(agg[s]["errors"], pct=False) for s in systems) + " |")
    crit = {s: agg[s]["crit_failed"] for s in systems if agg[s]["crit_failed"]}
    if crit:
        out.append("\nCritical items failed in at least one run: " + "; ".join(f"{s}: {', '.join(v)}" for s, v in crit.items()))
    return "\n".join(out)


if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(table(*summarise(d)))
        print()
