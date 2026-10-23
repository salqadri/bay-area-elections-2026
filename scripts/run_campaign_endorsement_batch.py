"""Resume local extraction, Jev review, and evidence export without publishing.

Run from any directory. Credentials are inherited only from the environment.
Progress and source-bound checkpoints stay under .research/endorsements/.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / '.research/endorsements/bulk-run'


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    status = {'started_at': datetime.now(timezone.utc).isoformat(),
              'state': 'running', 'stages': [], 'publication': 'not applied',
              'image_publication': 'Requires separate review/apply; text attachment does not publish image inventories'}

    checked_on = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
    image_dir = RUN / 'images' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    image_id = 'campaign-images-' + image_dir.name

    def save():
        temp = RUN / 'status.tmp'
        temp.write_text(json.dumps(status, indent=2) + '\n')
        temp.replace(RUN / 'status.json')

    commands = [
        ('image-inventory', ['review_endorsement_images.py', 'export-ledger',
            '--db', '.research/endorsements/campaign.sqlite3',
            '--output-dir', str(image_dir)]),
        ('image-publication-draft', ['review_endorsement_images.py', 'build-queue',
            '--queue', str(image_dir / 'queue.json'),
            '--id', image_id, '--reviewed-on', checked_on,
            '--output', str(image_dir / 'publication-review.json')]),
        ('local-extraction', ['campaign_endorsements.py', 'extract-llm',
            '--workers', '2', '--retry-errors']),
        ('quote-gates', ['campaign_endorsements.py', 'propose']),
    ]
    if os.environ.get('TYPESAFE_API_KEY'):
        commands += [('jev-review', ['jev_review_proposals.py', '--out',
                     '.research/endorsements/bulk-run/jev-decisions.json']),
                    ('record-decisions', ['campaign_endorsements.py', 'apply-review',
                     '.research/endorsements/bulk-run/jev-decisions.json'])]
    else:
        status['review_limitation'] = 'TYPESAFE_API_KEY absent; Jev review skipped.'
    commands.append(('final-status', ['campaign_endorsements.py', 'status']))
    save()
    for name, args in commands:
        status['current_stage'] = name
        save()
        with (RUN / (name + '.log')).open('a') as log:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / args[0]),
                                     *args[1:]], cwd=ROOT, stdout=log, stderr=log)
        status['stages'].append({'stage': name, 'exit_code': result.returncode})
        if result.returncode:
            status['state'] = 'failed'
            save()
            return result.returncode
        save()
    status['state'] = 'finished-research'
    status['finished_at'] = datetime.now(timezone.utc).isoformat()
    status['limitation'] = ('Research only. Fetch failures, attribution holds, and rejected '
                            'quotes remain explicit. Review before publication; images '
                            'never establish named endorsement identities.')
    save()
    return 0


if __name__ == '__main__':
    sys.exit(main())
