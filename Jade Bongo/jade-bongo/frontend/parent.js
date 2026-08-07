"use strict";
/* Jade Bɔngɔ́ — Espace Parents v2.0 : trilingue, évaluation initiale,
   réglages d'adaptation (langue / attention / soutien langage). */

const $ = (s) => document.querySelector(s);
let token = sessionStorage.getItem("jb_ptoken") || null;
let CHILD = null;
let CHILDREN = [];
let TREE = null;               // arbre complet (évaluation + badges)
const T = (k, v) => window.I18N.t("p." + k, v);

const CONSENT_LABELS = {
  education: { fr: "Éducation (autorise les leçons)", en: "Education (allows the lessons)", es: "Educación (autoriza las lecciones)" },
  stockage_donnees: { fr: "Stockage des données de progression", en: "Storage of progress data", es: "Almacenamiento de datos de progreso" },
  voix_audio: { fr: "Utilisation de la voix (STT/TTS navigateur)", en: "Voice use (browser STT/TTS)", es: "Uso de la voz (STT/TTS del navegador)" },
  rapports_parents: { fr: "Rapports et alertes parents", en: "Parent reports & alerts", es: "Informes y alertas para padres" },
};
const NOTIF_KEYS = {
  "identity.locked": "🔒 Accès verrouillé (échecs répétés)|🔒 Access locked (repeated failures)|🔒 Acceso bloqueado (fallos repetidos)",
  "wellbeing.veto": "⏱ Pause bien-être appliquée (veto)|⏱ Wellbeing break applied (veto)|⏱ Pausa de bienestar aplicada (veto)",
  "wellbeing.daily_limit": "🌙 Limite de sessions du jour atteinte|🌙 Daily session limit reached|🌙 Límite diario de sesiones alcanzado",
  "learning.milestone": "🏆 Jalon franchi|🏆 Milestone reached|🏆 Hito alcanzado",
  "learning.acceleration": "🚀 Accélération (compétence validée du premier coup)|🚀 Acceleration (skill mastered first try)|🚀 Aceleración (competencia validada a la primera)",
  "parent.child_created": "👶 Nouveau profil enfant|👶 New child profile|👶 Nuevo perfil de niño",
  "parent.child_deleted": "🗑 Profil enfant supprimé|🗑 Child profile deleted|🗑 Perfil de niño eliminado",
  "parent.evaluation": "📋 Évaluation initiale enregistrée|📋 Initial assessment saved|📋 Evaluación inicial guardada",
  "parent.child_updated": "⚙️ Réglages de l'enfant modifiés|⚙️ Child settings updated|⚙️ Ajustes del niño modificados",
};
function notifLabel(type) {
  const raw = NOTIF_KEYS[type];
  if (!raw) return type;
  const [fr, en, es] = raw.split("|");
  return { fr, en, es }[window.I18N.get()] || fr;
}

