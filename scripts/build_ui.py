"""Build the web app from the team's design (Claude Design export) and connect it to Mudarasa's backend.

Input : design/madarasa.html   (the bundled export, unchanged; re-export from Claude Design and re-run this script)
        scripts/ui/integration.js (code appended to the design's logic class)
Output: web/index.html          (the same bundle, with the integration code and small markup additions)

What the integration changes (everything else in the design runs as designed):
  reader       the four Zad-family books show their real text by chapter, in pages of at most 300 words ("next"; pages
               turn by themselves while listening) or as one scroll (a setting); bookmarks are placed on a word;
               selected text can be saved to the notes with a comment; a footnote number shows its takhrij
  listening    real Azure recordings from the clicked word; the highlight follows the recorded word timings
  recitation   the Zad matn, 50 words a page, checked by Azure speech-to-text (words revealed, mistakes marked)
  meaning      lexical / shar'i / contextual meaning from library passages (/api/meaning), with pages; a close button
  chat         streamed, cited, checked answers; each citation opens its book with the quote highlighted; dictation;
               a photo (a page or a written question) becomes the question (/api/image_question); Zad suggestions
  study        summaries from the verified study tools; a page to make a deck with several cards or add cards to a deck
  everywhere   Arabic-Indic digits; the Norsal font when web/fonts/Norsal-*.otf exist
Usage: python -m scripts.build_ui
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "design" / "madarasa.html"
JS = ROOT / "scripts" / "ui" / "integration.js"
OUT = ROOT / "web" / "index.html"

TITLE = "مدارسة · رفيق طالب العلم الشرعي"
Q1, Q2 = "ما حكم الماء الآجن، وهو المتغير بطول مكثه؟", "اشرح قوله: «وهي ارتفاع الحدث وما في معناه، وزوال الخبث»"

DORAR_MARKUP = """
                <sc-if value="{{ mean.hasLink }}" hint-placeholder-val="{{ false }}">
                  <a href="{{ mean.link }}" target="_blank" rel="noopener" style="align-self:flex-start;font-size:14px;color:var(--color-accent-800)">ابحث عن الحديث في الدرر السنية ↗</a>
                </sc-if>"""

CITES_MARKUP = """
                  <sc-if value="{{ m.hasCites }}" hint-placeholder-val="{{ false }}">
                    <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:12.5px">
                      <span style="border:1px solid {{ m.stColor }};color:{{ m.stColor }};border-radius:999px;padding:1px 10px;font-weight:600">{{ m.status }}</span>
                      <sc-for list="{{ m.cites }}" as="c">
                        <span style="display:inline-flex;align-items:stretch;border:1px solid {{ c.bd }};background:{{ c.bg }};border-radius:6px;overflow:hidden">
                          <button sc-camel-on-click="{{ c.open }}" title="اعرض النص من الكتاب" style="border:0;background:transparent;font:inherit;font-size:12.5px;color:var(--color-accent-800);padding:1px 8px;cursor:pointer">({{ c.n }}) {{ c.label }}</button>
                          <a href="{{ c.link }}" target="_blank" rel="noopener" title="افتح الصفحة في تراث" style="text-decoration:none;color:var(--color-accent-700);padding:1px 6px;border-inline-start:1px solid var(--color-accent-300)">↗</a>
                        </span>
                      </sc-for>
                    </div>
                    <sc-if value="{{ m.hasPv }}" hint-placeholder-val="{{ false }}">
                      <div data-cite-card="1" style="display:flex;flex-direction:column;gap:var(--space-2);padding:var(--space-4) var(--space-5);border:1px solid var(--color-divider);border-inline-start:3px solid var(--color-accent);border-radius:var(--radius-lg);background:var(--color-surface);box-shadow:var(--shadow-sm)">
                        <div style="display:flex;align-items:center;gap:var(--space-2);flex-wrap:wrap">
                          <span style="font-weight:700;font-size:14px;color:var(--color-accent-800)">{{ m.pv.book }}</span>
                          <span style="font-size:12px;color:var(--color-neutral-700)">{{ m.pv.where }}</span>
                          <button sc-camel-on-click="{{ m.pv.close }}" title="إغلاق" style="margin-inline-start:auto;width:28px;height:28px;display:grid;place-items:center;border:1px solid var(--color-divider);border-radius:var(--radius-md);background:transparent;color:var(--color-neutral-700);cursor:pointer;font:inherit;font-size:16px;line-height:1">×</button>
                        </div>
                        <p style="margin:0;font-family:'Norsal','IBM Plex Sans Arabic',sans-serif;font-size:19px;line-height:2.1;text-align:justify;color:var(--color-text)"><sc-for list="{{ m.pv.parts }}" as="pt"><span style="{{ pt.css }}">{{ pt.t }}</span></sc-for></p>
                        <div style="display:flex;gap:var(--space-2);flex-wrap:wrap;align-items:center">
                          <sc-if value="{{ m.pv.inApp }}" hint-placeholder-val="{{ true }}"><button class="btn btn-secondary" sc-camel-on-click="{{ m.pv.read }}" style="font-size:13px">اقرأ في الكتاب</button></sc-if>
                          <a href="{{ m.pv.link }}" target="_blank" rel="noopener" style="font-size:13px;color:var(--color-accent-800)">افتح الصفحة في تراث ↗</a>
                          <span style="font-size:12px;color:var(--color-neutral-600);margin-inline-start:auto">{{ m.pv.note }}</span>
                        </div>
                      </div>
                    </sc-if>
                    <span style="font-size:12px;color:var(--color-neutral-600)">{{ m.onlyNote }}</span>
                    <sc-if value="{{ m.hasDropped }}" hint-placeholder-val="{{ false }}"><span style="font-size:12px;color:oklch(0.55 0.15 30)">{{ m.droppedNote }}</span></sc-if>
                  </sc-if>"""

PAGER_MARKUP = """
            <sc-if value="{{ pgShow }}" hint-placeholder-val="{{ false }}">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:var(--space-3);flex-wrap:wrap;margin-top:var(--space-2);padding-top:var(--space-3);border-top:1px solid var(--color-divider)">
                <button class="btn btn-secondary" sc-camel-on-click="{{ pgPrev }}" style="opacity:{{ pgPrevOp }}">{{ pgPrevLabel }}</button>
                <span style="font-size:13px;color:var(--color-neutral-700)">{{ pgLabel }}</span>
                <button class="btn btn-primary" sc-camel-on-click="{{ pgNext }}" style="opacity:{{ pgNextOp }}">{{ pgNextLabel }}</button>
              </div>
            </sc-if>"""

MEAN_CLOSE = """<button sc-camel-on-click="{{ closeMean }}" title="إغلاق نافذة المعنى" style="margin-inline-start:auto;width:30px;height:30px;flex:none;display:grid;place-items:center;border:1px solid var(--color-divider);border-radius:var(--radius-md);background:transparent;color:var(--color-neutral-700);cursor:pointer;font:inherit;font-size:18px;line-height:1">×</button>"""

SELECTION_MARKUP = """
          <sc-if value="{{ selChipOn }}" hint-placeholder-val="{{ false }}">
            <button data-sel-ui="1" sc-camel-on-click="{{ selOpen }}" style="position:fixed;left:{{ selX }};top:{{ selY }};transform:translate(-50%,-120%);z-index:30;display:flex;align-items:center;gap:6px;padding:6px 14px;border:1px solid var(--color-accent);border-radius:999px;background:var(--color-bg);color:var(--color-accent-800);font:inherit;font-size:13px;font-weight:600;box-shadow:var(--shadow-md);cursor:pointer;white-space:nowrap">✎ أضف إلى التقييدات</button>
          </sc-if>
          <sc-if value="{{ selFormOn }}" hint-placeholder-val="{{ false }}">
            <div data-sel-ui="1" sc-camel-on-click="{{ selCancel }}" style="position:fixed;inset:0;z-index:40;display:grid;place-items:center;background:color-mix(in srgb,#000 28%,transparent)">
              <div data-sel-ui="1" sc-camel-on-click="{{ stop }}" style="width:min(540px,92vw);display:flex;flex-direction:column;gap:var(--space-3);padding:var(--space-6);background:var(--color-bg);border:1px solid var(--color-divider);border-radius:var(--radius-lg);box-shadow:var(--shadow-md)">
                <span style="font-weight:700;font-size:18px">تقييد على نص من «{{ selBook }}»</span>
                <div style="padding:var(--space-3) var(--space-4);border-inline-start:3px solid var(--color-accent);background:var(--color-surface);font-size:16px;line-height:1.9;max-height:30vh;overflow:auto">«{{ selText }}»</div>
                <textarea value="{{ selNote }}" sc-camel-on-change="{{ onSelNote }}" rows="3" placeholder="اكتب تعليقك أو فائدتك هنا (اختياري)…" style="border:1px solid var(--color-divider);border-radius:var(--radius-md);padding:var(--space-3);font:inherit;font-size:15px;line-height:1.8;background:var(--color-bg);color:var(--color-text);resize:vertical"></textarea>
                <div style="display:flex;gap:var(--space-2);justify-content:flex-end"><button class="btn btn-ghost" sc-camel-on-click="{{ selCancel }}">إلغاء</button><button class="btn btn-primary" sc-camel-on-click="{{ selSave }}">حفظ في التقييدات</button></div>
              </div>
            </div>
          </sc-if>
          <sc-if value="{{ selDoneOn }}" hint-placeholder-val="{{ false }}">
            <div style="position:fixed;bottom:var(--space-8);left:50%;transform:translateX(-50%);z-index:40;padding:8px 18px;border-radius:999px;background:var(--color-accent-800);color:var(--color-bg);font-size:14px;box-shadow:var(--shadow-md)">أُضيف إلى التقييدات ✓</div>
          </sc-if>"""

CHAT_IMG_PREVIEW = """<sc-if value="{{ hasChatImg }}" hint-placeholder-val="{{ false }}">
              <div style="display:flex;align-items:center;gap:var(--space-3)">
                <img data-img-key="draft" alt="الصورة المرفقة" style="width:96px;height:64px;flex:none;object-fit:cover;border-radius:var(--radius-md);border:1px solid var(--color-divider);background:var(--color-surface)">
                <span style="flex:1;font-size:12px;line-height:1.7;color:var(--color-neutral-700)">تُقرأ الصورة ليُستخرج منها السؤال، ثم يُجاب من الكتب المحمّلة. لا نحفظ الصورة.</span>
                <button class="btn btn-ghost" sc-camel-on-click="{{ dropChatImg }}" title="إزالة الصورة" style="font-size:18px;line-height:1">×</button>
              </div>
            </sc-if>
            """

TURN_IMG = """<sc-if value="{{ m.hasImg }}" hint-placeholder-val="{{ false }}"><img data-img-key="{{ m.imgKey }}" alt="الصورة المرفقة" style="align-self:flex-start;max-width:240px;max-height:200px;object-fit:contain;border-radius:var(--radius-md);border:1px solid var(--color-divider);background:var(--color-surface)"></sc-if>"""

INPUT_STYLE = "border:0;border-bottom:1px solid var(--color-divider);background:transparent;font:inherit;font-size:15px;padding:6px 0;color:var(--color-text);min-width:0"
DECK_EDITOR = """
                <sc-if value="{{ deckEditView }}" hint-placeholder-val="{{ false }}">
                  <div style="display:flex;flex-direction:column;gap:var(--space-4)">
                    <div style="display:flex;align-items:center;gap:var(--space-3);flex-wrap:wrap">
                      <button class="btn btn-secondary" sc-camel-on-click="{{ deCancel }}">المجموعات</button>
                      <span style="font-family:'Norsal','IBM Plex Sans Arabic',sans-serif;font-weight:700;font-size:22px">{{ deTitle }}</span>
                    </div>
                    <sc-if value="{{ deIsNew }}" hint-placeholder-val="{{ true }}">
                      <div style="display:flex;gap:var(--space-3);flex-wrap:wrap;align-items:center">
                        <input value="{{ deName }}" sc-camel-on-change="{{ onDeName }}" placeholder="اسم الرزمة، مثل: باب المياه" style="flex:2 1 240px;INPUT_STYLE">
                        <sc-raw-select value="{{ deParent }}" sc-camel-on-change="{{ onDeParent }}" style="flex:1 1 180px;border:1px solid var(--color-divider);border-radius:var(--radius-md);background:var(--color-bg);font:inherit;font-size:14px;padding:6px 8px;color:var(--color-text)">
                          <sc-for list="{{ deckParents }}" as="dp"><option value="{{ dp.id }}">{{ dp.name }}</option></sc-for>
                        </sc-raw-select>
                      </div>
                    </sc-if>
                    <div style="display:flex;flex-direction:column;border:1px solid var(--color-divider);border-radius:var(--radius-lg);overflow:hidden">
                      <div style="display:grid;grid-template-columns:36px minmax(0,1fr) minmax(0,1fr) 36px;gap:var(--space-3);padding:var(--space-2) var(--space-4);background:var(--color-surface);font-size:12px;color:var(--color-neutral-700);border-bottom:1px solid var(--color-divider)"><span>#</span><span>السؤال (وجه البطاقة)</span><span>الجواب (ظهرها)</span><span></span></div>
                      <sc-for list="{{ deCards }}" as="dc" hint-placeholder-count="2">
                        <div style="display:grid;grid-template-columns:36px minmax(0,1fr) minmax(0,1fr) 36px;gap:var(--space-3);align-items:center;padding:var(--space-2) var(--space-4);border-bottom:1px solid var(--color-divider)">
                          <span style="font-weight:700;color:var(--color-accent-700)">{{ dc.n }}</span>
                          <input value="{{ dc.q }}" sc-camel-on-change="{{ dc.onQ }}" placeholder="مثل: ما الماء الطهور؟" style="INPUT_STYLE">
                          <input value="{{ dc.a }}" sc-camel-on-change="{{ dc.onA }}" placeholder="مثل: الباقي على خلقته" style="INPUT_STYLE">
                          <button sc-camel-on-click="{{ dc.del }}" title="حذف البطاقة" style="visibility:{{ dc.delVis }};width:30px;height:30px;display:grid;place-items:center;border:1px solid var(--color-divider);border-radius:var(--radius-md);background:transparent;color:var(--color-neutral-700);cursor:pointer;font:inherit;font-size:16px">×</button>
                        </div>
                      </sc-for>
                    </div>
                    <div style="display:flex;gap:var(--space-3);align-items:center;flex-wrap:wrap">
                      <button class="btn btn-secondary" sc-camel-on-click="{{ deAddCard }}">+ بطاقة أخرى</button>
                      <span style="font-size:13px;color:var(--color-neutral-700)">{{ deHint }}</span>
                      <span style="font-size:13px;color:oklch(0.5 0.14 30)">{{ deErr }}</span>
                      <div style="margin-inline-start:auto;display:flex;gap:var(--space-2)"><button class="btn btn-ghost" sc-camel-on-click="{{ deCancel }}">إلغاء</button><button class="btn btn-primary" sc-camel-on-click="{{ deSave }}">{{ deSaveLabel }}</button></div>
                    </div>
                  </div>
                </sc-if>
