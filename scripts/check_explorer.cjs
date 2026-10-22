const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const path = require('path');
const root = path.resolve(__dirname, '..') + path.sep;
const generated = path.join(root, '.checks') + path.sep;
const fixture = JSON.parse(fs.readFileSync(generated + 'explorer_dom_fixture.json'));
const original = JSON.parse(fs.readFileSync(root + '2026-11-03_Bay_Area_Elections.json'));
// Mirror the page's own long-date rendering so refreshes of finance.checked_on never break this harness.
const longDate = value => new Date(value+'T12:00:00').toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'});
const checkedLong = longDate(original.finance.checked_on);
const money = value => new Intl.NumberFormat('en-US',{style:'currency',currency:original.finance.currency}).format(value);
const candidate = name => original.positions.flatMap(p=>p.candidates||[]).find(c=>c.name===name);
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
  assert.deepEqual($('county').options.map(option=>option.value).sort(),['',...original.election.counties_in_scope.map(county=>county.name)].sort(),'County selector must contain All plus exactly the registered researched counties');
  assert.equal(count(),original.positions.length,'Unfiltered default shows every researched contest, nationwide included');assert(text('notice-text').includes(original.coverage.unresolved_scheduled_contests+' unresolved'));assert(text('result-meta').includes(original.coverage.printed_candidate_entries+' printed'));
  assert(text('hero-subtitle').includes('Contra Costa'));assert(text('hero-subtitle').includes('San Francisco, San Mateo, and Santa Clara'));
  assert.deepEqual(groups().filter(n=>!n.dataset.sectionKey.includes('/')).map(n=>n.dataset.sectionKey),original.display_order.levels);
  assert.deepEqual(groups().filter(n=>n.dataset.sectionKey.startsWith('Federal/')).map(n=>n.dataset.sectionKey),['Federal/U.S. Senate','Federal/U.S. House'],'The Federal section groups Senate first, then House');
  const federalPositions=cardPositions().filter(p=>p.government_level==='Federal');
  assert.deepEqual([...new Set(federalPositions.map(p=>p.office_category))],['U.S. Senate','U.S. House'],'Every printed federal contest follows the Senate-then-House order');
  const caHouse=federalPositions.filter(p=>p.office_category==='U.S. House'&&(p.jurisdiction_ocd_division_id||'').includes('state:ca')).map(p=>p.district_or_seat);
  assert.deepEqual(caHouse.filter(d=>['CD-8','CD-9','CD-10','CD-11','CD-12','CD-14','CD-15','CD-16','CD-17','CD-18','CD-19'].includes(d)),['CD-8','CD-9','CD-10','CD-11','CD-12','CD-14','CD-15','CD-16','CD-17','CD-18','CD-19'],'California districts keep numeric order inside the House block');
  const houseDistricts=federalPositions.filter(p=>p.office_category==='U.S. House').map(p=>p.district_or_seat);
  assert(houseDistricts.length>=60,'The nationwide in-play House races appear in the House block');
  assert(federalPositions.filter(p=>p.office_category==='U.S. Senate'&&p.district_or_seat.includes('Statewide')).length>=35,'Unfiltered view must include the nationwide Senate statewide seats');
  set('level','State');const statePositions=cardPositions();assert.equal(statePositions[0].office,'Governor','The governors race leads the State section');
  assert.ok(!statePositions.some((p,i)=>i&&p.office==='Governor'&&statePositions[i-1].office!=='Governor'),'All governor races stay contiguous at the top');
  const govEnd=statePositions.findIndex(p=>p.office!=='Governor');
  assert.equal(statePositions[govEnd].office_category,'State Senate','State Senate follows the Governor block');
  assert.ok(statePositions.slice(govEnd).findIndex(p=>p.office_category==='State Assembly')<statePositions.slice(govEnd).findIndex(p=>p.office==='Lieutenant Governor'),'The assembly precedes other statewide offices');
  assert.deepEqual(groups().filter(n=>n.dataset.sectionKey.startsWith('State/')).map(n=>n.dataset.sectionKey),['State/Governor','State/State Senate','State/State Assembly','State/Other state offices']);
  $('collapse-sections').click();assert(groups().every(n=>!n.open));assert.equal(cards().filter(visible).length,0);
  $('expand-sections').click();assert(groups().every(n=>n.open));assert.equal(cards().filter(visible).length,cards().length);
  const assemblyGroup=groups().find(n=>n.dataset.sectionKey==='State/State Assembly');assemblyGroup.open=false;assemblyGroup.fire('toggle');assert(!visible(cards().find(n=>n.textContent.includes('AD-18'))));
  set('search','AD-18');assert.equal(count(),1);assert(groups().every(n=>n.open));assert(visible(cards()[0]));
  reset();$('collapse-sections').click();const city=original.positions.find(p=>p.government_level==='City or town'&&p.ballot_status==='confirmed');location.hash='#id='+city.id;window.events.hashchange();assert.equal(cards().find(c=>c.dataset.contestId===city.id).getAttribute('aria-pressed'),'true');assert(visible(cards().find(c=>c.dataset.contestId===city.id)));
  set('sort','jurisdiction');assert.equal(groups().length,0);assert($('group-controls').hidden);set('sort','level');assert(groups().length>0);
  reset();set('search','CD-8');for(const c of original.positions.find(p=>p.district_or_seat==='CD-8').candidates){if(c.fec.receipts!==null){assert(text('panel-candidates').includes(money(c.fec.receipts)));assert(text('panel-candidates').includes(longDate(c.fec.through)));}}assert(text('panel-candidates').includes(checkedLong));
  assert(text('panel-candidates').includes('Endorsed by JStreetPAC'));
  assert(text('panel-candidates').includes('Supported by California Jewish Democrats · Source rating: Support'));
  assert(!text('panel-candidates').includes('Endorsed by California Jewish Democrats'));
  tab('sources');assert(nodes($('panel-sources')).some(n=>n.tagName==='A'&&n.href==='https://www.fec.gov/data/candidate/H0CA10149/'));
  reset();set('search','CD-10');const frese=candidate('Jeff Frese');if(frese.fec.receipts===null){assert(text('panel-candidates').includes('No published total available'));assert(text('panel-candidates').includes('not zero'));}else assert(text('panel-candidates').includes(money(frese.fec.receipts)));
  assert(text('panel-candidates').includes('Endorsed by CAIR Action'));assert(nodes($('panel-candidates')).some(n=>n.tagName==='A'&&n.href==='https://cairactionguide.org/explore'));
  assert(text('panel-candidates').includes('supplied capture of CAIR Action'));
  reset();set('search','Marc Cooper');assert(text('panel-candidates').includes('Opposed by CAIR Action'));assert(text('panel-candidates').includes('1 opposed'));assert(!text('panel-candidates').includes('Endorsed by CAIR Action'));reset();set('search','CD-8');assert(text('panel-candidates').includes('Preferred by CAIR Action'));
  reset();set('search','CD-11');assert(text('panel-candidates').includes('Listed as Ally by Vote for Peace'));assert(text('panel-candidates').includes('Opposed by Vote for Peace'));assert(!text('panel-candidates').includes('Endorsed by Vote for Peace'));assert(text('panel-candidates').includes('Endorsed by AROC Action'));assert(text('panel-candidates').includes('Observed on 2026-10-09 (guide snapshot; original date unknown)'));
  reset();set('search','Manisha Pathak');assert(text('panel-candidates').includes('Supported by Dr. Romesh Japra'));
  assert(text('panel-candidates').includes('Endorsed by Americans4Hindus'));
  assert(!text('panel-candidates').includes('Endorsed by Dr. Romesh Japra'));
  reset();set('search','Murali Srinivasan');assert(text('panel-candidates').includes('Endorsed by Hindu American PAC'));assert(text('panel-candidates').includes('Historical record (prior race)'));assert(text('panel-candidates').includes('2022 candidacy'));assert(!text('panel-candidates').includes('(2026 cycle)'));
  reset();set('search','Yang Shao');assert(text('panel-candidates').includes('Endorsed by Hindu American PAC'));assert(text('panel-candidates').includes('Fremont City Council'));assert(text('panel-candidates').includes('not an office-specific endorsement'));
  reset();set('search','Kevin Mullin');assert(text('panel-candidates').includes('Supported by United Democracy Project'));assert(text('panel-candidates').includes('Historical record (prior race)'));assert(!text('panel-candidates').includes('Endorsed by AIPAC PAC'));
  reset();set('search','Scott Wiener');assert(text('panel-candidates').includes('January 1, 2023'));assert(text('panel-candidates').includes('not verified as a January 2025 onward subtotal'));
  const wienerIE=candidate('Scott Wiener').independent_expenditures;assert(text('panel-candidates').includes('Independent outside spending · FEC 2026 cycle'));if(wienerIE.for_total>0)assert(text('panel-candidates').includes('For: '+money(wienerIE.for_total)));if(wienerIE.against_total>0)assert(text('panel-candidates').includes('Against: '+money(wienerIE.against_total)));
  if(wienerIE.items.length){const spender=original.ie_spenders[wienerIE.items[0].spender_id];assert(all().some(n=>n.tagName==='A'&&n.href===spender.source_url),'Spender names must link to their FEC committee page');}assert(nodes($('panel-candidates')).some(n=>n.tagName==='A'&&String(n.href).includes('/data/independent-expenditures/')&&String(n.href).includes('candidate_id=H8CA11116')),'Candidate IE browse link required');
  const moneyDetails=all().filter(n=>n.tagName==='DETAILS'&&n.children.some(c=>typeof c==='object'&&(c.className==='ie-spend'||c.className==='fundraising')));assert(moneyDetails.length>0,'Campaign money must render inside a collapsible details block');assert(moneyDetails.every(d=>!d.open),'The campaign money section must start collapsed');
  reset();set('search','Jeff Frese');if(!frese.independent_expenditures.items.length)assert(text('panel-candidates').includes('No independent expenditures in the FEC regular-report totals for this two-year cycle.'));
  reset();set('search','CD-16');const soule=candidate('Peter Sundin Soulé');if(soule.fec.receipts!==null)assert(text('panel-candidates').includes(money(soule.fec.receipts)));
  $('download-filtered').click();const fundedExport=JSON.parse(await downloads.at(-1).blob.text());assert.equal(fundedExport.finance.currency,'USD');assert.equal(fundedExport.finance.checked_on,original.finance.checked_on);assert.equal(fundedExport.positions[0].candidates.find(c=>c.name===soule.name).fec.receipts,soule.fec.receipts);
  for(const county of original.election.counties_in_scope.map(c=>c.name)){reset();set('county',county);assert.equal(count(),original.positions.filter(p=>p.counties.includes(county)).length);}
  reset();set('county','San Mateo');set('search','CD-15');assert.equal(count(),1);assert(text('panel-candidates').includes('Kevin Mullin'));assert(text('detail-meta').includes('San Francisco + San Mateo'));
  reset();set('county','San Francisco');set('search','Ruth Ferguson');assert.equal(count(),1);assert(text('detail-meta').includes('Special election'));
  // October 14, 2026: the last two San Mateo unresolved contests (Bayshore ESD short term, Colma Fire PD) resolved to excluded; no county has unresolved records left.
  reset();set('county','San Mateo');clickStatus('unresolved');assert.equal(count(),0);assert(text('result-list').includes('No contests match'));
  reset();
  set('search','AD-18');assert.equal(count(),1);assert(text('detail-subtitle').includes('AD-18'));assert(text('panel-candidates').includes('Mia Bonta'));
  reset();set('search','CD-18');assert.equal(count(),1);assert(text('panel-candidates').includes('Zoe Lofgren'));
  reset();set('search','SD-10');assert.equal(count(),1);assert(text('detail-subtitle').includes('SD-10'));
  reset();set('search','San Jose');assert(count()>0,'Accent-insensitive search');
  reset();set('county','Alameda');const expectedAlameda=original.positions.filter(p=>p.counties.includes('Alameda')).length;assert.equal(count(),expectedAlameda);
  reset();set('county','Contra Costa');set('search','East Bay Regional Park District Ward 7');assert.equal(count(),1);assert(text('detail-status').includes('Confirmed on ballot'));assert(text('panel-candidates').includes('Colin J. Coffey'));assert(text('panel-candidates').includes('Sekhon'));assert(cards()[0].textContent.includes('2 candidates'));assert(text('panel-candidates').includes('Mushda Faiez'));assert(text('panel-candidates').includes('Provisional filing names'));
  reset();set('county','Contra Costa');set('search','AD-11');assert.equal(count(),1);assert(text('panel-candidates').includes('No Party Preference'));
  reset();set('party','NPP');{const nppExpected=original.positions.filter(p=>[...(p.candidates||[]),...(p.filed_candidates_not_confirmed_on_ballot||[])].some(c=>c.party==='NPP')).length;assert.equal(count(),nppExpected,'The NPP filter matches every contest with an NPP candidacy');}
  reset();set('county','Contra Costa');set('search','AD-14');assert.equal(count(),1);assert(text('detail-meta').includes('Alameda + Contra Costa'));
  reset();set('county','Contra Costa');set('search','East Bay Municipal Utility District Ward 3');assert.equal(count(),1);assert(text('detail-meta').includes('Alameda + Contra Costa'));
  reset();set('party','R');assert(count()>0);for(const card of cards()){const p=original.positions.find(p=>p.id===card.dataset.contestId);assert([...(p.candidates||[]),...(p.filed_candidates_not_confirmed_on_ballot||[])].some(c=>c.party==='R'));}
  reset();$('incumbents').checked=true;$('incumbents').fire('change');assert(count()>0);for(const card of cards()){const p=original.positions.find(p=>p.id===card.dataset.contestId);assert([...(p.candidates||[]),...(p.filed_candidates_not_confirmed_on_ballot||[])].some(c=>c.incumbent));}
  // October 20, 2026: official-source reconciliation all waves confirmed 70 of the 70 nationwide Senate/governor contests; the unresolved filter is now empty. Every Bay Area contest remains finally resolved.
  reset();clickStatus('unresolved');assert.equal(count(),original.coverage.unresolved_scheduled_contests);assert.equal(original.coverage.unresolved_scheduled_contests,0);for(const card of cards()){const p=original.positions.find(p=>p.id===card.dataset.contestId);assert.deepEqual(p.counties,[]);assert(['U.S. Senate','Statewide executive'].includes(p.office_category));}
  reset();clickStatus('unresolved');set('county','Alameda');assert.equal(count(),0);assert(text('result-list').includes('No contests match'));
  // October 13, 2026: Dublin USD Area 2 moved from unresolved to excluded (registrar Not On Ballot), so the provisional-filing render is asserted on that record via status=all + filer search.
  reset();clickStatus('all');set('search','Holden Lomeli');assert.equal(count(),1);assert(text('detail-status').includes('Confirmed not on ballot'));assert(text('panel-candidates').includes('Provisional filing names'));
  reset();set('search','Orchard');assert.equal(count(),1);assert(text('panel-candidates').includes('Hina Patel'));assert(text('panel-candidates').includes('Qualified write-in candidates'));
  tab('sources');assert(text('panel-sources').includes('Open Civic Data'));assert(text('panel-sources').includes('Research notes'));assert(text('panel-sources').includes('Sources'));
  tab('json');assert(text('panel-json').includes('note_ids'));
  reset();set('search','does-not-exist-349823');assert.equal(count(),0);assert(text('result-list').includes('No contests match'));assert.equal($('download-filtered').disabled,true);
  reset();set('search','AD-18');$('download-filtered').click();const filtered=JSON.parse(await downloads.at(-1).blob.text());assert.equal(filtered.positions.length,1);assert.equal(filtered.coverage.confirmed_contests,1);assert.equal(filtered.coverage.printed_candidate_entries,2);assert.equal(filtered.coverage.status,'filtered_view_of_research_inventory');
  const subsetCandidates=filtered.positions.flatMap(p=>p.candidates||[]);
  for(const [metric,key] of [['printed_candidates_with_x_url','x_url'],['printed_candidates_with_secondary_x_url','secondary_x_url'],['printed_candidates_with_campaign_url','campaign_url'],['printed_candidates_with_gaza_evidence','gaza_evidence'],['printed_candidates_with_gaza_voting_records','gaza_voting_records'],['printed_candidates_with_uscpr_grade','uscpr_grade'],['printed_candidates_with_gaza_platform','gaza_platform'],['printed_candidates_with_endorsements','endorsements']]) {
    assert.equal(filtered.coverage[metric],subsetCandidates.filter(c=>Array.isArray(c[key])?c[key].length:!!c[key]).length,metric+' must describe the downloaded subset');
  }
  reset();set('search','CD-11');
  assert(text('panel-candidates').includes('archive bound; original date unknown'),'Archive bounds must not look like publication dates');
  assert(text('panel-candidates').includes('(page metadata date)'),'Page metadata dates must be labeled in the rendered evidence');
  const recordContest=original.positions.find(p=>(p.candidates||[]).some(c=>c.gaza_voting_records?.length&&c.uscpr_grade));
  assert(recordContest,'Published voting records and official publisher grades must have matched candidates');
  const recordCandidate=recordContest.candidates.find(c=>c.gaza_voting_records?.length&&c.uscpr_grade);
  reset();set('search',recordContest.id);
  const recordMain=nodes($('panel-candidates')).find(n=>n.className==='candidate-name'&&n.textContent===recordCandidate.name).parent;
  const gazaDetails=recordMain.children.filter(n=>typeof n==='object'&&n.className==='candidate-evidence gaza-evidence');
  assert.equal(gazaDetails.length,1,'All Gaza layers share one disclosure');assert(!gazaDetails[0].open);
  const gaza=gazaDetails[0];assert(gaza.textContent.includes('USCPR Grade'));assert(gaza.textContent.includes('Congressional voting / legislative record'));
  for(const grade of recordCandidate.uscpr_grade.grades) assert(gaza.textContent.includes(grade.period+': '+(grade.grade||'Not graded')));
  assert.equal(nodes(gaza).filter(n=>n.className==='gaza-action').length,recordCandidate.gaza_voting_records.reduce((n,r)=>n+r.actions.length,0),'Every tracked source action is rendered');
  assert(nodes(gaza).filter(n=>n.className==='gaza-record').every(n=>!n.open));
  assert(nodes(gaza).some(n=>n.tagName==='A'&&n.href===original.uscpr_scorecard.methodology_url));
  for(const record of recordCandidate.gaza_voting_records) for(const item of record.actions) assert(gaza.textContent.includes(original.gaza_voting.actions[item.action_id].title));
  $('download-all').click();const full=JSON.parse(await downloads.at(-1).blob.text());assert.deepEqual(full,original);assert.equal(downloads.at(-1).filename,'2026-11-03_Bay_Area_Elections.json');
  $('download-schema').click();assert.equal(downloads.at(-1).filename,'elections.schema.json');const schema=JSON.parse(await downloads.at(-1).blob.text());assert.equal(schema.$schema,'https://json-schema.org/draft/2020-12/schema');
  fs.writeFileSync(generated+'explorer_filtered_test.json',JSON.stringify(filtered,null,2)+'\n');
  const report={passed:true,environment:'Minimal DOM integration harness; not a browser rendering test',checks:['Script initializes every confirmed contest','Senate, Assembly, then statewide offices; numeric congressional district order','Expandable sections, individual collapse, expand/collapse all, search and hash reveal','Alternative flat sorts','FEC receipt amounts, different cutoff dates, unavailable totals, period exception, sources and filtered export','AD/CD/SD search finds correct seats','Diacritic-insensitive SanJose search','All registered county scopes and shared CD-15, AD-14 and EBMUD Ward 3 coverage', 'Special election label and San Mateo unresolved subset', 'Party and incumbent filters match dataset, including NPP','Unresolved contests distinctly shown; confirmed Ward 7 has an explicitly unverified roster','Provisional and write-in rosters labeled separately','Notes and source registry resolution','Raw JSON and empty search states','Full-data and schema download bytes match','Filtered export recalculates all enrichment coverage fields','Evidence dates distinguish archive bounds from publication dates','One collapsed Gaza disclosure separates publisher grades from every tracked Congressional action and keeps methodology links'],alameda_confirmed:expectedAlameda,filtered_download:filtered.positions[0].id};
  fs.writeFileSync(generated+'explorer_test_report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
