'use strict';
(() => {
  const DATA = JSON.parse(document.getElementById('election-data').textContent);
  const $ = id => document.getElementById(id);
  const service = globalThis.ElectionAddressService;
  const matcher = globalThis.ElectionAddressMatcher;
  const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });
  const defaultLevels = ['Federal', 'State', 'State judiciary', 'County', 'City or town', 'Education', 'Special district'];
  const order = DATA.display_order || { levels: defaultLevels, state_categories: [], state_offices: [] };
  const levelOrder = new Map(order.levels.map((level, index) => [level, index]));
  const state = { request: 0, controller: null, estimates: [], current: null, lookup: null, groups: [] };
  let toastTimer;
  let addressAutocomplete;

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = String(text);
    return element;
  }
  function list(value) { return Array.isArray(value) ? value : value ? [value] : []; }
  function label(section, value) { return DATA.codes?.[section]?.[value] || value || ''; }
  function knownConfirmed(position) { return ['confirmed', 'confirmed_on_ballot'].includes(position.ballot_status); }
  function safeLink(url, text, className) {
    try {
      const parsed = new URL(url, location.href);
      if (!['http:', 'https:'].includes(parsed.protocol)) return node('span', className, text);
      const link = node('a', className, text);
      link.href = parsed.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      return link;
    } catch { return node('span', className, text); }
  }
  function partyLabel(code) {
    if (!code) return '';
    return DATA.codes?.party?.[code] || code;
  }
  function dateLabel(value) {
    if (!value) return 'date not supplied';
    return new Date(value + 'T12:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  }
  function evidenceDateLabel(evidence) {
    if (!evidence.date) return 'Date unverified';
    if (evidence.date_method === 'wayback_first_capture') return 'Observed by ' + evidence.date + ' (archive bound; original date unknown)';
    const methods = {page_metadata: 'page metadata date', x_snowflake: 'post date', event_recorded: 'event date'};
    const method = methods[evidence.date_method];
    return evidence.date + (method ? ' (' + method + ')' : '');
  }
  function ordinal(values, value) { const index = (values || []).indexOf(value); return index < 0 ? 999 : index; }
  function compareRaces(a, b) {
    const left = a.position, right = b.position;
    const leftLevel = label('government_level', left.government_level), rightLevel = label('government_level', right.government_level);
    let comparison = (levelOrder.get(leftLevel) ?? 99) - (levelOrder.get(rightLevel) ?? 99);
    if (comparison) return comparison;
    if (leftLevel === 'State') {
      comparison = ordinal(order.state_categories, label('office_category', left.office_category)) - ordinal(order.state_categories, label('office_category', right.office_category));
      if (comparison) return comparison;
      comparison = ordinal(order.state_offices, left.office) - ordinal(order.state_offices, right.office);
      if (comparison) return comparison;
    }
    if (leftLevel === 'State judiciary') {
      comparison = ordinal(['Supreme Court', 'Court of Appeal'], label('office_category', left.office_category)) - ordinal(['Supreme Court', 'Court of Appeal'], label('office_category', right.office_category));
      if (comparison) return comparison;
    }
    return collator.compare(left.jurisdiction, right.jurisdiction) || collator.compare(left.district_or_seat || '', right.district_or_seat || '') || collator.compare(left.office, right.office) || collator.compare(left.id, right.id);
  }
  function subgroup(position) {
    const level = label('government_level', position.government_level);
    const category = label('office_category', position.office_category);
    if (level === 'Federal') return '';
    if (level === 'State') return ['State Senate', 'State Assembly'].includes(category) ? category : 'Other state offices';
    if (['County', 'City or town'].includes(level)) return position.jurisdiction;
    return category;
  }
  function grouped(values, key) {
    const groups = new Map();
    for (const value of values) {
      const name = key(value);
      if (!groups.has(name)) groups.set(name, []);
      groups.get(name).push(value);
    }
    return groups;
  }
  function setLoading(loading) {
    $('find-ballot').disabled = loading;
    $('address-form').setAttribute('aria-busy', String(loading));
    $('lookup-status').textContent = loading ? 'Finding your address and districts…' : '';
  }
  function clearError() { $('lookup-error').hidden = true; $('lookup-error').textContent = ''; }
  function showError(message) { $('lookup-error').textContent = message; $('lookup-error').hidden = false; }
  function clearResults() {
    state.current = null;
    state.estimates = [];
    state.groups = [];
    $('ballot-results').hidden = true;
    $('ballot-primer').hidden = false;
    $('address-matches').hidden = true;
    $('address-match').replaceChildren();
    $('ballot-races').replaceChildren();
  }
  function addContext(labelText, value, className) {
    const values = list(value).filter(item => item !== null && item !== undefined && item !== '');
    const row = node('div', className);
    row.append(node('dt', null, labelText), node('dd', null, values.length ? values.join(' · ') : 'Not resolved'));
    $('ballot-context-values').append(row);
  }
  function renderContext(summary) {
    $('ballot-context-values').replaceChildren();
    if (!summary.manual) addContext(list(summary.matchedAddresses).length > 1 ? 'Matched addresses (combined)' : 'Matched address', summary.matchedAddresses, 'context-address');
    addContext('County', summary.counties);
    addContext('City or place', summary.places);
    const districts = summary.districts || {};
    addContext('Congressional district reported by Census', list(districts.CD).map(value => 'CD-' + value));
    addContext('State Assembly', list(districts.AD).map(value => 'AD-' + value));
    addContext('State Senate', list(districts.SD).map(value => 'SD-' + value));
    addContext('School districts reported by Census', summary.schoolDistricts);
  }
  function raceCard(race) {
    const position = race.position;
    const card = node('article', 'ballot-race');
    card.dataset.contestId = position.id;
    card.setAttribute('data-contest-id', position.id);
    card.dataset.confidence = race.confidence;
    card.setAttribute('data-confidence', race.confidence);
    const top = node('div', 'ballot-race-top');
    top.append(node('span', 'ballot-race-category', label('office_category', position.office_category)), node('span', 'ballot-race-district', position.district_or_seat || ''));
    card.append(top, node('h4', null, position.office), node('p', 'ballot-race-jurisdiction', position.jurisdiction));
    const metadata = node('p', 'ballot-race-meta');
    metadata.append(node('span', null, position.election_type === 'retention' ? 'Yes / No retention vote' : Number.isInteger(position.seats) ? position.seats + (position.seats === 1 ? ' seat' : ' seats') : 'Seat count unresolved'));
    if (position.term) metadata.append(node('span', null, position.term));
    if (position.election_type) metadata.append(node('span', null, label('election_type', position.election_type)));
    card.append(metadata);
    const confidence = race.confidence === 'expected' ? 'Expected geographic match' : race.confidence === 'district_uncertain' ? 'Possible · district uncertain' : 'Possible · membership uncertain';
    card.append(node('span', 'ballot-confidence' + (race.confidence === 'expected' ? '' : ' possible'), confidence));
    if (race.reason) card.append(node('p', 'ballot-reason', race.reason));
    if (!knownConfirmed(position)) card.append(node('p', 'ballot-unverified', 'Ballot appearance unresolved: this scheduled contest is not confirmed on the November ballot.'));
    if (Array.isArray(position.candidates) && position.candidates.length) {
      const candidates = node('ul', 'ballot-candidates');
      candidates.setAttribute('aria-label', 'Candidates');
      for (const candidate of position.candidates) {
        const row = node('li');
        row.append(node('span', 'ballot-candidate-name', candidate.name));
        if (candidate.party) row.append(node('span', 'ballot-candidate-party', partyLabel(candidate.party)));
        if (candidate.incumbent === true) row.append(node('span', 'pill incumbent', 'Incumbent'));
        if (candidate.campaign_url) { const w = node('a', 'ballot-candidate-x', 'Site ↗'); w.href = candidate.campaign_url; w.target = '_blank'; w.rel = 'noopener noreferrer'; row.append(w); }
        if (candidate.x_url) { const x = node('a', 'ballot-candidate-x', candidate.secondary_x_url ? 'X @' + candidate.x_url.split('/').pop() + ' ↗' : 'X ↗'); x.href = candidate.x_url; x.target = '_blank'; x.rel = 'noopener noreferrer'; row.append(x); }
        if (candidate.secondary_x_url) { const x2 = node('a', 'ballot-candidate-x', 'X @' + candidate.secondary_x_url.split('/').pop() + ' ↗'); x2.href = candidate.secondary_x_url; x2.target = '_blank'; x2.rel = 'noopener noreferrer'; row.append(x2); }
        if (candidate.gaza_evidence?.length) {
          const det = node('details', 'ballot-candidate-evidence');
          det.append(node('summary', null, 'Gaza stance research · ' + candidate.gaza_evidence.length + ' items (ungraded)'));
          for (const e of candidate.gaza_evidence) {
            const li = node('p', null, evidenceDateLabel(e) + ' — ' + e.summary);
            li.append(' ', safeLink(e.url, 'source ↗'));
            det.append(li);
          }
          row.append(det);
        }
        if (candidate.endorsements?.length) {
          const en = node('details', 'ballot-candidate-endorsements');
          en.append(node('summary', null, EndorsementDisplay.summary(candidate.endorsements)));
          for (const r of candidate.endorsements) {
            const li = node('p', null, EndorsementDisplay.label(r));
            li.append(' ', safeLink(r.url, 'source ↗'));
            if (r.note_id && DATA.notes[r.note_id]) li.append(node('span', null, ' — ' + DATA.notes[r.note_id]));
            en.append(li);
          }
          row.append(en);
        }
        candidates.append(row);
      }
      card.append(candidates);
    } else card.append(node('p', 'ballot-roster-unverified', 'Candidate roster has not been verified.'));
    if (position.election_type === 'retention') card.append(node('p', 'ballot-reason', 'Judicial retention: voters decide whether the listed justice should remain in office.'));
    const detailLink = node('a', 'ballot-contest-link', 'Candidates, sources & full race details ↗');
    detailLink.href = './index.html#' + new URLSearchParams({ id: position.id, status: 'all' }).toString();
    detailLink.target = '_blank';
    detailLink.rel = 'noopener noreferrer';
    card.append(detailLink);
    return card;
  }
  function renderRaces(races) {
    $('ballot-races').replaceChildren();
    state.groups = [];
    const sorted = [...races].sort(compareRaces);
    for (const [level, values] of grouped(sorted, race => label('government_level', race.position.government_level))) {
      const section = node('details', 'ballot-group');
      section.open = !['Education', 'Special district'].includes(level);
      section.dataset.level = level;
      section.setAttribute('data-level', level);
      const summary = node('summary');
      summary.append(node('span', null, level), node('span', 'ballot-group-count', values.length + ' ' + (values.length === 1 ? 'race' : 'races')));
      const body = node('div', 'ballot-group-body');
      for (const [name, records] of grouped(values, race => subgroup(race.position))) {
        const group = node('section', 'ballot-subsection');
        if (name) group.append(node('h3', null, name));
        const grid = node('div', 'ballot-race-grid');
        for (const race of records) grid.append(raceCard(race));
        group.append(grid);
        body.append(group);
      }
      section.append(summary, body);
      state.groups.push(section);
      $('ballot-races').append(section);
    }
  }
  function renderOfficial(counties) {
    const links = $('ballot-official-links');
    links.replaceChildren();
    const urls = DATA.address_lookup?.county_election_urls || {};
    const names = counties.length ? counties : (DATA.election.counties_in_scope || []).map(county => county.name);
    for (const county of names) {
      const entry = urls[county];
      const url = typeof entry === 'string' ? entry : entry?.url;
      if (url) links.append(safeLink(url, county + ' elections ↗'));
    }
    if (!links.children.length) links.append(safeLink('https://www.sos.ca.gov/elections/voting-resources/county-elections-offices', 'California county elections offices ↗'));
  }
  function renderEstimate(estimate, multipleUnion) {
    state.current = estimate;
    const summary = estimate.summary || {};
    const races = estimate.races || [];
    const counts = estimate.counts || {};
    $('ballot-results').hidden = false;
    $('ballot-primer').hidden = true;
    $('estimate-kicker').textContent = summary.manual ? 'County possibilities' : multipleUnion ? 'Combined address estimate' : 'Address estimate';
    $('ballot-results-title').textContent = summary.manual ? 'Possible races across this county' : multipleUnion ? 'Possible ballot across all matches' : 'Your expected ballot';
    $('ballot-results-subtitle').textContent = summary.manual ? 'County browsing is intentionally broad. Many listed races will not apply to your address.' : 'This is an estimate of elected offices, not an official ballot. Eligibility depends on your exact district and registration.';
    $('expected-count').textContent = (counts.expected || 0).toLocaleString();
    $('possible-count').textContent = (counts.possible || 0).toLocaleString();
    $('scheduled-count').textContent = (counts.scheduled || 0).toLocaleString();
    $('ballot-result-count').textContent = races.length.toLocaleString() + ' ' + (races.length === 1 ? 'race retained' : 'races retained') + ' · Office priority order';
    $('ballot-result-toolbar').hidden = !races.length;
    $('ballot-stats').hidden = estimate.status !== 'ok';
    $('download-estimate').disabled = !races.length;
    renderContext(summary);
    const warnings = [...list(estimate.warnings)];
    if (multipleUnion) warnings.unshift('Multiple addresses matched. This view combines every match, so it may include races from different districts. Choose a specific address above to narrow the estimate.');
    if ((counts.possible || 0) > 0 || summary.manual) warnings.unshift('Not all possible races listed here will appear on your ballot. Where a district is uncertain, every plausible alternative is retained; you may vote in only one of them.');
    $('ballot-warning-list').replaceChildren();
    for (const warning of [...new Set(warnings)]) $('ballot-warning-list').append(node('li', null, warning));
    $('ballot-warnings').hidden = !warnings.length;
    renderRaces(races);
    $('ballot-empty').hidden = races.length > 0;
    if (!races.length) {
      const outside = estimate.status === 'outside_scope';
      const needsCounty = estimate.status === 'needs_county';
      $('ballot-empty-title').textContent = outside ? 'This address is outside the current coverage' : needsCounty ? 'We could not resolve a covered county' : 'No races could be matched reliably';
      $('ballot-empty-description').textContent = outside ? 'The explorer currently covers five Bay Area counties. This result does not mean there are no elections at this address. Contact the appropriate county elections office for its official ballot.' : needsCounty ? 'Check the matched address and try a full street address with city, state, and ZIP code. You can also browse county possibilities above. An unresolved lookup does not mean there are no elections.' : 'The available address geography and election inventory did not produce a reliable match. Try county browsing or confirm your official ballot with your county elections office.';
    }
    renderOfficial(list(summary.counties));
  }
  function revealResults() {
    $('ballot-results-title').focus({ preventScroll: true });
    $('ballot-results').scrollIntoView({ behavior: 'auto', block: 'start' });
  }
  async function lookupAddress(event) {
    event.preventDefault();
    addressAutocomplete?.close();
    const address = $('voting-address').value.trim();
    clearError();
    if (!address) { showError('Enter your voting address, including the street number and city.'); $('voting-address').focus(); return; }
    const request = ++state.request;
    if (state.controller) state.controller.abort();
    state.controller = new AbortController();
    state.lookup = null;
    clearResults();
    setLoading(true);
    try {
      if (!service || !matcher) throw new Error('The address lookup could not load. Reload this page and try again.');
      const response = await service.lookup(address, { signal: state.controller.signal, timeoutMs: 25000 });
      if (request !== state.request) return;
      state.lookup = { provider: response.provider, benchmark: response.benchmark, vintage: response.vintage, layers: response.layers, queriedAt: response.queriedAt };
      const matches = Array.isArray(response.matches) ? response.matches : [];
      if (!matches.length) {
        showError('No matching address was returned. Check the street number, city, state, and ZIP code, then try again. This does not mean there are no races at your address. County browsing below is available if the address cannot be resolved.');
        return;
      }
      state.estimates = matches.map(match => matcher.estimateBallot(DATA, matcher.geographyFromMatch(match)));
      if (matches.length > 1) {
        const selector = $('address-match');
        const all = node('option', null, 'All matches (broader estimate)');
        all.value = 'all';
        selector.append(all);
        state.estimates.forEach((estimate, index) => {
          const addressText = list(estimate.summary?.matchedAddresses).join(' · ') || matches[index].matchedAddress || 'Address match ' + (index + 1);
          const option = node('option', null, (index + 1) + '. ' + addressText);
          option.value = String(index);
          selector.append(option);
        });
        selector.value = 'all';
        $('address-matches').hidden = false;
        renderEstimate(matcher.combineEstimates(DATA, state.estimates), true);
      } else renderEstimate(state.estimates[0], false);
      revealResults();
    } catch (error) {
      if (request !== state.request) return;
      if (error?.name === 'AbortError') showError('The lookup was interrupted. Please try again, or browse county possibilities below.');
      else showError('Address lookup is temporarily unavailable. Please try again, or browse county possibilities below. Your official ballot is available from your county elections office.');
    } finally {
      if (request === state.request) { setLoading(false); state.controller = null; }
    }
  }
  function chooseMatch() {
    if (!state.estimates.length) return;
    const value = $('address-match').value;
    if (value === 'all') renderEstimate(matcher.combineEstimates(DATA, state.estimates), true);
    else {
      const index = Number(value);
      if (Number.isInteger(index) && state.estimates[index]) renderEstimate(state.estimates[index], false);
    }
  }
  function browseCounty() {
    addressAutocomplete?.close();
    clearError();
    const county = $('manual-county').value;
    if (!county) { showError('Choose a county to browse its possible races.'); $('manual-county').focus(); return; }
    ++state.request;
    if (state.controller) state.controller.abort();
    state.controller = null;
    state.lookup = null;
    clearResults();
    setLoading(false);
    if (!matcher) { showError('The ballot matcher could not load. Reload this page and try again.'); return; }
    renderEstimate(matcher.estimateBallot(DATA, matcher.manualCounty(county)), false);
    revealResults();
  }
  function downloadEstimate() {
    if (!state.current?.races?.length) return;
    const estimate = state.current;
    const summary = estimate.summary || {};
    const exportData = {
      format: 'bay-area-ballot-estimate/v1',
      election_date: DATA.election.date,
      research_as_of: DATA.election.research_as_of,
      generated_at: new Date().toISOString(),
      method: 'Conservative geography estimate; not an official ballot. Raw addresses and coordinates are omitted.',
      geography_source: state.lookup,
      geography: { counties: summary.counties || [], places: summary.places || [], districts: summary.districts || {}, school_districts: summary.schoolDistricts || [], manual_county_selection: Boolean(summary.manual) },
      warnings: [...$('ballot-warning-list').children].map(item => item.textContent),
      counts: estimate.counts,
      races: estimate.races,
      codes: DATA.codes,
      defaults: DATA.defaults,
      finance: DATA.finance,
      notes: DATA.notes,
      sources: DATA.sources
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2) + '\n'], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = node('a');
    anchor.href = url;
    anchor.download = DATA.election.date + '-estimated-ballot.json';
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    clearTimeout(toastTimer);
    $('ballot-toast').textContent = 'Estimate downloaded. Your street address was not included.';
    $('ballot-toast').hidden = false;
    toastTimer = setTimeout(() => { $('ballot-toast').hidden = true; }, 3500);
  }

  for (const county of DATA.election.counties_in_scope || []) {
    const option = node('option', null, county.name);
    option.value = county.name;
    $('manual-county').append(option);
  }
  $('ballot-coverage').textContent = 'Coverage: ' + (DATA.election.counties_in_scope || []).map(county => county.name).join(', ') + ' counties.';
  $('ballot-footer-date').textContent = 'Election: ' + dateLabel(DATA.election.date) + ' · Election research: ' + dateLabel(DATA.election.research_as_of) + '. Estimates are not official ballots.';
  if (globalThis.ElectionAddressAutocomplete && globalThis.ElectionAddressSuggestions) {
    addressAutocomplete = globalThis.ElectionAddressAutocomplete.attach({
      input: $('voting-address'),
      listbox: $('address-suggestions'),
      status: $('address-suggestion-status'),
      lookup: (query, options) => globalThis.ElectionAddressSuggestions.lookup(query, options)
    });
  }
  $('address-form').addEventListener('submit', lookupAddress);
  $('address-match').addEventListener('change', chooseMatch);
  $('browse-county').addEventListener('click', browseCounty);
  $('ballot-expand-all').addEventListener('click', () => { for (const group of state.groups) group.open = true; });
  $('ballot-collapse-all').addEventListener('click', () => { for (const group of state.groups) group.open = false; });
  $('download-estimate').addEventListener('click', downloadEstimate);
})();
