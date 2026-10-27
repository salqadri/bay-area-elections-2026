"""Freeze latest successful Jev evaluations and attach reproducible public grades.

No provider calls. Exact requests/responses stay in an immutable archive; the
canonical dataset gets a compact projection bound to contest, name and roster.
"""
import argparse
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

from ballotpedia_endorsements import digest, dump
from grade_gaza import DEFAULT_CRITERIA, validate_questions, validate_response
from score_grade import row_grade, validate_mapping

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / '2026-11-03_Bay_Area_Elections.json'
FIELDS = ('pro_palestine_score', 'pro_palestine_score_grade', 'pro_palestine_evaluation')
ROSTERS = ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates')


def candidacy_id(position_id, name, roster):
    return digest(dump([position_id, name, roster]).encode())[:24]


def projection(row, mapping, publication_id):
    request, response = row['request'], row['response']
    validate_questions(request['questions']); validate_response(request['questions'], response)
    if digest(dump(request).encode()) != row['request_sha256']:
        raise ValueError('Saved request hash mismatch')
    grade = row_grade(row, mapping)
    eq = request['questions'].get('evidence_score', {})
    evidence = response['answers'].get('evidence_score', {})
    if grade is None or eq.get('type') != 'score' or len(eq.get('criteria', [])) != 2:
        raise ValueError('Publishing requires compatible score and evidence questions')
    score = response['answers']['pro_palestine_score']
    return {'pro_palestine_score': score['score'], 'pro_palestine_score_grade': grade,
            'pro_palestine_evaluation': {
                'publication_id': publication_id, 'candidate_id': row['id'],
                'request_sha256': row['request_sha256'],
                'questions_sha256': digest(dump(request['questions']).encode()),
                'model': response['model'], 'evaluated_at': row['finished_at'],
                'confidence': score['confidence'], 'evidence_score': evidence['score'],
                'evidence_confidence': evidence['confidence'],
                'source_run_id': row['evaluation']['run_id'],
                'input_dataset_sha256': row['evaluation']['dataset_sha256'],
                'input_state_version': row['evaluation']['state_version']}}


def freeze(latest, mapping, preferred, published_on, criteria_path='research/gaza-grading/criteria-pro-palestine-v3.json'):
    validate_mapping(mapping); validate_questions(preferred['questions'])
    if date.fromisoformat(published_on) > date.today() or latest.get('scope') != 'latest':
        raise ValueError('Use the latest-per-candidate projection and an actual observation date')
    rows = []
    for row in latest['rows']:
        if row['status'] != 'complete':
            raise ValueError('Resolve incomplete latest evaluations before publication')
        # Never archive transient UI metadata or copy a stale derived grade.
        rows.append({k: deepcopy(row[k]) for k in ('id','position_id','candidate','roster','status',
                                                    'request','request_sha256','response','finished_at','evaluation')})
    return {'format':'published-jev-grades/v1', 'id':'jev-'+published_on,
            'published_on':published_on, 'selection':'latest successful saved evaluation per candidacy',
            'score_grade_mapping':mapping, 'evidence_threshold':.10,
            'preferred_criteria_path':criteria_path,
            'preferred_criteria':preferred, 'rows':rows}



def recommendation_signal(record):
    name=''.join(c for c in record.get('endorser','').lower() if c.isalnum())
    if name not in {'cairaction','voteforpeace'} or record.get('historical'):
        return False
    # Neutral/no-endorsement observations do not establish a directional stance.
    rating=str(record.get('rating','')).strip().lower()
    if name=='voteforpeace' and rating in {'neutral','no endorsement'}:
        return False
    return record.get('relation') in {'endorsed','preferred','supported','opposed'}


def recommendation_key(record):
    return (''.join(c for c in record['endorser'].lower() if c.isalnum()),
            record.get('relation'),record.get('phase','unspecified'),record.get('rating'))


def validate_recommendation_evidence(candidate, row, grade):
    observed=[r for r in row['request']['state'].get('focused_endorsement_observations',[])
              if recommendation_signal(r)]
    expected=[r for r in candidate.get('endorsements',[]) if recommendation_signal(r)]
    if not {recommendation_key(r) for r in expected} <= {recommendation_key(r) for r in observed}:
        raise ValueError('CAIR Action / Vote for Peace recommendation missing from saved input: '+row['candidate'])
    if grade=='N/A' and observed:
        raise ValueError('N/A despite a concrete CAIR Action / Vote for Peace recommendation: '+row['candidate'])


