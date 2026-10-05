"""Download the library books from Turath into data/books/<id>/ (full.json + meta.json). Slow on purpose; run once.

Adapted from prep/step2_extraction/fetch_pages.py. Uses curl (as in prep). One request per file, 3 s apart.
  full text : https://files.turath.io/books-v3/<id>.json
  headings  : https://api.turath.io/book?id=<id>&include=indexes&ver=3
Usage: python -m scripts.fetch_books [ids...]      (default: 1679 147658 12216 10649)
"""
import json
import subprocess
import sys
import time

from app import books as B

DEFAULT = [1679, 147658, 12216, 10649]


def get(url, path):
    r = subprocess.run(["curl", "-s", "-f", "-m", "300", "-o", str(path), url])
    if r.returncode:
        raise RuntimeError(f"download failed ({r.returncode}): {url}")


def main(ids):
    for bid in ids:
        d = B.BOOKS / str(bid)
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "full.json").exists():
            get(f"https://files.turath.io/books-v3/{bid}.json", d / "full.json")
            time.sleep(3)
        if not (d / "meta.json").exists():
            get(f"https://api.turath.io/book?id={bid}&include=indexes&ver=3", d / "meta.json")
            time.sleep(3)
        pages = json.loads((d / "full.json").read_text(encoding="utf-8"), strict=False)["pages"]
        (d / "SOURCE.md").write_text(f"Turath book {bid}: https://app.turath.io/book/{bid}\nDownloaded {time.strftime('%Y-%m-%d')}; "
                                     f"{len(pages)} pages. Kept on the server only.\n", encoding="utf-8")
        print(bid, len(pages), "pages")


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or DEFAULT)
