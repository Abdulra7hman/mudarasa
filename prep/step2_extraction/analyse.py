"""Throwaway (prep, 1 Oct): extraction and linking test on باب المياه.

Questions answered (results -> results/*.json, summary printed):
  Q1 printed page: does every page carry vol + printed page, consistent with the book's page_map?
  Q2 matn vs sharh: can the Zad matn be separated from al-Bahuti's sharh by the ( ... ) convention?
  Q3 Ibn Qasim (12216): can each footnote be anchored to a Rawd paragraph via its inline marker?
  Q4 Sharh al-Mumti' (10649): can each section be linked to a Rawd paragraph via its lemma heading?
  Q5 editions: can the two Rawd editions (1679, 147658) be aligned paragraph by paragraph, and their differences shown?
"""
import difflib
import html
import json
import pathlib
import re
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
OUT = pathlib.Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

# ---------- Arabic normalisation ----------
TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # harakat, Quranic marks, tatweel


def normalise(s: str) -> str:
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = TASHKEEL.sub("", s)
    s = re.sub("[إأآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[^ء-ي0-9٠-٩ ]", " ", s)  # keep letters, digits, spaces
    return re.sub(r"\s+", " ", s).strip()


# ---------- page parsing ----------
FN_SEP = re.compile(r"\n_{5,}\n")
MARK = r"\(([٠-٩0-9]+)\)"  # footnote marker such as (١)
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def load_pages(bid):
    pages = []
    for f in sorted((BOOKS / str(bid) / "pages").glob("*.json"), key=lambda p: int(p.stem)):
        d = json.loads(f.read_text(encoding="utf-8"), strict=False)
        meta = json.loads(d["meta"], strict=False) if isinstance(d["meta"], str) else d["meta"]
        parts = FN_SEP.split(d["text"], maxsplit=1)
        body, notes = parts[0], (parts[1] if len(parts) > 1 else "")
        pages.append({"pg": int(f.stem), "meta": meta, "body": html.unescape(body), "notes": html.unescape(notes)})
    return pages


def split_notes(notes: str):
    """'(١) text\n(٢) text' -> {1: text, 2: text}; notes continuing from the previous page have key 0."""
    out, cur = {}, 0
    for line in notes.split("\n"):
        m = re.match(r"\s*" + MARK + r"\s*(.*)", line)
        if m:
            cur = int(m.group(1).translate(AR_DIGITS))
            out[cur] = m.group(2)
        else:
            out[cur] = (out.get(cur, "") + " " + line).strip()
    return out


def strip_markup(s):
    s = re.sub(r"<span[^>]*data-type=\"?title\"?[^>]*>.*?</span>", " ", s)
    return re.sub(r"<[^>]+>", " ", s)


def paragraphs(pages):
    """Body lines as study paragraphs, keyed by (internal page, line index)."""
    out = []
    for p in pages:
        for i, line in enumerate(strip_markup(p["body"]).split("\n")):
            if len(normalise(line)) > 15:
                out.append({"pg": p["pg"], "vol": p["meta"]["vol"], "page": p["meta"]["page"], "i": i, "text": line.strip()})
    return out


def matn_segments(text):
    """Text inside ( ... ) excluding footnote markers like (١) and Quran ﴿...﴾."""
    text = re.sub(r"﴿.*?﴾", " ", text)
    return [m.group(1).strip() for m in re.finditer(r"\(([^()]*)\)", text) if not re.fullmatch(r"[٠-٩0-9]+", m.group(1).strip())]


# ---------- Q1 printed pages ----------
def q1(bid):
    meta = json.loads((ROOT / f"step1_sources/raw/book_{bid}.json").read_text(encoding="utf-8"), strict=False)
    pmap = meta["indexes"]["page_map"]
    rows, bad = [], 0
    for p in load_pages(bid):
        expected = pmap[p["pg"] - 1] if p["pg"] - 1 < len(pmap) else None
        got = f"{p['meta']['vol']},{p['meta']['page']}"
        ok = expected == got
        bad += not ok
        rows.append({"pg": p["pg"], "page_meta": got, "page_map": expected, "ok": ok, "headings": p["meta"].get("headings")})
    return {"pages": len(rows), "mismatches": bad, "rows": rows}


# ---------- Q2 matn vs sharh ----------
def q2(bid):
    paras = paragraphs(load_pages(bid))
    segs = [s for p in paras for s in matn_segments(p["text"])]
    with_matn = sum(1 for p in paras if matn_segments(p["text"]))
    return {"paragraphs": len(paras), "paragraphs_with_matn": with_matn, "matn_segments": len(segs), "matn_sample": segs[:25]}


# ---------- units: each matn segment + the sharh that follows it ----------
MATN_RE = re.compile(r"\(([^()]*)\)")


