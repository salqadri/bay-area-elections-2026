const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const path = require('path');
const root = path.resolve(__dirname, '..') + path.sep;
const generated = path.join(root, '.checks') + path.sep;
const fixture = JSON.parse(fs.readFileSync(generated + 'explorer_dom_fixture.json'));
const original = JSON.parse(fs.readFileSync(root + '2026-11-03_Bay_Area_Elections.json'));
let activeElement, downloads = [];
class Element {
  constructor(tag, attrs = {}) { this.tagName=tag.toUpperCase(); this.attrs={...attrs}; this.children=[];this.events={};this.dataset={};this.hidden='hidden' in attrs;this.open='open' in attrs;this.checked=false;this.scrollTop=0;this._value=attrs.value;this.parent=null; for(const [k,v] of Object.entries(attrs)) if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,s)=>s.toUpperCase())]=v; }
  append(...items){for(const x of items){this.children.push(x);if(typeof x==='object')x.parent=this;}}
  replaceChildren(...items){this.children=[];this.append(...items);}
  get textContent(){return this.children.map(x=>typeof x==='string'?x:x.textContent).join('');}
  set textContent(text){this.children=[String(text)];}
  get value(){if(this._value!==undefined)return this._value; if(this.tagName==='SELECT')return this.options[0]?.value||'';return this.attrs.value||'';}
  set value(v){this._value=String(v);}
  get options(){return this.children.filter(x=>typeof x==='object'&&x.tagName==='OPTION');}
  get className(){return this.attrs.class||'';} set className(v){this.attrs.class=v;}
  setAttribute(k,v){this.attrs[k]=String(v);}
  getAttribute(k){return this.attrs[k]??null;}
  addEventListener(k,f){(this.events[k]??=[]).push(f);}
  fire(k,extra={}){for(const f of this.events[k]||[])f({target:this,preventDefault(){},...extra});}
  click(){if(this.tagName==='A'&&this.download)downloads.push({filename:this.download,blob:blobs.get(this.href)});this.fire('click');}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);}
  focus(){activeElement=this;}
  scrollIntoView(){}
}
function inflate(x){if(typeof x==='string')return x;const n=new Element(x.tag,x.attrs);n.append(...x.children.map(inflate));return n;}
const doc=inflate(fixture);
function nodes(parent=doc){return [parent,...parent.children.filter(x=>typeof x==='object').flatMap(n=>nodes(n))];}
const all=()=>nodes();
const document={createElement:tag=>new Element(tag),createDocumentFragment:()=>new Element('fragment'),getElementById:id=>all().find(n=>n.attrs.id===id),querySelectorAll:selector=>{const m=selector.match(/^\[([^\]]+)\]$/);assert(m,'Unsupported DOM selector: '+selector);return all().filter(n=>Object.hasOwn(n.attrs,m[1])||(m[1]==='data-contest-id'&&n.dataset.contestId));}};
document.body=all().find(n=>n.tagName==='BODY');
const $=document.getElementById;
const blobs=new Map();let blobId=0;
const RealURL=URL;RealURL.createObjectURL=blob=>{const id='blob:test-'+ ++blobId;blobs.set(id,blob);return id;};RealURL.revokeObjectURL=()=>{};
const location={hash:''};
const window={matchMedia:()=>({matches:false,addEventListener(){}}),events:{},addEventListener(k,f){this.events[k]=f;}};
const context={document,window,location,history:{replaceState(_a,_b,hash){location.hash=hash;}},URL:RealURL,URLSearchParams,Blob,Intl,console,setTimeout:()=>1,clearTimeout(){}};
vm.createContext(context);
const script=all().find(n=>n.tagName==='SCRIPT'&&!n.attrs.type).textContent;
vm.runInContext(script,context,{filename:'explorer-inline.js'});
const cards=()=>all().filter(n=>n.dataset.contestId);
const count=()=>cards().length;
const set=(id,value)=>{$(id).value=value;$(id).fire(id==='search'?'input':'change');};
const clickStatus=s=>all().find(n=>n.dataset.status===s).click();
const reset=()=>$('reset-filters').click();
const tab=s=>all().find(n=>n.dataset.tab===s).click();
const text=id=>$(id).textContent;
const groups=()=>all().filter(n=>n.dataset.sectionKey);
const cardPositions=()=>cards().map(n=>original.positions.find(p=>p.id===n.dataset.contestId));
function visible(n){for(let p=n;p;p=p.parent){if(p.hidden)return false;if(p.tagName==='DETAILS'&&!p.open&&p!==n)return false;}return true;}

