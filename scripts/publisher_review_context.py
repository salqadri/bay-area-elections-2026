"""Source-bound factual context for a publisher-withheld race; never selects a candidate."""
import hashlib
import json
from pathlib import Path
from grade_gaza import build_state
ROOT = Path(__file__).resolve().parent.parent

def context_payload(position, data, hold):
    report = json.loads((ROOT / hold['source_record']).read_text())
    records = []
    for person in position.get('candidates') or []:
        state = build_state(position, person, data)
        for key in ('part_of_muslim_community','community_alignment_context'):
            state.pop(key, None)  # Identity flags are not factual policy statements.
        records.append(state)
    return {'position_id':position['id'], 'candidate_records':records,
            'community_source_report':report,
            'publisher_disposition':{k:v for k,v in hold.items() if k!='narrative_context_path'}}

def context_digest(position, data, hold):
    return hashlib.sha256(json.dumps(context_payload(position,data,hold),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def current_context(path, position, data, hold):
    resolved = (ROOT/path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('Context path outside repository')
    if not resolved.is_file():
        return None
    value = json.loads(resolved.read_text())
    valid = (value.get('format') == 'publisher-race-context/v1'
             and value.get('position_id') == position['id']
             and value.get('recommended') is None
             and bool(value.get('text'))
             and value.get('source_context_sha256') == context_digest(position, data, hold))
    return value if valid else None
