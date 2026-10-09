'use strict';

// These fixtures exercise uncertainty and inclusion behavior using real contest
// records. They intentionally avoid asserting the matcher's internal context.
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, '2026-11-03_Bay_Area_Elections.json'), 'utf8'));
const { geographyFromMatch, estimateBallot, combineEstimates, manualCounty, normalizeName } = require(path.join(root, 'src/address-matcher.js'));
const positions = data.positions;
const checks = [];
const failures = [];

function test(name, body) {
  try { body(); checks.push(name); }
  catch (error) { failures.push({ name, message: error.message }); }
}

function census(overrides = {}) {
  const geographies = {
    'States': [{ STATE: '06', NAME: 'California' }],
    'Counties': [{ STATE: '06', COUNTY: '085', NAME: 'Santa Clara County' }],
    'Incorporated Places': [{ STATE: '06', BASENAME: 'San Jose', NAME: 'San Jose city' }],
    '120th Congressional Districts': [{ STATE: '06', CD120: '17' }],
    '2026 State Legislative Districts - Upper': [{ STATE: '06', SLDU: '015' }],
    '2026 State Legislative Districts - Lower': [{ STATE: '06', SLDL: '025' }],
    'Unified School Districts': [{ STATE: '06', NAME: 'San Jose Unified School District' }]
  };
  for (const [key, value] of Object.entries(overrides)) {
    if (value === null) delete geographies[key];
    else geographies[key] = value;
  }
  return {
    matchedAddress: '200 E SANTA CLARA ST, SAN JOSE, CA, 95113',
    coordinates: { x: -121.885, y: 37.338 },
    geographies
  };
}

const estimate = raw => estimateBallot(data, geographyFromMatch(raw));
const rowsFor = (result, predicate) => result.races.filter(row => predicate(row.position));
const race = (result, id) => result.races.find(row => row.position.id === id);
const ids = records => records.map(record => record.id).sort();
const resultIds = rows => ids(rows.map(row => row.position));
const countyPositions = county => positions.filter(position => position.counties.includes(county));
const sf = () => census({
  'Counties': [{ STATE: '06', COUNTY: '075', NAME: 'San Francisco County' }],
  'Incorporated Places': [{ STATE: '06', BASENAME: 'San Francisco', NAME: 'San Francisco city' }],
  '120th Congressional Districts': [{ STATE: '06', CD120: '11' }],
  '2026 State Legislative Districts - Upper': [{ STATE: '06', SLDU: '011' }],
  '2026 State Legislative Districts - Lower': [{ STATE: '06', SLDL: '017' }],
  'Unified School Districts': [{ STATE: '06', NAME: 'San Francisco Unified School District' }]
});

test('Current district geography narrows House and Assembly without inventing a Senate contest', () => {
  const result = estimate(census());
  assert.equal(result.status, 'ok');
  assert.deepEqual(rowsFor(result, p => p.government_level === 'Federal').map(row => row.position.district_or_seat), ['CD-17']);
  assert.equal(race(result, 'CA2026-004').confidence, 'expected');
  assert.deepEqual(rowsFor(result, p => p.office_category === 'State Assembly').map(row => row.position.district_or_seat), ['AD-25']);
  assert.equal(rowsFor(result, p => p.office_category === 'State Senate').length, 0);
  assert(result.races.every(row => row.position.counties.includes('Santa Clara')));
});

test('A verified even-numbered SD-10 is included, with leading zeros normalized', () => {
  const result = estimate(census({ '2026 State Legislative Districts - Upper': [{ STATE: '06', SLDU: '010' }] }));
  assert.equal(race(result, 'CA2026-022').confidence, 'expected');
});

test('A stale 119th Congress district cannot discard plausible 2026 congressional races', () => {
  const result = estimate(census({
    '120th Congressional Districts': null,
    '119th Congressional Districts': [{ STATE: '06', CD119: '17' }]
  }));
  const federal = rowsFor(result, p => p.government_level === 'Federal');
  assert.deepEqual(resultIds(federal), ids(countyPositions('Santa Clara').filter(p => p.government_level === 'Federal')));
  assert(federal.every(row => row.confidence !== 'expected'));
  assert(result.warnings.length > 0, 'Boundary uncertainty must produce a user-visible warning');
});

