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

const state = {
  childId: null, childName: "",
  lang: "fr",                          // ← langue du PROFIL (jamais persistée)
  speechSupport: false,
  challenge: null, qIndex: 0,
  token: null, remaining: 0, timer: null, ticker: null,
  skill: null, game: null, mode: "new",
  roundOk: 0, roundAttempts: 0, lastTarget: null, breakShownAt: 0, micFails: 0, freePick: false,
  songPlayed: new Set(), breathTimer: null,
};

/* Tout l'affichage suit la langue du PROFIL regardé — jamais celle stockée
   sur l'appareil (isolation multi-profils stricte). */
const T = (k, v) => window.I18N.tIn(state.lang, "kid." + k, v);

/* Le sélecteur de drapeaux, sur la page enfant, ne change QUE la session en
   cours (override temporaire) — il n'écrit JAMAIS la préférence globale, qui
   reste celle du tableau de bord des parents. */
window.__JB_LANG_HOOK__ = (l) => {
  state.lang = l;
  window.I18N.syncSwitcher(l);
  screenWelcome();
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
    const clean = String(text).replace(/[\p{Extended_Pictographic}\uFE0F]/gu, "").replace(/\n+/g, " ");
    const lang = langOverride || state.lang;
    const ttsLang = window.I18N.TTS_LANG[lang] || "fr-FR";
    const rate = state.speechSupport ? 0.7 : 0.95;
    // Coquille Android (APK) : la voix passe par le synthétiseur natif du téléphone,
    // car le WebView Android n'implémente pas l'API Web Speech.
    if (window.AndroidTTS && typeof window.AndroidTTS.speak === "function") {
      window.AndroidTTS.stop();
      window.AndroidTTS.speak(clean, ttsLang, rate, 1.1);
      return;
    }
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = ttsLang;
    u.rate = rate;
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
/**
 * [AJOUT — MICRO-REPLI v2.5.1] Écoute avec repli parental automatique.
 * Le micro peut « exister » sans fonctionner : coquille Windows (Electron)
 * sans service de reconnaissance Google, permission refusée, ou voix
 * d'enfant trop aiguë pour des modèles entraînés sur des adultes.
 * Règle : JAMAIS de blocage pour l'enfant.
 *   1ᵉʳ échec → « réessaie » (le souffle d'une seconde chance)
 *   2ᵉ  échec → le micro se retire pour la session, le bouton adulte
 *               s'illumine (.btn-big) et l'app l'annonce clairement.
 */
async function micAttempt(mic, langCode, onHeard, adultBtn) {
  mic.classList.add("listening");
  const said = await listenOnce(langCode);
  mic.classList.remove("listening");
  if (said) { state.micFails = 0; onHeard(said); return; }
  state.micFails = (state.micFails || 0) + 1;
  if (state.micFails >= 2) {
    try { mic.remove(); } catch (e) { /* déjà parti */ }
    if (adultBtn) adultBtn.classList.add("btn-big");
    speak(T("mic_parent_hint"));
  } else {
    speak(T("mic_retry"));
  }
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
function clearChips() { document.querySelectorAll(".chip, .quiet-quit, .breath-overlay, .repeat-btn, .garden-back-btn").forEach((n) => n.remove()); }

/* ---------------- ÉCRAN 1 : Bienvenue ---------------- */
/**
 * Règle absolue : la langue suit le PROFIL de l'enfant.
 * Elle vit dans state.lang (mémoire) — JAMAIS dans le localStorage de
 * l'appareil : chaque enfant a SA langue, qui n'en impacte aucune autre.
 */
function applyChildLanguage(child) {
  const lang = child && child.lang ? child.lang : null;
  if (!lang) return;
  state.lang = lang;
  window.I18N.syncSwitcher(lang);
}

async function screenWelcome() {
  stopTimers(); clearChips(); state.token = null;
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
    const parentBtn = el(`<button class="btn-soft">${T("adult_validate")}</button>`);
    parentBtn.onclick = () => answerQuestion("", true, parentBtn);
    if (SR) {
      const mic = el('<button class="mic">🎤</button>');
      mic.onclick = () => micAttempt(mic, ch.lang, (said) => answerQuestion(said, false, mic), parentBtn);
      nodes.push(mic);
    }
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
      setTimeout(screenJardin, 1200); // [AJOUT — JARDIN] le foyer = le pré fleuri
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

/* ---------------- [AJOUT — BIBLIOTHÈQUE v2.6.1] Les Livres du Jardin ----------------
   MENU = la pile de livres de la photo de Jade : chaque LIVRE est une
   rubrique (domaine). On ouvre le livre → ses fleurs à cueillir.
   La carte 🎯 « Mon programme » reste la lanterne adaptative ; le livre
   qui abrite la fleur recommandée pulse doucement pour guider l'œil. */

// Une mascotte-emoji par rubrique (côté enfant, décoratif — les données
// viennent toutes du serveur).
const DOMAIN_EMOJI = {
  maths: "🔢", formes: "🟪", arts: "🎨", animaux: "🐾", francais: "📖",
  anglais: "🗽", espagnol: "💃", logique: "🧩", "bien-etre": "🌙",
  decouverte: "🌍", comptines: "🎵", invention: "💡", lingala: "🦜", portugais: "🐬",
};

function flowerButtonNode(fl) {
  const f = el(`<button class="flower ${fl.status}${fl.recommended ? " rec" : ""}"><span class="fe">${fl.emoji}</span><span class="fl">${fl.label}</span></button>`);
  if (fl.status === "locked") {
    f.onclick = () => { f.classList.add("shake"); setTimeout(() => f.classList.remove("shake"), 500); speak(T("garden_bud_voice")); };
  } else {
    f.onclick = () => { state.freePick = true; screenGame(fl.id); };
  }
  return f;
}

async function screenJardin() {
  if (!state.token) return screenWelcome();
  state.freePick = false;
  document.querySelectorAll(".garden-back-btn").forEach((n) => n.remove());
  let g;
  try { g = await api("/api/learning/garden?token=" + encodeURIComponent(state.token) + "&lang=" + state.lang); }
  catch (e) {
    if (e.status === 403 && e.body.detail && e.body.detail.reason === "veto") return screenPauseVeto();
    return screenWelcome();
  }
  const hero = el('<div class="garden-hero"></div>');
  hero.appendChild(el(`<h1 class="kid-title">${T("garden_title", { name: state.childName || "" })}</h1>`));
  hero.appendChild(el(`<p class="hint">${T("lib_sub")}</p>`));
  const prog = el(`<button class="program-card">🎯 <span>${T("garden_program")}</span><span class="pc-sub">⭐ ${g.counts.mastered}/${g.total}</span></button>`);
  prog.onclick = () => screenGame();
  hero.appendChild(prog);

  const shelf = el('<div class="shelf"></div>');
  g.beds.forEach((bed, i) => {
    const open = bed.flowers.filter((f) => f.status !== "locked").length;
    const hasRec = bed.flowers.some((f) => f.recommended);
    const book = el(
      `<button class="book ${bed.closed ? "closed" : ""}${hasRec ? " rec" : ""}" style="--rot:${(i % 3 - 1) * 1.15}deg; --mx:${(i % 2) * 4}%">` +
      `<span class="b-emoji">${DOMAIN_EMOJI[bed.domain] || "📕"}</span>` +
      `<span class="b-title">${bed.domain_label}</span>` +
      `<span class="b-meta">${open ? "🌸 " + open : "🌱"}</span>` +
      `<span class="b-heart" aria-hidden="true">🤍</span></button>`
    );
    book.onclick = () => screenRubrique(bed);
    shelf.appendChild(book);
  });

  show(hero, shelf);
  speak(T("lib_sub"));
}

/* Livre ouvert : la rubrique avec ses fleurs à cueillir (vue « pages »). */
function screenRubrique(bed) {
  state.freePick = false;
  document.querySelectorAll(".garden-back-btn").forEach((n) => n.remove());
  const page = el('<div class="bookpage"></div>');
  page.appendChild(el(
    `<div class="page-head">` +
    `<span class="b-emoji">${DOMAIN_EMOJI[bed.domain] || "📕"}</span>` +
    `<h2 class="page-title">${bed.domain_label}</h2></div>`
  ));
  const grid = el('<div class="bed-grid"></div>');
  bed.flowers.forEach((fl) => grid.appendChild(flowerButtonNode(fl)));
  page.appendChild(grid);

  const back = el(`<button class="btn-soft">${T("lib_back")}</button>`);
  back.onclick = () => screenJardin();
  show(page, back);
  speak(bed.domain_label);
}

/* ---------------- ÉCRAN 3 : Leçon ---------------- */
async function screenGame(skillId) {
  if (!state.token) return screenWelcome();
  let step;
  const url = "/api/learning/step?token=" + encodeURIComponent(state.token) + "&lang=" + state.lang +
    (skillId ? "&skill_id=" + encodeURIComponent(skillId) : "");
  try { step = await api(url); }
  catch (e) {
    // Fleur choisie mais pas éclose : mot doux + retour au pré (jamais d'erreur sèche)
    if (e.status === 403 && skillId) { speak(T("garden_bud_voice")); return screenJardin(); }
    if (e.status === 403 && e.body.detail && e.body.detail.reason === "veto") return screenPauseVeto();
    return screenWelcome();
  }
  if (step.mode === "done") return screenAllDone(step.progress);

  state.skill = step.skill; state.game = step.game; state.mode = step.mode;
  if (step.mode !== "choice") { // le programme garde son fil — et le bouton jardin se retire
    state.freePick = false;
    document.querySelectorAll(".garden-back-btn").forEach((n) => n.remove());
  }
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
  // [AJOUT — JARDIN] en jeu libre, petit chemin de retour au pré (sans fermer la session)
  if (state.freePick && !document.querySelector(".garden-back-btn")) {
    const gb = el(`<button class="garden-back-btn">${T("garden_back")}</button>`);
    gb.onclick = () => screenJardin();
    document.body.appendChild(gb);
  }
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
  if (g.type === "draw") return renderDraw(state.mode);
  if (g.type === "build") return renderBuild(state.mode);
  if (g.type === "chat") return renderChat(state.mode);
  if (g.type === "coloring") return renderColoring(state.mode);
  return renderChoice(buildRound(g), state.mode);
}

/* ---------- conversation animée (type « chat » — lingala, portugais…) ----------
   Un guide animé qui fait des GESTES DÉMONSTRATIFS (signe de la main,
   révérence, dodo…) : l'enfant regarde le geste, écoute le mot, le répète —
   et l'adulte valide la réplique (toujours un succès : c'est un dialogue). */
function renderChat(mode) {
  const g = state.game;
  const lines = g.lines || [];
  const partner = (g.partner && g.partner.emoji) || "🤗";
  const cheer = (typeof g.cheer === "string" && g.cheer) || T("bravo");
  let idx = 0;

  function step() {
    const l = lines[idx];
    const mascot = el(`<div class="mascot-wrap"><div class="mascot ${l.gesture || "wave"}">${partner}</div><div class="mascot-shadow"></div></div>`);
    const said = el(`<div class="chat-bubble"><span class="chat-big">${l.say_l}</span></div>`);
    said.appendChild(repeatBtn(l.say_l));
    const counter = el(`<span class="chip-tag">${idx + 1} / ${lines.length}</span>`);
    const done = el(`<button class="btn-big">${T("adult_validate")}</button>`);
    done.onclick = async () => {
      confetti();
      idx += 1;
      if (idx >= lines.length) {
        speak(cheer);
        await outcome(true); afterRound(mode);
      } else {
        speak(T("bravo")); setTimeout(step, 700);
      }
    };
    show(gameHeader(mode), counter, promptNode(l.say_i18n), mascot, said, done,
      el(`<p class="hint">${T("adult_validate")}</p>`));
    setTimeout(() => speak(l.say_i18n + " " + l.say_l), 250);
  }
  step();
}

/* ---------- fabrique & assemble (Créer & Inventer — type « build ») ----------
   Un PLAN schématisé (pièces numérotées) + des pièces à JOINDRE une à une.
   Résultat GARANTI : la mauvaise pièce gigote (aucune pénalité), la bonne
   s'emboîte — à la fin, la création prend vie : confettis + encouragement. */
function renderBuild(mode) {
  const g = state.game;
  const parts = g.parts || [];
  const intro = (typeof g.intro === "string" && g.intro) || T("build_hint");

  const plan = el('<div class="build-plan"></div>');
  parts.forEach((p, i) => {
    plan.appendChild(el(`<div class="build-step" data-i="${i}"><span class="build-num">${i + 1}</span><span class="build-piece">${p.emoji}</span></div>`));
    if (i < parts.length - 1) plan.appendChild(el('<span class="build-arrow">➜</span>'));
  });

  const zone = el(`<div class="build-zone"><span class="build-zone-hint">${T("build_zone")}</span></div>`);
  const tray = el('<div class="build-tray"></div>');

  let next = 0;
  const markNext = () => {
    plan.querySelectorAll(".build-step").forEach((st) => st.classList.remove("next"));
    const st = plan.querySelector(`[data-i="${next}"]`);
    if (st) st.classList.add("next");                          // la prochaine pièce PULSE : l'œil suit le plan
  };
  shuffle(parts.map((p, i) => i)).forEach((idx) => {
    const p = parts[idx];
    const b = el(`<button class="build-part">${p.emoji}<small>${p.label || ""}</small></button>`);
    b.onclick = () => {
      if (idx !== next) {                                      // pas la bonne pièce : elle gigote, c'est tout
        b.classList.add("shake"); setTimeout(() => b.classList.remove("shake"), 500);
        speak(parts[next].label || "");
        return;
      }
      b.remove();                                              // bonne pièce → elle s'emboîte ✨
      const step = plan.querySelector(`[data-i="${idx}"]`);
      if (step) { step.classList.remove("next"); step.classList.add("done"); }
      const hint = zone.querySelector(".build-zone-hint"); if (hint) hint.remove();
      zone.classList.add("build-compose");                     // la création se COMPOSE en hauteur, grand format
      zone.appendChild(el(`<span class="build-placed">${p.emoji}</span>`));
      speak(p.label || "");
      next += 1;
      markNext();
      if (next >= parts.length) {                              // RÉSULTAT : toujours obtenu 🎉
        zone.appendChild(el(`<div class="build-result">${(g.result && g.result.emoji) || "🎉"}</div>`));
        tray.remove();
        confetti();
        const cheer = (typeof g.cheer === "string" && g.cheer) || T("bravo");
        setTimeout(() => speak(cheer), 400);
        setTimeout(async () => { await outcome(true); afterRound(mode); }, 1500);
      }
    };
    tray.appendChild(b);
  });

  show(gameHeader(mode), promptNode(intro), plan, zone, tray);
  markNext();
  speak(intro);
}

/* ---------- fiche de fabrication illustrée (schémas étape par étape + matériel) ---------- */
function guideFiche(guide, materiel) {
  const f = el(`<div class="guide"><div class="guide-title">${T("guide_title")}</div>${materiel ? `<div class="guide-mat">${materiel}</div>` : ""}<div class="guide-steps"></div></div>`);
  const row = f.querySelector(".guide-steps");
  guide.forEach((s, i) => {
    row.appendChild(el(`<div class="guide-step"><span class="build-num">${i + 1}</span><span class="guide-emoji">${s.emoji}</span><span class="guide-label">${s.label}</span></div>`));
  });
  return f;
}

/* ---------- moteur de dessin partagé (ardoise + coloriages) ----------
   Traits GLISSÉS au doigt ou au stylet, 3 tailles de mine (finesse/précision
   demandées : mine fine 7px pour les détails, moyenne 16px, grosse 30px) +
   gomme qui n'efface QUE la couleur de l'enfant (jamais les contours). */
function setupCanvasPaint(cv, palette) {
  const ctx = cv.getContext("2d");
  const paint = { ctx, color: palette[0], size: 16, eraser: false };
  paint.setColor = (c) => { paint.color = c; paint.eraser = false; };
  paint.setSize = (s) => { paint.size = s; paint.eraser = false; };
  paint.setEraser = (on) => { paint.eraser = on; };
  const r0 = cv.getBoundingClientRect();
  cv.width = Math.max(50, Math.round(r0.width));
  cv.height = Math.max(50, Math.round(r0.height));
  const pt = (e) => {
    const r = cv.getBoundingClientRect();
    return [(e.clientX - r.left) * (cv.width / r.width), (e.clientY - r.top) * (cv.height / r.height)];
  };
  let last = null;
  cv.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    try { cv.setPointerCapture(e.pointerId); } catch (err) {}
    last = pt(e);
    ctx.globalCompositeOperation = paint.eraser ? "destination-out" : "source-over";
    ctx.fillStyle = paint.color;
    ctx.beginPath(); ctx.arc(last[0], last[1], (paint.eraser ? paint.size + 10 : paint.size) / 2, 0, Math.PI * 2); ctx.fill();
  });
  cv.addEventListener("pointermove", (e) => {
    if (!last) return;
    e.preventDefault();
    const p = pt(e);
    ctx.globalCompositeOperation = paint.eraser ? "destination-out" : "source-over";
    ctx.strokeStyle = paint.color;
    ctx.lineWidth = paint.eraser ? paint.size + 20 : paint.size;
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    ctx.beginPath(); ctx.moveTo(last[0], last[1]); ctx.lineTo(p[0], p[1]); ctx.stroke();
    last = p;
  });
  ["pointerup", "pointercancel", "pointerleave"].forEach((ev) => cv.addEventListener(ev, () => { last = null; }));
  return paint;
}
function paletteRow(palette, paint) {
  const pal = el('<div class="draw-pal"></div>');
  palette.forEach((c, i) => {
    const d = el(`<button class="draw-dot${i === 0 ? " active" : ""}" style="background:${c}" aria-label="couleur"></button>`);
    d.onclick = () => { paint.setColor(c); pal.querySelectorAll(".draw-dot,.draw-eraser").forEach((x) => x.classList.remove("active")); d.classList.add("active"); };
    pal.appendChild(d);
  });
  return pal;
}
function nibRow(paint, pal) {
  const tools = el('<div class="draw-tools"></div>');
  const sizes = [[7, "draw_thin"], [16, "draw_normal"], [30, "draw_thick"]];
  const btns = sizes.map(([sz, key], i) => {
    const b = el(`<button class="draw-size${i === 1 ? " active" : ""}">${T(key)}</button>`);
    b.onclick = () => {
      paint.setSize(sz);
      tools.querySelectorAll(".draw-size").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      if (pal) pal.querySelectorAll(".draw-eraser").forEach((x) => x.classList.remove("active"));
    };
    tools.appendChild(b); return b;
  });
  const gum = el(`<button class="draw-size draw-eraser">${T("draw_eraser")}</button>`);
  gum.onclick = () => { paint.setEraser(true); tools.querySelectorAll(".draw-size").forEach((x) => x.classList.remove("active")); gum.classList.add("active"); };
  tools.appendChild(gum);
  return tools;
}

/* ---------- ardoise magique (Créer & Inventer — type « draw ») ----------
   Un espace pour CONCEvoir : l'enfant dessine au doigt ou au stylet, l'adulte valide.
   Jamais de « mauvaise réponse » : outcome(true) systématique (anti-frustration). */
function renderDraw(mode) {
  const g = state.game;
  const intro = (typeof g.intro === "string" && g.intro) ||
    { fr: "Dessine avec ton doigt ou ton stylet !", en: "Draw with your finger or your stylus!", es: "¡Dibuja con tu dedo o tu lápiz óptico!" }[state.lang] || "Dessine !";
  const palette = (Array.isArray(g.palette) && g.palette.length) ? g.palette
    : ["#e11d48", "#2563eb", "#16a34a", "#eab308", "#9333ea", "#0ea5e9", "#f97316", "#1e293b"];

  const cv = el('<canvas class="draw-canvas"></canvas>');
  const palHolder = el('<div></div>');
  const toolsHolder = el('<div></div>');
  const done = el(`<button class="btn-big">${T("draw_done")}</button>`);
  done.onclick = async () => { confetti(); speak(T("bravo")); await outcome(true); afterRound(mode); };

  show(gameHeader(mode), promptNode(intro), cv, palHolder, toolsHolder, done, el(`<p class="hint">${T("draw_adult")}</p>`));

  const paint = setupCanvasPaint(cv, palette);
  const pal = paletteRow(palette, paint);
  const tools = nibRow(paint, pal);
  const clear = el(`<button class="draw-size">${T("draw_clear")}</button>`);
  clear.onclick = () => paint.ctx.clearRect(0, 0, cv.width, cv.height);
  tools.appendChild(clear);
  palHolder.replaceWith(pal); toolsHolder.replaceWith(tools);
  speak(intro);
}

/* ---------- coloriage de précision (type « coloring ») ----------
   Une grande image à CONTOURS ÉPAIS : l'enfant colorie SOUS le trait (calque
   transparent posé par-dessus) → le dessin reste toujours net, même si la
   couleur déborde. Mines fines/moyennes/grosses + gomme — doigt ou stylet. */
function renderColoring(mode) {
  const g = state.game;
  const title = (typeof g.title === "string" && g.title) || T("draw_adult");
  const palette = ["#e11d48", "#2563eb", "#16a34a", "#eab308", "#9333ea", "#0ea5e9", "#f97316", "#7c3aed", "#84cc16", "#fb7185", "#f59e0b", "#1e293b"];

  const wrap = el('<div class="color-wrap"></div>');
  const cv = el('<canvas class="draw-canvas color-canvas"></canvas>');
  const lines = el(`<div class="color-lines">${g.art || ""}</div>`);
  wrap.appendChild(cv); wrap.appendChild(lines);

  const palHolder = el('<div></div>');
  const toolsHolder = el('<div></div>');
  const done = el(`<button class="btn-big">${T("draw_done")}</button>`);
  done.onclick = async () => { confetti(); speak(T("bravo")); await outcome(true); afterRound(mode); };

  show(gameHeader(mode), promptNode(title), wrap, palHolder, toolsHolder, done, el(`<p class="hint">${T("draw_adult")}</p>`));

  const paint = setupCanvasPaint(cv, palette);
  const pal = paletteRow(palette, paint);
  const tools = nibRow(paint, pal);
  const clear = el(`<button class="draw-size">${T("draw_clear")}</button>`);
  clear.onclick = () => paint.ctx.clearRect(0, 0, cv.width, cv.height);
  tools.appendChild(clear);
  palHolder.replaceWith(pal); toolsHolder.replaceWith(tools);
  speak(title);
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
  shuffle(opts).forEach((o, i) => {
    const fs = o.fontSize ? `font-size:${o.fontSize}px` : "";
    const b = el(`<button class="opt opt-r${i % 6} ${o.big ? "textbig" : ""}">${o.emoji ? `<span class="oe" style="${fs}">${o.emoji}</span>` : ""}<span class="ol" ${o.emoji ? "" : 'style="font-size:26px"'}>${o.label || ""}</span></button>`);
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
  const adult = el(`<button class="btn-soft">${T("adult_validate")}</button>`);
  adult.onclick = async () => { state.roundOk += 1; confetti(); speak(T("bravo")); await outcome(true); afterRound(mode); };
  if (SR) {
    const mic = el(`<button class="mic">🎤</button>`);
    mic.onclick = () => micAttempt(mic, targetLang, async (said) => {
      if (matchLoose(said, target)) {
        state.roundOk += 1; confetti(); speak(T("bravo"));
        await outcome(true); afterRound(mode);
      } else {
        speak(T("try_again"));
        state.roundAttempts += 1; await outcome(false);
      }
    }, adult);
    nodes.push(mic);
  }
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
  const nodes = [gameHeader(mode), promptNode(task)];
  if (Array.isArray(g.guide) && g.guide.length) nodes.push(guideFiche(g.guide, g.materiel));  // schémas + moyens de bord
  nodes.push(el(`<p class="hint">${T("task_adult")}</p>`), listen, done);
  show(...nodes);
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
      b.onclick = async () => { confetti(); speak(T("song_bravo")); await outcome(true); if (state.freePick) screenJardin(); else screenGame(); };
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
  // [AJOUT — JARDIN] fleur cueillie librement → on retourne au pré ; sinon le programme continue
  const next = state.freePick ? screenJardin : screenGame;
  if (state.roundOk >= goal) { confetti(); clearTimeout(state.breathTimer); setTimeout(next, 900); return; }
  if (state.roundAttempts >= goal + 6) { setTimeout(next, 400); return; } // on avance sans frustrer
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

/* ---------- décor vivant (émojis flottants, purement décoratif) ---------- */
function mountDeco() {
  if (document.querySelector(".deco")) return;
  const wrap = el('<div class="deco" aria-hidden="true"></div>');
  ["🎈", "⭐", "🌈", "☁️", "🎈", "✨", "☁️", "🎵", "🧸", "🌟"].forEach((e, i) => {
    wrap.appendChild(el(`<span style="left:${(i * 11 + 3) % 96}vw; animation-duration:${15 + i * 3}s; animation-delay:${-i * 2.5}s">${e}</span>`));
  });
  document.body.appendChild(wrap);
}
document.addEventListener("DOMContentLoaded", mountDeco);
window.I18N.applyStatic();
screenWelcome();
