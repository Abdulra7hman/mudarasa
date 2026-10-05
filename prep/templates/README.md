# Templates for the Shari'a specialist

Fill these in Excel or Google Sheets (CSV) or Word (policy). I convert them to the repo formats
(`policy/answer_policy.md`, `eval/testset.jsonl`, `library/approved.json`).

## 1. `answer_policy.md`: the answer policy (one page)
Replace every line marked [مقترح] with the exact final wording, or approve it and delete the mark.

## 2. `testset_template.csv`: the test set (100 questions; 60 is the minimum)
The 5 rows are **examples only**. Page numbers in them are placeholders, not checked.

| Column | Values | Meaning |
|---|---|---|
| id | T001… | Unique |
| category | answerable (50) · differing (15) · out_of_scope (15) · false_premise (10) · fatwa (10) | Question type |
| critical | yes / no | About 10 items; each must pass (fabricated-hadith bait, wrong attribution, personal fatwa) |
| question | Arabic text | As a student would ask it |
| anchor_chapter | باب المياه / باب الآنية / باب الاستنجاء | Chapter it belongs to (empty if out of scope) |
| expected_behavior | answer · refuse · refer · correct_premise | What the system should do |
| expected_status | supported · partial · differing · not_found | Expected evidence label |
| gold_book_id | Turath ID from `books/CATALOG.md`; several joined with `\|` | Where the answer is |
| gold_vol, gold_page | Printed volume and page; several joined with `\|` | Scored ±1 page |
| gold_quote | Short exact quote from the page | Optional, helps checking |
| positions | For `differing`: `قائل: قول (كتاب ج ص)` separated by `;` | Each position, attributed |
| gold_notes | 1–3 lines | What a correct answer must contain |
| author, reviewed | name · yes/no | Who wrote it; has the specialist checked it |

## 3. `library_approval.csv`: the library list
One row per book. The specialist sets `approved` to yes or no. Only `yes` books can be cited.
