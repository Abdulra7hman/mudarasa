"""Arabic text helpers.

Adapted from prep/step2_extraction/analyse.py (normalise, split_notes, strip_markup), plus:
  join_continuations: a footnote that runs onto the next page (key 0 there, often marked «=») is joined to its start
  speakable: text prepared for text-to-speech (honorific ligatures spelled out, footnote markers dropped)
"""
import html
import re

TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # harakat, Quranic marks, tatweel
FN_SEP = re.compile(r"\n_{5,}\n")
MARK = r"\(([٠-٩0-9]+)\)"  # footnote marker such as (١)
MARK_RE = re.compile(MARK)
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
TITLE_RE = re.compile(r"<span[^>]*data-type=\"?title\"?[^>]*>(.*?)</span>", re.S)


def normalise(s: str) -> str:
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = TASHKEEL.sub("", s)
    s = re.sub("[إأآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[^ء-ي0-9٠-٩ ]", " ", s)  # keep letters, digits, spaces
    return re.sub(r"\s+", " ", s).strip()


def strip_tashkeel(s: str) -> str:
    return TASHKEEL.sub("", s)


def split_page(text: str):
    """Page text -> (body, notes); notes are below a line of underscores."""
    parts = FN_SEP.split(text, maxsplit=1)
    return html.unescape(parts[0]), html.unescape(parts[1] if len(parts) > 1 else "")


def split_notes(notes: str):
    """'(١) text\n(٢) text' -> {1: text, 2: text}; text continuing from the previous page gets key 0."""
    out, cur = {}, 0
    for line in notes.split("\n"):
        m = re.match(r"\s*" + MARK + r"\s*(.*)", line)
        if m:
            cur = int(m.group(1).translate(AR_DIGITS))
            out[cur] = m.group(2)
        elif line.strip():
            out[cur] = (out.get(cur, "") + " " + line).strip()
    return out


def join_continuations(notes_by_pg: dict) -> dict:
    """notes_by_pg {pg: {n: text}} in page order. A key-0 note continues the last note of the previous page."""
    pgs = sorted(notes_by_pg)
    for prev, pg in zip(pgs, pgs[1:]):
        cont = notes_by_pg[pg].pop(0, None)
        if cont and notes_by_pg[prev]:
            last = max(notes_by_pg[prev])
            head = notes_by_pg[prev][last].rstrip(" =")
            notes_by_pg[prev][last] = head + " " + cont.lstrip(" =")
    return notes_by_pg


def strip_markup(s: str) -> str:
    s = TITLE_RE.sub(" ", s)
    return re.sub(r"<[^>]+>", " ", s)


LIGATURES = {"ﷺ": "صلى الله عليه وسلم", "﵇": "عليه السلام", "﵀": "رحمه الله", "﵁": "رضي الله عنه",
             "﵂": "رضي الله عنها", "﵃": "رضي الله عنهم", "﵄": "رضي الله عنهما", "﷿": "عز وجل", "ﷻ": "جل جلاله"}


def expand_ligatures(s: str) -> str:
    for k, v in LIGATURES.items():
        s = s.replace(k, " " + v + " ")
    return re.sub(r"[ \t]+", " ", s)


def speakable(s: str) -> str:
    """Text for TTS: ligatures spelled out; footnote markers, manuscript sigla and brackets removed."""
    s = strip_markup(s)
    s = expand_ligatures(s)
    s = MARK_RE.sub(" ", s)
    s = re.sub(r"\[\s*[أابج]\s*\]", " ", s)  # manuscript sigla such as [أ]
    s = re.sub(r"[«»\"\[\]{}﴿﴾()*_=]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
