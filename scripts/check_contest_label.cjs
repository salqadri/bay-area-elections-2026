/* Offline regressions for shared state-aware contest labels and natural district order (display-only). */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const path = require('path');
const root = path.resolve(__dirname, '..') + path.sep;

vm.runInThisContext(fs.readFileSync(root + 'src/contest-label.js', 'utf8'));
const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });

// State derivation: OCD identifier first, Bay Area county rows default to California.
assert.equal(ContestLabel.stateCode({ocd_division_id: 'ocd-division/country:us/state:ca/county:santa_clara'}), 'CA');
assert.equal(ContestLabel.stateCode({ocd_division_id: 'ocd-division/country:us/state:tx/cd:35'}), 'TX');
assert.equal(ContestLabel.stateCode({counties: ['Alameda']}), 'CA');
assert.equal(ContestLabel.stateCode({counties: []}), '');

// District labels carry the state only where codes are ambiguous across states.
assert.equal(ContestLabel.districtLabel({district_or_seat: 'CD-17', ocd_division_id: 'ocd-division/country:us/state:ca/county:santa_clara/cd:17'}), 'CA CD-17');
assert.equal(ContestLabel.districtLabel({district_or_seat: 'CD-2', ocd_division_id: 'ocd-division/country:us/state:al/cd:2'}), 'AL CD-2');
assert.equal(ContestLabel.districtLabel({district_or_seat: 'AD-18', ocd_division_id: 'ocd-division/country:us/state:ca/sldl:lower:18'}), 'CA AD-18');
assert.equal(ContestLabel.districtLabel({district_or_seat: 'SD-10', ocd_division_id: 'ocd-division/country:us/state:ca/sldu:senate:10'}), 'CA SD-10');
assert.equal(ContestLabel.districtLabel({district_or_seat: 'AL — Statewide', ocd_division_id: 'ocd-division/country:us/state:al'}), 'AL — Statewide');
assert.equal(ContestLabel.districtLabel({district_or_seat: 'Statewide', counties: ['Alameda']}), 'CA — Statewide');
assert.equal(ContestLabel.districtLabel({district_or_seat: 'Trustee Area 3', counties: ['Santa Clara']}), 'Trustee Area 3');

// Natural order: CA CD-1 before CA CD-2 and CA CD-17; state groups precede district numbers.
const order = (a, b) => ContestLabel.contestOrder(a, b, collator);
assert.ok(order({jurisdiction: 'H', district_or_seat: 'CD-1'}, {jurisdiction: 'H', district_or_seat: 'CD-17'}) < 0, 'CD-1 must precede CD-17');
assert.ok(order({jurisdiction: 'H', district_or_seat: 'CD-2'}, {jurisdiction: 'H', district_or_seat: 'CD-10'}) < 0, 'CD-2 must precede CD-10');
assert.ok(order({jurisdiction: 'H', district_or_seat: 'District 9'}, {jurisdiction: 'H', district_or_seat: 'District 10'}) < 0, 'local districts sort numerically');
const house = [
  {jurisdiction: 'US House', district_or_seat: 'CD-22', ocd_division_id: 'ocd-division/country:us/state:fl/cd:22'},
  {jurisdiction: 'US House', district_or_seat: 'CD-1', ocd_division_id: 'ocd-division/country:us/state:az/cd:1'},
  {jurisdiction: 'US House', district_or_seat: 'CD-17', ocd_division_id: 'ocd-division/country:us/state:ca/county:santa_clara/cd:17'},
  {jurisdiction: 'US House', district_or_seat: 'CD-8', ocd_division_id: 'ocd-division/country:us/state:ca/county:san_mateo/cd:8'},
].sort(order);
assert.deepEqual(house.map(p => ContestLabel.districtLabel(p)), ['AZ CD-1', 'CA CD-8', 'CA CD-17', 'FL CD-22'], 'flat order groups by state then natural district number');

// Generated pages embed the module and both readers use it for chips.
for (const page of ['index.html', 'ballot.html']) {
  const html = fs.readFileSync(root + page, 'utf8');
  assert.ok(html.includes('const ContestLabel'), page + ' must embed the shared contest label module');
}
assert.ok(fs.readFileSync(root + 'src/index.template.html', 'utf8').includes("node('span','district-chip',ContestLabel.districtLabel(p))"), 'Explorer cards render state-aware chips');
assert.ok(fs.readFileSync(root + 'src/ballot-page.js', 'utf8').includes('ContestLabel.districtLabel(position)'), 'Address reader renders state-aware district labels');

// On the real dataset: every printed CD/AD/SD label carries its state; stored values stay unprefixed.
const data = JSON.parse(fs.readFileSync(root + '2026-11-03_Bay_Area_Elections.json', 'utf8'));
let prefixed = 0;
for (const position of data.positions) {
  const seat = position.district_or_seat || '';
  if (/^(CD|SD|AD)-\d+$/.test(seat)) {
    prefixed++;
    const label = ContestLabel.districtLabel(position);
    assert.match(label, /^[A-Z]{2} (CD|SD|AD)-[1-9][0-9]*$/, position.id + ' legislative districts must render state-prefixed');
  }
}
assert.ok(prefixed >= 85, 'Regression must cover the full CD/AD/SD set (found ' + prefixed + ')');

const report = { passed: true, environment: 'Offline label/order regressions; display-only rendering, dataset labels unchanged', checks: ['state derivation from OCD identifiers with California county fallback', 'CD/AD/SD and Statewide labels carry the state; local seat labels stay plain', 'natural district order (CD-1 < CD-2 < CD-17) with states grouped first', 'both generated pages embed the module and both readers render through it', `all ${prefixed} printed legislative district rows render state-prefixed while stored values remain unprefixed`], districts_prefixed: prefixed };
fs.mkdirSync(root + '.checks', {recursive: true});
fs.writeFileSync(root + '.checks/contest_label_report.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report.checks));
