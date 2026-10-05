"""Pipeline rules with a fake model: quote check, support judge, evidence status, refusal and referral wording."""
from app import pipeline
from app import prompts as P
from app.textnorm import normalise

PASSAGES = [
    {"book_id": 1679, "book": "الروض", "vol": 1, "page": 9, "pg": 8, "kind": "متن وشرح", "link": "x", "id": "a", "para": "p1",
     "text": "(وإن تغير بمكثه) أي بطول إقامته في مقره وهو الآجن لم يكره"},
    {"book_id": 12216, "book": "ابن قاسم", "vol": 1, "page": 65, "pg": 64, "kind": "حاشية", "link": "y", "id": "b", "para": "p1",
     "text": "والآجن الدائم الذي لا يجري"},
]
for p in PASSAGES:
    p["norm"] = normalise(p["text"])


class FakeRet:
    def search(self, q, k=8, para=None):
        return PASSAGES


def fake(scope, sentences, status="supported", premise=True, judge=None):
    def ask(system, user, schema, role="answer", **kw):
        if system == P.SCOPE_RULES:
            return {"scope": scope}, {"cost_usd": 0.0}
        if system == P.JUDGE_RULES:
            return {"verdicts": [{"i": i, "supported": ok, "why": ""} for i, ok in enumerate(judge or [])]}, {"cost_usd": 0.0}
        return {"scope": "answerable", "premise_correct": premise, "evidence": [], "sentences": sentences, "status": status}, {"cost_usd": 0.0}
    return ask


def run(monkeypatch, **kw):
    monkeypatch.setattr(pipeline, "_RET", FakeRet())
    monkeypatch.setattr(pipeline.llm, "ask", fake(**kw))
    return pipeline.answer("سؤال")


GOOD = {"text": "الماء الآجن لا يكره", "passage": "P1", "quote": "وهو الآجن لم يكره"}
BAD_QUOTE = {"text": "يحرم الوضوء بالآجن", "passage": "P1", "quote": "يحرم الوضوء به"}
WRONG_P = {"text": "الآجن الدائم", "passage": "P9", "quote": "الدائم"}


def test_other_madhhab_refused_without_generation(monkeypatch):
    r = run(monkeypatch, scope="other_madhhab", sentences=[GOOD])
    assert r["status"] == "not_found" and r["message"] == P.REFUSALS["other_madhhab"] and not r["sentences"]


def test_supported_when_all_verified(monkeypatch):
    r = run(monkeypatch, scope="answerable", sentences=[GOOD], judge=[True])
    assert r["status"] == "supported" and len(r["sentences"]) == 1 and r["sentences"][0]["cite"]["page"] == 9


def test_quote_not_in_passage_dropped_and_partial(monkeypatch):
    r = run(monkeypatch, scope="answerable", sentences=[GOOD, BAD_QUOTE, WRONG_P], judge=[True])
    assert r["status"] == "partial" and len(r["sentences"]) == 1 and len(r["dropped"]) == 2
    assert {d["reason"] for d in r["dropped"]} == {"الاقتباس غير موجود حرفيًّا في المقطع", "رقم المقطع غير صحيح"}


def test_judge_drops_unsupported_sentence(monkeypatch):
    drift = {"text": "الماء الآجن لا يجوز الوضوء به", "passage": "P1", "quote": "وهو الآجن لم يكره"}
    r = run(monkeypatch, scope="answerable", sentences=[GOOD, drift], judge=[True, False])
    assert r["status"] == "partial" and [s["text"] for s in r["sentences"]] == [GOOD["text"]]
    assert r["dropped"][0]["reason"].startswith("الاقتباس لا يدل على الجملة")


def test_nothing_survives_is_not_found_with_refusal(monkeypatch):
    r = run(monkeypatch, scope="answerable", sentences=[BAD_QUOTE])
    assert r["status"] == "not_found" and r["message"] == P.REFUSALS["not_in_library"]


def test_personal_fatwa_general_statement_plus_referral(monkeypatch):
    r = run(monkeypatch, scope="personal_fatwa", sentences=[GOOD], judge=[True])
    assert r["message"] == P.PERSONAL_PREFIX and len(r["sentences"]) == 1


def test_false_premise_prefix(monkeypatch):
    r = run(monkeypatch, scope="answerable", sentences=[GOOD], premise=False, judge=[True])
    assert r["message"] == P.PREMISE_PREFIX


def test_no_verify_keeps_everything_raw(monkeypatch):
    monkeypatch.setattr(pipeline, "_RET", FakeRet())
    monkeypatch.setattr(pipeline.llm, "ask", fake(scope="answerable", sentences=[GOOD, BAD_QUOTE]))
    r = pipeline.answer("سؤال", verify=False)
    assert len(r["sentences"]) == 2 and not r["dropped"]
