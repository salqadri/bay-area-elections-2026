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
const catalog=C.catalogRows(snapshot,single);assert.equal(catalog.length,2);assert.equal(catalog[0].request,single.rows[0].request);assert.equal(catalog[0].response,single.rows[0].response);assert.equal(catalog[1].status,'preview');assert.equal(catalog[1].response,undefined);assert.equal(catalog[1].request,undefined);assert.equal(snapshot.candidates[0].status,undefined);
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

const cairQuestions={gaza_grade:{type:'choice',criteria:{A:'A',B:'B',C:'C',D:'D',E:'E',F:'F'}},pro_palestine_score:{type:'score',criteria:['0','1','2','3','4','5']}};
function reviewed(grade='B',score=4,relation='preferred',extra={}){return {status:'complete',cair_action:[{endorser:'CAIR Action',relation,phase:'general',...extra}],request:{questions:cairQuestions},response:{answers:{gaza_grade:{type:'choice',choice:grade,confidence:.01},pro_palestine_score:{type:'score',score,confidence:0}}}};}
assert(C.cairComparison(reviewed('C',5)).flagged);assert(C.cairComparison(reviewed('F',5)).flagged);
assert(C.cairComparison(reviewed('B',2.5,'endorsed')).flagged);
assert(C.cairComparison(reviewed('A',0)).flagged);assert(!C.cairComparison(reviewed('A',2.500001)).flagged);
assert(!C.cairComparison(reviewed('B',4)).flagged);assert(!C.cairComparison(reviewed('F',0,'opposed')).flagged);
assert(!C.cairComparison(reviewed('F',0,'endorsed',{historical:true})).positive);
assert(!C.cairComparison(reviewed('F',0,'endorsed',{phase:'primary'})).positive);
assert(C.cairComparison(reviewed('F',0,'preferred',{phase:'unspecified'})).flagged);
assert(C.cairComparison(reviewed('F',0,'endorsed',{shared:true})).flagged);
assert.equal(C.cairLabel({relation:'endorsed',shared:true}),'Jointly endorsed');
const waiting={...reviewed(),status:'preview'};assert(C.cairComparison(waiting).positive);assert(!C.cairComparison(waiting).comparable);assert(!C.cairComparison(waiting).flagged);
const missing=reviewed();delete missing.response.answers.gaza_grade;delete missing.response.answers.pro_palestine_score;assert(!C.cairComparison(missing).comparable);
const wrongScale=reviewed('A',0);wrongScale.request={questions:{...cairQuestions,pro_palestine_score:{type:'score',criteria:['0','1','2','3','4']}}};assert.equal(C.cairComparison(wrongScale).score,null);assert(!C.cairComparison(wrongScale).flagged);
const custom=reviewed('C',2);custom.request={questions:{custom_grade:cairQuestions.gaza_grade,custom_score:cairQuestions.pro_palestine_score}};custom.response={answers:{custom_grade:custom.response.answers.gaza_grade,custom_score:custom.response.answers.pro_palestine_score}};
assert(!C.cairComparison(custom).comparable);assert(C.cairComparison(custom,{gradeKey:'custom_grade',scoreKey:'custom_score'}).flagged);
assert.deepEqual(C.comparisonQuestions([custom]),{grades:['custom_grade'],scores:['custom_score']});
assert.equal(C.cairComparison(reviewed('F',5)).grade.confidence,.01);assert.equal(C.cairComparison(reviewed('A',0)).score.confidence,0);
const snapshotCair={...snapshot,candidates:[{...snapshot.candidates[0],cair_action:[{relation:'preferred',phase:'general'}]},snapshot.candidates[1]]};
const oldCair={...single,rows:[{...single.rows[0],cair_action:[{relation:'opposed',phase:'general'}]}]};
const withCurrent=C.catalogRows(snapshotCair,oldCair)[0];assert.equal(withCurrent.cair_action[0].relation,'preferred');assert.equal(withCurrent.request,oldCair.rows[0].request);assert.equal(oldCair.rows[0].cair_action[0].relation,'opposed');
const counties=['Alameda','Contra Costa','San Francisco','San Mateo','Santa Clara'];
const sharedCounty={counties:['Alameda','Santa Clara']};assert(C.countyMatches(sharedCounty,'Alameda',counties));assert(C.countyMatches(sharedCounty,'Santa Clara',counties));assert(C.countyMatches(sharedCounty,'bay-area',counties));assert(!C.countyMatches(sharedCounty,'San Mateo',counties));assert(!C.countyMatches({counties:[]},'bay-area',counties));assert(C.countyMatches({counties:[]},'all',counties));
for(const county of counties)assert(C.countyMatches({counties:[county]},'bay-area',counties));
console.log('PASS CAIR comparisons: C/F boundaries, inclusive 2.5/5, OR logic, confidence unfiltered, joint/current/unspecified versus historical/primary/opposed, missing/renamed/incompatible answers, exact saved inputs and county predicates.');

