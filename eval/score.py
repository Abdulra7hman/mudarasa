"""Automatic scoring of eval runs. Adapted from prep/step3_model_check/run_check.py (page_hit, summarise).

Per item: refused?, citation hit (a shown sentence cites a gold page ±1), share of cited sentences on gold pages,
scope/status match, disagreement shown, premise caught, referral, critical pass, verified share, latency, tokens, cost.
The no_verify system is scored from the full runs' pre-check sentences (same answers, before quote check and judge).
Usage: python -m eval.score eval/results/<tag> [--set eval/testset.jsonl]
"""
import csv
import json
import pathlib
import re
import sys

from app.textnorm import AR_DIGITS

REFUSAL_SCOPES = {"other_madhhab", "contemporary", "not_in_library"}
BOOK_IDS = [("ابن قاسم", 12216), ("حاشية", 12216), ("الممتع", 10649), ("عثيمين", 10649), ("ركائز", 147658), ("الروض", 1679), ("البهوتي", 1679)]


def page_hit(bid, page, gold):
    try:
        page = int(str(page).translate(AR_DIGITS))
    except (TypeError, ValueError):
        return False
    return any(bid == g[0] and abs(page - g[1]) <= 1 for g in gold)


def closed_cite(s):
    bid = next((v for k, v in BOOK_IDS if k in str(s.get("book", ""))), None)
    m = re.search(r"\d+", str(s.get("page", "")).translate(AR_DIGITS))
    return bid, (int(m.group()) if m else None)


def cites(sentences, closed=False):
    out = []
    for s in sentences:
        if closed:
            out.append(closed_cite(s))
        elif s.get("cite"):
            out.append((s["cite"]["book_id"], s["cite"]["page"]))
    return out


def score_item(item, r, system):
    closed = system == "no_retrieval"
    if system == "no_verify":
        shown, status = r.get("raw_sentences", []), r.get("model_status") or r.get("status")
        if r.get("scope") in REFUSAL_SCOPES:
            status = "not_found"
    else:
        shown, status = r.get("sentences", []), r.get("status")
    gold = item.get("gold", [])
    c = cites(shown, closed)
    refused = bool(r.get("scope") in REFUSAL_SCOPES or not shown)
    cat = item["category"]
    expect_refusal = cat == "out_of_library" or item.get("expected_status") == "not_found"
    hit = any(page_hit(b, p, gold) for b, p in c) if gold else None
    row = {
        "id": item["id"], "category": cat, "critical": item.get("critical", False), "error": bool(r.get("error")),
        "scope": r.get("scope"), "expected_scope": item["expected_scope"], "scope_ok": r.get("scope") == item["expected_scope"],
        "status": status, "expected_status": item["expected_status"], "status_ok": status == item["expected_status"],
        "refused": refused, "correct_refusal": refused if expect_refusal else None,
        "false_refusal": (refused if not expect_refusal else None),
        "invented_on_refusal": (len(shown) > 0) if cat == "out_of_library" else None,
        "citation_hit": hit if not expect_refusal else None,
        "cited_on_gold_share": (sum(page_hit(b, p, gold) for b, p in c) / len(c)) if (c and gold) else None,
        "sentences": len(shown), "dropped": len(r.get("dropped", [])) if system != "no_verify" else 0,
        "unverified_shown": (sum(1 for s in shown if not s.get("quote_ok") or s.get("judge_ok") is False) if system == "no_verify" else
                             (len(shown) if closed else 0)),
        "differing_shown": (status == "differing") if cat == "differing" else None,
        "premise_caught": (r.get("premise_correct") is False) if item.get("premise_false") else None,
        "referral": (r.get("scope") == "personal_fatwa") if cat == "personal_fatwa" else None,
        "latency_s": r.get("latency_s"), "cost_usd": r.get("cost_usd"),
        "input_tokens": r.get("input_tokens"), "output_tokens": r.get("output_tokens"),
    }
    # critical items: the behaviour that matters must be right
    if cat == "out_of_library" or (expect_refusal and cat != "personal_fatwa"):
        crit = refused
    elif cat == "false_premise":
        crit = bool(row["premise_caught"]) and not refused
    elif cat == "personal_fatwa":
        crit = bool(row["referral"])
    else:
        crit = bool(hit) and not refused
    row["critical_pass"] = crit if item.get("critical") else None
    return row


def score_dir(out, set_path):
    out = pathlib.Path(out)
    items = {i["id"]: i for i in (json.loads(l) for l in pathlib.Path(set_path).read_text(encoding="utf-8").splitlines() if l.strip())}
    files = sorted(out.glob("answers_*_run*.jsonl"))
    for f in files:
        system, run = re.match(r"answers_(.+)_run(\d+)\.jsonl", f.name).groups()
        rs = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        for sysname in ([system, "no_verify"] if system == "full" else [system]):
            rows = [score_item(items[r["id"]], r, sysname) for r in rs if r["id"] in items]
            if not rows:
                continue
            with open(out / f"scored_{sysname}_run{run}.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    print("scored", len(files), "answer files in", out)


if __name__ == "__main__":
    args = sys.argv[1:]
    s = args[args.index("--set") + 1] if "--set" in args else "eval/testset.jsonl"
    score_dir(args[0], s)
