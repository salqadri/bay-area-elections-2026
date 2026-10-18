'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict');
const display=vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/endorsement-display.js'),'utf8')+'\nEndorsementDisplay',{URL});
class Element {
  constructor(tag,cls,text){this.tagName=tag.toUpperCase();this.className=cls||'';this.children=[];this.listeners={};if(text!=null)this.children.push(String(text));}
  append(...nodes){this.children.push(...nodes);}
  get textContent(){return this.children.map(c=>typeof c==='string'?c:c.textContent).join('');}
  addEventListener(type,fn){this.listeners[type]=fn;}
  set innerHTML(value){throw Error('Source metadata must be text, never HTML');}
}
const node=(tag,cls,text)=>new Element(tag,cls,text);
const link=(url,text)=>{const a=node('a',null,text);a.href=url;return a;};
const all=n=>[n,...n.children.filter(c=>typeof c==='object').flatMap(all)];
const record={id:'I-test',image_url:'https://example.org/misleading.png',source_url:'https://example.org/endorsements',filename:'ag-bonta<script>.png',original_alt:'Wrong Person',context:'Rob Bonta',heading:'Endorsements',checked_on:'2026-10-17',provenance:'page_capture'};
const gallery=display.renderImages({endorsement_images:[record]},{node,link});
assert.equal(gallery.tagName,'DETAILS');assert(gallery.textContent.includes('Campaign image evidence · 1 images'));
assert(gallery.textContent.includes('Filename (metadata): ag-bonta<script>.png'));
assert(!gallery.textContent.includes('Endorsed by'));
const img=all(gallery).find(n=>n.tagName==='IMG');assert.equal(img.src,record.image_url);assert(!img.alt.includes('Wrong Person'));assert(!img.alt.includes('ag-bonta'));assert.equal(img.loading,'lazy');
assert(all(gallery).some(n=>n.href===record.image_url&&n.textContent==='View image ↗'));
img.listeners.error();assert(img.hidden);assert(all(gallery).some(n=>n.href===record.image_url),'Source link survives image failure');
const legacy=display.renderImages({endorsement_images:[{...record,provenance:'legacy_import'}]},{node,link});
assert(legacy.textContent.includes('exact page placement and image identity have not been reviewed'));
assert.equal(all(legacy).find(n=>n.tagName==='IMG').src,record.image_url);
const unsafe=display.renderImages({endorsement_images:[{...record,image_url:'javascript:alert(1)'}]},{node,link});
assert(!all(unsafe).some(n=>n.tagName==='IMG'),'Non-HTTPS preview URL must not render an image');
assert.equal(display.renderImages({}, {node,link}),null);
const badge=display.label({endorser:'Moms Demand Action',relation:'distinction',phase:'unspecified',checked_on:'2026-10-17',verification:'campaign_claim'});
assert(badge.startsWith('Distinction from '));assert(!badge.includes('Endorsed by'));
console.log(JSON.stringify({passed:true,checks:'neutral images, metadata, external URLs, missing-image fallback and distinction semantics'}));
