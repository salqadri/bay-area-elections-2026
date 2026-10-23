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
