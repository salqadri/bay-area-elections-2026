'use strict';
// Offline behavior checks; browser network inspection is a separate release step.
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/analytics.js'), 'utf8');
const publicUrl = 'https://salqadri.github.io/bay-area-elections-2026/';
function runner() {
  const context = vm.createContext({window: {location: new URL('http://localhost:8000/')}, console: {warn() {}}});
  vm.runInContext(source, context);
  return context.startPublishedAnalytics;
}
function sdk(supported = true) {
  const apps = [], calls = [];
  return {apps, calls, load: async () => [
    {initializeApp(config) {apps.push(config); return 'test-app';}},
    {isSupported: async () => supported, initializeAnalytics(app, options) {calls.push({app, options});}}
  ]};
}
(async () => {
  for (const url of ['http://localhost:8000/', 'http://127.0.0.1:8000/ballot.html', 'file:///tmp/index.html',
    'https://example.com/bay-area-elections-2026/', 'http://salqadri.github.io/bay-area-elections-2026/',
    'https://salqadri.github.io/other-project/', publicUrl + 'jev-playground/', publicUrl + 'nested/ballot.html']) {
    let fetched = false;
    assert.equal(await runner()(new URL(url), async () => {fetched = true;}), false);
    assert.equal(fetched, false, 'Nonproduction pages must not even fetch Firebase');
  }
  for (const origin of [publicUrl, 'https://tall-bay-area-research-tool.web.app/', 'https://tall-bay-area-research-tool.firebaseapp.com/']) {
  for (const name of ['', 'index.html', 'ballot.html']) {
    const run = runner(), mock = sdk();
    const url = new URL(origin + name + '?q=PRIVATE_QUERY#q=PRIVATE_FRAGMENT');
    assert.equal(await run(url, mock.load), true);
    assert.equal(await run(url, mock.load), false, 'Only one initialization per page');
    assert.equal(mock.apps.length, 1);
    assert.equal(mock.apps[0].measurementId, 'G-QKNPZZ1CDJ');
    assert.equal(mock.apps[0].appId, '1:693468629214:web:04e5a5f66ac3d549e39a4f');
    assert.equal(mock.calls.length, 1);
    const config = mock.calls[0].options.config;
    assert.equal(config.page_location, origin + (name === 'ballot.html' ? name : ''));
    assert.equal(config.page_referrer, '');
    assert.equal(config.allow_google_signals, false);
    assert.equal(config.allow_ad_personalization_signals, false);
    assert.equal(config.cookie_path, new URL(origin).pathname);
    assert.equal(config.cookie_domain, new URL(origin).hostname);
    assert(!JSON.stringify(mock).includes('PRIVATE_'), 'Never pass free text or URL parameters into Firebase');
  }
  }
  const unsupported = sdk(false);
  assert.equal(await runner()(new URL(publicUrl), unsupported.load), false);
  assert.equal(unsupported.apps.length, 0);
  assert.equal(await runner()(new URL(publicUrl), async () => {throw Error('offline');}), false);
  const denied = sdk();
  denied.load = async () => [{initializeApp() {throw Error('blocked');}}, {isSupported: async () => true}];
  assert.equal(await runner()(new URL(publicUrl), denied.load), false);
  for (const name of ['index', 'ballot']) {
    const html = fs.readFileSync(path.join(root, name + '.html'), 'utf8');
    const scripts = [...html.matchAll(/<script type="module">([\s\S]*?)<\/script>/g)];
    assert.equal(scripts.length, 1);
    assert.equal(scripts[0][1], source, 'Both readers embed exactly the maintained analytics module');
    assert(html.includes('Google Analytics cookies'));
  }
  console.log('Analytics: production scope, sanitized initialization, one-time setup and failure isolation PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
