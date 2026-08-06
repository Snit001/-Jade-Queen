"use strict";
/* Jade Bɔngɔ́ — Command Center « Mission Jade » (rafraîchissement 5 s) */

const $ = (s) => document.querySelector(s);
let token = sessionStorage.getItem("jb_ptoken") || null;
let refresher = null;

function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function fmtDur(s) { const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60; return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`; }
function fmtTs(ts) { return ts ? new Date(ts).toLocaleTimeString("fr-FR") : "—"; }

async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: { ...(opts.body ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { const e = new Error("http"); e.status = res.status; e.body = data; throw e; }
  return data;
}
function logout() { sessionStorage.removeItem("jb_ptoken"); token = null; clearInterval(refresher); location.reload(); }

$("#loginBtn").onclick = async () => {
  $("#loginErr").textContent = "";
  try {
    const r = await fetch("/api/parent/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pin: $("#pin").value }) });
    if (!r.ok) throw new Error("bad");
    const data = await r.json();
    token = data.token; sessionStorage.setItem("jb_ptoken", token);
    boot();
  } catch (e) { $("#loginErr").textContent = "Code incorrect."; }
};
$("#pin").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#loginBtn").click(); });

function boot() {
  $("#login").style.display = "none";
  $("#cmd").style.display = "block";
  $("#logoutBtn").onclick = logout;
  tick();
  refresher = setInterval(tick, 5000);
}

const EVENT_ICONS = {
  "identity.challenge_created": "🎫", "identity.answer_ok": "✅", "identity.answer_failed": "❌",
  "identity.succeeded": "🎉", "identity.locked": "🔒", "identity.unlocked": "🔓",
  "identity.challenge_refused_locked": "🚫",
};

async function tick() {
  let m;
  try { m = await api("/api/command/mission"); } catch (e) { if (e.status === 401) logout(); return; }
  $("#uptime").textContent = "uptime " + fmtDur(m.uptime_seconds);

  const k = m.kpi;
  $("#kpis").innerHTML = "";
  const tiles = [
    { v: k.age_display, l: "Âge exact" },
    { v: k.phase, l: k.phase_label },
    { v: k.progress_pct + " %", l: `Progression (${k.mastered}/${k.skills_total})` },
    { v: `${k.today_sessions}/${k.sessions_cap}`, l: "Sessions aujourd'hui" },
    { v: k.today_minutes + " min", l: "Temps d'écran" },
    { v: k.locked ? "🔒" : "✅", l: k.locked ? `Verrouillé (${k.lock_failures} échecs)` : "Accès libre" },
    { v: m.wellbeing.veto_total, l: "Vetos bien-être" },
  ];
  tiles.forEach((t) => $("#kpis").appendChild(el(`<div class="kpi"><div class="v">${t.v}</div><div class="l">${esc(t.l)}</div></div>`)));

  const sb = $("#cc-skills .body"); sb.innerHTML = "";
  m.skills.forEach((s) => {
    sb.appendChild(el(`<div style="padding:6px 0">
      <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px">
        <span>${s.emoji} ${esc(s.label)}</span><span style="color:#94a3b8">${s.mastered ? "✅ maîtrisé" : Math.round(s.mastery * 100) + " %"}</span>
      </div>
      <div class="pbar dark"><div class="pfill" style="width:${Math.round(s.mastery * 100)}%"></div></div>
    </div>`));
  });

  const ib = $("#cc-identity .body"); ib.innerHTML = "";
  if (m.identity_events.length === 0) ib.appendChild(el('<p style="color:#64748b;font-size:13px">Aucun événement pour le moment.</p>'));
  const table = el('<table class="cmd-table"><tbody></tbody></table>');
  m.identity_events.forEach((e) => {
    table.querySelector("tbody").appendChild(el(`<tr>
      <td>${EVENT_ICONS[e.type] || "•"}</td>
      <td class="mono" style="color:#94a3b8">${fmtTs(e.ts)}</td>
      <td style="font-size:12px">${esc(e.type)}</td>
      <td style="font-size:12px;color:#94a3b8">${esc(e.actor)}</td>
    </tr>`));
  });
  ib.appendChild(table);

  const vb = $("#cc-services .body"); vb.innerHTML = "";
  m.services.forEach((s) => vb.appendChild(el(`<div class="svc"><span class="dot"></span><b>${esc(s.name)}</b><span class="d">${esc(s.detail)}</span></div>`)));

  const wb = $("#cc-wellbeing .body"); wb.innerHTML = "";
  wb.appendChild(el(`<div>
    <div class="kv" style="border-color:var(--cmd-line)"><span>Durée max / session</span><b>${m.wellbeing.session_cap_minutes} min</b></div>
    <div class="kv" style="border-color:var(--cmd-line)"><span>Vetos appliqués</span><b>${m.wellbeing.veto_total}</b></div>
    <div class="kv" style="border-color:var(--cmd-line)"><span>Limites respectées</span><b>${m.wellbeing.limits_respected ? "✅ oui (100 %)" : "❌"}</b></div>
    <div class="kv" style="border-color:var(--cmd-line)"><span>Alertes non lues</span><b>${m.notifications.length}</b></div>
  </div>`));
}

if (token) boot();
