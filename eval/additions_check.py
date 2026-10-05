"""Small checks for the additions. They show direction, not statistical proof; the report says so.

  study tools : items generated -> quote verified -> judge supported (from data/tools/*.json)
  word        : 20 words that Ibn Qasim glosses (his gloss is the gold) -> top-1 hit; 20 other words -> coverage
  takhrij     : takhrij notes per chapter, share with a stated grading, share linked to a paragraph
  audio       : clips made vs planned, words with timings (from data/audio/manifest_*.json)
  recitation  : eval/recite/*.wav + same-name .json {"chapter","line","planted":[{"i":3,"type":"skip|wrong"}]}
                transcribed by Azure speech-to-text, then matched (app/recite.py): word accuracy on clean clips,
                planted mistakes caught
Usage: python -m eval.additions_check   -> eval/ADDITIONS.md
"""
import json
import pathlib
import random
import re

from app import books as B
from app import config as C
from app.features import Glossary, matn_lines, note_kind, takhrij_for
from app.recite import align
from app.textnorm import normalise

HERE = pathlib.Path(__file__).resolve().parent


def study_tools():
    rows = []
    for f in sorted((B.DATA / "tools").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        g = sum(s["stats"]["generated"] for s in d["sections"])
        q = sum(s["stats"]["quote_ok"] for s in d["sections"])
        j = sum(s["stats"]["judge_ok"] for s in d["sections"])
        rows.append((d["chapter"], len(d["sections"]), g, q, j))
    if not rows:
        return "Not generated yet.\n"
    out = ["| Chapter | Sections | Items generated | Quote verified | Judge supported (shown) |", "|---|---|---|---|---|"]
    for c, n, g, q, j in rows:
        out.append(f"| {c} | {n} | {g} | {q} ({q / g:.0%}) | {j} ({j / g:.0%}) |" if g else f"| {c} | {n} | 0 | – | – |")
    return "\n".join(out) + "\n"


def word(study):
    gl = Glossary(study)
    random.seed(7)
    gold = [e for e in gl.entries if e["kind"] == "note"]
    gold = random.sample(gold, min(20, len(gold)))
    hit = sum(1 for e in gold if (gl.lookup(e["word"], e["para"]) or [{}])[0].get("definition") == e["definition"])
    words = [w for p in study["paras"].values() for w in re.findall(r"[ء-ي]{4,}", p["text"])]
    others = random.sample(sorted(set(words)), 20)
    cov = sum(1 for w in others if gl.lookup(w))
    return (f"- Ibn Qasim glosses as gold: top-1 correct for {hit}/{len(gold)} words. This is partly circular, because the glossary is built from these notes; it tests lookup, stemming and ranking.\n"
            f"- 20 random words from the Rawd: a cited definition found for {cov}/20. Otherwise the app offers a checked «اشرح من النصوص» question.\n"
            f"- Glossary size: {len(gl.entries)} entries.\n")


def takhrij(study):
    out = ["| Chapter | Takhrij notes | With a stated grading | Manuscript-variant notes |", "|---|---|---|---|"]
    for ch in study["chapters"]:
        items = [t for pid in ch["paras"] for t in takhrij_for(study["paras"][pid])]
        tk = [t for t in items if t["kind"] == "takhrij"]
        out.append(f"| {ch['id']} | {len(tk)} | {sum(bool(t['grades']) for t in tk)} | {sum(t['kind'] == 'variant' for t in items)} |")
    return "\n".join(out) + "\n\nEvery grading shown is a phrase copied from the note itself (highlighted inside the verbatim note).\n"


def audio():
    rows = []
    for f in sorted((B.DATA / "audio").glob("manifest_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        clips = d["clips"]
        timed = [c for c in clips if c["words"]]
        mapped = sum(len(c["words"]) for c in timed)
        bounds = sum(c["boundaries"] for c in timed)
        rows.append(f"| {d['chapter']} | {len(clips)} | {sum(c['duration_ms'] for c in clips) / 60000:.0f} min | "
                    f"{sum(c['chars'] for c in clips)} | {mapped}/{bounds} ({(mapped / bounds) if bounds else 0:.0%}) |")
    if not rows:
        return "Not generated yet.\n"
    return "| Chapter | Clips | Duration | Characters | Word timings mapped to displayed words |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n"


def recitation(study):
    clips = sorted((HERE / "recite").glob("*.wav"))
    if not clips:
        return "No recorded clips yet (eval/recite/*.wav).\n"
    if not (C.SPEECH_KEY and C.SPEECH_REGION):
        return f"{len(clips)} clips found, but no Azure Speech key is configured.\n"
    import azure.cognitiveservices.speech as sdk
    lines_by = {}
    rows, clean_ok, clean_n, caught, planted = [], 0, 0, 0, 0
    for wav in clips:
        meta = json.loads(wav.with_suffix(".json").read_text(encoding="utf-8"))
        ch = meta["chapter"]
        lines_by.setdefault(ch, matn_lines(study, ch))
        expected = [w["plain"] for w in lines_by[ch][meta["line"] - 1]["words"]]
        cfg = sdk.SpeechConfig(subscription=C.SPEECH_KEY, region=C.SPEECH_REGION)
        cfg.speech_recognition_language = "ar-SA"
        rec = sdk.SpeechRecognizer(cfg, sdk.audio.AudioConfig(filename=str(wav)))
        pl = sdk.PhraseListGrammar.from_recognizer(rec)
        for w in expected:
            pl.addPhrase(w)
        text = rec.recognize_once_async().get().text
        st, said = align(expected, text.split())
        if meta.get("planted"):
            for p in meta["planted"]:
                planted += 1
                caught += st[p["i"]] in ("skip", "wrong")
        else:
            clean_n += len(expected)
            clean_ok += st.count("ok")
        rows.append(f"| {wav.name} | {len(meta.get('planted', []))} | {st.count('ok')}/{len(expected)} | {normalise(text)[:60]} |")
    return ("| Clip | Planted mistakes | Words matched | Transcript (start) |\n|---|---|---|---|\n" + "\n".join(rows) +
            f"\n\nClean clips: {clean_ok}/{clean_n} words accepted ({clean_ok / clean_n:.0%}). " if clean_n else "\n\n") + \
           (f"Planted mistakes caught: {caught}/{planted}.\n" if planted else "")


def main():
    study = json.loads((B.DATA / "build/study.json").read_text(encoding="utf-8"))
    stats = json.loads((B.DATA / "build/stats.json").read_text(encoding="utf-8"))
    link = ["| Chapter | Ibn Qasim notes linked | Both methods agree | Mumti' sections linked (by text) |", "|---|---|---|---|"]
    for c, s in stats.items():
        by_text = s["mumti_linked"] - s["mumti_by_method"].get("order", 0)
        link.append(f"| {c} | {s['iq_linked']}/{s['iq_notes']} | {s['iq_methods_agree']}/{s['iq_both_methods']} | {by_text}/{s['mumti_headings']} |")
    md = ["# Additions: small checks", "", "Small samples. They show direction, not statistical proof.", "",
          "## Linking (automatic; specialist check pending: `make label-sheet`)", "\n".join(link), "",
          "## Study tools", study_tools(), "## Word meaning", word(study), "## Takhrij", takhrij(study),
          "## Audio", audio(), "## Recitation", recitation(study)]
    (HERE / "ADDITIONS.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
