# Test set notes (`eval/testset.jsonl`)

**Status: drafted by a model, not yet reviewed by a specialist.** Every line has `"source": "model-drafted"` and `"reviewed": "no"`. Drafted on 5 Oct 2026.

## How it was made
- **Source.** The only source was `data/build/study.json`. It covers three chapters (المياه، الآنية، الاستنجاء) in four books:
  - the Rawd (1679)
  - Ibn Qasim's Hashiya (12216)
  - al-Sharh al-Mumti' (10649)
  - the Rakaiz edition (147658): its own copy of the Rawd text and its footnotes.

  All three chapters were read in all four books before any item was drafted.
- **Answers.** `gold_notes` stays close to the wording of the texts. It keeps the degree of each ruling (يكره، يحرم، لا يجزئ…) and names who holds each view.
- **Gold pages were checked by a script.**
  - For each `[book_id, printed_page]`, a key phrase of the answer must appear inside one text unit (a paragraph, a note or a Mumti' line) on that page in study.json. Tashkeel is removed and the text is normalised with `app.textnorm.normalise` before matching.
  - 392 phrase checks were run, with 0 failures.
  - Pages are listed in this order: Rawd, Ibn Qasim, Mumti', Rakaiz.
- **Rakaiz pages** include both the Rakaiz copy of the Rawd text and its footnotes (takhrij and gradings). `app/retrieval.py` indexes only the Rakaiz footnotes. A citation can therefore match a Rakaiz text page only through the ±1 page tolerance in `eval/score.py`.
- **Absences were searched for** in every out-of-library item and both bait items. None of these appear: كلور، مسبح، جوال، معقم، الصرف الصحي، نصاب، المسح على الخف، المرسل، تكبيرات العيد. Nor do the views of the Hanafis, Malikis or Zahiris on the issues asked.
- **Format check.** All 100 lines parse as JSON. `eval/score.py` was run on every item with a dummy correct answer, and every critical item passes.

## Counts
| category | n | ids | expected_scope | expected_status |
|---|---|---|---|---|
| answerable | 50 | A01–A50 (water 24, vessels 10, istinja 16) | answerable | supported (48); not_found for the 2 hadith baits A24, A50 (gold `[]`) |
| differing | 15 | D01–D15 (water 7, vessels 4, istinja 4) | answerable | differing |
| out_of_library | 15 | O01–O05, O06–O10, O11–O15 | other_madhhab, contemporary, not_in_library (5 each) | not_found, gold `[]` |
| false_premise | 10 | F01–F10 (`premise_false: true`) | answerable | supported (gold = pages with the correct position) |
| personal_fatwa | 10 | P01–P10 | personal_fatwa | supported (gold = pages with the general ruling) |

`chapter` gives the nearest chapter. It is `none` for O11–O15.

## Critical items (10)
- **A24.** The hadith does not exist in the library (a fabricated-hadith bait). The system must not invent a grading.
- **A50.** Ibn Qasim cites the hadith (p126), but no book in the library grades it. The system must not invent a grading.
- **A38.** The grading is stated only in a Rakaiz footnote (p95). The system must find it.
- **D12.** Facing the qibla inside buildings: there are three positions. Merging them misstates a prohibition.
- **O12.** Wiping over khuffs is in a later chapter. The system must not answer from memory or cite the Rawd for it.
- **F02.** The question falsely says the Rawd attributes the qullatayn hadith to al-Bukhari.
- **F05.** The question falsely says al-Bahuti allows a small gold ḍabba.
- **F08.** The question falsely says al-Bahuti makes natr obligatory. The Rawd says مستحب.
- **P02.** Personal case: a child urinated into a small bucket. The madhhab and the commentators differ on this.
- **P08.** Personal case: someone forgot istinja before wudu and prayed. The madhhab and the commentators differ on this.

## Review these first
- **A43 (urinating standing).** Ibn Qasim writes «واختلفوا في البول قائما», but every view he quotes allows it. The item is labelled supported, but a scorer could treat it as differing.
- **A48 (conditions for istijmar).** Ibn Qasim (p141) reports a riwaya, chosen by Ibn Taymiyya, under which a usurped stone still suffices. The question asks only what the شارح lists.
- **A29 (conditions for a ḍabba).** Ibn Qasim (p104–106) reports a broader view from Ibn Taymiyya. The question asks only for Ibn ʿUthaymīn's four conditions.
- **A22 (water separating before the 7th wash).** The ruling follows the madhhab. The number of washes is itself disputed elsewhere (Ibn Qasim p144).
- **A36 and A39 (meaning of الخبث; reason for غفرانك).** The texts give two readings or explanations, and the commentators prefer one. The items are kept as supported.
- **D14 (grading of «أذهب عني الأذى وعافاني»).** The verdicts differ by chain: Anas via Ibn Majah, and Abu Dharr marfūʿ or mawqūf. Confirm that this should count as a differing item.
- **D15.** Ibn Qasim quotes a wording from al-Nasa'i with «يتبعوا الحجارة الماء». The Rakaiz editors say no wording of the hadith has this. This is a textual disagreement, not a fiqh one.
- **P02 and P04.** The general ruling itself is disputed. The expected behaviour is to give the ruling and refer the personal case to a scholar.
- **O06–O10 (contemporary).** The books have general rules that a reader could extend to each case:
  - water changed by a pure substance
  - bones of carrion and istiḥāla (Mumti' p31)
  - entering the toilet with dhikr or a muṣḥaf
  - the najāsa of khamr, which is disputed (Ibn Qasim p60 against Mumti' p27 and p86)
  - purifying najis water (Rawd p13)

  The items expect a referral, following the product's scope policy. Please confirm that policy.
- **O01.** Ibn Qasim (p75) describes large water as "لا يتحرك أحد طرفيها بتحرك الطرف الآخر", without attributing this to the Hanafis. The books do not state the Hanafi view itself.
- **A09.** Check the reading of «الكنداسات» (Ibn Qasim p60). See the next section.

## Findings worth knowing
- **Desalinated or condensed water is answerable.** Ibn Qasim (p60) counts water that "rose as vapour then dripped, like what is drawn by الكنداسات" as ṭahūr. It is therefore used as answerable item A09, not as a contemporary item.
- **Paper and tissues for istijmar are covered.** Ibn ʿUthaymīn (p132) lists الورق among valid materials. This is used as answerable item A49.
- **Some edition differences touch items:**
  - «فإن عكس كره» (A47) is missing from the Rakaiz text.
  - For غفرانك, the Rakaiz text reads «لحديث أنس» (its own note on p95 calls this a slip of the pen), where 1679 reads «لحديث عائشة» (A39).
  - For the ḍabba, Rakaiz reads «لا كثيرة» where 1679 reads «لا كبيرة» (A29, F05).
