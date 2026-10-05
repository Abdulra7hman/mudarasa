# Content and sources: how Mudarasa uses and checks them

## The library
Mudarasa only cites the approved library. Today that is four books in three chapters of كتاب الطهارة:
- باب المياه
- باب الآنية
- باب الاستنجاء

The books, editions and terms are listed in [SOURCES.md](SOURCES.md).

| Book | Role | What we use |
|---|---|---|
| الروض المربع (ط الرسالة، 1679) | Anchor: the study text | Paragraphs, the matn of Zad inside `( … )`, printed volume and page |
| الروض المربع (ط ركائز، 147658) | The same book in a vocalized edition | Vocalized text (for listening and memorization), the editors' footnotes (takhrij with gradings, manuscript variants), differences between the editions |
| حاشية الروض المربع لابن قاسم (12216) | Direct commentary (hashiya) | His footnotes, each linked to the word of the Rawd it explains |
| الشرح الممتع لابن عثيمين (10649) | Direct commentary on the matn | Its sections, each linked to the matn it quotes |

Linking is automatic. Each Ibn Qasim note is linked twice and the two methods are compared:
- by the words its marker sits on
- by the order of the matn

The linking statistics are in `data/build/stats.json`, and the hand-check sheet comes from `make label-sheet`.
**No specialist has reviewed the links yet.** The app says so, and low-confidence links are marked.

## How an answer is checked (every answer, every time)
1. **Scope gate.** A separate model call classifies the question. Another madhhab, a contemporary issue the books don't
   discuss, or an unrelated topic gets fixed wording, and nothing is generated.
2. **Search.** The open paragraph's own commentary comes first, then hybrid search over the library: keywords plus embeddings.
3. **Answer, evidence first.** Every sentence must carry a passage number and a quote copied word for word.
4. **Quote check.** The quote must exist in the cited passage, after normalising tashkeel and hamza forms. If not, the
   sentence is removed.
5. **Support judge.** A second, cheaper model reads each sentence and its quote. If the quote doesn't say what the
   sentence says, the sentence is removed. This covers a changed ruling (يكره → يحرم), an added condition, or a wrong attribution.
6. **Evidence status.** It is recomputed from what survives and shown on every answer:

| Status | Shown as |
|---|---|
| supported | «مؤيَّد بالنص» |
| partial | «مؤيَّد جزئيًّا: حُذف ما لم نجد له نصًّا» (removed sentences stay visible, with the reason) |
| differing | «أقوال مختلفة: عُرض كل قول منسوبًا إلى قائله دون ترجيح» |
| not_found | «لم يوجد نص», a refusal and a referral |

The study tools (summaries, quiz questions, flashcards) go through steps 3–5 too. Word meanings and takhrij are not
generated: they are copied from the books, with their page.

## Mapping to the four content levels (المرجعية والحزمة العلمية)
| Level | Scope (organizers) | What Mudarasa does |
|---|---|---|
| (أ) معلومات أصلية مستقرة | Quran, sound hadith, settled basics | Shows the book's own text and its page. Hadith gradings are shown **only as the library states them**, attributed, never decided by the system. Plus a link to search Dorar |
| (ب) شرح وتعريف واستدلال | Concepts, definitions, reasoning | Answers from the library with the reference shown on every sentence. Word meanings come from the commentaries' own glosses. Status «مؤيَّد» or «مؤيَّد جزئيًّا» |
| (ج) مسائل خلافية أو عالية الحساسية | Disputed fiqh, sensitive issues | «أقوال مختلفة»: each position attributed, no system verdict. Other madhhabs and contemporary issues outside the library get a referral |
| (د) فتوى أو حالة شخصية | Individual cases | No ruling on the person's case. States what the book says in general, with citations, and refers to a qualified mufti: «لا تصدر مدارسة فتوى في الحالات الشخصية…» |

## Fixed wording
The refusal, referral, status and disclosure wording comes from the draft answer policy (`policy/answer_policy.md`).
It is marked [مقترح] until a specialist approves it.

## Reporting a problem
Every answer has «بلّغ عن خطأ». Reports go to `data/logs/reports.jsonl` for review, without personal data.
The evaluation's error log (`eval/ERRORS.md`) links each failure to its cause and to the commit that fixed it.

## Privacy
- No accounts.
- Logs keep the question text and measurements (status, latency, tokens, cost), never IP addresses or identifiers.
- Recitation audio goes to Azure Speech (or the browser's own recogniser) to become text, and is not stored by Mudarasa.
- The notebook and review cards stay in the user's browser.