def attach(data, archive, archive_path, archive_sha):
    if archive.get('format') != 'published-jev-grades/v1' or archive['evidence_threshold'] != .10:
        raise ValueError('Unsupported publication format or evidence threshold')
    mapping = validate_mapping(archive['score_grade_mapping'])
    result = deepcopy(data); targets = {}
    previous = data.get('pro_palestine_grading') or {}
    preserve_explanations = (previous.get('explanations') and previous.get('archive_sha256') == archive_sha
                             and previous.get('archive_path') == archive_path and previous.get('publication_id') == archive['id'])
    for p in result['positions']:
        for roster in ROSTERS:
            for c in p.get(roster) or []:
                for key in FIELDS: c.pop(key, None)
                if not preserve_explanations: c.pop('pro_palestine_explanation', None)
                targets[(p['id'], c['name'], roster)] = (p, c)
    seen = set()
    for row in archive['rows']:
        key = row['position_id'], row['candidate'], row['roster']
        if key in seen or key not in targets:
            raise ValueError('Duplicate or unmatched published candidacy: '+str(key))
        p,c = targets[key]
        if p.get('ballot_status') == 'excluded' or row['id'] != candidacy_id(*key):
            raise ValueError('Excluded contest or candidate identity mismatch')
        if row['request']['questions'] != archive['preferred_criteria']['questions']:
            raise ValueError('Every published evaluation must use the exact preferred question JSON')
        state=row['request']['state']
        if not isinstance(state,dict) or state.get('candidate') != row['candidate'] or state.get('candidate_roster') != row['roster']:
            raise ValueError('Saved input belongs to a different candidate or roster')
        projected=projection(row, mapping, archive['id'])
        validate_recommendation_evidence(c,row,projected['pro_palestine_score_grade'])
        c.update(projected); seen.add(key)
    active={key for key,(p,c) in targets.items() if p.get('ballot_status') != 'excluded'}
    if seen != active:
        raise ValueError('Publication must cover every active tracked candidacy')
    result['pro_palestine_grading'] = {
        'publication_id':archive['id'], 'published_on':archive['published_on'],
        'archive_path':archive_path, 'archive_sha256':archive_sha,
        'preferred_criteria_path':archive.get('preferred_criteria_path','research/gaza-grading/criteria-pro-palestine-v3.json'),
        'score_grade_mapping':mapping, 'evidence_threshold':.10,
        'methodology_url':'https://github.com/salqadri/bay-area-elections-2026/blob/main/docs/PUBLISHED_GRADES.md'}
    # Preserve explanations only on exact archive replay. A new score batch or
    # mapping must not display narratives bound to older answers or grade bands.
    explanations = (data.get('pro_palestine_grading') or {}).get('explanations')
    if preserve_explanations: result['pro_palestine_grading']['explanations'] = explanations
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot',type=Path,help='Saved /api/bootstrap response; only used for first freeze')
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--published-on',default=date.today().isoformat())
    ap.add_argument('--criteria',type=Path,default=DEFAULT_CRITERIA,help='Versioned exact preferred questions for this publication')
    ap.add_argument('--explanation-queue',type=Path,help='Write an immutable, source-bound Hermes follow-up queue')
    args=ap.parse_args(); path=args.archive.resolve()
    if not path.is_relative_to(ROOT/'research/gaza-grading'):
        raise ValueError('Store the immutable archive under research/gaza-grading')
    if args.snapshot:
        if path.exists(): raise ValueError('Preserve the existing archive; use a new publication path')
        criteria_path=args.criteria.resolve()
        if not criteria_path.is_relative_to(ROOT/'research/gaza-grading'):
            raise ValueError('Store preferred criteria under research/gaza-grading')
        boot=json.loads(args.snapshot.read_text()); preferred=json.loads(criteria_path.read_text())
        archive=freeze(boot['latest'],boot['score_grade_mapping'],preferred,args.published_on,str(criteria_path.relative_to(ROOT)))
        # Validate every projection before writing an archive or the dataset.
        attach(json.loads(DATASET.read_text()),archive,str(path.relative_to(ROOT)),'0'*64)
        path.write_text(json.dumps(archive,ensure_ascii=False,indent=1)+'\n')
    archive=json.loads(path.read_text())
    data=attach(json.loads(DATASET.read_text()),archive,str(path.relative_to(ROOT)),digest(path.read_bytes()))
    queue_text=None
    if args.explanation_queue:
        queue={'version':1,'publication_id':archive['id'],'archive_path':str(path.relative_to(ROOT)),
               'preferred_criteria_path':data['pro_palestine_grading']['preferred_criteria_path'],
               'candidates':[{'id':r['id'],'position_id':r['position_id'],'candidate':r['candidate'],
                              'roster':r['roster'],'request_sha256':r['request_sha256']} for r in archive['rows']]}
        queue_text=json.dumps(queue,ensure_ascii=False,indent=1)+'\n'
        if args.explanation_queue.exists() and args.explanation_queue.read_text()!=queue_text:
            raise ValueError('Preserve the existing explanation queue; use a new path')
    DATASET.write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n')
    if queue_text is not None:
        args.explanation_queue.parent.mkdir(parents=True,exist_ok=True)
        args.explanation_queue.write_text(queue_text)
    print(json.dumps({'published':len(archive['rows']),'archive':str(path.relative_to(ROOT))}))


if __name__=='__main__':main()
