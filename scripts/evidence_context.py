"""Reviewed links between evidence items; exact bindings prevent stale interpretation.

No model calls or political inference at runtime. The audit CLI proposes research
leads; only reviewed, source-bound entries become compact model context.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / 'research/gaza-grading/evidence-context-v1.json'
NEGATIVE_BLOCK = re.compile(r'\bno\s+block the bombs\s+support|\bno\s+support\s+(?:for\s+)?(?:the\s+)?block the bombs|\bnot\s+(?:signed|support(?:ed|s)?|co-?sponsor(?:ed|s)?)\s+(?:the\s+)?block the bombs', re.I)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def billstatus_capture(raw, url):
    match = re.fullmatch(r'https://www.govinfo.gov/bulkdata/BILLSTATUS/(\d+)/(hr|s)/BILLSTATUS-\1\2(\d+)\.xml', url)
    if not match:
        raise ValueError('Require an exact official GovInfo bill-status URL')
    tree = ET.fromstring(raw)
    bill = tree.find('bill')
    if bill is None or (bill.findtext('congress'), (bill.findtext('type') or '').lower(), bill.findtext('number')) != match.groups():
        raise ValueError('Bill-status identity does not match source URL')
    label = ('H.R.' if match[2] == 'hr' else 'S.') + match[3]
    rows = []
    for item in bill.findall('cosponsors/item'):
        row = {'bill': label, 'bioguide_id': item.findtext('bioguideId'),
               'name': item.findtext('fullName'), 'cosponsorship_date': item.findtext('sponsorshipDate')}
        if item.findtext('sponsorshipWithdrawnDate'):
            row['withdrawn_date'] = item.findtext('sponsorshipWithdrawnDate')
        if not all(row.values()):
            raise ValueError('Incomplete official cosponsor record')
        date.fromisoformat(row['cosponsorship_date'])
        if row.get('withdrawn_date'):
            date.fromisoformat(row['withdrawn_date'])
        rows.append(row)
    if not rows:
        raise ValueError('No official cosponsor records; do not infer no support')
    titles = list(dict.fromkeys([bill.findtext('title') or '', *[t.findtext('title') or '' for t in bill.findall('titles/item')]]))
    return {'title': label + ' official bill status', 'text': label + '\n' + '\n'.join(t for t in titles if t) + '\n' + '\n'.join(json.dumps(r, separators=(',', ':'), ensure_ascii=False) for r in rows),
            'retrieval': 'Official GovInfo BILLSTATUS XML; bill identity and cosponsor fields parsed; withdrawal dates preserved'}


def resolve_binding(candidate, binding):
    if binding['field'] == 'gaza_evidence':
        return next((e for e in candidate.get('gaza_evidence', []) if e.get('id') == binding['id']), None)
    if binding['field'] == 'gaza_voting_records':
        return next((a for r in candidate.get('gaza_voting_records', []) for a in r['actions'] if a.get('action_id') == binding['id']), None)
    raise ValueError('Unknown context binding field')


def contexts(position, candidate, document=None, data=None):
    document = json.loads(REGISTRY.read_text()) if document is None else document
    rows = []
    for entry in document['entries']:
        if (entry['position_id'], entry['candidate']) != (position['id'], candidate['name']):
            continue
        for binding in entry['bindings']:
            if fingerprint(resolve_binding(candidate, binding)) != binding['sha256']:
                raise ValueError('Stale reviewed evidence context: ' + entry['id'])
        rows.append({'topic':entry['topic'], 'context':entry['context']})
    # Shared, reviewed action families apply to every member in the tracker,
    # without inventing personal explanations or transferring one person's view.
    for group in document.get('action_groups', []):
        parts=[]
        for binding in group['actions']:
            item=resolve_binding(candidate,{'field':'gaza_voting_records','id':binding['id']})
            if item is not None:
                if data is not None and fingerprint((data.get('gaza_voting') or {}).get('actions',{}).get(binding['id'])) != binding['metadata_sha256']:
                    raise ValueError('Stale legislative action group: '+group['id'])
                parts.append(binding['label']+': '+str(item.get('value') or 'No entry'))
        if len(parts)>1:
            rows.append({'topic':group['topic'],'context':'; '.join(parts)+'. '+group['context']})
    return rows


def research_leads(data):
    """Detect missing context for review; never decide that a guide is wrong automatically."""
    rows = []
    registry = (data.get('gaza_voting') or {}).get('actions', {})
    for p in data['positions']:
        if p.get('ballot_status') == 'excluded':
            continue
        for roster in ('candidates','filed_candidates_not_confirmed_on_ballot','qualified_write_in_candidates'):
            for c in p.get(roster) or []:
                actions = [(a, registry.get(a['action_id'], {})) for r in c.get('gaza_voting_records', []) for a in r['actions']]
                block = [a for a,m in actions if 'block the bombs' in m.get('title','').lower() and a.get('value') == 'Sponsor']
                stale = [e['id'] for e in c.get('gaza_evidence', []) if e.get('source_kind') == 'voter_guide'
                         and NEGATIVE_BLOCK.search(e.get('summary','')+' '+e.get('quote',''))]
                if block and stale:
                    rows.append({'position_id':p['id'],'candidate':c['name'],'reason':'Guide no-support claim conflicts with tracker sponsorship; verify dated primary record.', 'evidence_ids':stale})
                unrwa = [(a,m) for a,m in actions if 'UNRWA' in m.get('title','') and m.get('kind') == 'roll_call_vote'
                         and a.get('value') in {'Yes','No','Yes (correct)','No (correct)'}]
                if len({a.get('value') for a,m in unrwa}) > 1:
                    rows.append({'position_id':p['id'],'candidate':c['name'],'reason':'Different UNRWA-related vote responses; research bill differences, explanations and later actions.','action_ids':[a['action_id'] for a,m in unrwa]})
                if any(re.search(r'revers|changed course|stopped short|reluctan',e.get('summary',''),re.I) for e in c.get('gaza_evidence',[])):
                    rows.append({'position_id':p['id'],'candidate':c['name'],'reason':'Position-change language needs trigger/date context; research debate, criticism and later statement.'})
    return rows


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset',type=Path,default=ROOT/'2026-11-03_Bay_Area_Elections.json')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();rows=research_leads(json.loads(args.dataset.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'status':'held research leads; not findings','candidates':rows},indent=2)+'\n')
    print(json.dumps({'leads':len(rows),'output':str(args.output)}))
