"use strict";
/* ============================================================
   Jade Bɔngɔ́ — Application enfant v2.0 « Plafond ouvert »
   - Trilingue (🇫🇷 🇬🇧 🇪🇸) : interface + voix + cours
   - Le contenu n'a AUCUN plafond d'âge : il avance au rythme
     de l'enfant (accélération célébrée, jamais plus d'écran)
   - Profils d'adaptation : attention courte, soutien langage
   - Anti-frustration : pause respiration proposée après 3 échecs
   ============================================================ */

const app = document.getElementById("app");
const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
const T = (k, v) => window.I18N.t("kid." + k, v);

const state = {
  childId: null, childName: "",
  lang: window.I18N.get(),
  speechSupport: false,
  challenge: null, qIndex: 0,
  token: null, remaining: 0, timer: null, ticker: null,
  skill: null, game: null, mode: "new",
  roundOk: 0, roundAttempts: 0, lastTarget: null, breakShownAt: 0,
  songPlayed: new Set(), breathTimer: null,
};

/* ---------------- helpers ---------------- */
function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
function show(...nodes) { app.innerHTML = ""; nodes.forEach((n) => app.appendChild(n)); }
function shuffle(a) { const c = [...a]; for (let i = c.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [c[i], c[j]] = [c[j], c[i]]; } return c; }
function fmt(s) { const m = Math.floor(s / 60), r = s % 60; return m + ":" + String(r).padStart(2, "0"); }
function rnd(min, max) { return min + Math.floor(Math.random() * (max - min + 1)); }
function uniqOptions(correct, candidates) {
  const out = [correct]; const pool = [...candidates];
  while (out.length < 4 && pool.length) { const c = pool.shift(); if (!out.includes(c) && c >= 0) out.push(c); }
  return shuffle(out);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: opts.body ? { "Content-Type": "application/json" } : undefined,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { const err = new Error(res.status); err.status = res.status; err.body = data; throw err; }
  return data;
}

/* ---------------- voix : TTS/STT multilingue ---------------- */
function speak(text, langOverride) {
  try {
    speechSynthesis.cancel();
    const clean = String(text).replace(/[\p{Extended_Pictographic}\uFE0F]/gu, "").replace(/\n+/g, " ");
    const u = new SpeechSynthesisUtterance(clean);
    const lang = langOverride || state.lang;
    u.lang = window.I18N.TTS_LANG[lang] || "fr-FR";
    u.rate = state.speechSupport ? 0.7 : 0.95;
    u.pitch = 1.1;
    const want = u.lang.slice(0, 2).toLowerCase();
    const v = speechSynthesis.getVoices().find((x) => x.lang && x.lang.toLowerCase().startsWith(want));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  } catch (e) { /* l'affichage suffit */ }
}
function listenOnce(langCode) {
  return new Promise((resolve) => {
    if (!SR) return resolve(null);
    try {
      const rec = new SR();
      rec.lang = window.I18N.TTS_LANG[langCode] || window.I18N.TTS_LANG[state.lang] || "fr-FR";
      rec.interimResults = false; rec.maxAlternatives = 3;
      let done = false;
      rec.onresult = (ev) => { done = true; resolve(ev.results[0][0].transcript || ""); };
      rec.onerror = () => resolve(null);
      rec.onend = () => { if (!done) resolve(null); };
      rec.start();
      setTimeout(() => { if (!done) { try { rec.stop(); } catch (e) {} } }, 7000);
    } catch (e) { resolve(null); }
  });
}
function confetti() {
  const pieces = ["🎉", "⭐", "🌟", "💛", "🎊", "✨"];
  for (let i = 0; i < 26; i++) {
    const s = el(`<span class="confetti-piece" style="left:${Math.random() * 100}vw; animation-delay:${Math.random() * 0.4}s">${pieces[i % pieces.length]}</span>`);
    document.body.appendChild(s);
    setTimeout(() => s.remove(), 2200);
  }
}
function toast(msg, ms = 3200) {
  const t = el(`<div class="toast">${msg}</div>`);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), ms);
}
function ensureChip() {
  let c = document.querySelector(".chip");
  if (!c) { c = el('<div class="chip">⏳ …</div>'); document.body.appendChild(c); }
  return c;
}
function clearChips() { document.querySelectorAll(".chip, .quiet-quit, .breath-overlay, .repeat-btn").forEach((n) => n.remove()); }

