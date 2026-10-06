/* Mudarasa front end (after the team's design): shell with sidebar and top bar, welcome, overview, sources, chat, study hub.
   Feature modules (features.js) add listen, recite, tools, review and notebook through MD.route / hooks. */
const MD = {routes: {}, tabs: [], paraHooks: [], answerHooks: [], state: {cfg: null, chapters: {}, tashkeel: true, fs: 19, askPara: null, thread: [], depth: "medium"}};
const $ = s => document.querySelector(s);
const TASH = /[ؐ-ًؚ-ٰٟۖ-ۭ]/g;
const TASH1 = new RegExp(TASH.source);
MD.esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
MD.view = s => MD.state.tashkeel ? String(s ?? "") : String(s ?? "").replace(TASH, "");
MD.digits = n => String(n).replace(/\d/g, d => "٠١٢٣٤٥٦٧٨٩"[d]);
MD.ref = c => `${MD.esc(c.book)}، ج${MD.digits(c.vol)} ص${MD.digits(c.page)}`;
MD.toast = msg => { const t = document.createElement("div"); t.className = "toast"; t.textContent = msg; document.body.append(t); setTimeout(() => t.remove(), 3200); };
MD.store = {
  get(k, d) { try { const v = localStorage.getItem("md:" + k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem("md:" + k, JSON.stringify(v)); } catch {} },
};
MD.api = async (path, body) => {
  const r = await fetch(path, body ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)} : {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || j.error || r.status);
  return j;
};
MD.route = (name, label, fn, opts = {}) => { MD.routes[name] = fn; if (label) MD.tabs.push({name, label, ...opts}); };
MD.highlight = (text, quote) => {
  const t = MD.view(text); if (!quote) return MD.esc(t);
  const strip = s => s.replace(TASH, "").replace(/ـ/g, "");
  const map = []; let plain = "";
  for (let i = 0; i < t.length; i++) { const c = t[i]; if (!TASH1.test(c) && c !== "ـ") { map.push(i); plain += c; } }
  const q = strip(quote).trim().replace(/^[«"(]+|[»")]+$/g, "").trim(); const k = plain.indexOf(q);
  if (k < 0 || !q) return MD.esc(t);
  const a = map[k]; let b = map[k + q.length - 1] + 1; while (b < t.length && (TASH1.test(t[b]) || t[b] === "ـ")) b++;
  return MD.esc(t.slice(0, a)) + "<mark>" + MD.esc(t.slice(a, b)) + "</mark>" + MD.esc(t.slice(b));
};
MD.matnHTML = text => MD.esc(MD.view(text)).replace(/\(([^()]*)\)/g, (m, inner) => /^[\s٠-٩0-9]+$/.test(inner) ? m : `<span class="matn">(${inner})</span>`);

/* ---------- icons ---------- */
const I = {
  home: '<svg viewBox="0 0 24 24"><path d="M4 11 12 4l8 7v9h-5v-6H9v6H4z"/></svg>',
  book: '<svg viewBox="0 0 24 24"><path d="M3 5c3-1 6-1 9 1 3-2 6-2 9-1v14c-3-1-6-1-9 1-3-2-6-2-9-1z"/><path d="M12 6v14"/></svg>',
  chat: '<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 0 1-11.5 7.2L4 20l1-4A8 8 0 1 1 20 12z"/></svg>',
  cap: '<svg viewBox="0 0 24 24"><path d="m2 9 10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/></svg>',
  mic: '<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>',
  send: '<svg viewBox="0 0 24 24"><path d="M12 19V5M6 11l6-6 6 6"/></svg>',
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
  lines: '<svg viewBox="0 0 24 24"><path d="M5 7h14M5 12h14M5 17h9"/></svg>',
  pen: '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/></svg>',
  cards: '<svg viewBox="0 0 24 24"><rect x="3" y="7" width="14" height="12" rx="2"/><path d="M7 4h12a2 2 0 0 1 2 2v10"/></svg>',
};

/* ---------- local activity (stays in this browser) ---------- */
const ACT = {
  day: (d = new Date()) => d.toISOString().slice(0, 10),
  all: () => MD.store.get("activity", {}),
  bump(kind, n = 1) { const a = ACT.all(), d = ACT.day(); a[d] = a[d] || {}; a[d][kind] = (a[d][kind] || 0) + n; MD.store.set("activity", a); },
  week() { // Saturday-first week, as in the design (س ح ن ث ر خ ج)
    const now = new Date(), start = new Date(now); start.setDate(now.getDate() - ((now.getDay() + 1) % 7));
    const a = ACT.all();
    return [...Array(7)].map((_, i) => { const d = new Date(start); d.setDate(start.getDate() + i); const k = ACT.day(d); return {k, today: k === ACT.day(), ...(a[k] || {})}; });
  },
};
MD.act = ACT;
setInterval(() => { if (document.visibilityState === "visible" && MD.store.get("name", "")) ACT.bump("min", 0.5); }, 30000);

/* ---------- settings ---------- */
function applySettings() {
  document.documentElement.style.setProperty("--fs", MD.state.fs + "px");
  const t = $("#tashkeel"); t.setAttribute("aria-pressed", MD.state.tashkeel); t.title = "التشكيل: " + (MD.state.tashkeel ? "ظاهر" : "مخفي"); t.style.opacity = MD.state.tashkeel ? 1 : .55;
  const th = MD.store.get("theme", null); if (th) document.documentElement.dataset.theme = th;
}
$("#fsUp").onclick = () => { MD.state.fs = Math.min(32, MD.state.fs + 2); MD.store.set("fs", MD.state.fs); applySettings(); };
$("#fsDown").onclick = () => { MD.state.fs = Math.max(14, MD.state.fs - 2); MD.store.set("fs", MD.state.fs); applySettings(); };
$("#tashkeel").onclick = () => { MD.state.tashkeel = !MD.state.tashkeel; MD.store.set("tashkeel", MD.state.tashkeel); applySettings(); render(); };
$("#theme").onclick = () => {
  const d = document.documentElement;
  const dark = d.dataset.theme === "dark";
  d.dataset.theme = dark ? "light" : "dark"; MD.store.set("theme", d.dataset.theme);
};
$("#burger").onclick = () => $("#side").classList.toggle("open");
$("#gsearch").addEventListener("keydown", e => { if (e.key === "Enter" && e.target.value.trim()) { MD.state.pendingQ = e.target.value.trim(); e.target.value = ""; location.hash = "#/ask"; } });

