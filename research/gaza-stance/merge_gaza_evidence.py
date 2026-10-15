#!/usr/bin/env python3
"""Copy collector evidence subject to the repository's publication guards.

Matches each evidence person key (norm_name|party) to printed/provisional/write-in
candidates across ALL counties in the dataset (statewide candidates appear once per
person; research is keyed by person, not county). Existing gaza_evidence on a
candidate is checked against the current quarantine and immutable review history.
Missing published evidence is an error. Manual publication changes can be copied
back into the collector with --sync-published, preserving quarantine history.

Usage: python3 merge_gaza_evidence.py [--dry-run]
"""
import argparse, copy, json, os, re, sys
from pathlib import Path
from datetime import date
from urllib.parse import urlsplit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xhunt2 import norm_name
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_evidence import check_evidence, canonical_url
from check_published_endorsements import check_endorsements
from schema_validation import SCHEMA, check

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "2026-11-03_Bay_Area_Elections.json")

def load_ledger():
    people, names = {}, {}
    for file in sorted(Path(LEDGER).glob('*.json')):
        for e in json.loads(file.read_text()):
            key = norm_name(e['person'])
            if key in names and names[key] != e['person']:
                raise ValueError('Ambiguous collector identity: ' + e['person'])
            names[key] = e['person']
            people.setdefault(key, []).append(e)
    return people

def clean_item(e):
    it = {"id": e["id"], "url": e["url"], "summary": e["summary"], "date": str(e.get("date") or ''),
          "dimension": e.get("dimension", "other"), "checked_on": e["checked_on"]}
    for field in ('quote', 'source_kind', 'date_method', 'date_note'):
        if e.get(field): it[field] = e[field]
    errors = check(it, SCHEMA['$defs']['stanceEvidence'])
    if errors:
        raise ValueError(f"Invalid ledger item {e['id']}: {errors}")
    return it


def validate_publication(data):
    errors = check_evidence(data) + check_endorsements(data)
    if errors:
        raise ValueError('Ledger conflicts with reviewed publication; reconcile before merging:\n' + '\n'.join(errors))


def merged_data(original, ledger):
    data = copy.deepcopy(original)
    applied_people, applied_entries = set(), 0
    for p in data["positions"]:
        rosters = [p.get("candidates") or [],
                   p.get("filed_candidates_not_confirmed_on_ballot") or [],
                   p.get("qualified_write_in_candidates") or []]
        for roster in rosters:
            for c in roster:
                rows = ledger.get(norm_name(c["name"]))
                if not rows:
                    if c.get('gaza_evidence'):
                        raise ValueError('Missing collector evidence for ' + c['name'] + '; apply a reviewed removal first')
                    continue
                items = [clean_item(e) for e in rows]
                if any(item not in items for item in c.get('gaza_evidence', [])):
                    raise ValueError('Collector would replace or remove published evidence for ' + c['name'] + '; use reviewed_updates.py first')
                published = c.get('gaza_evidence', [])
                items = published + [item for item in items if item not in published]
                c["gaza_evidence"] = items
                applied_people.add(norm_name(c["name"])); applied_entries += 1
    printed = [c for p in data["positions"] for c in (p.get("candidates") or [])]
    n_ev = sum(bool(c.get("gaza_evidence")) for c in printed)
    data["coverage"]["printed_candidates_with_gaza_evidence"] = n_ev
    validate_publication(data)
    return data, {"people_matched": len(applied_people), "entries": applied_entries,
                  "printed_with_evidence": n_ev}


