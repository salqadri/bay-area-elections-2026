'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const service = require('../src/address-services.js');

function fixture() {
  const host = {};
  const scripts = [];
  const timers = new Map();
  let timerSequence = 0;
  const head = {
    appendChild(script) { scripts.push(script); script.parentNode = head; },
    removeChild(script) { scripts.splice(scripts.indexOf(script), 1); script.parentNode = null; }
  };
  const document = {head, createElement(tag) { assert.equal(tag, 'script'); return {}; }};
  const client = service.createClient({
    globalObject: host, document,
    setTimeout(fn, ms) { const id = ++timerSequence; timers.set(id, {fn, ms}); return id; },
    clearTimeout(id) { timers.delete(id); },
    now() { return new Date('2026-10-06T22:00:00.000Z'); }
  });
  function pending(index = 0) {
    const script = scripts[index];
    const url = new URL(script.src);
    return {script, url, callback: host[url.searchParams.get('callback')]};
  }
  function clean() {
    assert.equal(scripts.length, 0, 'script removed');
    assert.equal(timers.size, 0, 'timer removed');
    assert.deepEqual(Object.keys(host), [], 'global callback removed');
  }
  return {host, document, scripts, timers, client, pending, clean};
}

function match(address = '200 E SANTA CLARA ST, SAN JOSE, CA, 95113') {
  return {
    matchedAddress: address,
    coordinates: {x: -121.885, y: 37.338},
    addressComponents: {city: 'SAN JOSE', state: 'CA', zip: '95113'},
    geographies: {
      Counties: [{STATE: '06', COUNTY: '085', NAME: 'Santa Clara County'}],
      '120th Congressional Districts': [{STATE: '06', CD120: '17'}]
    }
  };
}

function payload(matches = [match()]) { return {result: {addressMatches: matches}}; }
let passed = 0;
async function test(label, run) {
  await run();
  passed++;
  process.stdout.write('PASS ' + label + '\n');
}

