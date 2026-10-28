'use strict';
// Minimal DOM shim to execute the recommendations display module in Node.
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

class El {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.style = {}; this.attrs = {};
    this._text = ''; this._html = ''; this.className = '';
    this.value = ''; this.checked = false; this.listeners = {};
    this.href = ''; this.id = '';
  }
  get textContent() { return this._text || (this.children || []).map(c => c.textContent).join(''); }
  set textContent(v) { this._text = String(v); this.children = []; }
  get innerHTML() { return this._html; }
  set innerHTML(v) {
    this._html = String(v); this._text = '';
    // crude parse: top-level <tag>...</tag> blocks become child Els with _html set
    this.children = [];
    let rest = this._html;
    const re = /<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>([\s\S]*?)<\/\1>/g;
    let m, last = 0;
    while ((m = re.exec(rest))) {
      if (m.index > last) { const t = rest.slice(last, m.index).trim(); if (t) this.children.push(textEl(t)); }
      const c = new El(m[1]); c._html = m[0]; c._text = m[2]; this.children.push(c);
      last = m.index + m[0].length;
    }
    const tail = rest.slice(last).trim();
    if (tail) this.children.push(textEl(tail));
  }
  get options() { return [...String(this._html).matchAll(/<option value="([^"]*)">([^<]*)</g)].map(x => ({value: x[1], text: x[2]})); }
  appendChild(c) { this.children.push(c); return c; }
  replaceChildren(...cs) { this.children = [...cs]; }
  addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); }
  dispatch(ev) { (this.listeners[ev] || []).forEach(fn => fn()); }
  append(...cs) { this.children.push(...cs); }
}
function textEl(t) { const e = new El('#text'); e._text = t; return e; }
const els = {};
function makeEl(tag, id) { const e = new El(tag); if (id) e.id = id; els[id] = e; return e; }

makeEl('ul', 'rec-list');
makeEl('select', 'rec-office-filter');
makeEl('input', 'rec-search');
const picks = makeEl('input', 'rec-only-picks');
makeEl('span', 'footer-stats');
makeEl('div', 'hero-stats');

global.document = {
  getElementById: id => els[id] || null,
  createElement: t => new El(t),
  createTextNode: t => new El('#text'),
};
global.location = { hash: '' };
global.requestAnimationFrame = fn => {};
global.Intl = Intl;

// Extract the embedded JSON payload from the built page.
const html = fs.readFileSync(path.join(ROOT, 'recommendations.html'), 'utf8');
const m = /<script type="application\/json" id="rec-data">([\s\S]*?)<\/script>/.exec(html);
if (!m) throw new Error('rec-data script not found in recommendations.html');
els['rec-data'] = new El('script');
els['rec-data'].textContent = m[1];

// Load shared contest-label module first.
const labelJs = fs.readFileSync(path.join(ROOT, 'src', 'contest-label.js'), 'utf8');
(0, eval)(labelJs + '\n;global.ContestLabel = (typeof ContestLabel !== "undefined") ? ContestLabel : null;');

// Execute the display module (IIFE, uses the globals above).
const dispJs = fs.readFileSync(path.join(ROOT, 'src', 'recommendations-display.js'), 'utf8');
eval(dispJs);

// ---- assertions ----
const list = els['rec-list'];
const cards = list.children;
console.log('cards rendered:', cards.length);
console.log('footer:', els['footer-stats'].textContent);
console.log('hero:', els['hero-stats'].children.map(c => c._text || (c.children || []).map(x => x._text || x._html).join('')).join(' | '));
console.log('office filter options:', els['rec-office-filter'].options.length);

// Simulate the "only recommended" filter.
picks.checked = true;
els['rec-office-filter'].dispatch('change');
console.log('after picks-only filter:', els['rec-list'].children.length);
picks.checked = false;
els['rec-office-filter'].dispatch('change');

// Simulate an office filter.
const opts = els['rec-office-filter'].options.map(o => o.value);
console.log('filter values:', opts.join(', '));
els['rec-office-filter'].value = opts[1] || opts[0];
els['rec-office-filter'].dispatch('change');
const n1 = els['rec-list'].children.length;
els['rec-office-filter'].value = '';
els['rec-office-filter'].dispatch('change');
console.log('filtered by', JSON.stringify(opts[1] || opts[0]), '->', n1, 'cards; back to all:', els['rec-list'].children.length);

// Search filter.
els['rec-search'].value = 'mayor';
els['rec-search'].dispatch('input');
console.log('search "mayor":', els['rec-list'].children.length);
els['rec-search'].value = '';
els['rec-search'].dispatch('input');

// Verify a few card shapes.
const sample = cards[0];
console.log('first card class:', sample.className);
console.log('sample card html (first 600):', sample._html ? sample._html.slice(0, 600) : (sample.children[0] && sample.children[0]._html ? sample.children[0]._html.slice(0, 600) : 'n/a'));
console.log('OK');
