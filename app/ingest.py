"""Offline ingestion of the deep chapters (باب المياه، باب الآنية، باب الاستنجاء).

Builds the anchor's study paragraphs (al-Rawd, 1679) and links every commentary to them:
  Ibn Qasim (12216)  footnotes, by the words before each marker (text method) and by matn order (structure method)
  al-Mumti' (10649)  sections, by their lemma headings that quote the matn
  Rakaiz (147658)    the vocalized edition of the Rawd: units aligned by matn order; its footnotes (takhrij, variants)

Adapted from prep/step2_extraction/analyse.py (units, locate, q3, q4, q5), with one fix: a footnote marker is resolved
on the page where the marker itself appears. The prep code used the page where the marker's unit started, and units
cross pages, so many notes got another note's text (tests/test_linking.py).

Run:  python -m app.ingest      ->  data/build/study.json, data/build/stats.json
"""
import difflib
import html
import json
import re
from collections import Counter

from . import books as B
from .textnorm import (AR_DIGITS, TITLE_RE, join_continuations, normalise, split_notes, split_page, strip_markup)

OUT = B.DATA / "build"
CHAPTERS = [("water", "باب المياه"), ("vessels", "باب الآنية"), ("istinja", "باب الاستنجاء")]
CHAPTER_TITLE = dict(CHAPTERS)
# internal page ranges, from each book's heading index: كتاب الطهارة up to the page where باب السواك starts
RANGES = {1679: (6, 22), 147658: (65, 102), 12216: (53, 146), 10649: (21, 140)}
PAREN_RE = re.compile(r"\(([^()]*)\)")
DIGITS_RE = re.compile(r"[٠-٩0-9]+")


def chapter_of_title(title: str):
    n = normalise(title)
    if "كتاب الطهاره" in n or "باب المياه" in n:
        return "water"
    if "باب الانيه" in n:
        return "vessels"
    if "باب الاستنجاء" in n:
        return "istinja"
    if "باب السواك" in n:
        return "END"
    return None


def events(bid: int):
    """Reading-order events inside the deep chapters: ("title"|"line", text, pg, chapter); plus {pg: {n: note}}."""
    lo, hi = RANGES[bid]
    raw, notes_by_pg = [], {}
    for pg in range(lo, hi + 1):
        body, notes = split_page(B.page(bid, pg)["text"])
        notes_by_pg[pg] = split_notes(notes)
        for line in body.split("\n"):
            pos = 0
            for m in TITLE_RE.finditer(line):
                if line[pos:m.start()].strip():
                    raw.append(("line", line[pos:m.start()], pg))
                raw.append(("title", html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip(), pg))
                pos = m.end()
            if line[pos:].strip():
                raw.append(("line", line[pos:], pg))
    join_continuations(notes_by_pg)
    out, ch = [], None
    for kind, text, pg in raw:
        if kind == "title":
            c = chapter_of_title(text)
            if c == "END":
                break
            if c:
                ch = c
        if ch:
            out.append((kind, text, pg, ch))
    return out, notes_by_pg


def protect_quran(s: str) -> str:
    return re.sub(r"﴿.*?﴾", lambda m: m.group(0).replace("(", "[").replace(")", "]"), s, flags=re.S)