/* ---------------- ÉCRAN 1 : Bienvenue ---------------- */
/**
 * Règle absolue : la langue suit le PROFIL de l'enfant, pas l'appareil.
 * Un profil anglophone = interface + leçons + voix 100 % en anglais,
 * même si le téléphone de la famille est réglé en français (bug signalé :
 * « leçons en français prononcées en anglais » — corrigé ainsi).
 */
function applyChildLanguage(child) {
  const lang = child && child.lang ? child.lang : null;
  if (!lang) return;
  if (window.I18N.get() !== lang) window.I18N.set(lang);
  state.lang = lang;
  window.I18N.syncSwitcher();
}

async function screenWelcome() {
  stopTimers(); clearChips(); state.token = null;
  state.lang = window.I18N.get();
  applyProfileClasses();
  let children = [];
  try { children = await api("/api/children"); } catch (e) {}
  if (children.length && !state.childId) state.childId = children[0].id;
  const current = children.find((c) => c.id === state.childId);
  state.childName = current ? current.display_name : state.childName;
  applyChildLanguage(current);                              // ← langue du profil

  let phaseTxt = "", parentNote = "";
  try {
    const age = await api("/api/age" + (state.childId ? "?child_id=" + encodeURIComponent(state.childId) : ""));
    phaseTxt = `${age.phase_label}`;
    if (age.child) {
      state.speechSupport = !!age.child.speech_support;
      applyChildLanguage({ lang: age.child.lang });         // ← filet de sécurité
    }
    if (age.policy && age.policy.requires_parent_present) parentNote = T("parent_note");
  } catch (e) {}

  const nodes = [
    el(`<div class="kid-logo">${current ? current.emoji : "⭐"}</div>`),
    el(`<h1 class="kid-title">${state.childName ? T("hello", { name: state.childName }) : "Jade Bɔngɔ́"}</h1>`),
    el(`<p class="kid-sub">${state.childName ? T("school_mine", { name: state.childName }) : T("school_kids")}<br>${phaseTxt}</p>`),
  ];

  if (children.length > 1) {
    nodes.push(el(`<p class="hint">${T("who_plays")}</p>`));
    const row = el('<div style="display:flex; gap:12px; flex-wrap:wrap; justify-content:center"></div>');
    children.forEach((c) => {
      const active = c.id === state.childId;
      const b = el(`<button class="opt" style="min-height:96px; min-width:112px; ${active ? "outline:4px solid #fff; outline-offset:2px;" : "opacity:.75"}">
        <span class="oe" style="font-size:40px">${c.emoji}</span><span class="ol">${c.display_name}</span></button>`);
      b.onclick = () => { state.childId = c.id; state.childName = c.display_name; applyChildLanguage(c); screenWelcome(); };
      row.appendChild(b);
    });
    nodes.push(row);
  }

  const startBtn = el(`<button class="btn-big">${T("start")}</button>`);
  startBtn.onclick = startChallenge;
  nodes.push(startBtn, el(`<p class="hint">${parentNote}</p>`),
    el(`<a class="tiny-link" href="parent.html">${T("parents_space")}</a>`));
  show(...nodes);
}

