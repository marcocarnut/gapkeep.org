#!/usr/bin/env python3
"""
Makes the site's web fonts from the fonts' release zips, subset to the
characters English and Portuguese need (Basic Latin, Latin-1, a few
punctuation marks and arrows), as WOFF2, with their licences.

    python3 tools/make_fonts.py Montserrat.zip JetBrainsMono-2.304.zip

Montserrat (variable, one file for every weight) and JetBrains Mono, both
under the SIL Open Font License 1.1. Needs fontTools and brotli. Run it
rarely: its output (site/fonts/) is committed.
"""

import io
import os
import sys
import zipfile

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'site', 'fonts')
UNICODES = (list(range(0x20, 0x7F)) + list(range(0xA0, 0x100)) +
            [0x2010, 0x2011, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026,
             0x2032, 0x2033, 0x2192, 0x2190, 0x2191, 0x2193, 0x2212, 0x00D7, 0x2248, 0x2713, 0x20BF])

WANTED = {
    # zip member (suffix) -> output name
    'Montserrat-VariableFont_wght.ttf': 'montserrat-var.woff2',
    'Montserrat-Italic-VariableFont_wght.ttf': 'montserrat-italic-var.woff2',
    'fonts/ttf/JetBrainsMono-Regular.ttf': 'jetbrainsmono-regular.woff2',
}


def make(data, name):
    font = TTFont(io.BytesIO(data))
    opts = subset.Options()
    opts.flavor = 'woff2'
    opts.layout_features = ['kern', 'liga', 'calt', 'tnum', 'lnum', 'case', 'ccmp', 'locl', 'mark', 'mkmk']
    opts.name_IDs = ['*']
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=UNICODES)
    sub.subset(font)
    path = os.path.join(OUT, name)
    font.flavor = 'woff2'
    font.save(path)
    print('%s: %d bytes' % (path, os.path.getsize(path)))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    os.makedirs(OUT, exist_ok=True)
    for z in sys.argv[1:]:
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            for member, out in WANTED.items():
                for n in names:
                    if n.endswith(member) and '/static/' not in n:
                        make(zf.read(n), out)
                        break
            for n in names:
                if n.endswith('OFL.txt'):
                    lic = 'OFL-montserrat.txt' if 'ontserrat' in os.path.basename(z) else 'OFL-jetbrainsmono.txt'
                    with open(os.path.join(OUT, lic), 'wb') as f:
                        f.write(zf.read(n))
                    break


if __name__ == '__main__':
    main()
