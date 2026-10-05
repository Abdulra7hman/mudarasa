"""Prep (2 Oct): retrieval test. Is a correct page (±1) among the 8 passages given to the model?

Questions: the 10 from step 3 (answerable ones) + 4 asked by the user in the browser on 2 Oct.
Systems: old BM25 (step 3), keyword with stemming, dense (BGE-M3), hybrid, and Turath's own search (turath_find, our 4 books).
Output: results.md, results.json
"""
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "step3_model_check"))
import retrieval as RT  # noqa: E402
import run_check as OLD  # noqa: E402  (step-3 BM25)

USER_QS = [  # asked in the browser test, 2 Oct; expected pages found by searching the 4 books
    {"id": "U1", "question": "ما هو أول باب في الفقه؟", "gold": [[1679, 7], [147658, 70]]},
    {"id": "U2", "question": "كم أنواع المياه؟", "gold": [[1679, 8], [147658, 71], [10649, 28], [12216, 58]]},
    {"id": "U3", "question": "ما معنى الطهارة لغةً؟", "gold": [[1679, 7], [147658, 70], [10649, 25]]},
    {"id": "U4", "question": "ما الفرق بين الطاهر والطهور؟", "gold": [[1679, 8], [147658, 71], [12216, 58], [12216, 59], [10649, 28], [10649, 32]]},
]


def hit(p, gold):
    return any(p["book_id"] == b and abs(int(p["page"]) - pg) <= 1 for b, pg in gold)


def rank_of_first_hit(ps, gold):
    return next((i + 1 for i, p in enumerate(ps) if hit(p, gold)), None)


# ---------- Turath's own search (MCP), limited to our four books ----------
TURATH = "https://api.turath.ai/mcp"


def mcp(method, params, sid=None, rid=1):
    h = ["-H", "Content-Type: application/json", "-H", "Accept: application/json, text/event-stream"]
    if sid:
        h += ["-H", f"mcp-session-id: {sid}"]
    r = subprocess.run(["curl", "-s", "-m", "60", "-D", "-", *h, "-X", "POST", TURATH, "-d",
                        json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})], capture_output=True)
    head, _, body = r.stdout.decode().partition("\r\n\r\n")
    new_sid = next((l.split(":", 1)[1].strip() for l in head.splitlines() if l.lower().startswith("mcp-session-id")), sid)
    body = body.strip()
    if body.startswith("event:") or "data:" in body[:20]:
        body = "\n".join(l[5:].strip() for l in body.splitlines() if l.startswith("data:"))
    return (json.loads(body, strict=False) if body else {}), new_sid


def turath_search(question):
    _, sid = mcp("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "mudarasa-prep", "version": "0"}})
    subprocess.run(["curl", "-s", "-m", "30", "-H", "Content-Type: application/json", "-H", "Accept: application/json, text/event-stream",
                    "-H", f"mcp-session-id: {sid}", "-X", "POST", TURATH, "-d", '{"jsonrpc":"2.0","method":"notifications/initialized"}'],
                   capture_output=True)
    res, _ = mcp("tools/call", {"name": "turath_find", "arguments": {"query": key_terms(question), "book": [1679, 147658, 12216, 10649], "limit": 8}}, sid, 2)
    return res


def turath_passages(res):
    """(book_id, page) of each hit, in rank order."""
    sc = (res.get("result") or {}).get("structuredContent") or {}
    out = []
    for it in sc.get("items", []):
        m = re.match(r"tr_book_(\d+)", it.get("book_ref", ""))
        if m and str(it.get("page", "")).isdigit():
            out.append({"book_id": int(m.group(1)), "page": int(it["page"])})
    return out[:8]


def key_terms(question):
    """turath_find needs all words to match, so send the question without question-frame words (as an AI caller would)."""
    words = [w for w in RT.A.normalise(question).split() if RT.stem(w) not in RT.QUESTION_WORDS]
    return " ".join(words)


def main():
    qs = [json.loads(l) for l in (HERE.parent / "step3_model_check/questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    qs = [q for q in qs if q["gold"]] + USER_QS
    R = RT.Retriever()
    old_passages = OLD.build_passages()
    old_bm25 = OLD.BM25([p["tokens"] for p in old_passages])
    systems = {
        "bm25_step3": lambda q: OLD.retrieve(q, old_passages, old_bm25),
        "keyword_stem": lambda q: R.search(q, mode="keyword"),
        "dense_bge_m3": lambda q: R.search(q, mode="dense"),
        "hybrid": lambda q: R.search(q, mode="hybrid"),
    }
    rows, raw_turath = [], {}
    for q in qs:
        row = {"id": q["id"], "question": q["question"]}
        for name, fn in systems.items():
            row[name] = rank_of_first_hit(fn(q["question"]), q["gold"])
        try:
            res = turath_search(q["question"])
            raw_turath[q["id"]] = res
            row["turath_find"] = rank_of_first_hit(turath_passages(res), q["gold"])
        except Exception as e:
            row["turath_find"] = f"error: {e}"
        rows.append(row)
        print(row, flush=True)
    names = list(systems) + ["turath_find"]
    lines = ["| Q | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    for r in rows:
        lines.append(f"| {r['id']} {r['question']} | " + " | ".join("✗" if r[n] is None else str(r[n]) for n in names) + " |")
    lines.append("| **Found in top 8** | " + " | ".join(f"**{sum(1 for r in rows if isinstance(r[n], int))}/{len(rows)}**" for n in names) + " |")
    (HERE / "results.md").write_text("Rank of the first passage on a correct page (±1) among the 8 given to the model; ✗ = not found.\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    (HERE / "results.json").write_text(json.dumps({"rows": rows, "turath_raw": raw_turath}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
