/* Shared wording for both readers; provenance never changes the relationship. */
const EndorsementDisplay = {
  summary(records) {
    const opposed = records.filter(record => record.relation === 'opposed').length;
    return 'Endorsements and recommendations · ' + records.length + ' records' +
      (opposed ? ' · ' + opposed + ' opposed' : '') + ' (2026 cycle)';
  },
  label(record) {
    const relations = {endorsed: 'Endorsed by ', preferred: 'Preferred by ', opposed: 'Opposed by ', recommended: 'Recommended by ', supported: 'Supported by '};
    const provenance = {endorser_statement: 'Publisher statement', campaign_claim: 'Campaign claim', reported: 'Secondary report'};
    const phase = {primary: 'Primary election', general: 'General election', unspecified: 'Election phase not stated'};
    return (record.shared && record.relation === 'endorsed' ? 'Jointly endorsed by ' : relations[record.relation] || 'Record from ') + record.endorser +
      (record.rating ? ' · Source rating: ' + record.rating : '') +
      ' · ' + (phase[record.phase] || 'Election phase not stated') +
      ' · ' + (provenance[record.verification] || 'Source classification not recorded') +
      ' · checked ' + record.checked_on;
  }
};
