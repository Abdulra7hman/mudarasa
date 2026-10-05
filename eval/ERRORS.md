# Error log: failure → cause → fix

Every fix below was found by the evaluation, made in a commit, and measured again.
Results folders: `eval/results/v1_before_fixes` (1 run, commit 38b7f4c) and `eval/results/main_v2_gpt5mini` (3 runs, commit f447b7c).

## Fixed after the first full run (v1 → v2)
| Failure (v1) | Cause | Fix | Effect (v2, mean of 3 runs) |
|---|---|---|---|
| Disagreement never shown: 0% of the differing items | The attribution check («وقيل»، «روايتان»…) was built by normalising the whole pattern, which stripped the `\|` separators, so it never matched, and every «أقوال مختلفة» was downgraded | f447b7c: each marker normalised separately | 0% → **62%** |
| Personal fatwas not referred: 60% | The scope gate treated first-person questions («عندي إناءان…»، «استجمرت بحجرين…») as general | f447b7c: clearer gate rules with examples, plus a first-person check (9/9 flagged questions are personal; no false flags on the other 90) | 60% → **100%** |
| A modern product answered instead of referred (O07, bone-china porcelain) | The gate didn't count modern products as contemporary | f447b7c: modern products listed in the gate rules | Correct refusals 94% → **100%**; invented content where refusal is expected 7% → **0%** |
| F08 stopped with an error | Azure's default content filter blocked an istinja question («نتر الذكر») | f447b7c: the app shows the cited passages and explains instead of failing | Error → handled. **Still a critical failure:** fixing it needs a custom guardrail with higher thresholds in Foundry |

## Fixed on the 10-item quick set before the first full run
| Failure | Cause | Fix |
|---|---|---|
| An empty answer (Q05) | With medium reasoning effort, the reasoning used up the whole output allowance | 8d6fa3b: allowance raised |
| The Zamzam page never retrieved (Q08) | Long Rawd paragraphs hid a specific issue, and fusion diluted a strong match on a rare word | 8d6fa3b: the Rawd searched unit by unit; the top keyword and dense hits keep a guaranteed place |
| Off-topic sentences kept («اليقين»، «ثخن بتراب») | The judge saw only the sentence and the quote | 8d6fa3b: the judge also sees the question and the quote's context, with a relevance rule |
| The definition of «الطهور» given to «الطاهر» | The judge couldn't see which term the quote defines | 8d6fa3b: context around the quote |
| A faithful paraphrase rejected (لم يكره → غير مكروه) | The judge was too literal | 8d6fa3b: equivalent wording accepted |

## Still failing in all 3 runs of v2
| Item | What happens | Cause | Next |
|---|---|---|---|
| A04, A20, F03, P02, P08 | No gold page cited | **Search:** no gold page among the 8 passages | Give the model 12 passages; query expansion |
| F04 | A wrong passage cited | **Search:** the Rawd page on sun-heated water isn't in the top 8 | Same |
| D05, D11 | The disagreement isn't shown | **Model:** the passages contain both positions, but gpt-5-mini answers with one | A stronger answer model, with gpt-5-mini as the judge (quota pending) |
| F09 | The false premise is accepted | **Model** | Same |
| F08 ⚠ | Blocked | **Content filter** | A custom guardrail in Foundry |

Items failing in only 1 or 2 of the 3 runs (D03, D13, D14, F02, A16, D01, D02, D07, D09, D15, F01, F07) are run-to-run variation. GPT-5 models take no temperature setting.
