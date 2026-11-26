/* Tests statiques de l'interface (node:test) : contrôles réels, aucun faux
   jeu de données, aucune injection HTML, responsive et PWA. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..', 'app', 'web');
const read = (f) => fs.readFileSync(path.join(root, f), 'utf8');
const html = read('index.html');
const js = read('app.js');
const css = read('styles.css');
const manifest = JSON.parse(read('manifest.webmanifest'));
const sw = read('sw.js');

test('toutes les fonctionnalités demandées ont un contrôle réel', () => {
  const ids = ['mission-form', 'query', 'mode-grid', 'btn-launch', 'quick-status',
    'mission-header', 'progress-bar', 'agent-list', 'event-list', 'source-list',
    'contradiction-list', 'report-body', 'citation-list', 'history-list',
    'cache-list', 'provider-list', 'quota-list', 'settings-form', 'login-form'];
  ids.forEach((id) => assert.ok(html.includes('id="' + id + '"'), 'manque #' + id));
  ['search', 'mission', 'sources', 'contradictions', 'report', 'history',
    'providers', 'settings'].forEach((tab) =>
    assert.ok(html.includes('data-tab="' + tab + '"'), 'manque onglet ' + tab));
});

test('les trois modes sont présentés et sélectionnables', () => {
  assert.ok(js.includes("['fast', 'deep', 'maximum']") || js.includes("MODES ="));
  ['FAST', 'DEEP', 'MAXIMUM'].forEach((m) => assert.ok(js.includes(m)));
  assert.ok(js.includes("mode: state.mode"));
});

test('le front appelle les vrais endpoints du backend', () => {
  ['/api/auth/login', '/api/health', '/api/missions', '/api/settings',
    '/api/providers', '/api/history', '/api/providers/quota'].forEach((p) =>
    assert.ok(js.includes(p), 'endpoint manquant ' + p));
  ["'/agents'", "'/sources'", "'/contradictions'", "'/report'",
    "'/test'", "'/events'"].forEach((p) => assert.ok(js.includes(p)));
});

test('aucune donnée fictive ni interprétation HTML de contenu non fiable', () => {
  assert.ok(!js.includes('innerHTML'), 'innerHTML interdit');
  assert.ok(js.includes('textContent'), 'textContent requis');
  assert.ok(!/const (fake|mock|demo)(Data|Sources|Results)/i.test(js));
  assert.ok(js.includes('untrusted') || html.includes('non fiables'));
  assert.ok(js.includes('Aucune donnée disponible'));
});

test('interface Android/ordinateur et PWA', () => {
  assert.ok(css.includes('@media (max-width: 720px)'));
  assert.ok(css.includes('font-size: 16px'));
  assert.ok(html.includes('viewport-fit=cover'));
  assert.equal(manifest.display, 'standalone');
  assert.equal(manifest.start_url, '/');
  assert.ok(sw.includes('/api/'), 'le SW doit exclure les API du cache');
  assert.ok(fs.existsSync(path.join(root, 'icon.svg')));
});
