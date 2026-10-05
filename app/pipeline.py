"""The answer pipeline. Each step exists so that a sentence is either traced to a page or withheld.

  1. scope gate (separate, cheaper call): other madhhab / contemporary / unrelated -> fixed wording, no generation
  2. retrieval: the open paragraph's commentary first, then hybrid search over the library (top 8)
  3. evidence-first answer: every sentence carries a passage number and a verbatim quote
  4. quote check: the quote must exist (after normalising) in the cited passage
  5. support judge (cheaper model): does the quote actually say what the sentence says?
  6. evidence status recomputed from what survives; personal-fatwa and false-premise wording from the answer policy

Adapted from prep/demo/server.py (answer). Steps 2 and 4-5 can be switched off for the comparison runs in eval/.
"""
import concurrent.futures
import re
import time

from . import config as C
from . import llm
from . import prompts as P
from .textnorm import normalise

_RET = None
PMARK = re.compile(r"\s*[\[(]\s*P\d+\s*[\])]\s*")
# markers of an attributed position: روايتان، وجهان، وعنه، قيل، قال الشيخ، اختار، والصحيح، خالف، الجمهور، المذهب، القول الآخر …
ATTRIBUTION = re.compile("|".join(normalise(w) for w in "روايتان|رواية|وجهان|وعنه|عن أحمد|قيل|قال الشيخ|اختار|اختاره|والصحيح|خالف|الجمهور|القول الآخر|قول آخر|القولين|قولان|خلاف|بعض الأصحاب|ذهب|يرى|المذهب".split("|")))
# first-person wording: the question is about the asker's own case (a backstop for the scope gate)
FIRST_PERSON = re.compile("|".join(normalise(w) for w in (
    "يلزمني|يجزئني|يجزيني|علي أن|هل علي|صلاتي|وضوئي|طهارتي|ثوبي|ثيابي|عندي|لدي|أعيد|اعيد صلاتي|يجوز لي|فهل لي|"
    "توضأت|صليت|اغتسلت|استنجيت|استجمرت|اشتريت|نسيت|أهدي إلي|اهدي الي|طفلي|ابني|بنتي|زوجتي|بيتي|سيارتي").split("|")))


def retriever():
    global _RET
    if _RET is None:
        from .retrieval import Retriever
        _RET = Retriever()
    return _RET


def context(p, quote, width=220):
    """The passage text around the quote, so the judge sees which term or issue the quote is about."""
    text, q = p["text"], (quote or "").strip()
    i = text.find(q[:30]) if q else -1
    if i < 0:  # tashkeel or spacing differs: fall back to the passage start
        return text[: 2 * width]
    return text[max(0, i - width): i + len(q) + width]


def _cite(p):
    return {k: p[k] for k in ("book_id", "book", "vol", "page", "pg", "kind", "link", "id")}


def _sum(calls, key):
    vals = [c.get(key) for c in calls if c.get(key) is not None]
    return round(sum(vals), 6) if vals else None


_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=8)


def _gate(question, provider):
    gate, st = llm.ask(P.SCOPE_RULES, f"السؤال: {question}", P.SCHEMA_SCOPE, role="gate", provider=provider, max_out=1500)
    scope = gate.get("scope", "answerable") if isinstance(gate, dict) else "answerable"
    if scope not in P.SCOPE_ENUM:
        scope = "answerable"
    if scope == "answerable" and FIRST_PERSON.search(normalise(question)):
        scope = "personal_fatwa"
    return scope, st


