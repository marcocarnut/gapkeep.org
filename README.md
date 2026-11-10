# gapkeep.org

The website of [GapKeep](https://github.com/marcocarnut/GapKeep), a tiny
bare-metal OS for air-gapped apps: English and Brazilian Portuguese, the
documentation mirrored from the repository, the download page and the
browser IDE. Static files, no framework, nothing loaded from anywhere else.

## Layout

| Path | What | Edited by |
| --- | --- | --- |
| `content/en/`, `content/pt-br/` | The pages' text: `index.html` (home), `download.html` | hand |
| `content/pizero.svg` | The Pi Zero drawing (hero, hardware) | hand |
| `content/sw.js` | The service worker's template (offline) | hand |
| `data/downloads.json` | The SD card images: empty fields show as "coming soon" | hand, at each release |
| `docs-src/` | GapKeep's Markdown, with `SOURCE` (the commit) and `FILES` | `tools/import_docs.py` only |
| `site/` | **The output**, ready for GitHub Pages (`CNAME`, `.nojekyll`) | see below |
| `site/css/`, `site/js/`, `site/img/logo/`, `site/fonts/` | Static assets | hand, or the scripts below |
| `site/img/shots/` | App screenshots, `en/` and `pt-BR/`, with `SOURCE` | `tools/screenshots.py` |
| `site/ide/` | The browser IDE, with `SOURCE` | `tools/import_ide.sh` only |
| `site/**/*.html`, `site/sw.js`, `site/sitemap.xml` | Generated pages | `tools/build.py` only |
| `screenshots/` | Screenshots of the site itself, for review | `tools/screenshot_site.sh` |

## Building

Needs Python 3 and markdown-it-py (Debian: `python3-markdown-it`); no
network, no npm.

```sh
python3 tools/build.py            # content/ + docs-src/ + data/ -> site/
python3 tools/check_links.py      # every internal link and #anchor, both languages
```

`build.py --strict` fails on warnings (a missing screenshot, a document
link that points nowhere in GapKeep).

## Previewing

```sh
python3 -m http.server 8047 --bind 127.0.0.1 --directory site
```

Then <http://127.0.0.1:8047/>. (Not 8039: that is GapKeep's own
`tools/gkide.sh`.) Two more checks, with Google Chrome:

```sh
python3 tools/browser_check.py        # no third-party requests, no CSP or JS errors, the IDE starts
tools/screenshot_site.sh              # phone (390x844) and desktop (1440x900), EN and PT, into screenshots/
FULL=15000 tools/screenshot_site.sh   # ... and whole pages
THEME=light tools/screenshot_site.sh  # the light theme
```

`browser_check.py` needs Python's websockets (`python3-websockets`).

## Refreshing from a GapKeep commit

Each import records the GapKeep commit it came from, so what the site
shows can always be traced. With a GapKeep checkout in `../GapKeep`, at the
commit wanted:

```sh
python3 tools/import_docs.py ../GapKeep     # docs-src/ (committed files at HEAD only)
tools/import_ide.sh ../GapKeep              # site/ide/ (builds the WebAssembly simulator if emsdk is there)
python3 tools/screenshots.py ../GapKeep     # site/img/shots/ (builds the native simulator; ~3 minutes)
python3 tools/browser_check.py --ide-shot   # site/img/ide.png, the IDE on the home page (serve the site first)
python3 tools/build.py && python3 tools/check_links.py
```

- **Docs**: the mirrored files are listed in `tools/import_docs.py`
  (`DOCS`) and given their pages in `tools/build.py` (`DOCMAP`); the build
  warns about a document in one and not the other. Links between mirrored
  documents stay on the site; links to anything else in the repository go
  to GitHub at the recorded commit (`github.com/marcocarnut/GapKeep/blob/<commit>/...`,
  or `tree/` for a folder). The licence links on the home page are pinned
  the same way: GapKeep's own files at that commit, and each submodule's at
  the commit GapKeep pins it to (`docs-src/PINS`; `{{lic:...}}` in the
  content). The docs are English only: the pt-BR pages show the English
  text under a note saying so.
