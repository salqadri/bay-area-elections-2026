/* Conservative address matching. Geographic uncertainty and ballot uncertainty
 * are separate: unknown local membership must never mean an automatic exclusion. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.ElectionAddressMatcher = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const CA = 'ocd-division/country:us/state:ca';
  const COUNTY_FIPS = {'001':'Alameda','013':'Contra Costa','075':'San Francisco','081':'San Mateo','085':'Santa Clara'};
  const COUNTY_NAMES = Object.values(COUNTY_FIPS);
  const unique = values => [...new Set(values.filter(Boolean))];
  const normalizeName = value => String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[_’']/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
  const schoolName = name => normalizeName(name).replace(/\bmt\b/g, 'mount').replace(/\bschool district\b/g, 'district');
  const number = value => /^\d{1,3}$/.test(String(value || '')) && Number(value) > 0 ? Number(value) : null;
  const rows = (geographies, test) => Object.entries(geographies).filter(([name]) => test(name)).flatMap(([, value]) => Array.isArray(value) ? value.filter(v => v && typeof v === 'object') : []);
  const nameOf = row => String(row.BASENAME || row.NAME || '').trim();

  function geographyFromMatch(match) {
    match = match && typeof match === 'object' ? match : {};
    const geographies = match.geographies && typeof match.geographies === 'object' ? match.geographies : {};
    const stateRows = rows(geographies, name => /^States$/i.test(name));
    const countyRows = rows(geographies, name => /^Counties$/i.test(name));
    const stateCodes = unique([...stateRows, ...countyRows].map(r => String(r.STATE || '').padStart(2, '0')).filter(v => /^\d{2}$/.test(v) && v !== '00'));
    const counties = unique(countyRows.map(r => {
      const state = String(r.STATE || (stateCodes.length === 1 ? stateCodes[0] : '')).padStart(2, '0');
      const fips = String(r.COUNTY || '').padStart(3, '0');
      if (state === '06' && COUNTY_FIPS[fips]) return COUNTY_FIPS[fips];
      return nameOf(r).replace(/ County$/i, '');
    }));
    const caRows = test => rows(geographies, test).filter(r => !r.STATE || String(r.STATE).padStart(2, '0') === '06');
    // BASENAME excludes the Census legal suffix already. Do not strip the real
    // word "City" from Foster City, Union City, Redwood City or Daly City.
    const places = unique(caRows(name => /^Incorporated Places$/i.test(name)).map(r => r.BASENAME ? String(r.BASENAME).trim() : String(r.NAME || '').replace(/ (city|town)$/i, '').trim()));
    const cdps = unique(caRows(name => /^Census Designated Places$/i.test(name)).map(r => r.BASENAME ? String(r.BASENAME).trim() : String(r.NAME || '').replace(/ CDP$/i, '').trim()));
    // A label for the 119th Congress describes different California boundaries.
    // It must never narrow the inventory for the November 2026 election.
    const cd = caRows(name => /^120th Congressional Districts$/i.test(name)).filter(r => !r.CDSESSN || String(r.CDSESSN) === '120');
    const sd = caRows(name => /^2026 State Legislative Districts\s*-\s*Upper$/i.test(name));
    const ad = caRows(name => /^2026 State Legislative Districts\s*-\s*Lower$/i.test(name));
    const districts = {
      CD: unique(cd.map(r => number(r.CD120))).filter(n => n <= 52),
      SD: unique(sd.map(r => number(r.SLDU))).filter(n => n <= 40),
      AD: unique(ad.map(r => number(r.SLDL))).filter(n => n <= 80)
    };
    const schoolDistricts = [];
    for (const [layer, type] of [['Unified School Districts','unified'],['Secondary School Districts','secondary'],['Elementary School Districts','elementary']]) {
      for (const row of caRows(name => name.toLowerCase() === layer.toLowerCase())) {
        if (nameOf(row)) schoolDistricts.push({name:nameOf(row),type,geoid:row.GEOID || null});
      }
    }
    const warnings = [];
    if (!districts.CD.length && rows(geographies, name => /Congressional Districts/i.test(name)).length) warnings.push('The returned congressional map is not identified as the 120th Congress. All researched House races in the county are retained as possibilities because California changed its congressional boundaries for 2026.');
    if (!places.length && !cdps.length && !counties.includes('San Francisco')) warnings.push('An incorporated city boundary was not returned. City races across the county remain possible; the mailing-city name is not used to decide city residency.');
    if (cdps.length && !places.length) warnings.push('The location is in an unincorporated Census-designated place. City contests are excluded on that geographic basis; school and special-district membership is evaluated separately.');
    if (places.length > 1 || counties.length > 1 || Object.values(districts).some(v => v.length > 1)) warnings.push('The geographic response identifies more than one possible boundary match. All matching alternatives are included.');
    return {matchedAddress:String(match.matchedAddress || ''),stateCodes,counties,places,cdps,districts,schoolDistricts,manual:false,warnings};
  }

  function manualCounty(county) {
    const canonical = COUNTY_NAMES.find(c => normalizeName(c) === normalizeName(county)) || String(county || '');
    return {matchedAddress:'',stateCodes:['06'],counties:canonical?[canonical]:[],places:[],cdps:[],districts:{CD:[],AD:[],SD:[]},schoolDistricts:[],manual:true,warnings:['Only the county has been supplied. This broad estimate includes all researched contests in that county; city, legislative, school and special-district eligibility has not been determined.']};
  }

  function summary(geo) {
    const places = (geo.places || []).length ? geo.places : (geo.counties || []).includes('San Francisco') ? ['San Francisco'] : (geo.cdps || []).map(p => p+' (unincorporated)');
    return {counties:geo.counties || [],places,districts:geo.districts || {CD:[],AD:[],SD:[]},schoolDistricts:unique((geo.schoolDistricts || []).map(s => s.name)),matchedAddresses:geo.matchedAddress?[geo.matchedAddress]:[],manual:!!geo.manual};
  }

  function countsFor(races) {
    const counts = {expected:0,possible:0,scheduled:0,total:races.length,district_uncertain:0,membership_uncertain:0};
    for (const race of races) {
      if (race.position.ballot_status !== 'confirmed') counts.scheduled++;
      else if (race.confidence === 'expected') counts.expected++;
      else {counts.possible++;counts[race.confidence]++;}
    }
    return counts;
  }

  function classify(position, geo) {
    const level = position.government_level;
    const category = position.office_category;
    const id = position.ocd_division_id || '';
    const result = (confidence, reason) => ({position,confidence,reason});
    if (id === CA && ['State','State judiciary'].includes(level)) return result('expected','This is a statewide contest for California voters.');
    if (position.countywide_electorate === true) return result('expected','This electorate includes every voter in the matched county.'+(category==='Court of Appeal'?' Appellate retention questions are separate votes, even when several divisions appear.':''));
    const countyIds = geo.counties.map(c => CA+'/county:'+normalizeName(c).replace(/ /g,'_'));
    if (countyIds.includes(id)) return result('expected','The contest covers the matched county as a whole.');

    const legislative = (position.district_or_seat || '').match(/^(CD|AD|SD)-(\d+)$/);
    if (legislative && ['Federal','State'].includes(level)) {
      const prefix = legislative[1], district = Number(legislative[2]);
      const found = geo.districts[prefix] || [];
      if (found.length && !found.includes(district)) return null;
      if (found.length === 1) return result('expected','The address matches '+prefix+'-'+district+' in the '+(prefix==='CD'?'120th Congress':'2026 state legislative')+' geography.');
      return result('district_uncertain',found.length?'The location has several possible '+prefix+' boundary matches. Each researched matching race is included.':'The '+prefix+' district for this election could not be established. All researched alternatives in the county are included; your ballot may contain only one of them.');
    }

    if (level === 'City or town') {
      const place = id.match(/\/place:([^/]+)/);
      const sf = id.startsWith(CA+'/county:san_francisco');
      const target = sf ? 'san francisco' : place ? normalizeName(place[1]) : '';
      const cityMatches = sf && geo.counties.includes('San Francisco') ? ['San Francisco'] : geo.places.filter(p => normalizeName(p) === target);
      if (!sf && !geo.places.length && geo.cdps.length) return null;
      if (target && geo.places.length && !cityMatches.length) return null;
      if (!target || !cityMatches.length) return result('membership_uncertain','City residency could not be established for this contest. It is included as a county-level possibility; a mailing-city name alone does not establish eligibility.');
      const child = /\/(?:council_district|ward|supervisor_district):/.test(id);
      if (child) return result('district_uncertain','The address is in '+position.jurisdiction+', but its council or supervisor district is not resolved. All researched districts for this city are shown; only the applicable district belongs on the actual ballot.');
      if (geo.places.length > 1 && !sf) return result('membership_uncertain','More than one city boundary matched. This citywide contest is one of the alternatives.');
      return result('expected','This is a citywide contest in the matched incorporated city.');
    }

    if (level === 'County' || category === 'County board of education') return result('district_uncertain','The county matches, but the supervisor or county education trustee district is not resolved. Each researched district is retained as a possibility.');
    if (level === 'Education') {
      const matched = geo.schoolDistricts.filter(s => schoolName(s.name) === schoolName(position.jurisdiction));
      if (matched.length) {
        if (geo.schoolDistricts.some(s => matched.some(m => m.type === s.type && schoolName(m.name) !== schoolName(s.name)))) return result('membership_uncertain','Several possible school-district boundaries matched. This district is included as an alternative; its membership needs confirmation.');
        if (/^at[ -]?large\b|^districtwide\b/i.test(position.district_or_seat || '')) return result('expected','The address matches the school district name in Census geography, and this contest is at large within that district.');
        return result('district_uncertain','The school district matches, but the trustee area is not resolved. All researched trustee areas that may apply in this county are included.');
      }
      return result('membership_uncertain','Membership in this school, college or education district has not been established. This county-level possibility is included so an unresolved district is not silently omitted.');
    }
    if (level === 'Special district') return result('membership_uncertain','This service or special-district electorate could not be matched to the address. It is a county-level possibility; living nearby or receiving a service does not by itself establish voting eligibility.');
    return result('membership_uncertain','The county matches, but the complete electorate boundary has not been established.');
  }

  function estimateBallot(data, geo) {
    geo = geo || geographyFromMatch({});
    const scoped = (data.election.counties_in_scope || []).map(c => c.name);
    const counties = geo.counties || [];
    const matchingCounties = counties.filter(c => scoped.includes(c));
    const stateCodes = geo.stateCodes || [];
    let status = 'ok';
    if ((stateCodes.length && !stateCodes.includes('06')) || (counties.length && !matchingCounties.length)) status = 'outside_scope';
    else if (!counties.length || !stateCodes.includes('06')) status = 'needs_county';
    const warnings = [...(geo.warnings || [])];
    if (status !== 'ok') return {status,races:[],warnings,geography:geo,summary:summary(geo),counts:countsFor([])};
    const races = [];
    for (const position of data.positions) {
      if (position.ballot_status === 'excluded' || !position.counties.some(c => matchingCounties.includes(c))) continue;
      const race = classify(position, geo);
      if (!race) continue;
      if ((matchingCounties.length !== counties.length || counties.some(c => !position.counties.includes(c))) && race.confidence === 'expected') {
        race.confidence = 'membership_uncertain';
        race.reason = 'This race applies to only some of the possible county matches. The address geography needs to be narrowed.';
      }
      races.push(race);
    }
    const counts = countsFor(races);
    if (counts.possible) warnings.push('Possible matches are deliberately inclusive. Several listed districts may be alternatives, and your official ballot may contain only one or none of those races.');
    if (counts.membership_uncertain) warnings.push('Some school, college and special-district boundaries are unresolved. Their county-relevant races are retained as possibilities, including districts whose membership could not be verified.');
    if (counts.scheduled) warnings.push('Scheduled races are shown separately from confirmed ballot contests: their final November ballot appearance is still unverified in the research inventory.');
    for (const [prefix, found] of Object.entries(geo.districts)) {
      for (const district of found) {
        if (prefix === 'SD' && district % 2 === 1) continue;
        if (!races.some(r => r.position.district_or_seat === prefix+'-'+district)) warnings.push('The geography identifies '+prefix+'-'+district+', but this inventory has no matching researched contest for that county. This is a coverage gap, not confirmation that no election occurs.');
      }
    }
    if (matchingCounties.length !== counties.length) warnings.push('Some possible address locations are outside the five researched counties. Results only cover the supported portions.');
    return {status,races,warnings:unique(warnings),geography:geo,summary:summary(geo),counts};
  }

  function combineEstimates(data, estimates) {
    if (estimates.length === 1) return estimates[0];
    const usable = estimates.filter(e => e.status === 'ok');
    const status = usable.length ? 'ok' : estimates.some(e => e.status === 'needs_county') ? 'needs_county' : 'outside_scope';
    const maps = estimates.map(e => new Map(e.races.map(r => [r.position.id,r])));
    const races = [];
    for (const position of data.positions) {
      const matches = maps.map(m => m.get(position.id));
      const present = matches.filter(Boolean);
      if (!present.length) continue;
      if (present.length === estimates.length && present.every(r => r.confidence === 'expected')) races.push({...present[0]});
      else if (present.length === estimates.length && present.every(r => r.confidence !== 'membership_uncertain')) races.push({...present[0],confidence:'district_uncertain',reason:'The possible address locations do not resolve one voting district. Every researched alternative is included.'});
      else races.push({...present[0],confidence:'membership_uncertain',reason:'This race applies to only some possible address matches, or district membership is unresolved. Narrow the address matches to refine the estimate.'});
    }
    const all = key => unique(estimates.flatMap(e => e.summary[key] || []));
    const combinedSummary = {counties:all('counties'),places:all('places'),schoolDistricts:all('schoolDistricts'),matchedAddresses:all('matchedAddresses'),manual:estimates.some(e => e.summary.manual),districts:{}};
    for (const prefix of ['CD','AD','SD']) combinedSummary.districts[prefix] = unique(estimates.flatMap(e => e.summary.districts[prefix] || []));
    const warnings = unique(['The address matched multiple locations. This is the union of all their possible races, not one official ballot. Choose a single matched address to narrow the results.',...estimates.flatMap(e => e.warnings)]);
    if (usable.length !== estimates.length) warnings.push('Some address matches are outside coverage or lack a verified county. Their ballot content could not be estimated.');
    return {status,races,warnings,summary:combinedSummary,geography:null,counts:countsFor(races)};
  }
  return {geographyFromMatch,estimateBallot,combineEstimates,manualCounty,normalizeName};
});
