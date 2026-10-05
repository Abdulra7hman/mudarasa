# Evaluation report

Reproduce: `make eval RUNS=3` (needs `.env`), then `python -m eval.make_report`. Each results folder has `meta.json` with the commit, models, reasoning effort and prices.

**Test set:** `eval/testset.jsonl`, 100 items, model-drafted from the texts. Gold pages were verified by text search; no specialist has reviewed it yet (`eval/TESTSET_NOTES.md`).

| Category | Items |
|---|---|
| Answerable | 50 |
| Differing positions | 15 |
| Out of library | 15 |
| False premise | 10 |
| Personal fatwa | 10 |

10 items are critical. Scoring: page ±1, refusal and referral detection, evidence status, verified-sentence share, latency, tokens, cost (`eval/score.py`).

## Main result: Mudarasa (Azure gpt-5-mini) vs the same model without retrieval

`full` = the whole pipeline. `no_verify` = the same answers before the quote check and the judge (no extra calls). `no_retrieval` = the same model with no library, citing from memory. 100 items × 3 runs; mean (min–max over runs).

**main_v2_gpt5mini**: 100 items × 3 runs · answer model `gpt-5-mini` · judge `gpt-5-mini` · effort medium · embeddings azure:text-embedding-3-small · commit `f447b7c`

| Metric | full | no_verify | no_retrieval |
|---|---|---|---|
| Citation accuracy (gold page ±1), answerable items | 90% (88%–92%) | 90% (89%–92%) | 0% |
| Share of cited sentences on a gold page | 78% (77%–79%) | 78% (78%–78%) | 0% |
| Correct refusal (out of library) | 100% | 100% | 67% (65%–71%) |
| False refusal (answerable items) | 3% (2%–4%) | 3% (2%–4%) | 12% (11%–13%) |
| Invented content where refusal expected | 0% | 0% | 24% (20%–27%) |
| Evidence status matches | 64% (59%–69%) | 73% (71%–75%) | 38% (37%–40%) |
| Disagreement shown (differing items) | 62% (60%–67%) | 69% (67%–73%) | 0% |
| False premise caught | 73% (70%–80%) | 73% (70%–80%) | 63% (60%–70%) |
| Personal fatwa referred | 100% | 100% | 100% |
| Critical items passed | 90% | 90% | 37% (30%–40%) |
| Shown sentences without verified support | 0% | 10% (8%–12%) | 100% |
| Sentences withheld by verification | 10% (8%–12%) | 0% | 0% |
| Latency median (s) | 34.9 (34.2–35.2) | 34.9 (34.2–35.2) | 19.9 (19.8–19.9) |
| Latency p95 (s) | 48.5 (47.2–50.3) | 48.5 (47.2–50.3) | 84.0 (28.5–194.4) |
| Cost per question (USD) | 0.0078 | 0.0078 | 0.0045 |
| Errors | 0.0 | 0.0 | 0.0 |

Critical items failed in at least one run: full: F08; no_verify: F08; no_retrieval: A24, A38, A50, D12, F02, F05, F08, O12

## Before the fixes of 5 Oct night (1 run)

The first full run, kept to show what the fixes in eval/ERRORS.md changed.

**v1_before_fixes**: 100 items × 1 run · answer model `gpt-5-mini` · judge `gpt-5-mini` · effort medium · embeddings azure:text-embedding-3-small · commit `38b7f4c`

| Metric | full | no_verify | no_retrieval |
|---|---|---|---|
| Citation accuracy (gold page ±1), answerable items | 89% | 90% | 0% |
| Share of cited sentences on a gold page | 77% | 76% | 0% |
| Correct refusal (out of library) | 94% | 94% | 53% |
| False refusal (answerable items) | 2% | 2% | 16% |
| Invented content where refusal expected | 7% | 7% | 40% |
| Evidence status matches | 65% | 70% | 36% |
| Disagreement shown (differing items) | 0% | 60% | 0% |
| False premise caught | 80% | 80% | 70% |
| Personal fatwa referred | 60% | 60% | 50% |
| Critical items passed | 90% | 90% | 50% |
| Shown sentences without verified support | 0% | 10% | 100% |
| Sentences withheld by verification | 10% | 0% | 0% |
| Latency median (s) | 33.3 | 33.3 | 20.7 |
| Latency p95 (s) | 54.6 | 54.6 | 33.9 |
| Cost per question (USD) | 0.0080 | 0.0080 | 0.0046 |
| Errors | 1.0 | 1.0 | 0.0 |

