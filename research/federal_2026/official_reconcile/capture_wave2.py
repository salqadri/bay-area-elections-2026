#!/usr/bin/env python3
"""Capture wave-2 leads: fetch each pid's wave2_hits until one looks like a real
candidate list; record as caps[pid]['wave2'] (does not overwrite the wave-1 rec)."""
import hashlib, json, os, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = f'{HERE}/raw'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'

def fetch(url):
    r = subprocess.run(['curl', '-sL', '-m', '90', '--compressed', '-A', UA,
                        '-w', '\n@@%{http_code}@@%{content_type}@@%{url_effective}', url],
                       capture_output=True)
    body = r.stdout
    idx = body.rfind(b'\n@@')
    tail = body[idx+3:].decode('utf-8', 'replace') if idx >= 0 else ''
    body = body[:idx] if idx >= 0 else body
    code, ctype, final = (tail.split('@@') + ['', '', ''])[:3]
    sha = hashlib.sha256(body).hexdigest()[:16]
    ext = '.pdf' if ('%PDF' in body[:8].decode('latin1')) else ('.html' if b'<' in body[:400] else '.bin')
    path = f'{RAW}/{sha}{ext}'
    open(path, 'wb').write(body)
    return sha, os.path.basename(path), code, ctype, final, len(body)

def main():
    leads = json.load(open(f'{HERE}/../official_leads.json'))
    sf = f'{HERE}/captures.json'
    caps = json.load(open(sf))
    for pid in sorted(leads):
        e = leads[pid]
        if not e.get('wave2_hits') or (caps.get(pid) or {}).get('wave2'): continue
        rec = {'tried': []}
        for hit in e['wave2_hits'][:5]:
            try:
                sha, name, code, ctype, final, size = fetch(hit['url'])
            except Exception as ex:
                rec['tried'].append({'url': hit['url'], 'error': str(ex)[:100]}); continue
            rec['tried'].append({'url': hit['url'], 'code': code, 'bytes': size, 'ctype': ctype[:50]})
            if code == '200' and size > 800:
                rec.update({'sha': sha, 'path': name, 'source_url': hit['url'], 'final_url': final,
                            'code': code, 'bytes': size, 'checked_on': time.strftime('%Y-%m-%d')})
                break
        caps.setdefault(pid, {'state': e['state'], 'office': e['office']})['wave2'] = rec
        json.dump(caps, open(sf, 'w'), indent=1)
        print(pid, e['state'], '->', rec.get('path', 'FAILED'), rec.get('bytes', 0))

if __name__ == '__main__':
    main()