def walk(bid: int):
    """Split a book's deep chapters into paragraphs (lines), units (a ( matn ) segment plus the text after it)
    and footnote markers, each marker resolved on its own page."""
    evs, notes_by_pg = events(bid)
    paras, units, markers = [], [], []
    cur, since, title, ch_prev, heading = None, "", None, None, None
    for kind, text, pg, ch in evs:
        if ch != ch_prev:  # units never cross chapters
            cur, since, ch_prev = None, "", ch
        if kind == "title":
            title, since = text.strip("[]() "), ""
            heading = title
            continue
        body = protect_quran(strip_markup(text))
        if len(normalise(body)) <= 15 and not DIGITS_RE.search(body):
            heading = (heading + " " if heading else "") + body.strip()
            continue
        pid = f"{bid}p{len(paras) + 1}"
        para = {"id": pid, "chapter": ch, "pg": pg, "text": body.strip(), "heading": heading, "units": []}
        heading = None
        paras.append(para)
        pos = 0
        for m in PAREN_RE.finditer(body):
            inner = m.group(1).strip()
            seg = body[pos:m.start()]
            if seg.strip() and cur is None:  # text before the first matn of a chapter
                cur = {"id": f"{bid}u{len(units) + 1}", "chapter": ch, "para": pid, "pg": pg, "matn": "", "text": ""}
                units.append(cur)
            if cur is not None:
                cur["text"] += seg
                if seg.strip() and cur["id"] not in para["units"]:
                    para["units"].append(cur["id"])
            since += seg
            if seg.strip():
                title = None
            if DIGITS_RE.fullmatch(inner):  # footnote marker, resolved on THIS page
                n = int(inner.translate(AR_DIGITS))
                lemma = normalise(since).split()[-12:]
                how = "text"
                if not lemma and title:
                    lemma, how = normalise(title).split(), "title"
                elif not lemma and cur is not None:
                    lemma = normalise(cur["matn"]).split()[-12:]
                markers.append({"pg": pg, "n": n, "note": notes_by_pg.get(pg, {}).get(n, ""), "lemma": " ".join(lemma),
                                "how": how, "unit": len(units) - 1 if cur is not None else None, "para": pid, "chapter": ch,
                                "unit_pg": cur["pg"] if cur is not None else pg})
                since = ""
                if cur is not None:
                    cur["text"] += m.group(0)
            else:  # matn segment: a new unit
                cur = {"id": f"{bid}u{len(units) + 1}", "chapter": ch, "para": pid, "pg": pg, "matn": inner, "text": m.group(0)}
                units.append(cur)
                para["units"].append(cur["id"])
                since, title = m.group(0), None
            pos = m.end()
        tail = body[pos:]
        if tail.strip() and cur is None:
            cur = {"id": f"{bid}u{len(units) + 1}", "chapter": ch, "para": pid, "pg": pg, "matn": "", "text": ""}
            units.append(cur)
        if cur is not None:
            cur["text"] += tail + "\n"
            if tail.strip() and cur["id"] not in para["units"]:
                para["units"].append(cur["id"])
        since += tail + "\n"
        if tail.strip():
            title = None
    for u in units:
        u["norm"], u["matn_norm"] = normalise(u["text"]), normalise(u["matn"])
    return paras, units, markers, notes_by_pg


