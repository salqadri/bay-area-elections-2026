"""Run the complete offline release gate; does not rebuild, research or publish."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PYTHON_CHECKS = [
    ('build_site.py', '--check'), ('check_firebase_hosting.py',), ('check_summary_source_policy.py',), ('check_data.py',), ('check_evidence.py',),
    ('check_published_endorsements.py',), ('check_endorsement_images.py',), ('check_research_gaps.py',), ('check_education_policy.py',), ('check_endorsements.py',), ('check_ballotpedia_endorsements.py',), ('check_x_profiles.py',), ('check_jev_playground.py',), ('check_published_grades.py',), ('check_grade_explanations.py',), ('check_candidate_community.py',),
    ('check_campaign_endorsement_batch.py', 'research/endorsements/batch-2026-10-18'),
    ('check_recommendations.py',), ('check_bamc_action.py',), ('check_cair_guide.py',), ('check_cair_refresh.py',), ('check_local_ceasefires.py',), ('check_peace_guides.py',), ('check_research_workflow.py',),
    ('check_schema.py',), ('check_fec_money.py',), ('check_gaza_ledger.py',), ('check_funding_evidence.py',),
    ('check_organization_context.py',), ('check_playground_restore.py',), ('check_evidence_context.py',), ('check_gaza_voting_records.py',), ('check_uscpr_scorecard.py',), ('check_gaza_records.py',),
    ('check_campaign_platforms.py',), ('check_platform_positions.py',), ('prepare_dom_fixture.py',),
]
NODE_CHECKS = ['check_pro_palestine_grade_display.cjs', 'check_analytics.cjs', 'check_jev_playground.cjs', 'check_endorsement_display.cjs', 'check_finance_display.cjs', 'check_gaza_display.cjs', 'check_platform_display.cjs', 'check_candidate_sort.cjs', 'check_contest_label.cjs', 'check_explorer.cjs', 'check_address_services.cjs', 'check_address_suggestions.cjs',
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