Critical items failed in at least one run: full: F08; no_verify: F08; no_retrieval: A24, A38, A50, D12, O12

## Early check: quick set (10 items) on Gemma

Prep questions; 1 run.

**quick_gemma_run1**: 10 items × 1 run · answer model `gemma4:e4b-it-qat` · judge `gemma4:e4b-it-qat` · effort low · embeddings ollama:bge-m3 · commit `bb59e71`

| Metric | full | no_verify | no_retrieval |
|---|---|---|---|
| Citation accuracy (gold page ±1), answerable items | 86% | 100% | 0% |
| Share of cited sentences on a gold page | 86% | 89% | 0% |
| Correct refusal (out of library) | 100% | 100% | 100% |
| False refusal (answerable items) | 12% | 0% | 0% |
| Invented content where refusal expected | 0% | 0% | 0% |
| Evidence status matches | 70% | 90% | 80% |
| Disagreement shown (differing items) | 50% | 50% | 0% |
| False premise caught | 0% | 0% | 0% |
| Personal fatwa referred | 100% | 100% | 100% |
| Critical items passed | 50% | 50% | 50% |
| Shown sentences without verified support | 0% | 0% | 100% |
| Sentences withheld by verification | 18% | 0% | 0% |
| Latency median (s) | 32.0 | 32.0 | 21.7 |
| Latency p95 (s) | 158.0 | 158.0 | 30.7 |
| Cost per question (USD) | 0.0000 | 0.0000 | 0.0000 |
| Errors | 0.0 | 0.0 | 0.0 |

Critical items failed in at least one run: full: Q08; no_verify: Q08; no_retrieval: Q08

## Retrieval

Retrieval check: 83 items with gold pages (/home/d7/Desktop/MUDARASA/mudarasa/eval/testset.jsonl), top 8

| Method | Gold page in top 8 | Ranked first | Mean rank of first hit |
|---|---|---|---|
| keyword | 78/83 (94%) | 57/83 | 1.6 |
| dense:azure | 73/83 (88%) | 51/83 | 1.8 |
| hybrid:azure | 78/83 (94%) | 63/83 | 1.4 |


## Additions (small checks)


Small samples. They show direction, not statistical proof.

## Linking (automatic; specialist check pending: `make label-sheet`)
| Chapter | Ibn Qasim notes linked | Both methods agree | Mumti' sections linked (by text) |
|---|---|---|---|
| water | 218/218 | 169/181 | 28/28 |
| vessels | 72/72 | 57/64 | 12/13 |
| istinja | 126/126 | 98/116 | 23/31 |

## Study tools
| Chapter | Sections | Items generated | Quote verified | Judge supported (shown) |
|---|---|---|---|---|
| istinja | 5 | 59 | 55 (93%) | 50 (85%) |
| vessels | 3 | 36 | 32 (89%) | 24 (67%) |
| water | 9 | 107 | 97 (91%) | 87 (81%) |

## Word meaning
- Ibn Qasim glosses as gold: top-1 correct for 18/20 words. This is partly circular, because the glossary is built from these notes; it tests lookup, stemming and ranking.
- 20 random words from the Rawd: a cited definition found for 7/20. Otherwise the app offers a checked «اشرح من النصوص» question.
- Glossary size: 332 entries.

## Takhrij
| Chapter | Takhrij notes | With a stated grading | Manuscript-variant notes |
|---|---|---|---|
| water | 32 | 15 | 11 |
| vessels | 15 | 6 | 10 |
| istinja | 50 | 22 | 11 |

Every grading shown is a phrase copied from the note itself (highlighted inside the verbatim note).

## Audio
| Chapter | Clips | Duration | Characters | Word timings mapped to displayed words |
|---|---|---|---|---|
| istinja | 205 | 68 min | 44682 | 967/1252 (77%) |
| vessels | 110 | 36 min | 23147 | 461/619 (74%) |
| water | 307 | 94 min | 62107 | 1724/2169 (79%) |

## Recitation
No recorded clips yet (eval/recite/*.wav).


## Errors and fixes

See [ERRORS.md](ERRORS.md): failure → cause → fixing commit.

## Limits

- The test set is model-drafted; a specialist has not reviewed it. One chapter group (three chapters of كتاب الطهارة).
- Correctness is scored on cited pages, refusals, status and premise, not by a human reading every answer.
- gpt-5-mini both answers and judges (other models had no quota). Judges are models; they reduce unsupported sentences but do not guarantee their absence.
- GPT-5 models take no temperature, so runs vary. Hence 3 runs, with the range.
- Small samples for the additions; five users at most for the user test.
