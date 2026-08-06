"use strict";
/* Jade Bɔngɔ́ — Espace Parents : supervision, questions, politiques, audit. */

const $ = (s) => document.querySelector(s);
let token = sessionStorage.getItem("jb_ptoken") || null;

const CONSENT_LABELS = {
  education: "Éducation (autorise les leçons)",
  stockage_donnees: "Stockage des données de progression",
  voix_audio: "Utilisation de la voix (STT/TTS navigateur)",
  rapports_parents: "Rapports et alertes parents",
};
const NOTIF_LABELS = {
  "identity.locked": "🔒 Accès verrouillé (échecs répétés)",
  "wellbeing.veto": "⏱ Pause bien-être appliquée (veto)",
  "wellbeing.daily_limit": "🌙 Limite de sessions du jour atteinte",
  "learning.milestone": "🏆 Jalon franchi par Jade",
};

function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function fmtDate(ts) { return ts ? new Date(ts).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"; }

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
$("#loginBtn").onclick = async () => {
  $("#loginErr").textContent = "";
  try {
    const r = await api("/api/parent/login", { method: "POST", body: { pin: $("#pin").value }, authErr: false });
    token = r.token; sessionStorage.setItem("jb_ptoken", token);
    boot();
  } catch (e) { $("#loginErr").textContent = "Code incorrect. Réessayez."; }
};
$("#pin").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#loginBtn").click(); });

/* ---------------- dashboard ---------------- */
async function boot() {
  $("#login").style.display = "none";
  $("#dash").style.display = "block";
  $("#refreshBtn").onclick = loadAll;
  $("#logoutBtn").onclick = logout;
  $("#readNotifBtn").onclick = async () => { await api("/api/parent/notifications/read", { method: "POST" }); loadAll(); };
  $("#unlockBtn").onclick = async () => { await api("/api/parent/unlock", { method: "POST" }); loadAll(); };
  await loadAll();
}

async function loadAll() {
  const ov = await api("/api/parent/overview");
  renderAge(ov);
  renderToday(ov);
  renderMastery(ov);
  renderNotifs(ov);
  renderConsents(ov);
  await renderQuestions();
  await renderAudit();
}

/* Âge & phase + politique */
function renderAge(ov) {
  const b = $("#c-age .body"); b.innerHTML = "";
  const a = ov.age;
  b.appendChild(el(`<div>
    <div class="kv"><span>Âge exact</span><b>${a.years} ans ${a.months} mois</b></div>
    <div class="kv"><span>Phase</span><b>${a.phase} — ${a.phase_label}</b></div>
    <div class="kv"><span>Naissance</span><b>03/09/2022</b></div>
  </div>`));
  b.appendChild(el(`<hr style="border:none;border-top:1px solid var(--line);margin:10px 0">`));
  b.appendChild(el(`<div class="f">Durée max par session (min)</div>`));
  const inMin = el(`<input type="number" min="1" max="120" value="${ov.policy.session_max_minutes}">`);
  b.appendChild(el(`<div class="f">Sessions max par jour</div>`));
  const inSess = el(`<input type="number" min="1" max="10" value="${ov.policy.sessions_per_day_max}">`);
  b.appendChild(inMin); b.appendChild(inSess);
  const save = el('<button class="btn" style="margin-top:10px">💾 Enregistrer la politique</button>');
  save.onclick = async () => {
    await api("/api/parent/policy", { method: "PATCH", body: { session_max_minutes: +inMin.value, sessions_per_day_max: +inSess.value } });
    loadAll();
  };
  b.appendChild(save);
}

/* Aujourd'hui & bien-être */
function renderToday(ov) {
  const b = $("#c-today .body"); b.innerHTML = "";
  const mins = (ov.today.screen_seconds / 60).toFixed(1);
  const lockBadge = ov.lock.locked
    ? `<span class="badge bad">🔒 Verrouillé jusqu'à ${fmtDate(ov.lock.locked_until)}</span>`
    : `<span class="badge ok">✅ Accès libre</span>`;
  b.appendChild(el(`<div>
    <div class="kv"><span>Temps d'écran</span><b>${mins} min</b></div>
    <div class="kv"><span>Sessions</span><b>${ov.today.sessions} / ${ov.today.sessions_cap}</b></div>
    <div class="kv"><span>Échecs d'identification</span><b>${ov.lock.failed_count}</b></div>
    <div class="kv"><span>Statut d'accès</span><b>${lockBadge}</b></div>
  </div>`));
}

/* Compétences */
function renderMastery(ov) {
  const b = $("#c-mastery .body"); b.innerHTML = "";
  b.appendChild(el(`<div class="kv"><span>Progression globale</span><b>${ov.progress_pct} % (${ov.mastered_count}/${ov.skills_total})</b></div>`));
  ov.mastery.forEach((s) => {
    b.appendChild(el(`<div style="padding:7px 0; border-bottom:1px dashed var(--line)">
      <div style="display:flex; justify-content:space-between; font-size:14px; margin-bottom:5px">
        <span>${s.emoji} <b>${esc(s.label)}</b> <span style="color:var(--muted)">(${esc(s.domain)})</span></span>
        <span>${s.mastered ? "✅" : Math.round(s.mastery * 100) + " %"}</span>
      </div>
      <div class="pbar"><div class="pfill" style="width:${Math.round(s.mastery * 100)}%"></div></div>
      <div style="font-size:12px;color:var(--muted);margin-top:3px">série : ${s.streak} · prochaine révision : ${fmtDate(s.next_review_at)}</div>
    </div>`));
  });
}

/* Alertes */
function renderNotifs(ov) {
  const b = $("#c-notif .body"); b.innerHTML = "";
  const list = ov.audit_tail.filter(() => false); // placeholder；真正的未读在 overview.notifications_unread
  b.appendChild(el(`<div class="kv"><span>Alertes non lues</span><b>${ov.notifications_unread}</b></div>`));
  const evts = ov.audit_tail.filter((e) => ["identity.locked", "wellbeing.veto", "wellbeing.daily_limit", "learning.milestone"].includes(e.type)).slice(0, 8);
  if (evts.length === 0) b.appendChild(el('<p style="color:var(--muted);font-size:13px">Aucune alerte récente. Tout va bien 💛</p>'));
  evts.forEach((e) => b.appendChild(el(`<div class="kv"><span>${NOTIF_LABELS[e.type] || e.type}</span><b>${fmtDate(e.ts)}</b></div>`)));
}

/* Consentements */
function renderConsents(ov) {
  const b = $("#c-consents .body"); b.innerHTML = "";
  ov.consents.forEach((c) => {
    const row = el(`<label class="switch"><input type="checkbox" ${c.granted ? "checked" : ""}> <span>${esc(CONSENT_LABELS[c.scope] || c.scope)} <span style="color:var(--muted)">v${c.version}</span></span></label>`);
    row.querySelector("input").onchange = async (e) => {
      await api("/api/parent/consents", { method: "POST", body: { scope: c.scope, granted: e.target.checked } });
      loadAll();
    };
    b.appendChild(row);
  });
  b.appendChild(el('<p style="font-size:12px;color:var(--muted);margin-top:8px">Révoquer « Éducation » bloque immédiatement toute nouvelle session.</p>'));
}

/* Questions d'identification */
async function renderQuestions() {
  const b = $("#c-questions .body"); b.innerHTML = "";
  const qs = await api("/api/parent/questions");
  const table = el(`<table><thead><tr><th></th><th>Question</th><th>Modalité</th><th>Actif</th></tr></thead><tbody></tbody></table>`);
  qs.forEach((q) => {
    const tr = el(`<tr>
      <td>${q.prompt.emoji || "🔐"}</td>
      <td>${esc(q.prompt.text)}</td>
      <td>${q.modality === "voice" ? "🎤 voix" : "👆 image"}</td>
      <td><input type="checkbox" ${q.active ? "checked" : ""}></td>
    </tr>`);
    tr.querySelector("input").onchange = async (e) => {
      await api(`/api/parent/questions/${q.id}`, { method: "PATCH", body: { active: e.target.checked } });
    };
    table.querySelector("tbody").appendChild(tr);
  });
  b.appendChild(el(`<div class="kv"><span>Questions actives</span><b>${qs.filter((q) => q.active).length}</b></div>`));
  b.appendChild(table);

  b.appendChild(el('<h2 style="margin-top:16px">➕ Ajouter une question</h2>'));
  const fText = el('<input placeholder="Texte de la question (ex : Comment s\'appelle ton doudou ?)">');
  const fEmoji = el('<input placeholder="Emoji (ex : 🧸)" maxlength="4">');
  const fMod = el('<select><option value="voice">🎤 voix</option><option value="image_tap">👆 image</option></select>');
  const fOpts = el('<textarea rows="3" placeholder="Options (si image) — une par ligne : id|emoji|label\nchat|🐱|chat"></textarea>');
  const fAns = el('<textarea rows="2" placeholder="Réponses acceptées — une par ligne (variantes tolérées)\ndoudou\nmon doudou"></textarea>');
  b.appendChild(el('<label class="f">Question</label>')); b.appendChild(fText);
  b.appendChild(el('<label class="f">Emoji</label>')); b.appendChild(fEmoji);
  b.appendChild(el('<label class="f">Modalité</label>')); b.appendChild(fMod);
  b.appendChild(el('<label class="f">Options (image_tap)</label>')); b.appendChild(fOpts);
  b.appendChild(el('<label class="f">Réponses acceptées</label>')); b.appendChild(fAns);
  const add = el('<button class="btn" style="margin-top:10px">💾 Ajouter (hachées côté serveur)</button>');
  const err = el('<p style="color:var(--bad);font-size:13px;margin-top:6px"></p>');
  add.onclick = async () => {
    err.textContent = "";
    const options = fOpts.value.trim()
      ? fOpts.value.trim().split("\n").map((l) => { const [id, emoji, label] = l.split("|").map((x) => (x || "").trim()); return { id, emoji, label }; })
      : null;
    try {
      await api("/api/parent/questions", {
        method: "POST",
        body: { modality: fMod.value, text: fText.value, emoji: fEmoji.value || "🔐", options, accepted_answers: fAns.value.split("\n").map((s) => s.trim()).filter(Boolean) },
      });
      renderQuestions();
    } catch (e2) { err.textContent = (e2.body && e2.body.detail) || "Erreur : vérifiez les champs."; }
  };
  b.appendChild(add); b.appendChild(err);
}

/* Audit */
async function renderAudit(typePrefix) {
  const b = $("#c-audit .body"); b.innerHTML = "";
  const sel = el(`<select style="max-width:260px">
    <option value="">Tous les événements</option>
    <option value="identity">Identifications</option>
    <option value="learning">Apprentissage</option>
    <option value="wellbeing">Bien-être</option>
    <option value="session">Sessions</option>
    <option value="parent">Actions parents</option>
    <option value="rgpd">RGPD / consentements</option>
  </select>`);
  sel.value = typePrefix || "";
  sel.onchange = () => renderAudit(sel.value || null);
  b.appendChild(sel);
  const events = await api("/api/parent/audit?limit=80" + (typePrefix ? `&type_prefix=${encodeURIComponent(typePrefix)}` : ""));
  const table = el(`<table style="margin-top:10px"><thead><tr><th>Heure</th><th>Acteur</th><th>Événement</th><th>Détails</th></tr></thead><tbody></tbody></table>`);
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
