/* Offline regressions for the shared display-only candidate ordering. */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const path = require('path');
const root = path.resolve(__dirname, '..') + path.sep;

vm.runInThisContext(fs.readFileSync(root + 'src/candidate-sort.js', 'utf8'));
const c = (name, extra = {}) => ({ name, ...extra });

// Rule order: incumbent → reported receipts → endorsement count → D/R tier → name.
let r = CandidateSort.sortRoster([
  c('Zed Incumbent', { incumbent: true, party: 'NPP' }),
  c('Amy Bigmoney', { fec: { receipts: 500000 } }),
  c('Bob Endorsed', { endorsements: [{}, {}, {}] }),
  c('Cara Dem', { party: 'D' }),
  c('Dan Libertarian', { party: 'L' }),
  c('Eve Unknown', { fec: { receipts: null } }),
  c('Fay Zero', { ca_finance: { receipts: 0 } }),
]);
assert.deepEqual(r.map(x => x.name), [
  'Zed Incumbent',   // a verified incumbent leads regardless of money or party
  'Amy Bigmoney',    // highest reported receipts first
  'Fay Zero',        // a reported zero outranks an unknown amount
  'Bob Endorsed',    // among no/unknown-money candidates, more endorsement records lead
  'Cara Dem',        // Democratic or Republican affiliation precedes other parties
  'Dan Libertarian',
  'Eve Unknown',     // unknown receipts rank below every reported figure
], 'Rule order must be incumbent → receipts → endorsements → major party → name');

// Two incumbents fall through to the remaining rules; DFL counts as the Democratic ballot line.
r = CandidateSort.sortRoster([
  c('Tom Two-Term', { incumbent: true, party: 'DFL' }),
  c('Ann Incumbent', { incumbent: true, party: 'R' }),
]);
assert.deepEqual(r.map(x => x.name), ['Ann Incumbent', 'Tom Two-Term'], 'Incumbent ties fall through to name order');

// Equal everything sorts by collated name; the input roster is never mutated.
const input = [c('Bo'), c('Al')];
CandidateSort.sortRoster(input);
assert.deepEqual(input.map(x => x.name), ['Bo', 'Al'], 'sortRoster must not mutate the dataset order');

// Generated pages embed the module and both readers apply it at render time.
for (const page of ['index.html', 'ballot.html']) {
  const html = fs.readFileSync(root + page, 'utf8');
  assert.ok(html.includes('const CandidateSort'), page + ' must embed the shared candidate sort');
}
assert.ok(fs.readFileSync(root + 'src/index.template.html', 'utf8').includes('rosterSection(container,heading,candidates,partisan,subtitleText){candidates=CandidateSort.sortRoster(candidates);'), 'Explorer rosters must render in sorted order');
assert.ok(fs.readFileSync(root + 'src/ballot-page.js', 'utf8').includes('CandidateSort.sortRoster(position.candidates)'), 'Address reader rosters must render in sorted order');

// On the real dataset every printed roster is a permutation with incumbents leading.
const data = JSON.parse(fs.readFileSync(root + '2026-11-03_Bay_Area_Elections.json', 'utf8'));
let checked = 0, incumbentRaces = 0;
for (const position of data.positions) {
  const roster = position.candidates;
  if (!Array.isArray(roster)) continue;
  const sorted = CandidateSort.sortRoster(roster);
  assert.equal(sorted.length, roster.length, 'Sorting must preserve every candidate');
  assert.deepEqual([...sorted].sort((a, b) => a.name.localeCompare(b.name)), [...roster].sort((a, b) => a.name.localeCompare(b.name)), position.id + ' sorting must be a permutation');
  if (roster.some(x => x.incumbent === true)) {
    incumbentRaces++;
    assert.ok(sorted[0].incumbent === true || sorted.every(x => !x.incumbent), position.id + ' incumbents must lead the displayed roster');
    const firstNonIncumbent = sorted.findIndex(x => x.incumbent !== true);
    if (firstNonIncumbent > 0) assert.ok(sorted.slice(firstNonIncumbent).every(x => x.incumbent !== true), position.id + ' incumbents must be contiguous at the front');
  }
  checked++;
}
assert.ok(checked > 400 && incumbentRaces > 50, 'Regression must exercise a large share of real rosters');

const report = { passed: true, environment: 'Offline sort regressions; display-only ordering, not a dataset change', checks: ['incumbent → receipts → endorsements → major party → name rule order', 'reported zero outranks unknown amounts', 'incumbent ties fall through', 'input roster never mutated', 'both generated pages embed the module and both readers apply it at render time', `every printed roster is an incumbent-leading permutation (${checked} rosters, ${incumbentRaces} with incumbents)`], rosters_checked: checked, incumbent_rosters: incumbentRaces };
fs.writeFileSync(root + '.checks/candidate_sort_report.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report.checks));
