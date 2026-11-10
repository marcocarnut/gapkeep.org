#!/usr/bin/env python3
"""
Opens the site's pages in headless Chrome, over its DevTools protocol, and
checks what a link checker can't: that no page asks for anything outside
the site (fonts, scripts, images: no third-party requests at all), that
nothing breaks the Content-Security-Policy, that there are no JavaScript
errors, that the IDE under /ide/ starts, and that a "Try it" link
(?run=totp&lang=pt-BR) boots that app at phone size (its screenshot goes
to screenshots/). It can also take the IDE's
screenshot for the home page.

    python3 -m http.server 8047 --bind 127.0.0.1 --directory site &
    python3 tools/browser_check.py [--base http://127.0.0.1:8047] [--ide-shot]

--ide-shot writes site/img/ide.png: the IDE running the hello app.
Needs Google Chrome and Python's websockets (Debian: python3-websockets).
"""

import argparse
import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), 'site')
DEBUG_PORT = 9347

PAGES = ['/', '/pt-br/', '/download.html', '/pt-br/download.html', '/docs/', '/pt-br/docs/',
         '/docs/architecture.html', '/pt-br/docs/apps/signer.html', '/gapwallet/', '/pt-br/gapwallet/',
         '/logo-concepts.html', '/404.html']


class CDP:
    def __init__(self, ws):
        self.ws, self.n, self.events, self.waiting = ws, 0, [], {}

    async def reader(self):
        async for raw in self.ws:
            msg = json.loads(raw)
            if 'id' in msg and msg['id'] in self.waiting:
                self.waiting.pop(msg['id']).set_result(msg)
            elif 'method' in msg:
                self.events.append(msg)

    async def call(self, method, **params):
        self.n += 1
        fut = asyncio.get_event_loop().create_future()
        self.waiting[self.n] = fut
        await self.ws.send(json.dumps({'id': self.n, 'method': method, 'params': params}))
        msg = await asyncio.wait_for(fut, 60)
        if 'error' in msg:
            raise RuntimeError('%s: %s' % (method, msg['error']))
        return msg.get('result', {})

    async def js(self, expr):
        r = await self.call('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=True)
        return r.get('result', {}).get('value')


async def run(args):
    base = args.base.rstrip('/')
    tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % DEBUG_PORT))
    page = [t for t in tabs if t['type'] == 'page'][0]
    problems = []
    async with websockets.connect(page['webSocketDebuggerUrl'], max_size=100_000_000) as ws:
        cdp = CDP(ws)
        task = asyncio.ensure_future(cdp.reader())
        for d in ('Page', 'Runtime', 'Network', 'Log'):
            await cdp.call(d + '.enable')
        # each page in its own language: no redirect by the browser's
        await cdp.call('Page.addScriptToEvaluateOnNewDocument', source=
                       "try { localStorage.setItem('gapkeep-lang', location.pathname.indexOf('/pt-br/') === 0 ? 'pt-BR' : 'en'); } catch (e) {}")
        await cdp.call('Emulation.setDeviceMetricsOverride', width=1440, height=860, deviceScaleFactor=1, mobile=False)
        for path in PAGES:
            cdp.events.clear()
            await cdp.call('Page.navigate', url=base + path)
            await asyncio.sleep(2.0)
            for ev in cdp.events:
                m, p = ev['method'], ev['params']
                if m == 'Network.requestWillBeSent':
                    url = p['request']['url']
                    # the /gapwallet/ pages forward to GapWallet's own site: a
                    # navigation, not a request the page makes
                    if p.get('type') == 'Document' and url.startswith('https://gapwallet.org/') \
                            and path.endswith('/gapwallet/'):
                        continue
                    if not (url.startswith(base) or url.startswith('data:') or url.startswith('blob:')):
                        problems.append('%s: request outside the site: %s' % (path, url))
                elif m == 'Runtime.exceptionThrown':
                    problems.append('%s: exception: %s' % (path, p['exceptionDetails'].get('text')))
                elif m == 'Log.entryAdded' and p['entry']['level'] in ('error', 'warning'):
                    text = p['entry'].get('text', '')
                    if path == '/404.html' and '404' in text:
                        continue
                    problems.append('%s: console %s: %s' % (path, p['entry']['level'], text))
                elif m == 'Runtime.consoleAPICalled' and p['type'] in ('error', 'warning'):
                    problems.append('%s: console.%s: %s' % (path, p['type'],
                                                            ' '.join(str(a.get('value', '')) for a in p['args'])))
            print('ok  ' if not any(x.startswith(path + ':') for x in problems) else 'FAIL', path)

        # The IDE: starts, and runs an app
        cdp.events.clear()
        await cdp.call('Page.navigate', url=base + '/ide/')
        ok = False
        for _ in range(60):
            await asyncio.sleep(0.5)
            if await cdp.js("!!window.gkide && /^running/.test((document.getElementById('status') || {}).textContent || '')"):
                ok = True
                break
        if not ok:
            problems.append('/ide/: the IDE did not start (its status never said running): %s'
                            % await cdp.js("document.getElementById('status') && document.getElementById('status').textContent"))
            for ev in cdp.events:
                if ev['method'] in ('Log.entryAdded', 'Runtime.consoleAPICalled', 'Runtime.exceptionThrown'):
                    problems.append('/ide/: ' + json.dumps(ev['params'])[:300])
        else:
            await cdp.js("gkide.openFile('apps/hello/main.js', 1)")
            await asyncio.sleep(1)
            await cdp.js("gkide.run('hello')")
            await asyncio.sleep(3)
            print('ok   /ide/ (started, ran hello)')
            if args.ide_shot:
                shot = await cdp.call('Page.captureScreenshot', format='png')
                path = os.path.join(SITE, 'img', 'ide.png')
                with open(path, 'wb') as f:
                    f.write(base64.b64decode(shot['data']))
                try:
                    from PIL import Image
                    im = Image.open(path).convert('RGB')
                    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)
                except ImportError:
                    pass
                print('wrote', path)
        for ev in cdp.events:
            if ev['method'] == 'Runtime.exceptionThrown':
                problems.append('/ide/: exception: %s' % ev['params']['exceptionDetails'].get('text'))

        # A "Try it" link of the Portuguese home page, on a phone: the IDE
        # boots straight into the app, in Portuguese
        cdp.events.clear()
        await cdp.call('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=2, mobile=True)
        link = '/ide/web/index.html?run=totp&lang=pt-BR'
        await cdp.call('Page.navigate', url=base + link)
        ok = False
        for _ in range(60):
            await asyncio.sleep(0.5)
            if await cdp.js("/running totp/.test((document.getElementById('status') || {}).textContent || '')"):
                ok = True
                break
        if not ok:
            problems.append('%s: did not boot into totp (status: %s)' % (link, await cdp.js(
                "(document.getElementById('status') || {}).textContent")))
        else:
            await asyncio.sleep(2)
            shot = await cdp.call('Page.captureScreenshot', format='png')
            path = os.path.join(os.path.dirname(SITE), 'screenshots', 'ide-try-totp-pt-BR-phone.png')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(base64.b64decode(shot['data']))
            print('ok   %s (phone; screenshot %s)' % (link, path))
        for ev in cdp.events:
            if ev['method'] == 'Runtime.exceptionThrown':
                problems.append('%s: exception: %s' % (link, ev['params']['exceptionDetails'].get('text')))
        task.cancel()
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8047')
    ap.add_argument('--ide-shot', action='store_true')
    ap.add_argument('--chrome', default=shutil.which('google-chrome') or shutil.which('chromium'))
    args = ap.parse_args()
    profile = tempfile.mkdtemp(prefix='gksite-chrome-')
    chrome = subprocess.Popen([args.chrome, '--headless=new', '--no-sandbox', '--hide-scrollbars',
                               '--force-dark-mode', '--remote-debugging-port=%d' % DEBUG_PORT,
                               '--user-data-dir=' + profile, 'about:blank'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen('http://127.0.0.1:%d/json' % DEBUG_PORT)
                break
            except OSError:
                time.sleep(0.2)
        problems = asyncio.run(run(args))
    finally:
        chrome.terminate()
        chrome.wait()
        shutil.rmtree(profile, ignore_errors=True)
    for p in problems:
        print('problem:', p)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