/* ---------------- ÉCRAN 2 : Identification ---------------- */
async function startChallenge() {
  try {
    const qs = state.childId ? "?child_id=" + encodeURIComponent(state.childId) : "";
    state.challenge = await api("/api/identity/challenge" + qs, { method: "POST" });
    state.qIndex = 0;
    speak(T("id_hello", { name: state.childName || "" }));
    screenQuestion();
  } catch (e) {
    if (e.status === 423) return screenLocked(e.body.detail && e.body.detail.locked_until);
    screenError(T("oops_adult"));
  }
}
function screenQuestion() {
  const ch = state.challenge, i = state.qIndex, q = ch.questions[i];
  const nodes = [
    el(`<div class="q-progress">${T("q_progress", { i: i + 1, n: ch.questions.length })}</div>`),
    el(`<div class="q-emoji">${q.prompt.emoji || "🔐"}</div>`),
    el(`<div class="q-text">${q.prompt.text}</div>`),
  ];
  speak(q.prompt.text);

  if (q.modality === "image_tap" && q.options) {
    const grid = el('<div class="grid-options"></div>');
    shuffle(q.options).forEach((o) => {
      const b = el(`<button class="opt"><span class="oe">${o.emoji}</span><span class="ol">${o.label}</span></button>`);
      b.onclick = () => answerQuestion(o.id, false, b);
      grid.appendChild(b);
    });
    nodes.push(grid);
  } else {
    nodes.push(el(`<p class="hint">${T("mic_hint")}</p>`));
    if (SR) {
      const mic = el('<button class="mic">🎤</button>');
      mic.onclick = async () => {
        mic.classList.add("listening");
        const said = await listenOnce(ch.lang);
        mic.classList.remove("listening");
        if (said) answerQuestion(said, false, mic);
        else speak(T("mic_retry"));
      };
      nodes.push(mic);
    }
    const parentBtn = el(`<button class="btn-soft">${T("adult_validate")}</button>`);
    parentBtn.onclick = () => answerQuestion("", true, parentBtn);
    nodes.push(parentBtn);
  }
  show(...nodes);
}
async function answerQuestion(value, parentValidated, btn) {
  const ch = state.challenge, q = ch.questions[state.qIndex];
  try {
    const r = await api("/api/identity/answer", {
      method: "POST",
      body: { challenge_id: ch.challenge_id, question_id: q.id, answer: value, parent_validated: parentValidated },
    });
    if (r.correct && !r.done) {
      speak(T("bravo")); confetti();
      state.qIndex += 1;
      setTimeout(screenQuestion, 700);
    } else if (r.correct && r.done) {
      if (r.denied && r.denied.reason === "daily_limit") return screenDailyLimit();
      if (r.denied) return screenError(T("need_consent"));
      state.token = r.session.token;
      state.remaining = r.session.remaining_seconds;
      state.breakShownAt = 0;
      confetti(); speak(T("play_together", { name: state.childName || "" }));
      startTimers();
      setTimeout(screenGame, 1200);
    } else {
      if (btn) { btn.classList.add("shake"); setTimeout(() => btn.classList.remove("shake"), 500); }
      speak(T("try_again"));
    }
  } catch (e) {
    if (e.status === 423) return screenLocked(e.body.detail && e.body.detail.locked_until);
    speak(T("try_again"));
  }
}

/* ---------------- Écrans verrou / limites ---------------- */
function screenLocked(until) {
  stopTimers(); clearChips();
  const when = until ? new Date(until).toLocaleTimeString(state.lang, { hour: "2-digit", minute: "2-digit" }) : "";
  show(
    el('<div class="kid-logo">🔒</div>'),
    el(`<h1 class="kid-title">${T("locked_title")}</h1>`),
    el(`<p class="kid-sub">${T("locked_body")}<br>${when ? T("locked_when", { t: when }) : ""}</p>`),
    el(`<p class="hint">${T("locked_mail")}</p>`),
    el(`<a class="tiny-link" href="parent.html">${T("parents_space")}</a>`)
  );
}
function screenDailyLimit() {
  stopTimers(); clearChips();
  show(
    el('<div class="kid-logo">🌙</div>'),
    el(`<h1 class="kid-title">${T("daily_title")}</h1>`),
    el(`<p class="kid-sub">${T("daily_body").replace("\n", "<br>")}</p>`),
    el(`<p class="hint">${T("daily_hint")}</p>`)
  );
  speak(T("daily_voice"));
}
function screenError(msg) {
  stopTimers(); clearChips();
  show(el('<div class="kid-logo">🧸</div>'), el(`<h1 class="kid-title">${T("oops")}</h1>`), el(`<p class="kid-sub">${msg}</p>`),
    (() => { const b = el(`<button class="btn-soft">${T("restart")}</button>`); b.onclick = screenWelcome; return b; })());
}

