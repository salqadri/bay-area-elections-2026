"""Project explicitly registered community reports without inventing policy positions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / 'research/community-reports/state-sources-v1.json'


def observations(position, candidate):
    endorsements, policy = [], []
    for source in json.loads(REGISTRY.read_text())['reports']:
        path = (ROOT / source).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('Community report outside repository')
        report = json.loads(path.read_text())
        if (report['position_id'], report['candidate']) != (position['id'], candidate['name']):
            continue
        row = report['opposition_observation']
        if (report['status'] != 'owner_report_recorded' or row['source_type'] != 'owner_report'
                or row['relation'] != 'opposed' or row['independently_verified'] is not False
                or (row['position_id'], row['candidate']) != (position['id'], candidate['name'])):
            raise ValueError('Unexpected community report contract')
        endorsements.append({
            'endorser': row['organization'], 'relation': row['relation'],
            'source': 'owner report; not independently verified',
            'reported_on': row['reported_on'], 'reported_strength': row['reported_strength'],
        })
        article = report.get('article_context')
        if article:
            policy.append({'date': article['published_on'], 'summary': article['documented_event'],
                           'source_url': article['source_url'], 'scope': article['classification']})
    return {'endorsements': endorsements, 'policy': policy}
