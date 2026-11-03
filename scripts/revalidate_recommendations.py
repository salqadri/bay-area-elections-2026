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
    args = parser.parse_args()
    data = json.loads(args.dataset.read_text())
    plan = json.loads(args.plan.read_text())
    source_hash = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    if plan['source_dataset_sha256'] != source_hash:
        raise SystemExit('Refusing a plan that does not bind this exact dataset')
    result, audit = recommendations.revalidate_plan(plan, data)
    audit.update(source_dataset_sha256=source_hash,
                 previous_plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest())
    # Archive displaced choices/reasons before replacing the plan.
    for path, value in ((args.audit, audit), (args.output, result)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: v for k, v in audit.items() if k != 'changed_choices'}))
    print('Withdrawn choices:', [row['position_id'] for row in audit['changed_choices']])


if __name__ == '__main__':
    main()
