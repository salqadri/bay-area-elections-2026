'use strict';
// Interaction checks in a minimal DOM with a deterministic clock, not a browser
// rendering test. Real providers are replaced with controlled responses.
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../src/address-autocomplete.js'), 'utf8');
const choices = [
  { label: '200 East Santa Clara Street', detail: 'San Jose, CA 95113', value: '200 East Santa Clara Street, San Jose, CA 95113' },
  { label: '200 West Santa Clara Street', detail: 'San Jose, CA 95113', value: '200 West Santa Clara Street, San Jose, CA 95113' }
];
const settle = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
function deferred() { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
class Element {
  constructor(tag, doc) { this.tagName = tag.toUpperCase(); this.ownerDocument = doc; this.events = {}; this.attrs = {}; this.children = []; this.dataset = {}; this.hidden = false; this.value = ''; }
  addEventListener(type, fn) { (this.events[type] ||= []).push(fn); }
  removeEventListener(type, fn) { this.events[type] = (this.events[type] || []).filter(f => f !== fn); }
  fire(type, values = {}) { const event = { target: this, prevented: false, preventDefault() { this.prevented = true; }, ...values }; for (const fn of this.events[type] || []) fn(event); return event; }
  append(child) { child.parentNode = this; this.children.push(child); }
  replaceChildren() { this.children = []; }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  removeAttribute(name) { delete this.attrs[name]; }
  get textContent() { return this._text || this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this.children = []; this._text = String(value); }
  contains(node) { return node === this || this.children.some(child => child.contains(node)); }
  focus() { this.ownerDocument.activeElement = this; }
  scrollIntoView() {}
}
function harness(handler = () => choices) {
  let now = 0, nextTimer = 0;
  const timers = new Map(), calls = [];
  const doc = new Element('document');
  doc.createElement = tag => new Element(tag, doc);
  const input = doc.createElement('input'), listbox = doc.createElement('ul'), status = doc.createElement('p'), form = doc.createElement('form');
  input.id = 'voting-address'; listbox.id = 'address-suggestions'; input.form = form;
  const context = { document: doc, AbortController, Date: { now: () => now }, console,
    setTimeout(fn, delay) { const id = ++nextTimer; timers.set(id, { fn, at: now + delay }); return id; },
    clearTimeout(id) { timers.delete(id); }
  };
  for (const key of ['localStorage', 'sessionStorage']) Object.defineProperty(context, key, { get() { throw Error('Autocomplete must not use browser storage'); } });
  vm.createContext(context); vm.runInContext(source, context);
  const instance = context.ElectionAddressAutocomplete.attach({ input, listbox, status, lookup(query, options) { calls.push({ query, options, at: now }); return handler(query, options); } });
  async function tick(ms) {
    const until = now + ms;
    while (true) {
      const entry = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
      if (!entry || entry[1].at > until) break;
      now = entry[1].at; timers.delete(entry[0]); entry[1].fn(); await settle();
    }
    now = until; await settle();
  }
  return { input, listbox, status, form, doc, calls, tick, instance, type(value) { input.value = value; input.fire('input'); }, key(key) { return input.fire('keydown', { key }); } };
}
const checks = [];
async function check(name, fn) { await fn(); checks.push(name); }
(async () => {
  await check('Short input is private; typing is debounced and requests are spaced at least one second apart', async () => {
    const h = harness(); h.type('200'); await h.tick(2000); assert.equal(h.calls.length, 0);
    h.type('200 S'); await h.tick(400); h.type('200 Santa'); await h.tick(749); assert.equal(h.calls.length, 0);
    await h.tick(1); assert.equal(h.calls.length, 1); assert.equal(h.calls[0].query, '200 Santa');
    h.type('200 Santa Clara'); await h.tick(999); assert.equal(h.calls.length, 1); await h.tick(1);
    assert.equal(h.calls.length, 2); assert(h.calls[1].at - h.calls[0].at >= 1000);
  });
  await check('No default selection; keyboard chooses an address without submitting it', async () => {
    const h = harness(); h.type('200 Santa'); await h.tick(750);
    assert.equal(h.input.attrs['aria-expanded'], 'true'); assert.equal(h.input.attrs['aria-activedescendant'], undefined);
    assert.equal(h.listbox.children[0].attrs['aria-selected'], 'false');
    assert(h.key('ArrowDown').prevented); assert.equal(h.input.attrs['aria-activedescendant'], h.listbox.children[0].id);
    assert(h.key('Enter').prevented); assert.equal(h.input.value, choices[0].value); assert(h.listbox.hidden);
    assert.equal(h.key('Enter').prevented, false, 'A second Enter can submit the populated address');
  });
  await check('Manual Enter stays a normal form submission even when suggestions are open', async () => {
    const h = harness(); h.type('200 Santa'); await h.tick(750); assert.equal(h.key('Enter').prevented, false); assert(h.listbox.hidden);
    assert.equal(h.input.value, '200 Santa');
  });
  await check('Pointer selection includes the city in the filled address and keeps focus on the input', async () => {
    const h = harness(); h.type('200 Santa'); await h.tick(750);
    assert(h.listbox.fire('pointerdown', { button: 0 }).prevented);
    h.listbox.fire('click', { target: h.listbox.children[1].children[1] });
    assert.equal(h.input.value, choices[1].value); assert.equal(h.doc.activeElement, h.input); assert(h.listbox.hidden);
  });
  await check('Aborted or stale responses cannot reopen or replace the latest suggestions', async () => {
    const first = deferred(), second = deferred();
    const h = harness(query => query === '200 First' ? first.promise : second.promise);
    h.type('200 First'); await h.tick(750); h.type('200 Second'); assert(h.calls[0].options.signal.aborted);
    await h.tick(1000); second.resolve([choices[1]]); await settle(); first.resolve([choices[0]]); await settle();
    assert(h.listbox.textContent.includes('West')); assert(!h.listbox.textContent.includes('East'));
    h.type('200 Third'); await h.tick(1000); h.instance.close(); await settle(); assert(h.listbox.hidden);
  });
  await check('Form submission, blur, Escape, Tab, and outside click close suggestions and cancel work', async () => {
    for (const action of [h => h.form.fire('submit'), h => h.input.fire('blur'), h => h.key('Escape'), h => h.key('Tab'), h => h.doc.fire('pointerdown', { target: h.doc })]) {
      const pending = deferred(), h = harness(() => pending.promise); h.type('200 Santa'); await h.tick(750); action(h);
      assert(h.calls[0].options.signal.aborted); pending.resolve(choices); await settle(); assert(h.listbox.hidden);
    }
    const h = harness(); h.type('200 Santa'); await h.tick(750); assert.equal(h.key('Tab').prevented, false);
  });
  await check('IME composition does not send partial composition text or intercept confirmation', async () => {
    const h = harness(); h.input.fire('compositionstart'); h.type('200 Santa'); await h.tick(1000); assert.equal(h.calls.length, 0);
    assert.equal(h.key('Enter').prevented, false); h.input.fire('compositionend'); await h.tick(750); assert.equal(h.calls.length, 1);
  });
  await check('Provider failure leaves manual entry available and backs off without automatic retries', async () => {
    const h = harness(() => Promise.reject(Error('offline'))); h.type('200 Santa'); await h.tick(750);
    assert(h.listbox.hidden); assert(h.status.textContent.includes('manually')); h.type('200 Santa Clara'); await h.tick(10000); assert.equal(h.calls.length, 1);
    await h.tick(30000); assert.equal(h.calls.length, 1); h.type('200 Santa Clara Street'); await h.tick(750); assert.equal(h.calls.length, 2);
    assert.equal(h.key('Enter').prevented, false);
  });
  await check('Suggestion text is rendered as text; empty results explain manual entry', async () => {
    const h = harness(() => [{ label: '<img src=x onerror=alert(1)>', detail: '<b>City</b>', value: '200 Test Street, City, CA' }]);
    h.type('200 Test'); await h.tick(750); assert.equal(h.listbox.children[0].children[0].tagName, 'SPAN');
    assert.equal(h.listbox.children[0].children[0].textContent, '<img src=x onerror=alert(1)>');
    const empty = harness(() => []); empty.type('200 Test'); await empty.tick(750); assert(empty.listbox.hidden); assert(empty.status.textContent.includes('manually'));
  });
  await check('Destroy removes listeners and pending work without browser storage', async () => {
    const h = harness(); h.type('200 Santa'); h.instance.destroy(); await h.tick(2000); assert.equal(h.calls.length, 0);
    h.type('300 Santa'); await h.tick(2000); assert.equal(h.calls.length, 0); assert.equal(h.doc.events.pointerdown.length, 0);
  });
  console.log(JSON.stringify({ passed: true, check_count: checks.length, environment: 'Minimal DOM and clock harness; not a live provider or browser rendering test', checks }, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
