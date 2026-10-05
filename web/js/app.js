/* Mudarasa front end: router, settings, study view, cited chat. Feature modules (features.js) register more tabs. */
const MD = {routes: {}, tabs: [], paraHooks: [], answerHooks: [], state: {cfg: null, chapters: {}, tashkeel: true, fs: 19, askPara: null, last: null}};
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

/* highlight a quote inside a text, ignoring tashkeel differences (from prep/demo) */
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
/* matn ( … ) in colour; footnote markers like (١) left as they are */
MD.matnHTML = text => MD.esc(MD.view(text)).replace(/\(([^()]*)\)/g, (m, inner) => /^[\s٠-٩0-9]+$/.test(inner) ? m : `<span class="matn">(${inner})</span>`);

/* ---------- settings ---------- */
function applySettings() {
  document.documentElement.style.setProperty("--fs", MD.state.fs + "px");
  $("#tashkeel").textContent = "التشكيل: " + (MD.state.tashkeel ? "ظاهر" : "مخفي");
  $("#tashkeel").setAttribute("aria-pressed", MD.state.tashkeel);
  const th = MD.store.get("theme", null); if (th) document.documentElement.dataset.theme = th;
}
$("#fsUp").onclick = () => { MD.state.fs = Math.min(32, MD.state.fs + 2); MD.store.set("fs", MD.state.fs); applySettings(); };
$("#fsDown").onclick = () => { MD.state.fs = Math.max(14, MD.state.fs - 2); MD.store.set("fs", MD.state.fs); applySettings(); };
$("#tashkeel").onclick = () => { MD.state.tashkeel = !MD.state.tashkeel; MD.store.set("tashkeel", MD.state.tashkeel); applySettings(); render(); };
$("#theme").onclick = () => {
  const d = document.documentElement;
  const dark = d.dataset.theme === "dark" || (!d.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
  d.dataset.theme = dark ? "light" : "dark"; MD.store.set("theme", d.dataset.theme);
};

/* ---------- study view ---------- */
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
  return p.mumti.map(s => {
    const a = s.lines[0], b = s.lines[s.lines.length - 1] || a;
    return `<div class="note"><div class="lemma">${MD.esc(MD.view(s.heading))} ${AUTO[s.method] ? `<span class="auto">${AUTO[s.method]}</span>` : ""}</div>
    <div class="book">${s.lines.map(l => MD.esc(MD.view(l.text))).join("<br>")}</div>
    <div class="meta">${a ? MD.ref({book: "الشرح الممتع", vol: a.vol, page: a.page}) + (b && b.page !== a.page ? "–" + MD.digits(b.page) : "") + ` · <a href="${a.link}" target="_blank" rel="noopener">افتح الصفحة</a>` : ""}</div></div>`;
  }).join("");
}
function rakaiz(p) {
  let h = "";
  if (p.rakaiz_paras.length) h += `<p class="meta">النص نفسه في طبعة ركائز (مشكول):</p>` + p.rakaiz_paras.map(r => `<div class="book">${MD.matnHTML(r.text)}</div><div class="meta">${MD.ref({book: "الروض (ط ركائز)", vol: r.vol, page: r.page})} · <a href="${r.link}" target="_blank" rel="noopener">افتح الصفحة</a></div>`).join("");
  const diffs = p.units.filter(u => u.edition_diffs && u.edition_diffs.length);
  if (diffs.length) {
    h += `<p class="meta" style="margin-top:10px">فروق بين الطبعتين (تُعرض دون ترجيح):</p>`;
    h += diffs.map(u => `<div class="diff meta">عند «${MD.esc(u.matn.slice(0, 40))}»: ` + u.edition_diffs.map(([t, a, b]) => `${a ? `<del>${MD.esc(a)}</del>` : ""} ${b ? `<ins>${MD.esc(b)}</ins>` : ""}`).join(" · ") + `</div>`).join("");
  }
  if (p.rakaiz_notes.length) h += `<p class="meta" style="margin-top:10px">حواشي المحققين في طبعة ركائز (تخريج وفروق نسخ):</p>` + p.rakaiz_notes.map(n => `<div class="note"><div class="book">${MD.esc(MD.view(n.text))}</div><div class="meta">${MD.ref({book: "الروض (ط ركائز)", vol: n.vol, page: n.page})} · حاشية ${MD.digits(n.n)} · <a href="${n.link}" target="_blank" rel="noopener">افتح الصفحة</a></div></div>`).join("");
  return h || `<p class="meta">لم تُربط هذه الفقرة بطبعة ركائز.</p>`;
}

