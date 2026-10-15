/* Both readers use the same dated receipts and independent-spending disclosure. */
const CampaignFinanceDisplay = {
  render(candidate, data, {node, link, dateLabel}) {
    const money = [];
    const currency = data.finance?.currency || data.ie_finance?.currency || 'USD';
    const format = value => new Intl.NumberFormat('en-US', {style: 'currency', currency}).format(value);
    if (candidate.fec) {
      const f = candidate.fec;
      const box = node('div', 'fundraising');
      const known = typeof f.receipts === 'number' && Number.isFinite(f.receipts);
      box.append(node('p', 'fundraising-label', 'Campaign receipts · FEC'));
      box.append(node('p', 'fundraising-amount' + (known ? '' : ' unavailable'), known ? format(f.receipts) : 'No published total available'));
      if (known) box.append(node('p', 'fundraising-dates', dateLabel(f.from) + ' – ' + dateLabel(f.through)));
      if (data.finance?.checked_on) box.append(node('p', 'fundraising-dates', 'Checked ' + dateLabel(data.finance.checked_on)));
      const source = data.sources[f.source_id];
      if (source) box.append(link(source.url, 'View FEC source ↗'));
      if (f.note_id) box.append(node('p', 'fundraising-note', data.notes[f.note_id]));
      money.push(box);
    }
    if (candidate.independent_expenditures && data.ie_finance) {
      const ie = candidate.independent_expenditures, cfg = data.ie_finance;
      const box = node('div', 'ie-spend');
      box.append(node('p', 'ie-label', 'Independent outside spending · FEC ' + cfg.cycle + ' cycle'));
      if (!ie.items.length) box.append(node('p', 'ie-note', 'No itemized independent expenditures reported for or against this candidate in the current cycle.'));
      else {
        const totals = node('p', 'ie-totals');
        if (ie.for_total > 0) totals.append(node('span', 'ie-for', 'For: ' + format(ie.for_total)));
        if (ie.against_total > 0) totals.append(node('span', 'ie-against', 'Against: ' + format(ie.against_total)));
        box.append(totals);
        const list = node('ul', 'ie-list');
        for (const item of ie.items) {
          const li = node('li');
          const spender = data.ie_spenders[item.spender_id];
          const name = spender?.source_url ? link(spender.source_url, spender.name, 'inline-source ie-name') : node('span', 'ie-name', spender?.name || item.spender_id);
          if (spender?.committee_type) name.append(node('span', null, ' · ' + spender.committee_type));
          li.append(name, node('span', 'ie-amt', (item.direction === 'against' ? '- ' : '+ ') + format(item.amount)));
          list.append(li);
        }
        box.append(list);
      }
      if (cfg.checked_on) box.append(node('p', 'ie-note', 'Checked ' + dateLabel(cfg.checked_on)));
      if (ie.browse_url) box.append(link(ie.browse_url, 'All independent expenditures for this candidate on FEC.gov ↗'));
      const source = data.sources[cfg.source_id];
      if (source) box.append(link(source.url, 'View FEC source ↗'));
      box.append(node('p', 'ie-note', cfg.method));
      money.push(box);
    }
    if (!money.length) return null;
    const disclosure = node('details', 'candidate-evidence campaign-money');
    disclosure.append(node('summary', null, 'Campaign money · receipts and independent spending'));
    for (const box of money) disclosure.append(box);
    return disclosure;
  }
};
