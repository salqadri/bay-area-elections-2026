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
const gallery=display.render({endorsement_images:[record]},{node,link});
assert.equal(gallery.tagName,'DETAILS');assert(gallery.textContent.includes('Endorsements and recommendations · 1 entry'));assert(!gallery.textContent.includes('Campaign image evidence'));
assert(gallery.textContent.includes('Filename (metadata): ag-bonta<script>.png'));
assert(!gallery.textContent.includes('Endorsed by'));
const img=all(gallery).find(n=>n.tagName==='IMG');assert.equal(img.src,record.image_url);assert(!img.alt.includes('Wrong Person'));assert(!img.alt.includes('ag-bonta'));assert.equal(img.loading,'lazy');
assert(all(gallery).some(n=>n.href===record.image_url&&n.textContent==='View image ↗'));
img.listeners.error();assert(img.hidden);assert(all(gallery).some(n=>n.href===record.image_url),'Source link survives image failure');
const legacy=display.render({endorsement_images:[{...record,provenance:'legacy_import'}]},{node,link});
assert(legacy.textContent.includes('exact page placement and image identity have not been reviewed'));
assert.equal(all(legacy).find(n=>n.tagName==='IMG').src,record.image_url);
const unsafe=display.render({endorsement_images:[{...record,image_url:'javascript:alert(1)'}]},{node,link});
assert(!all(unsafe).some(n=>n.tagName==='IMG'),'Non-HTTPS preview URL must not render an image');
assert.equal(display.render({}, {node,link}),null);
const badge=display.label({endorser:'Moms Demand Action',relation:'distinction',phase:'unspecified',checked_on:'2026-10-17',verification:'campaign_claim'});
assert(badge.startsWith('Distinction from '));assert(!badge.includes('Endorsed by'));
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../2026-11-03_Bay_Area_Elections.json'),'utf8'));
const wiener=data.positions.flatMap(p=>p.candidates||[]).find(c=>c.name==='Scott Wiener');
const unified=display.render(wiener,{node,link,noteText:id=>data.notes[id]||''});
const lists=all(unified).filter(n=>n.tagName==='UL'&&n.className==='endorsement-list');
assert.equal(lists.length,1,'Text and image entries must share one list');
assert.equal(lists[0].children.length,wiener.endorsements.length+wiener.endorsement_images.length);
assert.equal(lists[0].children.filter(n=>n.className==='endorsement-text-item').length,69);
assert.equal(lists[0].children.filter(n=>n.className==='endorsement-image-entry').length,50);
assert.equal(all(unified).filter(n=>n.tagName==='IMG').length,50);
assert(!unified.textContent.includes('Campaign image evidence'));
assert(unified.textContent.includes('119 entries'));
assert(unified.textContent.includes('Endorsed by Matt Haney'));
assert(!unified.textContent.includes('Endorsed by ag bonta'));
for(const name of ['Jimmy Panetta','Gail Pellerin','Connie Chan']) {
  const candidate=data.positions.flatMap(p=>p.candidates||[]).find(c=>c.name===name);
  const rendered=display.render(candidate,{node,link});
  const list=all(rendered).find(n=>n.tagName==='UL'&&n.className==='endorsement-list');
  assert.equal(list.children.length,candidate.endorsements.length+candidate.endorsement_images.length,name+' must keep all text and image entries');
  assert(!rendered.textContent.includes('Campaign image evidence'));
}
assert(display.render({endorsements:[{endorser:'Example',relation:'endorsed'}]},{node,link}));
const connie=data.positions.flatMap(p=>p.candidates||[]).find(c=>c.name==='Connie Chan');
const connieList=all(display.render(connie,{node,link,noteText:id=>data.notes[id]||''})).find(n=>n.className==='endorsement-list');
for(const endorser of ['Mabel Teng', "Sailors' Union of the Pacific"]) {
  const record=connie.endorsements.find(r=>r.endorser===endorser);
  const entry=connieList.children.find(n=>n.textContent.startsWith('Endorsed by '+endorser+' ·'));
  assert(entry,endorser+' must have its own endorsement entry');
  assert.equal(all(entry).filter(n=>n.tagName==='IMG').length,1);
  assert.equal(all(entry).find(n=>n.tagName==='IMG').src,record.logo_url,endorser+' must retain its own image');
  assert(all(entry).some(n=>n.href===record.url));
  assert(all(entry).some(n=>n.className==='endorsement-note'),'The research note belongs to the same entry');
  assert(!entry.textContent.includes(endorser==='Mabel Teng'?"Sailors' Union of the Pacific":'Mabel Teng'));
}
console.log(JSON.stringify({passed:true,checks:'one mixed list, Wiener 69 text + 50 images, Connie image ownership, metadata, external URLs, image fallback, distinction semantics'}));