/* ---------------- Minuteur & veto bien-être ---------------- */
function startTimers() {
  stopTimers();
  ensureChip();
  state.ticker = setInterval(() => {
    state.remaining = Math.max(0, state.remaining - 1);
    ensureChip().textContent = "⏳ " + fmt(state.remaining);
  }, 1000);
  state.timer = setInterval(async () => {
    try {
      const s = await api("/api/session/status?token=" + encodeURIComponent(state.token));
      state.remaining = s.remaining_seconds;
      if (s.status === "veto") return screenPauseVeto();
    } catch (e) {}
  }, 5000);
}
function stopTimers() { [state.timer, state.ticker].forEach((t) => t && clearInterval(t)); state.timer = state.ticker = null; }
function screenPauseVeto() {
  stopTimers(); clearChips(); state.token = null;
  show(
    el('<div class="kid-logo">🌙</div>'),
    el(`<h1 class="kid-title">${T("veto_title")}</h1>`),
    el(`<p class="kid-sub">${T("veto_body").replace("\n", "<br>")}</p>`)
  );
  speak(T("veto_voice"));
}

/* ---------------- Pause respiration (anti-frustration) ---------------- */
function showBreakModal() {
  if (document.querySelector(".break-overlay")) return;
  const box = el(`<div class="break-overlay"><div class="break-card">
    <div style="font-size:64px">🌬️</div>
    <h2>${T("break_title").replace("🌬️ ", "")}</h2>
    <p>${T("break_body")}</p>
    <div style="display:flex;gap:12px;justify-content:center;margin-top:14px;flex-wrap:wrap">
      <button class="btn-soft" id="brkGo">${T("break_continue")}</button>
      <button class="btn-soft" id="brkStop">${T("break_stop")}</button>
    </div></div></div>`);
  document.body.appendChild(box);
  box.querySelector("#brkGo").onclick = () => { box.remove(); };
  box.querySelector("#brkStop").onclick = async () => {
    box.remove();
    try { await api("/api/session/end", { method: "POST", body: { token: state.token } }); } catch (e) {}
    screenDailyLimit();
  };
}

/* ---------------- ÉCRAN 3 : Leçon ---------------- */
async function screenGame() {
  if (!state.token) return screenWelcome();
  let step;
  try { step = await api("/api/learning/step?token=" + encodeURIComponent(state.token) + "&lang=" + state.lang); }
  catch (e) {
    if (e.status === 403 && e.body.detail && e.body.detail.reason === "veto") return screenPauseVeto();
    return screenWelcome();
  }
  if (step.mode === "done") return screenAllDone(step.progress);

  state.skill = step.skill; state.game = step.game; state.mode = step.mode;
  if (step.child) { state.speechSupport = !!step.child.speech_support; state.lang = step.child.lang || state.lang; }
  applyProfileClasses();
  state.roundOk = 0; state.roundAttempts = 0; state.lastTarget = null; state.songPlayed = new Set();
  renderGameFrame();
}
function applyProfileClasses() {
  document.body.classList.toggle("speech-support", !!state.speechSupport);
}
function gameHeader() {
  const wrap = el('<div style="display:flex; flex-direction:column; align-items:center; gap:8px; width:100%"></div>');
  wrap.appendChild(el(`<span class="chip-tag">${state.mode === "review" ? T("review") : T("new_lesson")} · ${state.skill.emoji} ${state.skill.label} · ${state.skill.domain_label}</span>`));
  const bar = el(`<div class="mastery-bar"><div class="mastery-fill" style="width:${Math.round(state.skill.mastery * 100)}%"></div></div>`);
  wrap.appendChild(bar);
  const quit = el(`<button class="quiet-quit">${T("finish")}</button>`);
  quit.onclick = async () => { try { await api("/api/session/end", { method: "POST", body: { token: state.token } }); } catch (e) {} screenWelcome(); };
  if (!document.querySelector(".quiet-quit")) document.body.appendChild(quit);
  return wrap;
}
function repeatBtn(spokenText, langOverride) {
  const b = el(`<button class="repeat-btn" title="🔊">🔊</button>`);
  b.onclick = () => speak(spokenText, langOverride);
  return b;
}
function promptNode(text, spokenText, langOverride) {
  const wrap = el('<div class="q-text"></div>');
  wrap.innerHTML = String(text).replace(/\n/g, "<br>");
  wrap.appendChild(repeatBtn(spokenText || text, langOverride));
  return wrap;
}
function renderGameFrame() {
  const g = state.game;
  if (g.type === "song") return renderSong(state.mode);
  if (g.type === "voice") return renderVoice(state.mode);
  if (g.type === "breath") return renderBreath(state.mode);
  if (g.type === "task") return renderTask(state.mode);
  return renderChoice(buildRound(g), state.mode);
}

