/* OMNI-RESEARCH 100 — interface réelle.
   Toutes les données affichées proviennent de l'API. Aucune donnée fictive,
   aucun bouton décoratif, aucune insertion HTML de contenu non fiable. */
'use strict';

const MODES = ['fast', 'deep', 'maximum'];
const MODE_LABELS = { fast: 'FAST', deep: 'DEEP', maximum: 'MAXIMUM' };
const TERMINAL = new Set(['completed', 'failed', 'cancelled', 'insufficient_evidence']);

const state = {
  token: localStorage.getItem('or100_token') || '',
  role: localStorage.getItem('or100_role') || '',
  missionId: localStorage.getItem('or100_mission') || '',
  mode: 'fast',
  modes: {},
  pollTimer: null,
  reportMarkdown: '',
  reportName: 'rapport-or100.md',
  eventAbort: null,
  providerTestResult: null, // { name, text } conservé across le re-rendu
};

const $ = (id) => document.getElementById(id);

function el(tag, text, attrs) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'href') node.href = v;
    else if (k === 'onClick') node.addEventListener('click', v);
    else node.setAttribute(k, String(v));
  }
  return node;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

async function api(path, options) {
  const opts = options || {};
  const headers = Object.assign({}, opts.headers || {});
  if (opts.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
  const response = await fetch(path, {
    method: opts.method || 'GET',
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let payload = null;
  const ctype = response.headers.get('content-type') || '';
  if (ctype.includes('json')) {
    try { payload = await response.json(); } catch (_) { payload = null; }
  } else {
    payload = await response.text();
  }
  if (!response.ok) {
    const message = payload && payload.message ? payload.message
      : (typeof payload === 'string' ? payload : 'Erreur HTTP ' + response.status);
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

function showError(node, error) {
  node.textContent = error && error.message ? error.message : String(error);
}

function setRole(text, ok) {
  const badge = $('role-badge');
  badge.textContent = text;
  badge.className = 'badge' + (ok ? ' ok' : '');
}

function showApp(show) {
  $('app').hidden = !show;
  $('login-panel').hidden = show;
}

async function loadHealth() {
  try {
    const h = await api('/api/health');
    $('health-line').textContent = 'Backend ' + h.status + ' · base ' +
      (h.database ? 'OK' : 'HS') + ' · ' + h.agents + ' agents · ' +
      h.providers_configured.length + ' fournisseur(s) configuré(s)';
    $('footer-status').textContent = h.default_secret_in_use
      ? '⚠ secret JWT par défaut — à changer' : 'secret JWT personnalisé';
  } catch (e) {
    $('health-line').textContent = 'Backend inaccessible : ' + e.message;
  }
}

async function loadModes() {
  try {
    const data = await api('/api/settings');
    state.modes = data.modes || {};
    renderModes();
  } catch (e) {
    $('mode-detail').textContent = 'Modes indisponibles : ' + e.message;
    $('btn-launch').disabled = true;
  }
}

function renderModes() {
  const grid = $('mode-grid');
  clear(grid);
  MODES.forEach((mode) => {
    const info = state.modes[mode];
    const card = el('div', null, { class: 'mode-card' + (state.mode === mode ? ' selected' : ''), role: 'radio' });
    card.appendChild(el('strong', MODE_LABELS[mode]));
    card.appendChild(el('span', info ? info.description : 'Description indisponible'));
    card.addEventListener('click', () => { state.mode = mode; renderModes(); });
    grid.appendChild(card);
  });
  const info = state.modes[state.mode];
  if (info) {
    $('mode-detail').textContent = info.agents_planned + ' agents planifiés · ' +
      info.max_simultaneous_agents + ' simultanés au maximum · ' + info.waves +
      ' vague(s) · ' + info.providers_targeted + ' fournisseur(s) · ' +
      info.max_sources + ' sources max. · ' + info.verification_passes +
      ' passe(s) de vérification · contradictions : ' +
      (info.contradiction_analysis ? 'oui' : 'non');
  }
}

function activateTab(name) {
  document.querySelectorAll('.tab').forEach((t) =>
    t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach((p) =>
    p.classList.toggle('active', p.id === 'tab-' + name));
  const loaders = {
    mission: loadMission, sources: loadSources,
    contradictions: loadContradictions, report: loadReport,
    history: loadHistory, providers: loadProviders, settings: loadSettings,
    search: loadQuickStatus,
  };
  if (loaders[name]) loaders[name]();
}

function requireMission() {
  if (!state.missionId) return null;
  return state.missionId;
}

function missionPath(suffix) {
  return '/api/missions/' + encodeURIComponent(state.missionId) + suffix;
}

async function launch(event) {
  event.preventDefault();
  const errorNode = $('launch-error');
  errorNode.textContent = '';
  const query = $('query').value.trim();
  if (query.length < 3) { errorNode.textContent = 'Question trop courte.'; return; }
  const body = {
    query,
    mode: state.mode,
    language: $('language').value,
    max_sources: Number($('max-sources').value) || undefined,
  };
  $('btn-launch').disabled = true;
  try {
    const result = await api('/api/missions', { method: 'POST', body });
    state.missionId = result.mission_id;
    localStorage.setItem('or100_mission', state.missionId);
    errorNode.textContent = '';
    state.reportMarkdown = '';
    activateTab('mission');
    startPolling();
  } catch (e) {
    showError(errorNode, e);
    if (e.status === 401) { state.token = ''; showApp(false); }
  } finally {
    $('btn-launch').disabled = false;
  }
}

function startPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(() => {
    loadMission();
    loadQuickStatus();
  }, 1500);
  loadMission();
  loadQuickStatus();
  startEventStream();
}

/* Flux SSE réel (Authorization par en-tête, impossible avec EventSource). */
async function startEventStream() {
  if (state.eventAbort) state.eventAbort.abort();
  if (!state.missionId || !state.token) return;
  const controller = new AbortController();
  state.eventAbort = controller;
  try {
    const response = await fetch(missionPath('/events') + '?timeout=300', {
      headers: { Authorization: 'Bearer ' + state.token },
      signal: controller.signal,
    });
    if (!response.ok || !response.body) return;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';
      blocks.forEach((block) => {
        const line = block.split('\n').find((l) => l.indexOf('data: ') === 0);
        if (!line) return;
        try {
          const event = JSON.parse(line.slice(6));
          const list = $('event-list');
          const detail = event.payload && Object.keys(event.payload).length
            ? ' ' + JSON.stringify(event.payload).slice(0, 180) : '';
          list.appendChild(el('li', '[' + event.stage + '] ' + event.kind + detail));
          while (list.children.length > 120) list.removeChild(list.firstChild);
        } catch (_) { /* heartbeat ou frame ignorée */ }
      });
    }
  } catch (error) {
    if (error && error.name !== 'AbortError') {
      $('footer-status').textContent = 'Flux temps réel indisponible (repli sur polling)';
    }
  }
}

function maybeStopPolling(status) {
  if (TERMINAL.has(status) && state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
    loadReport();
    loadSources();
    loadContradictions();
  }
}

async function loadQuickStatus() {
  const node = $('quick-status');
  if (!requireMission()) { node.textContent = 'Aucune mission lancée.'; return; }
  try {
    const m = await api(missionPath(''));
    clear(node);
    node.appendChild(el('div', 'Mission ' + m.id));
    node.appendChild(el('div', 'État : ' + m.status + ' · étape : ' + m.stage +
      ' · progression : ' + Math.round((m.progress || 0) * 100) + ' %'));
    node.appendChild(el('div', 'Agents : ' + JSON.stringify(m.task_summary)));
  } catch (e) { node.textContent = 'Suivi indisponible : ' + e.message; }
}

async function loadMission() {
  const header = $('mission-header');
  if (!requireMission()) { header.textContent = 'Aucune mission sélectionnée.'; return; }
  try {
    const [m, agents] = await Promise.all([
      api(missionPath('')), api(missionPath('/agents')),
    ]);
    clear(header);
    header.appendChild(el('div', m.query, { class: 'mono' }));
    header.appendChild(el('div', m.id + ' · mode ' + m.mode + ' · état ' + m.status +
      ' · verdict ' + m.verdict + ' · étape ' + m.stage));
    $('progress-bar').style.width = Math.round((m.progress || 0) * 100) + '%';
    const summary = $('task-summary');
    clear(summary);
    const s = m.task_summary || {};
    [['total', s.total], ['ok', s.ok], ['actifs', s.running],
     ['en file', s.queued], ['échecs', s.failed]].forEach(([label, value]) => {
      summary.appendChild(el('span', label + ' : ' + (value === undefined ? 0 : value),
        { class: 'chip' }));
    });
    summary.appendChild(el('span', 'limite de concurrence : ' +
      (agents.max_parallel_agents || 0), { class: 'chip' }));
    const list = $('agent-list');
    clear(list);
    (agents.tasks || []).forEach((t) => {
      const card = el('div', null, { class: 'agent' });
      card.appendChild(el('span', t.status, {
        class: 'state ' + (t.status === 'ok' ? 'ok' : (t.status === 'failed' ? 'fail' : 'run')),
      }));
      card.appendChild(el('span', t.agent_id, { class: 'id' }));
      card.appendChild(el('div', t.division + ' · vague ' + t.wave +
        ' · ' + t.findings + ' résultat(s) · ' + Math.round(t.duration_ms) + ' ms'));
      if (t.error) card.appendChild(el('div', 'Erreur : ' + t.error, { class: 'error' }));
      list.appendChild(card);
    });
    const events = $('event-list');
    clear(events);
    (m.events || []).slice(-60).forEach((e) => {
      const detail = e.payload && Object.keys(e.payload).length
        ? ' ' + JSON.stringify(e.payload).slice(0, 220) : '';
      events.appendChild(el('li', '[' + e.stage + '] ' + e.kind + detail));
    });
    maybeStopPolling(m.status);
  } catch (e) { header.textContent = 'Suivi indisponible : ' + e.message; }
}

function renderTable(node, columns, rows, linkColumn) {
  clear(node);
  const table = el('table');
  const thead = el('thead');
  const headRow = el('tr');
  columns.forEach((c) => headRow.appendChild(el('th', c.label)));
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = el('tbody');
  rows.forEach((row) => {
    const tr = el('tr');
    columns.forEach((c) => {
      const td = el('td');
      const value = c.get(row);
      if (c.key === linkColumn && value) {
        const a = el('a', value, { href: value, target: '_blank', rel: 'noopener noreferrer' });
        td.appendChild(a);
      } else {
        td.textContent = value === undefined || value === null ? '—' : String(value);
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  node.appendChild(table);
  if (!rows.length) node.appendChild(el('p', 'Aucune donnée disponible pour cette mission.',
    { class: 'muted' }));
}

async function loadSources() {
  const node = $('source-list');
  if (!requireMission()) { clear(node); node.appendChild(el('p', 'Aucune mission sélectionnée.', { class: 'muted' })); return; }
  try {
    const data = await api(missionPath('/sources'));
    renderTable(node, [
      { key: 'url', label: 'URL', get: (r) => r.url },
      { key: 'title', label: 'Titre', get: (r) => (r.title || '').slice(0, 90) },
      { key: 'domain', label: 'Domaine', get: (r) => r.domain },
      { key: 'provider', label: 'Fournisseur', get: (r) => r.provider },
      { key: 'verified', label: 'Vérifiée', get: (r) => r.verified ? 'oui' : 'non' },
      { key: 'hash', label: 'Empreinte', get: (r) => (r.content_hash || '').slice(0, 12) },
      { key: 'flags', label: 'Injection neutralisée', get: (r) => (r.injection_flags || []).join(', ') || '—' },
    ], data.sources || [], 'url');
  } catch (e) { clear(node); node.appendChild(el('p', 'Sources indisponibles : ' + e.message, { class: 'error' })); }
}

async function loadContradictions() {
  const node = $('contradiction-list');
  if (!requireMission()) { clear(node); node.appendChild(el('p', 'Aucune mission sélectionnée.', { class: 'muted' })); return; }
  try {
    const data = await api(missionPath('/contradictions'));
    clear(node);
    (data.contradictions || []).forEach((c) => {
      const card = el('div', null, { class: 'card' });
      const head = el('div', null, { class: 'head' });
      head.appendChild(el('strong', c.resolution === 'resolved' ? 'Arbitrée' : 'Non tranchée'));
      head.appendChild(el('span', c.winner ? 'lot ' + c.winner : 'égalité', { class: 'muted' }));
      card.appendChild(head);
      card.appendChild(el('p', 'A : ' + c.statement_a));
      card.appendChild(el('p', 'B : ' + c.statement_b));
      card.appendChild(el('p', c.rationale, { class: 'muted' }));
      node.appendChild(card);
    });
    if (!data.count) node.appendChild(el('p', 'Aucune contradiction enregistrée.', { class: 'muted' }));
  } catch (e) { clear(node); node.appendChild(el('p', 'Indisponible : ' + e.message, { class: 'error' })); }
}

async function loadReport() {
  const meta = $('report-meta');
  const body = $('report-body');
  const citations = $('citation-list');
  if (!requireMission()) { meta.textContent = 'Aucun rapport.'; body.textContent = ''; clear(citations); return; }
  try {
    const data = await api(missionPath('/report'));
    if (!data.available) {
      meta.textContent = 'Rapport pas encore disponible (mission en cours).';
      body.textContent = '';
      clear(citations);
      return;
    }
    state.reportMarkdown = data.markdown || '';
    state.reportName = 'rapport-' + state.missionId + '.md';
    meta.textContent = 'Verdict ' + data.verdict + ' · ' + data.citation_count +
      ' citation(s) · généré le ' + new Date(data.created_at * 1000).toLocaleString();
    body.textContent = state.reportMarkdown; // jamais interprété comme du HTML
    clear(citations);
    (data.structured && data.structured.citations || []).forEach((c) => {
      const card = el('div', null, { class: 'card' });
      card.appendChild(el('strong', '[' + c.index + '] '));
      const a = el('a', c.title || c.url, {
        href: c.url, target: '_blank', rel: 'noopener noreferrer',
      });
      card.appendChild(a);
      card.appendChild(el('div', c.domain + ' · ' + c.provider +
        ' · vérifiée : ' + c.verified + ' · empreinte ' + (c.content_hash || '').slice(0, 12),
        { class: 'muted' }));
      citations.appendChild(card);
    });
  } catch (e) { meta.textContent = 'Rapport indisponible : ' + e.message; }
}

async function loadHistory() {
  const node = $('history-list');
  const cache = $('cache-list');
  try {
    const data = await api('/api/history');
    clear(node);
    (data.missions || []).forEach((m) => {
      const card = el('div', null, { class: 'card' });
      card.appendChild(el('div', m.query.slice(0, 160), { class: 'mono' }));
      card.appendChild(el('div', m.id + ' · ' + m.mode + ' · ' + m.status +
        ' · verdict ' + m.verdict + ' · ' + new Date(m.created_at * 1000).toLocaleString(),
        { class: 'muted' }));
      const btn = el('button', 'Ouvrir cette mission', { class: 'btn small', type: 'button' });
      btn.addEventListener('click', () => {
        state.missionId = m.id;
        localStorage.setItem('or100_mission', m.id);
        state.reportMarkdown = '';
        activateTab('mission');
        if (state.pollTimer) clearInterval(state.pollTimer);
        state.pollTimer = null;
        loadAllForMission();
        startEventStream();
      });
      card.appendChild(btn);
      node.appendChild(card);
    });
    if (!(data.missions || []).length) node.appendChild(el('p', 'Historique vide.', { class: 'muted' }));
    clear(cache);
    (data.reusable_researches || []).forEach((c) => {
      cache.appendChild(el('div', c.query.slice(0, 140) + ' · ' + c.hits + ' réutilisation(s)',
        { class: 'chip' }));
    });
    if (!(data.reusable_researches || []).length) cache.appendChild(el('p', 'Aucune recherche en cache.', { class: 'muted' }));
  } catch (e) { clear(node); node.appendChild(el('p', 'Historique indisponible : ' + e.message, { class: 'error' })); }
}

function loadAllForMission() {
  loadMission(); loadSources(); loadContradictions(); loadReport();
}

async function loadProviders() {
  const node = $('provider-list');
  const quota = $('quota-list');
  try {
    const [data, quotas] = await Promise.all([
      api('/api/providers'), api('/api/providers/quota'),
    ]);
    clear(node);
    (data.providers || []).forEach((p) => {
      const card = el('div', null, { class: 'card' });
      const head = el('div', null, { class: 'head' });
      head.appendChild(el('strong', p.label + ' (' + p.name + ')'));
      head.appendChild(el('span', p.status + (p.verified_live ? ' · appel réel vérifié' : ''),
        { class: 'chip ' + (p.status === 'cooldown' ? 'fail' : '') }));
      card.appendChild(head);
      card.appendChild(el('div', 'Forces : ' + (p.strengths || []).join(', ') +
        ' · extraction : ' + (p.supports_extract ? 'oui' : 'non') +
        ' · clé requise : ' + (p.requires_key ? 'oui' : 'non'), { class: 'muted' }));
      card.appendChild(el('div', 'Appels : ' + p.total_calls + ' · résultats : ' +
        p.total_results + ' · échecs consécutifs : ' + p.consecutive_failures +
        ' · dernière latence : ' + Math.round(p.last_latency_ms) + ' ms', { class: 'muted' }));
      if (p.last_error) card.appendChild(el('div', 'Dernière erreur : ' + p.last_error,
        { class: 'error' }));
      const row = el('div', null, { class: 'row' });
      const toggle = el('button',
        data.disabled.indexOf(p.name) >= 0 ? 'Activer' : 'Désactiver',
        { class: 'btn small', type: 'button' });
      toggle.addEventListener('click', async () => {
        const enable = data.disabled.indexOf(p.name) >= 0;
        toggle.disabled = true;
        try {
          await api('/api/providers/' + encodeURIComponent(p.name) + '?enabled=' +
            (enable ? 'true' : 'false'), { method: 'PATCH' });
          await loadProviders();
        } catch (e) { showError($('settings-error'), e); }
        toggle.disabled = false;
      });
      row.appendChild(toggle);
      const test = el('button', 'Tester réellement', { class: 'btn small', type: 'button' });
      const out = el('div', '', { class: 'muted' });
      // Le résultat survit au re-rendu de la liste (sinon le bouton ne montre rien).
      if (state.providerTestResult && state.providerTestResult.name === p.name) {
        out.textContent = state.providerTestResult.text;
      }
      test.addEventListener('click', async () => {
        test.disabled = true;
        out.textContent = 'Appel en cours…';
        let text = '';
        try {
          const r = await api('/api/providers/' + encodeURIComponent(p.name) + '/test', {
            method: 'POST', body: { query: 'open source intelligence' },
          });
          text = r.configured
            ? (r.sources.length + ' source(s) réelle(s) · résultats réels : ' +
               r.real_results + ' · ' + Math.round(r.elapsed_ms) + ' ms' +
               (r.errors.length ? ' · erreurs : ' + JSON.stringify(r.errors).slice(0, 180) : ''))
            : 'Non configuré : ' + r.message;
        } catch (e) { text = 'Test impossible : ' + e.message; }
        state.providerTestResult = { name: p.name, text: text };
        out.textContent = text;
        test.disabled = false;
        await loadProviders();
      });
      row.appendChild(test);
      card.appendChild(row);
      card.appendChild(out);
      node.appendChild(card);
    });
    clear(quota);
    Object.entries(quotas.quotas || {}).forEach(([name, q]) => {
      quota.appendChild(el('span', name + ' : ' + q.used + '/' +
        (q.limit > 0 ? q.limit : '∞') + ' (reste ' +
        (q.remaining < 0 ? 'illimité' : q.remaining) + ')', { class: 'chip' }));
    });
  } catch (e) { clear(node); node.appendChild(el('p', 'Fournisseurs indisponibles : ' + e.message, { class: 'error' })); }
}

async function loadSettings() {
  const errorNode = $('settings-error');
  errorNode.textContent = '';
  try {
    const data = await api('/api/settings');
    const s = data.settings || {};
    $('set-parallel').value = s.max_parallel_agents;
    $('set-concurrent').value = s.max_concurrent_missions;
    $('set-sources').value = s.max_sources_per_mission;
    $('set-rate').value = s.rate_limit_per_minute;
    $('set-retention').value = s.retention_days;
    $('settings-raw').textContent = JSON.stringify(s, null, 2);
  } catch (e) { showError(errorNode, e); }
}

async function saveSettings(event) {
  event.preventDefault();
  const errorNode = $('settings-error');
  errorNode.textContent = '';
  const body = {
    max_parallel_agents: Number($('set-parallel').value),
    max_concurrent_missions: Number($('set-concurrent').value),
    max_sources_per_mission: Number($('set-sources').value),
    rate_limit_per_minute: Number($('set-rate').value),
    retention_days: Number($('set-retention').value),
  };
  try {
    const result = await api('/api/settings', { method: 'PATCH', body });
    errorNode.textContent = 'Appliqué : ' + JSON.stringify(result.applied);
    await loadSettings();
    await loadModes();
  } catch (e) { showError(errorNode, e); }
}

async function login(event) {
  event.preventDefault();
  const errorNode = $('login-error');
  errorNode.textContent = '';
  try {
    const result = await api('/api/auth/login', {
      method: 'POST',
      body: { username: $('login-user').value, password: $('login-pass').value },
    });
    state.token = result.access_token;
    state.role = result.role;
    localStorage.setItem('or100_token', state.token);
    localStorage.setItem('or100_role', state.role);
    setRole(result.role + ' · connecté', true);
    showApp(true);
    await loadHealth();
    await loadModes();
    activateTab('search');
    if (state.missionId) loadQuickStatus();
  } catch (e) { showError(errorNode, e); }
}

function logout() {
  state.token = '';
  state.role = '';
  localStorage.removeItem('or100_token');
  localStorage.removeItem('or100_role');
  if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  if (state.eventAbort) { state.eventAbort.abort(); state.eventAbort = null; }
  setRole('non connecté', false);
  showApp(false);
}

function downloadReport() {
  if (!state.reportMarkdown) return;
  const blob = new Blob([state.reportMarkdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = el('a', '', { href: url });
  a.download = state.reportName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function wire() {
  $('login-form').addEventListener('submit', login);
  $('btn-logout').addEventListener('click', logout);
  $('mission-form').addEventListener('submit', launch);
  $('settings-form').addEventListener('submit', saveSettings);
  $('btn-download-report').addEventListener('click', downloadReport);
  $('btn-refresh-mission').addEventListener('click', loadMission);
  $('btn-refresh-history').addEventListener('click', loadHistory);
  $('btn-refresh-providers').addEventListener('click', loadProviders);
  document.querySelectorAll('.tab').forEach((tab) =>
    tab.addEventListener('click', () => activateTab(tab.dataset.tab)));
}

async function boot() {
  wire();
  await loadHealth();
  if (state.token) {
    setRole(state.role + ' · connecté', true);
    showApp(true);
    try {
      await loadModes();
      activateTab('search');
      if (state.missionId) loadQuickStatus();
    } catch (e) {
      showError($('launch-error'), e);
    }
  } else {
    showApp(false);
  }
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* mode dégradé */ });
  }
}

boot();
