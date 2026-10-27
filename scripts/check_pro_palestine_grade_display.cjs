'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const display=vm.runInNewContext(fs.readFileSync(__dirname+'/../src/pro-palestine-grade-display.js','utf8')+'\nProPalestineGradeDisplay');
class Element{constructor(tag,cls,text){this.tagName=tag;this.className=cls;this.textContent=text;this.attrs={};this.children=[];}setAttribute(k,v){this.attrs[k]=v;}append(...kids){for(const child of kids)if(child)this.children.push(child);return this;}set innerHTML(v){throw Error('Never inject HTML');}}
const node=(...args)=>new Element(...args),data={pro_palestine_grading:{methodology_url:'https://example.org/rubric'}};
const meta={confidence:.72,evidence_score:.91,evaluated_at:'2026-10-26T07:00:00Z'};
const e=display.render({pro_palestine_score:1.36,pro_palestine_score_grade:'E',pro_palestine_evaluation:meta},data,{node});
assert.equal(e.textContent,'E (1.36 / 5)');assert.equal(e.className,'pro-palestine-grade grade-e');assert.equal(e.href,data.pro_palestine_grading.methodology_url);assert(e.title.includes('72.0%'));assert(e.attrs['aria-label'].includes('Jev pro-Palestine model grade'));
for(const grade of 'ABCDEF'){const b=display.render({pro_palestine_score:3,pro_palestine_score_grade:grade,pro_palestine_evaluation:meta},data,{node});assert(b.className.endsWith('grade-'+grade.toLowerCase()));}
for(const candidate of [{},{pro_palestine_score:0,pro_palestine_score_grade:'F'},{pro_palestine_score:1.77,pro_palestine_score_grade:'N/A',pro_palestine_evaluation:{...meta,evidence_score:0}},{pro_palestine_score:NaN,pro_palestine_score_grade:'<img>',pro_palestine_evaluation:meta}]){
 const b=display.render(candidate,data,{node});assert.equal(b.textContent,'N/A');assert(b.className.endsWith('grade-na'));
}
const low=display.render({pro_palestine_score:0,pro_palestine_score_grade:'F',pro_palestine_evaluation:meta},data,{node});assert.equal(low.textContent,'F (0.00 / 5)');
for(const file of ['src/index.template.html','src/ballot.template.html'])assert(fs.readFileSync(__dirname+'/../'+file,'utf8').includes('__PRO_PALESTINE_GRADE_JS__'));
// Grade explanations: collapsed evidence summary bound to the saved evaluation.
const explanation={publication_id:'jev-2026-10-26',candidate_id:'x',request_sha256:'a'.repeat(64),summary:'Connie Chan received A because her saved score of 4.95 falls in the A band; the state records direct statements and endorsements.',model:'qwen/qwen3.8-27b'};
const panel=display.renderExplanation({pro_palestine_score_grade:'A',pro_palestine_explanation:explanation},{node});
assert.equal(panel.tagName,'details');assert.equal(panel.className,'grade-explanation');assert(!panel.open);
assert(panel.children.some(c=>c.textContent==='Why this grade?'));assert(panel.children.some(c=>c.textContent===explanation.summary));
assert(panel.children.some(c=>typeof c==='object'&&c.textContent.includes(explanation.model)&&c.textContent.includes('never changes it')));
const naPanel=display.renderExplanation({pro_palestine_score_grade:'N/A',pro_palestine_explanation:{...explanation,summary:'Rudy Recile received N/A because the saved evidence score was 0.01 out of 1, below the 0.10 threshold; the available evidence was insufficient and no letter grade was assigned.'}},{node});
assert(naPanel.children.some(c=>typeof c==='object'&&c.textContent.includes('insufficient-evidence note')));
const fundingCandidate={pro_palestine_score_grade:'B',pro_palestine_explanation:explanation,pro_palestine_evaluation:{input_state_version:'candidate-evidence-v7-local-federal-community'},gaza_evidence:[{dimension:'aipac_funding'}]};
assert(display.renderExplanation(fundingCandidate,{node}).children.some(c=>c.textContent?.includes('Funding evidence rules changed')));
fundingCandidate.pro_palestine_evaluation.input_state_version='candidate-evidence-v11-local-federal-funding-periods';
assert(!display.renderExplanation(fundingCandidate,{node}).children.some(c=>c.textContent?.includes('Funding evidence rules changed')));
for(const candidate of [{}, {pro_palestine_explanation:null}, {pro_palestine_explanation:{summary:'   '}}, {pro_palestine_score_grade:'B'}])assert.equal(display.renderExplanation(candidate,{node}),null,'missing or blank explanations render nothing');
const indexTemplate=fs.readFileSync(__dirname+'/../src/index.template.html','utf8'),ballotPage=fs.readFileSync(__dirname+'/../src/ballot-page.js','utf8');
assert(indexTemplate.includes('renderExplanation(c,')&&indexTemplate.includes('.grade-explanation{'),'explorer must render and style the explanation panel');
assert(ballotPage.includes('renderExplanation(candidate,'),'ballot reader must render the explanation panel');
console.log('PASS public grades: compact E/score format, all color bands, accessible model provenance/confidence, gray N/A for insufficient/missing data, valid zero scores and collapsed bound evidence explanations.');

const customThreshold=display.render({pro_palestine_score:3,pro_palestine_score_grade:'N/A',pro_palestine_evaluation:{...meta,evidence_score:.19}},{pro_palestine_grading:{evidence_threshold:.2}},{node});assert(customThreshold.title.includes('below 0.2 / 1'));assert(!customThreshold.title.includes('below 0.10'));