/* ---------- construction des manches (tous types « à choix ») ---------- */
function buildRound(g) {
  switch (g.type) {
    case "tap": {
      const target = pickOne(g.items);
      const tpl = g.instruction_tpl || "Touche : {label} {emoji}";
      const txt = tpl.replace("{label}", target.label || "").replace("{emoji}", target.emoji || "");
      return { prompt: txt, options: g.items, targetId: target.id };
    }
    case "letters": {
      const abc = (g.alphabet || "ABCDEFGHIJKLMNOPQRSTUVWXYZ").split("");
      const target = abc[Math.floor(Math.random() * abc.length)];
      const others = shuffle(abc.filter((l) => l !== target)).slice(0, 3);
      const options = shuffle([target, ...others]).map((l) => ({ id: l, emoji: "", label: l }));
      return { prompt: T("letter_q", { l: target }), options, targetId: target };
    }
    case "count": {
      let n; do { n = rnd(g.min, g.max); } while (state.lastTarget === n && g.max > g.min);
      state.lastTarget = n; state.lastTargetKind = "count";
      const options = [];
      for (let v = g.min; v <= g.max; v++) options.push({ id: String(v), emoji: "", label: String(v) });
      return {
        prompt: `<span class="count-objs" style="font-size:${n > 8 ? 34 : 54}px">${Array(n + 1).join(g.object_emoji + " ")}</span><br>${T("count_q")}`,
        speak: T("count_voice"), options, targetId: String(n), isCount: true,
      };
    }
    case "math": return buildMath(g);
    case "sequence": {
      const p = pickOne(g.puzzles);
      const byId = Object.fromEntries(g.options.map((o) => [o.id, o]));
      const seqTxt = p.seq.map((id) => byId[id].emoji).join(" ") + " ❓";
      return { prompt: `<span style="font-size:40px">${seqTxt}</span><br>${T("seq_q")}`, speak: T("seq_q"), options: g.options, targetId: p.answer };
    }
    case "oddone": {
      const s = pickOne(g.sets);
      return { prompt: T("oddone_q", { hint: s.hint }), options: s.options.map((o) => ({ ...o, label: o.label || "" })), targetId: s.odd };
    }
    case "same": {
      const t = pickOne(g.targets);
      const options = shuffle([t.emoji, ...t.distractors]).map((e, i) => ({ id: e + i, emoji: e, label: "", _same: e }));
      const target = options.find((o) => o._same === t.emoji);
      return { prompt: `<span style="font-size:50px">${t.emoji}</span><br>${T("same_q")}`, speak: T("same_q"), options, targetId: target.id };
    }
    case "size": {
      const s = pickOne(g.sets);
      const askMax = state.roundOk % 2 === 0;
      const target = [...s.options].sort((a, b) => (askMax ? b.size - a.size : a.size - b.size))[0];
      const q = askMax ? T("big_q") : T("small_q");
      const options = s.options.map((o) => ({ ...o, fontSize: 30 + o.size * 14 }));
      return { prompt: q, options, targetId: target.id };
    }
    case "mix": {
      const c = pickOne(g.combos);
      const opts = shuffle([c.r, ...c.distractors]).map((e, i) => ({ id: e + i, emoji: e, label: "", _v: e }));
      const target = opts.find((o) => o._v === c.r);
      return { prompt: `<span style="font-size:44px">${c.a} ➕ ${c.b} = ❓</span><br>${T("mix_q")}`, speak: T("mix_q"), options: opts, targetId: target.id };
    }
    case "quiz": {
      const s = pickOne(g.scenes);
      return {
        prompt: s.q, options: s.options.map((o) => ({ ...o, big: true })), targetId: s.answer,
      };
    }
    default:
      return buildRound({ type: "tap", items: g.items || [] });
  }
}
function buildMath(g) {
  let prompt = "", ans = 0, options = [];
  if (g.kind === "after") {
    const n = rnd(g.min, g.max);
    prompt = T("after_q", { n });
    ans = n + 1;
    options = uniqOptions(ans, shuffle([n - 1, n + 2, n + 3, n - 2, ans + 4, ans + 10]));
  } else if (g.kind === "evenodd") {
    const wantEven = Math.random() < 0.5;
    const pool = []; for (let v = g.min; v <= g.max; v++) pool.push(v);
    const good = shuffle(pool.filter((v) => (v % 2 === 0) === wantEven))[0];
    const bad = shuffle(pool.filter((v) => (v % 2 === 0) !== wantEven)).slice(0, 3);
    prompt = wantEven ? T("even_q") : T("odd_q");
    ans = good;
    options = shuffle([good, ...bad]);
  } else if (g.kind === "sequence") {
    const step = g.step || 2;
    const start = rnd(g.min, Math.max(g.min, g.max - step * 3));
    prompt = `${start}, ${start + step}, ${start + 2 * step}, ❓`;
    ans = start + 3 * step;
    options = uniqOptions(ans, shuffle([ans + step, ans - step, ans + 2 * step, ans + 1, ans - 1]));
  } else if (g.kind === "add") {
    let a, b; do { a = rnd(g.min, g.max); b = rnd(g.min, g.max); } while (a + b > (g.max_sum || 10));
    prompt = `${a} ➕ ${b} = ❓`;
    ans = a + b;
    options = uniqOptions(ans, shuffle([ans + 1, ans - 1, ans + 2, ans - 2, ans + 3]));
  } else if (g.kind === "sub") {
    const a = rnd(g.min, g.max), b = rnd(1, a);
    prompt = `${a} ➖ ${b} = ❓`;
    ans = a - b;
    options = uniqOptions(ans, shuffle([ans + 1, ans + 2, Math.max(0, ans - 1), ans + 3]));
  } else if (g.kind === "mult") {
    const op = g.ops[Math.floor(Math.random() * g.ops.length)];
    const f = rnd(1, g.maxf || 5);
    prompt = `${op} ✖️ ${f} = ❓`;
    ans = op * f;
    options = uniqOptions(ans, shuffle([ans + op, ans - op, ans + 1, ans - 1, ans + 2 * op].filter((x) => x >= 0)));
  }
  return {
    prompt: `<span style="font-size:44px;font-weight:800">${prompt}</span>`,
    speak: prompt.replace(/[❓✖️➕➖]/g, " "),
    options: options.map((v) => ({ id: String(v), emoji: "", label: String(v) })),
    targetId: String(ans),
  };
}
function pickOne(arr) {
  let t;
  do { t = arr[Math.floor(Math.random() * arr.length)]; } while (state.lastTarget === t && arr.length > 1);
  state.lastTarget = t;
  return t;
}