test('Known incorporated city includes its unresolved council districts, excludes other cities', () => {
  const result = estimate(census());
  const municipal = rowsFor(result, p => p.government_level === 'City or town');
  assert.deepEqual(resultIds(municipal), ids(positions.filter(p => p.jurisdiction === 'City of San José')));
  assert(municipal.every(row => row.confidence === 'district_uncertain'));
  assert(municipal.every(row => typeof row.reason === 'string' && row.reason.length));
});

test('Real city names ending in City survive BASENAME and Census NAME suffix handling', () => {
  const places = [
    { city: 'Foster City', county: 'San Mateo', fips: '081' },
    { city: 'Union City', county: 'Alameda', fips: '001' },
    { city: 'Redwood City', county: 'San Mateo', fips: '081' },
    { city: 'Daly City', county: 'San Mateo', fips: '081' }
  ];
  for (const { city, county, fips } of places) {
    for (const placeRow of [
      { STATE: '06', BASENAME: city, NAME: `${city} city` },
      { STATE: '06', NAME: `${city} city` }
    ]) {
      const result = estimate(census({
        Counties: [{ STATE: '06', COUNTY: fips, NAME: `${county} County` }],
        'Incorporated Places': [placeRow]
      }));
      const municipal = rowsFor(result, p => p.government_level === 'City or town');
      const expected = positions.filter(p => p.jurisdiction === `City of ${city}`);
      assert(expected.length > 0, `Regression fixture must contain ${city} contests`);
      assert.deepEqual(resultIds(municipal), ids(expected), `${city}: ${placeRow.BASENAME ? 'BASENAME' : 'NAME fallback'}`);
      for (const row of municipal) {
        assert.equal(row.confidence, /^District\s/.test(row.position.district_or_seat) ? 'district_uncertain' : 'expected');
      }
    }
  }
});

test('Missing incorporated place retains all county municipal possibilities, not the mailing city', () => {
  const raw = census({ 'Incorporated Places': null });
  raw.matchedAddress = '200 TEST RD, SAN JOSE, CA, 95113';
  const result = estimate(raw);
  const municipal = rowsFor(result, p => p.government_level === 'City or town');
  assert.deepEqual(resultIds(municipal), ids(countyPositions('Santa Clara').filter(p => p.government_level === 'City or town')));
  assert(municipal.every(row => row.confidence === 'membership_uncertain'));
});

test('An identified unincorporated Census place excludes municipalities despite a mailing-city label', () => {
  const raw = census({
    'Incorporated Places': null,
    'Census Designated Places': [{ STATE: '06', BASENAME: 'San Martin', NAME: 'San Martin CDP' }]
  });
  raw.matchedAddress = '200 TEST RD, SAN JOSE, CA, 95113';
  const result = estimate(raw);
  assert.equal(result.status, 'ok');
  assert.equal(rowsFor(result, p => p.government_level === 'City or town').length, 0);
  assert(result.warnings.length > 0, 'Explain the geographic basis for omitting city contests');
  for (const p of countyPositions('Santa Clara').filter(p => ['Education', 'Special district'].includes(p.government_level))) {
    assert(race(result, p.id), 'Unincorporated status must not exclude school or special districts');
  }
  assert(race(result, 'CA2026-225') && race(result, 'CA2026-226'), 'Separate full and short terms remain distinct');
});

test('School parent match does not manufacture trustee-area precision', () => {
  const result = estimate(census());
  for (const id of ['CA2026-170', 'CA2026-171']) {
    assert(race(result, id), 'Both San José Unified trustee-area races must remain possible');
    assert.equal(race(result, id).confidence, 'district_uncertain');
  }
});

test('Multiple same-type school boundaries retain both at-large races as alternatives', () => {
  const milpitas = { STATE: '06', NAME: 'Milpitas Unified School District' };
  const paloAlto = { STATE: '06', NAME: 'Palo Alto Unified School District' };
  const single = estimate(census({ 'Unified School Districts': [milpitas] }));
  assert.equal(race(single, 'CA2026-158').confidence, 'expected', 'A single matched at-large school electorate is expected');
  const multiple = estimate(census({ 'Unified School Districts': [milpitas, paloAlto] }));
  for (const id of ['CA2026-158', 'CA2026-169']) {
    assert(race(multiple, id), `${id} must remain in the inclusive estimate`);
    assert.equal(race(multiple, id).confidence, 'membership_uncertain', 'Same-type boundary alternatives are not simultaneous exact matches');
  }
});

