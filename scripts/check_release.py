"""Run the complete offline release gate; does not rebuild, research or publish."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PYTHON_CHECKS = [
    ('build_site.py', '--check'), ('check_data.py',), ('check_evidence.py',),
    ('check_published_endorsements.py',), ('check_endorsements.py',),
    ('check_cair_guide.py',), ('check_peace_guides.py',), ('check_research_workflow.py',),
    ('check_schema.py',), ('prepare_dom_fixture.py',),
]
NODE_CHECKS = ['check_explorer.cjs', 'check_address_services.cjs', 'check_address_suggestions.cjs',
               'check_address_autocomplete.cjs', 'check_address_matcher.cjs', 'check_ballot_page.cjs']


if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Do not disable assertions with Python -O')
    output = ROOT / '.checks'; output.mkdir(exist_ok=True)
    report = {'passed': True, 'checks': [], 'data_sha256': hashlib.sha256((ROOT / '2026-11-03_Bay_Area_Elections.json').read_bytes()).hexdigest(),
              'limitation': 'Offline consistency and regression checks; not source truth, live-service availability or browser rendering.'}
    commands = [[sys.executable, str(ROOT / 'scripts' / name), *args] for name, *args in PYTHON_CHECKS]
    commands += [['node', str(ROOT / 'scripts' / name)] for name in NODE_CHECKS]
    with (output / 'release-checks.log').open('w') as log:
        for command in commands:
            result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            name = Path(command[1]).name
            log.write(name + '\n' + result.stdout + '\n'); log.flush()
            report['checks'].append({'name': name, 'passed': result.returncode == 0})
            print(('PASS ' if result.returncode == 0 else 'FAIL ') + name, flush=True)
            if result.returncode:
                report['passed'] = False
                print(result.stdout)
                break
    (output / 'release-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if report['passed'] else 1)
