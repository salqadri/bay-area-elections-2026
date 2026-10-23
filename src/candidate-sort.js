/* Display-only candidate ordering inside a race, shared by both readers.
   Rules: a verified incumbent always leads; then higher reported total receipts
   (FEC or CAL-ACCESS — an unknown amount ranks below any reported figure);
   then more endorsement records; then Democratic or Republican affiliation
   before other parties and nonpartisan candidates; finally the candidate name.
   This never changes the dataset's stored roster order. */
const CandidateSort = (() => {
  const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });
  // DFL is Minnesota's official Democratic-Farmer-Labor ballot line.
  const majorParty = code => code === 'D' || code === 'R' || code === 'DFL';
  function reportedReceipts(candidate) {
    for (const record of [candidate.fec, candidate.ca_finance]) {
      if (record && Number.isFinite(record.receipts)) return record.receipts;
    }
    return null; // unknown is not zero: it ranks below every reported amount
  }
  function compare(a, b) {
    const incumbent = (b.incumbent === true ? 1 : 0) - (a.incumbent === true ? 1 : 0);
    if (incumbent) return incumbent;
    const raisedA = reportedReceipts(a), raisedB = reportedReceipts(b);
    if (raisedA !== raisedB) {
      if (raisedA === null) return 1;
      if (raisedB === null) return -1;
      return raisedB - raisedA;
    }
    const endorsements = (b.endorsements?.length || 0) - (a.endorsements?.length || 0);
    if (endorsements) return endorsements;
    const tier = (majorParty(a.party) ? 0 : 1) - (majorParty(b.party) ? 0 : 1);
    if (tier) return tier;
    return collator.compare(a.name, b.name);
  }
  return { compare, sortRoster: candidates => candidates.slice().sort(compare) };
})();
