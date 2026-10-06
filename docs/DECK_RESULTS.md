# Numbers for the deck (each with the file it comes from)

All results are from `eval/` (re-run with `make eval RUNS=3`). The deployed settings are gpt-5-mini answering and judging, 12 passages, and single-pass answers.

## Slide: Results against the plain model (100 questions × 3 runs)
Source: `eval/REPORT.md` § Main result, folder `eval/results/main_v3_live`.

| | Mudarasa | Same model, no books |
|---|---|---|
| Right page cited (±1) | **90%** (88–92) | 0% |
| Out-of-library questions refused | **98%** | 67% |
| Invented content where it should refuse | **2%** | 27% |
| Personal fatwa referred | **100%** | 97% |
| Critical items passed | **87%** | 40% |
| False refusals on answerable questions | 4% | 15% |

**What verification adds:** 9% of drafted sentences had no verified support and were withheld. Without the checks, they would have been shown (`no_verify` column).

## Slide: Every sentence checked
1. A verbatim quote must exist on the cited page.
2. A second model call checks that the quote says what the sentence says.
3. Whatever fails is withheld and listed for the user.
4. An evidence label is shown on every answer: مؤيد / مؤيد جزئيًّا / أقوال مختلفة / لم يوجد نص.

Source: `CONTENT.md`, `app/pipeline.py`.

## Slide: Against Qaf (20 probes, the same questions)
Source: `eval/qaf/COMPARISON.md` (filled after the Qaf column is entered).

Mudarasa on the 14 chat probes (3 runs, majority vote): **11 pass, 1 partial, 2 fail**. The other 6 probes are features (paragraph-by-paragraph study, edition differences, quizzes, progress), scored from the screens.

Qaf: *to be filled in from the sheet.*

## Slide: Running it
| | Value | Source |
|---|---|---|
| Time per checked answer | median **26 s** (the found passages appear after ~3 s) | `eval/REPORT.md` |
| Out-of-scope refusals | ~3 s | measured on the live site |
| Suggested questions | 0.7 s (cached) | live site |
| Cost per question | **$0.0064** | `eval/results/main_v3_live/summary.json` |
| Hosting | Azure App Service B1, ~$13/month | Azure price list |
| Fallback | If the model is unreachable: search-only mode (cited passages, nothing generated). Changing model: one line in `.env` | `SOURCES.md` |

**Estimate for 1,000 active students a month, at 30 questions each:**
- About **$190** for questions.
- **$13** for hosting.
- Speech-to-text for recitation at $1 an hour: if each student recites 30 minutes a month, about **$500**.
- **Total about $700 a month, roughly $0.70 per student.** Caching repeated questions lowers the model cost.

## Slide: Choosing the model by test (100 questions)
Source: `eval/REPORT.md` § Answer model compared.

| | gpt-5-mini (deployed) | gpt-5.4-mini |
|---|---|---|
| Right page cited | **90%** | 87% |
| Cited sentences on a right page | 77% | **91%** |
| False refusals | **4%** | 11% |
| Critical items | **87%** | 80% |
| Median time | 26 s | **13 s** |

The newer model is twice as fast, but the word-for-word quote check removes more of its sentences, so gpt-5-mini stays.

## Slide: The additions (small checks; direction, not proof)
Source: `eval/ADDITIONS.md`.

| Addition | Measured |
|---|---|
| Study tools | 202 items generated, 91% with verified quotes, 80% shown after the judge |
| Audio | 622 recordings, about 3 h 17 min, 79% of words with timings |
| Takhrij | 97 takhrij notes in the 3 chapters, 43 with a stated grading (quoted, never decided by the system) |
| Word meaning | 332 glossary entries from the books' own glosses; otherwise a checked question |
| Memorization | Words revealed live as recited (Azure speech-to-text, ar-SA); a line recited correctly scored 8/8 |

## Slide: Done / Next
**Done:**
- 4 books in 3 chapters of كتاب الطهارة, linked paragraph by paragraph.
- Cited chat with two checks and evidence labels.
- Refusal and referral.
- Listening, memorization, study tools, word meaning, takhrij, review cards, notebook.
- An evaluation that re-runs with one command.
- The team's interface connected to the books: pages that turn with the voice, a citation opens its quote highlighted in the book, bookmarks on a word, notes from a selection, dictation and photo questions in the chat.
- A live site.

**Next:**
- All of كتاب الطهارة, then the whole Rawd.
- A specialist review of the links and the test set.
- A tolerant quote match, then gpt-5.4-mini (twice as fast) or gpt-5.4 (no quota yet) as the answer model, with gpt-5-mini as a separate judge.
- BGE-M3 search (99% vs 95% gold page in the top 8).
- Hosting in Saudi Arabia East when it opens.
- A data agreement for more books.

## Honest limits (appendix)
- The test set is model-drafted and not yet reviewed by a specialist.
- The linking is automatic and not hand-checked.
- One model both answers and judges.
- Three chapters only.
- GPT-5 runs vary, so the ranges are shown.
- The content filter blocks one istinja question (F08) until a custom guardrail is set.
