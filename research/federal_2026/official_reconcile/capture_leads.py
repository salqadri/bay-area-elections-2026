#!/usr/bin/env python3
"""Wave 1 of official-source reconciliation: capture every cached .gov lead.

Fetches each contest's first usable official lead into raw/ (content-addressed,
resumable), records content-type + size so the per-state parser pass can route
PDF vs HTML vs JS-shell. Never mutates the dataset. MA has no cached lead and is
discovered separately.
"""
import hashlib, json, os, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = f'{HERE}/raw'
os.makedirs(RAW, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'

def fetch(url):
    """Return (sha, path, http_code, content_type, body_bytes_head)."""
    r = subprocess.run(['curl', '-sL', '-m', '60', '--compressed', '-A', UA,
                        '-w', '\n@@%{http_code}@@%{content_type}@@%{url_effective}', url],
                       capture_output=True)
    body = r.stdout
    marker = b'\n@@'
    idx = body.rfind(marker)
    tail = body[idx+3:].decode('utf-8', 'replace') if idx >= 0 else ''
    body = body[:idx] if idx >= 0 else body
    parts = tail.split('@@')
    code, ctype, final = (parts + ['', '', ''])[:3]
    sha = hashlib.sha256(body).hexdigest()[:16]
    ext = '.pdf' if ('%PDF' in body[:8].decode('latin1')) else ('.html' if b'<' in body[:400] else '.bin')
    path = f'{RAW}/{sha}{ext}'
    open(path, 'wb').write(body)
    return sha, path, code, ctype, final, len(body)

def main():
    leads = json.load(open(f'{HERE}/../official_leads.json'))
    state_file = f'{HERE}/captures.json'
    try: caps = json.load(open(state_file))
    except FileNotFoundError: caps = {}
    for pid in sorted(leads):
        entry = leads[pid]
        if pid in caps and caps[pid].get('sha'):
            continue
        rec = {'state': entry['state'], 'office': entry['office']}
        tried = []
        for hit in entry['gov_hits'][:3]:
            url = hit['url']
            try:
                sha, path, code, ctype, final, size = fetch(url)
            except Exception as e:
                tried.append({'url': url, 'error': str(e)[:120]}); continue
            tried.append({'url': url, 'code': code, 'ctype': ctype[:60], 'final_url': final, 'bytes': size})
            if code == '200' and size > 500:
                rec.update({'sha': sha, 'path': os.path.basename(path), 'source_url': url,
                            'final_url': final, 'code': code, 'ctype': ctype[:60],
                            'bytes': size, 'checked_on': time.strftime('%Y-%m-%d')})
                break
        rec['attempts'] = tried
        caps[pid] = rec
        json.dump(caps, open(state_file, 'w'), indent=1)
        print(pid, entry['state'], entry['office'], '->', rec.get('path', 'FAILED'),
              rec.get('ctype', '')[:30], rec.get('bytes', 0), flush=True)

if __name__ == '__main__':
    main()
