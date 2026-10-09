/* Shared wording for both readers; provenance never changes the relationship. */
const EndorsementDisplay = {
  label(record) {
    const relations = {endorsed: 'Endorsed by ', recommended: 'Recommended by ', supported: 'Supported by '};
    const provenance = {endorser_statement: 'Publisher statement', campaign_claim: 'Campaign claim', reported: 'Secondary report'};
    const phase = {primary: 'Primary election', general: 'General election', unspecified: 'Election phase not stated'};
    return (relations[record.relation] || 'Record from ') + record.endorser +
      (record.rating ? ' · Source rating: ' + record.rating : '') +
      ' · ' + (phase[record.phase] || 'Election phase not stated') +
      ' · ' + (provenance[record.verification] || 'Source classification not recorded') +
      ' · checked ' + record.checked_on;
  }
};