(async function () {
  await test('JSONP safely encodes the address and keeps every match with metadata', async () => {
    const f = fixture();
    const address = '  123 A&B St, Example, CA?callback=evil <script>  ';
    const promise = f.client.lookup(address);
    const {script, url, callback} = f.pending();
    assert.equal(url.origin + url.pathname, service.ENDPOINT);
    assert.equal(url.searchParams.get('address'), address.trim());
    assert.equal(url.searchParams.get('format'), 'jsonp');
    assert.equal(url.searchParams.get('benchmark'), 'Public_AR_Current');
    assert.equal(url.searchParams.get('vintage'), 'Current_Current');
    assert.equal(url.searchParams.get('layers'), '14,16,18,28,30,54,56,58,80,82');
    assert.match(url.searchParams.get('callback'), /^__electionCensus_[a-z0-9]+_\d+_\d+$/);
    assert.equal(url.searchParams.getAll('callback').length, 1);
    assert.equal(script.referrerPolicy, 'no-referrer');
    assert.equal([...f.timers.values()][0].ms, 20000);
    callback(payload([match(), match('ANOTHER POSSIBLE ADDRESS')]));
    const result = await promise;
    assert.equal(result.matches.length, 2);
    assert.equal(result.matches[1].matchedAddress, 'ANOTHER POSSIBLE ADDRESS');
    assert.equal(result.provider, 'U.S. Census Bureau');
    assert.equal(result.queriedAt, '2026-10-06T22:00:00.000Z');
    assert.deepEqual(result.layers, service.LAYERS);
    assert.equal(result.benchmark, service.BENCHMARK);
    assert.equal(result.vintage, service.VINTAGE);
    f.clean();
    callback(payload()); // A previously queued callback cannot settle again or leak resources.
    f.clean();
  });

  await test('an address with no matches returns an empty list', async () => {
    const f = fixture();
    const promise = f.client.lookup('No Match, CA');
    f.pending().callback(payload([]));
    assert.deepEqual((await promise).matches, []);
    f.clean();
  });

  await test('incomplete and invalid Census responses reject instead of inventing a location', async () => {
    const badMatch = match();
    badMatch.coordinates.x = 181;
    const malformedGeographies = match();
    malformedGeographies.geographies.Counties = {};
    const malformedShapes = [null, {}, {result: {}}, payload([{}]), payload([badMatch]), payload([malformedGeographies])];
    for (const response of malformedShapes) {
      const f = fixture();
      const promise = f.client.lookup('Example address');
      f.pending().callback(response);
      await assert.rejects(promise, {code: 'INVALID_RESPONSE'});
      f.clean();
    }
  });

  await test('Census service errors become helpful errors without exposing raw responses', async () => {
    for (const response of [{errors: ['internal details']}, {result: {error: 'internal details'}}]) {
      const f = fixture();
      const promise = f.client.lookup('Example address');
      f.pending().callback(response);
      await assert.rejects(promise, error => error.code === 'SERVICE_ERROR' && !error.message.includes('internal details'));
      f.clean();
    }
  });

  await test('timeout removes callbacks, scripts, and timers; late callback does nothing', async () => {
    const f = fixture();
    const promise = f.client.lookup('Example address', {timeoutMs: 50});
    const {callback} = f.pending();
    const timer = [...f.timers.values()][0];
    assert.equal(timer.ms, 50);
    timer.fn();
    await assert.rejects(promise, {code: 'TIMEOUT'});
    f.clean();
    callback(payload());
    f.clean();
  });

  await test('network failure cleans up pending resources', async () => {
    const f = fixture();
    const promise = f.client.lookup('Example address');
    f.pending().script.onerror();
    await assert.rejects(promise, {code: 'NETWORK'});
    f.clean();
  });

  await test('aborting a pending request removes its listener and all resources', async () => {
    const f = fixture();
    const controller = new AbortController();
    let listeners = 0;
    const signal = {
      get aborted() { return controller.signal.aborted; },
      addEventListener(...args) { listeners++; controller.signal.addEventListener(...args); },
      removeEventListener(...args) { listeners--; controller.signal.removeEventListener(...args); }
    };
    const promise = f.client.lookup('Example address', {signal});
    const {callback} = f.pending();
    assert.equal(listeners, 1);
    controller.abort();
    await assert.rejects(promise, {name: 'AbortError', code: 'ABORTED'});
    assert.equal(listeners, 0);
    f.clean();
    callback(payload());
    f.clean();
  });

  await test('already-aborted and invalid requests create no network resources', async () => {
    const f = fixture();
    const controller = new AbortController();
    controller.abort();
    await assert.rejects(f.client.lookup('Example address', {signal: controller.signal}), {code: 'ABORTED'});
    await assert.rejects(f.client.lookup('   '), {code: 'INVALID_ADDRESS'});
    await assert.rejects(f.client.lookup(null), {code: 'INVALID_ADDRESS'});
    await assert.rejects(f.client.lookup('Example address', {timeoutMs: 0}), {code: 'INVALID_OPTIONS'});
    f.clean();
  });

  await test('simultaneous lookups keep callbacks and cancellations separate', async () => {
    const f = fixture();
    const controller = new AbortController();
    const first = f.client.lookup('First address', {signal: controller.signal});
    const second = f.client.lookup('Second address');
    const a = f.pending(0);
    const b = f.pending(1);
    assert.notEqual(a.url.searchParams.get('callback'), b.url.searchParams.get('callback'));
    controller.abort();
    await assert.rejects(first, {code: 'ABORTED'});
    assert.equal(f.scripts.length, 1);
    b.callback(payload([match('SECOND')]));
    assert.equal((await second).matches[0].matchedAddress, 'SECOND');
    f.clean();
  });

  await test('DOM insertion failure removes the registered callback and timer', async () => {
    const f = fixture();
    f.document.head.appendChild = () => { throw new Error('blocked by environment'); };
    await assert.rejects(f.client.lookup('Example address'), {code: 'NETWORK'});
    f.clean();
  });

  await test('UMD browser export and Node export expose the same public interface', async () => {
    const source = fs.readFileSync(path.join(__dirname, '../src/address-services.js'), 'utf8');
    const context = {setTimeout, clearTimeout, URL, URLSearchParams};
    vm.runInNewContext(source, context);
    assert.equal(typeof context.ElectionAddressService.lookup, 'function');
    assert.equal(typeof service.lookup, 'function');
    assert.equal(context.ElectionAddressService.ENDPOINT, service.ENDPOINT);
    await assert.rejects(service.lookup('Example address'), {code: 'UNSUPPORTED_ENVIRONMENT'});
  });

  process.stdout.write(`${passed} address-service checks passed (mock transport; no live-network claim).\n`);
})().catch(error => { console.error(error); process.exitCode = 1; });