function panelHTML(p) {
  const tabs = [["iq", `حاشية ابن قاسم (${MD.digits(p.iq.length)})`], ["mumti", `الشرح الممتع (${MD.digits(p.mumti.length)})`], ["rk", "طبعة ركائز والفروق"]];
  return `<div class="panel" data-panel="${p.id}">
    <div class="ptabs" role="tablist">${tabs.map(([k, l], i) => `<button role="tab" data-t="${k}" class="${i ? "" : "on"}">${l}</button>`).join("")}</div>
    <div data-body>${notesIQ(p)}</div>
    <p class="meta">رُبطت الحواشي والشروح بالفقرة آليًّا ولم يراجعها مختص بعد.</p>
    <div class="row noprint" data-actions><button class="btn primary" data-ask>اسأل عن هذه الفقرة</button></div></div>`;
}

async function study(cid = "water") {
  const v = $("#view");
  v.innerHTML = `<div class="spin">يحمّل الباب…</div>`;
  const ch = await chapterData(cid);
  const cfg = MD.state.cfg;
  let h = `<div class="chapters" role="group" aria-label="الأبواب">${cfg.chapters.map(c => `<button class="${c.id === cid ? "on" : ""}" data-ch="${c.id}">${MD.esc(c.title)}</button>`).join("")}</div>`;
  h += `<div class="suggest" aria-label="جرّب سؤالًا"><span class="meta">جرّب:</span>${cfg.suggested.map(s => `<button data-try="${MD.esc(s.q)}">${MD.esc(s.q)}<small>${MD.esc(s.kind)}</small></button>`).join("")}</div>`;
  h += `<p class="meta">«الروض المربع» (ط الرسالة)؛ المتن (زاد المستقنع) بلون مختلف. اضغط على فقرة لتفتح حواشيها وشروحها.</p>`;
  h += ch.paras.map(p => `<div class="card para" data-pid="${p.id}" tabindex="0">
    ${p.heading ? `<div class="meta">${MD.esc(p.heading)}</div>` : ""}
    <div class="book" data-text>${MD.matnHTML(p.text)}</div>
    <div class="refs"><span class="pill">${MD.ref({book: "الروض", vol: p.vol, page: p.page})}</span>
    ${p.iq.length ? `<span class="pill">ابن قاسم ${MD.digits(p.iq.length)}</span>` : ""}${p.mumti.length ? `<span class="pill">الممتع ${MD.digits(p.mumti.length)}</span>` : ""}
    ${p.rakaiz_notes.length ? `<span class="pill">تخريج وفروق ${MD.digits(p.rakaiz_notes.length)}</span>` : ""}</div></div>`).join("");
  v.innerHTML = h;
  v.querySelectorAll("[data-ch]").forEach(b => b.onclick = () => location.hash = "#/study/" + b.dataset.ch);
  v.querySelectorAll("[data-try]").forEach(b => b.onclick = () => { MD.state.askPara = null; MD.state.pendingQ = b.dataset.try; location.hash = "#/ask"; });
  v.querySelectorAll(".para").forEach(el => {
    const open = e => {
      if (e.target.closest(".panel") || e.target.closest("a")) return;
      const p = ch.paras.find(x => x.id === el.dataset.pid);
      const existing = el.querySelector(".panel");
      v.querySelectorAll(".panel").forEach(x => x.remove()); v.querySelectorAll(".para.open").forEach(x => x.classList.remove("open"));
      if (existing) return;
      el.classList.add("open"); el.insertAdjacentHTML("beforeend", panelHTML(p));
      const panel = el.querySelector(".panel");
      panel.querySelectorAll("[data-t]").forEach(b => b.onclick = () => {
        panel.querySelectorAll("[data-t]").forEach(x => x.classList.toggle("on", x === b));
        panel.querySelector("[data-body]").innerHTML = b.dataset.t === "iq" ? notesIQ(p) : b.dataset.t === "mumti" ? notesMumti(p) : rakaiz(p);
      });
      panel.querySelector("[data-ask]").onclick = () => { MD.state.askPara = {id: p.id, text: p.text, page: p.page}; location.hash = "#/ask"; };
      MD.paraHooks.forEach(fn => fn(p, panel, el, cid));
    };
    el.onclick = open;
    el.onkeydown = e => { if (e.key === "Enter" && e.target === el) open(e); };
  });
}