- **IDE**: copied as `tools/gkide.sh` assembles it (`sim/web` to
  `site/ide/web/`, the simulator and the example apps of its `EXAMPLES` to
  `site/ide/build/web/`), unchanged. `/ide/` redirects to `/ide/web/`.
- **Screenshots**: each scenario in `tools/shots/*.txt` is played by
  GapKeep's own `tools/qemu_harness.py` on its simulator, once per
  language (a card whose `gapkeep.txt` sets it). `python3
  tools/screenshots.py ../GapKeep signer` retakes one.

## GapWallet

GapWallet, the watch-only web wallet made for the Signer, will be hosted at
`/gapwallet/`. Until it is imported, `tools/build.py` writes placeholder
pages there and at `/pt-br/gapwallet/`. To import a build:

```sh
tools/import_gapwallet.sh ../gapwallet     # its dist/, or else its gapwallet.html (build it first)
python3 tools/build.py                      # the placeholders give way; /pt-br/gapwallet/ forwards to /gapwallet/
```

The import copies the build unchanged (its own Content-Security-Policy
names the servers it may connect to), with its licences, and records the
commit and each file's SHA-256 in `site/gapwallet/SOURCE`.

## Downloads

When a release is published, fill in `data/downloads.json` (file name,
size in bytes, SHA-256, version, commit, date, and the URL of the file on
the GitHub release), then build. An image without file, SHA-256 and URL
shows as "coming soon".

## Fonts, logo, social card

- `tools/make_fonts.py Montserrat.zip JetBrainsMono-2.304.zip` makes the
  WOFF2 subsets in `site/fonts/` (Latin, Latin-1, box drawing for the
  docs' diagrams), with the fonts' licences (SIL OFL 1.1).
- `tools/make_logos.py` (same zips) makes the logo concepts in
  `site/img/logo/` and `site/favicon.svg`; `USE` names the concept in use,
  and so does `LOGO` in `tools/build.py`. All concepts are on
  `/logo-concepts.html`, which nothing links to.
- `tools/make_og.sh` makes `site/img/og.png` (link previews) from
  `tools/og.html`.

## The hero photo

The home page's opening picture is a placeholder: the launcher screenshot
on a drawn screen with a drawn Pi Zero. To use a photo of a Pi Zero running
GapKeep, put it in `site/img/` and replace the `<figure ...
data-placeholder="hero-photo">` in `content/en/index.html` and
`content/pt-br/index.html` (marked `PHOTO PLACEHOLDER`) with an `<img>` of
it, with its `width`, `height` and an `alt` in each language.

## Publishing (GitHub Pages)

`site/` is the whole site, with `CNAME` (gapkeep.org) and `.nojekyll`.
`.github/workflows/pages.yml` publishes it with GitHub's own Pages actions
when `main` is pushed, once Pages is set to "GitHub Actions" in the
repository's settings, with the custom domain gapkeep.org. Nothing is
built there: commit the output of `tools/build.py`.

## Licences

The site's text and pictures are under CC BY-SA 4.0, its scripts and
styles under GPL-3.0-or-later (`COPYING`); what it includes from
elsewhere keeps its own licence. See `LICENSE.md`.

## Privacy and security

No analytics, no cookies, no third-party requests: fonts, scripts and
images are all served from the site. Each page carries a strict
Content-Security-Policy (`default-src 'none'`, scripts, styles, fonts and
images from the site only, no inline scripts or styles). The language
choice is kept in `localStorage` (`gapkeep-lang`). The service worker
(`site/sw.js`) keeps the site working offline once visited: network first,
the cache when offline. The IDE under `/ide/` is GapKeep's own page, with
its own rules; it saves its files in the browser (IndexedDB).