def units(bid):
    """Split a book's running text into units that start at each ( matn ) segment.

    Returns [{"vol","page","pg","matn","text","norm","matn_norm"}] in reading order.
    Text before the first matn segment becomes a unit with empty matn.
    """
    out = [{"vol": None, "page": None, "pg": None, "matn": "", "text": ""}]
    for p in load_pages(bid):
        body = strip_markup(p["body"])
        body = re.sub(r"﴿.*?﴾", lambda m: m.group(0).replace("(", "[").replace(")", "]"), body, flags=re.S)
        pos = 0
        for m in MATN_RE.finditer(body):
            inner = m.group(1).strip()
            if re.fullmatch(r"[٠-٩0-9]+", inner):  # footnote marker, not matn
                continue
            out[-1]["text"] += body[pos:m.start()]
            out.append({"vol": p["meta"]["vol"], "page": p["meta"]["page"], "pg": p["pg"], "matn": inner, "text": m.group(0)})
            pos = m.end()
        out[-1]["text"] += body[pos:] + "\n"
        if out[-1]["page"] is None:
            out[-1].update(vol=p["meta"]["vol"], page=p["meta"]["page"], pg=p["pg"])
    for u in out:
        u["norm"] = normalise(u["text"])
        u["matn_norm"] = normalise(u["matn"])
    return out