/* ---------- rendu générique : consigne + grille de choix ---------- */
function renderChoice(round, mode) {
  const opts = round.options || [];
  show(gameHeader(mode), promptNode(round.prompt, round.speak || ""), 
    (() => { const hint = el('<p class="hint" style="margin-bottom:2px"></p>'); return hint; })());
  speak(round.speak || app.querySelector(".q-text").textContent);
  const grid = el(`<div class="grid-options ${opts.length > 5 ? "many" : ""}"></div>`);
  shuffle(opts).forEach((o) => {
    const fs = o.fontSize ? `font-size:${o.fontSize}px` : "";
    const b = el(`<button class="opt ${o.big ? "textbig" : ""}">${o.emoji ? `<span class="oe" style="${fs}">${o.emoji}</span>` : ""}<span class="ol" ${o.emoji ? "" : 'style="font-size:26px"'}>${o.label || ""}</span></button>`);
    b.onclick = async () => {
      state.roundAttempts += 1;
      if (o.id === round.targetId) {
        state.roundOk += 1; confetti();
        speak(round.isCount ? T("count_yes", { n: round.targetId }) : T("bravo"));
        await outcome(true);
        afterRound(mode);
      } else {
        b.classList.add("shake"); setTimeout(() => b.classList.remove("shake"), 500);
        speak(round.isCount ? T("recount") : T("try_again"));
        await outcome(false);
        maybeBreak();
      }
    };
    grid.appendChild(b);
  });
  app.appendChild(grid);
}
function maybeBreak() { /* la suggestion arrive aussi du backend ; filet local */
}

