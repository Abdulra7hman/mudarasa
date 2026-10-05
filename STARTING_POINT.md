# Starting point (disclosure)

This is everything that existed **before** product work began. It is the content of the first commit, tagged `start`.

## Timeline
| When | What | Where |
|---|---|---|
| 29 Sep 2026 | Pitch deck draft (16 pages, mockups) | not in repo |
| 1 Oct | Plan document "Mudarasa: Plan to the Final" | not in repo |
| 1 Oct | Step 1: data sources and terms (Turath, Shamela) | `prep/step1_sources/REPORT.md` |
| 1 Oct | Step 2: throwaway extraction and linking test, باب المياه only | `prep/step2_extraction/` |
| 2 Oct | Step 3: informal model check, 10 questions, local Gemma 4 E4B | `prep/step3_model_check/` |
| 2 Oct | Local test page for the step-3 pipeline | `prep/demo/` |
| 2 Oct | Retrieval fix (stemming, BGE-M3 hybrid, table of contents) | `prep/retrieval/` |
| 2 Oct | Research on Qaf, the named alternative | `prep/research_qaf/REPORT.md` |
| 4 Oct | Row 1 of the Qaf probe sheet filled in by hand | `prep/research_qaf/` (sheet kept out of git: it quotes book text) |
| 5 Oct, morning | One question asked on the local test page; build plan written | `prep/BUILD_PLAN.md` |

**No product code was written before 5 Oct, 18:15.** The build's commit history starts then, and nothing is backdated.
No work was done on 4 Oct apart from the Qaf row.

## What is reused
The prep code is a throwaway test, kept as it was. The product code in `app/`, `web/`, `scripts/` and `eval/` is new.
Where product code adapts prep code, the module says so. The main pieces adapted are:
- `normalise`, `split_notes` and `units` from `prep/step2_extraction/analyse.py`
- `Retriever` from `prep/retrieval/retrieval.py`
- `answer` from `prep/demo/server.py`

Known defect in the prep code, fixed in the product: `q3()` attaches Ibn Qasim notes using the page where the unit
*starts*. Units cross pages and note numbers restart on every page, so about 97 of the 222 notes in باب المياه got
another note's text. The product resolves each marker to its own page; see `tests/test_linking.py`.

## Kept out of git
Book texts, and any file that quotes them at length, stay on the server (see `.gitignore` and `SOURCES.md`):
- `prep/books/`
- `prep/step1_sources/raw/`
- the step-2 result files
- the linking sample sheet
- the Qaf sheet
- the step-3 raw outputs
- the embedding cache

The conversation export (`prep/conversation/*.md`) is private.

---
**بالعربية:** هذا الملف يفصح عن كل ما سبق بدء العمل على المنتج: التخطيط والتجارب في ١–٣ أكتوبر، وصفٌّ واحد في جدول اختبار «قاف» يوم ٤ أكتوبر.
لم تُكتب أي شيفرة للمنتج قبل ٥ أكتوبر الساعة ١٨:١٥، ولم يُقدَّم تاريخ أي إيداع. نصوص الكتب لا تُرفع إلى المستودع العام.