(async()=>{
  assert.deepEqual($('county').options.map(option=>option.value).sort(),['',...original.election.counties_in_scope.map(county=>county.name)].sort(),'County selector must contain All plus exactly the five researched counties');
  assert.equal(count(),original.coverage.confirmed_contests);assert(text('notice-text').includes(original.coverage.unresolved_scheduled_contests+' unresolved'));assert(text('result-meta').includes(original.coverage.printed_candidate_entries+' printed'));
  assert(text('hero-subtitle').includes('Contra Costa'));assert(text('hero-subtitle').includes('San Francisco, San Mateo, and Santa Clara'));
  assert.deepEqual(groups().filter(n=>!n.dataset.sectionKey.includes('/')).map(n=>n.dataset.sectionKey),original.display_order.levels);
  const federalDistricts=cardPositions().filter(p=>p.government_level==='Federal').map(p=>p.district_or_seat);
  assert.deepEqual(federalDistricts,['CD-8','CD-9','CD-10','CD-11','CD-12','CD-14','CD-15','CD-16','CD-17','CD-18','CD-19']);
  set('level','State');const statePositions=cardPositions();assert.equal(statePositions[0].office_category,'State Senate');
  assert.equal(statePositions[1].district_or_seat,'AD-11');
  const lastAssembly=statePositions.map(p=>p.office_category).lastIndexOf('State Assembly');
  assert.equal(statePositions[lastAssembly+1].office,'Governor');assert.equal(statePositions[lastAssembly+2].office,'Lieutenant Governor');
  assert.deepEqual(groups().filter(n=>n.dataset.sectionKey.startsWith('State/')).map(n=>n.dataset.sectionKey),['State/State Senate','State/State Assembly','State/Other state offices']);
  $('collapse-sections').click();assert(groups().every(n=>!n.open));assert.equal(cards().filter(visible).length,0);
  $('expand-sections').click();assert(groups().every(n=>n.open));assert.equal(cards().filter(visible).length,cards().length);
  const assemblyGroup=groups().find(n=>n.dataset.sectionKey==='State/State Assembly');assemblyGroup.open=false;assemblyGroup.fire('toggle');assert(!visible(cards().find(n=>n.textContent.includes('AD-18'))));
  set('search','AD-18');assert.equal(count(),1);assert(groups().every(n=>n.open));assert(visible(cards()[0]));
  reset();$('collapse-sections').click();const city=original.positions.find(p=>p.government_level==='City or town'&&p.ballot_status==='confirmed');location.hash='#id='+city.id;window.events.hashchange();assert.equal(cards().find(c=>c.dataset.contestId===city.id).getAttribute('aria-pressed'),'true');assert(visible(cards().find(c=>c.dataset.contestId===city.id)));
  set('sort','jurisdiction');assert.equal(groups().length,0);assert($('group-controls').hidden);set('sort','level');assert(groups().length>0);
  reset();set('search','CD-8');assert(text('panel-candidates').includes('$489,134.65'));assert(text('panel-candidates').includes('$20,073.00'));assert(text('panel-candidates').includes('September 30, 2026'));assert(text('panel-candidates').includes('October 6, 2026'));
  tab('sources');assert(nodes($('panel-sources')).some(n=>n.tagName==='A'&&n.href==='https://www.fec.gov/data/candidate/H0CA10149/'));
  reset();set('search','CD-10');assert(text('panel-candidates').includes('No published total available'));assert(text('panel-candidates').includes('not zero'));assert(!text('panel-candidates').includes('$0.00'));
  reset();set('search','Scott Wiener');assert(text('panel-candidates').includes('January 1, 2023'));assert(text('panel-candidates').includes('not verified as a January 2025 onward subtotal'));
  reset();set('search','CD-16');assert(text('panel-candidates').includes('$400.00'));
  $('download-filtered').click();const fundedExport=JSON.parse(await downloads.at(-1).blob.text());assert.equal(fundedExport.finance.currency,'USD');assert.equal(fundedExport.finance.checked_on,'2026-10-06');assert.equal(fundedExport.positions[0].candidates[1].fec.receipts,400);
  for(const county of original.election.counties_in_scope.map(c=>c.name)){reset();set('county',county);assert.equal(count(),original.positions.filter(p=>p.ballot_status==='confirmed'&&p.counties.includes(county)).length);}
  reset();set('county','San Mateo');set('search','CD-15');assert.equal(count(),1);assert(text('panel-candidates').includes('Kevin Mullin'));assert(text('detail-meta').includes('San Francisco + San Mateo'));
  reset();set('county','San Francisco');set('search','Ruth Ferguson');assert.equal(count(),1);assert(text('detail-meta').includes('Special election'));
  reset();set('county','San Mateo');clickStatus('unresolved');assert.equal(count(),2);
  reset();
  set('search','AD-18');assert.equal(count(),1);assert(text('detail-subtitle').includes('AD-18'));assert(text('panel-candidates').includes('Mia Bonta'));
  reset();set('search','CD-18');assert.equal(count(),1);assert(text('panel-candidates').includes('Zoe Lofgren'));
  reset();set('search','SD-10');assert.equal(count(),1);assert(text('detail-subtitle').includes('SD-10'));
  reset();set('search','San Jose');assert(count()>0,'Accent-insensitive search');
  reset();set('county','Alameda');const expectedAlameda=original.positions.filter(p=>p.ballot_status==='confirmed'&&p.counties.includes('Alameda')).length;assert.equal(count(),expectedAlameda);
  reset();set('county','Contra Costa');set('search','East Bay Regional Park District Ward 7');assert.equal(count(),1);assert(text('detail-status').includes('Confirmed on ballot'));assert(text('panel-candidates').includes('not verified'));assert(text('panel-candidates').includes('Mushda Faiez'));assert(cards()[0].textContent.includes('Roster unverified'));
  reset();set('county','Contra Costa');set('search','AD-11');assert.equal(count(),1);assert(text('panel-candidates').includes('No Party Preference'));
  reset();set('party','NPP');assert.equal(count(),2);
  reset();set('county','Contra Costa');set('search','AD-14');assert.equal(count(),1);assert(text('detail-meta').includes('Alameda + Contra Costa'));
  reset();set('county','Contra Costa');set('search','East Bay Municipal Utility District Ward 3');assert.equal(count(),1);assert(text('detail-meta').includes('Alameda + Contra Costa'));
  reset();set('party','R');assert(count()>0);for(const card of cards()){const p=original.positions.find(p=>p.id===card.dataset.contestId);assert(p.candidates.some(c=>c.party==='R'));}
  reset();$('incumbents').checked=true;$('incumbents').fire('change');assert(count()>0);for(const card of cards()){const p=original.positions.find(p=>p.id===card.dataset.contestId);assert([...(p.candidates||[]),...(p.filed_candidates_not_confirmed_on_ballot||[])].some(c=>c.incumbent));}
  reset();clickStatus('unresolved');assert.equal(count(),original.coverage.unresolved_scheduled_contests);assert(text('panel-candidates').includes('not been confirmed'));
  set('search','Dublin');assert(count()>0);assert(text('panel-candidates').includes('Provisional filing names'));
  reset();set('search','Orchard');assert.equal(count(),1);assert(text('panel-candidates').includes('Hina Patel'));assert(text('panel-candidates').includes('Qualified write-in candidates'));
  tab('sources');assert(text('panel-sources').includes('Open Civic Data'));assert(text('panel-sources').includes('Research notes'));assert(text('panel-sources').includes('Sources'));
  tab('json');assert(text('panel-json').includes('note_ids'));
  reset();set('search','does-not-exist-349823');assert.equal(count(),0);assert(text('result-list').includes('No contests match'));assert.equal($('download-filtered').disabled,true);
  reset();set('search','AD-18');$('download-filtered').click();const filtered=JSON.parse(await downloads.at(-1).blob.text());assert.equal(filtered.positions.length,1);assert.equal(filtered.coverage.confirmed_contests,1);assert.equal(filtered.coverage.printed_candidate_entries,2);assert.equal(filtered.coverage.status,'filtered_view_of_research_inventory');
  $('download-all').click();const full=JSON.parse(await downloads.at(-1).blob.text());assert.deepEqual(full,original);assert.equal(downloads.at(-1).filename,'2026-11-03_Bay_Area_Elections.json');
  $('download-schema').click();assert.equal(downloads.at(-1).filename,'elections.schema.json');const schema=JSON.parse(await downloads.at(-1).blob.text());assert.equal(schema.$schema,'https://json-schema.org/draft/2020-12/schema');
  fs.writeFileSync(generated+'explorer_filtered_test.json',JSON.stringify(filtered,null,2)+'\n');
  const report={passed:true,environment:'Minimal DOM integration harness; not a browser rendering test',checks:['Script initializes every confirmed contest','Senate, Assembly, then statewide offices; numeric congressional district order','Expandable sections, individual collapse, expand/collapse all, search and hash reveal','Alternative flat sorts','FEC receipt amounts, different cutoff dates, unavailable totals, period exception, sources and filtered export','AD/CD/SD search finds correct seats','Diacritic-insensitive SanJose search','All five county scopes and shared CD-15, AD-14 and EBMUD Ward 3 coverage', 'Special election label and San Mateo unresolved subset', 'Party and incumbent filters match dataset, including NPP','Unresolved contests distinctly shown; confirmed Ward 7 has an explicitly unverified roster','Provisional and write-in rosters labeled separately','Notes and source registry resolution','Raw JSON and empty search states','Full-data and schema download bytes match','Filtered export recalculates coverage'],alameda_confirmed:expectedAlameda,filtered_download:filtered.positions[0].id};
  fs.writeFileSync(generated+'explorer_test_report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
