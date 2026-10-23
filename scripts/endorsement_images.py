"""Lossless DOM image inventory. Filenames are metadata, never identities.

The inventory is deliberately broader than endorsements. A reviewer must select
relevant source observations; page URLs/headings alone establish no relationship.
"""
from html.parser import HTMLParser
import hashlib
from datetime import date
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, quote, unquote

VERSION = 'campaign-dom-images-3'
SUPPORTED_VERSIONS = {'campaign-dom-images-2', VERSION}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
SKIP = {'script', 'style', 'noscript', 'svg', 'template'}


def encode_url(url):
    p = urlsplit(url.strip())
    if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password:
        raise ValueError('Expected a public image URL without credentials')
    return urlunsplit((p.scheme, p.netloc, quote(p.path, safe="/%:@&=+$,-_.!~*'()"),
                      quote(p.query, safe="%=&;:+,/?@!$'()*-._~"), ''))


class Node:
    def __init__(self, tag='', attrs=None, parent=None):
        self.tag, self.attrs, self.parent = tag, attrs or {}, parent
        self.children = []
        self._text = None

    def text(self):
        if self.tag in SKIP:
            return ''
        if self._text is None:
            self._text = re.sub(r'\s+', ' ', ' '.join(c if isinstance(c, str) else c.text() for c in self.children)).strip()
        return self._text


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.images = []
        self.heading = ''
        self.headings = {}

    def handle_starttag(self, tag, attrs):
        # HTML permits unclosed list items and paragraphs.
        if tag in {'li', 'p'} and self.stack[-1].tag == tag:
            self.stack.pop()
        n = Node(tag, dict(attrs), self.stack[-1])
        n.parent.children.append(n)
        if tag == 'img':
            self.images.append(n)
            self.headings[id(n)] = self.heading
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                n = self.stack[i]
                if re.fullmatch('h[1-6]', tag):
                    self.heading = n.text()
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def images_from_html(html, base, unresolved=None):
    tree = Tree(); tree.feed(html); tree.close()
    out = []
    for index, n in enumerate(tree.images):
        a = n.attrs
        # Unbounce/responsive and common lazy loaders keep real URLs in data
        # attributes while src is only a data-URI placeholder. Preserve an
        # explicitly supplied URL; never derive a filename or resolution.
        raw = next((a[k] for k in ('data-src', 'data-lazy-src', 'data-src-desktop-1x',
                                   'data-src-mobile-1x', 'data-original', 'data-litespeed-src', 'src')
                    if a.get(k) and not a[k].startswith('data:')), a.get('src'))
        # Some lazy loaders publish only a srcset. Keep the actual selected URL,
        # not an inferred filename or a guessed higher-resolution derivative.
        if (not raw or raw.startswith('data:')) and (a.get('data-srcset') or a.get('srcset')):
            raw = (a.get('data-srcset') or a.get('srcset')).split(',')[0].strip().split()[0]
        if not raw:
            if unresolved is not None:
                unresolved.append({'index': index, 'reason': 'No src/data-src/srcset; browser or CSS review needed'})
            continue
        try:
            src = encode_url(urljoin(base, raw))
        except ValueError:
            if unresolved is not None:
                unresolved.append({'index': index, 'reason': 'Unsupported or non-public image URL; manual review needed'})
            continue
        ancestry, parent = [], n.parent
        context = ''
        while parent and parent.tag:
            ancestry.append(parent.tag)
            text = parent.text()
            if not context and text and len(text) <= 1200:
                context = text
            parent = parent.parent
        # Keep occurrences (the same asset can accompany different people).
        out.append({'src': src, 'alt': a.get('alt') or '', 'title': a.get('title') or '',
                    'filename': unquote(urlsplit(src).path.rsplit('/', 1)[-1]),
                    'nearby': context, 'heading': tree.headings[id(n)],
                    'class': a.get('class') or '', 'index': index,
                    'chrome': any(t in {'nav', 'footer', 'header'} for t in ancestry),
                    'observation_id': 'I-' + hashlib.sha256((base + '\n' + str(index) + '\n' + src).encode()).hexdigest()[:24]})
    return out


def image_record(image, source_url, checked_on, source_sha256):
    """Neutral publication record; selection and review happen outside this parser."""
    return {'id': image['observation_id'], 'source_url': source_url, 'image_url': image['src'],
            'filename': image['filename'], 'original_alt': image['alt'],
            'context': image['nearby'], 'heading': image['heading'], 'checked_on': checked_on,
            'provenance': 'page_capture', 'source_sha256': source_sha256}


def validate_published_images(data, root):
    errors = []
    for position in data['positions']:
        for candidate in position.get('candidates') or []:
            seen = set()
            for record in candidate.get('endorsement_images', []):
                prefix = candidate['name'] + ': '
                if record['id'] in seen:
                    errors.append(prefix + 'duplicate image observation')
                seen.add(record['id'])
                if date.fromisoformat(record['checked_on']) > date.today():
                    errors.append(prefix + 'future image observation')
                if 'asset_path' in record or 'image_sha256' in record:
                    errors.append(prefix + 'use external image URLs without copied-asset fields')
    return errors
