"""Retrieval check: for answerable test items, is a gold page (±1) among the top-k passages?

Compares keyword (BM25), dense (each available embedding provider) and hybrid (RRF of keyword + dense).
Adapted from prep/retrieval/retrieval_test.py (hit, rank_of_first_hit).
Usage: python -m eval.retrieval_check [--set eval/testset.jsonl] [--k 8] [--providers azure,ollama]
"""
import argparse
import json
import pathlib

from app.retrieval import Retriever, build_passages
from app import books as B

HERE = pathlib.Path(__file__).resolve().parent


def first_hit(passages, gold):
    for r, p in enumerate(passages, 1):
        if any(p["book_id"] == g[0] and abs(int(p["page"]) - g[1]) <= 1 for g in gold):
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default=str(HERE / "testset.jsonl"))
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--providers", default="azure,ollama")
    a = ap.parse_args()
    items = [json.loads(l) for l in pathlib.Path(a.set).read_text(encoding="utf-8").splitlines() if l.strip()]
    items = [i for i in items if i.get("gold") and i["category"] in ("answerable", "differing", "false_premise", "personal_fatwa")]
    study = json.loads((B.DATA / "build/study.json").read_text(encoding="utf-8"))
    passages = build_passages(study)
    rows = {}
    keyword = Retriever(passages, provider="none")
    rows["keyword"] = [first_hit(keyword.search(i["question"], k=a.k, mode="keyword"), i["gold"]) for i in items]
    for prov in a.providers.split(","):
        try:
            r = Retriever(passages, provider=prov)
            if r.vecs is None:
                continue
            rows[f"dense:{prov}"] = [first_hit(r.search(i["question"], k=a.k, mode="dense"), i["gold"]) for i in items]
            rows[f"hybrid:{prov}"] = [first_hit(r.search(i["question"], k=a.k, mode="hybrid"), i["gold"]) for i in items]
        except Exception as e:
            print(prov, "unavailable:", e)
    n = len(items)
    out = [f"Retrieval check: {n} items with gold pages ({a.set}), top {a.k}", "",
           f"| Method | Gold page in top {a.k} | Ranked first | Mean rank of first hit |", "|---|---|---|---|"]
    for m, hits in rows.items():
        found = [h for h in hits if h]
        out.append(f"| {m} | {len(found)}/{n} ({len(found) / n:.0%}) | {sum(h == 1 for h in found)}/{n} | "
                   f"{(sum(found) / len(found)):.1f} |" if found else f"| {m} | 0/{n} | 0 | – |")
    text = "\n".join(out)
    (HERE / "RETRIEVAL.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
