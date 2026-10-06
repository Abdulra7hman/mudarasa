// Integration code appended to the design's logic class (see scripts/build_ui.py).
// The design runs unchanged; these overrides connect it to Mudarasa's backend and the real books.
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
const chName = c => (CHAPTERS.find(x => x[0] === c) || [])[1] || '';
const NEXT_CH = {water:'vessels', vessels:'istinja'}, PREV_CH = {vessels:'water', istinja:'vessels'};
const SPLIT = t => String(t || '').split(/\s+/).filter(Boolean);
const CLEAN = t => String(t || '').replace(/\s*\n\s*/g, ' ').trim();
// The Zad family in the reader: the Rawd (vocalized Rakaiz edition, for books r1 and r2), Ibn Qasim's Hashiya (r3),
// al-Sharh al-Mumti' (r4); the Zad matn (vocalized) when reciting. One chapter is shown at a time.
const REAL_SRC = {
  iqh:   {id:'iqh', name:'حاشية الروض المربع', short:'حاشية ابن قاسم', art:'الفقه', author:'عبد الرحمن بن محمد بن قاسم', section:'', pct:3, text:''},
  mumti: {id:'mumti', name:'الشرح الممتع على زاد المستقنع', short:'الشرح الممتع', art:'الفقه', author:'محمد بن صالح العثيمين', section:'', pct:9, text:''}};
const BOOK_SRC = {r3:'iqh', r4:'mumti'};
const CITE_SRC = {1679:['zad','r1'], 147658:['zad','r2'], 12216:['iqh','r3'], 10649:['mumti','r4']};
const SAY_PREFIX = 'قال ابن قاسم: ';
const estimate = (dur, words, lead) => {   // Ibn Qasim clips have no word marks: spread the clip over the words by length
  const lens = words.map(w => w.length + 1), tot = SAY_PREFIX.length + lens.reduce((x, y) => x + y, 0); let acc = SAY_PREFIX.length;
  const out = [{t:0, i:0}]; words.forEach((w, k) => { out.push({t: Math.round(dur * acc / tot), i: k + lead}); acc += lens[k]; }); return out; };
const paraOf = (V, i) => { let k = 0; for (let j = 0; j < V.offs.length; j++) { if (V.offs[j] <= i) k = j; else break; } return k; };

/* ---------- pages: at most 300 words (50 when reciting), cut at paragraph or matn-line ends where possible ---------- */
const PAGE_WORDS = 300, RECITE_WORDS = 50;
const pagesFor = (V, limit) => {
  if (V.pages && V.pages.limit === limit) return V.pages.list;
  const list = []; let a = 0, n = 0;
  V.paras.forEach((p, k) => {
    const words = SPLIT(p.text), o = V.offs[k];
    if (n && n + words.length > limit) { list.push([a, o]); a = o; n = 0; }
    let start = o, left = words.length;
    while (n + left > limit) {   // a paragraph longer than a page: cut it, preferring the end of a sentence
      let cut = limit - n; const ws = words.slice(start - o);
      for (let j = cut; j >= Math.max(1, cut - 80); j--) if (/[.؛:!؟]$/.test(ws[j - 1] || '')) { cut = j; break; }
      list.push([a, start + cut]); a = start + cut; start = a; left -= cut; n = 0;
    }
    n += left;
  });
  if (V.n > a) list.push([a, V.n]);
  if (!list.length) list.push([0, V.n]);
  V.pages = {limit, list}; return list;
};
const pageOf = (list, i) => { let k = 0; for (let j = 0; j < list.length; j++) { if (list[j][0] <= i) k = j; else break; } return k; };
const scrollToWord = (i, block) => setTimeout(() => { const el = document.querySelector('[data-wi="' + i + '"]'); if (el) el.scrollIntoView({block: block || 'center', behavior:'smooth'}); }, 90);

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
    this.__R = R; this.__clips = clips; this.__est = est; this.__VC = {}; this.cache = {};
    // the sample bookmark points at «وهي ارتفاع الحدث» in the real text
    const wz = R.zad.filter(p => p.ch === 'water').flatMap(p => SPLIT(p.text)), bi = wz.findIndex(w => NORM(w) === 'وهي');
    this.setState(s => ({realLoaded: Date.now(), bms: s.bms.map(b => b.id === 1 && b.src === 'zad' ? {...b, i: bi >= 0 ? bi : 0, rch:'water'} : b)}));
  } catch(e) { console.warn('real text not loaded', e); }
};
P.__viewFor = function(src, ch){
  if (!this.__R || !this.__R[src]) return null;
  const key = src + ':' + ch; this.__VC = this.__VC || {};
  if (!this.__VC[key]) {
    const paras = this.__R[src].filter(p => ch === 'all' || p.ch === ch); let n = 0;
    const offs = paras.map(p => { const o = n; n += SPLIT(p.text).length; return o; });
    this.__VC[key] = {key, src, ch, paras, offs, n};
  }
  return this.__VC[key];
};
// which real paragraphs the reader shows for a source: the open chapter, or the whole matn when reciting
P.__view = function(id){
  if (!this.__R) return null;
  const s = this.state || {}, src = s.mode === 'recite' && (id === 'zad' || REAL_SRC[id]) ? 'matn' : id;
  if (!this.__R[src]) return null;
  return this.__viewFor(src, src === 'matn' ? 'all' : (s.rch || 'water'));
};
P.__paged = function(){ return ((this.state || {}).set || {}).readMode !== 'scroll'; };
P.__pages = function(V){ return pagesFor(V, V.src === 'matn' ? RECITE_WORDS : PAGE_WORDS); };
// the page on screen: it follows the reciter, or the voice while listening; otherwise it is the page the reader chose
P.__pageNow = function(V){
  const s = this.state, list = this.__pages(V);
  if (V.src === 'matn') return pageOf(list, Math.min(s.pos || 0, Math.max(0, V.n - 1)));
  if (s.playing && s.cur >= 0) return pageOf(list, s.cur);
  return Math.max(0, Math.min(s.rpage || 0, list.length - 1));
};
P.__scrollTop = function(i){
  setTimeout(() => { const el = document.querySelector('[data-wi="' + i + '"]'); const card = el && el.closest('p') && el.closest('p').parentElement;
    (card || el) && (card || el).scrollIntoView({block:'start', behavior:'smooth'}); }, 70);
};
// turn to page p of the open chapter (the next or previous chapter past either end)
P.__turn = function(V, p){
  const list = this.__pages(V), s = this.state;
  if (V.src === 'matn') {   // reciting: skip ahead, or go back and recite the earlier page again
    if (p < 0 || p >= list.length) return;
    const a = list[p][0], rev = {}; for (const [i, r] of Object.entries(s.rev || {})) if (+i < a) rev[i] = r;
    this.setState(p > this.__pageNow(V) ? {pos:a, recMiss:null} : {pos:a, rev, recMiss:null}); this.__scrollTop(a); return;
  }
  if (p < 0) { const pc = PREV_CH[V.ch]; if (pc) this.__goChapter(pc, this.__pages(this.__viewFor(V.src, pc)).length - 1); return; }
  if (p >= list.length) { if (NEXT_CH[V.ch]) this.__goChapter(NEXT_CH[V.ch]); return; }
  if (s.playing) { this.startPlay(list[p][0]); return; }   // listening continues from the new page
  this.setState({rpage:p, cur:-1, mean:null}); this.__scrollTop(list[p][0]);
};
const _parse = P.parse;
P.parse = function(id){
  const V = this.__view(id); if (!V) return _parse.call(this, id);
  if (this.cache[V.key]) return this.cache[V.key];
  let n = 0; const paras = V.paras.map(p => SPLIT(p.text).map(t => ({t, i:n++})));
  return this.cache[V.key] = {paras, n};
};
P.__goChapter = function(c, page){
  const V0 = this.__view(this.state.srcId); this.stopTimers();
  this.setState({rch:c, rpage:page || 0, cur:-1, playing:false, rev:{}, pos:0, mean:null, hl:null});
  const V = V0 && this.__viewFor(V0.src, c), list = V ? this.__pages(V) : [[0]];
  this.__scrollTop((list[page || 0] || [0])[0]);
};