/* ---------- voix (répéter / lire / compter à voix haute) ---------- */
function renderVoice(mode) {
  const g = state.game;
  if (g.kind === "count_to") {
    const txt = T("count_to", { n: g.to });
    const done = el(`<button class="btn-big">${T("task_done")}</button>`);
    done.onclick = async () => { confetti(); speak(T("bravo")); await outcome(true); afterRound(mode); };
    show(gameHeader(mode), promptNode(txt), done);
    speak(txt);
    return;
  }
  const target = pickOne(g.targets || [""]);
  const targetLang = g.target_lang || state.lang;
  const intro = g.intro || { fr: "Répète", en: "Say", es: "Repite" }[state.lang] || "Répète";
  const big = el(`<div class="voice-target">${target}</div>`);
  const listen = el(`<button class="btn-soft">${T("voice_listen")}</button>`);
  listen.onclick = () => speak(target, targetLang);
  const nodes = [gameHeader(mode), promptNode(intro), big, listen];
  if (SR) {
    const mic = el(`<button class="mic">🎤</button>`);
    mic.onclick = async () => {
      mic.classList.add("listening");
      const said = await listenOnce(targetLang);
      mic.classList.remove("listening");
      if (said && matchLoose(said, target)) {
        state.roundOk += 1; confetti(); speak(T("bravo"));
        await outcome(true); afterRound(mode);
      } else {
        speak(T("try_again"));
        if (said) { state.roundAttempts += 1; await outcome(false); }
      }
    };
    nodes.push(mic);
  }
  const adult = el(`<button class="btn-soft">${T("adult_validate")}</button>`);
  adult.onclick = async () => { state.roundOk += 1; confetti(); speak(T("bravo")); await outcome(true); afterRound(mode); };
  nodes.push(adult);
  show(...nodes);
  speak(intro + ". " + target, targetLang);
}
function matchLoose(said, target) {
  const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9 ]/g, "").trim();
  const a = norm(said), b = norm(target).replace(/…|\.\.\.$/, "");
  if (!b) return false;
  return a.includes(b) || b.split(" ").every((w) => a.includes(w));
}

