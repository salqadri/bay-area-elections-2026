/* Shared, attributed Gaza evidence layers. Text and links are created as DOM nodes. */
const GazaEvidenceDisplay = {
  actionDate(metadata = {}) {
    const label = String(metadata.date || metadata.date_label || '').trim();
    const unknown = {start:null,end:null,precision:'unknown'};
    const iso = (year,month,day) => {
      const value = new Date(0);value.setUTCHours(0,0,0,0);value.setUTCFullYear(year,month-1,day);
      return year>=1&&year<=9999&&value.getUTCFullYear()===year&&value.getUTCMonth()===month-1&&value.getUTCDate()===day
        ? `${String(year).padStart(4,'0')}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}` : null;
    };
    let match;
    if((match=/^(\d{4})-(\d{2})-(\d{2})$/.exec(label))){const value=iso(...match.slice(1).map(Number));return value?{start:value,end:value,precision:'day'}:unknown;}
    if((match=/^(\d{4})\s*[-–—]\s*(\d{4})$/.exec(label))){const first=Number(match[1]),last=Number(match[2]),start=iso(first,1,1),end=iso(last,12,31);return start&&end&&first<=last?{start,end,precision:'period'}:unknown;}
    if((match=/^(\d{4})-(\d{2})$/.exec(label))){const year=Number(match[1]),month=Number(match[2]),start=iso(year,month,1);if(!start)return unknown;const end=new Date(0);end.setUTCHours(0,0,0,0);end.setUTCFullYear(year,month,0);return {start,end:iso(year,month,end.getUTCDate()),precision:'month'};}
    if(/^\d{4}$/.test(label)){const start=iso(Number(label),1,1),end=iso(Number(label),12,31);return start&&end?{start,end,precision:'year'}:unknown;}
    if((match=/^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$/.exec(label))){const month=['january','february','march','april','may','june','july','august','september','october','november','december'].indexOf(match[1].toLowerCase())+1;const value=month&&iso(Number(match[3]),month,Number(match[2]));return value?{start:value,end:value,precision:'day'}:unknown;}
    return unknown;
  },
  orderedActions(records, registry = {}) {
    const entries = records.flatMap(record=>(record.actions||[]).map(item=>({record,item,action:registry[item.action_id]||{}})));
    return entries.map((entry,index)=>({...entry,index,date:this.actionDate(entry.action)})).sort((a,b)=>
      Number(b.date.precision==='day')-Number(a.date.precision==='day')||
      String(b.date.start||'').localeCompare(String(a.date.start||''))||a.index-b.index);
  },
  render(candidate, data, {node, link, dateLabel, evidenceDateLabel, className = 'candidate-evidence gaza-evidence'}) {
    const profile = candidate.uscpr_grade;
    const records = candidate.gaza_voting_records || [];
    const platform = candidate.gaza_platform;
    const evidence = candidate.gaza_evidence || [];
    if (!profile && !records.length && !platform && !evidence.length) return null;
    const disclosure = node('details', className);
    disclosure.append(node('summary', null, 'Gaza evidence · Israel / Palestine'));
    const section = title => {
      const element = node('section', 'gaza-section');
      element.append(node('h4', 'gaza-heading', title));
      disclosure.append(element);
      return element;
    };
    // Guard here as well as in each reader's general-purpose link helper.
    const sourceLink = (url, text) => {
      try {
        const parsed = new URL(url);
        if (['http:', 'https:'].includes(parsed.protocol)) return link(parsed.href, text, 'gaza-source');
      } catch {}
      return node('span', 'gaza-source', text + ' (link unavailable)');
    };
    const checked = (element, value) => {
      if (value) element.append(node('p', 'gaza-note', 'Snapshot checked ' + dateLabel(value)));
    };
    if (profile) {
      const cfg = data.uscpr_scorecard || {};
      const box = section('USCPR Grade');
      box.append(node('p', 'gaza-note', 'USCPR Action’s publisher assessment combines votes, letters and other legislative actions.'));
      for (const grade of profile.grades || []) {
        const row = node('p', 'gaza-grade-item');
        row.append(node('span', 'gaza-grade-period', grade.period + ': '));
        const known = ['A', 'B', 'C', 'D', 'F'].includes(grade.grade);
        row.append(node('strong', 'gaza-grade', known ? grade.grade : 'Not graded (publisher: ' + (grade.source_grade || 'not supplied') + ')'));
        if (known && typeof grade.score === 'number' && Number.isFinite(grade.score)) row.append(node('span', null, ' · ' + grade.score + '%'));
        box.append(row);
      }
      if (cfg.scope_note) box.append(node('p', 'gaza-note', cfg.scope_note));
      checked(box, profile.checked_on || cfg.checked_on);
      const links = node('p', 'gaza-links');
      if (profile.source_url || cfg.source_url) links.append(sourceLink(profile.source_url || cfg.source_url, 'USCPR Action scorecard ↗'));
      if (cfg.methodology_url) links.append(' · ', sourceLink(cfg.methodology_url, 'Grading methodology ↗'));
      box.append(links);
    } else if (records.length && data.uscpr_scorecard) {
      const box = section('USCPR Grade');
      box.append(node('p', 'gaza-note', 'No USCPR grade has been captured for this candidate. A missing grade does not establish a position.'));
      checked(box, data.uscpr_scorecard.checked_on);
      box.append(sourceLink(data.uscpr_scorecard.source_url, 'USCPR Action scorecard ↗'));
    }
    if (records.length) {
      const cfg = data.gaza_voting || {};
      const box = section('Congressional voting / legislative record');
      box.append(node('p', 'gaza-note', cfg.scope_note || 'Selected actions tracked by the source sheet; votes, sponsorships and letters are distinct. This is a source snapshot rather than a complete career record.'));
      const legend = node('p', 'gaza-note');
      legend.append('Sheet assessments: ', node('span', 'gaza-assessment positive', 'positive'), ' / ', node('span', 'gaza-assessment negative', 'negative'), ' / ', node('span', 'gaza-assessment neutral', 'neutral or unclassified'), '. Colors follow the sheet’s assessment of each response.');
      box.append(legend);
      const snapshots = node('details', 'gaza-record-sources');
      snapshots.append(node('summary', null, 'Source tracker snapshots · ' + records.length));
      for (const record of records) {
        const actions = record.actions || [];
        snapshots.append(node('p', 'gaza-note', (record.sheet_title || 'Source') + ' tracker tab · ' + actions.length + ' tracked actions'));
        const memberContext = [record.member_name, record.district || record.state].filter(Boolean).join(' · ');
        snapshots.append(node('p', 'gaza-note', 'Source member: ' + memberContext + ' · ' + record.sheet_title));
        checked(snapshots, record.checked_on || cfg.checked_on);
        if (record.source_url || cfg.source_url) {
          const source = node('p', 'gaza-links');
          source.append(sourceLink(record.source_url || cfg.source_url, 'Source sheet ↗'));
          snapshots.append(source);
        }
      }
      box.append(snapshots);
      const entries = this.orderedActions(records, cfg.actions);
      for (const dated of [true, false]) {
        const selected = entries.filter(entry=>(entry.date.precision==='day')===dated);
        if (!selected.length) continue;
        const group = node('details', 'gaza-record');
        group.append(node('summary', null, (dated ? 'Dated actions · ' : 'Period-only or undated actions · ') + selected.length));
        if (!dated) group.append(node('p', 'gaza-note', 'The source gives a period or incomplete date, not an exact action date. These entries follow dated actions; a Congress period is not a vote timestamp.'));
        const list = node('ul', 'gaza-action-list');
        for (const {record, item, action} of selected) {
          const row = node('li', 'gaza-action');
          row.append(node('p', 'gaza-action-title', action?.title || 'Tracked action ' + item.action_id));
          const kinds = {roll_call_vote: 'Recorded vote', committee_vote: 'Committee vote', sponsorship: 'Sponsorship', petition_signature: 'Petition signature', letter: 'Letter', statement: 'Statement'};
          const context = [kinds[action?.kind] || action?.kind, action?.date || action?.date_label, record.sheet_title].filter(Boolean);
          if (context.length) row.append(node('p', 'gaza-action-context', context.join(' · ')));
          const value = node('p', 'gaza-action-value');
          value.append(node('strong', null, item.value?.trim() || 'No entry recorded'));
          const assessment = ['positive', 'negative', 'neutral'].includes(item.assessment) ? item.assessment : 'unclassified';
          const badge = node('span', 'gaza-assessment ' + assessment, 'Sheet: ' + assessment);
          const bases = {sheet_dropdown: 'Source dropdown color', sheet_conditional_format: 'Source conditional color', sheet_fill: 'Source cell color', explicit_label: 'Explicit source label', none: 'No classified source color'};
          if (bases[item.assessment_basis]) badge.setAttribute('title', bases[item.assessment_basis]);
          value.append(' ', badge);
          row.append(value);
          if (item.note) row.append(node('p', 'gaza-note', item.note));
          for (const note of action?.notes || []) row.append(node('p', 'gaza-note', note));
          const links = node('p', 'gaza-links');
          if (item.source_url && item.source_url !== action?.source_url) links.append(sourceLink(item.source_url, 'Recorded-action source ↗'), ' · ');
          if (action?.source_url) links.append(sourceLink(action.source_url, 'Legislative source ↗'));
          let sheetUrl = action?.sheet_url || record.source_url || cfg.source_url;
          if (/^[A-Z]{1,3}$/.test(action?.sheet_column || '') && Number.isInteger(record.sheet_row) && record.sheet_row > 0) {
            try {
              const cell = new URL(sheetUrl);
              const fragment = new URLSearchParams(cell.hash.slice(1));
              fragment.set('range', action.sheet_column + record.sheet_row);
              cell.hash = fragment.toString();
              sheetUrl = cell.href;
            } catch {}
          }
          if (sheetUrl) {
            if (action?.source_url) links.append(' · ');
            links.append(sourceLink(sheetUrl, 'Sheet entry ↗'));
          }
          row.append(links);
          list.append(row);
        }
        group.append(list);
        box.append(group);
      }
    }
    if (platform) {
      const box = section('Campaign platform');
      const statuses = {
        statement_found: 'Israel / Palestine platform statement found.',
        no_statement_found: 'No Israel / Palestine platform statement found in the reviewed pages.',
        unavailable: 'Campaign website review unavailable or incomplete.',
        no_website: 'No verified campaign website is recorded in this inventory.'
      };
      box.append(node('p', 'gaza-platform-status', statuses[platform.status] || 'Platform review unresolved.'));
      if (platform.summary) box.append(node('p', null, platform.summary));
      if (platform.quote) box.append(node('blockquote', 'gaza-platform-quote', platform.quote));
      if (platform.scope_note) box.append(node('p', 'gaza-note', platform.scope_note));
      checked(box, platform.checked_on);
      if (platform.source_url) box.append(sourceLink(platform.source_url, 'Platform statement ↗'));
      if (platform.pages?.length) {
        const pages = node('details', 'gaza-platform-pages');
        pages.append(node('summary', null, 'Reviewed pages · ' + platform.pages.length));
        const list = node('ul');
        for (const page of platform.pages) {
          const item = node('li');
          item.append(sourceLink(page.url, page.title || page.url));
          list.append(item);
        }
        pages.append(list);
        box.append(pages);
      }
    }
    if (evidence.length) {
      const box = section('Web, social and guide evidence · ' + evidence.length + ' items');
      if (evidence.some(item => item.dimension === 'aipac_funding')) {
        box.append(node('p', 'gaza-note', 'Funding report dates are not necessarily contribution dates. Totals may combine years or individual and organization donors; see each item’s period and source.'));
      }
      // Newest first. ISO-style dates compare correctly across year/month/day
      // precision; undated items keep their original relative order at the end.
      const ordered = evidence.map((item, index) => ({ item, index })).sort((a, b) => {
        const da = a.item.date || '';
        const db = b.item.date || '';
        if (da === db) return a.index - b.index;
        if (!da) return 1;
        if (!db) return -1;
        return da < db ? 1 : -1;
      });
      for (const { item } of ordered) {
        const paragraph = node('p', 'gaza-web-item', evidenceDateLabel(item) + ' — ' + item.summary);
        paragraph.append(' ', sourceLink(item.url, 'Source ↗'));
        box.append(paragraph);
        if (item.date_note) box.append(node('p', 'gaza-note', item.date_note));
      }
    }
    return disclosure;
  }
};
