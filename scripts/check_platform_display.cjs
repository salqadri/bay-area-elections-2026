'use strict';
// Fixed source-shaped cases verify the shared platform positions renderer.
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert/strict');
const display = vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/platform-display.js'), 'utf8') + '\nPlatformDisplay', {URL});
class Element {
  constructor(tag, cls, text) { this.tagName=tag.toUpperCase();this.className=cls||'';this.children=[];this.attrs={};this.open=false;if(text!==undefined&&text!==null)this.children.push(String(text)); }
  append(...children) { for(const child of children){this.children.push(child);if(typeof child==='object')child.parent=this;} }
  get textContent() { return this.children.map(c=>typeof c==='string'?c:c.textContent).join(''); }
  setAttribute(key, value) { this.attrs[key]=String(value); }
  set innerHTML(value) { throw Error('Platform text must be rendered as text, never HTML'); }
}
const node=(tag,cls,text)=>new Element(tag,cls,text);
const link=(url,text,cls)=>{const result=node('a',cls,text);result.href=url;return result;};
const helpers={node,link,dateLabel:value=>value};
const all=n=>[n,...n.children.filter(c=>typeof c==='object').flatMap(all)];

const found=display.render({campaign_url:'https://example.org/',platform_positions:{status:'positions_found',checked_on:'2026-10-16',scope_note:'Bounded website check; positions quoted verbatim from the pages listed here.',pages:[{url:'https://example.org/issues',title:'Issues',content_sha256:'a'.repeat(64)}],points:[
  {topic:'Housing',summary:'Builds social housing at all income levels and expands rent protections.',quote:'build more affordable housing units',source_url:'https://example.org/issues'},
  {topic:'Israel / Palestine',summary:'Calls for full divestment by the city from Israel.',quote:'divest completely and immediately from Israel',source_url:'https://example.org/issues'}]}},helpers);
assert.equal(found.tagName,'DETAILS');assert.equal(found.open,false);
for(const expected of ['What they stand for','positions quoted from the campaign','Housing','social housing at all income levels','“build more affordable housing units”','Israel / Palestine','divest completely and immediately','Bounded website check','Snapshot checked 2026-10-16','Reviewed pages · 1']) assert(found.textContent.includes(expected),expected);
assert(all(found).some(n=>n.href==='https://example.org/issues'));
assert.equal(all(found).filter(n=>n.className==='platform-point').length,2);

const silence=display.render({campaign_url:'https://example.org/',platform_positions:{status:'no_positions_found',checked_on:'2026-10-16',scope_note:'No position found within the captured pages; not proof none exists elsewhere.',pages:[{url:'https://example.org/',title:'Home',content_sha256:'b'.repeat(64)}],points:[]}},helpers);
assert(silence.textContent.includes('not proof that none exists'));
assert.equal(all(silence).filter(n=>n.className==='platform-point').length,0,'Silence must not render points');

const missing=display.render({name:'No site'},helpers);
assert.equal(missing,null,'Candidates without a platform record render nothing');

// A non-HTTPS source URL degrades to text instead of an injectable link.
const unsafe=display.render({platform_positions:{status:'positions_found',checked_on:'2026-10-16',scope_note:'x',pages:[{url:'javascript:alert(1)',title:'t',content_sha256:'c'.repeat(64)}],points:[{topic:'Other',summary:'A position with an unsafe source URL for the guard.',quote:'unsafe url guard fixture',source_url:'javascript:alert(1)'}]}},helpers);
assert(!all(unsafe).some(n=>n.href));assert(unsafe.textContent.includes('link unavailable'));

console.log(JSON.stringify({passed:true,checks:'platform display renderer'}));
