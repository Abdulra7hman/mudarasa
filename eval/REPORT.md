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

## Main result: Mudarasa as deployed (Azure gpt-5-mini) vs the same model without retrieval

`full` = the whole pipeline with the live settings (single-pass answers, medium answer effort, low judge effort, 12 passages). `no_verify` = the same answers before the quote check and the judge (no extra calls). `no_retrieval` = the same model with no library, citing from memory. 100 items × 3 runs; mean (min–max over runs).

**main_v3_live**: 100 items × 3 runs · answer model `gpt-5-mini` · judge `gpt-5-mini` · effort medium · embeddings azure:text-embedding-3-small · commit `9bcfd8a`

| Metric | full | no_verify | no_retrieval |
|---|---|---|---|
| Citation accuracy (gold page ±1), answerable items | 90% (88%–92%) | 92% (92%–93%) | 0% |
| Share of cited sentences on a gold page | 77% (75%–78%) | 77% (76%–78%) | 0% |
| Correct refusal (out of library) | 98% (94%–100%) | 98% (94%–100%) | 67% (65%–71%) |
| False refusal (answerable items) | 4% (4%–6%) | 4% (2%–5%) | 15% (12%–20%) |
| Invented content where refusal expected | 2% (0%–7%) | 2% (0%–7%) | 27% |
| Evidence status matches | 66% (64%–67%) | 73% (72%–74%) | 39% (37%–41%) |
| Disagreement shown (differing items) | 58% (40%–73%) | 69% (60%–73%) | 0% |
| False premise caught | 70% | 70% | 63% (50%–70%) |
| Personal fatwa referred | 100% | 100% | 97% (90%–100%) |
| Critical items passed | 87% (80%–90%) | 87% (80%–90%) | 40% (30%–50%) |
| Shown sentences without verified support | 0% | 9% (7%–11%) | 100% |
| Sentences withheld by verification | 9% (7%–11%) | 0% | 0% |
| Latency median (s) | 25.7 (23.6–26.9) | 25.7 (23.6–26.9) | 16.7 (16.1–17.1) |
| Latency p95 (s) | 36.7 (34.8–37.8) | 36.7 (34.8–37.8) | 23.7 (22.9–24.5) |
| Cost per question (USD) | 0.0064 | 0.0064 | 0.0041 |
| Errors | 0.0 | 0.0 | 0.0 |

Critical items failed in at least one run: full: F02, F08; no_verify: F02, F08; no_retrieval: A24, A38, A50, D12, F05, F08, O12

## Earlier settings: evidence list first, medium judge effort, 8 passages (3 runs)

The same pipeline before the speed comparison below.

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

## Speed settings compared (30 mixed items, 1 run)

| Setting | Median s | p95 s | Gold page cited | False refusal | Status match | Premise caught | Critical |
|---|---|---|---|---|---|---|---|
| Evidence list first, answer medium, judge medium | 32.1 | 45.0 | 89% | 7% | 73% | 100% | 100% |
| Single pass, answer low, judge low | 12.6 | 17.8 | 100% | 0% | 63% | 75% | 50% |
| Single pass, answer medium, judge low (chosen) | 26.9 | 37.9 | 96% | 0% | 73% | 100% | 100% |

The fast setting loses a critical false-premise item, so the middle one is used.

## Answer model compared: gpt-5-mini vs gpt-5.4-mini (100 items; 6 Oct)

gpt-5.4-mini got quota on 6 Oct (Data Zone Standard, US). It was run on the full test set with the same pipeline and
the same judge (gpt-5-mini). Folders `eval/results/m54_medium` and `eval/results/m54_low` (1 run each; gpt-5-mini: 3 runs).

| Metric | gpt-5-mini, medium (deployed) | gpt-5.4-mini, medium | gpt-5.4-mini, low | gpt-5.4-mini, medium, quote moved* | gpt-5-mini, low |
|---|---|---|---|---|---|
| Citation accuracy (gold page ±1) | **90%** (88–92) | 87% | 78% | 88% | 84% |
| Share of cited sentences on a gold page | 77% (75–78) | **91%** | 85% | **91%** | 76% |
| Correct refusal (out of library) | 98% (94–100) | **100%** | **100%** | **100%** | 94% |
| False refusal (answerable) | **4%** (4–6) | 11% | 17% | 11% | 6% |
| Invented content where refusal expected | 2% (0–7) | **0%** | **0%** | **0%** | 7% |
| Evidence status matches | 66% (64–67) | 67% | 64% | **72%** | 54% |
| Disagreement shown | **58%** (40–73) | 33% | 27% | 33% | 47% |
| Critical items passed | **87%** (80–90) | 80% | 80% | 70% | 80% |
| Sentences withheld by verification | 9% (7–11) | 15% | 15% | 7% | 16% |
| Latency median (s) | 25.7 | 13.0 | **6.8** | 13.6 | 13.1 |
| Cost per question (USD) | 0.0064 | 0.0072 | **0.0038** | 0.0070 | 0.0029 |

\* A quote that is word for word in another retrieved passage is kept and cited where it really is (folder `m54_fix`;
not deployed). gpt-5-mini at low effort: folder `mini_low`. Every faster setting loses on false refusals or critical
items, and low effort invents content where it should refuse; answers stay at gpt-5-mini, medium effort.

Before verification, gpt-5.4-mini's answers cite as well (92%) and match the evidence status better (81%), but it writes
fewer sentences (164 per run against 281) and more of its quotes are not word for word (8.5% of sentences, against 4.6%),
so the checks empty more answers. **gpt-5-mini stays the answer model**; a tolerant quote match is the next step before
switching. Cost for the medium run was recomputed from the logged tokens (its price was added after the run started).

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
