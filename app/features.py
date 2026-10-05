"""Backend of the additions (each behind a FEATURE_* flag, labelled experimental in the UI).

  takhrij     hadith/verse referencing for a paragraph: library notes (Rakaiz editors, Ibn Qasim) shown verbatim,
              grading phrases highlighted and attributed; a link out to Dorar's search (no Dorar data is fetched)
  word        meaning of a tapped word, from glosses in the library (Ibn Qasim's notes, «أي …», «لغة …»), cited
  matn        the Zad matn of a chapter in lines, vocalized from the Rakaiz edition where the editions agree (memorization)
  speech      short-lived Azure Speech token for the browser (the key never leaves the server)
  audio       manifest of pre-generated recordings with word timings (scripts/build_tts.py)
  tools       pre-generated study tools per section (scripts/build_tools.py)
"""
import json
import re
import time
import urllib.parse

import requests
from fastapi import HTTPException

from . import books as B
from . import config as C
from .retrieval import stem
from .textnorm import normalise, strip_tashkeel

TAKHRIJ_RE = re.compile(r"(أخرجه|اخرجه|رواه|خرَّجه|خرجه|صحح|حسن|ضعف|إسناد|اسناد|الحديث|البخاري|مسلم|أبو داود|ابو داود|الترمذي|النسائي|ابن ماجه|الدارقطني|البيهقي|الحاكم|مسند|سنن|موطأ)")
VARIANT_RE = re.compile(r"(في \(\s*[أابجده]\s*\)|في \[\s*[أابجده]\s*\]|في نسخة|في النسخ|سقط|ساقطة|في المطبوع|في الأصل|زيادة من)")
HADITH_RE = re.compile(r"(رواه|أخرجه|اخرجه|حديث|الحديث|مرفوعا|موقوفا|عن النبي)")
GRADE_RE = re.compile(r"((?:و)?(?:صحَّحه|صححه|حسَّنه|حسنه|ضعَّفه|ضعفه|جوَّد إسناده|جود إسناده|قوَّاه|قواه)(?:\s+[^\s،.؛]+){0,3}"
                      r"|إسناده (?:صحيح|حسن|ضعيف|جيد)|حديث (?:صحيح|حسن|ضعيف|منكر)|(?:لا يصح|لا يثبت|منكر|موضوع|مرسل|منقطع))")


def note_kind(text):
    t = strip_tashkeel(text)
    if VARIANT_RE.search(t) and not re.search(r"(أخرجه|رواه)", t):
        return "variant"
    if TAKHRIJ_RE.search(t):
        return "takhrij"
    return "note"


def dorar_link(words):
    q = " ".join(normalise(words).split()[-8:])
    return "https://dorar.net/hadith/search?q=" + urllib.parse.quote(q)


def takhrij_for(p):
    out = []
    for n in p["rakaiz_notes"]:
        k = note_kind(n["text"])
        if k == "note":
            continue
        out.append({"source": "محققو الروض المربع (ط ركائز)", "kind": k, "text": n["text"], "vol": n["vol"], "page": n["page"],
                    "link": n["link"], "grades": [g.group(0) for g in GRADE_RE.finditer(strip_tashkeel(n["text"]))],
                    "lemma": n.get("lemma", ""), "dorar": dorar_link(n.get("lemma", "")) if k == "takhrij" else None})
    for n in p["iq"]:  # Ibn Qasim also «صحح» opinions; count his note only when it is about a hadith
        if note_kind(n["text"]) != "takhrij" or not HADITH_RE.search(strip_tashkeel(n["text"])):
            continue
        out.append({"source": "حاشية ابن قاسم", "kind": "takhrij", "text": n["text"], "vol": n["vol"], "page": n["page"],
                    "link": n["link"], "grades": [g.group(0) for g in GRADE_RE.finditer(strip_tashkeel(n["text"]))],
                    "lemma": n["lemma"], "dorar": dorar_link(n["lemma"])})
    return out


