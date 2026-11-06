/* Tests DOM de l'interface RÉELLE (jsdom, hors production).
   Le JavaScript de app/web/app.js est exécuté dans un vrai DOM ; fetch est
   remplacé par des réponses de forme identique à celles de l'API. On vérifie
   le rendu effectif, le flux SSE authentifié, l'absence de données fictives et
   la non-interprétation HTML du contenu non fiable. */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const ROOT = path.resolve(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'app/web/index.html'), 'utf8');
const JS = fs.readFileSync(path.join(ROOT, 'app/web/app.js'), 'utf8');
const MID = 'mission-dom-0001';

const tick = (ms = 25) => new Promise((resolve) => setTimeout(resolve, ms));

function build() {
  const calls = [];
  const modes = {
    fast: { description: 'Rapide', agents_planned: 3, max_simultaneous_agents: 3,
            waves: 1, providers_targeted: 1, max_sources: 8,
            verification_passes: 1, contradiction_analysis: false },
    deep: { description: 'Approffondi', agents_planned: 16, max_simultaneous_agents: 8,
            waves: 3, providers_targeted: 3, max_sources: 24,
            verification_passes: 2, contradiction_analysis: true },
    maximum: { description: '100 agents', agents_planned: 100,
               max_simultaneous_agents: 8, waves: 4, providers_targeted: 5,
               max_sources: 60, verification_passes: 3, contradiction_analysis: true },
  };
  const settings = {
    settings: { max_parallel_agents: 8, max_concurrent_missions: 4,
      max_sources_per_mission: 60, rate_limit_per_minute: 60, retention_days: 90 },
    modes,
  };
  const mission = {
    id: MID, query: 'Versions de l API et étude 2025', mode: 'fast',
    status: 'completed', stage: 'completed', progress: 1, verdict: 'NEEDS_WORK',
    task_summary: { total: 3, ok: 3, running: 0, queued: 0, failed: 0 },
    events: [{ stage: 'searching', kind: 'search_ok', payload: { results: 8 } }],
  };
  const data = {
    '/api/health': { status: 'ok', database: true, agents: 100,
      providers_configured: [], default_secret_in_use: false },
    '/api/auth/login': { access_token: 'dom-token', role: 'admin', expires_in: 43200 },
    '/api/settings': settings,
    '/api/missions': { mission_id: MID, status: 'queued', mode: 'fast' },
    [`/api/missions/${MID}`]: mission,
    [`/api/missions/${MID}/agents`]: { max_parallel_agents: 8, tasks: [
      { agent_id: 'WEB-01', division: 'Web Intelligence', status: 'ok', wave: 0,
        findings: 4, duration_ms: 12.4, error: '' },
      { agent_id: 'TECH-03', division: 'Technology Intelligence', status: 'ok',
        wave: 0, findings: 3, duration_ms: 9.1, error: '' },
    ] },
    [`/api/missions/${MID}/sources`]: { sources: [
      { url: 'https://docs.example.org/api/v2', title: 'API v2 — notes',
        domain: 'docs.example.org', provider: 'fixture', verified: true,
        content_hash: 'abcdef1234567890', injection_flags: [] },
    ] },
    [`/api/missions/${MID}/contradictions`]: { count: 1, contradictions: [
      { resolution: 'unresolved', winner: '', statement_a: 'v2 publiée en 2024',
        statement_b: 'v2 publiée en 2025', rationale: 'Égalité parfaite : non tranchée' },
    ] },
    [`/api/missions/${MID}/report`]: {
      available: true, verdict: 'NEEDS_WORK', citation_count: 1, created_at: 1793740000,
      markdown: '# Rapport [S1]\n<script>alert(1)</script> : texte non fiable conservé.',
      structured: { citations: [
        { index: 1, title: 'API v2 — notes', url: 'https://docs.example.org/api/v2',
          domain: 'docs.example.org', provider: 'fixture', verified: true,
          content_hash: 'abcdef1234567890' },
      ] },
    },
    '/api/history': { missions: [mission], reusable_researches: [
      { query: 'Versions de l API', hits: 2 },
    ] },
    '/api/providers': { disabled: [], providers: [
      { name: 'tavily', label: 'Tavily', status: 'not_configured', verified_live: false,
        strengths: ['general'], supports_extract: false, requires_key: true,
        total_calls: 0, total_results: 0, consecutive_failures: 0,
        last_latency_ms: 0, last_error: '' },
    ] },
    '/api/providers/quota': { quotas: { tavily: { used: 0, limit: 100, remaining: 100 } } },
  };

  const response = (body, ok = true, status = 200) => ({
    ok, status,
    headers: { get: (name) => name.toLowerCase() === 'content-type'
      ? 'application/json' : null },
    json: async () => body,
    text: async () => JSON.stringify(body),
    body: null, // SSE : pas de flux dans ce test DOM ; le code replie sur le polling
  });

  const fetchStub = async (url, opts = {}) => {
    calls.push({ url, opts });
    const clean = url.split('?')[0];
    if (opts.method === 'POST' && clean === '/api/missions') return response(data['/api/missions']);
    if (opts.method === 'POST' && clean === '/api/auth/login') return response(data['/api/auth/login']);
    if (opts.method === 'PATCH' && clean === '/api/settings') {
      return response({ applied: opts.body });
    }
    if (opts.method === 'POST' && clean.endsWith('/test')) {
      return response({ configured: false, message: 'clé API absente',
        sources: [], real_results: 0, errors: [], elapsed_ms: 0 });
    }
    if (opts.method === 'PATCH' && clean.startsWith('/api/providers/')) {
      return response({ ok: true });
    }
    if (clean.endsWith('/events')) return response({ ok: true });
    if (Object.prototype.hasOwnProperty.call(data, clean)) return response(data[clean]);
    return response({ message: 'route inconnue ' + clean }, false, 404);
  };

  const dom = new JSDOM(HTML, {
    url: 'http://localhost:8000/', runScripts: 'outside-only',
    pretendToBeVisual: true,
  });
  const { window } = dom;
  window.fetch = fetchStub;
  window.TextDecoder = TextDecoder;
  window.AbortController = AbortController;
  window.eval(JS);
  return { dom, window, calls, data };
}

