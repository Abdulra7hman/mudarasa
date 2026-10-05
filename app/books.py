"""Book texts on disk: data/books/<id>/full.json (pages) and meta.json (headings, page_map). Never committed."""
import functools
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BOOKS = DATA / "books"

BOOK_NAMES = {1679: "الروض المربع (ط الرسالة)", 147658: "الروض المربع (ط ركائز)",
              12216: "حاشية الروض المربع لابن قاسم", 10649: "الشرح الممتع لابن عثيمين",
              12145: "المصباح المنير للفيومي"}
SHORT = {1679: "الروض", 147658: "الروض (ركائز)", 12216: "ابن قاسم", 10649: "الممتع", 12145: "المصباح المنير"}


@functools.lru_cache(maxsize=None)
def pages(bid: int):
    return json.loads((BOOKS / str(bid) / "full.json").read_text(encoding="utf-8"), strict=False)["pages"]


@functools.lru_cache(maxsize=None)
def meta(bid: int):
    return json.loads((BOOKS / str(bid) / "meta.json").read_text(encoding="utf-8"), strict=False)


def page(bid: int, pg: int):
    """Internal page number (1-based, as Turath's pg)."""
    return pages(bid)[pg - 1]


def turath_link(bid: int, pg: int) -> str:
    return f"https://app.turath.io/book/{bid}?page={pg}"