# ---------- word meaning ----------
AR = "\u0621-\u064A\u064B-\u0652"
GLOSS_RE = re.compile(rf"([{AR}]{{3,}})\s*[:،]?\s*(?:\)\s*)?(أي|أَي|أَيْ)\s*[:،]?\s*([^.؛:(\n]{{3,90}})")
DEF_RES = [  # (pattern, label): group 1 = the word before, last group = the definition
    (re.compile(rf"([{AR}]{{2,}})\s*\)?\s*[:،]?\s*(?:في اللغة|لغة|لغةً|لُغَةً)\s*[:،]?\s*([^.؛(\n]{{3,120}})"), "لغةً: ", "lugha"),
    (re.compile(rf"([{AR}]{{2,}})\s*\)?\s*[:،]?\s*(?:في الاصطلاح|اصطلاحا|اصطلاحًا|في الشرع|شرعا|شرعًا)\s*[:،]?\s*([^.؛(\n]{{3,140}})"), "اصطلاحًا: ", "istilah"),
    (re.compile(rf"([{AR}]{{3,}})\s*:\s*(?:هو|هي)\s+([^.؛(\n]{{3,120}})"), "", "def"),
]
# «ومعناه لغة: …» defines the term being explained, not the word «معناه»
PRONOUNS = {normalise(w) for w in "معناه معناها ومعناه ومعناها وهو وهي هو هي وهذا هذا وذلك ذلك وهما هما وهم وحقيقته وحقيقتها".split()}
STOP = {normalise(w) for w in """و ما وما في من على الى إلى عن أن إن لا لم لن قد ثم أو او بل هو هي هذا هذه ذلك تلك التي الذي الذين كان كانت يكون تكون
    لأن لأنه لأنها لانه لانها إذا اذا إذ حتى كل بعض غير مع عند بين فيه فيها منه منها عليه عليها به بها له لها كما مما ممن وهو وهي
    ولا ولم وقد فإن فان وإن وان ولو لو أي يعني نحو مثل كذا وكذا أيضا ايضا إلا الا سواء كذلك فلا فلم وكان""".split()}
KIND_RANK = {"lugha": 0, "istilah": 1, "def": 2, "gloss_rawd": 3, "note": 4, "gloss": 5}


def content_words(text, limit=3):
    ws = [w for w in normalise(text).split() if len(w) >= 3 and w not in STOP]
    return ws if 0 < len(ws) <= limit else []


def build_glossary(study):
    entries = []

    def add(word, definition, src, ref, para, kind, context=()):
        n = normalise(word)
        words = list(context) if (not n or n in PRONOUNS or n in STOP) else [n.split()[-1]]
        for w in words:
            key = stem(w)
            if len(key) < 2 or len(normalise(definition)) < 3:
                continue
            entries.append({"key": key, "word": strip_tashkeel(w), "definition": definition.strip(" ،:"), "source": src,
                            "vol": ref["vol"], "page": ref["page"], "link": ref["link"], "para": para, "kind": kind})

    def scan(text, src, ref, para, context):
        for rx, label, kind in DEF_RES:
            for m in rx.finditer(text):
                add(m.group(1), label + m.group(m.lastindex), src, ref, para, kind, context)
        for m in GLOSS_RE.finditer(text):
            add(m.group(1), "أي " + m.group(3), src, ref, para, "gloss_rawd" if src == "الروض المربع" else "gloss", context)

    for ch in study["chapters"]:  # «باب الآنية: هي الأوعية…»: the chapter's opening sentence defines its title
        p = study["paras"][ch["paras"][0]] if ch["paras"] else None
        m = p and re.match(r"\s*(?:هي|هو)\s+([^.؛(\n]{3,120})", p["text"])
        if m:
            add(ch["title"].split()[-1], m.group(1), "الروض المربع", p, p["id"], "def")

    for u in study["units"].values():  # the Rawd, unit by unit: the matn term is the context of its sharh
        p = study["paras"][u["para"]]
        scan(u["text"], "الروض المربع", p, u["para"], content_words(u["matn"]))
    for pid, p in study["paras"].items():
        for n in p["iq"]:  # Ibn Qasim's note sits right after the word it explains
            if n["lemma"] and n["method"] != "title" and re.match(r"\s*(أي|يعني|بفتح|بضم|بكسر|بتثليث|جمع|مصدر|اسم)", n["text"]):
                add(n["lemma"].split()[-1], n["text"][:300], "حاشية ابن قاسم", n, pid, "note")
            scan(n["text"], "حاشية ابن قاسم", n, pid, content_words(n["lemma"].split()[-1] if n["lemma"] else ""))
        for s in p["mumti"]:
            heading = re.sub(r"[«»\"]|^قوله\s*:?", " ", s["heading"])
            for ln in s["lines"]:
                scan(ln["text"], "الشرح الممتع", ln, pid, content_words(heading))
    return entries


class Glossary:
    def __init__(self, study):
        self.entries = build_glossary(study)
        self.chapter = {pid: p["chapter"] for pid, p in study["paras"].items()}

    def lookup(self, word, para=None, k=4):
        n = normalise(word)
        if not n or n in STOP:
            return []
        key = stem(n.split()[-1])
        hits = [e for e in self.entries if e["key"] == key or e["key"] == n]
        ch = self.chapter.get(para)
        hits.sort(key=lambda e: (KIND_RANK.get(e["kind"], 9), e["para"] != para, self.chapter.get(e["para"]) != ch))
        seen, out = set(), []
        for e in hits:
            sig = normalise(e["definition"])[:60]
            if sig not in seen:
                seen.add(sig)
                out.append(e)
        return out[:k]


