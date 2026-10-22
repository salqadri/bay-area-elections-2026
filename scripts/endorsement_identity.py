"""Conservative duplicate checks shared by source collectors.

This does not merge organization aliases, PACs with parents, different relations,
explicit primary/general observations or historical/current records. Ambiguous
near-matches are review leads, never automatic identity assignments.
"""
from difflib import SequenceMatcher
from endorsement_extract import norm


def same_context(a, b):
    return (bool(a.get('historical')) == bool(b.get('historical'))
            and (a['phase'] == b['phase'] or 'unspecified' in (a['phase'], b['phase'])))


def equivalent_relationship(a, b):
    return (a['relation'] == b['relation'] and same_context(a, b)
            and a.get('rating') == b.get('rating')
            and bool(a.get('shared')) == bool(b.get('shared')))


def duplicate_record(record, current):
    return next((r for r in current if norm(r['endorser']) == norm(record['endorser'])
                 and equivalent_relationship(r, record)), None)


def possible_duplicates(record, current):
    """Bound model identity questions to plausible names, never accept fuzzy matches."""
    out = []
    name = norm(record['endorser'])
    for r in current:
        if not same_context(r, record):
            continue
        other = norm(r['endorser'])
        a, b = set(name.split()), set(other.split())
        overlap = len(a & b) / max(len(a | b), 1)
        if name == other or (min(len(name), len(other)) >= 6 and
                             (SequenceMatcher(None, name, other).ratio() >= .82 or overlap >= .67)):
            out.append(r)
    return out