/* ---------- Arabic-Indic digits everywhere in the interface (text only: styles, links and inputs are untouched) ---------- */
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'CODE', 'PRE']);
const arDigits = s => s.replace(/(\d)\.(?=\d)/g, '$1٫').replace(/(\d)%/g, '$1٪').replace(/\d/g, d => '٠١٢٣٤٥٦٧٨٩'[d]);
const fixText = node => { const v = node.nodeValue; if (v && /\d/.test(v) && !(node.parentNode && SKIP_TAGS.has(node.parentNode.nodeName))) { const w = arDigits(v); if (w !== v) node.nodeValue = w; } };
const walkDigits = root => {
  if (!root) return;
  if (root.nodeType === 3) return fixText(root);
  if (root.nodeType !== 1 || SKIP_TAGS.has(root.nodeName)) return;
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n; while ((n = tw.nextNode())) fixText(n);
};
const startDigits = () => {
  walkDigits(document.body);
  new MutationObserver(ms => { for (const m of ms) { if (m.type === 'characterData') fixText(m.target); else m.addedNodes.forEach(walkDigits); } })
    .observe(document.body, {subtree:true, childList:true, characterData:true});
};

const _mount = P.componentDidMount;
P.componentDidMount = function(){
  this.BOOKS = this.BOOKS.map(b => BOOK_SRC[b.id] ? {...b, src: BOOK_SRC[b.id]} : b);
  this.EXTRA = [...this.EXTRA, ...Object.values(REAL_SRC)];
  this.REAL = [...this.REAL, ...Object.keys(REAL_SRC)];
  window.__mudarasa = this;
  _mount && _mount.call(this); this.__loadReal();
  if (!window.__mdDigits) { window.__mdDigits = true; startDigits(); }
  if (!window.__mdSel) { window.__mdSel = true;
    document.addEventListener('mouseup', e => setTimeout(() => this.__onSelect(e), 0));
    document.addEventListener('scroll', e => {
      const s = this.state; if (s.selChip) this.setState({selChip:null});
      if (s.screen !== 'sources' || s.srcView !== 'reader') return;
      const el = e.target && e.target.nodeType === 1 ? e.target : document.scrollingElement, stuck = !!el && el.scrollTop > 60;
      if (stuck !== !!s.rdStuck) this.setState({rdStuck: stuck}); }, true); }
};
const _go = P.go;
P.go = function(screen, extra){ return _go.call(this, screen, {rdStuck:false, ...(extra || {})}); };
const _stop = P.stopTimers;
P.stopTimers = function(){
  const s = this.state || {}, V = this.__view && this.__view(s.srcId);
  if (s.playing && V && V.src !== 'matn' && s.cur >= 0) this.setState({rpage: pageOf(this.__pages(V), s.cur)});
  _stop.call(this); if (this.__audio) { this.__audio.pause(); this.__audio = null; } this.__stopRec && this.__stopRec(); this.__dict && this.__dict();
};

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
    if (this.__view(this.state.srcId) !== V) return;   // chapter or book changed
    if (pi >= V.paras.length) { const nx = NEXT_CH[V.ch];
      if (nx && this.state.playing) this.setState({rch:nx, cur:0, rpage:0}, () => this.startPlay(0, speed));
      else this.setState({playing:false, rpage: this.__pages(V).length - 1}); return; }
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
  this.setState({cur: from, playing: true, hl:null});
  play(paraOf(V, Math.max(0, from)), Math.max(0, from));
};
const _togglePlay = P.togglePlay;
P.togglePlay = function(){
  const V = this.__view(this.state.srcId);
  if (!V) return _togglePlay.call(this);
  if (this.state.playing) { if (this.__audio) this.__audio.pause(); this.setState(s => ({playing:false, rpage: s.cur >= 0 ? pageOf(this.__pages(V), s.cur) : s.rpage})); return; }
  const list = this.__pages(V), pg = this.__pageNow(V), cur = this.state.cur;
  // play from the paused word if it is on this page; otherwise from the top of the page on screen
  const start = this.__paged() ? (cur >= list[pg][0] && cur < list[pg][1] ? cur : list[pg][0]) : (cur < 0 || cur >= V.n - 1 ? 0 : cur);
  this.startPlay(start);
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

/* ---------- chat: dictation into the question box (Azure speech-to-text) ---------- */
P.__dictate = async function(){
  if (this.__dict) { this.__dict(); return; }
  const tok = await api('/api/speech/token').catch(() => ({available:false}));
  if (!tok.available) { this.soon('الإملاء الصوتي'); return; }
  try { await loadSDK(); } catch(e) { this.soon('الإملاء الصوتي'); return; }
  const S = window.SpeechSDK, cfg = S.SpeechConfig.fromAuthorizationToken(tok.token, tok.region); cfg.speechRecognitionLanguage = 'ar-SA';
  const rec = new S.SpeechRecognizer(cfg, S.AudioConfig.fromDefaultMicrophoneInput());
  const base = String(this.state.draft || '').trim(); let said = '';
  const join = (...xs) => xs.filter(Boolean).join(' ');
  rec.recognizing = (_, e) => this.setState({draft: join(base, said, e.result && e.result.text)});
  rec.recognized = (_, e) => { if (e.result && e.result.text) { said = join(said, e.result.text); this.setState({draft: join(base, said)}); } };
  this.__dict = () => { try { rec.stopContinuousRecognitionAsync(() => rec.close(), () => {}); } catch(e) {} this.__dict = null; this.setState({dictOn:false}); };
  rec.startContinuousRecognitionAsync(); this.setState({dictOn:true});
};

/* ---------- chat: a photo (a book page, a written question) becomes the question ---------- */
P.__pickImage = function(){
  const inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'image/*';
  inp.onchange = () => { const f = inp.files && inp.files[0]; if (!f) return;
    const r = new FileReader(); r.onload = () => { const im = new Image(); im.onload = () => {
      const k = Math.min(1, 1600 / Math.max(im.width, im.height)), c = document.createElement('canvas');
      c.width = Math.round(im.width * k); c.height = Math.round(im.height * k); c.getContext('2d').drawImage(im, 0, 0, c.width, c.height);
      this.setState({chatImg: c.toDataURL('image/jpeg', 0.85)}); }; im.src = r.result; }; r.readAsDataURL(f); };
  inp.click();
};

/* ---------- chat: cited, checked answers ---------- */
const STAGE_TEXT = {image:'يقرأ الصورة…', search:'يبحث في المصادر…', write:'وجد النصوص، ويكتب الجواب منها…', verify:'يتحقق من كل جملة واقتباسها…'};
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
  const img = this.state.chatImg || null;
  const q = String(text ?? this.state.draft ?? '').trim(); if (!q && !img) return;
  this.__dict && this.__dict();
  if ((this.state.ctx || 0) !== 0) { this.soon(this.CTX[this.state.ctx]); return; }
  const ctx = this.CTX[0], depth = this.state.depth, id = Date.now();
  const dLabel = depth == null ? '' : ' · ' + ['خفيفة','متوسطة','مفصلة'][depth];
  this.setState(s => ({draft:'', chatImg:null, msgs:[...s.msgs, {id, q: q || 'سؤال من صورة', img, a:'', pending:true, shown:0, ctx:ctx + dLabel, stage: img ? 'image' : 'search'}]}));
  const upd = f => this.setState(s => ({msgs: s.msgs.map(m => m.id === id ? {...m, ...f(m)} : m)}));
  let question = q, pre = '', r = null;
  if (img) {
    let d = null; try { d = await api('/api/image_question', {image: img, text: q}); } catch(e) {}
    if (d && d.question) { question = d.question; pre = 'فهمت من الصورة: «' + d.question + '»'; upd(() => ({stage:'search'})); }
    else r = {sentences:[], message:'لم أتبيّن في الصورة سؤالًا يتعلق بالكتب المحمّلة. اكتب سؤالك، أو أرسل صورة أوضح.', status:'not_found', status_ar:'لم يوجد نص'};
  }
  if (!r) { try { r = await streamAsk({question, depth:{0:'short', 1:'medium', 2:'long'}[depth] || 'medium'}, stage => upd(() => ({stage}))); } catch(e) {} }
  if (!r) r = {sentences:[], message:'تعذّر الوصول إلى الخادم الآن. حاول بعد قليل.', status:'not_found', status_ar:'لم يوجد نص'};
  const cites = [], idx = {};
  const lines = (r.sentences || []).map(s => { if (!s.cite) return s.text;
    const k = s.cite.book + '|' + s.cite.page; if (!(k in idx)) { idx[k] = cites.length;
      cites.push({n: toAr(cites.length + 1), label: s.cite.book + '، ج' + toAr(s.cite.vol) + ' ص' + toAr(s.cite.page), link: s.cite.link, quote: s.quote, book_id: s.cite.book_id}); }
    return s.text + ' (' + toAr(idx[k] + 1) + ')'; });
  const a = [pre, r.message, ...lines].filter(Boolean).join('\n');
  const dropped = (r.dropped || []).length;
  upd(() => ({a, pending:false, shown:0, cites, status:r.status, status_ar:r.status_ar, dropped, cached:!!r.cached}));
  clearInterval(this.st); let n = 0; const total = a.split(' ').length;
  this.st = setInterval(() => { n += 1; upd(() => ({shown:n})); if (n >= total) clearInterval(this.st); }, 38);
};

