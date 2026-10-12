"""Page-context rule: recover held proposals where Jev said choice='endorsement'
but confidence < 0.75, when BOTH the endorser name and its quote appear verbatim
on a captured page whose URL marks it as an endorsements/support listing — the
campaign's own page structure is mechanical evidence of endorsement intent.
Writes a decisions JSON compatible with apply-review:

    python3 scripts/page_context_rule.py
    python3 scripts/campaign_endorsements.py apply-review \
        .research/endorsements/review/campaign-page-context-accepts.json
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, 'scripts')
from campaign_endorsements import DEFAULT_DB  # noqa: E402
from endorsement_extract import norm  # noqa: E402

db = sqlite3.connect(DEFAULT_DB)
pages_by_site = {}


def pages(site_key):
    if site_key not in pages_by_site:
        out = []
        for url, pj in db.execute("select url, page_json from pages where site_key=?", (site_key,)):
            p = json.loads(pj)
            out.append((url.lower(), norm(p.get('text', ''))))
        pages_by_site[site_key] = out
    return pages_by_site[site_key]


rows = db.execute("""SELECT p.proposal_id, p.site_key, p.record_json, j.p_endorse FROM proposals p
                    JOIN jev_triage j USING(proposal_id)
                    WHERE p.gate='quote_verified' AND j.choice='endorsement' AND j.p_endorse < 0.75""").fetchall()
accepted = []
for pid, site_key, rj, p in rows:
    rec = json.loads(rj)
    name_q = norm(rec.get('endorser', ''))
    quote_n = norm(rec.get('quote', ''))
    for url, tnorm in pages(site_key):
        if ('endorse' in url or 'support' in url) and name_q and name_q in tnorm and (not quote_n or quote_n in tnorm):
            accepted.append({'proposal_id': pid, 'action': 'accept',
                             'reason': "page-context rule: endorser name AND quote appear verbatim on the campaign's own endorsements/support page; Jev classified it an endorsement (p=" + str(p) + ') below the 0.75 bar',
                             'reviewed_by': 'page_context_rule'})
            break
out = Path('.research/endorsements/review/campaign-page-context-accepts.json')
out.write_text(json.dumps(accepted))
cc = [a for a in accepted if db.execute("select campaign_url from tasks where site_key=?", (next(
    s for s, in db.execute("select site_key from proposals where proposal_id=?", (a['proposal_id'],))),)).fetchone()[0].find('conniechan') >= 0]
print(json.dumps({'accepted': len(accepted), 'connie_chan_recovered': [
    json.loads(db.execute("select record_json from proposals where proposal_id=?", (a['proposal_id'],)).fetchone()[0])['endorser'] for a in cc]}))
