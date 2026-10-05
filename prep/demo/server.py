"""Prep demo (2 Oct 2026, before the build window; disclose in STARTING_POINT.md).

A local test page for the step-3 pipeline on باب المياه:
  1. scope gate (separate Gemma call) -> out-of-scope questions get fixed draft wording, no generation
  2. BM25 retrieval over the 4 books' باب المياه passages (top 8)
  3. evidence-first answer from Gemma (JSON)
  4. quote check: drop sentences whose quote is not found verbatim (after normalising) in the cited passage;
     evidence status recomputed from what survives
No support judge yet: the page says so.

Run:  python3 prep/demo/server.py     then open http://127.0.0.1:8765
Standard library only. Needs Ollama running with gemma4:e4b-it-qat.
"""
import json
import pathlib
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "step2_extraction"))
sys.path.insert(0, str(HERE.parent / "step3_model_check"))
sys.path.insert(0, str(HERE.parent / "retrieval"))
import analyse as A  # noqa: E402
import run_check as R  # noqa: E402
import run_variants as V  # noqa: E402
import retrieval as RT  # noqa: E402  (hybrid: stemmed BM25 + BGE-M3, table of contents)

PORT = 8765
LOG = HERE / "questions_log.jsonl"  # question, timings, status; no personal data

# Draft wording from prep/templates/answer_policy.md ([مقترح], awaiting the specialist)
REFUSALS = {
    "other_madhhab": "مدارسة مخصصة لدراسة الروض المربع وشروحه في المذهب الحنبلي، ولا تشمل كتب المذاهب الأخرى. يُرجى الرجوع إلى كتب ذلك المذهب أو أهل العلم به.",
    "contemporary": "هذه مسألة معاصرة لم تتناولها الكتب المعتمدة في مدارسة. يُرجى الرجوع إلى جهات الفتوى المعتمدة.",
    "personal_fatwa": "لا تصدر مدارسة فتوى في الحالات الشخصية. يُرجى سؤال مفتٍ مؤهل.",
    "not_in_library": "لم أجد في الكتب المعتمدة في مدارسة نصًّا يجيب عن هذا السؤال، فلا أستطيع الجواب عنه. يُرجى سؤال أهل العلم المختصين.",
}
STATUS_AR = {"supported": "مؤيَّد بالنص", "partial": "مؤيَّد جزئيًّا: حُذف ما لم نجد له نصًّا",
             "differing": "أقوال مختلفة: عُرض كل قول منسوبًا إلى قائله دون ترجيح", "not_found": "لم يوجد نص"}

SCOPE_SCHEMA = {"type": "object", "properties": {"scope": R.SCHEMA["properties"]["scope"]}, "required": ["scope"]}
SCOPE_RULES = """صنّف سؤال طالب يدرس «الروض المربع» في الفقه الحنبلي (باب المياه) في scope:
answerable: سؤال عن مسائل الكتاب أو المذهب الحنبلي أو أقوال شراحه، ولو كان فيه نسبة خاطئة إلى المؤلف.
other_madhhab: يسأل عن مذهب غير الحنابلة.
contemporary: نازلة أو تقنية معاصرة.
personal_fatwa: يسأل عن حالته هو (فعلتُ كذا، هل يلزمني...).
not_in_library: موضوع لا علاقة له بالطهارة والمياه."""


RET = RT.Retriever()
PASSAGES = RET.passages
EXTRA_RULES = """
هـ. إن سأل الطالب عن أمرين (كالفرق بين شيئين) فاذكر كلًّا منهما من النصوص.
و. لا تكتب أرقام المقاطع داخل نص الجملة؛ ضعها في passage فقط."""
PMARK = re.compile(r"\s*[\[(]\s*P\d+\s*[\])]\s*")


def answer(question: str) -> dict:
    t0 = time.time()
    scope, st1 = R.ask(f"{SCOPE_RULES}\n\nالسؤال: {question}", SCOPE_SCHEMA)
    scope = scope.get("scope", "answerable")
    if scope != "answerable":
        return {"scope": scope, "status": "not_found", "status_ar": STATUS_AR["not_found"], "message": REFUSALS[scope],
                "sentences": [], "dropped": [], "passages": [], "seconds": round(time.time() - t0, 1)}
    shown = RET.search(question)
    ctx = "\n\n".join(f"[P{i}] {p['book']}، ج{p['vol']} ص{p['page']} ({'متن وشرح' if p['kind'] == 'text' else p['kind']}):\n{p['text']}"
                      for i, p in enumerate(shown, 1))
    ans, st2 = R.ask(f"{V.RULES_V2}{EXTRA_RULES}\n\nالنصوص:\n{ctx}\n\nالسؤال: {question}\n\nاكتب passage برقم المقطع مثل P3.", V.SCHEMA_V2)
    kept, dropped = [], []
    for s in ans.get("sentences", []) or []:
        digits = "".join(ch for ch in str(s.get("passage", "")) if ch.isdigit())
        p = shown[int(digits) - 1] if digits and 0 < int(digits) <= len(shown) else None
        q = A.normalise(s.get("quote", ""))
        ok = bool(p and q and q in p["norm"])
        (kept if ok else dropped).append({"text": PMARK.sub(" ", s.get("text", "")).strip(), "quote": s.get("quote", ""), "p": int(digits) if digits else None,
                                         "reason": None if ok else ("رقم المقطع غير صحيح" if not p else "الاقتباس غير موجود حرفيًّا في المقطع")})
    status = ans.get("status", "not_found")
    if not kept:
        status = "not_found"
    elif dropped and status == "supported":
        status = "partial"
    res = {"scope": scope, "premise_correct": ans.get("premise_correct"), "status": status, "status_ar": STATUS_AR.get(status, status),
           "sentences": kept, "dropped": dropped,
           "passages": [{"n": i, "book": p["book"], "vol": p["vol"], "page": p["page"], "kind": p["kind"], "text": p["text"],
                         "link": f"https://app.turath.io/book/{p['book_id']}?page={p['pg']}"} for i, p in enumerate(shown, 1)],
           "message": REFUSALS["not_in_library"] if not kept else None,
           "seconds": round(time.time() - t0, 1), "tokens": (st1.get("output_tokens") or 0) + (st2.get("output_tokens") or 0)}
    return res


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (HERE / "index.html").read_text(encoding="utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/ask":
            return self._send(404, "not found", "text/plain")
        try:
            q = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}").get("question", "").strip()[:500]
            if not q:
                return self._send(400, json.dumps({"error": "اكتب سؤالًا"}, ensure_ascii=False), "application/json")
            res = answer(q)
            with LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "question": q, "scope": res["scope"], "status": res["status"],
                                    "kept": len(res["sentences"]), "dropped": len(res["dropped"]), "seconds": res["seconds"]}, ensure_ascii=False) + "\n")
            self._send(200, json.dumps(res, ensure_ascii=False), "application/json; charset=utf-8")
        except Exception as e:  # show the error on the page instead of hanging
            self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False), "application/json; charset=utf-8")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"{len(PASSAGES)} passages. Open http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
