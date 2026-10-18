/* Shared wording for both readers; provenance never changes the relationship. */
const EndorsementDisplay = {
  summary(records) {
    const opposed = records.filter(record => record.relation === 'opposed').length;
    const distinctions = records.filter(record => record.relation === 'distinction').length;
    const historical = records.filter(record => record.historical === true).length;
    return 'Endorsements and recommendations · ' + records.length + ' records' +
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

/* Image evidence carries no inferred identity or endorsement relationship. */
EndorsementDisplay.renderImages = function(candidate, {node, link, className = 'candidate-evidence'}) {
  const records = candidate.endorsement_images || [];
  if (!records.length) return null;
  const details = node('details', className + ' endorsement-image-evidence');
  details.append(node('summary', null, 'Campaign image evidence · ' + records.length + ' images'));
  details.append(node('p', null, 'Images captured from campaign sites. A logo, portrait or program badge alone does not establish an endorsement. Names are not inferred from filenames.'));
  const gallery = node('div', 'endorsement-image-gallery');
  for (const record of records) {
    const figure = node('figure', 'endorsement-image-item');
    const image = node('img', 'endorsement-evidence-image');
    const local = /^assets\/endorsement-evidence\/[a-f0-9]{64}\.(png|jpg|webp|gif|avif|svg)$/.test(record.asset_path || '');
    let source = local ? record.asset_path : null;
    try { if (!source && new URL(record.image_url).protocol === 'https:') source = record.image_url; } catch {}
    if (source) {
      image.src = source;
      image.alt = 'Campaign image; identity and relationship not inferred';
      image.loading = 'lazy';
      image.referrerPolicy = 'no-referrer';
      image.addEventListener('error', () => { image.hidden = true; });
      figure.append(image);
    }
    const caption = node('figcaption');
    caption.append(link(record.source_url, 'Campaign source ↗'), node('span', null, ' · observed ' + record.checked_on));
    if (record.provenance === 'legacy_import') {
      caption.append(node('p', null, 'Legacy capture: exact page placement and image identity have not been reviewed. The source link is the campaign root retained by the earlier scan.'));
    } else if (record.heading) {
      caption.append(node('p', null, 'Page heading: ' + record.heading));
    }
    const metadata = node('details', 'endorsement-image-metadata');
    metadata.append(node('summary', null, 'Source and image metadata'));
    metadata.append(link(record.image_url, 'Original image ↗'));
    metadata.append(node('p', null, 'Filename (metadata): ' + record.filename));
    metadata.append(node('p', null, 'Original alt text: ' + (record.original_alt || '(empty)')));
    if (record.context) metadata.append(node('p', null, 'Source context: ' + record.context));
    if (record.image_sha256) metadata.append(node('p', null, 'Archived image SHA-256: ' + record.image_sha256));
    caption.append(metadata); figure.append(caption); gallery.append(figure);
  }
  details.append(gallery);
  return details;
};
