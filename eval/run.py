"""Run the test set through one or more systems, several times.

  full          scope gate -> hybrid retrieval -> answer -> quote check -> support judge
  no_retrieval  the same model with no library (closed book; cites from memory)
  no_verify     derived from the full runs at no extra cost: the same answers, scored before the quote check and judge
  (fallback     = full on another provider/model, e.g. --provider ollama, written under its own tag)

Usage:
  python -m eval.run --set eval/testset.jsonl --systems full,no_retrieval --runs 3 [--provider azure]
                     [--answer-model gpt-5.4 --judge-model gpt-5.4-mini --effort low] [--tag NAME] [--workers 4]
Writes eval/results/<tag>/answers_<system>_run<k>.jsonl (gitignored: quotes the books) and meta.json,
then scores them (eval/score.py) into scored_<system>_run<k>.csv (no book text).
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import subprocess
import time

from app import config as C
from app import pipeline

HERE = pathlib.Path(__file__).resolve().parent


def load_set(path):
    return [json.loads(l) for l in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def slim(res):
    """Keep what scoring and error analysis need; drop full passage texts."""
    out = {k: v for k, v in res.items() if k != "passages"}
    out["passages"] = [{k: p[k] for k in ("n", "book_id", "vol", "page", "kind")} for p in res.get("passages", [])]
    return out


def one(item, system, provider):
    t = time.time()
    try:
        res = pipeline.answer(item["question"], retrieval=(system != "no_retrieval"), verify=True, provider=provider)
    except Exception as e:
        res = {"error": f"{type(e).__name__}: {e}"[:500], "latency_s": round(time.time() - t, 1), "sentences": [], "dropped": [],
               "raw_sentences": [], "passages": [], "scope": None, "status": None}
    return {"id": item["id"], "system": system, **slim(res)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default=str(HERE / "testset.jsonl"))
    ap.add_argument("--systems", default="full,no_retrieval")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--answer-model")
    ap.add_argument("--judge-model")
    ap.add_argument("--effort")
    ap.add_argument("--tag")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", help="comma-separated ids")
    a = ap.parse_args()
    if a.answer_model:
        C.MODEL_ANSWER = a.answer_model
    if a.judge_model:
        C.MODEL_JUDGE = a.judge_model
    if a.effort:
        C.EFFORT_ANSWER = C.EFFORT_JUDGE = a.effort
    provider = a.provider or C.LLM_PROVIDER
    items = load_set(a.set)
    if a.only:
        keep = set(a.only.split(","))
        items = [i for i in items if i["id"] in keep]
    model_tag = "gemma" if provider == "ollama" else C.MODEL_ANSWER.split("/")[-1]
    tag = a.tag or f"{time.strftime('%m%d-%H%M')}_{pathlib.Path(a.set).stem}_{provider}_{model_tag}"
    out = HERE / "results" / tag
    out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    meta = {"tag": tag, "set": a.set, "items": len(items), "systems": a.systems, "runs": a.runs, "provider": provider,
            "answer_model": C.OLLAMA_MODEL if provider == "ollama" else C.MODEL_ANSWER,
            "judge_model": C.OLLAMA_MODEL if provider == "ollama" else C.MODEL_JUDGE,
            "effort_answer": C.EFFORT_ANSWER, "effort_judge": C.EFFORT_JUDGE, "embed": f"{C.EMBED_PROVIDER}:{C.MODEL_EMBED if C.EMBED_PROVIDER == 'azure' else C.OLLAMA_EMBED_MODEL}",
            "commit": commit, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "prices": C.PRICES}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    pipeline.retriever()  # build the index once before threads start
    workers = 1 if provider == "ollama" else a.workers
    for run in range(1, a.runs + 1):
        for system in [s for s in a.systems.split(",") if s != "no_verify"]:
            path = out / f"answers_{system}_run{run}.jsonl"
            done = {json.loads(l)["id"] for l in path.read_text(encoding="utf-8").splitlines()} if path.exists() else set()
            todo = [i for i in items if i["id"] not in done]
            print(f"[{tag}] {system} run {run}: {len(todo)} to do", flush=True)
            with cf.ThreadPoolExecutor(workers) as ex, path.open("a", encoding="utf-8") as f:
                futs = {ex.submit(one, i, system, provider): i for i in todo}
                for k, fu in enumerate(cf.as_completed(futs), 1):
                    r = fu.result()
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    f.flush()
                    print(f"  {k}/{len(todo)} {r['id']} {r.get('scope')} {r.get('status')} {r.get('latency_s')}s"
                          + (f" ERROR {r['error'][:80]}" if r.get("error") else ""), flush=True)
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    from eval import score
    score.score_dir(out, a.set)
    print("results:", out)


if __name__ == "__main__":
    main()
