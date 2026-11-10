#!/usr/bin/env python3
"""
Checks every link of the built site, offline: each href and src of each
page in site/ (the IDE's own files aside) must lead to a file of the site,
and each #fragment to an id on the page it names. Links to other sites are
counted, not fetched (--external lists them). Also checks that each page
has its counterpart in the other language.

    python3 tools/check_links.py [--external]

Exits non-zero if anything is broken.
"""

import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), 'site')


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.add(a['id'])
        if tag == 'a' and 'name' in a:
            self.ids.add(a['name'])
        for k in ('href', 'src'):
            if a.get(k) is not None and not (tag == 'link' and a.get('rel') in ('canonical', 'alternate')) \
                    and not (tag == 'meta'):
                self.links.append((tag, a[k]))


def target_file(path):
    full = os.path.join(SITE, path.lstrip('/'))
    if path.endswith('/') or os.path.isdir(full):
        full = os.path.join(full, 'index.html')
    return full


def main():
    pages = {}
    for root, dirs, files in os.walk(SITE):
        rel_root = os.path.relpath(root, SITE)
        if rel_root.split(os.sep)[0] == 'ide':
            dirs[:] = []
            continue
        for f in files:
            if f.endswith('.html'):
                path = '/' + os.path.relpath(os.path.join(root, f), SITE).replace(os.sep, '/')
                p = Page()
                with open(os.path.join(root, f), encoding='utf-8') as fh:
                    p.feed(fh.read())
                pages[path] = p
    broken, external = [], set()
    count = 0
    for path, page in sorted(pages.items()):
        for tag, link in page.links:
            count += 1
            u = urlsplit(link)
            if u.scheme in ('http', 'https', 'mailto'):
                if u.netloc != 'gapkeep.org':
                    external.add(link)
                    continue
                link = u.path + ('#' + u.fragment if u.fragment else '')
                u = urlsplit(link)
            elif u.scheme == 'data':
                continue
            elif u.scheme:
                broken.append('%s: unexpected link %s' % (path, link))
                continue
            if u.path:
                target = unquote(u.path) if u.path.startswith('/') else \
                    os.path.normpath(os.path.join(os.path.dirname(path), unquote(u.path))).replace(os.sep, '/') + \
                    ('/' if u.path.endswith('/') else '')
            else:
                target = path
            full = target_file(target)
            if not os.path.exists(full):
                broken.append('%s: %s -> %s does not exist' % (path, link, target))
                continue
            if u.fragment:
                key = '/' + os.path.relpath(full, SITE).replace(os.sep, '/')
                if key in pages and u.fragment not in pages[key].ids:
                    broken.append('%s: %s -> no id "%s" in %s' % (path, link, u.fragment, key))
    # every page in both languages
    for path in pages:
        if path.startswith('/pt-br/'):
            other = path[len('/pt-br'):]
        elif path == '/logo-concepts.html':
            continue
        else:
            other = '/pt-br' + path
        if other not in pages:
            broken.append('%s: no counterpart %s' % (path, other))
    if '--external' in sys.argv:
        for e in sorted(external):
            print('external:', e)
    for b in broken:
        print('BROKEN', b)
    print('%d pages, %d links checked, %d to other sites (not fetched), %d broken'
          % (len(pages), count, len(external), len(broken)))
    sys.exit(1 if broken else 0)


if __name__ == '__main__':
    main()
