'use strict';
// Fixed fixtures exercise both readers' shared renderer independently of live totals.
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert/strict');
const display = vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/finance-display.js'), 'utf8') + '\nCampaignFinanceDisplay', {Intl});
class Element {
  constructor(tag, cls, text) { this.tagName=tag.toUpperCase();this.className=cls||'';this.children=[];this.open=false;if(text!==undefined&&text!==null)this.children.push(String(text)); }
  append(...children) { for(const child of children){this.children.push(child);if(typeof child==='object')child.parent=this;} }
  get textContent() { return this.children.map(c=>typeof c==='string'?c:c.textContent).join(''); }
}
const node=(tag,cls,text)=>new Element(tag,cls,text);
const link=(url,text,cls)=>{const result=node('a',cls,text);result.href=url;return result;};
const helpers={node,link,dateLabel:value=>value};
const data={finance:{currency:'USD',checked_on:'2026-10-14'},ie_finance:{cycle:2026,checked_on:'2026-10-13',source_id:'S002',method:'Independent outside spending, not campaign receipts.'},sources:{S001:{url:'https://www.fec.gov/data/candidate/H6CA00001/'},S002:{url:'https://api.open.fec.gov/v1/schedules/schedule_e/'}},notes:{N001:'No published total is available; unknown is not zero.'},ie_spenders:{C00000001:{name:'Fixture PAC',committee_type:'Super PAC',source_url:'https://www.fec.gov/data/committee/C00000001/'}}};
const candidate={fec:{receipts:1250.25,from:'2025-01-01',through:'2026-09-30',source_id:'S001'},independent_expenditures:{for_total:100,against_total:40,browse_url:'https://www.fec.gov/data/independent-expenditures/?candidate_id=H6CA00001',items:[{spender_id:'C00000001',direction:'for',amount:100},{spender_id:'C00000001',direction:'against',amount:40}]}};
const all=n=>[n,...n.children.filter(c=>typeof c==='object').flatMap(all)];
const card=display.render(candidate,data,helpers);
assert.equal(card.tagName,'DETAILS');assert.equal(card.open,false);
for(const expected of ['$1,250.25','2025-01-01 – 2026-09-30','For: $100.00','Against: $40.00','+ $100.00','- $40.00','Checked 2026-10-14','Checked 2026-10-13','not campaign receipts'])assert(card.textContent.includes(expected),expected);
assert.equal(all(card).filter(n=>n.href===data.ie_spenders.C00000001.source_url).length,2,'Both directions retain the spender link');
assert(all(card).some(n=>n.href===candidate.independent_expenditures.browse_url));
const unknown=display.render({fec:{receipts:null,source_id:'S001',note_id:'N001'}},data,helpers);
assert(unknown.textContent.includes('No published total available'));assert(unknown.textContent.includes('unknown is not zero'));assert(!unknown.textContent.includes('$0.00'));
const zero=display.render({fec:{receipts:0,from:'2025-01-01',through:'2026-09-30',source_id:'S001'},independent_expenditures:{for_total:0,against_total:0,items:[],browse_url:candidate.independent_expenditures.browse_url}},data,helpers);
assert(zero.textContent.includes('$0.00'));assert(zero.textContent.includes('No itemized independent expenditures'));assert(all(zero).some(n=>n.href===candidate.independent_expenditures.browse_url));
assert.equal(display.render({},data,helpers),null);
console.log('Shared campaign-money display: receipts, unknown/zero, both spending directions, dates, sources and collapsed disclosure passed.');