/* ---------- respiration guidée ---------- */
function renderBreath(mode) {
  const g = state.game;
  const cycles = g.cycles || 3;
  let stepN = 0;
  const circle = el('<div class="breath-circle">🌬️</div>');
  const label = el(`<div class="q-text"></div>`);
  show(gameHeader(mode), label, circle);
  function next() {
    if (stepN >= cycles * 2) {
      confetti(); speak(T("breath_done"));
      (async () => { await outcome(true); })().then(() => afterRound(mode));
      return;
    }
    const inhale = stepN % 2 === 0;
    const key = inhale ? "breath_in" : "breath_out";
    label.textContent = T(key);
    speak(T(key));
    circle.classList.remove("in", "out");
    void circle.offsetWidth;
    circle.classList.add(inhale ? "in" : "out");
    stepN += 1;
    state.breathTimer = setTimeout(next, 3600);
  }
  next();
}

/* ---------- tâche hors-écran (écriture…) ---------- */
function renderTask(mode) {
  const g = state.game;
  const task = pickOne(g.tasks || ["…"]);
  const listen = el(`<button class="btn-soft">${T("task_listen")}</button>`);
  listen.onclick = () => speak(task);
  const done = el(`<button class="btn-big">${T("task_done")}</button>`);
  done.onclick = async () => { confetti(); speak(T("bravo")); await outcome(true); afterRound(mode); };
  show(gameHeader(mode), promptNode(task), el(`<p class="hint">${T("task_adult")}</p>`), listen, done);
  speak(task);
}

/* ---------- comptine ---------- */
function renderSong(mode) {
  const g = state.game;
  const nodes = [gameHeader(mode), el(`<div class="q-text">🎵 ${g.title}</div>`), el(`<p class="hint">${T("song_listen")}</p>`)];
  g.lines.forEach((line, idx) => {
    const row = el(`<div class="song-line"><span>${line}</span></div>`);
    const btn = el("<button>🔊</button>");
    btn.onclick = () => { speak(line); state.songPlayed.add(idx); maybeSongDone(); };
    row.appendChild(btn);
    nodes.push(row);
  });
  show(...nodes);
  function maybeSongDone() {
    if (state.songPlayed.size >= g.lines.length && !document.querySelector("[data-songdone]")) {
      const b = el(`<button class="btn-big" data-songdone="1">${T("song_done")}</button>`);
      b.onclick = async () => { confetti(); speak(T("song_bravo")); await outcome(true); screenGame(); };
      app.appendChild(b);
    }
  }
}

/* ---------- résultats ---------- */
async function outcome(success) {
  try {
    const r = await api("/api/learning/outcome", {
      method: "POST", body: { token: state.token, skill_id: state.skill.id, success },
    });
    if (r.suggest_break) setTimeout(showBreakModal, 800);
    if (r.accelerated) {
      toast(T("accel", { name: "" }).replace(" : ", " !"), 3400);
      setTimeout(() => speak(T("accel_voice")), 900);
    }
    if (r.mastered_now) confetti();
  } catch (e) {}
}
function afterRound(mode) {
  const g = state.game;
  const goal = g.rounds || 3;
  if (state.roundOk >= goal) { confetti(); clearTimeout(state.breathTimer); setTimeout(screenGame, 900); return; }
  if (state.roundAttempts >= goal + 6) { setTimeout(screenGame, 400); return; } // on avance sans frustrer
  renderGameFrame();
}
function screenAllDone(progress) {
  show(
    el('<div class="kid-logo">🏆</div>'),
    el(`<h1 class="kid-title">${T("alldone_t1", { name: state.childName || "" })}</h1>`),
    el(`<p class="kid-sub">${T("alldone_body", { m: progress.mastered, t: progress.total, p: progress.pct }).replace("\n", "<br>")}</p>`),
    el(`<p class="hint">${T("alldone_hint")}</p>`),
    (() => { const b = el(`<button class="btn-soft">${T("alldone_end")}</button>`); b.onclick = async () => { try { await api("/api/session/end", { method: "POST", body: { token: state.token } }); } catch (e) {} screenWelcome(); }; return b; })()
  );
  confetti(); speak(T("alldone_voice"));
}

/* ---------------- go ---------------- */
if (window.speechSynthesis) speechSynthesis.getVoices();
window.I18N.applyStatic();
screenWelcome();