test('Unmatched county schools and special districts remain possible, even after a parent school match', () => {
  const result = estimate(census());
  const local = countyPositions('Santa Clara').filter(p => ['Education', 'Special district'].includes(p.government_level));
  for (const position of local) {
    const row = race(result, position.id);
    assert(row, `${position.id} must not be silently excluded without district boundaries`);
    if (position.office_category === 'County board of education') {
      assert.equal(row.confidence, 'district_uncertain', `${position.id}: county is known, trustee area is unresolved`);
    } else if (position.jurisdiction !== 'San José Unified School District') {
      assert.equal(row.confidence, 'membership_uncertain', `${position.id} must not be falsely presented as an exact match`);
    }
  }
});

test('SF citywide contests match its county; supervisor alternatives and BART remain uncertain', () => {
  const result = estimate(sf());
  for (const id of ['CA2026-234', 'CA2026-235', 'CA2026-241', 'CA2026-242', 'CA2026-243']) {
    assert.equal(race(result, id).confidence, 'expected', `${id} has citywide geography`);
  }
  for (const id of ['CA2026-236', 'CA2026-237', 'CA2026-238', 'CA2026-239', 'CA2026-240']) {
    assert.equal(race(result, id).confidence, 'district_uncertain', 'No supervisor district was supplied');
  }
  assert(race(result, 'CA2026-244'));
  assert.notEqual(race(result, 'CA2026-244').confidence, 'expected', 'BART District 8 is not all of SF');
});

test('All applicable appellate retention votes and BOE are included despite missing OCD IDs', () => {
  for (const county of data.election.counties_in_scope.map(c => c.name)) {
    const result = estimateBallot(data, manualCounty(county));
    const judiciary = countyPositions(county).filter(p => p.government_level === 'State judiciary');
    for (const p of judiciary) assert.equal(race(result, p.id).confidence, 'expected', `${county}: ${p.id}`);
    assert.equal(race(result, 'CA2026-021').confidence, 'expected', `${county} belongs wholly to BOE District 2`);
    assert.equal(rowsFor(result, p => p.office_category === 'Court of Appeal').length, county === 'Santa Clara' ? 5 : 11);
  }
});

test('Manual county fallback preserves every inventory record with local uncertainty', () => {
  for (const county of data.election.counties_in_scope.map(c => c.name)) {
    const result = estimateBallot(data, manualCounty(county));
    assert.equal(result.status, 'ok');
    assert.deepEqual(resultIds(result.races), ids(countyPositions(county)), county);
    assert.equal(new Set(result.races.map(row => row.position.id)).size, result.races.length, 'Deduplicate only by stable contest ID');
    assert(result.races.every(row => row.position.ballot_status === positions.find(p => p.id === row.position.id).ballot_status));
    assert(result.warnings.length > 0);
  }
  const sm = estimateBallot(data, manualCounty('San Mateo'));
  assert.notEqual(race(sm, 'CA2026-303').confidence, 'expected', 'Supervisor District 5 is not countywide');
  assert.notEqual(race(sm, 'CA2026-287').confidence, 'expected', 'County education trustee area is not countywide');
});

test('Separate same-geography terms and unresolved ballot statuses survive matching', () => {
  const santaClara = estimate(census());
  assert.equal(race(santaClara, 'CA2026-225').position.ballot_status, 'unverified');
  assert.equal(race(santaClara, 'CA2026-226').position.ballot_status, 'unverified');
  assert.notEqual(race(santaClara, 'CA2026-225').position.term, race(santaClara, 'CA2026-226').position.term);
  const sanFrancisco = estimate(sf());
  assert(race(sanFrancisco, 'CA2026-242') && race(sanFrancisco, 'CA2026-243'), 'Full and partial college terms must both remain');
});

test('Multiple address matches return the union, with expected confidence only when every address agrees', () => {
  const estimates = [estimate(census()), estimate(sf())];
  const combined = combineEstimates(data, estimates);
  assert.equal(combined.status, 'ok');
  const unionIds = [...new Set(estimates.flatMap(result => result.races.map(row => row.position.id)))].sort();
  assert.deepEqual(resultIds(combined.races), unionIds);
  assert.equal(new Set(combined.races.map(row => row.position.id)).size, combined.races.length);
  for (const row of combined.races) {
    const agreedExpected = estimates.every(result => race(result, row.position.id)?.confidence === 'expected');
    assert.equal(row.confidence === 'expected', agreedExpected, `${row.position.id}: expected requires agreement across every address`);
  }
  assert.equal(race(combined, 'CA2026-014').confidence, 'expected', 'Governor applies to both locations');
  assert.notEqual(race(combined, 'CA2026-004').confidence, 'expected', 'CD-17 applies only to the San José match');
  assert(race(combined, 'CA2026-242') && race(combined, 'CA2026-243'), 'Both SF college terms survive the union');
  assert.equal(race(combined, 'CA2026-225').position.ballot_status, 'unverified');
  assert.equal(race(combined, 'CA2026-226').position.ballot_status, 'unverified');
  assert(combined.warnings.length > 0);
});

