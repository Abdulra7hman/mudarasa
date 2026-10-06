"""Build the web app from the team's design (Claude Design export) and connect it to Mudarasa's backend.

Input : design/madarasa.html   (the bundled export, unchanged; re-export from Claude Design and re-run this script)
Output: web/index.html          (the same bundle, with integration code appended to the design's logic class)

What the integration changes (everything else in the design runs as designed):
  send()       chat answers from /api/ask_stream: cited, quote-checked, judged; stages while waiting; citation chips and
               evidence status under each answer (markup patch)
  lookup()     word meaning (lexical / shar'i / contextual) generated from library passages via /api/meaning, with pages
  summarize()  summaries of the Zad family from the verified study tools (/api/tools/*)
  zad text     the reader shows the real Rakaiz (vocalized) paragraphs of the three loaded chapters
  startPlay()  real Azure recordings, the highlight follows the recorded word timings; click a word = play from it
  toggleRec()  recitation checked by Azure speech-to-text (words revealed as recited, mistakes marked)
Usage: python -m scripts.build_ui
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "design" / "madarasa.html"
OUT = ROOT / "web" / "index.html"

INTEGRATION = r"""
;(function(){
const P = Component.prototype;
const toAr = n => String(n).replace(/\d/g, d => '٠١٢٣٤٥٦٧٨٩'[d]);
const api = async (path, body) => { const r = await fetch(path, body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {}); if (!r.ok) throw new Error((await r.json().catch(()=>({}))).detail || r.status); return r.json(); };
const NORM = s => String(s||'').replace(/[ؐ-ًؚ-ٰٟۖ-ۭـ]/g,'').replace(/[إأآٱ]/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه').replace(/ؤ/g,'و').replace(/ئ/g,'ي').replace(/[^ء-ي0-9 ]/g,' ').replace(/\s+/g,' ').trim();
const STEM = w => { for (const p of ['وال','فال','بال','كال','لل','ال','و','ف','ب','ل','ك']) if (w.startsWith(p) && w.length-p.length>=2) { w = w.slice(p.length); break; } return w; };
const KEY = w => STEM(NORM(w));
const sim = (a, b) => { if (a===b) return 1; const m=a.length, n=b.length; if (!m||!n) return 0; const d=Array.from({length:m+1},(_,i)=>[i,...Array(n).fill(0)]); for (let j=1;j<=n;j++) d[0][j]=j; for (let i=1;i<=m;i++) for (let j=1;j<=n;j++) d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]===b[j-1]?0:1)); return 1-d[m][n]/Math.max(m,n); };
const STATUS_COLOR = {supported:'oklch(0.55 0.13 150)', partial:'oklch(0.62 0.12 75)', differing:'var(--color-accent-700)', not_found:'oklch(0.55 0.15 30)'};
const CHAPTERS = [['water','باب المياه'],['vessels','باب الآنية'],['istinja','باب الاستنجاء']];
const CH_TITLE = Object.fromEntries(CHAPTERS.map(([c, t]) => [t, c])); CH_TITLE['كتاب الطهارة'] = 'water';
const NEXT_CH = {water:'vessels', vessels:'istinja'};
const SPLIT = t => String(t || '').split(/\s+/).filter(Boolean);
const CLEAN = t => String(t || '').replace(/\s*\n\s*/g, ' ').trim();
// The Zad family in the reader: the Rawd (vocalized Rakaiz edition, for books r1 and r2), Ibn Qasim's Hashiya (r3),
// al-Sharh al-Mumti' (r4); the Zad matn (vocalized) when reciting. One chapter is shown at a time.
const REAL_SRC = {
  iqh:   {id:'iqh', name:'حاشية الروض المربع', short:'حاشية ابن قاسم', art:'الفقه', author:'عبد الرحمن بن محمد بن قاسم', section:'', pct:3, text:''},
  mumti: {id:'mumti', name:'الشرح الممتع على زاد المستقنع', short:'الشرح الممتع', art:'الفقه', author:'محمد بن صالح العثيمين', section:'', pct:9, text:''}};
