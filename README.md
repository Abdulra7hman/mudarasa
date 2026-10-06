# مدارسة · Mudarasa

**ادرس «الروض المربع» مع شروحه، وكل جملة بنصها وصفحتها.**
*Study al-Rawd al-Murbi' with its commentaries: every sentence comes with its text and page.*

العرض الحي (Live demo): https://mudarasa.azurewebsites.net · المسار: تحدي الذكاء الاصطناعي في خدمة المحتوى الإسلامي ٢٠٢٦، المسار الرابع

---

## بالعربية

### ما هي مدارسة؟
مدارسة رفيق دراسة لطالب العلم في «الروض المربع»:
- **عرض الدراسة:** كل فقرة من الكتاب بجوار ما قاله الشراح عليها، مع الجزء والصفحة ورابط الصفحة في تراث:
  - حاشية ابن قاسم
  - الشرح الممتع لابن عثيمين
  - طبعة ركائز المشكولة، وحواشي محققيها، والفروق بين الطبعتين
- **اسأل:** جواب كل جملة فيه مأخوذة من نص في الكتب المعتمدة مع اقتباسه الحرفي.
  - نتحقق آليًّا من وجود الاقتباس في الصفحة، ثم يتحقق نموذج ثانٍ من أن الاقتباس يدل على الجملة. ما لم يثبت يُحذف، ويُعرض عليك أنه حُذف.
  - على كل جواب حالة الدليل: مؤيد بالنص، مؤيد جزئيًّا، أقوال مختلفة (دون ترجيح)، لم يوجد نص.
- **الامتناع والإحالة:** لا نفتي في الحالات الشخصية؛ نذكر ما في الكتاب عمومًا ونحيل إلى مفتٍ. ولا نجيب عن المذاهب الأخرى ولا النوازل التي لا تتناولها الكتب.

### إضافات (تجريبية)
- استماع إلى المتن والشرح بصوت عربي مع إبراز الكلمة المقروءة.
- أدوات مذاكرة موثقة: ملخص، وأسئلة، وبطاقات.
- حفظ المتن بالتسميع الصوتي: تظهر الكلمات كلما نطقتها صحيحة، وتُعلَّم الأخطاء.
- معنى الكلمة من حواشي الكتب.
- التخريج كما نصّ عليه المصدر، مع رابط للبحث في الدرر السنية.
- مراجعة متباعدة للبطاقات.
- دفتر يُصدَّر بمراجعه.

### الواجهة: ما الحقيقي وما التوضيحي
- **حقيقي يعمل على الكتب:** الكتب الأربعة من عائلة «الزاد» في الأبواب الثلاثة (القراءة، والفهرس، والاستماع، والمعاني، والتخريج)، والمحادثة الموثقة، وتسميع متن الزاد، وملخصات الأبواب.
- **بيانات توضيحية لعرض النظام كاملًا:** بقية كتب المكتبة، والإحصاءات والتحليلات، والبطاقات والتقييدات المعدّة مسبقًا، وسجل المحادثات الأولي. ما لم يُبنَ بعد يظهر عليه «ضمن الإصدارات القادمة».

### ما تم وما بقي
| تم | التالي |
|---|---|
| ثلاثة أبواب من كتاب الطهارة: المياه، الآنية، الاستنجاء؛ أربعة كتب | بقية كتاب الطهارة ثم الكتاب كاملًا |
| ربط آلي للحواشي بالفقرات (طريقتان تُقارنان) | مراجعة الربط من مختص (عينة ٥٠ جاهزة) |
| التحقق من الاقتباس + نموذج تحقق ثانٍ | اعتماد المختص لسياسة الإجابة والمكتبة |
| تقييم قابل للإعادة بأمر واحد | كتب اللغة (المصباح المنير) ومعجم الجذور |

---

## In English

### What it does
- **Study view:** each paragraph of the anchor book beside what the commentaries say on it, each with volume, page and a link to the page on Turath:
  - Ibn Qasim's Hashiya
  - al-Sharh al-Mumti'
  - the vocalized Rakaiz edition, its editors' takhrij, and the differences between the two editions