const mapping=JSON.parse(fs.readFileSync(path.join(__dirname,'../research/gaza-grading/score-grade-mapping.json'),'utf8'));
assert.deepEqual(mapping,C.defaultScoreGradeMapping);
assert.equal(C.scoreGrade(0,mapping),'F');assert.equal(C.scoreGrade(5,mapping),'A');
for(const [i,upper]of mapping.upper_bounds.entries()){assert.equal(C.scoreGrade(upper,mapping),'FEDCB'[i]);assert.equal(C.scoreGrade(upper+Number.EPSILON*8,mapping),'EDCBA'[i]);}
for(const value of [null,true,'2',NaN,Infinity,-.01,5.01])assert.equal(C.scoreGrade(value,mapping),null);
const nonlinear={upper_bounds:[.1,.5,1,2,4.9]};assert.equal(C.scoreGrade(2.5,nonlinear),'B');
for(const invalid of [{},[],{upper_bounds:[0,1,2,3,4]},{upper_bounds:[1,2,2,3,4]},{upper_bounds:[1,2,3,4,5]},{upper_bounds:[1,2,3,4]},{upper_bounds:[false,1,2,3,4]},{upper_bounds:[1,2,3,4,NaN]},{...nonlinear,extra:1}])assert.throws(()=>C.validateMapping(invalid));
const derivedRow=reviewed('A',2.5),before=JSON.stringify(derivedRow);
assert.equal(C.derivedGrade(derivedRow,mapping),'D');assert.equal(C.derivedGrade(derivedRow,nonlinear),'B');
assert(C.cairComparison(derivedRow,{gradeKey:'pro_palestine_score_grade',scoreKey:'',mapping}).flagged);
assert(!C.cairComparison(derivedRow,{gradeKey:'pro_palestine_score_grade',scoreKey:'',mapping:nonlinear}).flagged);
const exported=C.withScoreGrades({rows:[derivedRow]},nonlinear);assert.equal(exported.rows[0].pro_palestine_score_grade,'B');assert.deepEqual(exported.score_grade_mapping,nonlinear);assert.equal(exported.rows[0].request,derivedRow.request);assert.equal(exported.rows[0].response,derivedRow.response);assert.equal(JSON.stringify(derivedRow),before);
assert.equal(C.derivedGrade({...derivedRow,status:'queued'}),null);assert.equal(C.derivedGrade(wrongScale),null);
assert(C.comparisonQuestions([derivedRow]).grades.includes('pro_palestine_score_grade'));
assert(html.includes('id="grade-mapping-form"'));assert(html.includes('id="candidate-score-grade"'));
console.log('PASS Derived grades: exact inclusive boundaries, nonlinear bounds/validation, unsupported scores/scales, CAIR selector, confidence unchanged and reproducible exports with immutable Jev answers.');

assert(C.samePrompt('{"q":{"type":"score","criteria":["low","high"]}}','{\n "q": { "type": "score", "criteria": ["low", "high"] }\n}'));
assert(!C.samePrompt('{"q":{"type":"score","criteria":["low","high"]}}','{"q":{"type":"score","criteria":["high","low"]}}'));
assert(!C.samePrompt('{"q":','{"q":{"type":"noul"}}'));
assert(html.includes('id="load-saved-prompt"'));
console.log('PASS Prompt identity: formatting-only changes remain clean, changed criteria and invalid drafts remain distinct; saved prompt control is available.');

const sparse=reviewed('D',1.77);
sparse.request=structuredClone(sparse.request);sparse.request.questions.evidence_score={type:'score',criteria:['none','concrete']};
sparse.response.answers.evidence_score={type:'score',score:0,confidence:1};
for(const value of [0,.05,.099999,.1,1]){
  sparse.response.answers.evidence_score.score=value;
  const raw=JSON.stringify(sparse);
  assert.equal(C.derivedGrade(sparse),value<.1?'Insufficient Info':'D');
  assert.equal(C.withScoreGrades({rows:[sparse]},mapping).rows[0].pro_palestine_score_grade,value<.1?'Insufficient Info':'D');
  assert.equal(JSON.stringify(sparse),raw);
}
sparse.response.answers.evidence_score.score=0;
const insufficientComparison=C.cairComparison(sparse,{gradeKey:'pro_palestine_score_grade',scoreKey:''});
assert.equal(insufficientComparison.grade.value,'Insufficient Info');assert.equal(insufficientComparison.grade.confidence,null);
assert(!insufficientComparison.flagged);assert(!insufficientComparison.comparable);
assert(C.cairComparison(sparse).flagged); // Original model grade/score comparisons stay explicit.
for(const value of [null,true,'0',NaN,-.1,1.1]){sparse.response.answers.evidence_score.score=value;assert.equal(C.derivedGrade(sparse),'D');}
sparse.response.answers.evidence_score.score=0;sparse.request.questions.evidence_score.criteria.push('wrong scale');assert.equal(C.derivedGrade(sparse),'D');
delete sparse.request.questions.evidence_score;assert.equal(C.derivedGrade(sparse),'D');
console.log('PASS Evidence sufficiency: strict 0.10 boundary, validated 0–1 question, unchanged historic prompts/raw answers and nonletter CAIR handling.');
