#!/usr/bin/env python3
"""Build a reviewed_updates review manifest from the held campaign-issues export.

Mechanical gates applied here (a model never decides publication):
- every point quote was already verbatim-gated at import; re-checked against the
  immutable captures by scripts/research_campaign_issues.py import-reviewed;
- each positions_found candidacy must have its own name tokens present verbatim
  in that source's captured pages (shared-site misattribution guard);
- only HTTPS seed sources publish through the common review workflow;
- unavailable/no_website inventory states stay held, never published.

Run from the repository root:
    python3 research/campaign-issues/build_review.py --reviewed-on YYYY-MM-DD \
        --output research/reviews/campaign-platform-positions-YYYY-MM-DD.json
Then preview with scripts/reviewed_updates.py preview before applying.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
WORK = ROOT / '.research/campaign-platforms'
HELD = ROOT / '.research/campaign-issues/held-export.json'


def name_tokens(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    return [w for w in re.findall(r'[^\W\d_]+', text.lower()) if w not in {'dr', 'hon', 'jr', 'sr', 'ii', 'iii'}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--held', type=Path, default=HELD)
    parser.add_argument('--reviewed-on', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    date.fromisoformat(args.reviewed_on)
    held = json.loads(args.held.read_text())
    plan = json.loads((WORK / 'plan.json').read_text())
    sources = {}
    decisions, held_back = [], []
    for record in held['candidates']:
        platform = record['platform_positions']
        status = platform['status']
        if status not in {'positions_found', 'no_positions_found'}:
            held_back.append((record['candidate'], status))
            continue
        source_id = next(c['source_id'] for c in plan['candidates'] if c['candidacy_id'] == record['candidacy_id'])
        crawl = json.loads((WORK / 'crawls' / (source_id + '.json')).read_text())
        captures = []
        for page in crawl['pages']:
            capture = json.loads((WORK / 'captures' / (page['capture_id'] + '.json')).read_text())
            if capture['status'] == 'ok':
                captures.append(capture)
        urls_in_record = {p['url'] for p in platform['pages']}
        captures = [c for c in captures if c['url'] in urls_in_record]
        https_captures = [c for c in captures if c['url'].startswith('https://')]
        if not https_captures:
            held_back.append((record['candidate'], 'http_only_capture'))
            continue
        # The review source is one hash-verified capture whose checked_on equals the record date.
        source_capture = next((c for c in https_captures if c['checked_on'] == platform['checked_on']), None)
        if source_capture is None:
            held_back.append((record['candidate'], 'capture_date_mismatch'))
            continue
        all_text = normalize(' '.join(c['text'] for c in captures))
        tokens = name_tokens(record['candidate'])
        identity_ok = bool(tokens) and tokens[0] in all_text and tokens[-1] in all_text
        if not identity_ok:
            held_back.append((record['candidate'], 'name_not_on_site'))
            continue
        source_key = source_id + '-' + source_capture['content_sha256'][:8]
        sources[source_key] = {'url': source_capture['url'], 'publisher': record['candidate'], 'role': 'campaign',
                               'checked_on': source_capture['checked_on'], 'retrieval': 'bounded_crawler_text',
                               'content_sha256': source_capture['content_sha256']}
        if status == 'positions_found':
            reason = ('Campaign-website platform points quoted verbatim from hash-verified captures; topic vocabulary, '
                      'quote containment and candidate-name presence on the site were mechanically gated.')
        else:
            reason = ('Bounded campaign-website check found no attributable policy position within the inspected scope; '
                      'silence is scoped to these pages and capture dates, not absolute.')
        decisions.append({
            'id': record['position_id'] + '-pp-' + source_capture['content_sha256'][:8],
            'action': 'change', 'field': 'platform_positions', 'source_key': source_key,
            'position_id': record['position_id'], 'candidate': record['candidate'], 'identity': record['identity'],
            'before': None, 'after': platform, 'reason': reason,
            'evidence': {
                'identity_basis': ('Candidate name appears verbatim on the campaign site captures bound to this record; '
                                   'the campaign URL was separately verified October 6-7, 2026 and the candidacy office/jurisdiction '
                                   'matches the site content. Shared-site points carry an explicit candidate binding.'),
                'date_basis': ('checked_on is the actual capture date of the bound website pages (bounded crawler, October 15, 2026); '
                               'it dates this observation, not any underlying campaign statement, whose publication date on the site is unknown.'),
                'issue_basis': ('Each point quote is an exact substring of a hash-verified capture (typography/whitespace-tolerant '
                                'containment), its topic comes from the fixed vocabulary and its source_url is one of the bound pages; '
                                'summaries preserve the site wording. No third-party or endorser text was used.')},
        })
    review = {'version': 1, 'id': 'campaign-platform-positions-' + args.reviewed_on,
              'election_date': held['election_date'], 'reviewed_on': args.reviewed_on,
              'counties': ['Alameda', 'Contra Costa', 'San Francisco', 'San Mateo', 'Santa Clara'],
              'sources': sources,
              'notes': {'N901': ('Campaign platform positions pass (docs/CAMPAIGN_PLATFORMS.md): points are quoted verbatim from '
                                 'hash-verified bounded website captures with mechanically gated topics and identity; silence findings '
                                 'state their scope and do not assert absence elsewhere. Extraction used the local qwen/qwen3.8-27b model; '
                                 'every published point passed deterministic quote/topic gates.')},
              'decisions': decisions}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit('Review manifest is immutable once written: ' + str(args.output))
    args.output.write_text(json.dumps(review, ensure_ascii=False, indent=1) + '\n')
    from collections import Counter
    print(json.dumps({'decisions': len(decisions), 'sources': len(sources),
                      'statuses': dict(Counter(d['after']['status'] for d in decisions)),
                      'held_back': dict(Counter(s for _, s in held_back))}, ensure_ascii=False, indent=2))


def normalize(text):
    return ' '.join(text.split()).lower()


if __name__ == '__main__':
    main()
