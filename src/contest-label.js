/* Shared contest-state derivation, district labels and natural ordering for both readers.
   Display-only: the dataset's stored district_or_seat values and roster order are untouched. */
const ContestLabel = (() => {
  const STATE_NAMES = {AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',DC:'District of Columbia',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming'};
  // Federal and California legislative district codes are ambiguous across states, so they carry the state prefix.
  const PREFIXED = /^(CD|SD|AD)-\d+$/;

  function stateCode(p) {
    const match = /state:([a-z]{2})/.exec((p && p.ocd_division_id) || '');
    if (match) return match[1].toUpperCase();
    // Local Bay Area districts without an OCD identifier are California-only electorates.
    return (p && p.counties && p.counties.length) ? 'CA' : '';
  }
  function stateName(p) { const code = stateCode(p); return STATE_NAMES[code] || ''; }
  function stateLabel(code) { return STATE_NAMES[code] || code; }

  function districtLabel(p) {
    const seat = (p && p.district_or_seat) || '';
    if (!seat) return '';
    const code = stateCode(p);
    if (PREFIXED.test(seat)) return code ? code + ' ' + seat : seat;
    if (/Statewide/.test(seat)) {
      // "AL — Statewide" already names its state; bare "Statewide" is California's.
      if (/^[A-Z]{2}\s*—/.test(seat) || !code) return seat;
      return code + ' — ' + seat;
    }
    return seat;
  }

  // Natural compare: digit runs sort by value so CA CD-1 precedes CA CD-17.
  function naturalCompare(a, b) {
    const left = String(a || ''), right = String(b || '');
    const parts = s => s.match(/\d+|\D+/g) || [];
    const x = parts(left), y = parts(right);
    for (let i = 0; i < Math.max(x.length, y.length); i++) {
      const l = x[i], r = y[i];
      if (l === undefined) return -1;
      if (r === undefined) return 1;
      const ln = /^\d+$/.test(l), rn = /^\d+$/.test(r);
      if (ln && rn) { const d = Number(l) - Number(r); if (d) return d < 0 ? -1 : 1; continue; }
      if (l !== r) return l < r ? -1 : 1;
    }
    return left === right ? 0 : (left < right ? -1 : 1);
  }

  // Jurisdiction → state → natural district order shared by every list sort.
  function contestOrder(a, b, collator) {
    const j = collator.compare(a.jurisdiction, b.jurisdiction);
    if (j) return j;
    const s = collator.compare(stateCode(a), stateCode(b));
    if (s) return s;
    return naturalCompare((a.district_or_seat || ''), (b.district_or_seat || ''))
      || collator.compare(a.office, b.office);
  }

  return {stateCode, stateName, stateLabel, districtLabel, naturalCompare, contestOrder};
})();
