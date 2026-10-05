# Mudarasa: UI design brief (for Claude Design)

Design the **Chat (اسأل)** screen first. The other screens come after, in the same style.
Everything below matches what the app's backend already sends, so every element you design can be built.

## 1. Brand (from the pitch deck, slide 14)
| Token | Colour | Use |
|---|---|---|
| Navy | `#0F1640` | Header bar, logo, headings, main text |
| Cream | `#ECE8DE` | Page background |
| Paper | `#FBF8F1` | Cards, answer area, book text |
| Teal | `#0B7461` | Buttons, links, active tab, citation chips |
| Bright teal | `#2EE6C0` | Logo icon on navy, small highlights |
| Status: green / amber / teal / red | (choose shades) | The 4 evidence statuses (section 3) |

**Fonts**
- Logo and headings: a geometric Kufi like the deck (e.g. *Reem Kufi*).
- Book text and quotes: Naskh with full tashkeel (*Amiri*).
- Interface: *IBM Plex Sans Arabic*.

**Rules**
- RTL, phone first (360–420 px wide), and also usable on desktop.
- Light and dark mode.
- Font-size control (أ− / أ+) and a tashkeel toggle (التشكيل: ظاهر / مخفي).
- One disclosure line, always visible: «مدارسة أداة مدعومة بالذكاء الاصطناعي، وليست عالمًا ولا مفتيًا. تحقق من النص بفتح المصدر.»
- No login.

**Navigation** (keep the deck's tab bar; the additions carry a small «تجريبي» label):
الدراسة · **اسأل** · استماع · أدوات المذاكرة · الحفظ · المراجعة · دفتري

## 2. Chat screen: states to design
**A. Empty**
- The promise line, e.g. «الإجابة من النصوص المحققة فقط».
- 3 suggested questions, each with a small type tag:
  - «ما حكم الماء الآجن، وهو المتغير بطول مكثه؟» *جواب موثق*
  - «ما الفرق بين الطاهر والطهور؟» *أقوال واختلاف*
  - «ما حكم الوضوء بماء البحر عند المالكية؟» *خارج النطاق*
- Input box: placeholder «اكتب سؤالك عن أبواب المياه والآنية والاستنجاء…», and a send button.
- **Optional context bar**, when the question is asked from a paragraph in the study view: «السؤال عن فقرة الروض، ج١ ص٩: «…أول الفقرة…»» with ✕ to remove it.

**B. Waiting.** This takes 20–40 s, so design it as a real state, not a spinner.
- Stage line with a seconds counter:
  1. «يبحث في الكتب…»
  2. «وجد النصوص، ويكتب الجواب منها…»
  3. «يتحقق من كل جملة واقتباسها…»
- **After about 3 s the found passages appear:** about 8 items, each showing book name, volume and page, type (متن وشرح / حاشية ابن قاسم / الشرح الممتع / حاشية ط ركائز), the passage text, and «افتح الصفحة». The student can read them while waiting.

**C. Answer** (user bubble + answer card)
- **Evidence-status badge**, always shown, one of four:
  - «مؤيَّد بالنص»
  - «مؤيَّد جزئيًّا: حُذف ما لم نجد له نصًّا»
  - «أقوال مختلفة: عُرض كل قول منسوبًا إلى قائله دون ترجيح»
  - «لم يوجد نص»
- **Optional message line** above the sentences, one of:
  - false premise: «لم أجد في الكتاب ما يدل على ما ورد في السؤال؛ والذي فيه:»
  - personal case: «لا تصدر مدارسة فتوى في الحالات الشخصية. هذا ما ذكره الكتاب في المسألة عمومًا، ولحالتك يُرجى سؤال مفتٍ مؤهل.»
- **2–5 sentences.** Each ends with a **citation chip**, e.g. «الروض المربع (ط الرسالة)، ج١ ص٩».
  - Tapping a chip opens that passage with the quote **highlighted**.
  - In «أقوال مختلفة», each position is attributed: «وقيل: …», «قال ابن قاسم: …».
- **Collapsed «حُذفت ٢ من الجمل لأن توثيقها لم يثبت».** Each removed sentence shows its reason:
  - «الاقتباس غير موجود حرفيًّا في المقطع»
  - «الاقتباس لا يدل على الجملة: …»
  - «رقم المقطع غير صحيح»
- **Collapsed «النصوص التي قُرئت للجواب (٨)»,** with the quote highlighted inside its passage.
- **Actions:** «أضف إلى دفتري», «بلّغ عن خطأ».
- **Small meta:** «٣٢ ثانية», or «جواب محفوظ» for a cached answer.

**D. Refusal card** (other madhhab / contemporary issue / outside the books). No sentences, only the fixed wording, like the deck's beige card. Examples:
- «مدارسة مخصصة لدراسة الروض المربع وشروحه في المذهب الحنبلي، ولا تشمل كتب المذاهب الأخرى. يُرجى الرجوع إلى كتب ذلك المذهب أو أهل العلم به.»
- «هذه مسألة معاصرة لم تتناولها الكتب المعتمدة في مدارسة. يُرجى الرجوع إلى جهات الفتوى المعتمدة.»

**E. Fallbacks**
- Search-only mode (model unreachable): a message plus the passages.
- Content filter: a message plus the passages.
- Too many questions: «عدد كبير من الأسئلة في دقيقة واحدة…».

## 3. A real answer to design with
Question: «هل يطهر جلد الميتة بالدباغ؟». Status: **أقوال مختلفة**.
1. لا يطهر جلد الميتة بالدباغ. — *الشرح الممتع لابن عثيمين، ج١ ص٧٦*
2. قال المؤلف كما نقله الشارح: «فإذا دُبغ جلد الميتة فإن المؤلف يقول: إنه لا يطهر بالدباغ.» — *الشرح الممتع، ج١ ص٧٦*
3. وقيل: «إن جلد الميتة لا يطهر بالدباغ؛ إلا أن تكون الميتة مما تحله الذكاة…» — *الشرح الممتع، ج١ ص٧٧*
4. وقال ابن قاسم: «ولو جف ولم يستحل لم يطهر». — *حاشية الروض لابن قاسم، ج١ ص١٠٧*

Passages read: 8. Dropped: 0. Time: 38 s.

## 4. Later screens (same style), for reference
| Screen | Contents |
|---|---|
| **الدراسة** | Chapter tabs. Paragraphs of the Rawd with the matn in colour, each with a page tag and counts. Opening a paragraph shows tabs for حاشية ابن قاسم / الشرح الممتع / طبعة ركائز والفروق / التخريج. Words are tappable for their meaning (popover). Buttons: «اسأل عن هذه الفقرة», «استمع», «أضف إلى دفتري» |
| **استماع** | Sticky player (play, previous, next, mode: المتن والشرح / مع الحواشي / المتن فقط, speed), with the paragraph and word being read highlighted |
| **الحفظ** | One matn line with hidden words, a 🎙 button, words revealing in green as recited, mistakes in red or orange, a score |
| **أدوات المذاكرة** | Per section: a cited summary, a multiple-choice quiz with explanation, flashcards |
| **المراجعة** | A card with «أظهر الجواب», then 4 grade buttons |
| **دفتري** | Saved items with citations; export Markdown / print |

## 5. What to send back
- Screenshots or an exported HTML of the chat screen, all states A–E, phone and desktop, light and dark if you can.
- The code is plain HTML/CSS/JS (no React), so exact colours, sizes and spacing are what matter most.