def sync_published(data, apply=False):
    """Mirror reviewed publication into the collector without dropping new drafts.

    An extra ledger item may be removed only if the repository quarantine records
    its candidate/source pair. Unknown extra items stop reconciliation for review.
    Resolved holds retain their original text and gain resolution metadata.
    """
    validate_publication(data)
    quarantine = json.loads((ROOT / 'docs/reviews/evidence-quarantine.json').read_text())
    blocked = {(r['candidate'], canonical_url(r['evidence']['url'])) for r in quarantine['items']}
    people = {}
    for position in data['positions']:
        for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates'):
            for candidate in position.get(roster) or []:
                if candidate.get('gaza_evidence'):
                    key = norm_name(candidate['name'])
                    pair = (candidate['name'], candidate['gaza_evidence'])
                    if key in people and people[key] != pair:
                        raise ValueError('Ambiguous collector name: ' + candidate['name'])
                    people[key] = pair
    accepted_ids = {e['id']: name for name, items in people.values() for e in items}
    paths, writes, previous = {}, {}, {}
    for file in sorted(Path(LEDGER).glob('*.json')):
        rows = json.loads(file.read_text())
        for item in rows:
            if item['id'] in previous:
                raise ValueError('Duplicate collector evidence ID: ' + item['id'])
            previous[item['id']] = item
        for item in rows:
            key = norm_name(item['person'])
            if key in paths and paths[key] != file:
                raise ValueError('Multiple collector files for ' + item['person'])
            paths[key] = file
            if item['id'] in accepted_ids and item['person'] != accepted_ids[item['id']]:
                raise ValueError('Collector evidence ID belongs to a different person: ' + item['id'])
            if item['id'] not in accepted_ids and (item['person'], canonical_url(item['url'])) not in blocked:
                raise ValueError('Unreviewed collector item would be lost: ' + item['id'])
        if rows and norm_name(rows[0]['person']) not in people:
            writes[file] = []
    for key, (name, items) in people.items():
        stem = re.sub(r'[^a-z0-9|_-]', '_', key + '|_')[:80]
        file = paths.get(key, Path(LEDGER) / (stem + '.json'))
        rows = []
        original_order = {r['id']: i for i, r in enumerate(json.loads(file.read_text()) if file.exists() else [])}
        for item in sorted(items, key=lambda r: original_order.get(r['id'], len(original_order))):
            row = {k: v for k, v in previous.get(item['id'], {}).items()
                   if k in item or k in {'person', 'domain'}}
            if not row:
                row = {'id': item['id'], 'person': name, 'date': item['date'], 'url': item['url'],
                       'domain': (urlsplit(item['url']).hostname or '').removeprefix('www.')}
            row.update(copy.deepcopy(item))
            rows.append(row)
        writes[file] = rows
    qpath = Path(LEDGER).parent / 'ledger/undated_quarantine.json'
    history = json.loads(qpath.read_text())
    known = {(r['person'], canonical_url(r['url'])) for r in history}
    for record in quarantine['items']:
        pair = record['candidate'], canonical_url(record['evidence']['url'])
        if pair not in known:
            history.append({'person': record['candidate'], 'url': record['evidence']['url'],
                            'summary': record['evidence']['summary'], 'evidence': record['evidence'],
                            'skipped_on': record.get('reviewed_on', date.today().isoformat()),
                            'reason': record['reason'] + ': ' + record['detail'],
                            'review_id': record.get('review_id')})
            known.add(pair)
    for resolution in quarantine.get('resolved_items', []):
        for record in history:
            if (record['person'], canonical_url(record['url'])) == (resolution['candidate'], canonical_url(resolution['evidence']['url'])):
                record.update(status='resolved', resolved_on=resolution['resolved_on'],
                              review_id=resolution['review_id'], resolution=resolution['resolution'])
    writes[qpath] = history
    changed = {file: rows for file, rows in writes.items()
               if not file.exists() or json.loads(file.read_text()) != rows}
    if apply:
        for file, rows in changed.items():
            file.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n')
    return {'changed_files': len(changed), 'accepted_items': len(accepted_ids), 'applied': apply}


def main(dry=False):
    original = json.loads(Path(DATA).read_text())
    data, report = merged_data(original, load_ledger())
    if dry:
        print(json.dumps(report, indent=2)); return
    if data != original:
        Path(DATA).write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sync-published', action='store_true', help='copy reviewed publication and holds back to collector')
    args = parser.parse_args()
    if args.sync_published:
        print(json.dumps(sync_published(json.loads(Path(DATA).read_text()), apply=not args.dry_run), indent=2))
    else:
        main(args.dry_run)