const BOOK_SRC = {r3:'iqh', r4:'mumti'};
const SAY_PREFIX = 'قال ابن قاسم: ';
const estimate = (dur, words, lead) => {   // Ibn Qasim clips have no word marks: spread the clip over the words by length
  const lens = words.map(w => w.length + 1), tot = SAY_PREFIX.length + lens.reduce((x, y) => x + y, 0); let acc = SAY_PREFIX.length;
  const out = [{t:0, i:0}]; words.forEach((w, k) => { out.push({t: Math.round(dur * acc / tot), i: k + lead}); acc += lens[k]; }); return out; };
const paraOf = (V, i) => { let k = 0; for (let j = 0; j < V.offs.length; j++) { if (V.offs[j] <= i) k = j; else break; } return k; };

P.__loadReal = async function(){
  try {
    const all = f => Promise.all(CHAPTERS.map(([c]) => f(c)));
    const [lists, mans, chaps, matns] = await Promise.all([all(c => api('/api/listen/' + c)), all(c => api('/api/audio/' + c).catch(() => ({clips:[]}))),
      all(c => api('/api/chapter/' + c).catch(() => ({paras:[]}))), all(c => api('/api/matn/' + c).catch(() => ({lines:[]})))]);
    const clips = {}; mans.forEach(m => (m.clips || []).forEach(c => clips[c.id] = c));
    const R = {zad:[], iqh:[], mumti:[], matn:[]}, est = {};
    CHAPTERS.forEach(([c], ci) => {
      const seen = new Set();
      lists[ci].paras.forEach(p => {
        R.zad.push({id:p.id, text:CLEAN(p.text), ch:c, page:p.page, vol:p.vol, link:p.link, anchors:p.anchor_paras || []});
        (p.notes || []).forEach(nt => { if (seen.has(nt.id)) return; seen.add(nt.id);
          const ws = SPLIT(CLEAN(nt.text)); R.iqh.push({id:nt.id, text:'(' + toAr(nt.n) + ') ' + ws.join(' '), ch:c});
          if (clips[nt.id]) est[nt.id] = estimate(clips[nt.id].duration_ms, ws, 1); }); });
      const ms = new Set();
      (chaps[ci].paras || []).forEach(p => (p.mumti || []).forEach(m => { if (ms.has(m.id)) return; ms.add(m.id);
        const lines = (m.lines || []).filter(l => !/^[.\s…]*$/.test(l.text)), l0 = lines[0] || {};
        const text = CLEAN((m.heading ? '«' + m.heading.trim().replace(/[،,]$/, '') + '» ' : '') + lines.map(l => l.text).join(' '));
        if (text) R.mumti.push({id:m.id, text, ch:c, page:l0.page, vol:l0.vol, link:l0.link}); }));
      (matns[ci].lines || []).forEach(l => R.matn.push({id:'matn-' + c + '-' + l.n, text:l.words.map(w => w.w).join(' '), ch:c, page:l.page}));
    });
    this.__R = R; this.__clips = clips; this.__est = est; this.__V = null; this.cache = {};
    // the sample bookmark points at «وهي ارتفاع الحدث» in the real text
    const wz = R.zad.filter(p => p.ch === 'water').flatMap(p => SPLIT(p.text)), bi = wz.findIndex(w => NORM(w) === 'وهي');
    this.setState(s => ({realLoaded: Date.now(), bms: s.bms.map(b => b.id === 1 && b.src === 'zad' ? {...b, i: bi >= 0 ? bi : 0, rch:'water'} : b)}));
  } catch(e) { console.warn('real text not loaded', e); }
};
// which real paragraphs the reader shows for a source: the open chapter, or the whole matn when reciting
P.__view = function(id){
  if (!this.__R) return null;
  const s = this.state || {}, src = s.mode === 'recite' && (id === 'zad' || REAL_SRC[id]) ? 'matn' : id;
  if (!this.__R[src]) return null;
  const ch = src === 'matn' ? 'all' : (s.rch || 'water'), key = src + ':' + ch;
  if (!this.__V || this.__V.key !== key) {
    const paras = this.__R[src].filter(p => ch === 'all' || p.ch === ch); let n = 0;
    const offs = paras.map(p => { const o = n; n += SPLIT(p.text).length; return o; });
    this.__V = {key, src, ch, paras, offs, n};
  }
  return this.__V;
};
const _parse = P.parse;
P.parse = function(id){
  const V = this.__view(id); if (!V) return _parse.call(this, id);
  if (this.cache[V.key]) return this.cache[V.key];
  let n = 0; const paras = V.paras.map(p => SPLIT(p.text).map(t => ({t, i:n++})));
  return this.cache[V.key] = {paras, n};
};
P.__goChapter = function(c){
  this.stopTimers(); this.setState({rch:c, cur:-1, playing:false, rev:{}, pos:0, mean:null});
  setTimeout(() => { const el = document.querySelector('[data-wi="0"]'); if (el) el.scrollIntoView({block:'center', behavior:'smooth'}); }, 60);
};