/* ---------- a citation opens its book with the quoted words highlighted ---------- */
P.__findQuote = function(src, quote){
  const q = NORM(quote).split(' ').filter(Boolean); if (q.length < 3) return null;
  let best = null;
  for (const [c] of CHAPTERS) {
    const V = this.__viewFor(src, c); if (!V) continue;
    const toks = []; V.paras.forEach((p, pi) => SPLIT(p.text).forEach((w, j) => { const t = NORM(w).replace(/ /g, ''); if (t) toks.push([V.offs[pi] + j, t]); }));
    for (let st = 0; st + q.length <= toks.length; st++) {
      if (sim(toks[st][1], q[0]) < 0.75 && sim(toks[st + 1][1], q[1]) < 0.75) continue;
      let ok = 0; for (let j = 0; j < q.length; j++) if (sim(toks[st + j][1], q[j]) >= 0.75) ok++;
      const score = ok / q.length;
      if (!best || score > best.score) best = {score, ch:c, a:toks[st][0], b:toks[st + q.length - 1][0]};
      if (score === 1) return best;
    }
  }
  return best && best.score >= 0.6 ? best : null;
};
const HL_CSS = 'background:color-mix(in srgb,var(--color-accent) 26%,transparent);border-radius:4px;padding:1px 2px';
P.__citePreview = function(c){   // the cited passage with about 40 words around it, the quote highlighted
  this.__pvCache = this.__pvCache || new Map();
  const key = c.book_id + '|' + c.quote; if (this.__pvCache.has(key)) return this.__pvCache.get(key);
  const m = CITE_SRC[c.book_id], hit = m && this.__R ? this.__findQuote(m[0], c.quote) : null;
  let pv;
  if (hit) {
    const V = this.__viewFor(m[0], hit.ch), words = V.paras.flatMap(p => SPLIT(p.text));
    const a0 = Math.max(0, hit.a - 40), b1 = Math.min(words.length, hit.b + 41);
    pv = {inApp: true, where: 'كتاب الطهارة · ' + chName(hit.ch), note: m[0] === 'zad' && c.book_id === 1679 ? 'النص من طبعة ركائز المشكولة للكتاب نفسه' : '',
      parts: [{t: (a0 > 0 ? '… ' : '') + words.slice(a0, hit.a).join(' ') + ' ', css: ''}, {t: words.slice(hit.a, hit.b + 1).join(' '), css: HL_CSS},
              {t: ' ' + words.slice(hit.b + 1, b1).join(' ') + (b1 < words.length ? ' …' : ''), css: ''}]};
  } else pv = {inApp: false, where: 'الاقتباس كما في الصفحة', note: '', parts: [{t: '«' + String(c.quote || '').trim() + '»', css: HL_CSS}]};
  this.__pvCache.set(key, pv); return pv;
};
P.__openCite = function(c){
  const m = CITE_SRC[c.book_id], hit = m && this.__R ? this.__findQuote(m[0], c.quote) : null;
  if (!hit) { window.open(c.link, '_blank', 'noopener'); return; }
  const V = this.__viewFor(m[0], hit.ch), page = pageOf(this.__pages(V), hit.a);
  this.go('sources', {srcId:m[0], rBook:m[1], srcView:'reader', rch:hit.ch, rpage:page, cur:-1, rev:{}, pos:0, mode:'listen', mean:null, info:null,
    hl:{src:m[0], ch:hit.ch, a:hit.a, b:hit.b}});
  scrollToWord(hit.a, 'center');
};

