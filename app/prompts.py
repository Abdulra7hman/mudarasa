"""Prompts, output schemas and fixed wording.

From prep: RULES and SCHEMA (step3 run_check), RULES_V2/SCHEMA_V2/CLOSED_FAIR (run_variants), SCOPE_RULES and
EXTRA_RULES (demo server). Fixed user-facing wording is the draft in policy/answer_policy.md ([مقترح]).
New: the support judge, the general-statement mode for personal-fatwa questions, the study-tools prompt.
"""

SCOPE_ENUM = ["answerable", "other_madhhab", "contemporary", "personal_fatwa", "not_in_library"]
STATUS_ENUM = ["supported", "partial", "differing", "not_found"]

SENTENCES = {"type": "array", "items": {"type": "object", "properties": {
    "text": {"type": "string"}, "passage": {"type": "string"}, "quote": {"type": "string"}}}}

SCHEMA_ANSWER = {"type": "object", "properties": {
    "scope": {"type": "string", "enum": SCOPE_ENUM},
    "premise_correct": {"type": "boolean"},
    "evidence": {"type": "array", "items": {"type": "object", "properties": {"passage": {"type": "string"}, "quote": {"type": "string"}}}},
    "sentences": SENTENCES,
    "status": {"type": "string", "enum": STATUS_ENUM}}}

SCHEMA_CLOSED = {"type": "object", "properties": {
    "scope": {"type": "string", "enum": SCOPE_ENUM}, "premise_correct": {"type": "boolean"},
    "status": {"type": "string", "enum": STATUS_ENUM},
    "sentences": {"type": "array", "items": {"type": "object", "properties": {
        "text": {"type": "string"}, "book": {"type": "string"}, "vol": {"type": "string"}, "page": {"type": "string"},
        "quote": {"type": "string"}}}}}}

SCHEMA_SCOPE = {"type": "object", "properties": {"scope": {"type": "string", "enum": SCOPE_ENUM}}}

SCHEMA_JUDGE = {"type": "object", "properties": {"verdicts": {"type": "array", "items": {"type": "object", "properties": {
    "i": {"type": "integer"}, "supported": {"type": "boolean"}, "why": {"type": "string"}}}}}}

RULES = """أنت شريك دراسة لطالب علم يدرس «الروض المربع» في المذهب الحنبلي.
القواعد:
1. صنّف السؤال في scope: answerable إن كان عن مسائل الكتاب ومذهب الحنابلة؛ other_madhhab إن سأل عن مذهب آخر؛ contemporary إن كان نازلة معاصرة؛ personal_fatwa إن سأل عن حالته هو؛ not_in_library إن لم يكن في النصوص ما يجيب.
2. إن كان في السؤال نسبة قول إلى المؤلف لم يقله فاجعل premise_correct = false وصحّح ذلك من النص.
3. كل جملة فيها حكم أو دليل أو نسبة قول أو حكم على حديث يجب أن تُوثَّق باقتباس حرفي منسوخ كما هو من النص (quote).
4. لا تذكر شيئًا من معرفتك الخاصة. إن لم تجد نصًّا فاجعل status = not_found ولا تكتب جملًا.
5. إن اختلفت الأقوال فاذكر كل قول منسوبًا لقائله، ولا ترجّح، واجعل status = differing.
6. لا تُفتِ في الحالات الشخصية.
أجب بالعربية."""

RULES_V2 = RULES + """
طريقة العمل:
أ. حدّد scope أولًا.
ب. في evidence انسخ حرفيًّا كل عبارة من النصوص تتعلق بالسؤال، مع رقم مقطعها. اقرأ المقاطع كلها، وكذلك الحواشي.
ج. اكتب sentences: جواب السؤال نفسه فقط، كل جملة مع اقتباسها ورقم مقطعها. لا تذكر ما لا يتعلق بالسؤال.
د. أخيرًا status: supported إن أجابت النصوص؛ differing فقط إن نقلت النصوص قولين مختلفين في المسألة نفسها؛ not_found إن كانت evidence فارغة.
هـ. إن سأل الطالب عن أمرين (كالفرق بين شيئين) فاذكر كلًّا منهما من النصوص.
و. لا تكتب أرقام المقاطع داخل نص الجملة؛ ضعها في passage فقط، مثل P3.
ز. الاقتباس quote يُنسخ من المقطع نفسه حرفًا بحرف، ولا يُختصر ولا يُعاد صياغته. وانقل الحكم بدرجته كما هي (يكره غير يحرم، ويجوز غير يستحب)."""

