'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const display=vm.runInNewContext(fs.readFileSync(__dirname+'/../src/pro-palestine-grade-display.js','utf8')+'\nProPalestineGradeDisplay');
class Element{constructor(tag,cls,text){this.tagName=tag;this.className=cls;this.textContent=text;this.attrs={};}setAttribute(k,v){this.attrs[k]=v;}set innerHTML(v){throw Error('Never inject HTML');}}
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
console.log('PASS public grades: compact E/score format, all color bands, accessible model provenance/confidence, gray N/A for insufficient/missing data and valid zero scores.');
