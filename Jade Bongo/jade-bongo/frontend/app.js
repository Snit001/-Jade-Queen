"use strict";
/* ============================================================
   Jade Bɔngɔ́ — Application enfant (Phase 1 : voix + images)
   Identification obligatoire → parcours étape par étape →
   veto bien-être en temps réel. Toutes les données viennent de
   l'API ; rien n'est codé en dur côté client sauf l'UX.
   ============================================================ */

const app = document.getElementById("app");
const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;

const state = {
  challenge: null, qIndex: 0,
  token: null, remaining: 0, timer: null, ticker: null,
  skill: null, game: null,
  roundOk: 0, roundAttempts: 0, lastTarget: null,
  songPlayed: new Set(),
};

/* ---------------- helpers ---------------- */
function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}
function show(...nodes) { app.innerHTML = ""; nodes.forEach((n) => app.appendChild(n)); }
function shuffle(a) { const c = [...a]; for (let i = c.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [c[i], c[j]] = [c[j], c[i]]; } return c; }
function fmt(s) { const m = Math.floor(s / 60), r = s % 60; return m + ":" + String(r).padStart(2, "0"); }

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

/* voix : TTS (partout) + STT (si disponible, sinon validation parentale) */
function speak(text) {
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[🔴🔵🟢🟡🐱🐶🐰🦆⭐❤️🔺⭕🟦🍎🎉🌟🚀💪🏆🌙🎵🐭🌿🐾🎩]/gu, ""));
    u.lang = "fr-FR"; u.rate = 0.95; u.pitch = 1.1;
    const v = speechSynthesis.getVoices().find((v) => v.lang && v.lang.toLowerCase().startsWith("fr"));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  } catch (e) { /* silencieux : l'affichage suffit */ }
}
function listenOnce() {
  return new Promise((resolve) => {
    if (!SR) return resolve(null);
    try {
      const rec = new SR();
      rec.lang = "fr-FR"; rec.interimResults = false; rec.maxAlternatives = 3;
      let done = false;
      rec.onresult = (ev) => { done = true; resolve(ev.results[0][0].transcript || ""); };
      rec.onerror = () => resolve(null);
      rec.onend = () => { if (!done) resolve(null); };
      rec.start();
      setTimeout(() => { if (!done) { try { rec.stop(); } catch (e) {} } }, 6000);
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
function ensureChip() {
  let c = document.querySelector(".chip");
  if (!c) { c = el('<div class="chip">⏳ …</div>'); document.body.appendChild(c); }
  return c;
}
function clearChips() { document.querySelectorAll(".chip, .quiet-quit").forEach((n) => n.remove()); }

/* ---------------- ÉCRAN 1 : Bienvenue ---------------- */
async function screenWelcome() {
  stopTimers(); clearChips(); state.token = null;
  let phaseTxt = "", parentNote = "";
  try {
    const age = await api("/api/age");
    phaseTxt = `${age.phase_label} — ${age.years} ans`;
    if (age.policy && age.policy.requires_parent_present) parentNote = "💛 Un adulte accompagne Jade pendant la session.";
  } catch (e) {}
  show(
    el('<div class="kid-logo">⭐</div>'),
    el('<h1 class="kid-title">Jade Bɔngɔ́</h1>'),
    el(`<p class="kid-sub">L'école magique de Jade<br>${phaseTxt}</p>`),
    (() => { const b = el('<button class="btn-big">▶ Commencer</button>'); b.onclick = startChallenge; return b; })(),
    el(`<p class="hint">${parentNote}</p>`),
    el('<a class="tiny-link" href="parent.html">👨‍👩‍👧 Espace Parents</a>')
  );
}

/* ---------------- ÉCRAN 2 : Identification (Portier) ---------------- */
async function startChallenge() {
  try {
    state.challenge = await api("/api/identity/challenge", { method: "POST" });
    state.qIndex = 0;
    speak("Coucou ! C'est bien toi Jade ?");
    screenQuestion();
  } catch (e) {
    if (e.status === 423) return screenLocked(e.body.detail && e.body.detail.locked_until);
    screenError("Oh oh, petit souci. Demande à un adulte !");
  }
}
function screenQuestion() {
  const ch = state.challenge, i = state.qIndex, q = ch.questions[i];
  const nodes = [
    el(`<div class="q-progress">Question ${i + 1} / ${ch.questions.length}</div>`),
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
    nodes.push(el('<p class="hint">🎤 Dis ta réponse à voix haute !</p>'));
    if (SR) {
      const mic = el('<button class="mic">🎤</button>');
      mic.onclick = async () => {
        mic.classList.add("listening");
        const said = await listenOnce();
        mic.classList.remove("listening");
        if (said) answerQuestion(said, false, mic);
        else speak("Je n'ai pas entendu. Réessaie !");
      };
      nodes.push(mic);
    }
    const parentBtn = el('<button class="btn-soft">✅ Un adulte valide ma réponse</button>');
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
      speak("Bravo !"); confetti();
      state.qIndex += 1;
      setTimeout(screenQuestion, 700);
    } else if (r.correct && r.done) {
      if (r.denied && r.denied.reason === "daily_limit") return screenDailyLimit();
      if (r.denied) return screenError("Un adulte doit d'abord autoriser les leçons (Espace Parents).");
      state.token = r.session.token;
      state.remaining = r.session.remaining_seconds;
      confetti(); speak("Bonjour Jade ! On va jouer et apprendre ensemble !");
      startTimers();
      setTimeout(screenGame, 1200);
    } else {
      if (btn) { btn.classList.add("shake"); setTimeout(() => btn.classList.remove("shake"), 500); }
      speak("Essaie encore, tu vas y arriver !");
    }
  } catch (e) {
    if (e.status === 423) return screenLocked(e.body.detail && e.body.detail.locked_until);
    speak("Essaie encore !");
  }
}

/* ---------------- ÉCRANS verrou / limites ---------------- */
function screenLocked(until) {
  stopTimers(); clearChips();
  const when = until ? new Date(until).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) : "";
  show(
    el('<div class="kid-logo">🔒</div>'),
    el('<h1 class="kid-title">Petite pause !</h1>'),
    el(`<p class="kid-sub">Demande à papa ou maman.<br>${when ? "On pourra réessayer à " + when + "." : ""}</p>`),
    el('<p class="hint">💌 Un message a été envoyé aux parents.</p>'),
    el('<a class="tiny-link" href="parent.html">👨‍👩‍👧 Espace Parents</a>')
  );
}
function screenDailyLimit() {
  stopTimers(); clearChips();
  show(
    el('<div class="kid-logo">🌙</div>'),
    el('<h1 class="kid-title">Tu as bien joué !</h1>'),
    el('<p class="kid-sub">C\'est assez pour aujourd\'hui.<br>On retourne jouer dehors ! 🌳</p>'),
    el('<p class="hint">À demain pour de nouvelles aventures !</p>')
  );
  speak("Tu as bien joué Jade ! C'est assez pour aujourd'hui. À demain !");
}
function screenError(msg) {
  stopTimers(); clearChips();
  show(el('<div class="kid-logo">🧸</div>'), el('<h1 class="kid-title">Oups !</h1>'), el(`<p class="kid-sub">${msg}</p>`),
    (() => { const b = el('<button class="btn-soft">↩ Recommencer</button>'); b.onclick = screenWelcome; return b; })());
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
    el('<h1 class="kid-title">C\'est l\'heure de la pause !</h1>'),
    el('<p class="kid-sub">Tu as bien travaillé Jade !<br>Maintenant on bouge, on joue dehors ! 🌳⚽</p>')
  );
  speak("C'est l'heure de la pause Jade ! Bravo pour aujourd'hui !");
}

/* ---------------- ÉCRAN 3 : Leçon du jour (étape par étape) ---------------- */
async function screenGame() {
  if (!state.token) return screenWelcome();
  let step;
  try { step = await api("/api/learning/step?token=" + encodeURIComponent(state.token)); }
  catch (e) {
    if (e.status === 403 && e.body.detail && e.body.detail.reason === "veto") return screenPauseVeto();
    return screenWelcome();
  }
  if (step.mode === "done") return screenAllDone(step.progress);

  state.skill = step.skill; state.game = step.game;
  state.roundOk = 0; state.roundAttempts = 0; state.lastTarget = null; state.songPlayed = new Set();
  renderGameFrame(step.mode);
}
function gameHeader(mode) {
  const wrap = el('<div style="display:flex; flex-direction:column; align-items:center; gap:8px; width:100%"></div>');
  wrap.appendChild(el(`<span class="chip-tag">${mode === "review" ? "🔁 Révision" : "✨ Nouvelle leçon"} · ${state.skill.emoji} ${state.skill.label}</span>`));
  const bar = el(`<div class="mastery-bar"><div class="mastery-fill" style="width:${Math.round(state.skill.mastery * 100)}%"></div></div>`);
  wrap.appendChild(bar);
  const quit = el('<button class="quiet-quit">⏹ Fin</button>');
  quit.onclick = async () => { try { await api("/api/session/end", { method: "POST", body: { token: state.token } }); } catch (e) {} screenWelcome(); };
  if (!document.querySelector(".quiet-quit")) document.body.appendChild(quit);
  return wrap;
}
function renderGameFrame(mode) {
  const g = state.game;
  if (g.type === "tap") return renderTapRound(mode);
  if (g.type === "count") return renderCountRound(mode);
  if (g.type === "song") return renderSong(mode);
  screenGame();
}
function pickTarget(items) {
  let t;
  do { t = items[Math.floor(Math.random() * items.length)]; } while (state.lastTarget && t.id === state.lastTarget && items.length > 1);
  state.lastTarget = t.id;
  return t;
}
async function outcome(success) {
  try { await api("/api/learning/outcome", { method: "POST", body: { token: state.token, skill_id: state.skill.id, success } }); } catch (e) {}
}
function afterRound() {
  const g = state.game;
  const goal = g.rounds || 3;
  if (state.roundOk >= goal) { confetti(); setTimeout(screenGame, 900); return; }
  if (state.roundAttempts >= goal + 4) { setTimeout(screenGame, 400); return; } // on avance sans frustrer
  renderGameFrame(state.skill && "new");
}
function renderTapRound(mode) {
  const g = state.game, target = pickTarget(g.items);
  const instruction = g.instruction_tpl.replace("{label}", target.label).replace("{emoji}", target.emoji);
  show(gameHeader(mode), el(`<div class="q-text">${instruction}</div>`));
  speak(instruction);
  const grid = el('<div class="grid-options"></div>');
  shuffle(g.items).forEach((o) => {
    const b = el(`<button class="opt"><span class="oe">${o.emoji}</span><span class="ol">${o.label}</span></button>`);
    b.onclick = async () => {
      state.roundAttempts += 1;
      if (o.id === target.id) {
        state.roundOk += 1; confetti();
        speak("Bravo !");
        await outcome(true);
        afterRound();
      } else {
        b.classList.add("shake"); setTimeout(() => b.classList.remove("shake"), 500);
        speak("Essaie encore !");
        await outcome(false);
      }
    };
    grid.appendChild(b);
  });
  app.appendChild(grid);
}
function renderCountRound(mode) {
  const g = state.game;
  let n;
  do { n = g.min + Math.floor(Math.random() * (g.max - g.min + 1)); } while (state.lastTarget === n);
  state.lastTarget = n;
  const objs = g.object_emoji.repeat(n).split("").join(" ");
  show(
    gameHeader(mode),
    el('<div class="q-text">Combien tu en vois ? Compte avec moi !</div>'),
    el(`<div class="count-objs">${objs}</div>`)
  );
  speak("Compte avec moi ! Combien tu en vois ?");
  const grid = el('<div class="grid-options"></div>');
  for (let v = g.min; v <= g.max; v++) {
    const b = el(`<button class="opt"><span class="oe" style="font-size:44px">${v}</span></button>`);
    b.onclick = async () => {
      state.roundAttempts += 1;
      if (v === n) { state.roundOk += 1; confetti(); speak("Oui, " + n + " ! Bravo !"); await outcome(true); afterRound(); }
      else { b.classList.add("shake"); setTimeout(() => b.classList.remove("shake"), 500); speak("Recompte doucement !"); await outcome(false); }
    };
    grid.appendChild(b);
  }
  app.appendChild(grid);
}
function renderSong(mode) {
  const g = state.game;
  const nodes = [gameHeader(mode), el(`<div class="q-text">🎵 ${g.title}</div>`), el('<p class="hint">Écoute chaque phrase, puis répète !</p>')];
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
      const b = el('<button class="btn-big" data-songdone="1">J\'ai tout écouté ! 🎵</button>');
      b.onclick = async () => { confetti(); speak("Quelle belle voix ! Bravo Jade !"); await outcome(true); screenGame(); };
      app.appendChild(b);
      speak("Bravo ! Tu as écouté toute la comptine !");
    }
  }
}
function screenAllDone(progress) {
  show(
    el('<div class="kid-logo">🏆</div>'),
    el('<h1 class="kid-title">Bravo Jade !</h1>'),
    el(`<p class="kid-sub">Tu as tout appris pour le moment !<br>${progress.mastered} / ${progress.total} compétences maîtrisées (${progress.pct} %)</p>`),
    el('<p class="hint">Reviens demain : il y aura des révisions et des surprises ! ⭐</p>'),
    (() => { const b = el('<button class="btn-soft">⏹ Finir la session</button>'); b.onclick = async () => { try { await api("/api/session/end", { method: "POST", body: { token: state.token } }); } catch (e) {} screenWelcome(); }; return b; })()
  );
  confetti(); speak("Bravo Jade ! Tu es une vraie championne !");
}

/* ---------------- go ---------------- */
if (window.speechSynthesis) speechSynthesis.getVoices();
screenWelcome();
