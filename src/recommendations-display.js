'use strict';
/* Recommendations reader: renders the per-race recommendation cards from the embedded plan data.
   Display-only — all decisions and summaries come pre-computed from the research pipeline. */
(() => {
  const DATA = JSON.parse(document.getElementById('rec-data').textContent);
  const RACES = DATA.races || [];
  const collator = new Intl.Collator('en', {numeric: true, sensitivity: 'base'});
  const listEl = document.getElementById('rec-list');
  const officeSel = document.getElementById('rec-office-filter');
  const searchEl = document.getElementById('rec-search');
  const picksOnly = document.getElementById('rec-only-picks');

  const PARTIES = {D: 'Democrat', R: 'Republican', I: 'Independent', L: 'Left Party', N: 'No Party'};

  function gradeBadge(g) {
    const cls = g ? 'grade-' + String(g).toLowerCase().replace(/[^a-z]/g, '') : 'grade-na';
    return `<span class="grade ${cls}">${g ? g : 'N/A'}</span>`;
  }
  function partyLabel(party) {
    if (!party) return '';
    return PARTIES[party] || (party === 'NP' ? 'Nonpartisan' : party);
  }
  function districtText(r) {
    const label = ContestLabel.districtLabel(r);
    if (label) return r.office + (r.district_or_seat ? ' — ' + label : '');
    const seat = r.district_or_seat || (r.counties && r.counties.length === 1 ? r.counties[0] : '');
    return seat ? r.office + ' — ' + seat : r.office;
  }
  function searchHit(r) {
    const hay = [r.office, r.jurisdiction, r.district_or_seat, (r.counties || []).join(' '),
      r.recommended || '', (r.muslim_candidate || ''), (r.category || '')]
      .concat((r.roster || []).map(c => c.name || ''))
      .join(' ').toLowerCase();
    return hay;
  }
  function badges(r) {
    if (r.ballot_status === 'excluded') return '<span class="badge badge-excluded">Not on ballot</span>';
    if (r.category === 'muslim_community') return '<span class="badge badge-muslim">Muslim community</span>';
    if (r.category === 'jev_pick') return '<span class="badge badge-jev">Jev pick</span>';
    if (r.category === 'no_good_candidate') return '<span class="badge badge-nogood">No good candidate</span>';
    return '<span class="badge badge-noinfo">No information</span>';
  }
  function rosterRows(r) {
    const roster = r.roster || [];
    if (!roster.length) return '';
    return '<div class="rec-roster"><p class="roster-title">On the ballot</p>' + roster.map(c => {
      const win = r.recommended === c.name;
      const party = partyLabel(c.party);
      return `<div class="roster-row${win ? ' win' : ''}">${gradeBadge(c.grade)}<span class="roster-name">${c.name}</span>`
        + (party ? `<span class="roster-party">· ${party}</span>` : '')
        + (win ? `<span class="win-flag${r.category === 'muslim_community' ? '' : ' flag-jev'}">Recommended</span>` : '')
        + '</div>';
    }).join('') + '</div>';
  }
  function card(r) {
    const cls = r.ballot_status === 'excluded' ? 'rec-none'
      : r.category === 'muslim_community' ? 'rec-muslim'
      : r.category === 'jev_pick' ? 'rec-jev' : 'rec-none';
    let who;
    if (r.recommended) {
      const c = (r.roster || []).find(x => x.name === r.recommended);
      const grade = c ? gradeBadge(c.grade) : '';
      const party = c ? partyLabel(c.party) : '';
      who = `<p class="rec-who">Support <span class="who-name">${r.recommended}</span>${grade}${party ? ` <span class="roster-party">· ${party}</span>` : ''}</p>`;
    } else {
      who = '<p class="rec-who">No recommendation.</p>';
    }
    const note = r.category === 'no_information'
      ? '<div class="rec-note none">No recommendation due to a lack of information about this race.</div>'
      : r.category === 'no_good_candidate'
        ? '<div class="rec-note none">No recommendation due to a lack of known good candidates.</div>'
        : '';
    const summary = (r.summary && r.summary.text)
      ? `<div class="rec-note"><strong>Why:</strong> ${r.summary.text}</div>` : '';
    const jev = (r.jev && r.jev.confidence != null && r.category === 'jev_pick')
      ? `<p class="rec-jev">Jev decision model: confidence ${(r.jev.confidence * 100).toFixed(0)}% <code>${r.jev.model}</code></p>` : '';
    const reason = (r.recommended && r.category === 'muslim_community')
      ? '<p class="rec-reason">Confirmed member of the Muslim community.</p>' : '';
    const view = `<p class="rec-meta"><a href="./index.html#${encodeURIComponent('id=' + r.position_id)}">View race details in the explorer →</a></p>`;
    const excluded = r.ballot_status === 'excluded'
      ? '<div class="rec-note">Confirmed not on the November ballot.</div>' : '';
    return `<article class="rec-card ${cls}" id="rec-${r.position_id}"><div class="rec-head"><div><h2 class="rec-office">${districtText(r)}</h2><p class="rec-district">${r.jurisdiction || (r.counties || []).join(' + ')}</p></div><div class="rec-badges">${badges(r)}</div></div>`
      + who + reason + jev + note + summary + excluded + rosterRows(r) + view + '</article>';
  }

  // Office filter: distinct office_category values in stable order.
  const cats = [...new Set(RACES.map(r => r.office_category || 'Uncategorized'))].sort((a, b) => collator.compare(a, b));
  officeSel.innerHTML = '<option value="">All offices</option>' + cats.map(c => `<option value="${c}">${c}</option>`).join('');

  function visible() {
    const q = searchEl.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const office = officeSel.value;
    const only = picksOnly.checked;
    return RACES.filter(r => {
      if (office && (r.office_category || 'Uncategorized') !== office) return false;
      if (only && !r.recommended) return false;
      if (q.length && !q.every(t => searchHit(r).includes(t))) return false;
      return true;
    });
  }
  function render() {
    const rows = visible();
    const wrap = document.createElement('div');
    wrap.innerHTML = rows.map(card).join('');
    listEl.replaceChildren(...wrap.children);
    document.getElementById('footer-stats').textContent =
      `Showing ${rows.length} of ${RACES.length} evaluated races · ${DATA.counts ? Object.values(DATA.counts).reduce((a, b) => a + b, 0) : RACES.length} total`;
  }
  officeSel.addEventListener('change', render);
  searchEl.addEventListener('input', render);
  picksOnly.addEventListener('change', render);

  // Hero stats from the plan's counts.
  const c = DATA.counts || {};
  const stats = [
    ['Recommended candidates', (c.jev_pick || 0) + (c.muslim_community || 0)],
    ['No good candidate', c.no_good_candidate || 0],
    ['No information', c.no_information || 0]
  ];
  document.getElementById('hero-stats').replaceChildren(
    ...stats.map(([label, n]) => {
      const d = document.createElement('div');
      d.className = 'chip-stat';
      d.appendChild(Object.assign(document.createElement('b'), {textContent: n}));
      d.appendChild(document.createTextNode(label));
      return d;
    }));

  render();
  // Deep links: #rec-<position_id> or #id=<position_id>.
  const hash = decodeURIComponent(location.hash.slice(1));
  const mId = /(^|&)id=([^&]+)/.exec(hash) || (/^rec-(.+)$/.exec(hash));
  if (mId) {
    const target = document.getElementById('rec-' + (mId[2] || mId[1]));
    if (target) requestAnimationFrame(() => target.scrollIntoView({behavior: 'smooth', block: 'center'}));
  }
})();
