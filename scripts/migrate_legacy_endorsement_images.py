"""Draft a deterministic correction of ALL explicitly filename-derived imports.

No network, name inference or roster changes. Each old named assertion is
removed and its image URL retained as neutral legacy evidence with its original
observation date. This does not assert withdrawal. Source hashes bind to the
prior published record, NOT to unavailable historical HTML/image bytes.
Explicit Gun Sense Candidate text is reclassified as a distinction separately.
Review/preview/apply the generated manifest with reviewed_updates.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from endorsement_extract import uid
from campaign_endorsements import is_distinction
from reviewed_updates import identity
from research_endorsements import atomic_json, digest, dump


def filename_import(record, notes):
    return (record.get('verification') == 'campaign_claim' and
            'image filename' in notes.get(record.get('note_id'), '').lower())


def draft(data, reviewed_on):
    sources, changes, baseline = {}, [], []
    note_id = 'N' + str(max(int(k[1:]) for k in data['notes']) + 1)
    notes = {note_id: 'The campaign source calls this a Gun Sense Candidate designation or distinction. The official program FAQ (https://gunsensevoter.org/faq/) states that this distinction is not an endorsement. The original observation date and source quote are retained; this correction does not claim a new source check.'}
    for position in data['positions']:
        for candidate in position.get('candidates') or []:
            for record in candidate.get('endorsements', []):
                legacy = filename_import(record, data['notes'])
                distinction = record.get('verification') == 'campaign_claim' and record['relation'] == 'endorsed' and is_distinction(record['endorser'] + ' ' + record.get('quote', ''))
                if not legacy and not distinction:
                    continue
                observation = {'position_id': position['id'], 'candidate': candidate['name'], 'record': record,
                               'prior_note': data['notes'].get(record.get('note_id'))}
                baseline.append(observation)
                key = uid('legacy-', position['id'], candidate['name'], dump(record))
                sources[key] = {'url': record['url'], 'publisher': candidate['name'] + ' campaign (prior published record)',
                                'role': 'campaign', 'candidate': candidate['name'], 'checked_on': record['checked_on'],
                                'content_sha256': digest(dump(observation)),
                                'retrieval': 'Reclassification of the exact prior published JSON observation and note, not a new HTML/image fetch. The earlier scan retained only the campaign root; exact page placement is unverified.'}
                common = {'action': 'change', 'source_key': key, 'position_id': position['id'], 'candidate': candidate['name'],
                          'identity': identity(position), 'evidence': {'identity_basis': 'Same exact dataset candidacy and office; no fuzzy identity match.',
                          'date_basis': 'Preserve original observation date; correction is not a new check.',
                          'relationship_basis': 'A filename establishes neither identity nor endorsement; explicit Gun Sense text is a program distinction.',
                          'issue_basis': 'Neutral preservation of original image evidence; source placement remains unreviewed.'}}
                if legacy:
                    if not record.get('logo_url'):
                        raise ValueError('Legacy filename assertion has no image to preserve: ' + key)
                    changes.append({**common, 'id': key + '-remove', 'field': 'endorsements', 'before': record, 'after': None,
                                    'reason': 'Retire unsupported filename-derived identity and endorsement assertion. Image retained neutrally; not a withdrawal.'})
                    image = {'id': uid('I-', position['id'], candidate['name'], record['url'], record['logo_url']),
                             'source_url': record['url'], 'image_url': record['logo_url'],
                             'filename': unquote(urlsplit(record['logo_url']).path.rsplit('/', 1)[-1]),
                             'original_alt': '', 'context': '', 'heading': '', 'checked_on': record['checked_on'],
                             'provenance': 'legacy_import'}
                    if not any(c['field'] == 'endorsement_images' and c['position_id'] == position['id'] and c['candidate'] == candidate['name'] and c['after']['id'] == image['id'] for c in changes):
                        changes.append({**common, 'id': key + '-image', 'field': 'endorsement_images', 'before': None, 'after': image,
                                        'reason': 'Preserve previously published image URL without inferred identity; original alt text and exact source page are unavailable.'})
                elif distinction:
                    changes.append({**common, 'id': key + '-distinction', 'field': 'endorsements', 'before': record,
                                    'after': {**record, 'relation': 'distinction', 'note_id': note_id},
                                    'reason': 'Explicit program designation is a distinction, not a formal endorsement; preserve the source quote.'})
    return {'version': 1, 'id': 'legacy-endorsement-images-' + reviewed_on, 'election_date': data['election']['date'],
            'reviewed_on': reviewed_on, 'counties': [c['name'] for c in data['election']['counties_in_scope']],
            'base_dataset_sha256': digest(dump(data)), 'sources': sources, 'notes': notes if any(d['after'] and d['field'] == 'endorsements' for d in changes) else {},
            'decisions': changes, 'prior_observations': baseline}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, default=Path('2026-11-03_Bay_Area_Elections.json'))
    p.add_argument('--reviewed-on', required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Preserve existing reviews; use a new output')
    review = draft(json.loads(args.dataset.read_text()), args.reviewed_on)
    atomic_json(args.output, review)
    print(json.dumps({'observations': len(review['prior_observations']), 'changes': len(review['decisions']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