""".replace("INPUT_STYLE", INPUT_STYLE)

FONT_FACES = ("<style>@font-face{font-family:'Norsal';src:url('/fonts/Norsal-Light.otf') format('opentype');font-weight:100 500;font-display:swap}"
              "@font-face{font-family:'Norsal';src:url('/fonts/Norsal-Bold.otf') format('opentype');font-weight:600 900;font-display:swap}</style>")


def once(tpl, old, new, what, count=1):
    n = tpl.count(old)
    assert n == count, f"{what}: expected {count}, found {n}"
    return tpl.replace(old, new)


def main():
    html = SRC.read_text(encoding="utf-8")
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    tpl = json.loads(m.group(2))
    js = JS.read_text(encoding="utf-8")
    assert "</script" not in js
    # 1) chat: citations (each opens its book at the quote) and evidence status; image in the question; attach and dictate
    tpl = once(tpl, "{{ m.a }}</p>", "{{ m.a }}</p>" + CITES_MARKUP, "chat answer")
    tpl = once(tpl, "{{ m.q }}</h3>", "{{ m.q }}</h3>" + TURN_IMG, "chat question")
    tpl = once(tpl, '<button class="btn btn-ghost btn-icon" title="إرفاق" style="width:34px;height:34px">',
               '<button class="btn btn-ghost btn-icon" title="أرفق صورة: صفحة من كتاب أو سؤالًا مكتوبًا" sc-camel-on-click="{{ attachImg }}" style="width:34px;height:34px">', "attach")
    tpl = once(tpl, '<button class="btn btn-ghost btn-icon" title="إملاء صوتي" style="margin-inline-start:auto;width:34px;height:34px">',
               '<button class="btn btn-ghost btn-icon" title="{{ dictTitle }}" sc-camel-on-click="{{ dictate }}" style="margin-inline-start:auto;width:34px;height:34px;background:{{ dictBg }};color:{{ dictC }}">', "dictate")
    tpl = once(tpl, '<textarea value="{{ draft }}"', CHAT_IMG_PREVIEW + '<textarea value="{{ draft }}"', "chat input")
    # suggested questions: the Zad
    for old, new in (("ما الفرق بين الكلام والكلمة عند النحاة؟", Q1), ("ما معنى «بالوضع» في تعريف الكلام في الآجرومية؟", Q2), ("ما معنى «بالوضع» في تعريف الكلام؟", Q2)):
        assert old in tpl, old
        tpl = tpl.replace(old, new)
    # 2) each word carries its index; the player, meaning and recitation panels stay pinned at the bottom of the screen
    tpl = once(tpl, 'title="{{ w.title }}"', 'title="{{ w.title }}" data-wi="{{ w.i }}"', "word spans", 2)
    PIN = "position:sticky;bottom:var(--space-3);z-index:4;background:var(--color-bg);box-shadow:var(--shadow-md);"
    for cond, style in [("isListen", "display:flex;align-items:center;gap:var(--space-4);padding:var(--space-4) var(--space-6);border:1px solid var(--color-divider);border-radius:var(--radius-lg);flex-wrap:wrap"),
                        ("isMeaning", "display:flex;flex-direction:column;gap:var(--space-3);padding:var(--space-4) var(--space-6);border:1px solid var(--color-divider);border-radius:var(--radius-lg)"),
                        ("isRecite", "display:flex;flex-direction:column;gap:var(--space-4);padding:var(--space-4) var(--space-6);border:1px solid var(--color-divider);border-radius:var(--radius-lg)")]:
        a = tpl.find('<sc-if value="{{ ' + cond + ' }}"'); b = tpl.find('<div style="' + style + '"', a)
        assert a > 0 and 0 < b - a < 200, (cond, a, b)
        extra = PIN + ("max-height:45vh;overflow:auto;" if cond == "isMeaning" else "")
        tpl = tpl[:b] + '<div style="' + extra + style + '"' + tpl[b + len('<div style="' + style + '"'):]
    # 3) pages: previous / next under the text, in the reader and in recitation
    starts = [k.start() for k in re.finditer(re.escape('<sc-for list="{{ paras }}"'), tpl)]
    assert len(starts) == 2, len(starts)
    for a in reversed(starts):
        inner = tpl.find("</sc-for>", a); outer = tpl.find("</sc-for>", inner + 1) + len("</sc-for>")
        tpl = tpl[:outer] + PAGER_MARKUP + tpl[outer:]
    # 3b) listening: when the reader browses away from the voice, a button brings the view back to it
    a = tpl.find('sc-camel-on-click="{{ togglePlay }}"'); b = tpl.find("</button>", a) + len("</button>")
    assert a > 0 and b > a
    tpl = tpl[:b] + ('<sc-if value="{{ pgBackShow }}" hint-placeholder-val="{{ false }}"><button class="btn btn-secondary" sc-camel-on-click="{{ pgBack }}" '
                     'style="font-size:13px;white-space:nowrap">عُد إلى موضع القراءة</button></sc-if>') + tpl[b:]
    # 4) the meaning panel: Dorar link-out after the rows, and a close button
    a = tpl.find('<sc-for list="{{ mean.rows }}"'); b = tpl.find("</sc-for>", a) + len("</sc-for>")
    assert a > 0 and b > a
    tpl = tpl[:b] + DORAR_MARKUP + tpl[b:]
    st = '<span style="font-size:12px;color:var(--color-neutral-600)">{{ mean.status }}</span>'
    tpl = once(tpl, st, st + MEAN_CLOSE, "meaning status")
    # 5) bookmark button: asks for a word
    tpl = once(tpl, 'sc-camel-on-click="{{ addBm }}" title="احفظ موضعك" class="btn btn-secondary" style="display:flex;align-items:center;gap:6px"',
               'sc-camel-on-click="{{ addBm }}" title="{{ bmBtnTitle }}" class="btn btn-secondary" style="display:flex;align-items:center;gap:6px;background:{{ bmBtnBg }};border-color:{{ bmBtnBd }}"', "bookmark button")
    a = tpl.find('title="{{ bmBtnTitle }}"'); b = tpl.find("علامة</button>", a)
    assert 0 < b - a < 1500
    tpl = tpl[:b] + "{{ bmBtnLabel }}</button>" + tpl[b + len("علامة</button>"):]
    # 5b) the reader's header (title, listening / meanings, bookmark) stays at the top while the book scrolls;
    #     the table of contents and the text card leave room for it
    r0 = tpl.find('<sc-if value="{{ isReader }}"')
    head = '<div style="display:flex;align-items:flex-end;justify-content:space-between;gap:var(--space-4);flex-wrap:wrap">'
    h = tpl.find(head, r0); assert 0 < h - r0 < 600, h - r0
    tpl = tpl[:h] + ('<div style="position:sticky;top:0;z-index:6;background:var(--color-bg);padding-block:var(--space-3);margin-block:calc(-1 * var(--space-3));'
                     'box-shadow:{{ rdShadow }};transition:box-shadow .2s;display:flex;align-items:center;justify-content:space-between;gap:var(--space-4);flex-wrap:wrap">') + tpl[h + len(head):]
    tpl = once(tpl, '<span style="font-size:13px;color:var(--color-accent-700)">{{ src.art }} · {{ src.author }}</span>',
               '<span style="font-size:13px;color:var(--color-accent-700);display:{{ rdMetaDisp }}">{{ src.art }} · {{ src.author }}</span>', "reader meta")
    tpl = once(tpl, "font-weight:700;font-size:40px;line-height:1.3\">{{ src.name }}</h1>",
               "font-weight:700;font-size:{{ rdTitleFs }};line-height:1.3;transition:font-size .2s\">{{ src.name }}</h1>", "reader title")
    toc = 'position:sticky;top:var(--space-4);max-height:calc(100vh - 160px)'
    t0 = tpl.find(toc, r0); assert t0 > 0
    tpl = tpl[:t0] + 'position:sticky;top:96px;max-height:calc(100vh - 250px)' + tpl[t0 + len(toc):]
    card = '<div style="border:1px solid var(--color-divider);border-radius:var(--radius-lg);padding:var(--space-8);background:var(--color-surface);box-shadow:var(--shadow-sm)">'
    c0 = tpl.find(card, r0); assert c0 > 0
    tpl = tpl[:c0] + card.replace('box-shadow:var(--shadow-sm)', 'box-shadow:var(--shadow-sm);scroll-margin-top:110px') + tpl[c0 + len(card):]
    # 6) select text in the reader -> notes with a comment
    a = tpl.find('<sc-if value="{{ isReader }}"'); b = tpl.find(">", tpl.find("<div", a)) + 1
    assert a > 0 and b > a
    tpl = tpl[:b] + SELECTION_MARKUP + tpl[b:]
    # 7) settings: pages or one scroll
    a = tpl.find("حجم خط المتن"); row = tpl.rfind('<div style="display:flex;align-items:center;justify-content:space-between', 0, a)
    f0 = tpl.find('<sc-for list="{{ optFs }}"'); f1 = tpl.find("</sc-for>", f0) + len("</sc-for>")
    assert 0 < row < a and f0 > 0
    opts = tpl[f0:f1].replace("optFs", "optReadMode")
    new_row = ('<div style="display:flex;align-items:center;justify-content:space-between;gap:var(--space-4);padding:var(--space-3) 0;border-bottom:1px solid var(--color-divider);flex-wrap:wrap">'
               '<div style="display:flex;flex-direction:column;gap:2px;min-width:200px;flex:1"><span style="font-weight:700;font-size:15px">عرض النص في القارئ</span>'
               '<span style="font-size:12px;color:var(--color-neutral-700)">صفحات (٣٠٠ كلمة، و٥٠ في التسميع) تنتقل بـ«التالي» وتنتقل وحدها مع الاستماع والتسميع، أو تمرير متصل كما في تراث</span></div>'
               '<div style="display:flex;gap:var(--space-1);flex-wrap:wrap">' + opts + '</div></div>\n            ')
    toggle = ('<button sc-camel-on-click="{{ setHoverMean }}" style="width:44px;height:24px;flex:none;border-radius:999px;border:1px solid {{ tgHoverMean.bd }};background:{{ tgHoverMean.bg }};position:relative;cursor:pointer;transition:all .2s">'
              '<span style="position:absolute;top:2px;width:18px;height:18px;border-radius:50%;background:{{ tgHoverMean.knob }};transition:all .2s;inset-inline-start:{{ tgHoverMean.x }}"></span></button>')
    hover_row = ('<div style="display:flex;align-items:center;justify-content:space-between;gap:var(--space-4);padding:var(--space-3) 0;border-bottom:1px solid var(--color-divider);flex-wrap:wrap">'
                 '<div style="display:flex;flex-direction:column;gap:2px;min-width:200px;flex:1"><span style="font-weight:700;font-size:15px">المعنى عند الوقوف على الكلمة</span>'
                 '<span style="font-size:12px;color:var(--color-neutral-700)">في وضع الاستماع: قف على كلمة ثلاث ثوانٍ فيظهر معناها. أطفئه إن كان يظهر وأنت لا تريده</span></div>'
                 + toggle + '</div>\n            ')
    tpl = tpl[:row] + new_row + hover_row + tpl[row:]
    # 8) flashcards: a page to make a deck with several cards; "add cards" inside an open deck
    tpl = once(tpl, '<sc-if value="{{ deckListView }}" hint-placeholder-val="{{ true }}">', DECK_EDITOR + '<sc-if value="{{ deckListView }}" hint-placeholder-val="{{ true }}">', "deck list")
    back = '<button class="btn btn-secondary" sc-camel-on-click="{{ backToDecks }}">المجموعات</button>'
    tpl = once(tpl, back, back + '<button class="btn btn-secondary" sc-camel-on-click="{{ deckAddCards }}">+ إضافة بطاقات</button>', "deck study header")
    # 8b) the founder's photo in the "صاحب الفكرة" boxes, in place of the letter (when web/img/founder.png exists; not in git)
    if (ROOT / "web" / "img" / "founder.png").exists():
        avatar = ('<div style="width:52px;height:52px;flex:none;border-radius:50%;border:1px solid var(--color-accent);display:grid;place-items:center;'
                  'font-weight:700;font-size:20px;color:var(--color-accent-700)">ع</div>')
        photo = ('<img src="/img/founder.png" alt="عبدالرحمن المزيعل" style="width:64px;height:64px;flex:none;border-radius:50%;'
                 'border:1px solid var(--color-accent);object-fit:cover">')
        done, pos = 0, 0
        while (i := tpl.find("صاحب الفكرة", pos)) >= 0:
            j = tpl.find(avatar, i)
            if 0 < j - i < 400:
                tpl = tpl[:j] + photo + tpl[j + len(avatar):]; done += 1
            pos = i + 1
        assert done >= 1, "founder box not found"
    # 9) integration code after the design's logic class
    i = tpl.find('<script type="text/x-dc"'); j = tpl.find("</script>", i)
    assert i > 0 and j > i
    tpl = tpl[:j] + "\n" + js + tpl[j:]
    # 10) page title, icon and the Norsal font
    icon = ('<link rel="icon" type="image/svg+xml" href="/img/icon.svg"><link rel="icon" type="image/png" sizes="64x64" href="/img/icon-64.png">'
            '<link rel="apple-touch-icon" href="/img/icon-180.png">')   # the approved mark (logo sheet 4d)
    fonts = FONT_FACES if (ROOT / "web" / "fonts" / "Norsal-Bold.otf").exists() else ""
    assert "<head>" in tpl
    tpl = tpl.replace("<head>", "<head>" + icon + fonts, 1).replace("<title>في الهرم</title>", "<title>" + TITLE + "</title>")
    html = html[:m.start(2)] + json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/") + html[m.end(2):]
    html = html.replace("<title>في الهرم</title>", "<title>" + TITLE + "</title>")
    if "<title>" not in html:
        html = html.replace("<head>", "<head><title>" + TITLE + "</title>", 1)
    html = html.replace("<head>", "<head>" + icon, 1)   # the loader page shows the icon too
    OUT.write_text(html, encoding="utf-8")
    print("written", OUT, len(html), "chars")


if __name__ == "__main__":
    main()
