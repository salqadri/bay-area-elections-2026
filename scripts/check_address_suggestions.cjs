'use strict';

const assert = require('node:assert/strict');
const service = require('../src/address-suggestions.js');

function feature(properties = {}) {
  return {type: 'Feature', properties: {
    countrycode: 'US', country: 'United States', housenumber: '200',
    street: 'East Santa Clara Street', city: 'San Jose', state: 'California',
    postcode: '95113', ...properties
  }};
}

function payload(features = [feature()]) { return {type: 'FeatureCollection', features}; }
function response(body = payload(), status = 200) {
  return {ok: status >= 200 && status < 300, status, async json() { return body; }};
}

function trackedSignal() {
  const controller = new AbortController();
  const listeners = new Set();
  const signal = {
    get aborted() { return controller.signal.aborted; },
    addEventListener(type, callback, options) {
      assert.equal(type, 'abort');
      listeners.add(callback);
      controller.signal.addEventListener(type, callback, options);
    },
    removeEventListener(type, callback) {
      listeners.delete(callback);
      controller.signal.removeEventListener(type, callback);
    }
  };
  return {signal, listeners, abort() { controller.abort(); }};
}

function fixture() {
  const calls = [];
  const timers = new Map();
  let nextTimer = 0;
  let time = 1_000_000;
  const client = service.createClient({
    fetch(url, options) {
      let resolve, reject;
      const pending = new Promise((a, b) => { resolve = a; reject = b; });
      const aborted = () => {
        const error = new Error('Mock fetch aborted.');
        error.name = 'AbortError';
        reject(error);
      };
      options.signal.addEventListener('abort', aborted, {once: true});
      calls.push({url: new URL(url), options, resolve, reject});
      return pending.finally(() => options.signal.removeEventListener('abort', aborted));
    },
    setTimeout(fn, ms) { const id = ++nextTimer; timers.set(id, {fn, ms}); return id; },
    clearTimeout(id) { timers.delete(id); },
    now() { return time; }
  });
  function clean(external) {
    assert.equal(timers.size, 0, 'request timeout cleared');
    if (external) assert.equal(external.listeners.size, 0, 'caller abort listener removed');
  }
  return {client, calls, timers, clean, advance(ms) { time += ms; }};
}

let passed = 0;
async function test(label, run) {
  await run();
  passed++;
  process.stdout.write('PASS ' + label + '\n');
}

