#!/usr/bin/env python3
"""Regenerate the 8 race-reason paragraphs that named Samir Laymoun despite the
prompt policy (his support/opposition must be omitted from voter prose when
other relevant directional evidence exists — see summary_source_policy).
Uses the reasons-phase ban-list retry pattern with an explicit hard constraint,
validates each result against prose_errors exactly like
check_summary_source_policy does, and appends the corrected records (the cache
loader keeps the latest record per position_id).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_recommendations as rec  # noqa: E402
from summary_source_policy import prose_errors  # noqa: E402

BAN = ("\nHARD CONSTRAINT: you may NOT mention, allude to, or characterize Samir Laymoun "
       "or his recommendations in this paragraph — not by name, not anonymously, not as "
       "\"an individual\" or \"another source\". Omit his support and opposition entirely; "
       "build the paragraph from the remaining evidence only. Output ONLY the paragraph.")

TARGETS = ['CA2026-005', 'CA2026-025', 'CA2026-094', 'CA2026-148',
           'CA2026-152', 'CA2026-161', 'CA2026-162', 'CA2026-173']


def main():
    data = json.loads(rec.DATA.read_text())
    by_pos = {p['id']: p for p in data['positions']}
    plan = json.loads(rec.PLAN.read_text())
    races = {r['position_id']: r for r in plan['races']}
    with rec.REASON_CACHE.open('a') as out:
        for pid in TARGETS:
            race = races[pid]
            prompt = rec.reason_prompt(race, by_pos)
            assert 'Samir Laymoun source policy' in prompt, 'policy line missing from prompt'
            text = rec._lmstudio(prompt + BAN, max_tokens=8000)
            for attempt in range(2):
                errs = prose_errors(text, {'samir_allowed': pid == 'CA2026-174'})
                if not errs:
                    break
                print(f'  [retry {attempt+1}] {pid}: {errs}', flush=True)
                text = rec._lmstudio(prompt + BAN, max_tokens=8000)
            errs = prose_errors(text, {'samir_allowed': pid == 'CA2026-174'})
            if errs:
                raise SystemExit(f'{pid} still violating after retries: {errs}')
            words = len(text.split())
            if not 30 <= words <= 215:
                raise SystemExit(f'{pid}: {words} words outside 30-215')
            out.write(json.dumps({'position_id': pid, 'text': text, 'words': words,
                                  'model': rec.LMSTUDIO_MODEL,
                                  'prompt_sha256': rec.request_hash(prompt)}) + '\n')
            print(pid, '->', words, 'words', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