# ---------- matching ----------
def word_cover(lemma_words, target_words):
    if not lemma_words:
        return 0.0
    sm = difflib.SequenceMatcher(None, lemma_words, target_words, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / len(lemma_words)


class Finder:
    """Find a lemma in the anchor's units (exact, exact across neighbouring units, or fuzzy by word coverage)."""

    def __init__(self, units, field="norm", window=3):
        self.units, self.field, self.window = units, field, window
        self.joined = [" ".join(units[k][field] for k in range(i, min(i + window, len(units)))) for i in range(len(units))]

    def end_unit(self, i, lemma):
        """For a match starting in unit i (joined window), the unit where the lemma ends (= where the marker sits)."""
        s = self.joined[i].find(lemma)
        end, acc = s + len(lemma), 0
        for k in range(i, min(i + self.window, len(self.units))):
            acc += len(self.units[k][self.field]) + 1
            if end <= acc:
                return k
        return i

    def find(self, lemma, chapter, min_cover=0.75, use_end=True):
        words = lemma.split()
        if len(words) < 2:
            return [], "too_short", 0.0
        ok = [i for i, u in enumerate(self.units) if u["chapter"] == chapter]
        hits = [i for i in ok if lemma in self.units[i][self.field]]
        if hits:
            return hits, "exact", 1.0
        hits = [i for i in ok if lemma in self.joined[i]]
        if hits:
            return ([self.end_unit(i, lemma) for i in hits] if use_end else hits), "exact_span", 1.0
        best_i, best = None, 0.0
        for i in ok:
            c = word_cover(words, self.joined[i].split())
            if c > best:
                best_i, best = i, c
        if best >= min_cover:
            return [best_i], "fuzzy", round(best, 3)
        return [], "none", round(best, 3)


def align(a_units, b_units):
    """Map b unit index -> a unit index by matn order (equal runs, and same-length replaced runs)."""
    sm = difflib.SequenceMatcher(None, [u["matn_norm"] for u in b_units], [u["matn_norm"] for u in a_units], autojunk=False)
    out = {}
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == "equal" or (t == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                if b_units[i1 + k]["chapter"] == a_units[j1 + k]["chapter"]:
                    out[i1 + k] = j1 + k
    return out


def pick(hits, near):
    """Several exact hits: take the one nearest the structural guess, else the first."""
    if not hits:
        return None
    if near is None:
        return hits[0]
    return min(hits, key=lambda i: abs(i - near))


def first_unit(units, chapter):
    return next(i for i, u in enumerate(units) if u["chapter"] == chapter)


def link_markers(markers, src_units, anchor, finder, struct):
    """Attach each footnote marker of a commentary to an anchor unit (text method first, structure as fallback)."""
    rows = []
    for k, m in enumerate(markers):
        sidx = struct.get(m["unit"]) if m["unit"] is not None else None
        if m["how"] == "title":
            idx, how, score, amb = first_unit(anchor, m["chapter"]), "title", 1.0, False
        else:
            hits, how, score = finder.find(m["lemma"], m["chapter"])
            idx, amb = pick(hits, sidx), len(hits) > 1
            if idx is None and sidx is not None:
                idx, how = sidx, "struct"
        rows.append({**m, "anchor_unit": None if idx is None else anchor[idx]["id"], "method": how, "score": score,
                     "ambiguous": amb, "struct_unit": None if sidx is None else anchor[sidx]["id"],
                     "agree": None if idx is None or sidx is None or how == "struct" else abs(idx - sidx) <= 1})
    return rows


# ---------- build ----------
def ref(bid, pg):
    p = B.page(bid, pg)
    return {"vol": p["vol"], "page": p["page"], "pg": pg, "link": B.turath_link(bid, pg)}


def build():
    a_paras, anchor, _, _ = walk(1679)
    a_index = {u["id"]: i for i, u in enumerate(anchor)}
    finder = Finder(anchor)

    # Ibn Qasim
    _, iq_units, iq_markers, _ = walk(12216)
    iq_rows = link_markers(iq_markers, iq_units, anchor, finder, align(anchor, iq_units))

    # Rakaiz: the same book in another edition, vocalized; its notes carry the hadith referencing
    r_paras, r_units, r_markers, _ = walk(147658)
    r_struct = align(anchor, r_units)
    r_rows = []
    for m in r_markers:
        k = m["unit"]
        while k is not None and k >= 0 and k not in r_struct:  # nearest previous aligned unit
            k -= 1
        r_rows.append({**m, "anchor_unit": anchor[r_struct[k]]["id"] if k is not None and k >= 0 else None, "method": "edition_align"})
    for j, i in r_struct.items():  # word differences between the editions, per aligned unit
        wa, wb = anchor[i]["norm"].split(), r_units[j]["norm"].split()
        ops = [(t, " ".join(wa[a1:a2]), " ".join(wb[b1:b2])) for t, a1, a2, b1, b2 in
               difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes() if t != "equal"]
        ops = [o for o in ops if not re.fullmatch(r"[٠-٩0-9 ]*", o[1] + o[2])]
        anchor[i]["rakaiz_unit"] = r_units[j]["id"]
        anchor[i]["edition_diffs"] = ops[:12]
    for p in r_paras:  # Rakaiz paragraph -> anchor paragraphs
        targets = []
        for uid in p["units"]:
            j = int(uid.split("u")[1]) - 1
            if j in r_struct:
                ap = anchor[r_struct[j]]["para"]
                if ap not in targets:
                    targets.append(ap)
        p["anchor_paras"] = targets

    # al-Mumti': sections under lemma headings
    m_evs, _ = events(10649)
    sections, cur = [], None
    for kind, text, pg, ch in m_evs:
        if kind == "title":
            cur = {"id": f"m{len(sections) + 1}", "chapter": ch, "heading": text.strip("[] "), "is_chapter": bool(chapter_of_title(text)),
                   "lines": []}
            sections.append(cur)
            continue
        if cur is None:
            continue
        t = strip_markup(text).strip()
        if t:
            cur["lines"].append({"pg": pg, "text": t})
    m_finder = Finder(anchor, field="matn_norm", window=8)
    last = {}
    for s in sections:
        if s["is_chapter"]:
            idx, how, score = first_unit(anchor, s["chapter"]), "title", 1.0
        else:
            lemma = normalise(re.sub(r"[.…]{2,}", " ", s["heading"]))
            hits, how, score = m_finder.find(lemma, s["chapter"], use_end=False)
            after = [h for h in hits if h >= last.get(s["chapter"], -1)]
            idx = (after or hits or [None])[0]
            if idx is None and s["chapter"] in last:  # unlinked heading: keep reading order, low confidence
                idx, how = last[s["chapter"]], "order"
        s.update(anchor_unit=None if idx is None else anchor[idx]["id"], method=how, score=score)
        if idx is not None:
            last[s["chapter"]] = idx

    # ---------- output ----------
    def unit_para(uid):
        return anchor[a_index[uid]]["para"] if uid else None

    paras_out = {}
    for p in a_paras:
        paras_out[p["id"]] = {**p, **ref(1679, p["pg"]), "iq": [], "mumti": [], "rakaiz_notes": [], "rakaiz_paras": []}
    for k, r in enumerate(iq_rows):
        pid = unit_para(r["anchor_unit"])
        note = {"id": f"iq{k + 1}", "n": r["n"], "text": r["note"], "lemma": r["lemma"], **ref(12216, r["pg"]),
                "unit": r["anchor_unit"], "para": pid, "method": r["method"], "agree": r["agree"], "ambiguous": r["ambiguous"]}
        r["id"] = note["id"]
        if pid:
            paras_out[pid]["iq"].append(note)
    for k, r in enumerate(r_rows):
        pid = unit_para(r["anchor_unit"])
        if pid:
            paras_out[pid]["rakaiz_notes"].append({"id": f"rk{k + 1}", "n": r["n"], "text": r["note"], **ref(147658, r["pg"]),
                                                   "unit": r["anchor_unit"]})
    for p in r_paras:
        if p["anchor_paras"]:
            paras_out[p["anchor_paras"][0]]["rakaiz_paras"].append({"id": p["id"], "text": p["text"], **ref(147658, p["pg"])})
    for s in sections:
        pid = unit_para(s["anchor_unit"])
        s["para"] = pid
        s["lines"] = [{**l, **ref(10649, l["pg"])} for l in s["lines"]]
        if pid:
            paras_out[pid]["mumti"].append({**{k: s[k] for k in ("id", "heading", "method", "score", "lines")}, "unit": s["anchor_unit"]})

    units_out = {u["id"]: {k: u[k] for k in ("id", "chapter", "para", "pg", "matn", "text")} | {
        "rakaiz_unit": u.get("rakaiz_unit"), "edition_diffs": u.get("edition_diffs", [])} for u in anchor}
    rakaiz_out = [{"id": p["id"], "chapter": p["chapter"], "text": p["text"], "heading": p["heading"],
                   "anchor_paras": p["anchor_paras"], **ref(147658, p["pg"])} for p in r_paras]
    chapters = [{"id": cid, "title": title, "paras": [p["id"] for p in a_paras if p["chapter"] == cid]} for cid, title in CHAPTERS]
    study = {"chapters": chapters, "paras": paras_out, "units": units_out, "rakaiz_paras": rakaiz_out}

    stats = {}
    for cid, _ in CHAPTERS:
        iq = [r for r in iq_rows if r["chapter"] == cid]
        both = [r for r in iq if r["agree"] is not None]
        ms = [s for s in sections if s["chapter"] == cid and not s["is_chapter"]]
        stats[cid] = {
            "anchor_paragraphs": sum(p["chapter"] == cid for p in a_paras),
            "anchor_units": sum(u["chapter"] == cid for u in anchor),
            "iq_notes": len(iq), "iq_linked": sum(r["anchor_unit"] is not None for r in iq),
            "iq_by_method": dict(Counter(r["method"] for r in iq)),
            "iq_both_methods": len(both), "iq_methods_agree": sum(bool(r["agree"]) for r in both),
            "iq_marker_page_differs_from_unit_start": sum(r["pg"] != r["unit_pg"] for r in iq),
            "iq_empty_note_text": sum(not r["note"] for r in iq),
            "mumti_headings": len(ms), "mumti_linked": sum(s["anchor_unit"] is not None for s in ms),
            "mumti_by_method": dict(Counter(s["method"] for s in ms)),
            "rakaiz_units": sum(u["chapter"] == cid for u in r_units),
            "rakaiz_units_aligned": sum(1 for j in r_struct if r_units[j]["chapter"] == cid),
            "rakaiz_notes": sum(r["chapter"] == cid for r in r_rows),
            "anchor_units_with_edition_diffs": sum(1 for u in anchor if u["chapter"] == cid and u.get("edition_diffs")),
        }
    return study, stats, iq_rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    study, stats, iq_rows = build()
    (OUT / "study.json").write_text(json.dumps(study, ensure_ascii=False), encoding="utf-8")
    (OUT / "iq_links.json").write_text(json.dumps(iq_rows, ensure_ascii=False), encoding="utf-8")
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