/* ---------- ask (cited chat) ---------- */
function answerHTML(r) {
  let h = `<div class="card" id="answer"><div class="row"><span class="badge s-${r.status}">${MD.esc(r.status_ar)}</span>
    <span class="meta">${r.cached ? "جواب محفوظ" : (r.latency_s ? MD.digits(Math.round(r.latency_s)) + " ثانية" : "")}</span></div>`;
  if (r.message) h += `<p>${MD.esc(r.message)}</p>`;
  const quoteFor = {};
  for (const s of r.sentences || []) {
    (quoteFor[s.n] = quoteFor[s.n] || []).push(s.quote);
    h += `<p class="sent book" style="font-size:calc(var(--fs) - 1px)">${MD.esc(MD.view(s.text))}${s.cite ? `<button class="chip" data-p="${s.n}" title="افتح المقطع والاقتباس">${MD.ref(s.cite)}</button>` : ""}</p>`;
  }
  if ((r.dropped || []).length) {
    h += `<details><summary>حُذفت ${MD.digits(r.dropped.length)} من الجمل لأن توثيقها لم يثبت</summary>`;
    for (const d of r.dropped) h += `<p class="dropped">✕ ${MD.esc(MD.view(d.text))} <span class="meta">(${MD.esc(d.reason)})</span></p>`;
    h += `</details>`;
  }
  if ((r.passages || []).length) {
    h += `<details id="ps"${(r.sentences || []).length ? "" : " open"}><summary>النصوص التي قُرئت للجواب (${MD.digits(r.passages.length)})</summary>`;
    for (const p of r.passages) {
      h += `<div class="passage" id="p${p.n}"><h4>[${MD.digits(p.n)}] ${MD.ref(p)} · ${MD.esc(p.kind)} · <a href="${p.link}" target="_blank" rel="noopener">افتح الصفحة في تراث</a></h4><div class="book">${MD.highlight(p.text, (quoteFor[p.n] || [])[0])}</div></div>`;
    }
    h += `</details>`;
  }
  h += `<div class="row noprint" style="margin-top:10px" data-answer-actions><span class="spacer"></span><button class="btn small" data-report>بلّغ عن خطأ</button></div></div>`;
  return h;
}
function bindAnswer(r) {
  const a = $("#answer"); if (!a) return;
  a.querySelectorAll(".chip").forEach(b => b.onclick = () => {
    $("#ps").open = true; a.querySelectorAll(".passage").forEach(x => x.classList.remove("focus"));
    const el = $("#p" + b.dataset.p); el.classList.add("focus"); el.scrollIntoView({behavior: "smooth", block: "center"});
  });
  a.querySelector("[data-report]").onclick = async () => {
    const c = prompt("ما الخطأ؟ (مثلًا: الصفحة غير صحيحة، أو الجملة لا يدل عليها النص)");
    if (c === null) return;
    const res = await MD.api("/api/report", {kind: "answer", question: r.question, comment: c, where: location.hash});
    MD.toast(res.message);
  };
  MD.answerHooks.forEach(fn => fn(r, a));
}
async function ask() {
  const v = $("#view"), cfg = MD.state.cfg, ctx = MD.state.askPara;
  v.innerHTML = `${ctx ? `<div class="context">السؤال عن فقرة ${MD.ref({book: "الروض", vol: 1, page: ctx.page})}: «${MD.esc(MD.view(ctx.text.slice(0, 90)))}…» <button class="btn small" id="clearCtx">إلغاء</button></div>` : ""}
    <div class="suggest" aria-label="أسئلة مقترحة">${cfg.suggested.map(s => `<button data-q="${MD.esc(s.q)}">${MD.esc(s.q)}<small>${MD.esc(s.kind)}</small></button>`).join("")}</div>
    <form class="askf" id="f"><textarea id="q" placeholder="اكتب سؤالك عن أبواب المياه والآنية والاستنجاء…" aria-label="السؤال"></textarea><button id="go">اسأل</button></form>
    <div id="out">${MD.state.last ? answerHTML(MD.state.last) : ""}</div>`;
  if (MD.state.last) bindAnswer(MD.state.last);
  if (ctx) $("#clearCtx").onclick = () => { MD.state.askPara = null; ask(); };
  const go = async q => {
    if (!q.trim()) return;
    $("#go").disabled = true; let t = 0;
    $("#out").innerHTML = `<div class="card spin" id="sp">يبحث في الكتب ويكتب الجواب ثم يتحقق من كل جملة…</div>`;
    const timer = setInterval(() => { t++; const sp = $("#sp"); if (sp) sp.textContent = `يبحث في الكتب ويكتب الجواب ثم يتحقق من كل جملة… ${MD.digits(t)} ث`; }, 1000);
    try { const r = await MD.api("/api/ask", {question: q, para: ctx ? ctx.id : null}); MD.state.last = r; $("#out").innerHTML = answerHTML(r); bindAnswer(r); }
    catch (e) { $("#out").innerHTML = `<div class="card dropped">${MD.esc(e.message)}</div>`; }
    finally { clearInterval(timer); $("#go").disabled = false; }
  };
  $("#f").onsubmit = e => { e.preventDefault(); go($("#q").value); };
  $("#q").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); go($("#q").value); } });
  v.querySelectorAll("[data-q]").forEach(b => b.onclick = () => { $("#q").value = b.dataset.q; go(b.dataset.q); });
}
MD.answerHTML = answerHTML;

