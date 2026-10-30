/* California Elections Code 13109 office order. Counties may vary local blocks.
   This display order is independent of the research explorer's preferred order. */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.TallBallotOrder = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  const collator = new Intl.Collator('en', {numeric:true, sensitivity:'base'});
  const stateOffices = ['Governor','Lieutenant Governor','Secretary of State','Controller','Treasurer','Attorney General','Insurance Commissioner'];
  const groups = ['Statewide offices','U.S. Senate','U.S. House','State Senate','State Assembly','Judicial','Schools & colleges','County','City & town','Special districts'];
  function rank(p) {
    let i = stateOffices.indexOf(p.office);
    if (p.government_level === 'State' && i >= 0) return [0,i];
    if (p.office_category === 'Board of Equalization') return [0,7];
    if (p.office_category === 'U.S. Senate') return [1,0];
    if (p.office_category === 'U.S. House') return [2,0];
    if (p.office_category === 'State Senate') return [3,0];
    if (p.office_category === 'State Assembly') return [4,0];
    if (p.government_level === 'State judiciary' || /Supreme Court|Court of Appeal|Superior Court|Judge|Justice/.test(p.office_category+' '+p.office)) {
      return [5, /Supreme/.test(p.office_category) ? 0 : /Appeal/.test(p.office_category) ? 1 : 2];
    }
    if (p.government_level === 'Education' || p.office_category === 'Statewide education' || /Superintendent.*(?:Instruction|Schools)/i.test(p.office)) {
      const text = p.office_category+' '+p.jurisdiction+' '+p.office;
      return [6, /Public Instruction/i.test(text) ? 0 : /Superintendent/i.test(text) ? 1 : /County board of education/i.test(text) ? 2 : /College/i.test(text) ? 3 : /Unified/i.test(text) ? 4 : /High School/i.test(text) ? 5 : /Elementary/i.test(text) ? 6 : 7];
    }
    // San Francisco combines city/county offices in the research inventory.
    if (p.government_level === 'County' || /Board of Supervisors|Assessor-Recorder|Public Defender/.test(p.office_category)) return [7,/Supervisor/i.test(p.office+' '+p.office_category)?0:1];
    if (p.government_level === 'City or town') return [8,/Mayor/i.test(p.office)?0:/Council/i.test(p.office)?1:2];
    return [9,0];
  }
  function compare(a,b) {
    const x=rank(a),y=rank(b);
    return x[0]-y[0] || x[1]-y[1] || collator.compare(a.jurisdiction,b.jurisdiction) || collator.compare(a.office,b.office) || collator.compare(a.district_or_seat,b.district_or_seat) || collator.compare(a.id,b.id);
  }
  return {rank, compare, groups, group:p=>groups[rank(p)[0]]};
});
