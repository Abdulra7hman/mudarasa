# Mudarasa: preparation work (1–3 Oct 2026)

Everything here was made before the build window (4–6 Oct). It will be listed in
`STARTING_POINT.md` at the first commit. Book texts in `books/` are never committed to the public repo.

| Step | Folder | Status | Result |
|---|---|---|---|
| 1. Data sources and terms (Turath, Shamela) | `step1_sources/` | Done, 1 Oct | `step1_sources/REPORT.md` |
| 2. Throwaway extraction test, باب المياه | `step2_extraction/` | Done, 1 Oct (specialist to label `linking_sample_50.csv`) | `step2_extraction/REPORT.md` |
| 3. Informal model check, 10 questions | `step3_model_check/` | Done, 2 Oct (Gemma 4 E4B, local) | `step3_model_check/REPORT.md` |
| Local test page (step 3 pipeline in a browser) | `demo/` | Running, 2 Oct | `python3 prep/demo/server.py` → http://127.0.0.1:8765 |
| Retrieval fix (stemming + BGE-M3 hybrid + table of contents) | `retrieval/` | Done, 2 Oct | `retrieval/REPORT.md` |
| Research: Qaf, the named alternative | `research_qaf/` | Done, 2 Oct | `research_qaf/REPORT.md` |

- `conversation/`: the whole conversation as Markdown. Refresh any time with `python3 prep/conversation/export_conversation.py`.
- `books/CATALOG.md`: every book or source we depend on, with its ID, edition, link and status.
- `الأدوات_والتقنيات_والمصادر.md`: Arabic summary of every tool, technology, model and source, in use and planned.
- `templates/`: the exact formats for the specialist's answer policy, test set and library list.

## Where the code is
| File | What it does |
|---|---|
| `step2_extraction/analyse.py` | Arabic normalisation; page parsing (text vs footnotes); matn extraction; linking commentary notes to the Rawd; edition alignment |
| `step2_extraction/fetch_pages.py` | Fetched the باب المياه pages from Turath |
| `step2_extraction/make_label_sheet.py` | Builds the 50-note sheet for the specialist |
| `retrieval/retrieval.py` | Passages, stemming, BM25, BGE-M3 embeddings, hybrid search, table of contents |
| `retrieval/retrieval_test.py` | Measures whether the right page is retrieved |
| `step3_model_check/run_check.py`, `run_variants.py`, `score_all.py` | The 10-question model check |
| `demo/server.py` | The local test website's backend: scope gate → search → Gemma answer → quote check |
| `demo/index.html` | The test website's page |
| `conversation/export_conversation.py` | Exports this conversation to Markdown |