function about() {
  $("#view").innerHTML = `<div class="card"><h2>عن مدارسة</h2>
  <p>مدارسة تعين طالب العلم على دراسة «الروض المربع» مع حواشيه وشروحه: كل فقرة بجوار ما قاله الشراح عليها، وكل جواب مبني على نص من الكتب المعتمدة مع الجزء والصفحة.</p>
  <ul><li>كل جملة في الجواب يجب أن يكون لها اقتباس حرفي، ونتحقق آليًّا من وجود الاقتباس في الصفحة، ثم يتحقق نموذج ثانٍ من أن الاقتباس يدل على الجملة. ما لم يثبت يُحذف ويُعرض عليك أنه حُذف.</li>
  <li>حالة الدليل تظهر على كل جواب: مؤيد بالنص، مؤيد جزئيًّا، أقوال مختلفة (دون ترجيح)، لم يوجد نص.</li>
  <li>لا تفتي مدارسة في الحالات الشخصية، ولا تجيب عن المذاهب الأخرى ولا النوازل المعاصرة التي لا تتناولها الكتب.</li>
  <li>الكتب المحمّلة: الروض المربع (ط الرسالة وط ركائز)، حاشية ابن قاسم، الشرح الممتع؛ في أبواب المياه والآنية والاستنجاء.</li>
  <li>الربط بين الفقرات والحواشي آلي ولم يراجعه مختص بعد؛ ما كان منخفض الثقة عليه وسم.</li>
  <li>لا نحفظ أي بيانات شخصية. يُحفظ نص السؤال دون أي معرّف لتحسين الخدمة. ما تحفظه في «دفتري» و«المراجعة» يبقى في متصفحك.</li></ul></div>`;
}

/* ---------- router ---------- */
MD.route("study", "الدراسة", study);
MD.route("ask", "اسأل", ask);
MD.route("about", null, about);
function renderTabs(cur) {
  $("#tabs").innerHTML = MD.tabs.map(t => `<a href="#/${t.name}" class="${t.name === cur ? "on" : ""}">${t.label}${t.exp ? `<span class="exp">تجريبي</span>` : ""}</a>`).join("");
}
async function render() {
  const [name, arg] = (location.hash.replace(/^#\//, "") || "study").split("/");
  const fn = MD.routes[name] || study;
  renderTabs(name);
  try { await fn(arg); } catch (e) { $("#view").innerHTML = `<div class="card dropped">${MD.esc(e.message)}</div>`; }
}
MD.render = render;
window.addEventListener("hashchange", render);
(async () => {
  MD.state.fs = MD.store.get("fs", 19); MD.state.tashkeel = MD.store.get("tashkeel", true);
  applySettings();
  MD.state.cfg = await MD.api("/api/config");
  $("#disclosure").textContent = MD.state.cfg.disclosure;
  MD.ready = true;
  document.dispatchEvent(new Event("md:ready"));
  render();
})();
