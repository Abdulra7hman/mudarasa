# Step 1: Data sources and terms (1 Oct 2026)

## Turath (app.turath.io, run by Nuqayah; texts come from Shamela)
- API: `https://api.turath.io`, no key needed.
  - `/book?id=ID&include=indexes&ver=3`: metadata, headings (chapter path), `page_map` (internal page → "volume,printed page").
  - `/page?book_id=ID&pg=N&ver=3`: page text plus meta (vol, printed page). Footnotes come after a `_________` line, numbered `(١)`.
  - `/search?q=...&ver=3`: full-text search.
- Terms: none published. robots.txt has only Cloudflare's content-signal boilerplate with no signals and no Disallow, so it neither permits nor forbids anything.
- Python's default user agent gets HTTP 403; curl works.
- The full-book JSON (`files.turath.io/books/ID.json`) returns 404, so a book has to be fetched page by page.
- Decision (user, 1 Oct): use Turath for a small prototype set, fetched slowly, texts kept off the public repo.

## Shamela
- Terms updated 19 Sep 2026: lawful research and reading are allowed; no getting around rate limits; no rebuilding the index; rights stay with each book's holder.
- Official MCP service at `mcp.shamela.ws`, with tools `shamela_find`, `shamela_find_scoped`, `shamela_open` and `shamela_open_many`. It is for limited, page-by-page reading, not bulk ingestion. Fine for live cross-checks.

## Findings that matter for the build
- Matn inside the Rawd is wrapped in `( … )`, so separating matn from sharh is mechanical.
- Ibn Qasim's Hashiya (12216) reprints the Rawd with note numbers placed inline, which gives exact link anchors.
- Al-Sharh al-Mumti' (10649) uses Zad lemmas as headings, which gives direct links to the anchor.
- All four books checked are marked «ترقيم الكتاب موافق للمطبوع».
- Caveat for 1679: Shamela says its e-text was taken from a different printing, so wording should be checked against the print.
- The organizers' reference package (`raw/marjiyya_reference_package.txt`) defines the four content levels (أ–د) and accepts Shamela editions.

## Files
- `raw/book_*.json`: metadata and indexes for 1679, 147658, 12216, 10649.
- `raw/p1679_8.json`, `raw/p12216.json`: sample pages.
- `raw/shamela_tools.json`: Shamela MCP tool list.
- `find_books.py`: the throwaway search script used to find the books.

## Update, 2 Oct 2026
- **Full books are downloadable**: `https://files.turath.io/books-v3/<ID>.json`, the file behind the app's «تحميل الكتب» (offline download) button. The four books are saved in `../books/<ID>/full.json` (identical text to the API pages). The old SDK path (`/books/<ID>.json`) is what returned 404.
- **Turath runs its own MCP server for AI models**: `https://api.turath.ai/mcp`, tools `turath_find` and `turath_open` ("open … as exact, citable sources"). A sample client connecting it to OpenAI was published on 1 Oct 2026: https://gist.github.com/mustafa0x/5a71db72bf87a1f4c5923bb51498db1f
- Qaf's app states: "The Shamela data is generously provided by the developers behind Turath.io."
- Together: Turath openly supports AI research and offline download of whole books. Still no written licence; rights in each edition stay with its holders, so texts stay off the public repo.
