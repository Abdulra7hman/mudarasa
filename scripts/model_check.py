"""Choose the models by test: run the quick set (10 questions) through the full pipeline for each candidate.

Usage:
  python -m scripts.model_check "azure:gpt-5.4:low" "azure:gpt-5.4:none" "azure:gpt-5.4-mini:low" "github:gpt-5-mini:low"
Each candidate is provider:answer_model:effort; the judge model is --judge (default from .env).
Writes eval/results/model_check_<time>.md with one table per candidate, then picks nothing: you decide from the table.
"""
import argparse
import pathlib
import subprocess
import sys
import time

from app import config as C
from eval import report

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates", nargs="+")
    ap.add_argument("--judge", default=None)
    ap.add_argument("--set", default="eval/quick.jsonl")
    ap.add_argument("--systems", default="full")
    a = ap.parse_args()
    stamp = time.strftime("%m%d-%H%M")
    parts = [f"# Model check {stamp}\n\nQuick set `{a.set}`, systems {a.systems}, 1 run each.\n"]
    for cand in a.candidates:
        provider, model, effort = (cand.split(":") + ["low"])[:3]
        judge = a.judge or (model if provider == "github" else C.MODEL_JUDGE)
        tag = f"mc_{stamp}_{provider}_{model.replace('/', '-')}_{effort}"
        cmd = [sys.executable, "-m", "eval.run", "--set", a.set, "--systems", a.systems, "--runs", "1", "--provider", provider,
               "--answer-model", model, "--judge-model", judge, "--effort", effort, "--tag", tag, "--workers", "2"]
        print(">>", " ".join(cmd), flush=True)
        subprocess.run(cmd, cwd=ROOT)
        d = ROOT / "eval/results" / tag
        if list(d.glob("scored_*.csv")):
            parts.append(f"## {cand} (judge {judge})\n\n" + report.table(*report.summarise(d)) + "\n")
    out = ROOT / "eval/results" / f"model_check_{stamp}.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
