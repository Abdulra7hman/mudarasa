"""Pre-generate the audio for the listen view with Azure AI Speech (neural Arabic voice) and word timings.

Reads what the listen view plays (/api/listen order): Rakaiz paragraphs (vocalized), their matn only, and Ibn Qasim's
notes. Text is made speakable first (honorific ligatures spelled out, footnote markers and brackets removed). Word
timings from the synthesizer are mapped onto the words the page displays, by searching forward.

Usage: python -m scripts.build_tts [--chapters water] [--voice ar-SA-HamedNeural] [--limit N] [--probe]
Output: data/audio/<chapter>/<id>.mp3 and data/audio/manifest_<chapter>.json (gitignored)
"""
import argparse
import json
import re
import time

from app import books as B
from app import config as C
from app.textnorm import normalise, speakable

OUT = B.DATA / "audio"


def display_words(text):
    """Words exactly as the page splits them (web/js/features.js: textContent.split(/(\\s+)/))."""
    return [w for w in re.split(r"\s+", text) if w]


def map_words(boundaries, shown):
    """boundaries [(ms, word)] from the synthesizer -> [{t, i}] with i an index into the displayed words."""
    keys = [normalise(w) for w in shown]
    out, i = [], 0
    for ms, w in boundaries:
        n = normalise(w)
        if not n:
            continue
        for j in range(i, min(i + 8, len(keys))):
            if keys[j] and (keys[j] == n or keys[j].endswith(n) or n.endswith(keys[j])):
                out.append({"t": ms, "i": j})
                i = j + 1
                break
    return out


def synth(text, voice, path):
    import azure.cognitiveservices.speech as speechsdk
    cfg = speechsdk.SpeechConfig(subscription=C.SPEECH_KEY, region=C.SPEECH_REGION)
    cfg.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
    cfg.speech_synthesis_voice_name = voice
    syn = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=speechsdk.audio.AudioOutputConfig(filename=str(path)))
    bounds = []
    syn.synthesis_word_boundary.connect(lambda e: bounds.append((round(e.audio_offset / 10000), e.text)))
    r = syn.speak_text_async(text).get()
    if r.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError(f"{r.reason}: {getattr(r, 'cancellation_details', None) and r.cancellation_details.error_details}")
    return bounds, round(r.audio_duration.total_seconds() * 1000)


def matn_only(text):
    return " ".join(m for m in re.findall(r"\(([^()]*)\)", text) if not re.fullmatch(r"[\s٠-٩0-9]+", m))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="water,vessels,istinja")
    ap.add_argument("--voice", default="ar-SA-HamedNeural")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--probe", action="store_true", help="2 clips only, print timings")
    a = ap.parse_args()
    from fastapi import FastAPI
    from app import features
    study = json.loads((B.DATA / "build/study.json").read_text(encoding="utf-8"))
    app = FastAPI()
    features.register(app, study)
    listen = next(r.endpoint for r in app.routes if getattr(r, "path", "") == "/api/listen/{cid}")
    for cid in a.chapters.split(","):
        d = listen(cid)
        (OUT / cid).mkdir(parents=True, exist_ok=True)
        man_path = OUT / f"manifest_{cid}.json"
        man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {"chapter": cid, "voice": a.voice, "clips": []}
        have = {c["id"] for c in man["clips"]}
        jobs = []
        for p in d["paras"]:
            jobs.append((p["id"], p["text"], p["text"]))
            if matn_only(p["text"]):
                jobs.append((p["id"] + ":matn", matn_only(p["text"]), None))
            for n in p["notes"]:
                jobs.append((n["id"], "قال ابن قاسم: " + n["text"], None))
        jobs = [j for j in jobs if j[0] not in have][: (2 if a.probe else (a.limit or None))]
        print(cid, len(jobs), "clips to make", flush=True)
        for k, (cid_, text, shown) in enumerate(jobs, 1):
            say = speakable(text)
            fname = f"{cid}/{cid_.replace(':', '_')}.mp3"
            for attempt in range(4):
                try:
                    bounds, dur = synth(say, a.voice, OUT / fname)
                    break
                except Exception as e:  # free tier: 20 requests a minute; back off and retry
                    print("  retry", attempt + 1, str(e)[:120], flush=True)
                    time.sleep(15 * (attempt + 1))
            else:
                continue
            words = map_words(bounds, display_words(shown)) if shown else []
            man["clips"].append({"id": cid_, "file": fname, "duration_ms": dur, "chars": len(say), "boundaries": len(bounds), "words": words})
            man_path.write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
            if a.probe:
                print(" ", cid_, dur, "ms;", len(bounds), "boundaries;", len(words), "mapped of", len(display_words(shown or "")), "shown words;",
                      bounds[:6], flush=True)
            elif k % 10 == 0:
                print(" ", k, "/", len(jobs), flush=True)
            time.sleep(3.1)  # stay under 20 requests per minute on F0


if __name__ == "__main__":
    main()