/* ---------- bookmarks are placed on a word ---------- */
P.__addBmAt = function(i){
  const s = this.state, V = this.__view(s.srcId); if (!V) return;
  if (s.bms.some(b => b.src === s.srcId && b.i === i && (b.rch || 'water') === V.ch)) { this.setState({bmPick:false}); return; }
  const words = this.parse(s.srcId).paras.flat(), label = words.slice(i, i + 5).map(w => w.t).join(' ');
  this.setState({bmPick:false, bms:[...s.bms, {id:Date.now(), src:s.srcId, i, rch:V.ch, label}]});
};

/* ---------- select text in a book, then save it to the notes (تقييدات) with a comment ---------- */
P.__onSelect = function(e){
  const s = this.state; if (s.screen !== 'sources' || s.srcView !== 'reader' || s.mode === 'recite' || s.selForm) return;
  if (e && e.target && e.target.closest && e.target.closest('[data-sel-ui]')) return;
  const sel = window.getSelection(), txt = sel && sel.rangeCount ? String(sel).replace(/\s+/g, ' ').trim() : '';
  if (!txt || txt.split(' ').length < 2) { if (s.selChip) this.setState({selChip:null}); return; }
  const r = sel.getRangeAt(0), box = r.commonAncestorContainer.nodeType === 1 ? r.commonAncestorContainer : r.commonAncestorContainer.parentNode;
  if (!box || !box.closest || !(box.closest('[data-wi]') || (box.querySelector && box.querySelector('[data-wi]')))) return;
  const rect = r.getBoundingClientRect(), z = this.__zoom || 1;
  this.setState({selChip: {text: txt.slice(0, 1500), x: Math.round((rect.left + rect.width / 2) / z) + 'px', y: Math.round(rect.top / z) + 'px'}});
};

