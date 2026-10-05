/* The additions (each labelled تجريبي): takhrij, word meaning, listen, recite, study tools, review (spaced repetition), notebook.
   Notebook and review cards live in this browser's localStorage only; both can be exported. */
(function () {
  const start = () => {
    const F = MD.state.cfg.features;
    const esc = MD.esc, view = MD.view, dg = MD.digits;
    const STRIP = s => String(s || "").replace(/[ؐ-ًؚ-ٰٟۖ-ۭـ]/g, "");
    const NORM = s => STRIP(s).replace(/[إأآٱ]/g, "ا").replace(/ى/g, "ي").replace(/ة/g, "ه").replace(/ؤ/g, "و").replace(/ئ/g, "ي").replace(/[^ء-ي0-9 ]/g, " ").replace(/\s+/g, " ").trim();
    const STEM = w => { for (const p of ["وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك"]) if (w.startsWith(p) && w.length - p.length >= 2) { w = w.slice(p.length); break; } return w; };
    const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const download = (name, text, type = "text/markdown") => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], {type: type + ";charset=utf-8"})); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
    const chapterButtons = (cur, base) => `<div class="chapters">${MD.state.cfg.chapters.map(c => `<button class="${c.id === cur ? "on" : ""}" onclick="location.hash='#/${base}/${c.id}'">${esc(c.title)}</button>`).join("")}</div>`;

    /* ================= notebook ================= */
    const NB = {
      all: () => MD.store.get("notebook", []),
      save: items => MD.store.set("notebook", items),
      add(item) { const it = {id: uid(), t: Date.now(), note: "", ...item}; const all = NB.all(); all.unshift(it); NB.save(all); MD.toast("أضيف إلى دفتري"); },
      md(items) {
        const L = ["# دفتري في مدارسة", "", `صُدِّر في ${new Date().toLocaleString("ar")}. كل معلومة معها مصدرها.`, ""];
        for (const it of items) {
          L.push(`## ${it.title || ""}`, "", it.body || "", "");
          for (const c of it.cites || []) L.push(`- ${c.book}، ج${c.vol} ص${c.page}${c.quote ? `: «${c.quote}»` : ""} — ${c.link || ""}`);
          if (it.note) L.push("", `> ملاحظتي: ${it.note}`);
          L.push("");
        }
        return L.join("\n");
      },
    };
    MD.notebook = NB;
    if (F.notebook) {
      MD.route("notebook", "دفتري", () => {
        const items = NB.all();
        const v = document.querySelector("#view");
        v.innerHTML = `<div class="row noprint"><span class="meta">${dg(items.length)} عنصرًا · محفوظة في هذا المتصفح فقط</span><span class="spacer"></span>
          <button class="btn" id="nbMd">تصدير Markdown</button><button class="btn" id="nbPrint">طباعة / PDF</button><button class="btn" id="nbJson">نسخة احتياطية</button></div>
          ${items.length ? "" : `<div class="card meta">دفترك فارغ. أضف إليه الأجوبة والملخصات ومعاني الكلمات والتخريج بزر «أضف إلى دفتري».</div>`}
          ${items.map(it => `<div class="card" data-id="${it.id}"><div class="row"><b>${esc(it.title || "")}</b><span class="spacer"></span><span class="meta">${esc(it.type || "")}</span><button class="btn small noprint" data-del>حذف</button></div>
            <div class="book" style="white-space:pre-wrap">${esc(view(it.body || ""))}</div>
            ${(it.cites || []).map(c => `<div class="meta">${MD.ref(c)}${c.quote ? `: «${esc(view(c.quote).slice(0, 140))}»` : ""} · <a href="${c.link}" target="_blank" rel="noopener">افتح الصفحة</a></div>`).join("")}
            <textarea class="noprint" data-note placeholder="ملاحظتك…" style="width:100%;margin-top:6px;font:inherit;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);padding:6px">${esc(it.note || "")}</textarea>
            ${it.note ? `<div class="meta" style="display:none" data-print-note>ملاحظتي: ${esc(it.note)}</div>` : ""}</div>`).join("")}`;
        v.querySelector("#nbMd").onclick = () => download("mudarasa-notebook.md", NB.md(NB.all()));
        v.querySelector("#nbPrint").onclick = () => window.print();
        v.querySelector("#nbJson").onclick = () => download("mudarasa-notebook.json", JSON.stringify({notebook: NB.all(), cards: MD.store.get("cards", [])}, null, 1), "application/json");
        v.querySelectorAll("[data-del]").forEach(b => b.onclick = () => { NB.save(NB.all().filter(x => x.id !== b.closest(".card").dataset.id)); MD.render(); });
        v.querySelectorAll("[data-note]").forEach(t => t.onchange = () => { const all = NB.all(); const it = all.find(x => x.id === t.closest(".card").dataset.id); if (it) { it.note = t.value; NB.save(all); } });
      }, {exp: true});
      MD.answerHooks.push((r, el) => {
        if (!(r.sentences || []).length) return;
        const b = document.createElement("button"); b.className = "btn small"; b.textContent = "أضف إلى دفتري";
        b.onclick = () => NB.add({type: "جواب", title: r.question, body: r.sentences.map(s => s.text).join("\n"),
          cites: r.sentences.filter(s => s.cite).map(s => ({...s.cite, quote: s.quote}))});
        el.querySelector("[data-answer-actions]").prepend(b);
      });
    }

    /* ================= spaced repetition (SM-2) ================= */
    const SRS = {
      all: () => MD.store.get("cards", []),
      save: c => MD.store.set("cards", c),
      add(card) {
        const all = SRS.all();
        if (all.some(c => c.front === card.front)) { MD.toast("البطاقة موجودة في المراجعة"); return; }
        all.push({id: uid(), due: Date.now(), interval: 0, ease: 2.5, reps: 0, lapses: 0, ...card}); SRS.save(all); MD.toast("أضيفت إلى المراجعة");
      },
      grade(card, q) { // q: 0 again, 3 hard, 4 good, 5 easy
        if (q < 3) { card.reps = 0; card.interval = 0; card.lapses++; card.due = Date.now() + 10 * 60e3; }
        else {
          card.reps++;
          card.interval = card.reps === 1 ? 1 : card.reps === 2 ? 3 : Math.round(card.interval * card.ease * (q === 3 ? 0.8 : q === 5 ? 1.3 : 1));
          card.ease = Math.max(1.3, card.ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
          card.due = Date.now() + card.interval * 864e5;
        }
        return card;
      },
      dueCards: () => SRS.all().filter(c => c.due <= Date.now()).sort((a, b) => a.due - b.due),
    };
    MD.srs = SRS;
    if (F.srs) {
      const label = () => `المراجعة${SRS.dueCards().length ? ` (${dg(SRS.dueCards().length)})` : ""}`;
      MD.route("review", label(), () => {
        const v = document.querySelector("#view"), due = SRS.dueCards(), total = SRS.all().length;
        if (!due.length) {
          v.innerHTML = `<div class="card"><p>لا بطاقات مستحقة الآن. ${total ? `عندك ${dg(total)} بطاقة؛ أقرب موعد: ${new Date(Math.min(...SRS.all().map(c => c.due))).toLocaleString("ar")}.` : "أضف بطاقات من «أدوات المذاكرة» أو من أخطاء «الحفظ»."}</p>
            <p class="meta">تبقى البطاقات في هذا المتصفح فقط. <button class="btn small" id="exp">تصدير</button> <label class="btn small">استيراد<input type="file" id="imp" accept=".json" hidden></label></p></div>`;
        } else {
          const c = due[0];
          v.innerHTML = `<div class="card"><div class="meta">${dg(due.length)} مستحقة · ${esc(c.src || "")}</div>
            <div class="book" style="margin:12px 0">${esc(view(c.front))}</div>
            <div id="back" class="hidden"><hr style="border:0;border-top:1px solid var(--line)"><div class="book">${esc(view(c.back))}</div>
              ${c.cite ? `<div class="meta">${MD.ref(c.cite)} · <a href="${c.cite.link}" target="_blank" rel="noopener">افتح الصفحة</a></div>` : ""}</div>
            <div class="row" style="margin-top:12px" id="acts"><button class="btn primary" id="show">أظهر الجواب</button></div></div>
            <p class="meta">تبقى البطاقات في هذا المتصفح فقط. <button class="btn small" id="exp">تصدير</button> <label class="btn small">استيراد<input type="file" id="imp" accept=".json" hidden></label></p>`;
          v.querySelector("#show").onclick = () => {
            v.querySelector("#back").classList.remove("hidden");
            v.querySelector("#acts").innerHTML = [[0, "أعد (لم أتذكر)"], [3, "صعب"], [4, "جيد"], [5, "سهل"]].map(([q, l]) => `<button class="btn" data-q="${q}">${l}</button>`).join("");
            v.querySelectorAll("[data-q]").forEach(b => b.onclick = () => { const all = SRS.all(); const i = all.findIndex(x => x.id === c.id); SRS.grade(all[i], +b.dataset.q); SRS.save(all); MD.render(); });
          };
        }
        v.querySelector("#exp").onclick = () => download("mudarasa-review.json", JSON.stringify({version: 1, cards: SRS.all()}, null, 1), "application/json");
        v.querySelector("#imp").onchange = async e => {
          try { const d = JSON.parse(await e.target.files[0].text()); const have = new Set(SRS.all().map(c => c.front)); const add = (d.cards || []).filter(c => !have.has(c.front)); SRS.save(SRS.all().concat(add)); MD.toast(`استُورد ${dg(add.length)} بطاقة`); MD.render(); }
          catch { MD.toast("ملف غير صالح"); }
        };
      }, {exp: true});
    }

    /* ================= takhrij + word meaning inside the study panel ================= */
    MD.paraHooks.push((p, panel, el, cid) => {
      const tabs = panel.querySelector(".ptabs"), body = panel.querySelector("[data-body]");
      if (F.takhrij) {
        const b = document.createElement("button"); b.dataset.t = "takhrij"; b.textContent = "التخريج"; tabs.append(b);
        b.onclick = async () => {
          tabs.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
          body.innerHTML = `<p class="spin">…</p>`;
          const d = await MD.api("/api/takhrij/" + p.id);
          if (!d.items.length) { body.innerHTML = `<p class="meta">لا تخريج في حواشي الكتب المعتمدة لهذه الفقرة.</p>`; return; }
          body.innerHTML = `<p class="meta">نعرض التخريج والحكم على الحديث كما نصّ عليه مصدره حرفيًّا، ولا تحكم مدارسة على الأحاديث.</p>` + d.items.map((t, i) => {
            let txt = esc(view(t.text));
            for (const g of t.grades) txt = txt.split(esc(g)).join(`<mark>${esc(g)}</mark>`);
            return `<div class="note"><div class="meta">${t.kind === "variant" ? "فرق بين النسخ" : "تخريج"} · ${esc(t.source)}</div><div class="book">${txt}</div>
              <div class="meta">${MD.ref({book: t.source, vol: t.vol, page: t.page})} · <a href="${t.link}" target="_blank" rel="noopener">افتح الصفحة</a>
              ${t.kind === "takhrij" && !t.grades.length ? " · لم يذكر المصدر حكمًا على الحديث" : ""}
              ${t.dorar ? ` · <a href="${t.dorar}" target="_blank" rel="noopener">ابحث عنه في الدرر السنية</a>` : ""}
              ${F.notebook ? ` · <button class="btn small" data-nb="${i}">أضف إلى دفتري</button>` : ""}</div></div>`;
          }).join("");
          body.querySelectorAll("[data-nb]").forEach(x => x.onclick = () => { const t = d.items[+x.dataset.nb]; NB.add({type: "تخريج", title: "تخريج: " + (t.lemma || "").split(" ").slice(-6).join(" "), body: t.text, cites: [{book: t.source, vol: t.vol, page: t.page, link: t.link}]}); });
        };
      }
      if (F.word) {
        const tx = el.querySelector("[data-text]");
        tx.innerHTML = tx.innerHTML.replace(/(^|[\s>(«])([ء-يً-ْٰ]{3,})(?=[\s<)»،.؛:]|$)/g, (m, a, w) => `${a}<span class="word" tabindex="0">${w}</span>`);
        tx.title = "اضغط على كلمة لمعرفة معناها";
        tx.querySelectorAll(".word").forEach(w => w.onclick = e => { e.stopPropagation(); wordPop(w.textContent, p); });
        const hint = document.createElement("span"); hint.className = "meta"; hint.textContent = "اضغط على أي كلمة في الفقرة لمعرفة معناها من الكتب.";
        panel.querySelector("[data-actions]").append(hint);
      }
      if (F.notebook) {
        const b = document.createElement("button"); b.className = "btn"; b.textContent = "أضف الفقرة إلى دفتري";
        b.onclick = () => NB.add({type: "فقرة", title: `الروض المربع، ص${dg(p.page)}`, body: p.text, cites: [{book: "الروض المربع (ط الرسالة)", vol: p.vol, page: p.page, link: p.link}]});
        panel.querySelector("[data-actions]").append(b);
      }
      if (F.audio) {
        const b = document.createElement("button"); b.className = "btn"; b.textContent = "استمع";
        b.onclick = () => { MD.state.listenFrom = p.id; location.hash = "#/listen/" + cid; };
        panel.querySelector("[data-actions]").append(b);
      }
    });

    async function wordPop(word, p) {
      document.querySelectorAll(".pop").forEach(x => x.remove());
      const pop = document.createElement("div"); pop.className = "pop"; pop.setAttribute("role", "dialog");
      pop.innerHTML = `<div class="row"><b class="book">${esc(word)}</b><span class="spacer"></span><button class="btn small" data-x>إغلاق</button></div><p class="spin">…</p>`;
      document.body.append(pop);
      pop.querySelector("[data-x]").onclick = () => pop.remove();
      const d = await MD.api(`/api/word?w=${encodeURIComponent(STRIP(word))}&para=${p.id}`).catch(() => ({items: []}));
      const items = d.items || [];
      pop.innerHTML = `<div class="row"><b class="book">${esc(word)}</b><span class="spacer"></span><button class="btn small" data-x>إغلاق</button></div>` +
        (items.length ? items.map((e, i) => `<div class="note"><div class="book">${esc(view(e.definition))}</div><div class="meta">${MD.ref({book: e.source, vol: e.vol, page: e.page})} · <a href="${e.link}" target="_blank" rel="noopener">افتح الصفحة</a>${F.notebook ? ` · <button class="btn small" data-nb="${i}">أضف إلى دفتري</button>` : ""}</div></div>`).join("")
          : `<p class="meta">لم نجد تعريفًا لهذه الكلمة في حواشي الكتب المحمّلة.</p>`) +
        `<div class="row" style="margin-top:8px"><button class="btn primary" data-ask>اشرح من النصوص</button><span class="meta">سؤال موثق بالخطوات نفسها</span></div>`;
      pop.querySelector("[data-x]").onclick = () => pop.remove();
      pop.querySelectorAll("[data-nb]").forEach(b => b.onclick = () => { const e = items[+b.dataset.nb]; NB.add({type: "معنى كلمة", title: `معنى «${STRIP(word)}»`, body: e.definition, cites: [{book: e.source, vol: e.vol, page: e.page, link: e.link}]}); });
      pop.querySelector("[data-ask]").onclick = () => { pop.remove(); MD.state.askPara = {id: p.id, text: p.text, page: p.page}; MD.state.pendingQ = `ما معنى «${STRIP(word)}» في هذه الفقرة؟`; location.hash = "#/ask"; };
    }
    // a pending question (from the word popover) is asked when the ask view opens
    const _ask = MD.routes.ask;
    MD.routes.ask = async a => { await _ask(a); if (MD.state.pendingQ) { const q = MD.state.pendingQ; MD.state.pendingQ = null; document.querySelector("#q").value = q; document.querySelector("#f").requestSubmit(); } };

    /* ================= listen ================= */
    const LIG = {"ﷺ": "صلى الله عليه وسلم", "﵇": "عليه السلام", "﵀": "رحمه الله", "﵁": "رضي الله عنه", "﵂": "رضي الله عنها", "﵃": "رضي الله عنهم", "﵄": "رضي الله عنهما"};
    const speakable = s => String(s).replace(/[ﷺ﵇﵀﵁﵂﵃﵄]/g, m => " " + LIG[m] + " ").replace(/\([٠-٩0-9]+\)/g, " ").replace(/[«»"\[\]{}﴿﴾()*_=]/g, " ").replace(/\s+/g, " ").trim();
    const matnOnly = s => (String(s).match(/\(([^()]*)\)/g) || []).filter(x => !/^\([\s٠-٩0-9]+\)$/.test(x)).map(x => x.slice(1, -1)).join(" ");
    let player = null;
    if (F.audio) {
      MD.route("listen", "استماع", async (cid = "water") => {
        const v = document.querySelector("#view");
        v.innerHTML = `<div class="spin">…</div>`;
        const [d, man] = await Promise.all([MD.api("/api/listen/" + cid), MD.api("/api/audio/" + cid).catch(() => ({clips: []}))]);
        const clips = {}; (man.clips || []).forEach(c => clips[c.id] = c);
        const mode = MD.store.get("listenMode", "text");
        v.innerHTML = chapterButtons(cid, "listen") +
          `<div class="card noprint" style="position:sticky;top:0;z-index:5"><div class="row">
            <button class="btn primary" id="lp">▶ تشغيل</button><button class="btn" id="lprev" aria-label="السابق">السابق</button><button class="btn" id="lnext" aria-label="التالي">التالي</button>
            <select id="lmode" class="btn"><option value="text">المتن والشرح</option><option value="notes">مع حواشي ابن قاسم</option><option value="matn">المتن فقط</option></select>
            <select id="lrate" class="btn"><option value="0.8">٠٫٨×</option><option value="1" selected>١×</option><option value="1.2">١٫٢×</option></select>
            <span class="meta" id="lsrc"></span></div></div>
          <p class="meta">النص المقروء من طبعة ركائز (مشكولة). ${Object.keys(clips).length ? "التسجيل: صوت عربي آلي (Azure)." : "التسجيلات الجاهزة غير متاحة بعد؛ يُقرأ النص بصوت المتصفح."}</p>` +
          d.paras.map((p, i) => `<div class="card" data-i="${i}" id="lp${i}">${p.heading ? `<div class="meta">${esc(p.heading)}</div>` : ""}<div class="book" data-words>${MD.matnHTML(p.text)}</div>
            <div class="meta">${MD.ref({book: "الروض (ط ركائز)", vol: p.vol, page: p.page})}${p.notes.length ? ` · <button class="btn small" data-notes="${i}">حواشي ابن قاسم (${dg(p.notes.length)})</button>` : ""}</div><div data-notebox></div></div>`).join("");
        v.querySelector("#lmode").value = mode;
        let idx = Math.max(0, d.paras.findIndex(p => MD.state.listenFrom && p.anchor_paras.includes(MD.state.listenFrom))); MD.state.listenFrom = null;
        let playing = false, queue = [], audio = null;
        const mark = i => { v.querySelectorAll("[data-i]").forEach(c => c.classList.toggle("open", +c.dataset.i === i)); const el = v.querySelector("#lp" + i); if (el) el.scrollIntoView({behavior: "smooth", block: "center"}); };
        const wordsOf = el => { // wrap words for highlighting; returns [{span, start, end}] over the speakable text
          const box = el.querySelector("[data-words]"); const raw = box.textContent; const parts = raw.split(/(\s+)/);
          box.innerHTML = parts.map(w => /\S/.test(w) ? `<span class="w">${esc(view(w))}</span>` : w).join("");
          return [...box.querySelectorAll(".w")];
        };
        const items = () => { // build what to read for the paragraph idx
          const p = d.paras[idx], m = v.querySelector("#lmode").value;
          const list = [{id: p.id, text: m === "matn" ? matnOnly(p.text) : p.text, el: v.querySelector("#lp" + idx)}];
          if (m === "notes") p.notes.forEach(n => list.push({id: n.id, text: "قال ابن قاسم: " + n.text, note: n}));
          return list;
        };
        const stopAll = () => { speechSynthesis.cancel(); if (audio) { audio.pause(); audio = null; } };
        const next = () => { if (!playing) return; if (!queue.length) { if (idx < d.paras.length - 1) { idx++; mark(idx); queue = items(); } else { playing = false; v.querySelector("#lp").textContent = "▶ تشغيل"; return; } } speak(queue.shift()); };
        const speak = it => {
          const rate = +v.querySelector("#lrate").value;
          let spans = [];
          if (it.el && v.querySelector("#lmode").value !== "matn") spans = wordsOf(it.el);
          if (it.note) { const box = v.querySelector(`#lp${idx} [data-notebox]`); box.innerHTML = `<div class="note book"><span class="meta">حاشية ابن قاسم ${MD.ref({book: "", vol: it.note.vol, page: it.note.page})}</span><br>${esc(view(it.note.text))}</div>`; }
          const clip = clips[it.id + (v.querySelector("#lmode").value === "matn" ? ":matn" : "")];
          spans.forEach(s => s.style.background = "");
          if (clip) {
            audio = new Audio("/audio/" + clip.file); audio.playbackRate = rate; v.querySelector("#lsrc").textContent = "تسجيل";
            audio.ontimeupdate = () => { const t = audio.currentTime * 1000; const k = clip.words.findIndex(w => w.t > t) - 1; spans.forEach((s, j) => s.style.background = j === clip.words[Math.max(0, k)]?.i ? "var(--mark)" : ""); };
            audio.onended = next; audio.play().catch(() => { playing = false; });
          } else {
            const txt = speakable(STRIP(it.text) === it.text ? it.text : it.text);
            const u = new SpeechSynthesisUtterance(txt); u.lang = "ar-SA"; u.rate = rate;
            const voice = speechSynthesis.getVoices().find(x => x.lang && x.lang.startsWith("ar")); if (voice) u.voice = voice;
            v.querySelector("#lsrc").textContent = voice ? "صوت المتصفح: " + voice.name : "صوت المتصفح";
            const words = txt.split(/\s+/); let acc = 0; const offs = words.map(w => { const o = acc; acc += w.length + 1; return o; });
            u.onboundary = e => { if (e.name && e.name !== "word") return; const k = offs.findIndex((o, j) => e.charIndex >= o && (j === offs.length - 1 || e.charIndex < offs[j + 1])); spans.forEach((s, j) => s.style.background = j === k ? "var(--mark)" : ""); };
            u.onend = next; u.onerror = next; speechSynthesis.speak(u);
          }
        };
        v.querySelector("#lp").onclick = () => { if (playing) { playing = false; stopAll(); v.querySelector("#lp").textContent = "▶ تشغيل"; return; } playing = true; v.querySelector("#lp").textContent = "⏸ إيقاف"; mark(idx); queue = items(); next(); };
        v.querySelector("#lnext").onclick = () => { stopAll(); idx = Math.min(d.paras.length - 1, idx + 1); mark(idx); queue = items(); if (playing) next(); };
        v.querySelector("#lprev").onclick = () => { stopAll(); idx = Math.max(0, idx - 1); mark(idx); queue = items(); if (playing) next(); };
        v.querySelector("#lmode").onchange = e => MD.store.set("listenMode", e.target.value);
        v.querySelectorAll("[data-i]").forEach(c => c.ondblclick = () => { stopAll(); idx = +c.dataset.i; mark(idx); queue = items(); if (!playing) v.querySelector("#lp").click(); else next(); });
        v.querySelectorAll("[data-notes]").forEach(b => b.onclick = () => { // read one note, then continue where we were
          const p = d.paras[+b.dataset.notes]; stopAll(); const resume = queue.slice();
          queue = p.notes.map(n => ({id: n.id, text: "قال ابن قاسم: " + n.text, note: n})).concat(resume);
          if (!playing) { playing = true; v.querySelector("#lp").textContent = "⏸ إيقاف"; } next();
        });
        mark(idx);
        window.addEventListener("hashchange", stopAll, {once: true});
      }, {exp: true});
    }

    /* ================= recite (memorization) ================= */
    const sim = (a, b) => { // normalised edit-distance similarity
      if (a === b) return 1; const m = a.length, n = b.length; if (!m || !n) return 0;
      const d = Array.from({length: m + 1}, (_, i) => [i, ...Array(n).fill(0)]); for (let j = 1; j <= n; j++) d[0][j] = j;
      for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++) d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      return 1 - d[m][n] / Math.max(m, n);
    };
    const key = w => STEM(NORM(w));
    // align recognised words to expected words: returns states per expected word: ok | wrong | skip | pending
    function align(expected, heard, final) {
      const E = expected.map(key), H = heard.map(key).filter(Boolean), st = E.map(() => "pending"), said = E.map(() => "");
      let i = 0;
      for (let h = 0; h < H.length && i < E.length; h++) {
        if (sim(H[h], E[i]) >= 0.75 || (H[h].length > 2 && E[i].includes(H[h]) && H[h].length / E[i].length > 0.6)) { st[i] = "ok"; i++; continue; }
        let j = 1; while (j <= 3 && i + j < E.length && sim(H[h], E[i + j]) < 0.75) j++;
        if (j <= 3 && i + j < E.length) { for (let k = i; k < i + j; k++) st[k] = "skip"; st[i + j] = "ok"; i += j + 1; continue; }
        if (h + 1 < H.length && sim(H[h] + H[h + 1], E[i]) >= 0.75) { st[i] = "ok"; i++; h++; continue; } // a word split in two
        st[i] = "wrong"; said[i] = heard[h]; i++;
      }
      if (final) for (let k = i; k < E.length; k++) if (st[k] === "pending") st[k] = "pending";
      return {st, said, pos: i};
    }
    MD.reciteAlign = align;
    if (F.recite) {
      MD.route("recite", "الحفظ", async (cid = "water") => {
        const v = document.querySelector("#view");
        const d = await MD.api("/api/matn/" + cid);
        const hideMode = MD.store.get("hideMode", "all");
        let li = MD.store.get("reciteLine:" + cid, 0); if (li >= d.lines.length) li = 0;
        v.innerHTML = chapterButtons(cid, "recite") + `<p class="meta">متن «زاد المستقنع» من الروض المربع، مشكولًا من طبعة ركائز حيث اتفقت الطبعتان. أخفِ الكلمات ثم سمّع: تظهر الكلمات كلما نطقتها صحيحة، وتُعلَّم الأخطاء.</p>
          <div class="card"><div class="row"><select id="line" class="btn">${d.lines.map((l, i) => `<option value="${i}">السطر ${dg(i + 1)}: ${esc(l.words.slice(0, 4).map(w => w.plain).join(" "))}…</option>`).join("")}</select>
            <select id="hide" class="btn"><option value="all">إخفاء كل الكلمات</option><option value="first">إظهار الحرف الأول</option><option value="alt">إخفاء كلمة وترك كلمة</option><option value="none">بلا إخفاء</option></select></div>
            <div class="book" id="matn" style="font-size:calc(var(--fs) + 4px);margin:14px 0;min-height:3em"></div>
            <div class="row"><button class="btn primary" id="mic">🎙 ابدأ التسميع</button><button class="btn" id="reveal">أظهر السطر</button><button class="btn" id="nextl">السطر التالي</button><span class="meta" id="engine"></span></div>
            <details><summary>لا يوجد ميكروفون؟ سمّع كتابةً</summary><textarea id="typed" style="width:100%;min-height:60px;font:inherit;font-size:18px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);padding:8px" placeholder="اكتب السطر من حفظك…"></textarea></details>
            <div id="result" class="meta" style="margin-top:8px"></div></div>
          <p class="meta">يُرسَل الصوت إلى خدمة التعرف على الكلام (Azure أو المتصفح) لتحويله إلى نص، ولا نحفظه.</p>`;
        const lineSel = v.querySelector("#line"), hideSel = v.querySelector("#hide"); lineSel.value = li; hideSel.value = hideMode;
        let state = {st: [], said: []}, revealed = false;
        const draw = () => {
          const l = d.lines[li], mode = hideSel.value;
          v.querySelector("#matn").innerHTML = l.words.map((w, k) => {
            const s = state.st[k] || "pending";
            if (s === "ok" || revealed) return `<span style="color:${s === "ok" ? "var(--ok)" : "inherit"}">${esc(view(w.w))}</span>`;
            if (s === "wrong") return `<span style="color:var(--bad);text-decoration:underline" title="قلتَ: ${esc(state.said[k])}">${esc(view(w.w))}</span>`;
            if (s === "skip") return `<span style="color:var(--warn);text-decoration:underline dotted" title="تخطيتها">${esc(view(w.w))}</span>`;
            const hidden = mode === "all" || (mode === "alt" && k % 2 === 1) || mode === "first";
            if (!hidden || mode === "none") return `<span>${esc(view(w.w))}</span>`;
            return mode === "first" ? `<span style="color:var(--muted)">${esc(w.plain[0])}${"ـ".repeat(Math.max(1, w.plain.length - 1))}</span>` : `<span style="color:var(--muted)">${"ـ".repeat(Math.max(2, w.plain.length))}</span>`;
          }).join(" ");
        };
        const finish = () => {
          const l = d.lines[li], ok = state.st.filter(s => s === "ok").length, bad = l.words.filter((w, k) => state.st[k] === "wrong" || state.st[k] === "skip");
          v.querySelector("#result").innerHTML = `النتيجة: ${dg(ok)} من ${dg(l.words.length)} صحيحة${bad.length ? ` · الأخطاء: ${bad.map(w => esc(w.plain)).join("، ")}` : ""}
            ${bad.length && F.srs ? ` <button class="btn small" id="toSrs">أضف الأخطاء إلى المراجعة</button>` : ""}`;
          const b = v.querySelector("#toSrs");
          if (b) b.onclick = () => bad.forEach(w => SRS.add({front: l.words.map(x => x === w ? "……" : x.w).join(" "), back: w.w, src: "الحفظ: " + MD.state.cfg.chapters.find(c => c.id === cid).title,
            cite: {book: "الروض المربع (ط الرسالة)", vol: 1, page: l.page, link: ""}}));
        };
        const hear = (text, final) => { state = align(d.lines[li].words.map(w => w.plain), text.split(/\s+/), final); draw(); if (final) finish(); };
        const reset = () => { state = {st: [], said: []}; revealed = false; v.querySelector("#result").textContent = ""; v.querySelector("#typed").value = ""; draw(); MD.store.set("reciteLine:" + cid, li); };
        lineSel.onchange = () => { li = +lineSel.value; reset(); };
        hideSel.onchange = () => { MD.store.set("hideMode", hideSel.value); draw(); };
        v.querySelector("#reveal").onclick = () => { revealed = !revealed; draw(); };
        v.querySelector("#nextl").onclick = () => { li = Math.min(d.lines.length - 1, li + 1); lineSel.value = li; reset(); };
        v.querySelector("#typed").oninput = e => hear(e.target.value, false);
        v.querySelector("#typed").onchange = e => hear(e.target.value, true);
        let rec = null, heardFinal = "";
        const stop = () => { if (rec) { try { rec.stop ? rec.stop() : rec.stopContinuousRecognitionAsync(); } catch {} rec = null; } v.querySelector("#mic").textContent = "🎙 ابدأ التسميع"; };
        v.querySelector("#mic").onclick = async () => {
          if (rec) { stop(); hear(heardFinal, true); return; }
          heardFinal = ""; reset();
          const tok = await MD.api("/api/speech/token").catch(() => ({available: false}));
          if (tok.available) {
            if (!window.SpeechSDK) await new Promise((ok, no) => { const s = document.createElement("script"); s.src = "https://cdn.jsdelivr.net/npm/microsoft-cognitiveservices-speech-sdk@1.43.0/distrib/browser/microsoft.cognitiveservices.speech.sdk.bundle-min.js"; s.onload = ok; s.onerror = no; document.head.append(s); });
            const S = window.SpeechSDK, cfg = S.SpeechConfig.fromAuthorizationToken(tok.token, tok.region); cfg.speechRecognitionLanguage = "ar-SA";
            const r = new S.SpeechRecognizer(cfg, S.AudioConfig.fromDefaultMicrophoneInput());
            const pl = S.PhraseListGrammar.fromRecognizer(r); d.lines[li].words.forEach(w => pl.addPhrase(w.plain));
            r.recognizing = (_, e) => hear((heardFinal + " " + e.result.text).trim(), false);
            r.recognized = (_, e) => { if (e.result.text) { heardFinal = (heardFinal + " " + e.result.text).trim(); hear(heardFinal, false); } if (state.pos >= d.lines[li].words.length) { stop(); hear(heardFinal, true); } };
            r.startContinuousRecognitionAsync(); rec = r; v.querySelector("#engine").textContent = "التعرف على الكلام: Azure";
          } else if (window.SpeechRecognition || window.webkitSpeechRecognition) {
            const R = new (window.SpeechRecognition || window.webkitSpeechRecognition)(); R.lang = "ar-SA"; R.interimResults = true; R.continuous = true;
            R.onresult = e => { let interim = ""; for (let k = e.resultIndex; k < e.results.length; k++) { if (e.results[k].isFinal) heardFinal += " " + e.results[k][0].transcript; else interim += " " + e.results[k][0].transcript; } hear((heardFinal + " " + interim).trim(), false); if (state.pos >= d.lines[li].words.length) { stop(); hear(heardFinal, true); } };
            R.onend = () => { if (rec) { stop(); hear(heardFinal, true); } };
            R.start(); rec = R; v.querySelector("#engine").textContent = "التعرف على الكلام: المتصفح";
          } else { MD.toast("المتصفح لا يدعم التعرف على الكلام؛ سمّع كتابةً."); v.querySelector("details").open = true; return; }
          v.querySelector("#mic").textContent = "⏹ أنهِ التسميع";
        };
        reset();
        window.addEventListener("hashchange", stop, {once: true});
      }, {exp: true});
    }

    /* ================= study tools ================= */
    if (F.study_tools) {
      MD.route("tools", "أدوات المذاكرة", async (cid = "water") => {
        const v = document.querySelector("#view");
        const d = await MD.api("/api/tools/" + cid);
        const chip = c => c ? `<a class="chip" href="${c.link}" target="_blank" rel="noopener" title="${esc(c.quote || "")}">${MD.ref(c)}</a>` : "";
        v.innerHTML = chapterButtons(cid, "tools") + `<p class="meta">ملخصات وأسئلة وبطاقات مولّدة من نصوص الكتب المعتمدة فقط. كل جملة وكل جواب له اقتباس تحققنا من وجوده في الصفحة، ثم من أنه يدل عليه؛ وما لم يثبت حُذف.</p>` +
          (d.sections.length ? "" : `<div class="card meta">لم تُولَّد أدوات هذا الباب بعد.</div>`) +
          d.sections.map((s, si) => `<div class="card"><h3 style="margin:0 0 6px">${esc(s.title)}</h3><div class="meta">${MD.ref({book: "الروض", vol: 1, page: s.page})}</div>
            <h4>الملخص</h4>${s.summary.map(x => `<p class="book" style="margin:4px 0">${esc(view(x.text))} ${chip(x.cite)}</p>`).join("")}
            ${s.quiz.length ? `<h4>أسئلة</h4>` + s.quiz.map((q, qi) => `<div class="note" data-quiz="${si}:${qi}"><div>${esc(view(q.question))}</div><div class="row">${q.options.map((o, oi) => `<button class="btn" data-o="${oi}">${esc(view(o))}</button>`).join("")}</div><div class="meta hidden" data-expl>${esc(view(q.explanation || ""))} ${chip(q.cite)}</div></div>`).join("") : ""}
            ${s.cards.length ? `<h4>بطاقات</h4>` + s.cards.map((c, ci) => `<div class="note"><div class="book">${esc(view(c.front))}</div><details><summary>الجواب</summary><div class="book">${esc(view(c.back))} ${chip(c.cite)}</div>
              <div class="row">${F.srs ? `<button class="btn small" data-srs="${si}:${ci}">أضف إلى المراجعة</button>` : ""}${F.notebook ? `<button class="btn small" data-nbc="${si}:${ci}">أضف إلى دفتري</button>` : ""}</div></details></div>`).join("") : ""}
            <div class="row" style="margin-top:8px">${F.notebook ? `<button class="btn small" data-nbs="${si}">أضف الملخص إلى دفتري</button>` : ""}${F.srs ? `<button class="btn small" data-allsrs="${si}">أضف كل البطاقات إلى المراجعة</button>` : ""}</div></div>`).join("");
        v.querySelectorAll("[data-quiz]").forEach(box => {
          const [si, qi] = box.dataset.quiz.split(":").map(Number), q = d.sections[si].quiz[qi];
          box.querySelectorAll("[data-o]").forEach(b => b.onclick = () => {
            box.querySelectorAll("[data-o]").forEach(x => { x.disabled = true; if (+x.dataset.o === q.answer) x.style.borderColor = "var(--ok)"; });
            if (+b.dataset.o !== q.answer) b.style.borderColor = "var(--bad)";
            box.querySelector("[data-expl]").classList.remove("hidden");
          });
        });
        const card = s => s.split(":").map(Number);
        v.querySelectorAll("[data-srs]").forEach(b => b.onclick = () => { const [si, ci] = card(b.dataset.srs), c = d.sections[si].cards[ci]; SRS.add({front: c.front, back: c.back, cite: c.cite, src: d.sections[si].title}); });
        v.querySelectorAll("[data-allsrs]").forEach(b => b.onclick = () => d.sections[+b.dataset.allsrs].cards.forEach(c => SRS.add({front: c.front, back: c.back, cite: c.cite, src: d.sections[+b.dataset.allsrs].title})));
        v.querySelectorAll("[data-nbc]").forEach(b => b.onclick = () => { const [si, ci] = card(b.dataset.nbc), c = d.sections[si].cards[ci]; NB.add({type: "بطاقة", title: c.front, body: c.back, cites: c.cite ? [c.cite] : []}); });
        v.querySelectorAll("[data-nbs]").forEach(b => b.onclick = () => { const s = d.sections[+b.dataset.nbs]; NB.add({type: "ملخص", title: "ملخص: " + s.title, body: s.summary.map(x => x.text).join("\n"), cites: s.summary.filter(x => x.cite).map(x => x.cite)}); });
      }, {exp: true});
    }
    // re-render now that the extra tabs exist (route order: study, ask, listen, tools, recite, review, notebook)
    const order = ["study", "ask", "listen", "tools", "recite", "review", "notebook"];
    MD.tabs.sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));
    MD.render();
  };
  if (window.MD && MD.ready) start(); else document.addEventListener("md:ready", start, {once: true});
})();