(async function () {
  await test('actual US house addresses are formatted, deduplicated, and capped', () => {
    const features = [feature(), feature({street: 'east santa clara street'}),
      feature({housenumber: '  1 ', street: '  Main  Street ', city: '', town: 'Pleasanton'}),
      feature({housenumber: '42', city: '', village: 'Example Village', state: 'Oregon'}),
      ...Array.from({length: 8}, (_, n) => feature({housenumber: String(1000 + n)}))];
    const rows = service.suggestionsFromResponse(payload(features));
    assert.equal(rows.length, 6);
    assert.deepEqual(rows[0], {
      label: '200 East Santa Clara Street', detail: 'San Jose, CA 95113',
      value: '200 East Santa Clara Street, San Jose, CA 95113'
    });
    assert.equal(rows[1].value, '1 Main Street, Pleasanton, CA 95113');
    assert.equal(rows[2].value, '42 East Santa Clara Street, Example Village, Oregon 95113');
    assert.equal(rows.filter(row => row.label.toLowerCase() === '200 east santa clara street').length, 1);
    assert.deepEqual(service.suggestionsFromResponse(payload([])), []);
  });

  await test('street-only, foreign, and incomplete records cannot become invented addresses', async () => {
    const unusable = [
      null, {}, feature({housenumber: '', name: '200 East Santa Clara Street'}),
      feature({street: '', name: 'East Santa Clara Street'}),
      feature({city: '', town: '', village: '', locality: ''}), feature({state: ''}),
      feature({countrycode: 'CA', country: 'Canada'}),
      feature({countrycode: '', country: ''}), feature({housenumber: 200}),
      feature({street: ['East Santa Clara Street']})
    ];
    const f = fixture();
    const promise = f.client.lookup('1234 East Santa Clara Street');
    f.calls[0].resolve(response(payload(unusable)));
    assert.deepEqual(await promise, [], 'typed number is never attached to a returned road or place');
    f.clean();
  });

  await test('query encoding preserves input, requests US houses, and biases without excluding other regions', async () => {
    const f = fixture();
    const external = trackedSignal();
    const input = '  200 A&B Street?countrycode=GB #1, San Jose  ';
    const promise = f.client.lookup(input, {signal: external.signal});
    assert.equal(f.calls.length, 1);
    const {url, options} = f.calls[0];
    assert.equal(url.origin + url.pathname, service.endpoint);
    assert.equal(url.searchParams.get('q'), input.trim());
    assert.equal(url.searchParams.get('countrycode'), 'US');
    assert.equal(url.searchParams.get('layer'), 'house');
    assert.equal(url.searchParams.getAll('countrycode').length, 1);
    assert.equal(url.hash, '');
    assert.ok(Number(url.searchParams.get('lat')) > 37 && Number(url.searchParams.get('lat')) < 39);
    assert.ok(Number(url.searchParams.get('lon')) > -123 && Number(url.searchParams.get('lon')) < -121);
    assert.equal(url.searchParams.has('bbox'), false, 'full addresses outside the Bay Area remain discoverable');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.referrerPolicy, 'no-referrer');
    assert.equal(options.headers, undefined);
    assert.equal([...url.searchParams.keys()].some(key => /key|token|secret/i.test(key)), false);
    assert.equal(external.listeners.size, 1);
    f.calls[0].resolve(response(payload([feature({city: 'Portland', state: 'Oregon'})])));
    assert.match((await promise)[0].value, /Portland, Oregon/);
    f.clean(external);
  });

  await test('short, non-string, empty, and overlong inputs make no requests', async () => {
    const f = fixture();
    for (const input of ['', '  ', '123', 'x'.repeat(201), null, undefined, 1234]) {
      assert.deepEqual(await f.client.lookup(input), []);
    }
    assert.equal(f.calls.length, 0);
    f.clean();
  });

  await test('malformed payloads and invalid JSON fail without leaking resources', async () => {
    for (const invalid of [null, {}, {features: {}}, {features: null}]) {
      const f = fixture();
      const external = trackedSignal();
      const promise = f.client.lookup('200 East Santa Clara', {signal: external.signal});
      f.calls[0].resolve(response(invalid));
      await assert.rejects(promise, /Invalid address suggestions response/);
      f.clean(external);
    }
    const f = fixture();
    const promise = f.client.lookup('200 East Santa Clara');
    f.calls[0].resolve({ok: true, status: 200, async json() { throw new SyntaxError('Invalid JSON'); }});
    await assert.rejects(promise, SyntaxError);
    f.clean();
  });

  await test('network and server failures leave manual entry available and allow a later request', async () => {
    for (const fail of [call => call.reject(new TypeError('Failed to fetch')),
      call => call.resolve(response({}, 503))]) {
      const f = fixture();
      const external = trackedSignal();
      const promise = f.client.lookup('200 East Santa Clara', {signal: external.signal});
      fail(f.calls[0]);
      await assert.rejects(promise);
      f.clean(external);
      const retry = f.client.lookup('200 East Santa Clara');
      assert.equal(f.calls.length, 2);
      f.calls[1].resolve(response());
      assert.equal((await retry).length, 1);
      f.clean();
    }
  });

  await test('HTTP 429 stops new requests during backoff and resumes afterward', async () => {
    const f = fixture();
    const promise = f.client.lookup('200 East Santa Clara');
    f.calls[0].resolve(response({}, 429));
    await assert.rejects(promise, /busy.*manually/i);
    f.clean();
    await assert.rejects(f.client.lookup('1 Dr Carlton Goodlett'), /temporarily unavailable.*manually/i);
    f.advance(59_999);
    await assert.rejects(f.client.lookup('1 Dr Carlton Goodlett'), /temporarily unavailable/i);
    assert.equal(f.calls.length, 1, 'backoff does not send additional provider requests');
    f.advance(1);
    const retried = f.client.lookup('1 Dr Carlton Goodlett');
    assert.equal(f.calls.length, 2);
    f.calls[1].resolve(response());
    assert.equal((await retried).length, 1);
    f.clean();
  });

  await test('timeout aborts the transport and cleans its timer and caller listener', async () => {
    const f = fixture();
    const external = trackedSignal();
    const promise = f.client.lookup('200 East Santa Clara', {signal: external.signal});
    assert.equal(f.timers.size, 1);
    const timer = [...f.timers.values()][0];
    assert.ok(timer.ms > 0 && timer.ms <= 10_000, 'suggestions use a short finite timeout');
    timer.fn();
    await assert.rejects(promise, /timed out.*manually/i);
    assert.equal(f.calls[0].options.signal.aborted, true);
    assert.equal(external.signal.aborted, false, 'caller signal is not mutated');
    f.clean(external);
  });

  await test('caller cancellation aborts only its own lookup and releases resources', async () => {
    const f = fixture();
    const first = trackedSignal(), second = trackedSignal();
    const a = f.client.lookup('200 East Santa Clara', {signal: first.signal});
    const b = f.client.lookup('1 Dr Carlton Goodlett', {signal: second.signal});
    first.abort();
    await assert.rejects(a, {name: 'AbortError'});
    assert.equal(f.calls[0].options.signal.aborted, true);
    assert.equal(f.calls[1].options.signal.aborted, false);
    assert.equal(first.listeners.size, 0);
    assert.equal(f.timers.size, 1);
    f.calls[1].resolve(response());
    assert.equal((await b).length, 1);
    f.clean(second);
  });

  await test('already canceled calls send nothing and cancellation during JSON parsing cannot return suggestions', async () => {
    const f = fixture();
    const external = trackedSignal();
    external.abort();
    await assert.rejects(f.client.lookup('200 East Santa Clara', {signal: external.signal}), {name: 'AbortError'});
    assert.equal(f.calls.length, 0);
    f.clean(external);

    const active = trackedSignal();
    let finishJSON, startJSON;
    const parsingStarted = new Promise(resolve => { startJSON = resolve; });
    const promise = f.client.lookup('200 East Santa Clara', {signal: active.signal});
    f.calls[0].resolve({ok: true, status: 200, json() {
      startJSON();
      return new Promise(resolve => { finishJSON = resolve; });
    }});
    await parsingStarted;
    active.abort();
    finishJSON(payload());
    await assert.rejects(promise, {name: 'AbortError'});
    f.clean(active);
  });

  process.stdout.write('Address suggestion checks passed: ' + passed + '\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
