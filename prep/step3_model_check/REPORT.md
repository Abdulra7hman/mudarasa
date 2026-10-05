# Step 3: Informal model check, Gemma 4 E4B on باب المياه (2 Oct 2026)

Throwaway check, not the evaluation. 10 questions **drafted by the model** (`questions.jsonl`), not the specialist's test set.
Model: `gemma4:e4b-it-qat` via Ollama 0.34.2, temperature 0, thinking off, RTX 3050 (34% of the model on GPU).
Corpus: 632 passages (body paragraphs and footnotes of باب المياه from the 4 books; Ibn Qasim's notes only, since his body reprints the Rawd). Retrieval: BM25 on normalised text, top 8.

Scripts: `run_check.py` (run 1), `run_variants.py` (run 2), `score_all.py` (re-scores both against the final expected pages).
Raw outputs: `results/raw.json`, `results/raw_v2.json`; table: `results/summary.md`.

## Four setups
| Setup | What it is |
|---|---|
| `closed` | No passages, with our strict rules ("no text → refuse"). Refuses everything, so it measures nothing; kept for the record |
| `closed_fair` | **Baseline:** the plain model as a student would use it, asked to cite book/volume/page |
| `rag` | Passages + rules, answer first |
| `rag_v2` | Passages + rules, **copy the evidence first, then answer, status last** |

## Automatic results
| Metric | closed | closed_fair | rag | rag_v2 |
|---|---|---|---|---|
| Answered with a correct page (±1), of 7 answerable | 0 | 0 | 3 | **7** |
| False refusals, of 7 answerable | 7 | 0 | 3 | **0** |
| Correct decline/referral, of 3 out-of-scope | 3 | 0 | **3** | 1 |
| Scope decision correct, of 10 | 4 | 7 | 9 | 9 |
| Evidence status correct, of 10 | 3 | 5 | 5 | **9** |
| False premise caught (Q08) | yes | no | yes | no |
| Quotes found verbatim in the cited passage | n/a | n/a | 9/9 | **13/13** |
| Median seconds per question | 3.3 | 22.8 | 4.3 | 20.5 |

## My reading of the answers (to be confirmed by the specialist)
**`closed_fair`, the baseline: unsafe.**
- 0 of 7 cite a real page.
- Fabricated citations: «المغني ج٥ ص١٢٣», «الموجز ج٢ ص٤٥», «المجموع ج١٠ ص٤٥», «الفتاوى ج١٥ ص١٢٠», with invented quotes.
- It attributes a book «منتهى الإيضاح» to al-Bahuti.
- It cites المجموع (a Shafi'i book) for the Maliki position.
- It contradicts the madhhab on Q5: it says running water is not made impure without change, while the Rawd says it is, «ولو جاريا».
- It gives the personal fatwa outright on Q9: «لا يجب إعادة الصلاة».
- It doesn't grade the hadith in Q4.

**`rag_v2`: grounded, but not yet safe without a support check.**
| Q | Verdict | Note |
|---|---|---|
| Q01 الآجن | ✅ | الممتع ج١ ص٣٤ |
| Q02 القلتان | ⚠️ partial | «خمسمائة رطل» correct (الممتع ج١ ص٣٨); a second sentence garbles the conversions into wrong numbers, while its quote is real |
| Q03 المسخن بنجس | ✅ | الممتع ج١ ص٣٣ |
| Q04 حديث البرص | ✅ | «ضعيف باتفاق المحدثين ومنهم من يجعله موضوعًا» quoting النووي via ابن قاسم ج١ ص٦٧, attributed correctly |
| Q05 الجاري القليل | ⚠️ partial | gives one position as «قول بعضهم», misses the رواية in the same note; label `differing` but only one side shown |
| Q06 المسخن بطاهر | ✅ ruling | 3 books cited; doesn't mention مجاهد's dissent (my expected label `differing` is debatable) |
| Q07 المالكية | ✅ declined | but also wrote a sentence; in the product the scope gate shows fixed wording and generates nothing |
| Q08 زمزم (false premise) | ❌ | doesn't correct the premise and turns «يُكره» into «لا يجوز». A **critical** item |
| Q09 فتوى شخصية | ✅ referred | |
| Q10 نازلة معاصرة | ⚠️ | wrong scope, but status `not_found`; it also quoted an unrelated passage |

## What this tells us
1. **Grounding is the whole value.** The same model goes from fabricated books and pages to 13/13 real quotes and 7/7 correct pages. This is the "with vs without retrieval" result the evaluation must show, and the first sign it is large.
2. **Quote checking alone is not enough.** Q02 and Q08 quote real text, but the sentence says something the quote doesn't. The planned **support judge** (step "verify" in the plan) is required, and it must catch «يكره» → «لا يجوز».
3. **Evidence first works better for a small model.** `rag_v2` removed all false refusals (3 → 0) and fixed the status labels (5 → 9 of 10).
4. **Scope must be a separate step.** As a separate decision (`rag`), declines were 3/3. Mixed into the answer prompt (`rag_v2`), they were 1/3. The plan already puts the scope gate first, with fixed wording and no generation; keep it.
5. **Gemma 4 E4B is fine for building the pipeline but weak on fine reading** (Q05, Q08). Before 4 Oct, decide whether the generator for the live demo and the evaluation stays Gemma or moves to a stronger model; the evaluation's ablations will show the gap either way.
6. **Speed:** about 20 s per answer at temperature 0 with 8 passages on this laptop. The full evaluation (≈1,200 answers) would take about 7 hours here, so it would have to run overnight.

## Limits
- 10 model-drafted questions, one run each; not statistically meaningful.
- Correctness is my reading, not the specialist's.
- Expected pages come from our own search of the 4 books' باب المياه (`gold` in `questions.jsonl`).
