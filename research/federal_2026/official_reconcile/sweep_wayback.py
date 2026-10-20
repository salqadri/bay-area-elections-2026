#!/usr/bin/env python3
"""Wave 2 wayback sweep: for each still-unverified contest, query the Wayback
CDX index for recent (post-primary, Aug-Oct 2026) snapshots of candidate-list
URLs on the state's official domain(s). Prints candidates ranked by recency;
capture step is manual/next script."""
import json, re, subprocess, sys

DATASET = '/workspace/bay-area-elections-2026/2026-11-03_Bay_Area_Elections.json'
# state -> (domains, url regex for listy pages)
STATES = {
 'AL': ['sos.alabama.gov'], 'AR': ['candidates.arkansas.gov', 'sos.arkansas.gov'],
 'CO': ['coloradosos.gov'], 'CT': ['portal.ct.gov'], 'FL': ['dos.elections.myflorida.com', 'ee.dos.florida.com'],
 'GA': ['sos.ga.gov', 'ballotaccess.sos.ga.gov'], 'HI': ['elections.hawaii.gov', 'csc.hawaii.gov'],
 'IA': ['sos.iowa.gov'], 'ID': ['sos.idaho.gov', 'idea.idaho.gov', 'voteidaho.gov'],
 'KS': ['sos.ks.gov'], 'LA': ['voterportal.sos.la.gov', 'sos.la.gov', 'la.gov'],
 'ME': ['maine.gov'], 'MI': ['michigan.gov'], 'MN': ['candidates.sos.mn.gov', 'sos.mn.gov'],
 'MS': ['sos.ms.gov'], 'NC': ['ncsbe.gov'], 'NH': ['sos.nh.gov'], 'NJ': ['nj.gov'],
 'NV': ['nvsos.gov'], 'OK': ['oklahoma.gov'], 'OR': ['oregon.gov', 'sos.oregon.gov', 'secure.sos.state.or.us'],
 'PA': ['pa.gov', 'pavoterservices.pa.gov', 'dos.pa.gov'], 'RI': ['vote.sos.ri.gov', 'elections.ri.gov', 'ri.gov'],
 'SC': ['scvotes.gov', 'vrems.scvotes.sc.gov'], 'TN': ['sos.tn.gov'], 'TX': ['sos.texas.gov', 'texas.gov'],
 'VT': ['vermont.gov'], 'VA': ['elections.virginia.gov'], 'WI': ['wi.gov', 'wisconsin.gov'],
 'WV': ['wv.gov', 'apps.sos.wv.gov'], 'WY': ['wyo.gov'],
}
LISTY = re.compile(r'(candidat|ballot|qualified|nominee|general)', re.I)

def cdx(domain):
    url = (f'http://web.archive.org/cdx/search/cdx?url={domain}*&from=20260815&to=20261020'
           '&output=text&fl=timestamp,original,statuscode,mimetype,length&collapse=urlkey'
           f'&filter=statuscode:200&limit=4000')
    r = subprocess.run(['curl', '-s', '-m', '90', url], capture_output=True)
    return r.stdout.decode('utf-8', 'replace').splitlines()

def main():
    data = json.load(open(DATASET))
    caps = json.load(open('/workspace/bay-area-elections-2026/research/federal_2026/official_reconcile/captures.json'))
    unv = [p['id'] for p in data['positions'] if p['ballot_status'] == 'unverified']
    st_of = {pid: (caps.get(pid) or {}).get('state') for pid in unv}
    todo_states = sorted({st_of[pid] for pid in unv if st_of.get(pid)})
    only = set(sys.argv[1:]) or None
    out = {}
    for st in todo_states:
        if only and st not in only: continue
        rows = []
        for dom in STATES.get(st, []):
            for line in cdx(dom):
                parts = line.split(' ')
                if len(parts) < 5: continue
                ts, orig, code, mime, ln = parts[:5]
                if not LISTY.search(orig): continue
                if re.search(r'(press|news|calendar|guide|form|law|code|map|poll|survey|job)', orig, re.I): continue
                rows.append((ts, orig, mime, int(ln) if ln.isdigit() else 0))
        rows.sort(reverse=True)
        out[st] = rows[:25]
        print(f"\n##### {st}: {len(rows)} listy snapshots")
        for ts, orig, mime, ln in rows[:12]:
            print(f"  {ts} {mime[:9]} {ln:>8} {orig[:105]}")
    json.dump(out, open('/tmp/wayback_sweep.json', 'w'), indent=1)

if __name__ == '__main__':
    main()
