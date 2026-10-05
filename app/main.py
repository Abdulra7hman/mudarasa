"""Mudarasa web app: FastAPI backend + static front end (web/).

Run locally:  make run   (http://127.0.0.1:8000)
Logs (no personal data, no IP addresses): data/logs/questions.jsonl, data/logs/reports.jsonl
"""
import asyncio
import json
import queue
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import books as B
from . import config as C
from . import pipeline
from . import prompts as P
from .textnorm import normalise

ROOT = B.ROOT
LOGS = B.DATA / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
CACHE_FILE = B.DATA / "build" / "answer_cache.json"

app = FastAPI(title="Mudarasa")
STUDY = json.loads((B.DATA / "build/study.json").read_text(encoding="utf-8"))
SUGGESTED = [
    {"q": "ما حكم الماء الآجن، وهو المتغير بطول مكثه؟", "kind": "جواب موثق"},
    {"q": "ما الفرق بين الطاهر والطهور؟", "kind": "أقوال واختلاف"},
    {"q": "ما حكم الوضوء بماء البحر عند المالكية؟", "kind": "خارج النطاق"},
]

_lock = threading.Lock()
_cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}
_hits = defaultdict(deque)  # per-client request times, in memory only (never logged)
_day = {"date": time.strftime("%Y-%m-%d"), "n": 0}


def _log(name, row):
    with _lock, (LOGS / name).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **row}, ensure_ascii=False) + "\n")


def _limit(request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= C.PER_IP_PER_MINUTE:
        raise HTTPException(429, "عدد كبير من الأسئلة في دقيقة واحدة. انتظر قليلًا ثم أعد المحاولة.")
    q.append(now)
    today = time.strftime("%Y-%m-%d")
    if _day["date"] != today:
        _day.update(date=today, n=0)
    if _day["n"] >= C.DAILY_QUESTION_CAP:
        raise HTTPException(503, "بلغت الخدمة حدها اليومي من الأسئلة. أعد المحاولة غدًا.")
    _day["n"] += 1


@app.get("/healthz")
def healthz():
    return {"ok": True, "provider": C.LLM_PROVIDER, "answer_model": C.MODEL_ANSWER, "judge_model": C.MODEL_JUDGE}


@app.get("/api/config")
def config():
    return {"features": C.FEATURES, "disclosure": P.AI_DISCLOSURE, "suggested": SUGGESTED,
            "status_ar": P.STATUS_AR, "books": {str(k): v for k, v in B.BOOK_NAMES.items()},
            "chapters": [{"id": c["id"], "title": c["title"], "n": len(c["paras"])} for c in STUDY["chapters"]]}


@app.get("/api/chapter/{cid}")
def chapter(cid: str):
    ch = next((c for c in STUDY["chapters"] if c["id"] == cid), None)
    if not ch:
        raise HTTPException(404, "not found")
    paras = []
    for pid in ch["paras"]:
        p = dict(STUDY["paras"][pid])
        p["units"] = [STUDY["units"][u] for u in p["units"]]
        paras.append(p)
    return {"id": cid, "title": ch["title"], "paras": paras}


async def _question(request: Request):
    body = await request.json()
    q = (body.get("question") or "").strip()[:500]
    if not q:
        raise HTTPException(400, "اكتب سؤالًا")
    return q, body.get("para") or None


def _run(q, para, events=None):
    """The pipeline, or search-only mode when the model is unreachable."""
    try:
        return pipeline.answer(q, para=para, events=events)
    except Exception as e:  # model outage: show the cited passages only (search-only mode)
        try:
            shown = pipeline.retriever().search(q, para=para)
        except Exception:
            shown = []
        return {"question": q, "scope": "answerable", "status": "not_found", "status_ar": "وضع البحث فقط",
                "message": "تعذر الوصول إلى نموذج اللغة الآن. هذه أقرب النصوص إلى سؤالك من الكتب المعتمدة، دون جواب مولَّد.",
                "sentences": [], "dropped": [], "search_only": True, "error": type(e).__name__,
                "passages": [{"n": i, **pipeline._cite(p), "text": p["text"], "para": p.get("para")} for i, p in enumerate(shown, 1)]}


def _finish(q, para, key, res):
    """Cache good answers, log the measurements (no personal data), drop internal fields."""
    if not res.get("cached") and not res.get("search_only") and (res.get("sentences") or res.get("scope") in P.REFUSALS):
        with _lock:
            _cache[key] = {k: v for k, v in res.items() if k != "calls"}
            if len(_cache) % 5 == 0:
                CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
    _log("questions.jsonl", {"question": q, "para": para, "scope": res.get("scope"), "status": res.get("status"),
                             "kept": len(res.get("sentences", [])), "dropped": len(res.get("dropped", [])),
                             "latency_s": res.get("latency_s"), "cost_usd": res.get("cost_usd"),
                             "input_tokens": res.get("input_tokens"), "output_tokens": res.get("output_tokens"),
                             "cached": bool(res.get("cached")), "search_only": bool(res.get("search_only"))})
    return {k: v for k, v in res.items() if k != "calls"}


@app.post("/api/ask")
async def ask(request: Request):
    q, para = await _question(request)
    key = normalise(q) + "|" + (para or "")
    if key in _cache:
        res = {**_cache[key], "cached": True}
    else:
        _limit(request)
        res = await asyncio.get_running_loop().run_in_executor(None, _run, q, para)
    return JSONResponse(_finish(q, para, key, res))


@app.post("/api/ask_stream")
async def ask_stream(request: Request):
    """Server-sent events: stage changes and the passages as soon as they are found, then the checked answer."""
    q, para = await _question(request)
    key = normalise(q) + "|" + (para or "")
    cached = _cache.get(key)
    if not cached:
        _limit(request)
    events = queue.Queue()

    def work():
        res = {**cached, "cached": True} if cached else _run(q, para, events=lambda kind, payload: events.put((kind, payload)))
        events.put(("result", _finish(q, para, key, res)))
        events.put(None)

    threading.Thread(target=work, daemon=True).start()

    async def stream():
        loop = asyncio.get_running_loop()
        while True:
            item = await loop.run_in_executor(None, events.get)
            if item is None:
                break
            kind, payload = item
            yield f"event: {kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/report")
async def report(request: Request):
    body = await request.json()
    row = {k: str(body.get(k, ""))[:2000] for k in ("kind", "question", "where", "comment")}
    _log("reports.jsonl", row)
    return {"ok": True, "message": "شكرًا لك، وصل البلاغ وسيراجعه المختص."}


# optional feature routers are added by their modules when present
try:
    from . import features
    features.register(app, STUDY)
except ImportError:
    pass

app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