/* ---------- render: everything above, shown through the design's own markup ---------- */
const ZAD_NAMES = {r1:'الروض المربع شرح زاد المستقنع', r2:'الروض المربع (مشكول)'};
const chip = on => ({bd:on?'var(--color-accent)':'var(--color-divider)', bg:on?'var(--color-accent-100)':'transparent', fg:on?'var(--color-accent-900)':'var(--color-neutral-800)', fw:on?'700':'400'});
const _rv = P.renderVals;
P.renderVals = function(){
  const s = this.state, V = this.__view(s.srcId), real = !!V;
  if (this.__R) {   // the reader's title, author and section follow the open book and chapter
    const z = this.EXTRA.find(x => x.id === 'zad'), chT = chName(s.rch || 'water');
    if (z && s.mode === 'recite') Object.assign(z, {name:'زاد المستقنع', author:'موسى الحجاوي', section:'كتاب الطهارة: المياه، الآنية، الاستنجاء'});
    else if (z) Object.assign(z, {name: ZAD_NAMES[s.rBook] || ZAD_NAMES.r2, author:'منصور بن يونس البهوتي', section:'كتاب الطهارة · ' + chT});
    for (const r of Object.values(REAL_SRC)) { const e = this.EXTRA.find(x => x.id === r.id); if (!e) continue;   // reciting is always the Zad matn
      if (s.mode === 'recite') Object.assign(e, {name:'زاد المستقنع', author:'موسى الحجاوي', section:'كتاب الطهارة: المياه، الآنية، الاستنجاء'});
      else Object.assign(e, {name:r.name, author:r.author, section:'كتاب الطهارة · ' + chT}); }
  }
  const v = _rv.call(this);
  if (!v) return v;
  this.__zoom = v.zoom || 1;
  const paged = this.__paged();
  // settings: how the reader shows the text
  v.optReadMode = [['pages','صفحات'],['scroll','تمرير متصل']].map(([k, l]) => ({label:l, pick:() => this.setState({set:{...this.state.set, readMode:k}, rpage:0}), ...chip((paged ? 'pages' : 'scroll') === k)}));
  v.rdTitleFs = s.rdStuck ? '24px' : '40px'; v.rdMetaDisp = s.rdStuck ? 'none' : 'inline'; v.rdShadow = s.rdStuck ? '0 1px 0 var(--color-divider)' : 'none';
  v.pgShow = false; v.pgLabel = ''; v.pgPrevLabel = 'السابق'; v.pgNextLabel = 'التالي'; v.pgPrevOp = '1'; v.pgNextOp = '1'; v.pgPrev = () => {}; v.pgNext = () => {};
  v.bmBtnLabel = 'علامة'; v.bmBtnTitle = 'ضع علامة عند كلمة'; v.bmBtnBg = ''; v.bmBtnBd = '';
  if (real) {
    // each word: its index; the cited passage highlighted; bookmarked words marked; clicks place a bookmark when asked
    const hl = s.hl && s.hl.src === s.srcId && s.hl.ch === V.ch ? s.hl : null;
    const bmSet = new Set(s.bms.filter(b => b.src === s.srcId && (b.rch || 'water') === V.ch).map(b => b.i));
    let k = 0;
    (v.paras || []).forEach(p => (p.words || []).forEach(w => {
      w.i = k++;
      if (hl && w.i >= hl.a && w.i <= hl.b) w.css += ';background:color-mix(in srgb,var(--color-accent) 24%,transparent)';
      if (bmSet.has(w.i)) w.css = /box-shadow:/.test(w.css) ? w.css.replace('box-shadow:', 'box-shadow:inset 0 3px 0 var(--color-accent-700),') : w.css + ';box-shadow:inset 0 3px 0 var(--color-accent-700)';
      if (s.bmPick) w.title = 'ضع العلامة عند هذه الكلمة';
      const c0 = w.click; w.click = () => { if (this.state.bmPick) return this.__addBmAt(w.i); if (this.state.hl) this.setState({hl:null}); c0 && c0(); };
    }));
    // pages
    const list = this.__pages(V), pg = this.__pageNow(V), last = list.length - 1, isRec = V.src === 'matn';
    if (paged) {
      const [pa, pb] = list[pg];
      v.paras = (v.paras || []).map(p => ({...p, words: (p.words || []).filter(w => w.i >= pa && w.i < pb)})).filter(p => p.words.length);
      const key = V.key + '#' + pg;
      if (this.__pgKey && this.__pgKey !== key && !s.playing && !s.recOn && !s.hl) this.__scrollTop(pa);
      this.__pgKey = key;
      const canPrev = pg > 0 || (!isRec && !!PREV_CH[V.ch]), canNext = pg < last || (!isRec && !!NEXT_CH[V.ch]);
      v.pgShow = true;
      v.pgLabel = 'الصفحة ' + toAr(pg + 1) + ' من ' + toAr(list.length) + (isRec ? ' · تنتقل وحدها مع تسميعك' : s.playing ? ' · تنتقل وحدها مع الاستماع' : '');
      v.pgPrevLabel = pg > 0 ? 'السابق' : (!isRec && PREV_CH[V.ch] ? 'الباب السابق' : 'السابق');
      v.pgNextLabel = pg < last ? 'التالي' : (!isRec && NEXT_CH[V.ch] ? 'الباب التالي: ' + chName(NEXT_CH[V.ch]) : 'نهاية المتاح');
      v.pgPrevOp = canPrev ? '1' : '0.4'; v.pgNextOp = canNext ? '1' : '0.4';
      v.pgPrev = () => { if (canPrev) this.__turn(V, pg - 1); }; v.pgNext = () => { if (canNext) this.__turn(V, pg + 1); };
    } else if (!isRec) {
      v.pgShow = true; v.pgLabel = chName(V.ch);
      v.pgPrevLabel = PREV_CH[V.ch] ? 'الباب السابق' : 'السابق'; v.pgNextLabel = NEXT_CH[V.ch] ? 'الباب التالي: ' + chName(NEXT_CH[V.ch]) : 'نهاية المتاح';
      v.pgPrevOp = PREV_CH[V.ch] ? '1' : '0.4'; v.pgNextOp = NEXT_CH[V.ch] ? '1' : '0.4';
      v.pgPrev = () => { if (PREV_CH[V.ch]) this.__goChapter(PREV_CH[V.ch]); }; v.pgNext = () => { if (NEXT_CH[V.ch]) this.__goChapter(NEXT_CH[V.ch]); };
    }
    // table of contents: chapters switch the reader
    const tocFix = lst => (lst || []).map(e => { const c = CH_TITLE[e.t]; if (!c) return e; const on = c === (s.rch || 'water') && e.t !== 'كتاب الطهارة';
      return {...e, go: () => this.__goChapter(c), bg: on ? 'var(--color-accent-100)' : 'transparent', c: on ? 'var(--color-accent-900)' : 'var(--color-text)', bd: on ? 'var(--color-accent)' : 'transparent'}; });
    v.sideToc = tocFix(v.sideToc); v.tocList = tocFix(v.tocList);
    // bookmarks: jump to the word's chapter and page; the bookmark button asks for a word
    const bms = s.bms.filter(b => b.src === s.srcId);
    v.bmList = (v.bmList || []).map((x, j) => { const b = bms[j]; if (!b) return x;
      return {...x, go: () => { const bv = this.__viewFor(V.src, b.rch || 'water'); this.stopTimers();
        this.setState({rch: b.rch || 'water', rpage: bv ? pageOf(this.__pages(bv), b.i) : 0, cur: b.i, playing:false}); scrollToWord(b.i, 'center'); }}; });
    v.addBm = () => this.setState({bmPick: !this.state.bmPick, selChip:null});
    if (s.bmPick) Object.assign(v, {bmBtnLabel:'اختر كلمة…', bmBtnTitle:'اضغط على الكلمة التي تضع عندها العلامة', bmBtnBg:'var(--color-accent-100)', bmBtnBd:'var(--color-accent)'});
    if (s.bmPick) v.readerHint = 'اضغط على الكلمة التي تريد وضع العلامة عندها';
    else if (hl) v.readerHint = 'المظلَّل موضع الاقتباس من جواب المحادثة';
    else if (s.srcId === 'zad' && s.mode === 'meaning') v.readerHint = 'اضغط على أي كلمة لمعرفة معناها، أو على رقم حاشية لترى تخريجها';
  }
  // select text -> notes
  const rb = this.BOOKS.find(b => b.id === s.rBook) || this.BOOKS.find(b => b.src === s.srcId) || {};
  v.selChipOn = !!s.selChip && !s.selForm; v.selX = s.selChip ? s.selChip.x : '0px'; v.selY = s.selChip ? s.selChip.y : '0px';
  v.selOpen = () => { const t = (this.state.selChip || {}).text; if (!t) return; try { window.getSelection().removeAllRanges(); } catch(e) {} this.setState({selForm:{text:t, note:''}, selChip:null}); };
  v.selFormOn = !!s.selForm; v.selText = s.selForm ? s.selForm.text : ''; v.selNote = s.selForm ? s.selForm.note : ''; v.selBook = rb.title || this.srcOf(s.srcId).name;
  v.onSelNote = e => { const val = e.target.value; this.setState(st => ({selForm: st.selForm ? {...st.selForm, note: val} : null})); };
  v.selCancel = () => this.setState({selForm:null});
  v.selSave = () => { const f = this.state.selForm; if (!f) return; const st = this.state, words = f.text.split(' ');
    const q = words.slice(0, 6).join(' ') + (words.length > 6 ? '…' : ''), note = f.note.trim();
    this.setState({notes:[{id:st.nid, book: rb.id || 'r1', q, t: note ? note + ' — «' + f.text + '»' : '«' + f.text + '»', d:'الآن', fav:false}, ...st.notes], nid:st.nid + 1, selForm:null, selDone:Date.now()});
    setTimeout(() => this.setState({selDone:null}), 2200); };
  v.selDoneOn = !!s.selDone;
  // meaning panel: a close button; takhrij and grounded meanings say where they come from
  v.closeMean = () => this.setState({mean:null});
  if (s.recOn && s.recMiss) v.recStatus = s.recMiss;
  if (v.mean) v.mean = {...v.mean, hasLink:false, link:''};
  if (v.mean && s.mean && s.mean.takhrij) v.mean = {...v.mean, rows: s.mean.takhrij, status:'من حواشي الكتاب بنصها · البرنامج لا يحكم على الأحاديث', hasLink: !!s.mean.dorar, link: s.mean.dorar || ''};
  if (v.mean && s.mean && s.mean.grounded && !s.mean.loading) v.mean = {...v.mean, status:'من نصوص الكتب المحمّلة بصياغة الذكاء الاصطناعي · راجعه مع شيخك'};
  if (Array.isArray(v.rcResults)) v.rcResults = v.rcResults.filter(r => !Object.values(REAL_SRC).some(x => x.name === r.name));
  // chat: image and dictation buttons
  v.attachImg = () => this.__pickImage(); v.hasChatImg = !!s.chatImg; v.dropChatImg = () => this.setState({chatImg:null});
  v.dictate = () => this.__dictate(); v.dictBg = s.dictOn ? 'var(--color-accent-100)' : ''; v.dictC = s.dictOn ? 'var(--color-accent-800)' : '';
  v.dictTitle = s.dictOn ? 'يستمع… اضغط لإيقاف الإملاء' : 'إملاء صوتي';
  // flashcards: a page to make a deck with several cards, or to add cards to an open deck
  const E = s.deckEdit;
  v.toggleAddDeck = () => this.setState({deckEdit:{id:null, name:'', parent:'root', cards:[['', '']]}, deck:null});
  v.addDeckOpen = false; v.deckEditView = !!E;
  v.deckAddCards = () => { const f = this.findDeck(this.state.deck); if (f) this.setState({deckEdit:{id:this.state.deck, name:f.n.name, parent:'root', cards:[['', '']]}}); };
  if (E) {
    v.deckListView = false; v.deckStudyView = false;
    const up = o => this.setState(st => ({deckEdit: st.deckEdit ? {...st.deckEdit, ...o} : null}));
    const setCard = (j, side, val) => this.setState(st => ({deckEdit: st.deckEdit ? {...st.deckEdit, cards: st.deckEdit.cards.map((x, i) => i === j ? (side ? [x[0], val] : [val, x[1]]) : x)} : null}));
    const full = E.cards.filter(c => c[0].trim() && c[1].trim()).length;
    Object.assign(v, {deTitle: E.id ? 'إضافة بطاقات إلى «' + E.name + '»' : 'رزمة جديدة', deIsNew: !E.id, deName: E.name, deParent: E.parent,
      onDeName: e => up({name: e.target.value}), onDeParent: e => up({parent: e.target.value}),
      deCards: E.cards.map((c, j) => ({n: toAr(j + 1), q: c[0], a: c[1], onQ: e => setCard(j, 0, e.target.value), onA: e => setCard(j, 1, e.target.value),
        del: () => this.setState(st => ({deckEdit: {...st.deckEdit, cards: st.deckEdit.cards.filter((_, i) => i !== j)}})), delVis: E.cards.length > 1 ? 'visible' : 'hidden'})),
      deAddCard: () => this.setState(st => ({deckEdit: {...st.deckEdit, cards: [...st.deckEdit.cards, ['', '']]}})),
      deCancel: () => this.setState({deckEdit:null}),
      deHint: full ? toAr(full) + (full === 1 ? ' بطاقة مكتملة' : ' بطاقات مكتملة') : 'اكتب السؤال والجواب لكل بطاقة',
      deSaveLabel: E.id ? 'أضف البطاقات' : 'حفظ الرزمة',
      deErr: E.err || '',
      deSave: () => { const st = this.state, D = st.deckEdit; if (!D) return;
        const cards = D.cards.map(c => [c[0].trim(), c[1].trim()]).filter(c => c[0] && c[1]);
        if (D.id) { const f = this.findDeck(D.id); if (!f) return; if (!cards.length) { up({err:'أضف بطاقة واحدة على الأقل.'}); return; }
          const before = (f.n.cards || []).length; f.n.cards = [...(f.n.cards || []), ...cards];
          this.setState({deckEdit:null, deck:D.id, queue:[...(st.queue || []), ...cards.map((_, j) => before + j)], dShow:false}); return; }
        const name = D.name.trim(); if (!name) { up({err:'اكتب اسم الرزمة.'}); return; }
        const node = {id:'u' + Date.now(), name, due:0, cards}; const p = D.parent === 'root' ? null : this.findDeck(D.parent);
        if (p) (p.n.kids = p.n.kids || []).push(node); else this.DECKS.push(node);
        this.setState({deckEdit:null, deckOpen:{...st.deckOpen, [D.parent]:true}}); }});
  }
  const imgs = {draft: s.chatImg}; (s.msgs || []).forEach(m => { if (m.img) imgs['m' + m.id] = m.img; });
  requestAnimationFrame(() => document.querySelectorAll('img[data-img-key]').forEach(el => { const u = imgs[el.dataset.imgKey]; if (u && el.getAttribute('src') !== u) el.setAttribute('src', u); }));
  // keep the word being read (or recited) in view
  const focus = s.mode === 'recite' ? (s.recOn ? s.pos : null) : (s.playing ? s.cur : null);
  if (focus != null && focus >= 0 && focus !== this.__focus) { this.__focus = focus;
    requestAnimationFrame(() => { const el = document.querySelector('[data-wi="' + focus + '"]'); if (!el) return; const r = el.getBoundingClientRect();
      if (r.top < 190 || r.bottom > innerHeight * 0.6) el.scrollIntoView({block:'center', behavior:'smooth'}); }); }
  // chat turns: stage while waiting, image, citations (each opens the book at the quote) and evidence status
  if (Array.isArray(v.turns)) v.turns = v.turns.map((t, i) => { const m = this.state.msgs[i] || {};
    if (m.pending) t = {...t, a: STAGE_TEXT[m.stage] || t.a};
    const done = !m.pending && m.status && (m.shown == null || m.shown >= String(m.a || '').split(' ').length);
    const pvOpen = done && s.cpv && s.cpv.mid === m.id && (m.cites || [])[s.cpv.k], pvc = pvOpen ? m.cites[s.cpv.k] : null, pv = pvc ? this.__citePreview(pvc) : null;
    return {...t, hasImg: !!m.img, imgKey: m.img ? 'm' + m.id : '', hasCites: !!done,
            cites: (m.cites || []).map((c, k) => { const on = !!(s.cpv && s.cpv.mid === m.id && s.cpv.k === k);
              return {...c, bg: on ? 'var(--color-accent-300)' : 'var(--color-accent-100)', bd: on ? 'var(--color-accent)' : 'var(--color-accent-300)',
                open: () => { this.setState(st => ({cpv: st.cpv && st.cpv.mid === m.id && st.cpv.k === k ? null : {mid: m.id, k}}));
                  setTimeout(() => { const el = document.querySelector('[data-cite-card]'); if (el) el.scrollIntoView({block:'nearest', behavior:'smooth'}); }, 80); }}; }),
            hasPv: !!pv, pv: pv ? {book: pvc.label, where: pv.where, parts: pv.parts, inApp: pv.inApp, link: pvc.link, note: pv.note,
              close: () => this.setState({cpv:null}), read: () => this.__openCite(pvc)} : {parts:[]},
            status: m.status_ar || '', stColor: STATUS_COLOR[m.status] || 'var(--color-neutral-600)',
            hasDropped: !!(done && m.dropped), droppedNote: 'حُذفت ' + toAr(m.dropped || 0) + ' من الجمل لأن توثيقها لم يثبت',
            onlyNote: m.cites && m.cites.length ? 'الإجابة من النصوص المحققة فقط · اضغط رقمًا لترى نصه من الكتاب مظلَّلًا، و↗ لصفحته في تراث' : ''}; });
  return v;
};

