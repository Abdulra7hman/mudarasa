"""Throwaway (prep, 1 Oct): fetch باب المياه pages from Turath, slowly, one page at a time.

Saves raw API responses untouched to prep/books/<ID>/pages/<pg>.json and skips pages already saved.
Uses curl with its default user agent; 2 s between requests.
"""
import json
import pathlib
import subprocess
import time
from datetime import datetime, timezone

BOOKS = pathlib.Path(__file__).resolve().parent.parent / "books"
RANGES = {  # Turath internal page ranges covering باب المياه (from the book headings)
    1679: (6, 14),
    147658: (65, 83),
    12216: (53, 99),
    10649: (21, 64),
}
DELAY = 2.0


def fetch(url: str) -> bytes:
    r = subprocess.run(["curl", "-s", "-f", "-m", "30", url], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl exit {r.returncode} for {url}")
    return r.stdout


def main():
    for bid, (a, b) in RANGES.items():
        out = BOOKS / str(bid) / "pages"
        out.mkdir(parents=True, exist_ok=True)
        for pg in range(a, b + 1):
            f = out / f"{pg}.json"
            if f.exists():
                continue
            url = f"https://api.turath.io/page?book_id={bid}&pg={pg}&ver=3"
            try:
                raw = fetch(url)
                json.loads(raw.decode(), strict=False)  # sanity check only
                f.write_bytes(raw)
                print(bid, pg, "ok", flush=True)
            except Exception as e:  # keep going; report gaps
                print(bid, pg, "FAILED", e, flush=True)
            time.sleep(DELAY)
        src = BOOKS / str(bid) / "SOURCE.md"
        src.write_text(
            f"# Source of book {bid}\n\n"
            f"- Fetched from: https://api.turath.io/page?book_id={bid}&pg=N&ver=3 (Turath, Nuqayah; text from Shamela)\n"
            f"- Pages: {a}–{b} (Turath internal numbering), باب المياه only\n"
            f"- Fetched: {datetime.now(timezone.utc).isoformat(timespec='seconds')} by fetch_pages.py, 2 s between requests\n"
            f"- Terms: Turath publishes none; rights in the edition stay with its holders. Prototype use only; never commit to the public repo.\n"
            f"- Metadata: ../../step1_sources/raw/book_{bid}.json\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
