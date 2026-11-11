#!/usr/bin/env python3
"""
Takes the site's screenshots with GapKeep's simulator, from a GapKeep
checkout, in English and in Brazilian Portuguese.

    python3 tools/screenshots.py ../GapKeep          # all of them
    python3 tools/screenshots.py ../GapKeep signer   # one scenario

Each scenario in tools/shots/<name>.txt (a line starting "en: " or
"pt-BR: " is played in that language only) is played by GapKeep's own
tools/qemu_harness.py on the native simulator (sim/build/gksim, built
with "make -C sim"), with the apps below on a fresh card. The card's
gapkeep.txt sets the language, as on a real card. The PNGs go to
site/img/shots/<lang>/, and site/img/shots/SOURCE records the GapKeep commit.

Needs what GapKeep's simulator needs (gcc, g++, make) and Pillow.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
OUT = os.path.join(SITE, 'site', 'img', 'shots')
APPS = ['clock', 'codex32', 'dice39', 'gallery', 'qrscan', 'repl', 'settings', 'signer', 'totp', 'sneakernet']
LANGS = ['en', 'pt-BR']


def shrink(src, dst):
    # The simulator writes plain PNGs (900 KB at 640x480). Its screens have
    # few colours: a 256-colour palette, undithered, looks the same at a
    # tenth of the size.
    from PIL import Image
    im = Image.open(src).convert('RGB')
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(dst, optimize=True)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    gk = os.path.abspath(sys.argv[1])
    only = sys.argv[2:]
    subprocess.run(['make', '-C', os.path.join(gk, 'sim'), '-s', '-j%d' % os.cpu_count()], check=True,
                   stdout=subprocess.DEVNULL)
    commit = subprocess.run(['git', '-C', gk, 'rev-parse', 'HEAD'], check=True,
                            capture_output=True, text=True).stdout.strip()
    scenarios = sorted(f[:-4] for f in os.listdir(os.path.join(HERE, 'shots')) if f.endswith('.txt'))
    if only:
        scenarios = [s for s in scenarios if s in only]
    failed = []
    for lang in LANGS:
        dest = os.path.join(OUT, lang)
        os.makedirs(dest, exist_ok=True)
        for name in scenarios:
            with tempfile.TemporaryDirectory(prefix='gkshots-') as tmp:
                card = os.path.join(tmp, 'card')
                os.makedirs(os.path.join(card, 'apps'))
                for app in APPS:
                    shutil.copytree(os.path.join(gk, 'apps', app), os.path.join(card, 'apps', app))
                with open(os.path.join(card, 'gapkeep.txt'), 'w') as f:
                    f.write('language = %s\n' % lang)
                out = os.path.join(tmp, 'out')
                # a line starting "en: " or "pt-BR: " is for that language only
                scenario = os.path.join(tmp, name + '.txt')
                with open(os.path.join(HERE, 'shots', name + '.txt')) as f, open(scenario, 'w') as g:
                    for line in f:
                        tag, sep, rest = line.partition(': ')
                        if sep and tag in LANGS:
                            if tag == lang:
                                g.write(rest)
                        else:
                            g.write(line)
                r = subprocess.run([sys.executable, os.path.join(gk, 'tools', 'qemu_harness.py'),
                                    '--sim', os.path.join(gk, 'sim', 'build', 'gksim'),
                                    '--card', card, '--out', out,
                                    scenario],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    failed.append('%s (%s)' % (name, lang))
                    sys.stderr.write(r.stdout[-2000:] + r.stderr[-2000:])
                for f in sorted(os.listdir(out)) if os.path.isdir(out) else []:
                    if f.endswith('.png'):
                        shrink(os.path.join(out, f), os.path.join(dest, f))
                        print('%s/%s' % (lang, f))
    with open(os.path.join(OUT, 'SOURCE'), 'w') as f:
        f.write('Taken with tools/screenshots.py from GapKeep commit %s\n' % commit)
    if failed:
        sys.exit('failed: ' + ', '.join(failed))


if __name__ == '__main__':
    main()
