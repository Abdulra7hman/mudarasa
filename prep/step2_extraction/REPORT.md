# Step 2: Extraction and linking test, باب المياه (1 Oct 2026)

Throwaway test, not product code. Run: `python3 fetch_pages.py` (once), then `python3 analyse.py` (under 1 s).
Raw pages: `../books/<ID>/pages/`. Detailed results: `results/*.json`. Fetch log: `fetch_log.txt`.

## Data fetched
119 pages from Turath, 2 s apart, no failures: 1679 (9 pages), 147658 (19), 12216 (47), 10649 (44).

## Results

| Question | Result | Verdict |
|---|---|---|
| Q1. Does every page carry its printed volume and page? | 119/119 pages; all agree with each book's `page_map` | ✅ Solved |
| Q2. Can the matn be separated from the sharh in the Rawd (1679)? | Yes: the text inside `( … )`. Joined in order, it rebuilds the Zad matn | ✅ Solved for 1679 |
| Q2b. Same for Rakaiz (147658)? | Only partly. Parentheses also wrap quotations from other books and manuscript sigla; the formatting that distinguished matn in print is lost | ⚠️ Matn must be confirmed against the 1679 matn |
| Q3. Do Ibn Qasim's 222 notes link to the Rawd paragraph they comment on? | Every note links by at least one method. On the 184 notes both methods link, they agree on the same Rawd unit for 171 (93%) and on the same printed page for 178 (97%) | ✅ Good; precision still to be confirmed by the specialist |
| Q4. Does al-Sharh al-Mumti' link through its lemma headings? | 29/29 lemma headings link (26 exact, 3 fuzzy). The 2 unlinked headings are chapter titles. The body also has 80 «قوله» quotes for finer links | ✅ Solved |
| Q5. Can the two Rawd editions be aligned? | 93 aligned units: 74 identical after normalising, 19 with word differences, 11 blocks of differing matn | ✅ Works; feeds the edition comparison |

### How the linking works (the method we'll build on 4 Oct)
- **Unit:** one matn segment `( … )` plus the sharh that follows it. Units are the study paragraphs.
- **Ibn Qasim, two independent methods:**
  - (A) the words just before a note marker `(١)`, searched in the Rawd after normalising (exact, then fuzzy by word coverage ≥ 0.75);
  - (B) Ibn Qasim's own reprinted matn sequence aligned to the Rawd's matn sequence.
  
  Where they disagree, it is almost always the neighbouring unit on the same page.
- **Mumti':** a heading quotes a stretch of matn continuously, so it is searched in the Rawd's matn stream with the sharh removed.

## Things we learned that change the plan
1. **The anchor e-text (1679) has no footnotes.** The hadith referencing by عبد القدوس نذير that the edition advertises is missing from Shamela's copy. **Rakaiz (147658) has it:** 12 hadith-referencing notes with gradings (e.g. «وجوَّد إسناده يحيى بن معين، وصححه ابن منده») and 13 manuscript-variant notes («في (أ) و(ب): …»). Our rule "a hadith grading only from the library" therefore depends on Rakaiz, so it should be approved as a citable source, not only as support.
2. **The two editions really differ.** In 19 of 93 aligned units the wording differs, and 1679's own notes warn its e-text came from another printing. The edition comparison has real content to show.
3. **Ibn Qasim's reprint of the Rawd differs slightly from 1679** (e.g. «ليس بنجاسة» vs «ليس نجاسة»). The quote check must compare against the cited book's own text, never the anchor's.
4. **No embeddings are needed for linking in these books.** Exact or fuzzy text matching plus structural alignment covered every note.

## Limits of this test
- One chapter only (باب المياه), 4 books.
- The precision numbers are agreement between two methods, not a human check. **Next:** the specialist labels `linking_sample_50.csv` (50 random Ibn Qasim notes, seed 42) by filling the `correct` column. That gives the precision figure for the results slide.
- Units that cross a page boundary are credited to their start page.
- Footnotes can continue onto the next page. None in Ibn Qasim's sample, but Rakaiz does it (e.g. the takhrij of the قلتين hadith, ج١ ص٧٤ → ٧٥, continuation marked «=»). Ingestion must join them.
- Turath text is Shamela's e-text; page numbers are the publisher's, but wording may not match the print exactly (stated for 1679).
