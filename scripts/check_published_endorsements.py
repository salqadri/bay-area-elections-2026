"""Publication guard for known rejected endorsement sources and support semantics."""
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

from endorsement_extract import invalid_endorser_name, norm
from import_cair_guide import reviewed_records, REVIEW as CAIR_REVIEW

ROOT = Path(__file__).resolve().parent.parent
QUARANTINE = ROOT / 'research/endorsements/quarantine-2026-10-09.json'


def source_key(url):
    p = urlsplit(url)
    return (p.hostname or '').removeprefix('www.').lower(), p.path.rstrip('/').lower()


def blocked_reason(record, quarantine=None):
    quarantine = quarantine or json.loads(QUARANTINE.read_text())
    for item in quarantine['blocked_urls']:
        if source_key(record['url']) == source_key(item['url']):
            return item['reason']
    for item in quarantine['blocked_endorser_names']:
        if norm(record['endorser']) == norm(item['name']):
            return item['reason']
    if invalid_endorser_name(record['endorser']):
        return 'UI text or category heading is not an identifiable endorser'


def check_endorsements(data, review_cair=True):
    quarantine = json.loads(QUARANTINE.read_text())
    errors = []
    expected_cair = reviewed_records(data, json.loads(CAIR_REVIEW.read_text())) if review_cair else {}
    for p in data['positions']:
        for c in p.get('candidates') or []:
            seen = set()
            for r in c.get('endorsements', []):
                prefix = p['id'] + ' / ' + c['name'] + ': '
                reason = blocked_reason(r, quarantine)
                if reason:
                    errors.append(prefix + reason)
                key = (norm(r['endorser']), r['relation'], r['phase'], source_key(r['url']))
                if key in seen:
                    errors.append(prefix + 'duplicate endorsement/support source')
                seen.add(key)
                try:
                    assert date.fromisoformat(r['checked_on']) <= date.today()
                except (ValueError, AssertionError):
                    errors.append(prefix + 'invalid/future check date')
                if r.get('rating') and r['relation'] != 'supported':
                    errors.append(prefix + 'a support rating is not a formal endorsement')
                if r['relation'] in {'supported', 'preferred', 'opposed'} or r.get('verification') in {'reported', 'campaign_claim'}:
                    if r.get('note_id') not in data['notes']:
                        errors.append(prefix + 'support or indirect evidence needs an explanatory note')
                if review_cair and r['endorser'] == 'CAIR Action':
                    expected = expected_cair.get((p['id'], c['name']))
                    if r != expected:
                        errors.append(prefix + 'CAIR recommendation differs from reviewed official capture; update the review before publishing')
            if (p['id'], c['name']) in expected_cair and not any(r['endorser'] == 'CAIR Action' for r in c.get('endorsements', [])):
                errors.append(p['id'] + ' / ' + c['name'] + ': missing reviewed CAIR recommendation')
    return errors


if __name__ == '__main__':
    data = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())
    errors = check_endorsements(data)
    if errors:
        raise SystemExit('\n'.join(errors))
    print('Published endorsements pass quarantine and support-semantics guards.')