# ---------- matn lines for memorization ----------
def matn_lines(study, cid, min_words=6, max_words=14):
    ch = next(c for c in study["chapters"] if c["id"] == cid)
    words, src = [], []
    for pid in ch["paras"]:
        for uid in study["paras"][pid]["units"]:
            u = study["units"][uid]
            if not u["matn"] or u["para"] != pid:
                continue
            plain = u["matn"].split()
            voc = (u.get("rakaiz_matn") or "").split()
            use_voc = voc and [normalise(w) for w in voc] == [normalise(w) for w in plain]
            for i, w in enumerate(plain):
                words.append({"w": voc[i] if use_voc else w, "plain": strip_tashkeel(w), "unit": uid, "page": study["paras"][pid]["page"]})
            if words:
                words[-1]["end"] = True  # segment boundary: a natural place to break a line
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if (w.get("end") and len(cur) >= min_words) or len(cur) >= max_words:
            lines.append(cur)
            cur = []
    if cur:
        if lines and len(cur) < min_words // 2:
            lines[-1] += cur
        else:
            lines.append(cur)
    return [{"n": i + 1, "words": [{k: w[k] for k in ("w", "plain")} for w in ln], "page": ln[0]["page"], "unit": ln[0]["unit"]}
            for i, ln in enumerate(lines)]


# ---------- routes ----------
_token = {"t": 0, "v": None}


def register(app, study):
    gl = Glossary(study) if C.FEATURES["word"] else None
    tools_dir = B.DATA / "tools"
    audio_dir = B.DATA / "audio"

    @app.get("/api/takhrij/{pid}")
    def takhrij(pid: str):
        if not C.FEATURES["takhrij"] or pid not in study["paras"]:
            raise HTTPException(404, "not found")
        return {"para": pid, "items": takhrij_for(study["paras"][pid])}

    @app.get("/api/word")
    def word(w: str, para: str = None):
        if not gl:
            raise HTTPException(404, "not found")
        return {"word": w, "stop": normalise(w) in STOP, "items": gl.lookup(w[:40], para)}

    @app.get("/api/matn/{cid}")
    def matn(cid: str):
        if not C.FEATURES["recite"]:
            raise HTTPException(404, "not found")
        return {"chapter": cid, "lines": matn_lines(study, cid)}

    @app.get("/api/speech/token")
    def speech_token():
        if not (C.SPEECH_KEY and C.SPEECH_REGION):
            return {"available": False}
        if time.time() - _token["t"] > 480:
            r = requests.post(f"https://{C.SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
                              headers={"Ocp-Apim-Subscription-Key": C.SPEECH_KEY}, timeout=10)
            r.raise_for_status()
            _token.update(t=time.time(), v=r.text)
        return {"available": True, "token": _token["v"], "region": C.SPEECH_REGION}

    @app.get("/api/audio/{cid}")
    def audio(cid: str):
        f = audio_dir / f"manifest_{cid}.json"
        if not C.FEATURES["audio"]:
            raise HTTPException(404, "not found")
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"chapter": cid, "clips": []}

    @app.get("/api/listen/{cid}")
    def listen(cid: str):
        """Reading order for the listen view: Rakaiz (vocalized) paragraphs, each with the Ibn Qasim notes of its anchor paragraph."""
        out, seen = [], set()
        for r in study["rakaiz_paras"]:
            if r["chapter"] != cid:
                continue
            notes = []
            for ap in [a for a in r["anchor_paras"] if a not in seen][:1]:  # each anchor paragraph's notes once
                seen.add(ap)
                notes = [{"id": n["id"], "n": n["n"], "text": n["text"], "vol": n["vol"], "page": n["page"], "link": n["link"],
                          "lemma": n["lemma"]} for n in study["paras"][ap]["iq"]]
            out.append({"id": r["id"], "text": r["text"], "heading": r["heading"], "vol": r["vol"], "page": r["page"], "link": r["link"],
                        "anchor_paras": r["anchor_paras"], "notes": notes})
        return {"chapter": cid, "paras": out}

    @app.get("/api/tools/{cid}")
    def tools(cid: str):
        f = tools_dir / f"{cid}.json"
        if not C.FEATURES["study_tools"]:
            raise HTTPException(404, "not found")
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"chapter": cid, "sections": []}

    if audio_dir.exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")
