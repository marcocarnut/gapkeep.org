#!/usr/bin/env python3
"""
Print dice39's dice tables to PDF, in English and Portuguese, A4 and Letter.

The tables are dice39's own: its page (bip39_generator.html) builds them
from its bundled wordlist and prints them with its print stylesheet, so
this only loads the page in headless Chrome and saves what Ctrl+P would
print. They hold no secret.

Usage: tools/dice39_pdfs.py <path/to/bip39_generator.html> <output-dir>

Writes dice39-tables-{en,pt-br}-{a4,letter}.pdf, and dice39-tables.json
with the source's SHA-256 (the GapKeep app names the same hash in
apps/dice39/vendor/).

SPDX-License-Identifier: GPL-3.0-or-later
"""
import asyncio
import base64
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

DEBUG_PORT = 9333
PAPERS = {'a4': (11.69, 8.27), 'letter': (11.0, 8.5)}   # inches, landscape
LANGS = {'en': 'en', 'pt-br': 'pt'}


def pages(data):
    return len(re.findall(rb'/Type\s*/Page(?![s\w])', data))


async def call(ws, n, method, **params):
    await ws.send(json.dumps({'id': n, 'method': method, 'params': params}))
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), 120))
        if msg.get('id') == n:
            if 'error' in msg:
                raise RuntimeError('%s: %s' % (method, msg['error']))
            return msg.get('result', {})


async def run(src, out):
    tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % DEBUG_PORT))
    page = [t for t in tabs if t['type'] == 'page'][0]
    written = []
    async with websockets.connect(page['webSocketDebuggerUrl'], max_size=None) as ws:
        n = 0
        for slug, lang in LANGS.items():
            n += 1
            await call(ws, n, 'Page.navigate', url=pathlib.Path(src).resolve().as_uri() + '?lang=' + lang)
            for _ in range(100):
                n += 1
                r = await call(ws, n, 'Runtime.evaluate', returnByValue=True,
                               expression="document.readyState == 'complete' && "
                                          "document.querySelectorAll('#printSheets table').length")
                if r.get('result', {}).get('value'):
                    break
                time.sleep(0.1)
            else:
                sys.exit('dice39_pdfs: no tables on the page (%s)' % lang)
            n += 1
            r = await call(ws, n, 'Runtime.evaluate', returnByValue=True,
                           expression='document.documentElement.lang')
            got = r['result']['value']
            if not got.lower().startswith(lang):
                sys.exit('dice39_pdfs: asked for %s, the page is in %s' % (lang, got))
            n += 1
            r = await call(ws, n, 'Runtime.evaluate', returnByValue=True,
                           expression="document.querySelectorAll('#printSheets > *').length")
            sheets = r['result']['value']
            for paper, (w, h) in PAPERS.items():
                # one sheet a page: the page's text in Portuguese runs a few
                # lines past an A4 page, so shrink a little until it fits
                for scale in (1.0, 0.98, 0.96, 0.94, 0.92, 0.9):
                    n += 1
                    r = await call(ws, n, 'Page.printToPDF', landscape=True, printBackground=True,
                                   paperWidth=w, paperHeight=h, preferCSSPageSize=True, scale=scale,
                                   marginTop=0, marginBottom=0, marginLeft=0, marginRight=0)
                    data = base64.b64decode(r['data'])
                    if pages(data) == sheets:
                        break
                else:
                    sys.exit('dice39_pdfs: %s %s: the sheets do not fit one a page' % (slug, paper))
                name = 'dice39-tables-%s-%s.pdf' % (slug, paper)
                with open(os.path.join(out, name), 'wb') as f:
                    f.write(data)
                written.append(name)
    return written


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    chrome_bin = shutil.which('google-chrome') or shutil.which('chromium')
    profile = tempfile.mkdtemp(prefix='gksite-chrome-')
    chrome = subprocess.Popen([chrome_bin, '--headless=new', '--no-sandbox',
                               '--remote-debugging-port=%d' % DEBUG_PORT,
                               '--user-data-dir=' + profile, 'about:blank'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen('http://127.0.0.1:%d/json' % DEBUG_PORT)
                break
            except OSError:
                time.sleep(0.2)
        written = asyncio.run(run(src, out))
    finally:
        chrome.terminate()
        chrome.wait()
        shutil.rmtree(profile, ignore_errors=True)
    with open(src, 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.join(out, 'dice39-tables.json'), 'w') as f:
        json.dump({'source': 'bip39_generator.html', 'sha256': sha, 'files': written}, f, indent=1)
        f.write('\n')
    for w in written:
        print(os.path.join(out, w))


if __name__ == '__main__':
    main()