/* ---------- welcome (name only, local) ---------- */
function who() {
  const n = MD.store.get("name", "");
  $("#welcome").classList.toggle("hidden", !!n || /^#\/(about|contact)/.test(location.hash));
  $("#uname").textContent = n; $("#av").textContent = (n.trim()[0] || "ع");
  return n;
}
$("#wf").onsubmit = e => { e.preventDefault(); const n = $("#wname").value.trim(); if (!n) { $("#wname").focus(); return; } MD.store.set("name", n); ACT.bump("visits"); who(); location.hash = "#/home"; render(); };
document.querySelectorAll("[data-wl]").forEach(a => a.addEventListener("click", () => $("#welcome").classList.add("hidden")));
$("#logout").onclick = e => { e.preventDefault(); MD.store.set("name", ""); who(); $("#wname").value = ""; };

/* ---------- books (only the four loaded books are «متاح») ---------- */
const BOOKS = [
  {id: 1679, art: "الفقه", title: "الروض المربع شرح زاد المستقنع", by: "منصور بن يونس البهوتي (ت ١٠٥١ هـ)", ed: "دار المؤيد / مؤسسة الرسالة", pages: 734, vols: 1, role: "النص المدروس", on: true},
  {id: 147658, art: "الفقه", title: "الروض المربع (مشكول)", by: "البهوتي · تحقيق دار ركائز", ed: "دار ركائز، ١٤٣٨ هـ", pages: 1607, vols: 3, role: "التشكيل والتخريج والفروق", on: true},
  {id: 12216, art: "الفقه", title: "حاشية الروض المربع", by: "عبد الرحمن بن محمد بن قاسم (ت ١٣٩٢ هـ)", ed: "ط١ ١٣٩٧ هـ", pages: 4103, vols: 7, role: "حاشية", on: true},
  {id: 10649, art: "الفقه", title: "الشرح الممتع على زاد المستقنع", by: "محمد بن صالح العثيمين (ت ١٤٢١ هـ)", ed: "دار ابن الجوزي", pages: 6753, vols: 15, role: "شرح المتن", on: true},
  {id: 0, art: "الفقه", title: "زاد المستقنع", by: "شرف الدين موسى الحجاوي (ت ٩٦٨ هـ)", ed: "ضمن الروض المربع", pages: null, vols: null, role: "المتن", on: true, inside: true},
  {id: 1319, art: "الفقه", title: "تيسير مسائل الفقه شرح الروض المربع", by: "عبد الكريم النملة", ed: "", role: "شرح", on: false},
  {id: 807, art: "الفقه", title: "شرح زاد المستقنع", by: "آل حسين", ed: "", role: "شرح المتن", on: false},
  {id: 17500, art: "الفقه", title: "الحاشية العثيمينية على زاد المستقنع", by: "", ed: "", role: "حاشية", on: false},
  {id: 12145, art: "اللغة", title: "المصباح المنير", by: "أحمد بن محمد الفيومي (ت ٧٧٠ هـ)", ed: "", role: "معاني الألفاظ", on: false},
];

/* ---------- study view (the Rawd with its commentaries) ---------- */
async function chapterData(cid) {
  if (!MD.state.chapters[cid]) MD.state.chapters[cid] = await MD.api("/api/chapter/" + cid);
  return MD.state.chapters[cid];
}
MD.chapterData = chapterData;
const AUTO = {fuzzy: "تطابق تقريبي", struct: "بترتيب المتن", exact_span: "عبر مقطعين", order: "بالترتيب فقط", title: "عنوان الباب"};
function notesIQ(p) {
  if (!p.iq.length) return `<p class="meta">لا حواشي لابن قاسم على هذه الفقرة.</p>`;
  return p.iq.map(n => `<div class="note"><div class="book"><span class="lemma">«${MD.esc(MD.view(n.lemma && n.method !== "title" ? n.lemma.split(" ").slice(-5).join(" ") : "الترجمة"))}»</span> ${MD.esc(MD.view(n.text))}</div>
    <div class="meta">${MD.ref({book: "حاشية ابن قاسم", vol: n.vol, page: n.page})} · حاشية ${MD.digits(n.n)} · <a href="${n.link}" target="_blank" rel="noopener">افتح الصفحة</a>
    ${AUTO[n.method] || n.agree === false ? `<span class="auto" title="${AUTO[n.method] || "طريقتا الربط مختلفتان"}">ربط منخفض الثقة</span>` : ""}</div></div>`).join("");
}
function notesMumti(p) {
  if (!p.mumti.length) return `<p class="meta">لا مقاطع من الشرح الممتع مربوطة بهذه الفقرة.</p>`;
  return p.mumti.map(s => { const a = s.lines[0], b = s.lines[s.lines.length - 1] || a;
    return `<div class="note"><div class="lemma">${MD.esc(MD.view(s.heading))} ${AUTO[s.method] ? `<span class="auto">${AUTO[s.method]}</span>` : ""}</div>
    <div class="book">${s.lines.map(l => MD.esc(MD.view(l.text))).join("<br>")}</div>
    <div class="meta">${a ? MD.ref({book: "الشرح الممتع", vol: a.vol, page: a.page}) + (b && b.page !== a.page ? "–" + MD.digits(b.page) : "") + ` · <a href="${a.link}" target="_blank" rel="noopener">افتح الصفحة</a>` : ""}</div></div>`; }).join("");
}
function rakaiz(p) {
  let h = "";
  if (p.rakaiz_paras.length) h += `<p class="meta">النص نفسه في طبعة ركائز (مشكول):</p>` + p.rakaiz_paras.map(r => `<div class="book">${MD.matnHTML(r.text)}</div><div class="meta">${MD.ref({book: "الروض (ط ركائز)", vol: r.vol, page: r.page})} · <a href="${r.link}" target="_blank" rel="noopener">افتح الصفحة</a></div>`).join("");
  const diffs = p.units.filter(u => u.edition_diffs && u.edition_diffs.length);
  if (diffs.length) h += `<p class="meta" style="margin-top:10px">فروق بين الطبعتين (تُعرض دون ترجيح):</p>` + diffs.map(u => `<div class="diff meta">عند «${MD.esc(u.matn.slice(0, 40))}»: ` + u.edition_diffs.map(([t, a, b]) => `${a ? `<del>${MD.esc(a)}</del>` : ""} ${b ? `<ins>${MD.esc(b)}</ins>` : ""}`).join(" · ") + `</div>`).join("");
  if (p.rakaiz_notes.length) h += `<p class="meta" style="margin-top:10px">حواشي المحققين في طبعة ركائز (تخريج وفروق نسخ):</p>` + p.rakaiz_notes.map(n => `<div class="note"><div class="book">${MD.esc(MD.view(n.text))}</div><div class="meta">${MD.ref({book: "الروض (ط ركائز)", vol: n.vol, page: n.page})} · حاشية ${MD.digits(n.n)} · <a href="${n.link}" target="_blank" rel="noopener">افتح الصفحة</a></div></div>`).join("");
  return h || `<p class="meta">لم تُربط هذه الفقرة بطبعة ركائز.</p>`;
}
function panelHTML(p) {
  const tabs = [["iq", `حاشية ابن قاسم (${MD.digits(p.iq.length)})`], ["mumti", `الشرح الممتع (${MD.digits(p.mumti.length)})`], ["rk", "طبعة ركائز والفروق"]];
  return `<div class="panel" data-panel="${p.id}"><div class="ptabs" role="tablist">${tabs.map(([k, l], i) => `<button role="tab" data-t="${k}" class="${i ? "" : "on"}">${l}</button>`).join("")}</div>
    <div data-body>${notesIQ(p)}</div><p class="meta">رُبطت الحواشي والشروح بالفقرة آليًّا ولم يراجعها مختص بعد.</p>
    <div class="row noprint" data-actions><button class="btn primary" data-ask>اسأل عن هذه الفقرة</button></div></div>`;
}
async function study(cid = "water") {
  const v = $("#view"); v.innerHTML = `<div class="page"><div class="spin">يحمّل الباب…</div></div>`;
  const ch = await chapterData(cid), cfg = MD.state.cfg;
  let h = `<div class="page"><p class="eyebrow"><a href="#/sources" style="text-decoration:none">المصادر</a> › الروض المربع وشروحه</p><h2 class="h2">${MD.esc(ch.title)}</h2>
    <div class="row noprint" style="margin-bottom:10px"><div class="chapters" role="group" aria-label="الأبواب" style="margin:0">${cfg.chapters.map(c => `<button class="${c.id === cid ? "on" : ""}" data-ch="${c.id}">${MD.esc(c.title)}</button>`).join("")}</div><span class="spacer"></span>
    ${cfg.features.audio ? `<a class="btn" href="#/listen/${cid}">استمع للباب</a>` : ""}${cfg.features.recite ? `<a class="btn" href="#/recite/${cid}">سمّع المتن</a>` : ""}</div>
    <p class="meta">«الروض المربع» (ط الرسالة)، والمتن (زاد المستقنع) بلون مختلف. اضغط على فقرة لتفتح حواشيها وشروحها، وعلى أي كلمة لمعرفة معناها.</p>`;
  h += ch.paras.map(p => `<div class="card para" data-pid="${p.id}" tabindex="0">${p.heading ? `<div class="meta">${MD.esc(p.heading)}</div>` : ""}
    <div class="book" data-text>${MD.matnHTML(p.text)}</div>
    <div class="refs"><span class="pill">${MD.ref({book: "الروض", vol: p.vol, page: p.page})}</span>${p.iq.length ? `<span class="pill">ابن قاسم ${MD.digits(p.iq.length)}</span>` : ""}${p.mumti.length ? `<span class="pill">الممتع ${MD.digits(p.mumti.length)}</span>` : ""}${p.rakaiz_notes.length ? `<span class="pill">تخريج وفروق ${MD.digits(p.rakaiz_notes.length)}</span>` : ""}</div></div>`).join("") + `</div>`;
  v.innerHTML = h;
  v.querySelectorAll("[data-ch]").forEach(b => b.onclick = () => location.hash = "#/study/" + b.dataset.ch);
  v.querySelectorAll(".para").forEach(el => {
    const open = e => {
      if (e.target.closest(".panel") || e.target.closest("a")) return;
      const p = ch.paras.find(x => x.id === el.dataset.pid), existing = el.querySelector(".panel");
      v.querySelectorAll(".panel").forEach(x => x.remove()); v.querySelectorAll(".para.open").forEach(x => x.classList.remove("open"));
      if (existing) return;
      el.classList.add("open"); el.insertAdjacentHTML("beforeend", panelHTML(p)); ACT.bump("paras");
      const panel = el.querySelector(".panel");
      panel.querySelectorAll("[data-t]").forEach(b => b.onclick = () => { panel.querySelectorAll("[data-t]").forEach(x => x.classList.toggle("on", x === b)); panel.querySelector("[data-body]").innerHTML = b.dataset.t === "iq" ? notesIQ(p) : b.dataset.t === "mumti" ? notesMumti(p) : rakaiz(p); });
      panel.querySelector("[data-ask]").onclick = () => { MD.state.askPara = {id: p.id, text: p.text, page: p.page}; location.hash = "#/ask"; };
      MD.paraHooks.forEach(fn => fn(p, panel, el, cid));
    };
    el.onclick = open; el.onkeydown = e => { if (e.key === "Enter" && e.target === el) open(e); };
  });
}

/* ---------- chat ---------- */
const DEPTHS = [["short", "خفيفة"], ["medium", "متوسطة"], ["long", "مفصلة"]];
function answerHTML(r) {
  const refused = !(r.sentences || []).length;
  let h = `<div class="answer" data-answer><div class="head"><span class="badge s-${r.status}">● ${MD.esc(r.status_ar)}</span>${refused ? "" : `<span class="only">الإجابة من النصوص المحققة فقط</span>`}
    <span class="spacer"></span><span class="meta">${r.cached ? "جواب محفوظ" : (r.latency_s ? MD.digits(Math.round(r.latency_s)) + " ثانية" : "")}</span></div>`;
  if (refused && r.message) h += `<div class="refusal"><b>⚠ لم أجد في المصادر المحققة ما يجيب عن هذا</b><p style="margin:6px 0 0">${MD.esc(r.message)}</p></div>`;
  else if (r.message) h += `<div class="msg">${MD.esc(r.message)}</div>`;
  const quoteFor = {};
  for (const s of r.sentences || []) { (quoteFor[s.n] = quoteFor[s.n] || []).push(s.quote);
    h += `<p class="sent book" style="font-size:calc(var(--fs) - 1px)">${MD.esc(MD.view(s.text))}${s.cite ? `<button class="chip" data-p="${s.n}" title="افتح المقطع والاقتباس">${MD.ref(s.cite)}</button>` : ""}</p>`; }
  if ((r.dropped || []).length) { h += `<details><summary>حُذفت ${MD.digits(r.dropped.length)} من الجمل لأن توثيقها لم يثبت</summary>`;
    for (const d of r.dropped) h += `<p class="dropped">✕ ${MD.esc(MD.view(d.text))} <span class="meta">(${MD.esc(d.reason)})</span></p>`; h += `</details>`; }
  if ((r.passages || []).length) { h += `<details data-ps${(r.sentences || []).length ? "" : " open"}><summary>النصوص التي قُرئت للجواب (${MD.digits(r.passages.length)})</summary>`;
    for (const p of r.passages) h += `<div class="passage" data-n="${p.n}"><h4>[${MD.digits(p.n)}] ${MD.ref(p)} · ${MD.esc(p.kind)} · <a href="${p.link}" target="_blank" rel="noopener">افتح الصفحة في تراث</a></h4><div class="book">${MD.highlight(p.text, (quoteFor[p.n] || [])[0])}</div></div>`;
    h += `</details>`; }
  return h + `<div class="row noprint" style="margin-top:10px" data-answer-actions><span class="spacer"></span><button class="btn small" data-report>بلّغ عن خطأ</button></div></div>`;
}
MD.answerHTML = answerHTML;
function bindAnswer(r, a) {
  a.querySelectorAll(".chip").forEach(b => b.onclick = () => { const ps = a.querySelector("[data-ps]"); if (ps) ps.open = true;
    a.querySelectorAll(".passage").forEach(x => x.classList.remove("focus")); const el = a.querySelector(`.passage[data-n="${b.dataset.p}"]`); if (el) { el.classList.add("focus"); el.scrollIntoView({behavior: "smooth", block: "center"}); } });
  a.querySelector("[data-report]").onclick = async () => { const c = prompt("ما الخطأ؟ (مثلًا: الصفحة غير صحيحة، أو الجملة لا يدل عليها النص)"); if (c === null) return;
    MD.toast((await MD.api("/api/report", {kind: "answer", question: r.question, comment: c, where: location.hash})).message); };
  MD.answerHooks.forEach(fn => fn(r, a));
}
function composerHTML(id) {
  const speech = MD.state.cfg.features.recite;
  return `<form class="composer" id="${id}"><textarea name="q" placeholder="اسأل عن مسألة في الروض المربع، أو الصق عبارة من متنه…" aria-label="السؤال" rows="2"></textarea>
    <div class="bar"><button class="send" title="أرسل" aria-label="أرسل">${I.send}</button>${speech ? `<button type="button" class="mic" title="اسأل بصوتك" aria-label="اسأل بصوتك">${I.mic}</button>` : ""}
    <span class="spacer"></span><span class="seg" role="group" aria-label="نمط الجواب">${DEPTHS.map(([k, l]) => `<button type="button" data-depth="${k}" class="${MD.state.depth === k ? "on" : ""}">${l}</button>`).join("")}</span>
    <span class="srcchip" title="المكتبة المعتمدة: الروض المربع (طبعتان)، حاشية ابن قاسم، الشرح الممتع">${I.book} المصدر: الروض المربع وشروحه</span></div></form>`;
}
async function voiceInto(ta, btn) {  // ask by voice: Azure speech-to-text
  const tok = await MD.api("/api/speech/token").catch(() => ({available: false}));
  btn.classList.add("on");
  try {
    if (tok.available) {
      if (!window.SpeechSDK) await new Promise((ok, no) => { const s = document.createElement("script"); s.src = "https://cdn.jsdelivr.net/npm/microsoft-cognitiveservices-speech-sdk@1.43.0/distrib/browser/microsoft.cognitiveservices.speech.sdk.bundle-min.js"; s.onload = ok; s.onerror = no; document.head.append(s); });
      const S = window.SpeechSDK, c = S.SpeechConfig.fromAuthorizationToken(tok.token, tok.region); c.speechRecognitionLanguage = "ar-SA";
      const r = new S.SpeechRecognizer(c, S.AudioConfig.fromDefaultMicrophoneInput());
      MD.toast("تحدّث الآن…");
      await new Promise(ok => r.recognizeOnceAsync(res => { if (res.text) ta.value = (ta.value + " " + res.text).trim(); else MD.toast("لم نسمع صوتًا. تأكد أن الميكروفون يعمل."); r.close(); ok(); }, () => { r.close(); ok(); }));
    } else MD.toast("التحدث غير متاح الآن؛ اكتب سؤالك.");
  } finally { btn.classList.remove("on"); ta.focus(); }
}
function bindComposer(form, onAsk) {
  const ta = form.querySelector("textarea");
  form.querySelectorAll("[data-depth]").forEach(b => b.onclick = () => { MD.state.depth = b.dataset.depth; MD.store.set("depth", MD.state.depth); form.querySelectorAll("[data-depth]").forEach(x => x.classList.toggle("on", x === b)); });
  const mic = form.querySelector(".mic"); if (mic) mic.onclick = () => voiceInto(ta, mic);
  form.onsubmit = e => { e.preventDefault(); const q = ta.value.trim(); if (q) { ta.value = ""; onAsk(q); } };
  ta.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
}
const STAGES = [["search", "يبحث في الكتب"], ["write", "يكتب الجواب من النصوص"], ["verify", "يتحقق من كل جملة واقتباسها"]];
async function runAsk(q, slot) {
  const ctx = MD.state.askPara, depth = MD.state.depth, body = {question: q, para: ctx ? ctx.id : null, depth};
  ACT.bump("q"); const hist = MD.store.get("history", []); hist.unshift({t: Date.now(), q}); MD.store.set("history", hist.slice(0, 50));
  let stage = "search", t = 0;
  slot.innerHTML = `<div class="answer"><div class="stages" data-st></div><div class="meta" data-t></div><div data-early></div></div>`;
  const draw = () => { const st = slot.querySelector("[data-st]"); if (!st) return; const i = STAGES.findIndex(s => s[0] === stage);
    st.innerHTML = STAGES.map(([k, l], j) => `<span class="${j < i ? "done" : j === i ? "on" : ""}">${j < i ? "✓" : j === i ? "●" : "○"} ${l}</span>`).join(""); slot.querySelector("[data-t]").textContent = MD.digits(t) + " ث"; };
  draw(); const timer = setInterval(() => { t++; draw(); }, 1000);
  const show = r => { slot.innerHTML = answerHTML(r); bindAnswer(r, slot.querySelector("[data-answer]")); return r; };
  try {
    const resp = await fetch("/api/ask_stream", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    if (!resp.ok || !resp.body) throw new Error((await resp.json().catch(() => ({}))).detail || "stream unavailable");
    const reader = resp.body.getReader(), dec = new TextDecoder(); let buf = "", got = null;
    while (true) { const {value, done} = await reader.read(); if (done) break; buf += dec.decode(value, {stream: true}); let i;
      while ((i = buf.indexOf("\n\n")) >= 0) { const block = buf.slice(0, i); buf = buf.slice(i + 2);
        const kind = (block.match(/^event: (.*)$/m) || [])[1], data = JSON.parse((block.match(/^data: (.*)$/m) || [, "null"])[1]);
        if (kind === "stage") { stage = data; draw(); }
        else if (kind === "passages" && data.length) slot.querySelector("[data-early]").innerHTML = `<details open><summary>النصوص التي وُجدت (${MD.digits(data.length)})، اقرأها حتى يكتمل الجواب</summary>` + data.map(p => `<div class="passage"><h4>[${MD.digits(p.n)}] ${MD.ref(p)} · ${MD.esc(p.kind)}</h4><div class="book">${MD.esc(MD.view(p.text))}</div></div>`).join("") + `</details>`;
        else if (kind === "result") got = show(data); } }
    if (!got) throw new Error("no result");
    return got;
  } catch (e) {
    if (/عدد كبير|الحد اليومي/.test(e.message)) { slot.innerHTML = `<div class="answer dropped">${MD.esc(e.message)}</div>`; return null; }
    try { return show(await MD.api("/api/ask", body)); } catch (e2) { slot.innerHTML = `<div class="answer dropped">${MD.esc(e2.message)}</div>`; return null; }
  } finally { clearInterval(timer); }
}
async function ask(arg) {
  const v = $("#view"), cfg = MD.state.cfg, ctx = MD.state.askPara;
  if (arg === "history") {
    const hist = MD.store.get("history", []);
    v.innerHTML = `<div class="history"><p class="eyebrow">المحادثة</p><h2 class="h2">السجل</h2>${hist.length ? hist.map((h, i) => `<button class="idea" style="width:100%;margin-bottom:8px" data-h="${i}"><b>${MD.esc(h.q)}</b><span>${new Date(h.t).toLocaleString("ar")}</span></button>`).join("") : `<p class="meta">لم تسأل شيئًا بعد.</p>`}
      <p class="meta">السجل محفوظ في هذا المتصفح فقط.</p><a class="btn" href="#/ask">رجوع</a></div>`;
    v.querySelectorAll("[data-h]").forEach(b => b.onclick = () => { MD.state.pendingQ = hist[+b.dataset.h].q; MD.state.thread = []; location.hash = "#/ask"; });
    return;
  }
  const ctxBar = ctx ? `<div class="notice" style="color:var(--ink)">السؤال عن فقرة ${MD.ref({book: "الروض", vol: 1, page: ctx.page})}: «${MD.esc(MD.view(ctx.text.slice(0, 90)))}…» <button class="btn small" id="clearCtx">إلغاء</button></div>` : "";
  const top = `<div class="chat-top noprint"><button class="btn" id="newChat">+ محادثة جديدة</button><a class="btn" href="#/ask/history">السجل</a></div>`;
  const ideas = cfg.suggested.map((s, i) => `<button class="idea" data-q="${MD.esc(s.q)}"><b>${i === 0 ? I.search : i === 1 ? I.book : I.chat} ${MD.esc(["اسأل عن مسألة", "أقوال واختلاف", "خارج الكتب"][i] || s.kind)}</b><span>${MD.esc(s.q)}</span></button>`).join("");
  document.body.classList.toggle("wm-on", !MD.state.thread.length);
  if (!MD.state.thread.length) {
    v.innerHTML = `${top}<div class="hero"><p class="eyebrow">المحادثة</p><h2 class="h2">عمّ تريد أن تسأل؟</h2>${ctxBar}${composerHTML("cf")}<div class="ideas">${ideas}</div>
      <p class="meta" style="margin-top:14px">كل جملة في الجواب لها اقتباس حرفي من صفحة تفتحها بنفسك، ويتحقق نموذج ثانٍ من أن الاقتباس يدل عليها؛ وما لم يثبت يُحذف.</p></div>`;
  } else {
    v.innerHTML = `${top}<div class="thread" id="thread"></div><div class="dock">${ctxBar}${composerHTML("cf")}</div>`;
    const th = $("#thread");
    for (const turn of MD.state.thread.filter(t => t.r)) { th.insertAdjacentHTML("beforeend", `<div class="qbubble">${MD.esc(turn.q)}</div><div data-slot></div>`);
      const slot = th.lastElementChild; if (turn.r) { slot.innerHTML = answerHTML(turn.r); bindAnswer(turn.r, slot.querySelector("[data-answer]")); } }
  }
  const go = async q => {
    MD.state.thread.push({q, r: null});
    if (MD.state.thread.length === 1) await ask();
    const th = $("#thread"); th.insertAdjacentHTML("beforeend", `<div class="qbubble">${MD.esc(q)}</div><div data-slot></div>`);
    const slot = th.lastElementChild; slot.scrollIntoView({behavior: "smooth", block: "start"});
    const btn = document.querySelector("#cf .send"); if (btn) btn.disabled = true;
    const r = await runAsk(q, slot); MD.state.thread[MD.state.thread.length - 1].r = r;
    if (btn) btn.disabled = false;
  };
  bindComposer($("#cf"), go);
  if (ctx) $("#clearCtx").onclick = () => { MD.state.askPara = null; ask(); };
  $("#newChat").onclick = () => { MD.state.thread = []; MD.state.askPara = null; ask(); };
  v.querySelectorAll("[data-q]").forEach(b => b.onclick = () => go(b.dataset.q));
  if (MD.state.pendingQ) { const q = MD.state.pendingQ; MD.state.pendingQ = null; go(q); }
}

/* ---------- overview ---------- */
async function home() {
  const v = $("#view"), cfg = MD.state.cfg, wk = ACT.week(), name = MD.store.get("name", "");
  const days = wk.filter(d => (d.min || 0) + (d.q || 0) + (d.paras || 0) > 0).length, mins = wk.reduce((s, d) => s + (d.min || 0), 0);
  const totals = await Promise.all(cfg.chapters.map(c => MD.api("/api/matn/" + c.id).then(d => d.lines.length).catch(() => 0)));
  const total = totals.reduce((a, b) => a + b, 0), best = MD.store.get("recite_best", {}), mem = Object.values(best).filter(x => x >= 0.9).length;
  const pct = total ? Math.round(100 * mem / total) : 0, max = Math.max(1, ...wk.map(d => d.min || 0));
  const notes = (MD.notebook ? MD.notebook.all() : []).slice(0, 2), cards = MD.srs ? MD.srs.all() : [], due = MD.srs ? MD.srs.dueCards().length : 0;
  const tri = (() => { const s = Math.sqrt(pct / 100); return `<svg class="pyr" width="220" height="180" viewBox="0 0 220 180"><polygon points="110,6 10,176 210,176" fill="var(--teal-soft)"/>${pct ? `<polygon points="${110 - 100 * s},176 ${110 + 100 * s},176 ${110 + 100 * s * 0},${176 - 170 * s}" fill="var(--teal)"/>` : ""}<text x="110" y="150" text-anchor="middle" font-size="30" font-weight="700" fill="${pct > 30 ? "#fff" : "var(--ink)"}">${pct}%</text></svg>`; })();
  v.innerHTML = `<div class="page"><p class="eyebrow">مرحبًا ${MD.esc(name)}</p><h2 class="h2" style="margin-bottom:14px">نظرة عامة</h2><div class="dash">
    <div class="stat teal"><div class="k">سلسلة المذاكرة</div><div class="v">${days}</div><div class="d">أيام من سبعة ذاكرت فيها هذا الأسبوع</div></div>
    <div class="stat"><div class="k">وقت المذاكرة</div><div class="v">${mins >= 60 ? (mins / 60).toFixed(1) : Math.round(mins)}</div><div class="d">${mins >= 60 ? "ساعة" : "دقيقة"} هذا الأسبوع في مدارسة</div></div>
    <div class="panel-side"><div class="row"><b>المحفوظ مقابل المتبقي</b><span class="spacer"></span><span class="meta">متن زاد المستقنع</span></div>${tri}
      <div class="row meta"><span>المحفوظ</span><span class="spacer"></span><span>${MD.digits(mem)} سطرًا</span></div><div class="row meta"><span>المتبقي</span><span class="spacer"></span><span>${MD.digits(total - mem)} سطرًا</span></div>
      <hr style="border:0;border-top:1px solid var(--line2);margin:14px 0"><div class="row"><b style="font-size:13px">دقائق الأسبوع</b><span class="spacer"></span><span class="meta">${MD.digits(Math.round(wk.find(d => d.today)?.min || 0))} اليوم</span></div>
      <div class="bars">${wk.map(d => `<i class="${d.today ? "today" : ""}" style="height:${Math.round(100 * (d.min || 0) / max)}%" title="${MD.digits(Math.round(d.min || 0))} دقيقة"></i>`).join("")}</div><div class="days">${"سحنثرخج".split("").map(x => `<span>${x}</span>`).join("")}</div>
      <p class="meta" style="margin-top:10px">تُحسب هذه الأرقام من استعمالك وتبقى في متصفحك.</p></div>
    <div class="services"><div class="row"><b>الخدمات</b><span class="spacer"></span><span class="meta">اختر ما تبدأ به</span></div><div class="svc">
      <div class="box"><span class="num">01</span><span class="ic">${I.book}</span><h3>المصادر</h3><div class="opts">
        <a href="#/study/water">القراءة مع الشروح</a>${cfg.features.audio ? `<a href="#/listen/water">الاستماع، من أي فقرة</a>` : ""}${cfg.features.recite ? `<a href="#/recite/water">التسميع، بصوتك</a>` : ""}</div><a class="go" href="#/sources">افتح المصادر ←</a></div>
      <div class="box"><span class="num">02</span><span class="ic">${I.chat}</span><h3>المحادثة</h3><span class="meta">اختر نمط المحادثة</span><div class="seg" style="margin-top:6px">${DEPTHS.map(([k, l]) => `<button data-d="${k}" class="${MD.state.depth === k ? "on" : ""}">${l}</button>`).join("")}</div><a class="go" href="#/ask">ابدأ محادثة ←</a></div>
      <div class="box"><span class="num">03</span><span class="ic">${I.cap}</span><h3>المذاكرة</h3><div class="opts">${cfg.features.study_tools ? `<a href="#/tools/water">الملخص والأسئلة</a>` : ""}${cfg.features.notebook ? `<a href="#/notebook">تقييدات (${MD.digits(MD.notebook ? MD.notebook.all().length : 0)})</a>` : ""}${cfg.features.srs ? `<a href="#/review">بطاقات تعليمية (${MD.digits(cards.length)}${due ? `، ${MD.digits(due)} مستحقة` : ""})</a>` : ""}</div>
        ${notes.length ? `<div class="meta" style="margin-top:8px">آخر التقييدات</div>` + notes.map(n => `<div style="font-size:13px"><b>${MD.esc((n.title || "").slice(0, 40))}</b></div>`).join("") : ""}<a class="go" href="#/hub">ابدأ المذاكرة ←</a></div></div></div>
  </div></div>`;
  v.querySelectorAll("[data-d]").forEach(b => b.onclick = () => { MD.state.depth = b.dataset.d; MD.store.set("depth", MD.state.depth); location.hash = "#/ask"; });
}

/* ---------- sources ---------- */
function sources(filter = "all") {
  const v = $("#view"), on = BOOKS.filter(b => b.on), off = BOOKS.filter(b => !b.on);
  const list = filter === "on" ? on : filter === "soon" ? off : BOOKS;
  v.innerHTML = `<div class="page"><p class="eyebrow">المكتبة المعتمدة</p><h2 class="h2">المصادر</h2>
    <div class="row"><div class="filters">${[["all", `الكل ${MD.digits(BOOKS.length)}`], ["on", `المتاحة ${MD.digits(on.length)}`], ["soon", `قريبًا ${MD.digits(off.length)}`]].map(([k, l]) => `<button data-f="${k}" class="${k === filter ? "on" : ""}">${l}</button>`).join("")}</div><span class="spacer"></span>
    <span class="meta">المحمّل الآن: أبواب المياه والآنية والاستنجاء من كتاب الطهارة</span></div>
    <div class="books">${list.map(b => `<div class="bk ${b.on ? "" : "off"}" ${b.on ? `data-open="1" tabindex="0"` : ""}><div class="top">${b.art}<span class="spacer"></span><span class="tag ${b.on ? "" : "soon"}">${b.on ? "متاح" : "قريبًا"}</span></div>
      <h3>${MD.esc(b.title)}</h3><div class="by">${MD.esc(b.by)}</div><div class="by" style="margin-top:4px">${MD.esc(b.role)}${b.ed ? " · " + MD.esc(b.ed) : ""}</div>
      <div class="foot2"><span>${b.pages ? MD.digits(b.pages) + " صفحة" : b.inside ? "ضمن الروض" : "لم يُحمَّل"}</span><span>${b.vols ? (b.vols === 1 ? "مجلد واحد" : MD.digits(b.vols) + " مجلدات") : ""}</span>${b.id ? `<a href="https://app.turath.io/book/${b.id}" target="_blank" rel="noopener" onclick="event.stopPropagation()">تراث ↗</a>` : ""}</div></div>`).join("")}</div>
    <p class="meta" style="margin-top:14px">الكتب المتاحة تُفتح على «الروض المربع» فقرةً فقرة، ومع كل فقرة حاشية ابن قاسم والشرح الممتع وطبعة ركائز. الكتب «قريبًا» وُجدت في تراث وتنتظر اعتماد المختص.</p></div>`;
  v.querySelectorAll("[data-f]").forEach(b => b.onclick = () => sources(b.dataset.f));
  v.querySelectorAll("[data-open]").forEach(b => { b.onclick = () => location.hash = "#/study/water"; b.onkeydown = e => { if (e.key === "Enter") b.click(); }; });
}

/* ---------- study hub ---------- */
function hub() {
  const f = MD.state.cfg.features, cards = MD.srs ? MD.srs.all().length : 0, notes = MD.notebook ? MD.notebook.all().length : 0;
  const tiles = [
    f.study_tools && ["#/tools/water", I.lines, "الملخص", "ملخصات وأسئلة موثقة لكل مقطع"],
    f.notebook && ["#/notebook", I.pen, "تقييدات", `${MD.digits(notes)} تقييدات`],
    f.recite && ["#/recite/water", I.mic, "تسميع المتون", "اختر سطرًا من المتن وسمّعه"],
    f.srs && ["#/review", I.cards, "بطاقات تعليمية", `${MD.digits(cards)} بطاقة`],
  ].filter(Boolean);
  $("#view").innerHTML = `<div class="page narrow"><p class="eyebrow">مذاكرتك</p><h2 class="h2">المذاكرة</h2><div class="hub">${tiles.map(([h, ic, t, d]) => `<a href="${h}"><span class="ic">${ic}</span><h3>${t}</h3><span class="meta">${d}</span></a>`).join("")}</div></div>`;
}

/* ---------- about, contact ---------- */
function about() {
  $("#view").innerHTML = `<div class="page narrow"><p class="eyebrow">مدارسة</p><h2 class="h2">عن مدارسة</h2><div class="card">
  <p>مدارسة تعين طالب العلم على دراسة «الروض المربع» مع حواشيه وشروحه: كل فقرة بجوار ما قاله الشراح عليها، وكل جواب مبني على نص من الكتب المعتمدة مع الجزء والصفحة.</p>
  <ul><li>كل جملة في الجواب لها اقتباس حرفي، ونتحقق آليًّا من وجوده في الصفحة، ثم يتحقق نموذج ثانٍ من أن الاقتباس يدل على الجملة. ما لم يثبت يُحذف ويُعرض عليك أنه حُذف.</li>
  <li>حالة الدليل تظهر على كل جواب: مؤيد بالنص، مؤيد جزئيًّا، أقوال مختلفة (دون ترجيح)، لم يوجد نص.</li>
  <li>لا تفتي مدارسة في الحالات الشخصية، ولا تجيب عن المذاهب الأخرى ولا النوازل المعاصرة التي لا تتناولها الكتب.</li>
  <li>الكتب المحمّلة: الروض المربع (ط الرسالة وط ركائز)، حاشية ابن قاسم، الشرح الممتع؛ في أبواب المياه والآنية والاستنجاء.</li>
  <li>الربط بين الفقرات والحواشي آلي ولم يراجعه مختص بعد؛ ما كان منخفض الثقة عليه وسم.</li>
  <li>لا حسابات ولا بيانات شخصية: الاسم والتقييدات والبطاقات والسجل تبقى في متصفحك. يُحفظ نص السؤال دون أي معرّف لتحسين الخدمة.</li></ul>
  <p class="meta">المصادر من تراث (app.turath.io) وأرقام الصفحات موافقة للمطبوع.</p></div></div>`;
}
function contact() {
  $("#view").innerHTML = `<div class="page narrow"><p class="eyebrow">مدارسة</p><h2 class="h2">للتواصل</h2><div class="card">
    <p>لملاحظة أو خطأ في نص أو جواب أو ربط، اكتبه هنا، ويصل إلى الفريق دون أي بيانات شخصية.</p>
    <textarea id="cmsg" rows="5" style="width:100%;border:1px solid var(--line);border-radius:6px;padding:10px;background:var(--bg)" placeholder="ملاحظتك…"></textarea>
    <div class="row" style="margin-top:10px"><button class="btn primary" id="csend">أرسل</button></div></div></div>`;
  $("#csend").onclick = async () => { const c = $("#cmsg").value.trim(); if (!c) return; MD.toast((await MD.api("/api/report", {kind: "contact", comment: c, where: "contact"})).message); $("#cmsg").value = ""; };
}

/* ---------- router ---------- */
const NAV = [["home", "نظرة عامة", I.home, []], ["sources", "المصادر", I.book, ["study", "listen", "recite"]], ["ask", "المحادثة", I.chat, []], ["hub", "المذاكرة", I.cap, ["tools", "review", "notebook"]]];
const TITLES = {home: "نظرة عامة", sources: "المصادر", study: "الدراسة", ask: "المحادثة", hub: "المذاكرة", listen: "الاستماع", recite: "التسميع", tools: "الملخص والأسئلة", review: "بطاقات تعليمية", notebook: "تقييدات", about: "عن مدارسة", contact: "للتواصل"};
MD.route("home", null, home); MD.route("sources", null, sources); MD.route("study", null, study); MD.route("ask", null, ask);
MD.route("hub", null, hub); MD.route("about", null, about); MD.route("contact", null, contact);
async function render() {
  const [name, arg] = (location.hash.replace(/^#\//, "") || "home").split("/");
  const fn = MD.routes[name] || home;
  $("#nav").innerHTML = NAV.map(([k, l, ic, also]) => `<a href="#/${k}" class="${k === name || also.includes(name) ? "on" : ""}">${ic}<span>${l}</span></a>`).join("");
  $("#title").textContent = TITLES[name] || "مدارسة"; document.title = (TITLES[name] ? TITLES[name] + " · " : "") + "مدارسة";
  $("#side").classList.remove("open"); who();
  document.body.classList.toggle("wm-on", name === "ask" && !MD.state.thread.length || !MD.store.get("name", ""));
  try { await fn(arg); } catch (e) { $("#view").innerHTML = `<div class="page"><div class="card dropped">${MD.esc(e.message)}</div></div>`; }
  window.scrollTo(0, 0);
}
MD.render = render;
window.addEventListener("hashchange", render);
(async () => {
  MD.state.fs = MD.store.get("fs", 19); MD.state.tashkeel = MD.store.get("tashkeel", true); MD.state.depth = MD.store.get("depth", "medium");
  applySettings();
  MD.state.cfg = await MD.api("/api/config");
  $("#disclosure").textContent = MD.state.cfg.disclosure;
  MD.ready = true; document.dispatchEvent(new Event("md:ready"));
  render();
})();
