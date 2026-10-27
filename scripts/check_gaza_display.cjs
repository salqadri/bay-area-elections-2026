'use strict';
// Fixed source-shaped cases verify the shared renderer independently of live grades.
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert/strict');
const display = vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/gaza-evidence-display.js'), 'utf8') + '\nGazaEvidenceDisplay', {URL,URLSearchParams});
class Element {
  constructor(tag, cls, text) { this.tagName=tag.toUpperCase();this.className=cls||'';this.children=[];this.attrs={};this.open=false;if(text!==undefined&&text!==null)this.children.push(String(text)); }
  append(...children) { for(const child of children){this.children.push(child);if(typeof child==='object')child.parent=this;} }
  get textContent() { return this.children.map(c=>typeof c==='string'?c:c.textContent).join(''); }
  setAttribute(key, value) { this.attrs[key]=String(value); }
  set innerHTML(value) { throw Error('Evidence must be rendered as text, never HTML'); }
}
const node=(tag,cls,text)=>new Element(tag,cls,text);
const link=(url,text,cls)=>{const result=node('a',cls,text);result.href=url;return result;};
const evidenceDateLabel=e=>e.date_method==='source_observed'?'Observed on '+e.date+' (guide snapshot; original date unknown)':e.date;
const helpers={node,link,dateLabel:value=>value,evidenceDateLabel};
const all=n=>[n,...n.children.filter(c=>typeof c==='object').flatMap(all)];
const data={
  uscpr_scorecard:{provider:'USCPR Action',checked_on:'2026-10-14',source_url:'https://www.uscpraction.org/scorecard',methodology_url:'https://www.uscpraction.org/methodology',scope_note:'Publisher scope: Democratic Caucus; current Congress and publisher lifetime periods differ.'},
  gaza_voting:{provider:'Source sheet',checked_on:'2026-10-14',source_url:'https://docs.google.com/spreadsheets/d/fixture/edit',scope_note:'Selected 118th and 119th Congress votes, sponsorships and letters; a source snapshot rather than a complete career history.',actions:{
    block:{title:'Block weapons transfer',kind:'roll_call_vote',date_label:'April 15, 2026',sheet_column:'F',sheet_url:'https://docs.google.com/spreadsheets/d/fixture/edit#range=F1',source_url:'https://www.senate.gov/legislative/fixture'},
    aid:{title:'Military aid package',kind:'roll_call_vote',date_label:'June 24, 2011',sheet_url:'https://docs.google.com/spreadsheets/d/fixture/edit#range=G4'},
    letter:{title:'Humanitarian letter',kind:'letter',date_label:'2023-2025'},
    committee:{title:'Committee amendment',kind:'committee_vote',date_label:'September 18, 2025'},
    sponsor:{title:'Ceasefire resolution',kind:'sponsorship',date_label:'2023-2025'}
  }}
};
const record=(congress,actions)=>({record_id:'fixture-'+congress,member_name:'Source Member',chamber:'House',district:'CA-19',state:'CA',congress,checked_on:'2026-10-14',source_url:data.gaza_voting.source_url,sheet_title:congress+'th House',sheet_row:4,actions});
const candidate={
  uscpr_grade:{name:'Source Member',grades:[{period:'119th Congress',grade:'F',source_grade:'F',score:7},{period:'Lifetime',grade:'D',source_grade:'D',score:25}],checked_on:'2026-10-14',source_url:data.uscpr_scorecard.source_url},
  gaza_voting_records:[record(119,[
    {action_id:'block',value:'No',assessment:'positive',sheet_color:'#d9ead3',assessment_basis:'sheet_dropdown',note:'Source member cell note.',source_url:'https://example.org/member-action'},
    {action_id:'aid',value:'Yes',assessment:'negative',sheet_color:'#f4cccc'},
    {action_id:'committee',value:'Not on committee',assessment:'neutral',sheet_color:'#cccccc'}
  ]),record(118,[
    {action_id:'letter',value:'Not signing',assessment:'negative',sheet_color:'#f4cccc'},
    {action_id:'sponsor',value:'Yes',assessment:'unclassified',sheet_color:null}
  ])],
  gaza_platform:{status:'no_statement_found',checked_on:'2026-10-14',scope_note:'Homepage and linked issues pages reviewed; this does not establish a position.',pages:[{url:'https://example.org/issues',title:'Issues',content_sha256:'a'.repeat(64)}]},
  gaza_evidence:[{date:'2026-10-09',date_method:'source_observed',date_note:'Historical guide assessment; original date unknown.',summary:'Guide reports a ceasefire position.',url:'https://example.org/guide'}]
};
const card=display.render(candidate,data,helpers);
assert.equal(card.tagName,'DETAILS');assert.equal(card.open,false);
assert.equal(card.className,'candidate-evidence gaza-evidence');
assert(card.textContent.includes('Source member: Source Member · CA-19'),'Prior/current member district stays visible');
for(const expected of ['Gaza evidence','USCPR Grade','119th Congress: F · 7%','Lifetime: D · 25%','publisher assessment','Congressional voting / legislative record','119th House tracker tab · 3 tracked actions','118th House tracker tab · 2 tracked actions','Source Member','Snapshot checked 2026-10-14','Recorded vote','Committee vote','Sponsorship','Letter','April 15, 2026','June 24, 2011','Not on committee','Not signing','Sheet: positive','Sheet: negative','Sheet: neutral','Sheet: unclassified','Campaign platform','No Israel / Palestine platform statement found in the reviewed pages.','Web, social and guide evidence','guide snapshot; original date unknown','Historical guide assessment']) assert(card.textContent.includes(expected),expected);
const records=all(card).filter(n=>n.className==='gaza-record');assert.equal(records.length,2);assert(records.every(n=>!n.open));
assert.equal(records[0].children[0].textContent,'Dated actions · 3');assert.equal(records[1].children[0].textContent,'Period-only or undated actions · 2');
assert(card.textContent.includes('Source member cell note.'));
assert(all(card).some(n=>n.href==='https://example.org/member-action'));
assert(all(card).some(n=>n.attrs.title==='Source dropdown color'));
const actions=all(card).filter(n=>n.className==='gaza-action');assert.equal(actions.length,5,'Every tracked action must be available');
assert(actions[0].textContent.includes('No'));assert(all(actions[0]).some(n=>n.className==='gaza-assessment positive'),'Positive color comes from the source assessment even for a No');
const aidAction=actions.find(a=>a.textContent.includes('Military aid package'));assert(aidAction.textContent.includes('Yes'));assert(all(aidAction).some(n=>n.className==='gaza-assessment negative'),'A Yes is not automatically positive');
assert.deepEqual(actions.map(a=>a.children[0].textContent),['Block weapons transfer','Committee amendment','Military aid package','Humanitarian letter','Ceasefire resolution']);
assert(all(actions[4]).some(n=>n.className==='gaza-assessment unclassified'),'Unknown colors stay unclassified');
assert(all(card).some(n=>n.href===data.uscpr_scorecard.methodology_url));
assert(all(card).some(n=>n.href===data.gaza_voting.actions.block.source_url));
assert(all(card).some(n=>n.href==='https://docs.google.com/spreadsheets/d/fixture/edit#range=F4'));
assert(all(card).some(n=>n.href===candidate.gaza_platform.pages[0].url));

