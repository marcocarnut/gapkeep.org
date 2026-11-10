#!/usr/bin/env python3
"""
Screenshots one section of a page (an element, by id), whole, at desktop
and phone sizes, in both languages, into screenshots/. For reviewing a
section without the whole page; the site must be served (see README).

    python3 tools/section_shot.py verify [--base http://127.0.0.1:8047]

Writes screenshots/section-<id>-<lang>-<desktop|phone>.png. Dark theme,
animations off. Needs Google Chrome and Python's websockets.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from browser_check import CDP, DEBUG_PORT  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'screenshots')


async def run(args):
    tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % DEBUG_PORT))
    page = [t for t in tabs if t['type'] == 'page'][0]
    async with websockets.connect(page['webSocketDebuggerUrl'], max_size=200_000_000) as ws:
        cdp = CDP(ws)
        task = asyncio.ensure_future(cdp.reader())
        await cdp.call('Page.enable')
        await cdp.call('Page.addScriptToEvaluateOnNewDocument', source=
                       "try { localStorage.setItem('gapkeep-lang', location.pathname.indexOf('/pt-br/') === 0 ? 'pt-BR' : 'en'); } catch (e) {}")
        await cdp.call('Emulation.setEmulatedMedia', features=[
            {'name': 'prefers-color-scheme', 'value': 'dark'}, {'name': 'prefers-reduced-motion', 'value': 'reduce'}])
        for lang, prefix in (('en', '/'), ('pt-BR', '/pt-br/')):
            for kind, w, h, mobile in (('desktop', 1440, 900, False), ('phone', 390, 844, True)):
                await cdp.call('Emulation.setDeviceMetricsOverride', width=w, height=h, deviceScaleFactor=1, mobile=mobile)
                await cdp.call('Page.navigate', url=args.base.rstrip('/') + prefix)
                await asyncio.sleep(1)
                # lazy pictures beyond the window would come out black
                await cdp.js("document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager')")
                await asyncio.sleep(2)
                box = await cdp.js("(() => { const r = document.getElementById(%s).getBoundingClientRect();"
                                   " return [r.left + scrollX, r.top + scrollY, r.width, r.height]; })()" % json.dumps(args.id))
                shot = await cdp.call('Page.captureScreenshot', format='png', captureBeyondViewport=True,
                                      clip={'x': 0, 'y': box[1], 'width': w, 'height': box[3], 'scale': 1})
                path = os.path.join(OUT, 'section-%s-%s-%s.png' % (args.id, lang, kind))
                with open(path, 'wb') as f:
                    f.write(base64.b64decode(shot['data']))
                print(path)
        task.cancel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('id')
    ap.add_argument('--base', default='http://127.0.0.1:8047')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    profile = tempfile.mkdtemp(prefix='gksite-chrome-')
    chrome = subprocess.Popen([shutil.which('google-chrome') or shutil.which('chromium'), '--headless=new',
                               '--no-sandbox', '--hide-scrollbars', '--remote-debugging-port=%d' % DEBUG_PORT,
                               '--user-data-dir=' + profile, 'about:blank'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen('http://127.0.0.1:%d/json' % DEBUG_PORT)
                break
            except OSError:
                time.sleep(0.2)
        asyncio.run(run(args))
    finally:
        chrome.terminate()
        chrome.wait()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    main()