def answer(question, para=None, retrieval=True, verify=True, provider=None, k=8, events=None):
    """events(kind, payload): optional progress callback ("stage", name) / ("passages", list), used for streaming."""
    t0, calls = time.time(), []
    emit = events or (lambda kind, payload: None)
    res = {"question": question, "para": para, "retrieval": retrieval, "verify": verify}
    # the scope check runs alongside search and answer; a refusal discards the answer (refusals are rare and cheap)
    parallel = C.PARALLEL_GATE and retrieval
    gate_future = _POOL.submit(_gate, question, provider) if parallel else None
    if not parallel:
        emit("stage", "scope")
        scope, st = _gate(question, provider)
        calls.append({"step": "scope", **st})
    else:
        scope = None
    res["scope"] = scope

    def done(**kw):
        res.update(kw)
        res["status_ar"] = P.STATUS_AR.get(res.get("status"), res.get("status"))
        res.update(calls=calls, latency_s=round(time.time() - t0, 1), cost_usd=_sum(calls, "cost_usd"),
                   input_tokens=_sum(calls, "input_tokens"), output_tokens=_sum(calls, "output_tokens"))
        return res

    if scope in P.REFUSALS:
        return done(status="not_found", message=P.REFUSALS[scope], sentences=[], dropped=[], raw_sentences=[], passages=[])

    def gate_result():
        nonlocal scope
        if gate_future is not None and scope is None:
            scope, st = gate_future.result()
            calls.append({"step": "scope", **st})
            res["scope"] = scope
        return scope

    personal = (scope == "personal_fatwa") or (scope is None and bool(FIRST_PERSON.search(normalise(question))))
    if not retrieval:  # closed-book baseline: the same model, no library, cites from memory
        ans, st = llm.ask(P.CLOSED_FAIR, f"السؤال: {question}", P.SCHEMA_CLOSED, role="answer", provider=provider)
        calls.append({"step": "answer", **st})
        sents = [{"text": s.get("text", ""), "book": s.get("book"), "vol": s.get("vol"), "page": s.get("page"), "quote": s.get("quote")}
                 for s in (ans.get("sentences") or [])]
        return done(status=ans.get("status", "not_found"), premise_correct=ans.get("premise_correct"), message=None,
                    sentences=sents, dropped=[], raw_sentences=sents, passages=[])

    emit("stage", "search")
    shown = retriever().search(question, k=k, para=para)
    passages = [{"n": i, **_cite(p), "text": p["text"], "para": p.get("para")} for i, p in enumerate(shown, 1)]
    emit("passages", passages)
    emit("stage", "write")
    ctx = "\n\n".join(f"[P{i}] {p['book']}، ج{p['vol']} ص{p['page']} ({p['kind']}):\n{p['text']}" for i, p in enumerate(shown, 1))
    rules, schema = (P.RULES_V2, P.SCHEMA_ANSWER) if C.EVIDENCE_FIRST else (P.RULES_FAST, P.SCHEMA_ANSWER_FAST)
    system = rules + (P.GENERAL_MODE if personal else "")
    try:
        ans, st = llm.ask(system, f"النصوص:\n{ctx}\n\nالسؤال: {question}", schema, role="answer", provider=provider)
    except Exception as e:
        if "content management policy" not in str(e) and "content_filter" not in str(e):
            raise
        gate_result()
        if scope in P.REFUSALS:
            return done(status="not_found", message=P.REFUSALS[scope], sentences=[], dropped=[], raw_sentences=[], passages=[])
        return done(status="not_found", message=P.FILTERED, sentences=[], dropped=[], raw_sentences=[], passages=passages,
                    filtered=True, model_status=None)
    calls.append({"step": "answer", **st})
    if gate_result() in P.REFUSALS:  # the parallel scope check says: refuse, and discard the answer
        return done(status="not_found", message=P.REFUSALS[scope], sentences=[], dropped=[], raw_sentences=[], passages=[])
    personal = scope == "personal_fatwa"

    checked = []
    for s in ans.get("sentences") or []:
        digits = re.findall(r"\d+", str(s.get("passage", "")))
        n = int(digits[0]) if digits else None
        p = shown[n - 1] if n and 0 < n <= len(shown) else None
        q = normalise(s.get("quote", ""))
        ok = bool(p and q and q in p["norm"])
        checked.append({"k": len(checked), "text": PMARK.sub(" ", s.get("text", "")).strip(), "quote": s.get("quote", ""), "n": n,
                        "cite": _cite(p) if p else None, "quote_ok": ok,
                        "reason": None if ok else ("رقم المقطع غير صحيح" if not p else "الاقتباس غير موجود حرفيًّا في المقطع")})
    raw = [dict(c) for c in checked]

    if verify:
        emit("stage", "verify")
        kept = [c for c in checked if c["quote_ok"]]
        dropped = [c for c in checked if not c["quote_ok"]]
        if kept:
            items = "\n\n".join(f"[{i}] الجملة: {c['text']}\nالاقتباس: «{c['quote']}»\nالسياق ({c['cite']['book']}): …{context(shown[c['n'] - 1], c['quote'])}…"
                                  for i, c in enumerate(kept))
            j, st = llm.ask(P.JUDGE_RULES, f"سؤال الطالب: {question}\n\n{items}", P.SCHEMA_JUDGE, role="judge", provider=provider, max_out=8000)
            calls.append({"step": "judge", **st})
            verdicts = {v.get("i"): v for v in (j.get("verdicts") or [])} if isinstance(j, dict) else {}
            survivors = []
            for i, c in enumerate(kept):
                v = verdicts.get(i)
                if v is not None and not v.get("supported"):
                    c["reason"] = "الاقتباس لا يدل على الجملة" + (f": {v.get('why')}" if v.get("why") else "")
                    raw[c["k"]]["judge_ok"] = False  # so the no-verification baseline counts it as unsupported
                    dropped.append(c)
                else:
                    c["judge"] = "supported" if v else "missing"
                    survivors.append(c)
            kept = survivors
    else:
        kept, dropped = checked, []

    status = ans.get("status", "not_found")
    if status not in P.STATUS_ENUM:
        status = "not_found"
    if status == "differing" and not any(ATTRIBUTION.search(normalise(c["text"] + " " + c["quote"])) for c in kept):
        status = "supported"  # «أقوال مختلفة» needs a kept sentence that names who holds a position
    if not kept:
        status = "not_found"
    elif dropped and status == "supported":
        status = "partial"
    elif status == "not_found":
        status = "partial" if dropped else "supported"

    message = None
    if not kept:
        message = P.PERSONAL_NOTHING if personal else P.REFUSALS["not_in_library"]
    elif personal:
        message = P.PERSONAL_PREFIX
    elif ans.get("premise_correct") is False:
        message = P.PREMISE_PREFIX

    return done(status=status, premise_correct=ans.get("premise_correct"), message=message, sentences=kept, dropped=dropped,
                raw_sentences=raw, passages=passages, model_status=ans.get("status"))