- **Ask:** cited answers. Every sentence carries a word-for-word quote.
  - The quote must exist on the cited page, and a second model must agree that the quote supports the sentence. Otherwise the sentence is removed, and the user sees that it was removed.
  - Every answer shows an evidence status.
- **Refusal and referral:** personal fatwas, other madhhabs, and contemporary issues the books don't cover.
- **Additions (experimental):** listen (neural Arabic voice with word highlighting), cited study tools, matn memorization by recitation, word meanings from the commentaries, takhrij as stated by the source, spaced repetition, notebook export.

### Architecture
```
data/books (Turath JSON, server only) ─► app/ingest.py ─► data/build/study.json  (paragraphs, linked notes, editions)
                                                     └─► app/retrieval.py   (BM25 + embeddings, reciprocal-rank fusion)
question ─► scope gate (mini model) ─► retrieval ─► evidence-first answer (main model) ─► quote check ─► support judge (mini)
         ─► evidence status ─► FastAPI ─► web/index.html (the team's design, connected by scripts/build_ui.py)
```
| Part | What it uses |
|---|---|
| Models | Azure OpenAI gpt-5-mini (answers and judge) and text-embedding-3-small, set in `.env` and switchable |
| Fallback | If the model is unreachable, search-only mode: the cited passages, with no generated answer |
| Speech | Azure AI Speech |
| Hosting | Azure App Service |

### The interface: what is real, what is illustrative
The interface is the team's design (`design/madarasa.html`, exported from Claude Design). `python -m scripts.build_ui` writes
`web/index.html`: the design unchanged, plus integration code that connects it to the backend.
- **Real, on the books:** the four Zad-family books in the three chapters (reading with a table of contents, listening from any
  word, word meanings, takhrij from footnote numbers), the cited chat, Zad matn recitation, and chapter summaries.
- **Illustrative data, to show the whole system:** the rest of the library, statistics and insights, the prepared cards and
  notes, and the starting chat history. Parts not built yet open a "coming in a later release" notice.
- The earlier interface is kept at `/v2`.

### Run it
```bash
make setup                   # venv + dependencies
python -m scripts.fetch_books  # books from Turath into data/books (slow, once)
make ingest                  # build data/build/study.json (prints linking stats)
cp .env.example .env         # fill in the Azure keys
make test                    # unit tests (linking, pipeline rules, recitation matching)
make run                     # http://127.0.0.1:8000
```
Optional builds: `python -m scripts.build_tools` (study tools), `python -m scripts.build_tts` (recordings),
`python -m scripts.build_ui` (the interface, from `design/madarasa.html`).

### Evaluate it
```bash
make eval RUNS=3             # full pipeline and no-retrieval baseline, 3 runs; no-verification scored from the same answers
make report                  # table: mean (min–max) per system
python -m scripts.model_check "azure:gpt-5.4:low" "azure:gpt-5.4-mini:low"   # model choice on the quick set
```
- **Test set:** `eval/testset.jsonl`, 100 items.

  | Category | Items |
  |---|---|
  | Answerable | 50 |
  | Differing positions | 15 |
  | Out of library | 15 |
  | False premise | 10 |
  | Personal fatwa | 10 |

  The set is model-drafted from the texts, with gold pages checked by text search. It still needs specialist review; see `eval/TESTSET_NOTES.md`.
- **Results:** `eval/REPORT.md`. Errors and their fixes: `eval/ERRORS.md`.

### Limits (stated, not hidden)
- The library is three chapters and four books.
- The linking is automatic and hasn't been hand-checked yet.
- The test set is model-drafted.
- The judges are models: they reduce unsupported sentences but cannot guarantee their absence. The user always gets the page to check.
- gpt-5-mini both writes the answers and judges them. It's a separate, strict call, but a different judge model would be stronger. gpt-5.4 and gpt-5-nano had no quota on the new subscription.
- The live search uses keywords plus Azure embeddings (95% gold page in the top 8). Local BGE-M3 reaches 99% but needs a larger server.
- Hadith gradings are shown only as a library book states them.
- Recitation checking depends on speech recognition of classical Arabic, so treat its mistake flags as hints.
- See [STARTING_POINT.md](STARTING_POINT.md) for what existed before the build window.
- See [SOURCES.md](SOURCES.md) and [CONTENT.md](CONTENT.md) for sources, rights and checking.
