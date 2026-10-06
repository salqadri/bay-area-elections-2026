"""Create a DOM fixture for executing the actual explorer script without a browser."""
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / ".checks"
GENERATED.mkdir(exist_ok=True)


class FixtureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {'tag': 'document', 'attrs': {}, 'children': []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        item = {'tag': tag, 'attrs': dict(attrs), 'children': []}
        self.stack[-1]['children'].append(item)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(item)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i]['tag'] == tag:
                self.stack = self.stack[:i]
                return

    def handle_data(self, text):
        self.stack[-1]['children'].append(text)


for page, name in [('index', 'explorer'), ('ballot', 'ballot')]:
    parser = FixtureParser()
    parser.feed((ROOT / (page + '.html')).read_text())
    (GENERATED / (name + '_dom_fixture.json')).write_text(json.dumps(parser.root))
    print('Parsed ' + page + '.html into DOM fixture.')
