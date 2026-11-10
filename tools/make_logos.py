#!/usr/bin/env python3
"""
Makes the logo concepts as SVG: four marks, each with a wordmark whose
letters are paths (so the files need no font), in colour and in one colour.

    python3 tools/make_logos.py Montserrat.zip JetBrainsMono-2.304.zip

Writes site/img/logo/<concept>-mark.svg, <concept>-lockup.svg and
<concept>-mono.svg, and site/favicon.svg (from the concept in USE).
The marks are drawn on a 32-unit grid so they stay sharp at 16 and 32 px.
Needs fontTools. Its output is committed; run it only to change a logo.
"""

import io
import math
import os
import sys
import zipfile

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), 'site')
OUT = os.path.join(SITE, 'img', 'logo')

TEAL = '#00968c'
AMBER = '#ffc300'
USE = 'finder'          # the concept used across the site, for now


def arc_band(cx, cy, r_out, r_in, a0, a1):
    """A ring segment from angle a0 to a1 (degrees, clockwise from 3 o'clock, y down)."""
    def pt(r, a):
        return cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    x0, y0 = pt(r_out, a0)
    x1, y1 = pt(r_out, a1)
    x2, y2 = pt(r_in, a1)
    x3, y3 = pt(r_in, a0)
    return ('M%.2f %.2fA%g %g 0 %d 1 %.2f %.2fL%.2f %.2fA%g %g 0 %d 0 %.2f %.2fZ'
            % (x0, y0, r_out, r_out, large, x1, y1, x2, y2, r_in, r_in, large, x3, y3))


def rrect(x, y, w, h, r):
    return ('M%g %gh%gq%g 0 %g %gv%gq0 %g %g %gh%gq%g 0 %g %gv%gq0 %g %g %gZ'
            % (x + r, y, w - 2 * r, r, r, r, h - 2 * r, r, -r, r, -(w - 2 * r), -r, -r, -r,
               -(h - 2 * r), -r, r, -r))


# Each mark: a list of (path, role); role "a" is the main colour, "b" the accent.
def mark_finder():
    # A QR code's finder pattern: a wall, a gap all around, and what is kept
    # inside. The gap ring is the air gap; the core is the secret.
    return [(rrect(2, 2, 28, 28, 7) + ' ' + rrect(6.5, 6.5, 19, 19, 3.5), 'a', 'evenodd'),
            (rrect(11, 11, 10, 10, 2.5), 'b', None)]


def mark_tower():
    # A keep (a castle's tower) split down the middle by a gap.
    left = ('M5 4h4v4h2.5v-4h3.5v25h-10Z')
    right = ('M17 4h3.5v4h2.5v-4h4v25h-10Z')
    door = 'M12 29v-6a4 4 0 0 1 8 0v6Z'
    return [(left, 'a', None), (right, 'a', None), (door, 'cut', None)]


def mark_shares():
    # A "G" in three pieces, as a key split into shares; one of them stands out.
    w = 5.5
    r_out, r_in = 13, 13 - w
    gap = 9
    segs = [(-12 + gap / 2 + 360 * 0, 100 - gap / 2), (100 + gap / 2, 215 - gap / 2), (215 + gap / 2, 330)]
    paths = [(arc_band(16, 16, r_out, r_in, a0, a1), role, None) for (a0, a1), role in zip(segs, 'aba')]
    # the G's bar: from the right end of the arc, inward
    paths.append(('M17 13.25h12v5.5h-12Z', 'a', None))
    return paths


def mark_pixel():
    # An 80s pixel "G" on a 5x5 grid; the pixel it keeps inside is amber.
    rows = ['.###.',
            '#....',
            '#.#b#',
            '#...#',
            '.###.']
    s, g = 6, 0.7
    a, b = [], []
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c in '#b':
                (a if c == '#' else b).append('M%g %gh%gv%gh-%gZ' % (1 + x * s + g / 2, 1 + y * s + g / 2, s - g, s - g, s - g))
    return [(''.join(a), 'a', None), (''.join(b), 'b', None)]