test('Combining duplicate valid geographies preserves expected races without duplicates', () => {
  const first = estimate(sf());
  const raw = sf();
  raw.matchedAddress = '201 TEST ST, SAN FRANCISCO, CA, 94102';
  const second = estimate(raw);
  const combined = combineEstimates(data, [first, second]);
  assert.deepEqual(resultIds(combined.races), resultIds(first.races));
  for (const row of first.races) assert.equal(race(combined, row.position.id).confidence, row.confidence);
});

test('A supported plus unsupported address union warns and cannot claim a race applies to every match', () => {
  const supported = estimate(census());
  const unsupported = estimate(census({
    'Counties': [{ STATE: '06', COUNTY: '041', NAME: 'Marin County' }],
    'Incorporated Places': null
  }));
  assert.equal(unsupported.status, 'outside_scope');
  const combined = combineEstimates(data, [supported, unsupported]);
  assert.equal(combined.status, 'ok');
  assert.deepEqual(resultIds(combined.races), resultIds(supported.races));
  assert(combined.races.every(row => row.confidence !== 'expected'));
  assert(combined.warnings.some(warning => /outside|coverage|unsupported/i.test(warning)), 'Unknown ballot content for the unsupported match must be explained');
});

test('Unsupported California counties and non-California addresses produce no misleading ballot', () => {
  const marin = estimate(census({
    'Counties': [{ STATE: '06', COUNTY: '041', NAME: 'Marin County' }],
    'Incorporated Places': null
  }));
  assert.equal(marin.status, 'outside_scope');
  assert.equal(marin.races.length, 0);
  const nevada = estimate(census({
    'States': [{ STATE: '32', NAME: 'Nevada' }],
    'Counties': [{ STATE: '32', COUNTY: '003', NAME: 'Clark County' }],
    'Incorporated Places': null
  }));
  assert.equal(nevada.status, 'outside_scope');
  assert.equal(nevada.races.length, 0);
});

test('California registry resolves every FIPS code while coverage stays dataset-driven', () => {
  const registry = JSON.parse(fs.readFileSync(path.join(root, 'research/california-counties.json'), 'utf8'));
  for (const county of registry.counties) {
    const geo = geographyFromMatch({geographies:{States:[{STATE:'06'}],Counties:[{STATE:'06',COUNTY:county.fips}]}});
    assert.deepEqual(geo.counties,[county.name]);
    assert.deepEqual(manualCounty(county.name.toLowerCase()).counties,[county.name]);
    const expanded = {election:{counties_in_scope:[{name:county.name}]},positions:[{id:'fixture-'+county.fips,counties:[county.name],government_level:'County',office_category:'County board',ballot_status:'confirmed'}]};
    const estimate = estimateBallot(expanded, geo);
    assert.equal(estimate.status,'ok');
    assert.equal(estimate.races.length,1);
    const unavailable = estimateBallot({election:{counties_in_scope:[]},positions:[]},geo);
    assert.equal(unavailable.status,'outside_scope');
    assert.equal(unavailable.races.length,0);
  }
});

test('Missing or malformed county results request county information instead of guessing', () => {
  for (const raw of [{}, { geographies: {} }, census({ Counties: [] }), census({ Counties: [{}] })]) {
    const result = estimate(raw);
    assert.equal(result.status, 'needs_county');
    assert.equal(result.races.length, 0);
  }
});

test('Name normalization tolerates diacritics and does not merge distinct named places', () => {
  assert.equal(normalizeName('San José'), normalizeName('San Jose'));
  assert.notEqual(normalizeName('Santa Clara'), normalizeName('San Carlos'));
  assert.notEqual(normalizeName('San Francisco'), normalizeName('South San Francisco'));
});

console.log(JSON.stringify({ passed: failures.length === 0, checks, failures }, null, 2));
if (failures.length) process.exitCode = 1;