def word_cover(lemma_words, target_words):
    """Share of the lemma's words found, in order, in the target (difflib matching blocks)."""
    if not lemma_words:
        return 0.0
    sm = difflib.SequenceMatcher(None, lemma_words, target_words, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / len(lemma_words)


def locate(lemma, anchor, field="norm", min_cover=0.75, window=3):
    """Find the anchor unit containing the lemma.

    1. exact normalised substring in one unit, or across `window` consecutive units (lemma may span units)
    2. fuzzy: best word coverage over a window of units; accepted if >= min_cover
    Returns (unit index, method, score, n_exact_hits).
    """
    n = normalise(lemma)
    words = n.split()
    if len(words) < 2:
        return None, "too_short", 0.0, 0
    hits = [i for i, u in enumerate(anchor) if n in u[field]]
    if hits:
        return hits[0], "exact", 1.0, len(hits)
    joined = [" ".join(anchor[k][field] for k in range(i, min(i + window, len(anchor)))) for i in range(len(anchor))]
    hits = [i for i, t in enumerate(joined) if n in t]
    if hits:
        return hits[0], "exact_span", 1.0, len(hits)
    best_i, best = None, 0.0
    for i, t in enumerate(joined):
        c = word_cover(words, t.split())
        if c > best:
            best_i, best = i, c
    return best_i, ("fuzzy" if best >= min_cover else "none"), round(best, 3), 0


def anchor_index(bid=1679):
    return units(bid)


def ref(u):
    return {"vol": u["vol"], "page": u["page"], "pg": u["pg"], "matn": u["matn"], "text": u["text"].strip()}


# ---------- Q3 Ibn Qasim footnote anchors ----------
def q3(anchor):
    """Two independent methods, then compare:
    A. text: the words just before the note marker, searched in the Rawd units.
    B. structure: the note sits in an Ibn Qasim unit; align IQ units to Rawd units by matn, take the match.
    """
    iq = units(12216)
    # B: align IQ matn sequence to Rawd matn sequence
    a_keys = [u["matn_norm"] for u in anchor]
    b_keys = [u["matn_norm"] for u in iq]
    iq_to_anchor = {}
    for t, i1, i2, j1, j2 in difflib.SequenceMatcher(None, b_keys, a_keys, autojunk=False).get_opcodes():
        if t == "equal" or (t == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                iq_to_anchor[i1 + k] = j1 + k
    notes_by_pg = {p["pg"]: split_notes(p["notes"]) for p in load_pages(12216)}
    results = []
    for ui, u in enumerate(iq):
        prev_end = 0
        for m in re.finditer(MARK, u["text"]):
            n = int(m.group(1).translate(AR_DIGITS))
            lemma = u["text"][prev_end:m.start()]
            prev_end = m.end()
            lemma_words = normalise(lemma).split()[-12:]
            if not lemma_words:  # marker right after the matn: the matn itself is the lemma
                lemma_words = u["matn_norm"].split()[-12:]
            idx, how, score, nhits = locate(" ".join(lemma_words), anchor)
            # note markers restart per page; the note lives on the page where the marker appears
            pg = u["pg"]
            sidx = iq_to_anchor.get(ui)
            results.append({
                "iq_vol": u["vol"], "iq_page": u["page"], "note": n, "lemma": " ".join(lemma_words),
                "note_text": notes_by_pg.get(pg, {}).get(n, ""), "iq_pg": u["pg"],
                "text_link": how, "score": score, "ambiguous": nhits > 1,
                "text_anchor": None if idx is None or how == "none" else ref(anchor[idx]),
                "struct_anchor": None if sidx is None else ref(anchor[sidx]),
                "agree": (idx is not None and how != "none" and sidx is not None and abs(idx - sidx) <= 1),
            })
    c = Counter(r["text_link"] for r in results)
    linked = [r for r in results if r["text_link"] != "none" and r["text_link"] != "too_short"]
    both = [r for r in linked if r["struct_anchor"]]
    return {"notes": len(results), "text_method": dict(c),
            "ambiguous_exact": sum(r["ambiguous"] for r in results),
            "struct_aligned_units": f"{len(iq_to_anchor)}/{len(iq)}",
            "linked_by_text_and_struct": len(both), "methods_agree": sum(r["agree"] for r in both),
            "linked_by_either": sum(1 for r in results if (r["text_link"] not in ("none", "too_short")) or r["struct_anchor"]),
            "rows": results}


# ---------- Q4 Mumti' lemma headings ----------
def q4(anchor):
    """Mumti' headings quote the matn continuously; search them in the Rawd's matn stream (sharh removed)."""
    rows = []
    for p in load_pages(10649):
        for m in re.finditer(r"<span[^>]*data-type=\"?title\"?[^>]*>(.*?)</span>", p["body"]):
            lemma = re.sub(r"[.…]{2,}", " ", html.unescape(m.group(1))).strip()
            idx, how, score, _ = locate(lemma, anchor, field="matn_norm", window=8)
            rows.append({"vol": p["meta"]["vol"], "page": p["meta"]["page"], "lemma": lemma, "link": how, "score": score,
                         "anchor": None if idx is None or how == "none" else ref(anchor[idx])})
    quoted = sum(len(re.findall(r"قوله\s*:?\s*[«\"(]", p["body"])) for p in load_pages(10649))
    return {"headings": len(rows), "by_method": dict(Counter(r["link"] for r in rows)), "qawluhu_in_body": quoted, "rows": rows}


# ---------- Q5 edition alignment ----------
def q5():
    """Align the two Rawd editions unit by unit on their matn, then diff each aligned unit word by word."""
    a, b = units(1679), units(147658)
    sm = difflib.SequenceMatcher(None, [u["matn_norm"] for u in a], [u["matn_norm"] for u in b], autojunk=False)
    pairs, matn_diffs = [], []
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == "equal":
            pairs += [(i1 + k, j1 + k) for k in range(i2 - i1)]
        else:
            matn_diffs.append({"type": t, "1679": [a[k]["matn"] for k in range(i1, i2)], "147658": [b[k]["matn"] for k in range(j1, j2)],
                               "1679_page": a[i1]["page"] if i1 < len(a) else None, "147658_page": f"{b[j1]['vol']}/{b[j1]['page']}" if j1 < len(b) else None})
            if t == "replace" and i2 - i1 == j2 - j1:
                pairs += [(i1 + k, j1 + k) for k in range(i2 - i1)]
    diffs = []
    for i, j in pairs:
        wa, wb = a[i]["norm"].split(), b[j]["norm"].split()
        ops = [(t, " ".join(wa[i1:i2]), " ".join(wb[j1:j2]))
               for t, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes() if t != "equal"]
        ops = [o for o in ops if not re.fullmatch(r"[٠-٩0-9 ]*", o[1] + o[2])]  # ignore footnote numbers
        diffs.append({"1679": {"page": a[i]["page"], "matn": a[i]["matn"][:50]}, "147658": {"vol": b[j]["vol"], "page": b[j]["page"]},
                      "n_word_diffs": len(ops), "word_diffs": ops[:12]})
    rak_notes = sum(len(split_notes(p["notes"])) for p in load_pages(147658))
    return {"units_1679": len(a), "units_147658": len(b), "aligned_units": len(pairs),
            "matn_identical_share": round(sm.ratio(), 3), "matn_diff_blocks": len(matn_diffs),
            "units_identical_text": sum(d["n_word_diffs"] == 0 for d in diffs),
            "units_with_differences": sum(d["n_word_diffs"] > 0 for d in diffs),
            "rakaiz_footnotes": rak_notes, "matn_diffs": matn_diffs, "pairs": diffs}


def main():
    anchor = anchor_index()
    report = {}
    for bid in (1679, 147658, 12216, 10649):
        r = q1(bid)
        report[f"Q1_{bid}"] = {k: v for k, v in r.items() if k != "rows"}
        (OUT / f"q1_pages_{bid}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    for bid in (1679, 147658):
        r = q2(bid)
        report[f"Q2_{bid}"] = {k: v for k, v in r.items() if k != "matn_sample"}
        (OUT / f"q2_matn_{bid}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, fn in (("Q3_ibn_qasim", q3), ("Q4_mumti", q4)):
        r = fn(anchor)
        report[name] = {k: v for k, v in r.items() if k != "rows"}
        (OUT / f"{name.lower()}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    r = q5()
    report["Q5_editions"] = {k: v for k, v in r.items() if k != "pairs"}
    (OUT / "q5_editions.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