CONCEPTS = {
    'finder': ('Finder', mark_finder, 'montserrat',
               "A QR code's finder pattern read as a keep: a wall, a gap all around, and the "
               "secret kept in the middle. QR codes are how data crosses GapKeep's air gap."),
    'tower': ('Keep', mark_tower, 'montserrat',
              'A castle keep split by a gap down the middle: the name, literally. A door at the '
              'foot, since things do go in and out: by keyboard, camera and screen.'),
    'shares': ('Shares', mark_shares, 'montserrat',
               'A "G" in three pieces, like a key split into codex32 shares; one piece in amber. '
               'Keys live elsewhere, in pieces, and come together only for the task.'),
    'pixel': ('Pixel', mark_pixel, 'mono',
              'An 80s pixel "G", for the old joke: in the eighties, all computers were '
              'air-gapped. The pixel it keeps inside is amber.'),
}


def glyph_paths(font, text, size, x0, baseline, tracking=0.0):
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    upm = font['head'].unitsPerEm
    scale = size / upm
    x = x0
    out = []
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        tpen = TransformPen(pen, (scale, 0, 0, -scale, x, baseline))
        gs[name].draw(tpen)
        out.append(pen.getCommands())
        x += gs[name].width * scale + tracking
    return ' '.join(out), x


def render_mark(parts, a, b, bg=None):
    s = []
    cut = [p for p, role, _ in parts if role == 'cut']
    if cut:
        s.append('<defs><mask id="m"><rect width="32" height="32" fill="#fff"/>'
                 + ''.join('<path d="%s" fill="#000"/>' % p for p in cut) + '</mask></defs>')
    for p, role, rule in parts:
        if role == 'cut':
            continue
        attrs = ' fill-rule="%s"' % rule if rule else ''
        if cut:
            attrs += ' mask="url(#m)"'
        s.append('<path d="%s" fill="%s"%s/>' % (p, a if role == 'a' else b, attrs))
    return ''.join(s)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    fonts = {}
    for z in sys.argv[1:]:
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():
                if n.endswith('static/Montserrat-Bold.ttf'):
                    fonts['montserrat'] = TTFont(io.BytesIO(zf.read(n)))
                if n.endswith('fonts/ttf/JetBrainsMono-Bold.ttf'):
                    fonts['mono'] = TTFont(io.BytesIO(zf.read(n)))
    os.makedirs(OUT, exist_ok=True)
    for key, (title, fn, fontname, _) in CONCEPTS.items():
        parts = fn()
        # the mark alone, colour on transparent
        mark = render_mark(parts, TEAL, AMBER)
        with open(os.path.join(OUT, key + '-mark.svg'), 'w') as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">%s</svg>\n' % mark)
        with open(os.path.join(OUT, key + '-mono.svg'), 'w') as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">%s</svg>\n'
                    % render_mark(parts, 'currentColor', 'currentColor'))
        # the lockup: mark, then the wordmark (Gap in the text colour, Keep in teal)
        font = fonts[fontname]
        size = 26 if fontname == 'montserrat' else 24
        track = -0.4 if fontname == 'montserrat' else -1.2
        gap_d, x = glyph_paths(font, 'Gap', size, 42, 25, track)
        keep_d, x = glyph_paths(font, 'Keep', size, x, 25, track)
        width = math.ceil(x + 2)
        for variant, fg, kc in (('lockup', '#f4f3f7', TEAL), ('lockup-light', '#1d1c23', '#00756d')):
            with open(os.path.join(OUT, '%s-%s.svg' % (key, variant)), 'w') as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d 32">'
                        '<g>%s</g><path d="%s" fill="%s"/><path d="%s" fill="%s"/></svg>\n'
                        % (width, mark, gap_d, fg, keep_d, kc))
        with open(os.path.join(OUT, key + '-lockup-mono.svg'), 'w') as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d 32" fill="currentColor">'
                    '%s<path d="%s"/><path d="%s"/></svg>\n'
                    % (width, render_mark(parts, 'currentColor', 'currentColor'), gap_d, keep_d))
        print(key, width)
    # the favicon: the chosen mark on the dark background, rounded
    parts = CONCEPTS[USE][1]()
    with open(os.path.join(SITE, 'favicon.svg'), 'w') as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">%s</svg>\n'
                % render_mark(parts, TEAL, AMBER))


if __name__ == '__main__':
    main()
