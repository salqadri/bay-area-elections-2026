const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const C=require('../src/jev-playground/core.js');
const qs={custom:{type:'score',criteria:['low','high','top']},other:{type:'choice',criteria:{yes:'Yes',no:'No'}},binary:{type:'noul'}};
assert.deepEqual(C.parseQuestions(JSON.stringify(qs)),qs);assert.throws(()=>C.parseQuestions('[]'));assert.throws(()=>C.parseQuestions('{}'));assert.throws(()=>C.parseQuestions('{"x":{"type":"choice","criteria":[]}}'));
assert.equal(C.answerValue({type:'choice',choice:'F',confidence:0.01},qs.other),'F');assert.equal(C.percent(0.01),'1%');assert.equal(C.percent(0),'0%');
assert.equal(C.answerValue({type:'score',score:1.25},qs.custom),'1.25 / 2');assert.equal(C.answerValue({type:'noul',noul:.47},qs.binary),'47% true');
const races=[{id:'2',state:'CA',district_or_seat:'CD-17'},{id:'1',state:'CA',district_or_seat:'CD-1'},{id:'3',state:'TX',district_or_seat:'CD-35'}];assert.deepEqual(C.sortRaces(races).map(r=>r.id),['1','2','3']);
const request={state:{candidate:'Alice'},questions:qs};const run={id:'run',rows:[{id:'a',request,status:'queued'}]};const merged=C.mergeDelta(run,{id:'run',status:'complete',revision:1,changes:[{id:'a',status:'complete',response:{answers:{other:{type:'choice',choice:'no',confidence:0}}}}]});
assert.equal(merged.rows[0].request,request);assert.equal(merged.rows[0].response.answers.other.confidence,0);assert.equal(run.rows[0].status,'queued');assert.throws(()=>C.mergeDelta(run,{id:'another',changes:[]}));
const html=fs.readFileSync(path.join(__dirname,'../src/jev-playground/index.html'),'utf8');assert(html.includes('State JSON'));assert(html.includes('Full request'));assert(html.includes('role="status"'));assert(html.includes('no confidence cutoffs'));
console.log('PASS Jev playground: custom questions, confidence without thresholds, numeric district order, immutable state and run deltas.');

// A single experiment cannot inherit baseline answers for its unrun peers.
const snapshot={races,candidates:[{id:'a',position_id:'1',candidate:'Alice',state:{candidate:'Alice'}},{id:'b',position_id:'2',candidate:'Bob',state:{candidate:'Bob'}}]};
const single={id:'single',races,rows:[{id:'a',position_id:'1',request,status:'complete',response:{answers:{}}}]};
const catalog=C.catalogRows(snapshot,single);assert.equal(catalog.length,2);assert.equal(catalog[0],single.rows[0]);assert.equal(catalog[1].status,'preview');assert.equal(catalog[1].response,undefined);assert.equal(catalog[1].request,undefined);assert.equal(snapshot.candidates[0].status,undefined);
assert.deepEqual(C.catalogRaces(snapshot,single),races);
const historical={...single,rows:[{id:'removed',candidate:'Removed',status:'complete',request}]};assert.equal(C.catalogRows(snapshot,historical).at(-1).request,request);
assert(html.includes('id="run-selected"'));console.log('PASS Single-candidate catalog: exact evaluated inputs, unrun previews, historical candidates and no inherited answers.');

const distribution={type:'choice',choice:'yes',confidence:.12,probabilities:{no:.8,yes:.2,unknown:0}};
const probabilities=C.probabilityRows(distribution,{criteria:{yes:'Submitted yes criterion',no:'Submitted no criterion',unknown:'Unknown'}});
assert.deepEqual(probabilities.map(p=>p.key),['no','yes','unknown']);assert.equal(probabilities[1].selected,true);assert.equal(probabilities[0].selected,false);assert.equal(probabilities[1].label,'Submitted yes criterion');assert.equal(probabilities[2].probability,0);assert.equal(distribution.confidence,.12);
assert.equal(C.probabilityRows({type:'score',probabilities:{0:1,1:0},legend:{0:'Actual legend'}},{criteria:['Other text','High']})[0].label,'Actual legend');
assert.deepEqual(C.probabilityRows({type:'noul',noul:.47},{}),[]);
console.log('PASS Response distributions: returned probabilities and confidence remain distinct, zeroes and actual selections retained.');

const localRaces=[{id:'local10',state:'CA',jurisdiction:'City of Sunnyvale',office:'Council',district_or_seat:'District 10'},
{id:'local2',state:'CA',jurisdiction:'City of Sunnyvale',office:'Council',district_or_seat:'District 2'},
{id:'local-school',state:'CA',jurisdiction:'School district',office:'Trustee',district_or_seat:'Area 2'},
{...races[0],id:'house17'},{...races[1],id:'house1'}];
assert.deepEqual(C.sortRaces(localRaces).map(r=>r.id),['house1','house17','local2','local10','local-school']);
assert.equal(C.raceLabel(localRaces[0]),'City of Sunnyvale · Council · District 10');assert.equal(C.raceLabel(localRaces[3]),'CD-17');
const oldRace={...localRaces[0]};delete oldRace.office_category;assert.equal(C.catalogRaces({races:[{...oldRace,office_category:'City council'}]},{races:[oldRace]})[0].office_category,'City council');
console.log('PASS Mixed races: House numeric order, local jurisdiction/office labels and historical metadata.');

const linked={position_id:'CA2026-42',candidate:'Alex García & O’Connor'};
const link=new URL(C.candidateSiteUrl(linked)),params=new URLSearchParams(link.hash.slice(1));
assert.equal(link.origin,'https://salqadri.github.io');assert.equal(link.pathname,'/bay-area-elections-2026/');
assert.equal(params.get('id'),linked.position_id);assert.equal(params.get('q'),linked.candidate);
assert.equal(params.get('status'),'all');assert.equal(params.get('tab'),'candidates');
assert(html.includes('id="candidate-site"'));assert(html.includes('Latest per candidate'));
console.log('PASS Candidate site links: exact race, encoded candidate name, all roster statuses and candidate tab.');

assert(html.includes('id="run-bay-area"'));assert(html.includes('Run full roster'));