test('interface réelle exécutée dans un DOM : rendu, API, SSE et contenu non fiable', async (t) => {
  const { window, calls } = build();
  const doc = window.document;
  const $ = (id) => doc.getElementById(id);
  const clickTab = (name) => {
    const tab = [...doc.querySelectorAll('.tab')].find((x) => x.dataset.tab === name);
    assert.ok(tab, 'onglet ' + name + ' présent');
    tab.click();
  };

  await t.test(' santé et connexion utilisent les vraies routes', async () => {
    await tick();
    assert.match($('health-line').textContent, /Backend ok/);
    assert.match($('health-line').textContent, /100 agents/);
    $('login-user').value = 'admin';
    $('login-pass').value = 'motdepasse';
    $('login-form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    await tick(40);
    assert.equal($('app').hidden, false);
    assert.match($('role-badge').textContent, /admin/);
    const login = calls.find((c) => c.url === '/api/auth/login');
    assert.ok(login && login.opts.method === 'POST');
    assert.equal(JSON.parse(login.opts.body).username, 'admin');
  });

  await t.test(' les 3 modes affichent les ressources réelles du backend', async () => {
    assert.equal(doc.querySelectorAll('.mode-card').length, 3);
    const maximum = [...doc.querySelectorAll('.mode-card')][2];
    maximum.click();
    await tick();
    assert.match($('mode-detail').textContent, /100 agents planifiés/);
    assert.match($('mode-detail').textContent, /8 simultanés au maximum/);
  });

  await t.test(' lancer une mission appelle POST /api/missions et active le suivi', async () => {
    $('query').value = 'Versions de l API et étude 2025';
    $('mission-form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    await tick(60);
    assert.equal(window.localStorage.getItem('or100_mission'), MID);
    const created = calls.find((c) => c.url === '/api/missions' && c.opts.method === 'POST');
    assert.ok(created);
    assert.equal(JSON.parse(created.opts.body).mode, 'maximum');
    assert.match($('quick-status').textContent, new RegExp(MID));
    assert.ok(calls.some((c) => c.url.startsWith(`/api/missions/${MID}/events`)
      && c.opts.headers.Authorization === 'Bearer dom-token'),
      'SSE appelé avec en-tête Authorization');
  });

  await t.test(' onglet Mission : agents, vagues, événements et concurrence', async () => {
    clickTab('mission');
    await tick(50);
    assert.match($('mission-header').textContent, /Versions de l API/);
    assert.match($('agent-list').textContent, /WEB-01/);
    assert.match($('agent-list').textContent, /TECH-03/);
    assert.match($('task-summary').textContent, /limite de concurrence : 8/);
    assert.match($('event-list').textContent, /search_ok/);
  });

  await t.test(' onglet Sources : URL, empreinte et fournisseur réels', async () => {
    clickTab('sources');
    await tick(40);
    assert.match($('source-list').textContent, /docs\.example\.org/);
    assert.match($('source-list').textContent, /abcdef123456/);
    const link = $('source-list').querySelector('a');
    assert.equal(link.getAttribute('rel'), 'noopener noreferrer');
  });

  await t.test(' onglet Contradictions : égalité non tranchée', async () => {
    clickTab('contradictions');
    await tick(40);
    assert.match($('contradiction-list').textContent, /Non tranchée/);
    assert.match($('contradiction-list').textContent, /Égalité parfaite/);
  });

  await t.test(' onglet Rapport : markdown non interprété (anti-XSS) et citations', async () => {
    clickTab('report');
    await tick(40);
    assert.match($('report-meta').textContent, /NEEDS_WORK/);
    assert.equal($('report-body').querySelector('script'), null,
      'le contenu non fiable ne doit jamais devenir un élément HTML');
    assert.match($('report-body').textContent, /<script>alert\(1\)<\/script>/);
    assert.match($('citation-list').textContent, /API v2 — notes/);
  });

  await t.test(' Historique, Fournisseurs, Paramètres : données API uniquement', async () => {
    clickTab('history');
    await tick(40);
    assert.match($('history-list').textContent, /Versions de l API/);
    assert.match($('cache-list').textContent, /2 réutilisation/);
    clickTab('providers');
    await tick(40);
    assert.match($('provider-list').textContent, /Tavily/);
    assert.match($('provider-list').textContent, /not_configured/);
    assert.doesNotMatch($('provider-list').textContent, /appel réel vérifié/,
      'aucune vérification live ne doit être inventée');
    clickTab('settings');
    await tick(40);
    assert.match($('settings-raw').textContent, /"max_parallel_agents": 8/);
  });

  await t.test(' bouton « Tester réellement » : aucune source fictive', async () => {
    clickTab('providers');
    await tick(40);
    const button = [...$('provider-list').querySelectorAll('button')]
      .find((b) => b.textContent === 'Tester réellement');
    assert.ok(button, 'bouton de test réel présent');
    button.click();
    await tick(50);
    assert.match($('provider-list').textContent, /Non configuré : clé API absente/);
    assert.doesNotMatch($('provider-list').textContent, /[1-9][0-9]* source\(s\) réelle\(s\)/);
  });

  await t.test(' déconnexion : interface masquée, jeton effacé, flux interrompu', async () => {
    $('btn-logout').click();
    await tick();
    assert.equal($('app').hidden, true);
    assert.equal(window.localStorage.getItem('or100_token'), null);
    assert.match($('role-badge').textContent, /non connecté/);
  });

  window.close();
});