const _mount = P.componentDidMount;
P.componentDidMount = function(){
  this.BOOKS = this.BOOKS.map(b => BOOK_SRC[b.id] ? {...b, src: BOOK_SRC[b.id]} : b);
  this.EXTRA = [...this.EXTRA, ...Object.values(REAL_SRC)];
  this.REAL = [...this.REAL, ...Object.keys(REAL_SRC)];
  window.__mudarasa = this;
  _mount && _mount.call(this); this.__loadReal(); };
const _stop = P.stopTimers;
P.stopTimers = function(){ _stop.call(this); if (this.__audio) { this.__audio.pause(); this.__audio = null; } this.__stopRec && this.__stopRec(); };

// the table of contents of the Zad family: the loaded chapters open; page numbers from the source where known
const _tocOf = P.tocOf;
P.tocOf = function(b){
  const src = b && b.src;
  if (!this.__R || !(src === 'zad' || REAL_SRC[src])) return _tocOf.call(this, b);
  const first = c => (this.__R[src] || []).find(p => p.ch === c && p.page);
  return this.TOC_ZAD.map(e => { const c = CH_TITLE[e[0]]; const f = c && first(c);
    return {t:e[0], lvl:e[1] || 0, para: c ? 0 : undefined, pg: f ? toAr(f.page) : '', ch:c}; });
};

/* ---------- listening: real recordings, highlight from the recorded word timings ---------- */
const _startPlay = P.startPlay;
P.startPlay = function(from, speed){
  const V = this.__view(this.state.srcId);
  if (!V) return _startPlay.call(this, from, speed);
  clearInterval(this.pt); if (this.__audio) { this.__audio.pause(); this.__audio = null; }
  if (!V.paras.some(p => this.__clips[p.id])) { this.setState({playing:false}); this.soon('الاستماع إلى «' + this.srcOf(this.state.srcId).name + '»'); return; }
  const rate = speed || this.state.speed || 1;
  const play = (pi, word) => {
    if (this.__V !== V) return;   // chapter or book changed
    if (pi >= V.paras.length) { const nx = NEXT_CH[V.ch];
      if (nx && this.state.playing) this.setState({rch:nx, cur:0}, () => this.startPlay(0, speed)); else this.setState({playing:false}); return; }
    const p = V.paras[pi], off = V.offs[pi], clip = this.__clips[p.id];
    if (!clip) return play(pi + 1, V.offs[pi + 1]);
    const marks = clip.words && clip.words.length ? clip.words : (this.__est[p.id] || []);
    const a = new Audio('/audio/' + clip.file); a.playbackRate = rate; this.__audio = a;
    const w0 = marks.find(w => w.i >= word - off);
    a.addEventListener('loadedmetadata', () => { if (w0 && w0.t > 0) a.currentTime = Math.max(0, w0.t / 1000 - 0.05); }, {once:true});
    a.ontimeupdate = () => { const t = a.currentTime * 1000; let k = -1; for (const w of marks) { if (w.t <= t) k = w.i; else break; } if (k >= 0 && this.state.cur !== off + k) this.setState({cur: off + k}); };
    a.onended = () => { if (this.__audio === a) play(pi + 1, V.offs[pi + 1]); };
    a.play().catch(() => this.setState({playing:false}));
  };
  this.setState({cur: from, playing: true});
  play(paraOf(V, Math.max(0, from)), Math.max(0, from));
};
const _togglePlay = P.togglePlay;
P.togglePlay = function(){
  const V = this.__view(this.state.srcId);
  if (!V) return _togglePlay.call(this);
  if (this.state.playing) { if (this.__audio) this.__audio.pause(); this.setState({playing:false}); return; }
  this.startPlay(this.state.cur < 0 || this.state.cur >= V.n - 1 ? 0 : this.state.cur);
};

