/* Shared wording for both readers; provenance never changes the relationship. */
const EndorsementDisplay = {
  summary(records, imageCount = 0) {
    const opposed = records.filter(record => record.relation === 'opposed').length;
    const distinctions = records.filter(record => record.relation === 'distinction').length;
    const historical = records.filter(record => record.historical === true).length;
    const total = records.length + imageCount;
    return 'Endorsements and recommendations · ' + total + (total === 1 ? ' entry' : ' entries') +
      (distinctions ? ' · ' + distinctions + ' distinctions' : '') +
      (opposed ? ' · ' + opposed + ' opposed' : '') +
      (historical ? ' · ' + historical + ' historical' : '');
  },
  label(record) {
    const relations = {endorsed: 'Endorsed by ', preferred: 'Preferred by ', opposed: 'Opposed by ', recommended: 'Recommended by ', supported: 'Supported by ', distinction: 'Distinction from '};
    const provenance = {endorser_statement: 'Publisher statement', campaign_claim: 'Campaign claim', reported: 'Secondary report'};
    const phase = {primary: 'Primary election', general: 'General election', unspecified: 'Election phase not stated'};
    const ally = record.relation === 'supported' && record.rating === 'Ally';
    return (ally ? 'Listed as Ally by ' : record.shared && record.relation === 'endorsed' ? 'Jointly endorsed by ' : relations[record.relation] || 'Record from ') + record.endorser +
      (record.rating && !ally ? ' · Source rating: ' + record.rating : '') +
      (record.historical ? ' · Historical record (prior race)' : '') +
      ' · ' + (phase[record.phase] || 'Election phase not stated') +
      ' · ' + (provenance[record.verification] || 'Source classification not recorded') +
      ' · checked ' + record.checked_on;
  }
};

/* One list contains text and image entries; image metadata creates no names. */
EndorsementDisplay.render = function(candidate, {node, link, noteText = () => '', className = 'candidate-evidence'}) {
  const records = candidate.endorsements || [];
  const images = candidate.endorsement_images || [];
  if (!records.length && !images.length) return null;
  const details = node('details', className);
  details.append(node('summary', null, EndorsementDisplay.summary(records, images.length)));
  const list = node('ul', 'endorsement-list');
  for (const record of records) {
    const item = node('li', 'endorsement-text-item');
    item.append(node('span', null, EndorsementDisplay.label(record)), ' ', link(record.url, 'source ↗'));
    const note = record.note_id ? noteText(record.note_id) : '';
    if (note) {
      const provenance = node('details', 'endorsement-note');
      provenance.append(node('summary', null, 'Research note'), node('p', null, note));
      item.append(provenance);
    }
    if (record.logo_url) {
      try {
        const url = new URL(record.logo_url);
        if (url.protocol === 'https:') {
          const image = node('img', 'endorsement-logo');
          image.src = url.href; image.alt = record.endorser + ' logo'; image.loading = 'lazy';
          item.append(node('br'), image);
        }
      } catch {}
    }
    list.append(item);
  }
  for (const record of images) {
    const item = node('li', 'endorsement-image-entry');
    const figure = node('figure', 'endorsement-image-item');
    const image = node('img', 'endorsement-evidence-image');
    let source = null;
    try { if (new URL(record.image_url).protocol === 'https:') source = record.image_url; } catch {}
    if (source) {
      image.src = source;
      image.alt = 'Campaign-provided image';
      image.loading = 'lazy';
      image.referrerPolicy = 'no-referrer';
      image.addEventListener('error', () => { image.hidden = true; });
      figure.append(image);
    }
    const caption = node('figcaption');
    caption.append(link(record.source_url, 'Campaign source ↗'));
    if (source) caption.append(node('span', null, ' · '), link(source, 'View image ↗'));
    caption.append(node('span', null, ' · observed ' + record.checked_on));
    const metadata = node('details', 'endorsement-image-metadata');
    metadata.append(node('summary', null, 'Source and image metadata'));
    if (record.provenance === 'legacy_import') {
      metadata.append(node('p', null, 'Legacy capture: exact page placement and image identity have not been reviewed. The source link is the campaign root retained by the earlier scan.'));
    } else if (record.heading) {
      metadata.append(node('p', null, 'Page heading: ' + record.heading));
    }
    metadata.append(link(record.image_url, 'Original image ↗'));
    metadata.append(node('p', null, 'Filename (metadata): ' + record.filename));
    metadata.append(node('p', null, 'Original alt text: ' + (record.original_alt || '(empty)')));
    if (record.context) metadata.append(node('p', null, 'Source context: ' + record.context));
    caption.append(metadata); figure.append(caption); item.append(figure); list.append(item);
  }
  details.append(list);
  return details;
};
