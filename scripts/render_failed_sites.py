"""Render bot-walled / JS-only campaign sites with headless Chromium and store
the resulting pages into the scan ledger exactly like the plain-HTTP crawler, so
extract-llm/propose proceed unchanged. Use AFTER `campaign_endorsements.py crawl`
has exhausted its browser-UA and Internet-Archive fallbacks; requires
`pip install playwright && python3 -m playwright install chromium`.

Usage: python3 scripts/render_failed_sites.py [site_key ...]   (default: all state='error' tasks)
Pass explicit site keys to force-refresh a shallow crawl regardless of task state.
"""
import hashlib
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, 'scripts')
from campaign_endorsements import DEFAULT_DB, ENDORSE_LINK, NOISE_LINK, clean_url, _page_from_raw, dump  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def render_page(pg, url):
    pg.goto(url, timeout=60000, wait_until='domcontentloaded')
    try:
        pg.wait_for_load_state('networkidle', timeout=15000)
    except Exception:  # noqa: BLE001 - some sites poll forever; DOM is enough
        pass
    time.sleep(2.5)  # let late hydration paint
    html = pg.content()
    final = clean_url(pg.url) or url
    page = _page_from_raw(html.encode('utf-8'), final)
    page['capture'] = 'headless Chromium render'
    return page


def render_site(browser, root):
    """Render a site (root + endorsement links), retrying with media blocked —
    heavy animated sites can crash the renderer otherwise."""
    for block_media in (False, True):
        ctx = browser.new_context(user_agent=UA, viewport={'width': 1440, 'height': 2200})
        if block_media:
            ctx.route('**/*', lambda r: r.abort()
                      if r.request.resource_type in ('image', 'media', 'font') else r.continue_())
        pg = ctx.new_page()
        try:
            page = render_page(pg, root)
            pages = {page['final_url']: page}
            host = clean_url(root).split('/')[2].removeprefix('www.')
            followed = 0
            for link in page.get('links', []):
                if followed >= 8:
                    break
                try:
                    child = clean_url(link['url'])
                except (ValueError, KeyError):
                    continue
                label = (link.get('text') or '') + ' ' + child
                if (child.split('/')[2].removeprefix('www.') != host or child in pages
                        or NOISE_LINK.search(label) or not ENDORSE_LINK.search(label)):
                    continue
                try:
                    sub = render_page(pg, child)
                except Exception:  # noqa: BLE001
                    continue
                pages[sub['final_url']] = sub
                followed += 1
            return pages
        finally:
            try:
                ctx.close()  # isolate renderer crashes per site/attempt
            except Exception:  # noqa: BLE001
                pass
    raise ValueError('render failed with and without media')


def main():
    db = sqlite3.connect(DEFAULT_DB)
    wanted = set(sys.argv[1:])
    rows = list(db.execute("SELECT site_key, campaign_url, state FROM tasks ORDER BY site_key"))
    if wanted:
        # explicit keys render regardless of state (force-refresh shallow crawls)
        tasks = [{'site_key': k, 'campaign_url': u} for k, u, _st in rows if k in wanted]
    else:
        tasks = [{'site_key': k, 'campaign_url': u} for k, u, st in rows if st == 'error']
    print(f'rendering {len(tasks)} sites', flush=True)
    ok = fail = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-dev-shm-usage', '--no-sandbox',
                                                         '--js-flags=--max-old-space-size=2048'])
        for t in tasks:
            key, root = t['site_key'], t['campaign_url']
            try:
                pages = render_site(browser, root)
                sha_all = hashlib.sha256(dump(pages).encode()).hexdigest()
                db.execute('DELETE FROM pages WHERE site_key=?', (key,))
                db.execute('DELETE FROM results WHERE site_key=?', (key,))
                for url, pp in pages.items():
                    db.execute('INSERT OR REPLACE INTO pages(site_key,url,sha,observed_at,page_json) VALUES(?,?,?,?,?)',
                               (key, url, sha_all, now(), json.dumps(pp, sort_keys=True)))
                db.execute("UPDATE tasks SET state='crawled', error=NULL, observed_at=? WHERE site_key=?", (now(), key))
                db.commit()
                ok += 1
                print(f'OK   {root} ({len(pages)} pages)', flush=True)
            except Exception as e:  # noqa: BLE001
                fail += 1
                db.execute("UPDATE tasks SET error=? WHERE site_key=?", (str(e)[:280], key))
                db.commit()
                print(f'FAIL {root}: {type(e).__name__} {str(e)[:90]}', flush=True)
        browser.close()
    print(json.dumps({'ok': ok, 'fail': fail}))


if __name__ == '__main__':
    main()