/* ---------- word meaning from the library (RAG), with pages ---------- */
const MARKER = /^\(([٠-٩0-9]+)\)[،.:؛]?$/;
const _lookup = P.lookup;
P.lookup = async function(w){
  const V = this.__view(this.state.srcId);
  if (!V) return _lookup.call(this, w);
  const para = V.paras[paraOf(V, w.i)] || {};
  if (MARKER.test(w.t) && para.anchors && para.anchors.length) return this.__takhrij(w, para);
  const word = w.t.replace(/[،.:«»؛﴿﴾()]/g, '');
  this.setState({mean:{i:w.i, word, loading:true}});
  let res = null;
  try { const d = await api('/api/meaning?w=' + encodeURIComponent(word) + '&ctx=' + encodeURIComponent(String(para.text || '').slice(0, 400)));
    if (d.items && d.items.length) res = d.items.map(it => it.text ? it.text + ' (' + it.book + '، ج' + toAr(it.vol) + ' ص' + toAr(it.page) + ')' : 'لم نجد في الكتب المحمّلة نصًّا يدل على هذا المعنى.'); } catch(e) {}
  if (!res) res = this.findGloss(word);
  if (this.state.mean && this.state.mean.i !== w.i) return;
  this.setState({mean:{i:w.i, word, loading:false, res, grounded:true}});
};

/* ---------- takhrij: a footnote number in the Rawd shows its note, quoted, with any grading and a Dorar link-out ---------- */
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