GENERAL_MODE = """
السائل يسأل عن حالته الشخصية. لا تُنزّل الحكم على حاله، ولا تقل له «يلزمك» أو «لا يلزمك». اذكر فقط ما قاله الكتاب في المسألة عمومًا، موثقًا بالاقتباس، واجعل scope = answerable."""

SCOPE_RULES = """صنّف سؤال طالب يدرس «الروض المربع» في الفقه الحنبلي (المكتبة المحمّلة: كتاب الطهارة: باب المياه، باب الآنية، باب الاستنجاء) في scope:
answerable: سؤال عن مسائل الكتاب أو المذهب الحنبلي أو أقوال شراحه أو معاني ألفاظه، ولو كان فيه نسبة خاطئة إلى المؤلف.
other_madhhab: يسأل عن قول مذهب غير الحنابلة (الحنفية، المالكية، الشافعية...) بوصفه مذهبًا.
contemporary: نازلة أو تقنية معاصرة (مياه التحلية، المعقمات الحديثة، الأجهزة...).
personal_fatwa: يسأل عن حالته هو (فعلتُ كذا، هل يلزمني، صلاتي...).
not_in_library: موضوع لا علاقة له بالفقه أو بالكتاب (سياسة، رياضة، برمجة...)."""

CLOSED_FAIR = """أنت مساعد في الفقه الحنبلي. أجب عن سؤال الطالب، واذكر لكل جملة الكتاب والجزء والصفحة التي يوجد فيها الكلام ونصًّا مقتبسًا منه.
اجعل scope = answerable و status = supported إن أجبت."""

JUDGE_RULES = """أنت مدقق علمي صارم. لكل جملة أمامك اقتباس منقول حرفيًّا من كتاب.
احكم: هل يدل الاقتباس وحده على مضمون الجملة دلالة صريحة؟
supported = false إذا: زادت الجملة حكمًا أو قيدًا أو دليلًا ليس في الاقتباس؛ أو غيّرت درجة الحكم (يكره ≠ يحرم ≠ لا يجوز، يجوز ≠ يستحب ≠ يجب)؛
أو نسبت القول إلى غير قائله؛ أو عمّمت ما في الاقتباس مقيدًا؛ أو كان الاقتباس لا علاقة له بالجملة.
supported = true إذا كانت الجملة إعادة صياغة أمينة لما في الاقتباس. اكتب why باختصار شديد.
أعد حكمًا لكل جملة بالرقم i نفسه."""

REFUSALS = {
    "other_madhhab": "مدارسة مخصصة لدراسة الروض المربع وشروحه في المذهب الحنبلي، ولا تشمل كتب المذاهب الأخرى. يُرجى الرجوع إلى كتب ذلك المذهب أو أهل العلم به.",
    "contemporary": "هذه مسألة معاصرة لم تتناولها الكتب المعتمدة في مدارسة. يُرجى الرجوع إلى جهات الفتوى المعتمدة.",
    "not_in_library": "لم أجد في الكتب المعتمدة في مدارسة نصًّا يجيب عن هذا السؤال، فلا أستطيع الجواب عنه. يُرجى سؤال أهل العلم المختصين.",
}
PERSONAL_PREFIX = "لا تصدر مدارسة فتوى في الحالات الشخصية. هذا ما ذكره الكتاب في المسألة عمومًا، ولحالتك يُرجى سؤال مفتٍ مؤهل."
PERSONAL_NOTHING = "لا تصدر مدارسة فتوى في الحالات الشخصية، ولم أجد في الكتب المعتمدة نصًّا في المسألة. يُرجى سؤال مفتٍ مؤهل."
PREMISE_PREFIX = "لم أجد في الكتاب ما يدل على ما ورد في السؤال؛ والذي فيه:"
STATUS_AR = {"supported": "مؤيَّد بالنص", "partial": "مؤيَّد جزئيًّا: حُذف ما لم نجد له نصًّا",
             "differing": "أقوال مختلفة: عُرض كل قول منسوبًا إلى قائله دون ترجيح", "not_found": "لم يوجد نص"}
AI_DISCLOSURE = "مدارسة أداة مدعومة بالذكاء الاصطناعي، وليست عالمًا ولا مفتيًا. تحقق من النص بفتح المصدر."