function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function fmtDate(ts) { return ts ? new Date(ts).toLocaleString(window.I18N.get(), { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"; }
function qs() { return CHILD ? "?child_id=" + encodeURIComponent(CHILD) : ""; }
function qsAnd() { return CHILD ? "&child_id=" + encodeURIComponent(CHILD) : ""; }

async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: { ...(opts.body ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 || (res.status === 403 && opts.authErr !== false)) { logout(); throw new Error("auth"); }
  if (!res.ok) { const e = new Error("http"); e.body = data; throw e; }
  return data;
}
function logout() { sessionStorage.removeItem("jb_ptoken"); token = null; location.reload(); }

/* ---------------- login ---------------- */
if ($("#loginBtn")) {
  $("#loginBtn").onclick = async () => {
    $("#loginErr").textContent = "";
    try {
      const r = await api("/api/parent/login", { method: "POST", body: { pin: $("#pin").value }, authErr: false });
      token = r.token; sessionStorage.setItem("jb_ptoken", token);
      boot();
    } catch (e) { $("#loginErr").textContent = T("login_err"); }
  };
  $("#pin").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#loginBtn").click(); });
}

/* ---------------- boot & enfants ---------------- */
async function boot() {
  $("#login").style.display = "none";
  $("#dash").style.display = "block";
  $("#refreshBtn").onclick = loadAll;
  $("#logoutBtn").onclick = logout;
  $("#readNotifBtn").onclick = async () => { await api("/api/parent/notifications/read", { method: "POST" }); loadAll(); };
  $("#unlockBtn").onclick = async () => { await api("/api/parent/unlock" + qs(), { method: "POST" }); loadAll(); };
  window.I18N.applyStatic($("#dash"));
  await loadChildren();
  buildSelector();
  await loadAll();
}

async function loadChildren() {
  CHILDREN = await api("/api/parent/children");
  if (CHILDREN.length && (!CHILD || !CHILDREN.find((c) => c.id === CHILD))) CHILD = CHILDREN[0].id;
}

function buildSelector() {
  const old = $("#childSel");
  if (old) old.remove();
  const sel = el('<select id="childSel" style="max-width:220px"></select>');
  CHILDREN.forEach((c) => {
    const o = el(`<option value="${esc(c.id)}">${c.emoji} ${esc(c.display_name)} · ${c.age_years} 🇫🇷${c.lang !== "fr" ? " · 🌍" + c.lang.toUpperCase() : ""}</option>`);
    if (c.id === CHILD) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = async () => { CHILD = sel.value; TREE = null; await loadAll(); };
  $(".topbar").insertBefore(sel, $(".topbar").children[1] || null);
}

/* ---------------- cartes ---------------- */
async function loadAll() {
  const ov = await api("/api/parent/overview" + qs() + "&lang=" + window.I18N.get());
  TREE = await api("/api/parent/tree" + qs() + "&lang=" + window.I18N.get());
  renderAge(ov);
  renderToday(ov);
  renderSettings(ov);
  await renderAssistant(ov);
  renderEval();
  renderMastery(ov);
  renderNotifs(ov);
  renderConsents(ov);
  renderChildren();
  await renderQuestions();
  await renderAudit();
}

/* 🧭 Assistant de démarrage interactif : les 5 étapes, cochées en direct,
   avec une action immédiate à chaque étape. */
async function renderAssistant(ov) {
  let card = $("#c-assist");
  if (!card) {
    card = el(`<div class="card" id="c-assist" style="grid-column:1/-1; border:2px solid #4f46e5"><h2>${T("assist")}</h2><div class="body"></div></div>`);
    $(".cards").insertBefore(card, $(".cards").firstChild);
  }
  const b = $("#c-assist .body"); b.innerHTML = "";

  const qsList = await api("/api/parent/questions" + qs());
  const activeQ = qsList.filter((q) => q.active).length;
  const customQ = qsList.filter((q) => q.active && !q.id.includes("default")).length;
  const mastered = TREE.counts.mastered;
  let sessionsDone = false;
  try {
    const evts = await api("/api/parent/audit?limit=1&type_prefix=session.started" + qsAnd());
    sessionsDone = evts.length > 0;
  } catch (e) {}

  const steps = [
    { done: CHILDREN.length >= 1, label: T("a_step1"), action: null },
    {
      done: true, label: T("a_step2"),
      action: () => {
        const sel = el(`<select style="max-width:190px"><option value="fr">🇫🇷 Français</option><option value="en">🇬🇧 English</option><option value="es">🇪🇸 Español</option></select>`);
        sel.value = (ov.child && ov.child.lang) || "fr";
        sel.onchange = async () => {
          await api(`/api/parent/children/${encodeURIComponent(CHILD)}`, { method: "PATCH", body: { lang: sel.value } });
          await loadChildren(); buildSelector(); loadAll();
        };
        return sel;
      },
    },
    { done: mastered > 0, label: T("a_step3", { n: mastered }), action: () => scrollBtn("#c-eval") },
    { done: activeQ >= 2 && customQ >= 1, label: T("a_step4", { n: activeQ }), action: () => scrollBtn("#c-questions") },
    { done: sessionsDone, label: T("a_step5"), action: null },
  ];

  const doneCount = steps.filter((s) => s.done).length;
  b.appendChild(el(`<div class="pbar" style="margin-bottom:12px"><div class="pfill" style="width:${Math.round(100 * doneCount / steps.length)}%"></div></div>`));
  steps.forEach((s, i) => {
    const row = el(`<div class="tree-row"><span style="font-size:18px">${s.done ? "✅" : "⬜"}</span>
      <span class="nm"><b>${i + 1}.</b> ${s.label}</span></div>`);
    if (s.action) row.appendChild(s.action());
    b.appendChild(row);
  });
  if (doneCount === steps.length) b.appendChild(el(`<p class="eval-flash">${T("a_ready")}</p>`));
  if (customQ === 0) b.appendChild(el(`<p style="font-size:12px;color:var(--warn);margin-top:6px">${T("a_default_q")}</p>`));

  function scrollBtn(sel) {
    const btn = el(`<button class="mini-btn">${T("a_open")}</button>`);
    btn.onclick = () => { const c = $(sel); if (c) c.scrollIntoView({ behavior: "smooth", block: "start" }); };
    return btn;
  }
}

function renderAge(ov) {
  const b = $("#c-age .body"); b.innerHTML = "";
  const a = ov.age;
  b.appendChild(el(`<div>
    <div class="kv"><span>${T("age_exact")}</span><b>${a.years} ans ${a.months} mois</b></div>
    <div class="kv"><span>${T("phase")}</span><b>${a.phase} — ${a.phase_label}</b></div>
  </div>`));
  b.appendChild(el(`<hr style="border:none;border-top:1px solid var(--line);margin:10px 0">`));
  b.appendChild(el(`<label class="f">${T("session_min")}</label>`));
  const inMin = el(`<input type="number" min="1" max="120" value="${ov.policy.session_max_minutes}">`);
  b.appendChild(el(`<label class="f">${T("sessions_day")}</label>`));
  const inSess = el(`<input type="number" min="1" max="10" value="${ov.policy.sessions_per_day_max}">`);
  b.appendChild(inMin); b.appendChild(inSess);
  const save = el(`<button class="btn" style="margin-top:10px">${T("save_policy")}</button>`);
  save.onclick = async () => {
    await api("/api/parent/policy" + qs(), { method: "PATCH", body: { session_max_minutes: +inMin.value, sessions_per_day_max: +inSess.value } });
    loadAll();
  };
  b.appendChild(save);
}

function renderToday(ov) {
  const b = $("#c-today .body"); b.innerHTML = "";
  const mins = (ov.today.screen_seconds / 60).toFixed(1);
  const lockBadge = ov.lock.locked
    ? `<span class="badge bad">${T("locked_until", { t: fmtDate(ov.lock.locked_until) })}</span>`
    : `<span class="badge ok">${T("free")}</span>`;
  b.appendChild(el(`<div>
    <div class="kv"><span>${T("screen_time")}</span><b>${mins} min</b></div>
    <div class="kv"><span>${T("sessions")}</span><b>${ov.today.sessions} / ${ov.today.sessions_cap}</b></div>
    <div class="kv"><span>${T("id_fails")}</span><b>${ov.lock.failed_count}</b></div>
    <div class="kv"><span>${T("access")}</span><b>${lockBadge}</b></div>
  </div>`));
}

/* 🌍 Réglages d'adaptation : langue des cours, attention, soutien langage */
function renderSettings(ov) {
  let card = $("#c-settings");
  if (!card) {
    card = el(`<div class="card" id="c-settings"><h2>${T("c_settings")}</h2><div class="body"></div></div>`);
    $(".cards").insertBefore(card, $(".cards").children[2] || null);
  }
  const b = $("#c-settings .body"); b.innerHTML = "";
  const c = ov.child || { lang: "fr", attention: "normal", speech_support: false };

  b.appendChild(el(`<label class="f">${T("lang_child")}</label>`));
  const selLang = el(`<select>
    <option value="fr">🇫🇷 Français</option>
    <option value="en">🇬🇧 English</option>
    <option value="es">🇪🇸 Español</option></select>`);
  selLang.value = c.lang;

  b.appendChild(el(`<label class="f">${T("attention")}</label>`));
  const selAtt = el(`<select>
    <option value="normal">${T("attnormal")}</option>
    <option value="courte">${T("attcourte")}</option></select>`);
  selAtt.value = c.attention;

  const chk = el(`<label class="switch" style="margin-top:10px"><input type="checkbox"> <span>🗣️ ${T("speech")}</span></label>`);
  chk.querySelector("input").checked = !!c.speech_support;

  const ok = el('<p class="eval-flash"></p>');
  const save = el(`<button class="btn" style="margin-top:12px">${T("save_settings")}</button>`);
  save.onclick = async () => {
    ok.textContent = "";
    await api(`/api/parent/children/${encodeURIComponent(CHILD)}`, {
      method: "PATCH",
      body: { lang: selLang.value, attention: selAtt.value, speech_support: chk.querySelector("input").checked },
    });
    ok.textContent = T("saved");
    await loadChildren(); buildSelector();
  };
  b.appendChild(selLang); b.appendChild(selAtt); b.appendChild(chk); b.appendChild(save); b.appendChild(ok);
}

/* 🚀 Évaluation initiale : « elle sait déjà ! » — arbre complet cochable */
function renderEval() {
  let card = $("#c-eval");
  if (!card) {
    card = el(`<div class="card" id="c-eval" style="grid-column:1/-1"><h2>${T("c_eval")}</h2><div class="body"></div></div>`);
    $(".cards").insertBefore(card, $(".cards").children[3] || null);
  }
  const b = $("#c-eval .body"); b.innerHTML = "";
  b.appendChild(el(`<p style="font-size:13px;color:var(--muted)">${T("eval_help")}</p>`));
  const flash = el('<p class="eval-flash"></p>');

  const wrap = el('<div class="scrollbox" style="max-height:none"></div>');
  TREE.domains.forEach((d) => {
    const sec = el(`<div class="tree-domain"><h3>${esc(d.domain_label)} (${d.skills.filter((s) => s.status === "mastered").length}/${d.skills.length})</h3></div>`);
    d.skills.forEach((s) => {
      const row = el(`<div class="tree-row">
        <span>${s.emoji}</span>
        <span class="nm"><b>${esc(s.label)}</b> <span class="lvl">niv. ${s.level}</span></span>
        <span class="badge ${s.status}">${{ mastered: "✅", unlocked: "▶", locked: "🔒" }[s.status]}</span>
      </div>`);
      const btn = el(`<button class="mini-btn ${s.status === "mastered" ? "grey" : ""}">${s.status === "mastered" ? "↺" : T("eval_knows")}</button>`);
      btn.title = s.status === "mastered" ? "reset" : "mastered";
      btn.onclick = async () => {
        btn.disabled = true;
        try {
          const action = s.status === "mastered" ? "reset" : "mastered";
          const r = await api("/api/parent/mastery" + qs(), { method: "POST", body: { skill_ids: [s.id], action } });
          const n = r.updated.length + r.auto.length;
          flash.textContent = T("eval_done", { n, auto: r.auto.length ? T("eval_auto", { a: r.auto.length }) : "" });
          await loadAll();
        } catch (e2) { btn.disabled = false; }
      };
      row.appendChild(btn);
      sec.appendChild(row);
    });
    wrap.appendChild(sec);
  });
  b.appendChild(wrap);
  b.appendChild(flash);
}

function renderMastery(ov) {
  const b = $("#c-mastery .body"); b.innerHTML = "";
  b.appendChild(el(`<div class="kv"><span>${T("global_progress")}</span><b>${ov.progress_pct} % (${ov.mastered_count}/${ov.skills_total})</b></div>`));
  const domains = [...new Set(ov.mastery.map((s) => s.domain_label))];
  const sel = el(`<select style="max-width:240px;margin-bottom:6px"><option value="">${T("filter_domain")}</option>${domains.map((d) => `<option>${esc(d)}</option>`).join("")}</select>`);
  const list = el("<div></div>");
  function draw(filter) {
    list.innerHTML = "";
    ov.mastery.filter((s) => !filter || s.domain_label === filter).forEach((s) => {
      list.appendChild(el(`<div style="padding:7px 0; border-bottom:1px dashed var(--line)">
        <div style="display:flex; justify-content:space-between; font-size:14px; margin-bottom:5px">
          <span>${s.emoji} <b>${esc(s.label)}</b> <span style="color:var(--muted)">(${esc(s.domain_label)})</span></span>
          <span>${{ mastered: "✅", unlocked: "▶", locked: "🔒" }[s.status] || ""} ${s.mastered ? "" : Math.round(s.mastery * 100) + " %"}</span>
        </div>
        <div class="pbar"><div class="pfill" style="width:${Math.round(s.mastery * 100)}%"></div></div>
        <div style="font-size:12px;color:var(--muted);margin-top:3px">${T("series_review", { s: s.streak, d: fmtDate(s.next_review_at) })}</div>
      </div>`));
    });
  }
  sel.onchange = () => draw(sel.value);
  draw("");
  b.appendChild(sel); b.appendChild(list);
}

function renderNotifs(ov) {
  const b = $("#c-notif .body"); b.innerHTML = "";
  b.appendChild(el(`<div class="kv"><span>${T("unread")}</span><b>${ov.notifications_unread}</b></div>`));
  const evts = ov.audit_tail.filter((e) => NOTIF_KEYS[e.type]).slice(0, 8);
  if (evts.length === 0) b.appendChild(el(`<p style="color:var(--muted);font-size:13px">${T("no_alert")}</p>`));
  evts.forEach((e) => b.appendChild(el(`<div class="kv"><span>${notifLabel(e.type)}</span><b>${fmtDate(e.ts)}</b></div>`)));
}

function renderConsents(ov) {
  const b = $("#c-consents .body"); b.innerHTML = "";
  ov.consents.forEach((c) => {
    const lbl = CONSENT_LABELS[c.scope];
    const txt = lbl ? (lbl[window.I18N.get()] || lbl.fr) : c.scope;
    const row = el(`<label class="switch"><input type="checkbox" ${c.granted ? "checked" : ""}> <span>${esc(txt)} <span style="color:var(--muted)">v${c.version}</span></span></label>`);
    row.querySelector("input").onchange = async (e) => {
      await api("/api/parent/consents", { method: "POST", body: { scope: c.scope, granted: e.target.checked } });
      loadAll();
    };
    b.appendChild(row);
  });
  b.appendChild(el(`<p style="font-size:12px;color:var(--muted);margin-top:8px">${T("consent_note")}</p>`));
}

function renderChildren() {
  let card = $("#c-children");
  if (!card) {
    card = el(`<div class="card" id="c-children"><h2>${T("c_children")}</h2><div class="body"></div></div>`);
    $(".cards").insertBefore(card, $(".cards").children[2] || null);
  }
  const b = $("#c-children .body"); b.innerHTML = "";
  const flash = el('<p class="eval-flash"></p>');
  CHILDREN.forEach((c) => {
    const row = el(`<div class="tree-row"><span>${c.emoji}</span>
      <span class="nm"><b>${esc(c.display_name)}</b></span>
      <span style="font-size:12px;color:var(--muted)">${c.age_years} ans · ${c.phase} · 🌍${c.lang.toUpperCase()}${c.attention === "courte" ? " · ⚡" : ""}${c.speech_support ? " · 🗣️" : ""}</span></div>`);
    // 🗑 Suppression de profil (garde-fou : jamais le dernier)
    if (CHILDREN.length > 1) {
      const del = el(`<button class="mini-btn" style="background:var(--bad)">${T("del_child")}</button>`);
      del.onclick = async () => {
        if (!window.confirm(T("del_confirm", { n: c.display_name }))) return;
        del.disabled = true;
        try {
          const r = await api(`/api/parent/children/${encodeURIComponent(c.id)}`, { method: "DELETE" });
          flash.textContent = T("del_done", { n: r.display_name });
          if (CHILD === c.id) CHILD = null;
          await loadChildren(); buildSelector(); await loadAll();
        } catch (e2) {
          del.disabled = false;
          window.alert((e2.body && e2.body.detail) || T("check_fields"));
        }
      };
      row.appendChild(del);
    }
    row.addEventListener("click", async (ev) => {
      if (ev.target.closest("button")) return;
      CHILD = c.id; buildSelector(); TREE = null; await loadAll();
    });
    row.style.cursor = "pointer";
    b.appendChild(row);
  });
  b.appendChild(flash);
  b.appendChild(el(`<h2 style="margin-top:14px">${T("add_child")}</h2>`));
  const fName = el(`<input placeholder="${esc(T("firstname"))}" maxlength="40">`);
  const fDob = el('<input type="date" max="' + new Date().toISOString().slice(0, 10) + '">');
  const fEmoji = el('<input placeholder="🦊" maxlength="4">');
  const fLang = el(`<select><option value="fr">🇫🇷 Français</option><option value="en">🇬🇧 English</option><option value="es">🇪🇸 Español</option></select>`);
  const err = el('<p style="color:var(--bad);font-size:13px;margin-top:6px"></p>');
  const ok = el('<p class="eval-flash"></p>');
  b.appendChild(el(`<label class="f">${T("firstname")}</label>`)); b.appendChild(fName);
  b.appendChild(el(`<label class="f">${T("dob")}</label>`)); b.appendChild(fDob);
  b.appendChild(el(`<label class="f">${T("emoji")}</label>`)); b.appendChild(fEmoji);
  b.appendChild(el(`<label class="f">${T("lang_child")}</label>`)); b.appendChild(fLang);
  const add = el(`<button class="btn" style="margin-top:10px">${T("create_profile")}</button>`);
  add.onclick = async () => {
    err.textContent = ""; ok.textContent = "";
    try {
      const r = await api("/api/parent/children", { method: "POST", body: { display_name: fName.value, dob: fDob.value, emoji: fEmoji.value || "⭐", lang: fLang.value } });
      ok.textContent = T("profile_created", { n: r.display_name, e: r.emoji });
      await loadChildren(); buildSelector(); CHILD = r.id; buildSelector(); await loadAll();
    } catch (e2) { err.textContent = (e2.body && e2.body.detail) || T("check_fields"); }
  };
  b.appendChild(add); b.appendChild(ok); b.appendChild(err);
}

async function renderQuestions() {
  const b = $("#c-questions .body"); b.innerHTML = "";
  const qsList = await api("/api/parent/questions" + qs());
  const table = el(`<table><thead><tr><th></th><th>❓</th><th></th><th>✓</th></tr></thead><tbody></tbody></table>`);
  qsList.forEach((q) => {
    const tr = el(`<tr>
      <td>${q.prompt.emoji || "🔐"}</td>
      <td>${esc(q.prompt.text)}</td>
      <td>${q.modality === "voice" ? T("q_modality_voice") : T("q_modality_image")}</td>
      <td><input type="checkbox" ${q.active ? "checked" : ""}></td>
    </tr>`);
    tr.querySelector("input").onchange = async (e) => {
      await api(`/api/parent/questions/${q.id}` + qs(), { method: "PATCH", body: { active: e.target.checked } });
    };
    table.querySelector("tbody").appendChild(tr);
  });
  b.appendChild(el(`<div class="kv"><span>${T("q_active")}</span><b>${qsList.filter((q) => q.active).length}</b></div>`));
  b.appendChild(table);

  b.appendChild(el(`<h2 style="margin-top:16px">${T("q_add")}</h2>`));
  const fText = el(`<input placeholder="${esc(T("q_text"))}">`);
  const fEmoji = el('<input placeholder="🧸" maxlength="4">');
  const fMod = el(`<select><option value="voice">${T("q_modality_voice")}</option><option value="image_tap">${T("q_modality_image")}</option></select>`);
  const fOpts = el(`<textarea rows="3" placeholder="${esc(T("q_options"))}\nchat|🐱|chat"></textarea>`);
  const fAns = el(`<textarea rows="2" placeholder="${esc(T("q_answers"))}"></textarea>`);
  b.appendChild(fText); b.appendChild(fEmoji); b.appendChild(fMod); b.appendChild(fOpts); b.appendChild(fAns);
  const add = el(`<button class="btn" style="margin-top:10px">${T("q_add_btn")}</button>`);
  const err = el('<p style="color:var(--bad);font-size:13px;margin-top:6px"></p>');
  add.onclick = async () => {
    err.textContent = "";
    const options = fOpts.value.trim()
      ? fOpts.value.trim().split("\n").map((l) => { const [id, emoji, label] = l.split("|").map((x) => (x || "").trim()); return { id, emoji, label }; })
      : null;
    try {
      await api("/api/parent/questions" + qs(), {
        method: "POST",
        body: { modality: fMod.value, text: fText.value, emoji: fEmoji.value || "🔐", options, accepted_answers: fAns.value.split("\n").map((s) => s.trim()).filter(Boolean) },
      });
      renderQuestions();
    } catch (e2) { err.textContent = (e2.body && e2.body.detail) || T("check_fields"); }
  };
  b.appendChild(add); b.appendChild(err);
}

async function renderAudit(typePrefix) {
  const b = $("#c-audit .body"); b.innerHTML = "";
  const sel = el(`<select style="max-width:260px">
    <option value="">${T("all_events")}</option>
    <option value="identity">${T("ev_identity")}</option>
    <option value="learning">${T("ev_learning")}</option>
    <option value="wellbeing">${T("ev_wellbeing")}</option>
    <option value="session">${T("ev_session")}</option>
    <option value="parent">${T("ev_parent")}</option>
    <option value="rgpd">${T("ev_gdpr")}</option>
  </select>`);
  sel.value = typePrefix || "";
  sel.onchange = () => renderAudit(sel.value || null);
  b.appendChild(sel);
  const events = await api("/api/parent/audit?limit=80" + (typePrefix ? `&type_prefix=${encodeURIComponent(typePrefix)}` : ""));
  const table = el(`<table style="margin-top:10px"><thead><tr><th>🕒</th><th></th><th></th><th></th></tr></thead><tbody></tbody></table>`);
  events.forEach((e) => {
    table.querySelector("tbody").appendChild(el(`<tr>
      <td class="mono">${fmtDate(e.ts)}</td>
      <td>${esc(e.actor)}</td>
      <td><span class="badge ${e.type.startsWith("identity") ? "warn" : e.type.startsWith("wellbeing") ? "bad" : "ok"}">${esc(e.type)}</span></td>
      <td class="mono">${esc(JSON.stringify(e.payload)).slice(0, 90)}</td>
    </tr>`));
  });
  b.appendChild(table);
}

/* go */
if (token) boot();
