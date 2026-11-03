"""Withhold invalid saved selections without scoring or making new choices."""
import argparse
import hashlib
import json
from pathlib import Path

import build_recommendations as recommendations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=recommendations.DATA)
    parser.add_argument('--plan', type=Path, default=recommendations.PLAN)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--refresh-source-binding', action='store_true',
                        help='Allow reviewed factual source changes with identical scores/rosters; never regrade.')
    args = parser.parse_args()
    data = json.loads(args.dataset.read_text())
    plan = json.loads(args.plan.read_text())
    source_hash = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    old_source_hash = plan['source_dataset_sha256']
    if old_source_hash != source_hash and not args.refresh_source_binding:
        raise SystemExit('Refusing a plan that does not bind this exact dataset')
    if args.refresh_source_binding:
        from publication_reviews import check_registered_reviews, load_reviews
        errors = check_registered_reviews(data, load_reviews())
        if errors or plan['source_score_publication_id'] != data['pro_palestine_grading']['publication_id']:
            raise SystemExit('Source refresh failed registered-research or score-publication validation')
    result, audit = recommendations.revalidate_plan(plan, data)
    result['source_dataset_sha256'] = source_hash
    audit.update(source_dataset_sha256=source_hash,
                 previous_source_dataset_sha256=old_source_hash,
                 previous_plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest())
    # Archive displaced choices/reasons before replacing the plan.
    for path, value in ((args.audit, audit), (args.output, result)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: v for k, v in audit.items() if k != 'changed_choices'}))
    print('Withdrawn choices:', [row['position_id'] for row in audit['changed_choices']])


if __name__ == '__main__':
    main()