/* ---------- recitation: Azure speech-to-text, words revealed as recited ---------- */
const loadSDK = () => window.SpeechSDK ? Promise.resolve() : new Promise((ok, no) => { const s = document.createElement('script'); s.src = 'https://cdn.jsdelivr.net/npm/microsoft-cognitiveservices-speech-sdk@1.43.0/distrib/browser/microsoft.cognitiveservices.speech.sdk.bundle-min.js'; s.onload = ok; s.onerror = no; document.head.append(s); });
const _toggleRec = P.toggleRec;
P.toggleRec = async function(){
  if (this.state.recOn) { this.__stopRec && this.__stopRec(); this.setState({recOn:false}); return; }
  const words = this.parse(this.state.srcId).paras.flat();
  const tok = await api('/api/speech/token').catch(() => ({available:false}));
  if (!tok.available) return _toggleRec.call(this);
  try { await loadSDK(); } catch(e) { return _toggleRec.call(this); }
  const S = window.SpeechSDK, cfg = S.SpeechConfig.fromAuthorizationToken(tok.token, tok.region); cfg.speechRecognitionLanguage = 'ar-SA';
  const rec = new S.SpeechRecognizer(cfg, S.AudioConfig.fromDefaultMicrophoneInput());
  const pl = S.PhraseListGrammar.fromRecognizer(rec); words.slice(this.state.pos, this.state.pos + 60).forEach(w => pl.addPhrase(w.t.replace(/[،.:«»؛]/g,'')));
  const consume = text => this.setState(s => {
    const heard = String(text).split(/\s+/).map(KEY).filter(Boolean); let pos = s.pos, ok = 0; const rev = {...s.rev};
    for (const h of heard) { if (pos >= words.length) break;
      const e = KEY(words[pos].t);
      if (sim(h, e) >= 0.75 || (h.length > 2 && e.includes(h) && h.length / e.length > 0.6)) { rev[pos] = 'ok'; pos++; ok++; continue; }
      let j = 1; while (j <= 3 && pos + j < words.length && sim(h, KEY(words[pos + j].t)) < 0.75) j++;
      if (j <= 3 && pos + j < words.length) { for (let k = pos; k < pos + j; k++) rev[k] = 'err'; rev[pos + j] = 'ok'; pos += j + 1; ok++; continue; }
      rev[pos] = 'err'; pos++; }
    // an utterance that mostly doesn't match this place (a repeat, or a different passage) is not marked: ask to resume
    if (heard.length >= 3 && ok / heard.length < 0.4) return {recMiss: 'لم يطابق ما سمعته هذا الموضع؛ أكمل من «' + words[s.pos].t + '»'};
    return {rev, pos, recOn: pos < words.length, recMiss: null};
  });
  rec.recognized = (_, e) => { if (e.result && e.result.text) consume(e.result.text); if (this.state.pos >= words.length) this.__stopRec(); };
  this.__stopRec = () => { try { rec.stopContinuousRecognitionAsync(() => rec.close(), () => {}); } catch(e) {} this.__stopRec = null; };
  rec.startContinuousRecognitionAsync();
  this.setState({recOn:true});
};