const na=display.render({uscpr_grade:{grades:[{period:'119th Congress',grade:null,source_grade:'N/A',score:null}]}},data,helpers);
assert(na.textContent.includes('Not graded (publisher: N/A)'));assert(!na.textContent.includes('Congress: F'));
const onlyVotes=display.render({gaza_voting_records:candidate.gaza_voting_records},data,helpers);
assert(onlyVotes.textContent.includes('No USCPR grade has been captured'),'Absent profile stays explicitly unknown');
assert(!onlyVotes.textContent.includes('Congress: F'),'No publisher profile is never an inferred F');
for(const status of ['unavailable','no_website','no_statement_found']) {
  const platform=display.render({gaza_platform:{status,checked_on:'2026-10-14',scope_note:'Limited review.',pages:[]}},data,helpers);
  assert(platform.textContent.includes('Campaign platform'));assert(!platform.textContent.toLowerCase().includes('neutral'));
  if(status==='no_website') assert(platform.textContent.includes('No verified campaign website is recorded in this inventory.'),'A missing URL is an inventory limitation, not a finding that no website exists');
  if(status==='unavailable') assert(platform.textContent.includes('review unavailable or incomplete'),'Unreviewed sites must not be described as completed failed inspections');
}
const found=display.render({gaza_platform:{status:'statement_found',checked_on:'2026-10-14',scope_note:'Issues page.',summary:'Calls for a ceasefire with conditions.',quote:'<img src=x onerror=alert(1)>',source_url:'javascript:alert(1)',pages:[{url:'data:text/html,test',title:'Unsafe page'}]},gaza_evidence:[{date:'2026-10-01',summary:'<script>literal text</script>',url:'javascript:alert(2)'}]},data,helpers);
assert(found.textContent.includes('Calls for a ceasefire with conditions.'));assert(found.textContent.includes('<img src=x'));
assert.equal(all(found).filter(n=>n.tagName==='IMG'||n.tagName==='SCRIPT').length,0);
assert.equal(all(found).filter(n=>n.tagName==='A').length,0,'Unsafe URLs must not reach even an unguarded link helper');
assert(found.textContent.includes('link unavailable'));
assert.equal(display.render({},data,helpers),null);
const ballot=display.render(candidate,data,{...helpers,className:'ballot-candidate-evidence'});assert.equal(ballot.className,'ballot-candidate-evidence');
// Evidence renders newest-first across mixed date precisions; undated items keep input order at the end.
const sorted=display.render({gaza_evidence:[
  {date:'2024',summary:'Year-only oldest.',url:'https://example.org/y2024'},
  {date:'2026-10-09',summary:'Day newest A.',url:'https://example.org/a'},
  {date:'2025-03',summary:'Month middle.',url:'https://example.org/m'},
  {date:'2026-10-09',summary:'Day newest B (tie keeps order).',url:'https://example.org/b'}
]},data,helpers);
const webItems=all(sorted).filter(n=>n.className==='gaza-web-item').map(n=>n.textContent);
assert.equal(webItems.length,4);
assert(webItems[0].includes('Day newest A')&&webItems[1].includes('Day newest B'),'Same-date items keep their original relative order');
assert(webItems[2].includes('Month middle')&&webItems[3].includes('Year-only oldest'),'Descending by date across precisions');
console.log('Shared Gaza display: attributed grade periods, every tracked action, source assessment colors and text, platform statuses, dated evidence, safe links and collapsed disclosures passed.');

// Calendar parsing is the same contract as the Python Jev builder; no locale parsing.
const dateFixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'../research/gaza-records/action-date-fixtures.json'),'utf8'));
for(const fixture of dateFixtures){const parsed=JSON.parse(JSON.stringify(display.actionDate(fixture.input)));assert.deepEqual(parsed,fixture.expected);}
const crossCandidate={gaza_voting_records:[record(119,[{action_id:'aid',value:'Yes',assessment:'negative'}]),record(118,[{action_id:'block',value:'No',assessment:'positive'}])]};
const beforeCross=JSON.stringify(crossCandidate),cross=display.render(crossCandidate,data,helpers);
assert.deepEqual(all(cross).filter(n=>n.className==='gaza-action').map(n=>n.children[0].textContent),['Block weapons transfer','Military aid package']);
assert.equal(JSON.stringify(crossCandidate),beforeCross);
assert(cross.textContent.includes('118th House')&&cross.textContent.includes('119th House'));
console.log('PASS Legislative ordering: cross-tab newest-first, historical actions retained, periods separate, date-parser parity and immutable source records.');