/* ---------- chat: cited, checked answers ---------- */
const STAGE_TEXT = {search:'يبحث في المصادر…', write:'وجد النصوص، ويكتب الجواب منها…', verify:'يتحقق من كل جملة واقتباسها…'};
const streamAsk = async (body, onStage) => {
  const resp = await fetch('/api/ask_stream', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if (!resp.ok || !resp.body) return api('/api/ask', body);
  const reader = resp.body.getReader(), dec = new TextDecoder(); let buf = '', got = null;
  while (true) { const {value, done} = await reader.read(); if (done) break; buf += dec.decode(value, {stream:true}); let i;
    while ((i = buf.indexOf('\n\n')) >= 0) { const block = buf.slice(0, i); buf = buf.slice(i + 2);
      const kind = (block.match(/^event: (.*)$/m) || [])[1], data = JSON.parse((block.match(/^data: (.*)$/m) || [, 'null'])[1]);
      if (kind === 'stage') onStage(data); else if (kind === 'result') got = data; } }
  return got || api('/api/ask', body);
};
P.send = async function(text){
  const q = (text ?? this.state.draft).trim(); if (!q) return;
  if ((this.state.ctx || 0) !== 0) { this.soon(this.CTX[this.state.ctx]); return; }
  const ctx = this.CTX[0], depth = this.state.depth, id = Date.now();
  const dLabel = depth == null ? '' : ' · ' + ['خفيفة','متوسطة','مفصلة'][depth];
  this.setState(s => ({draft:'', msgs:[...s.msgs, {id, q, a:'', pending:true, shown:0, ctx:ctx + dLabel, stage:'search'}]}));
  const upd = f => this.setState(s => ({msgs: s.msgs.map(m => m.id === id ? {...m, ...f(m)} : m)}));
  let r = null;
  try { r = await streamAsk({question:q, depth:{0:'short', 1:'medium', 2:'long'}[depth] || 'medium'}, stage => upd(() => ({stage}))); } catch(e) {}
  if (!r) r = {sentences:[], message:'تعذّر الوصول إلى الخادم الآن. حاول بعد قليل.', status:'not_found', status_ar:'لم يوجد نص'};
  const cites = [], idx = {};
  const lines = (r.sentences || []).map(s => { if (!s.cite) return s.text;
    const k = s.cite.book + '|' + s.cite.page; if (!(k in idx)) { idx[k] = cites.length; cites.push({n: toAr(cites.length + 1), label: s.cite.book + '، ج' + toAr(s.cite.vol) + ' ص' + toAr(s.cite.page), link: s.cite.link, quote: s.quote}); }
    return s.text + ' (' + toAr(idx[k] + 1) + ')'; });
  const a = [r.message, ...lines].filter(Boolean).join('\n');
  const dropped = (r.dropped || []).length;
  upd(() => ({a, pending:false, shown:0, cites, status:r.status, status_ar:r.status_ar, dropped, cached:!!r.cached}));
  clearInterval(this.st); let n = 0; const total = a.split(' ').length;
  this.st = setInterval(() => { n += 1; upd(() => ({shown:n})); if (n >= total) clearInterval(this.st); }, 38);
};
const ZAD_NAMES = {r1:'الروض المربع شرح زاد المستقنع', r2:'الروض المربع (مشكول)'};
const _rv = P.renderVals;
P.renderVals = function(){
  const s = this.state, real = !!this.__view(s.srcId);
  if (this.__R) {   // the reader's title, author and section follow the open book and chapter
    const z = this.EXTRA.find(x => x.id === 'zad'), chT = (CHAPTERS.find(c => c[0] === (s.rch || 'water')) || [])[1];
    if (z && s.mode === 'recite') Object.assign(z, {name:'زاد المستقنع', author:'موسى الحجاوي', section:'كتاب الطهارة: المياه، الآنية، الاستنجاء'});
    else if (z) Object.assign(z, {name: ZAD_NAMES[s.rBook] || ZAD_NAMES.r2, author:'منصور بن يونس البهوتي', section:'كتاب الطهارة · ' + chT});
    for (const r of Object.values(REAL_SRC)) { const e = this.EXTRA.find(x => x.id === r.id); if (!e) continue;   // reciting is always the Zad matn
      if (s.mode === 'recite') Object.assign(e, {name:'زاد المستقنع', author:'موسى الحجاوي', section:'كتاب الطهارة: المياه، الآنية، الاستنجاء'});
      else Object.assign(e, {name:r.name, author:r.author, section:'كتاب الطهارة · ' + chT}); }
  }
  const v = _rv.call(this);
  if (!v) return v;
  if (real) {
    let k = 0; (v.paras || []).forEach(p => (p.words || []).forEach(w => { w.i = k++; }));
    const tocFix = list => (list || []).map(e => { const c = CH_TITLE[e.t]; if (!c) return e; const on = c === (s.rch || 'water') && e.t !== 'كتاب الطهارة';
      return {...e, go: () => this.__goChapter(c), bg: on ? 'var(--color-accent-100)' : 'transparent', c: on ? 'var(--color-accent-900)' : 'var(--color-text)', bd: on ? 'var(--color-accent)' : 'transparent'}; });
    v.sideToc = tocFix(v.sideToc); v.tocList = tocFix(v.tocList);
    const bms = s.bms.filter(b => b.src === s.srcId);
    v.bmList = (v.bmList || []).map((x, j) => { const b = bms[j]; return b ? {...x, go: () => { this.stopTimers(); this.setState({rch: b.rch || s.rch, cur: b.i, playing:false});
      setTimeout(() => { const el = document.querySelector('[data-wi="' + b.i + '"]'); if (el) el.scrollIntoView({block:'center', behavior:'smooth'}); }, 80); }} : x; });
    const add0 = v.addBm; v.addBm = () => { add0 && add0(); this.setState(st => ({bms: st.bms.map(b => b.rch ? b : {...b, rch: st.rch || 'water'})})); };
  }
  if (s.recOn && s.recMiss) v.recStatus = s.recMiss;
  if (v.mean) v.mean = {...v.mean, hasLink:false, link:''};
  if (v.mean && s.mean && s.mean.takhrij) v.mean = {...v.mean, rows: s.mean.takhrij, status:'من حواشي الكتاب بنصها · البرنامج لا يحكم على الأحاديث', hasLink: !!s.mean.dorar, link: s.mean.dorar || ''};
  if (real && s.srcId === 'zad' && s.mode === 'meaning') v.readerHint = 'اضغط على أي كلمة لمعرفة معناها، أو على رقم حاشية لترى تخريجها';
  if (v.mean && s.mean && s.mean.grounded && !s.mean.loading) v.mean = {...v.mean, status:'من نصوص الكتب المحمّلة بصياغة الذكاء الاصطناعي · راجعه مع شيخك'};
  if (Array.isArray(v.rcResults)) v.rcResults = v.rcResults.filter(r => !Object.values(REAL_SRC).some(x => x.name === r.name));
  // keep the word being read (or recited) in view
  const focus = s.mode === 'recite' ? (s.recOn ? s.pos : null) : (s.playing ? s.cur : null);
  if (focus != null && focus >= 0 && focus !== this.__focus) { this.__focus = focus;
    requestAnimationFrame(() => { const el = document.querySelector('[data-wi="' + focus + '"]'); if (!el) return; const r = el.getBoundingClientRect();
      if (r.top < 100 || r.bottom > innerHeight * 0.6) el.scrollIntoView({block:'center', behavior:'smooth'}); }); }
  if (v && Array.isArray(v.turns)) v.turns = v.turns.map((t, i) => { const m = this.state.msgs[i] || {};
    if (m.pending) t = {...t, a: STAGE_TEXT[m.stage] || t.a};
    const done = !m.pending && m.status && (m.shown == null || m.shown >= String(m.a || '').split(' ').length);
    return {...t, hasCites: !!done, cites: m.cites || [], status: m.status_ar || '', stColor: STATUS_COLOR[m.status] || 'var(--color-neutral-600)',
            hasDropped: !!(done && m.dropped), droppedNote: 'حُذفت ' + toAr(m.dropped || 0) + ' من الجمل لأن توثيقها لم يثبت',
            onlyNote: m.cites && m.cites.length ? 'الإجابة من النصوص المحققة فقط · كل رقم يفتح صفحته في تراث' : ''}; });
  return v;
};

/* ---------- word meaning from the library (RAG), with pages ---------- */
const _lookup = P.lookup;
P.lookup = async function(w){
  const V = this.__view(this.state.srcId);
  if (!V) return _lookup.call(this, w);
  const para = V.paras[paraOf(V, w.i)] || {};
  if (MARKER.test(w.t) && para.anchors && para.anchors.length) return this.__takhrij(w, para);
  const word = w.t.replace(/[،.:«»؛﴿﴾()]/g, '');
  this.setState({mean:{i:w.i, word, loading:true}});
  const p = V.paras[paraOf(V, w.i)] || {};
  let res = null;
  try { const d = await api('/api/meaning?w=' + encodeURIComponent(word) + '&ctx=' + encodeURIComponent(String(p.text || '').slice(0, 400)));
    if (d.items && d.items.length) res = d.items.map(it => it.text ? it.text + ' (' + it.book + '، ج' + toAr(it.vol) + ' ص' + toAr(it.page) + ')' : 'لم نجد في الكتب المحمّلة نصًّا يدل على هذا المعنى.'); } catch(e) {}
  if (!res) res = this.findGloss(word);
  if (this.state.mean && this.state.mean.i !== w.i) return;
  this.setState({mean:{i:w.i, word, loading:false, res, grounded:true}});
};

/* ---------- takhrij: a footnote number in the Rawd shows its note, quoted, with any grading and a Dorar link-out ---------- */
const MARKER = /^\(([٠-٩0-9]+)\)[،.:؛]?$/;
P.__takhrij = async function(w, p){
  this.setState({mean:{i:w.i, word:'حاشية ' + w.t.replace(/[،.:؛]$/, ''), loading:true}});
  let items = [];
  try { const all = await Promise.all(p.anchors.map(a => api('/api/takhrij/' + a).catch(() => ({items:[]})))); items = all.flatMap(d => d.items || []); } catch(e) {}
  // the note behind this marker: its lemma ends with the word before the marker; the editors' (Rakaiz) notes first
  const flat = this.parse(this.state.srcId).paras.flat(), prev = flat[w.i - 1] ? KEY(flat[w.i - 1].t) : '';
  const hit = it => { const ws = NORM(it.lemma || '').split(' ').filter(Boolean); return prev && ws.length && sim(STEM(ws[ws.length - 1]), prev) >= 0.75; };
  let pick = items.filter(it => hit(it) && it.source.includes('ركائز'));
  if (!pick.length) pick = items.filter(hit);
  if (!pick.length) pick = items.filter(it => it.kind === 'takhrij');
  const KIND = {takhrij:'التخريج', variant:'فروق النسخ'};
  const rows = pick.slice(0, 3).map(it => ({k: KIND[it.kind] || 'تعليق', c:'var(--color-text)',
    v: it.text + (it.grades && it.grades.length ? ' — الحكم كما نقله: ' + it.grades.join('؛ ') : '') + ' (' + it.source + (it.page ? '، ص' + toAr(it.page) : '') + ')'}));
  const dorar = (pick.find(it => it.kind === 'takhrij' && it.dorar) || {}).dorar || null;
  if (this.state.mean && this.state.mean.i !== w.i) return;
  this.setState({mean:{i:w.i, word:'حاشية ' + w.t.replace(/[،.:؛]$/, ''), loading:false, res:['', '', ''],
    takhrij: rows.length ? rows : [{k:'الحاشية', v:'لم نجد نص هذه الحاشية في المصادر المحمّلة.', c:'var(--color-neutral-600)'}], dorar}});
};

/* ---------- summaries of the Zad family from the verified study tools ---------- */
const _summarize = P.summarize;
P.summarize = async function(id, title){
  const b = (this.BOOKS || []).find(x => x.id === id) || (this.BOOKS || []).find(x => x.src === id) || {};
  if (!(id === 'zad' || REAL_SRC[id] || b.real)) return _summarize.call(this, id, title);
  let items = [];
  try { const all = await Promise.all(CHAPTERS.map(([c]) => api('/api/tools/' + c)));
    for (const d of all) for (const s of d.sections || []) {
      const ref = s.summary[0] && s.summary[0].cite ? ' (' + s.summary[0].cite.book + '، ص' + toAr(s.summary[0].cite.page) + ')' : '';
      if (s.summary.length) items.push([s.title, s.summary.map(x => x.text).join(' ') + ref]); } } catch(e) {}
  this.setState(s => ({sums: (s.sums || []).map(x => x.id === id ? {...x, status: items.length ? 'ready' : 'offline', items} : x)}));
};
})();
"""

DORAR_MARKUP = """
                <sc-if value="{{ mean.hasLink }}" hint-placeholder-val="{{ false }}">
                  <a href="{{ mean.link }}" target="_blank" rel="noopener" style="align-self:flex-start;font-size:14px;color:var(--color-accent-800)">ابحث عن الحديث في الدرر السنية ↗</a>
                </sc-if>"""

CITES_MARKUP = """
                  <sc-if value="{{ m.hasCites }}" hint-placeholder-val="{{ false }}">
                    <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:12.5px">
                      <span style="border:1px solid {{ m.stColor }};color:{{ m.stColor }};border-radius:999px;padding:1px 10px;font-weight:600">{{ m.status }}</span>
                      <sc-for list="{{ m.cites }}" as="c">
                        <a href="{{ c.link }}" target="_blank" rel="noopener" title="{{ c.quote }}" style="text-decoration:none;border:1px solid var(--color-accent-300);background:var(--color-accent-100);color:var(--color-accent-800);border-radius:6px;padding:1px 8px">({{ c.n }}) {{ c.label }}</a>
                      </sc-for>
                    </div>
                    <span style="font-size:12px;color:var(--color-neutral-600)">{{ m.onlyNote }}</span>
                    <sc-if value="{{ m.hasDropped }}" hint-placeholder-val="{{ false }}"><span style="font-size:12px;color:oklch(0.55 0.15 30)">{{ m.droppedNote }}</span></sc-if>
                  </sc-if>"""


def main():
    html = SRC.read_text(encoding="utf-8")
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    tpl = json.loads(m.group(2))
    # 1) citations and evidence status under each chat answer
    anchor = '{{ m.a }}</p>'
    assert tpl.count(anchor) == 1, "chat answer anchor not found"
    tpl = tpl.replace(anchor, anchor + CITES_MARKUP)
    # 2) each word carries its index (to follow playback and recitation); the player, meaning and recitation panels
    #    stay pinned at the bottom of the screen, because the real chapters are much longer than the design's samples
    n = tpl.count('title="{{ w.title }}"'); assert n == 2, n
    tpl = tpl.replace('title="{{ w.title }}"', 'title="{{ w.title }}" data-wi="{{ w.i }}"')
    PIN = "position:sticky;bottom:var(--space-3);z-index:4;background:var(--color-bg);box-shadow:var(--shadow-md);"
    for cond, style in [("isListen", "display:flex;align-items:center;gap:var(--space-4);padding:var(--space-4) var(--space-6);border:1px solid var(--color-divider);border-radius:var(--radius-lg);flex-wrap:wrap"),
                        ("isMeaning", "display:flex;flex-direction:column;gap:var(--space-3);padding:var(--space-4) var(--space-6);border:1px solid var(--color-divider);border-radius:var(--radius-lg)"),
                        ("isRecite", "display:flex;flex-direction:column;gap:var(--space-4);padding:var(--space-4) var(--space-6);border:1px solid var(--color-divider);border-radius:var(--radius-lg)")]:
        a = tpl.find('<sc-if value="{{ ' + cond + ' }}"'); b = tpl.find('<div style="' + style + '"', a)
        assert a > 0 and 0 < b - a < 200, (cond, a, b)
        extra = PIN + ("max-height:45vh;overflow:auto;" if cond == "isMeaning" else "")
        tpl = tpl[:b] + '<div style="' + extra + style + '"' + tpl[b + len('<div style="' + style + '"'):]
    # 3) the Dorar link-out after the meaning rows
    a = tpl.find('<sc-for list="{{ mean.rows }}"'); b = tpl.find("</sc-for>", a) + len("</sc-for>")
    assert a > 0 and b > a
    tpl = tpl[:b] + DORAR_MARKUP + tpl[b:]
    # 4) integration code after the design's logic class
    i = tpl.find('<script type="text/x-dc"'); j = tpl.find("</script>", i)
    assert i > 0 and j > i and "</script" not in INTEGRATION
    tpl = tpl[:j] + INTEGRATION + tpl[j:]
    # 5) the page title and icon
    html = html[:m.start(2)] + json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/") + html[m.end(2):]
    if "<title>" not in html:
        html = html.replace("<head>", "<head><title>مدارسة</title>", 1)
    icon = ("<link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' "
            "fill='%23175c46'/%3E%3Ctext x='16' y='23' font-size='19' text-anchor='middle' fill='white' font-family='sans-serif'%3E%D9%85%3C/text%3E%3C/svg%3E\">")
    html = html.replace("<head>", "<head>" + icon, 1)   # the loader page; the design's own page gets it below
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    tpl = json.loads(m.group(2))
    if "<head>" in tpl and 'rel="icon"' not in tpl:
        tpl = tpl.replace("<head>", "<head>" + icon, 1)
        html = html[:m.start(2)] + json.dumps(tpl, ensure_ascii=False).replace("</", "<\\/") + html[m.end(2):]
    OUT.write_text(html, encoding="utf-8")
    print("written", OUT, len(html), "chars")


if __name__ == "__main__":
    main()
