#!/usr/bin/env python3
"""
Builds gapkeep.org into site/: the pages in English and in Brazilian
Portuguese, the documentation mirrored from GapKeep, the download page from
data/downloads.json, and the logo concepts page.

    python3 tools/build.py

Sources:
    content/<lang>/*.html    the pages' main content, one file per page and
                             language ({{...}} markers below)
    docs-src/                GapKeep's Markdown, from tools/import_docs.py
    data/downloads.json      the SD card images (empty fields: coming soon)
    site/css, site/js, site/fonts, site/img    static, edited by hand
    site/ide/                the browser IDE, from tools/import_ide.sh

Everything else in site/ (the .html files, sitemap.xml, sw.js's list) is
written by this script: edit the sources, not the output.

Markers in content files:
    {{shot:NAME}}            a screenshot in the page's language
    {{lang}} {{root}}        "en" or "pt-BR"; "/" or "/pt-br/"
    {{gk-commit}}            the GapKeep commit the docs came from (short)
    {{downloads}}            the download cards
    {{pizero}}               the Pi Zero drawing (an <svg>)
    {{logo}}                 the logo mark in use (an <svg>)
First line of a content file: <!--meta {"title": ..., "description": ...} -->

Needs Python 3 and markdown-it-py (Debian: python3-markdown-it).
"""

import hashlib
import html
import json
import os
import re
import sys

from markdown_it import MarkdownIt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, 'site')
CONTENT = os.path.join(ROOT, 'content')
DOCSRC = os.path.join(ROOT, 'docs-src')
GITHUB = 'https://github.com/marcocarnut/GapKeep'
DOMAIN = 'https://gapkeep.org'
LOGO = 'finder'                       # tools/make_logos.py's USE

LANGS = {
    # code: (html lang, url prefix, content folder)
    'en': ('en', '/', 'en'),
    'pt-BR': ('pt-BR', '/pt-br/', 'pt-br'),
}

CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; connect-src 'self'; manifest-src 'self'; worker-src 'self'; "
       "base-uri 'none'; form-action 'none'")

T = {
    'en': {
        'skip': 'Skip to the content',
        'nav': [('#why', 'Why'), ('#verify', 'See it'), ('#apps', 'Apps'), ('#hardware', 'Hardware'),
                ('#developers', 'Developers'), ('docs/', 'Docs'), ('download.html', 'Download')],
        'menu': 'Menu',
        'langlabel': 'Language',
        'home': 'GapKeep home',
        'footer_tag': 'A tiny bare-metal OS for air-gapped apps.',
        'footer_privacy': 'No trackers, no analytics, no cookies, no third-party requests: this site '
                          'loads nothing from anywhere else, in the spirit of GapKeep.',
        'footer_licence': 'GapKeep is free software, under the GNU GPL version 3 or later.',
        'footer_docs': 'Documentation mirrored from GapKeep commit',
        'footer_links': [('docs/', 'Documentation'), ('download.html', 'Download'), ('ide/', 'Browser IDE'),
                         (GITHUB, 'Source on GitHub'), ('docs/security.html', 'Security'),
                         ('docs/contributing.html', 'Contributing')],
        'docs_title': 'Documentation',
        'docs_intro': ('GapKeep\'s documentation, as it is in the repository. These pages are made '
                       'from the Markdown files of commit {commit} ({date}); the latest is always '
                       '<a href="{gh}">on GitHub</a>.'),
        'docs_note': '',
        'docs_source': 'Source: <a href="{url}"><code>{path}</code></a> at <a href="{commit_url}">{commit}</a>',
        'docs_contents': 'All documents',
        'groups': [('start', 'Start here'), ('guides', 'Guides'), ('reference', 'Reference and design'),
                   ('apps', 'Apps'), ('project', 'The project'), ('more', 'More')],
        'notfound_title': 'Page not found',
        'notfound': 'There is nothing at this address. Perhaps it crossed the air gap?',
        'notfound_home': 'Back to the home page',
        'redirect_note': '',
    },
    'pt-BR': {
        'skip': 'Pular para o conteúdo',
        'nav': [('#why', 'Por quê'), ('#verify', 'Veja'), ('#apps', 'Aplicativos'), ('#hardware', 'Hardware'),
                ('#developers', 'Desenvolvedores'), ('docs/', 'Documentação'), ('download.html', 'Baixar')],
        'menu': 'Menu',
        'langlabel': 'Idioma',
        'home': 'Página inicial do GapKeep',
        'footer_tag': 'Um sistema operacional mínimo, bare-metal, para aplicativos air-gapped.',
        'footer_privacy': 'Sem rastreadores, sem analytics, sem cookies, sem requisições a terceiros: '
                          'este site não carrega nada de nenhum outro lugar, no espírito do GapKeep.',
        'footer_licence': 'O GapKeep é software livre, sob a GNU GPL versão 3 ou posterior.',
        'footer_docs': 'Documentação espelhada do commit do GapKeep',
        'footer_links': [('docs/', 'Documentação'), ('download.html', 'Baixar'), ('ide/', 'IDE no navegador'),
                         (GITHUB, 'Código no GitHub'), ('docs/security.html', 'Segurança'),
                         ('docs/contributing.html', 'Como contribuir')],
        'docs_title': 'Documentação',
        'docs_intro': ('A documentação do GapKeep, tal como está no repositório. Estas páginas são '
                       'geradas a partir dos arquivos Markdown do commit {commit} ({date}); a versão '
                       'mais recente está sempre <a href="{gh}">no GitHub</a>.'),
        'docs_note': ('Por enquanto, a documentação existe só em inglês. O texto abaixo é o original; '
                      'traduções são bem-vindas.'),
        'docs_source': 'Fonte: <a href="{url}"><code>{path}</code></a> no commit <a href="{commit_url}">{commit}</a>',
        'docs_contents': 'Todos os documentos',
        'groups': [('start', 'Comece aqui'), ('guides', 'Guias'), ('reference', 'Referência e projeto'),
                   ('apps', 'Aplicativos'), ('project', 'O projeto'), ('more', 'Mais')],
        'notfound_title': 'Página não encontrada',
        'notfound': 'Não há nada neste endereço. Talvez tenha atravessado o air gap?',
        'notfound_home': 'Voltar à página inicial',
        'redirect_note': '',
    },
}

# The mirrored documents: repository path -> (page under docs/, group).
# Order is the order of the docs index.
DOCMAP = [
    ('README.md', 'readme.html', 'start'),
    ('docs/APPS.md', 'apps.html', 'start'),
    ('docs/AGENTS.md', 'agents.html', 'start'),
    ('docs/SIMULATOR.md', 'simulator.html', 'guides'),
    ('docs/IDE.md', 'ide.html', 'guides'),
    ('docs/CAMERA.md', 'camera.html', 'guides'),
    ('docs/CLOCK.md', 'clock.html', 'guides'),
    ('docs/RIG.md', 'rig.html', 'guides'),
    ('docs/API.md', 'api.html', 'reference'),
    ('docs/ARCHITECTURE.md', 'architecture.html', 'reference'),
    ('docs/DESIGN.md', 'design.html', 'reference'),
    ('docs/EXPERIMENTAL.md', 'experimental.html', 'reference'),
    ('apps/signer/README.md', 'apps/signer.html', 'apps'),
    ('apps/dice39/README.md', 'apps/dice39.html', 'apps'),
    ('apps/codex32/README.md', 'apps/codex32.html', 'apps'),
    ('apps/totp/README.md', 'apps/totp.html', 'apps'),
    ('SECURITY.md', 'security.html', 'project'),
    ('CONTRIBUTING.md', 'contributing.html', 'project'),
    ('AGENTS.md', 'agents-gapkeep.html', 'project'),
    ('docs/camera/SPEC.md', 'camera/spec.html', 'more'),
    ('docs/camera/IMPLEMENTATION.md', 'camera/implementation.html', 'more'),
    ('docs/camera/PROVENANCE.md', 'camera/provenance.html', 'more'),
    ('docs/i18n/pt-BR.md', 'i18n/pt-br.html', 'more'),
    ('lib/js/README.md', 'lib-js.html', 'more'),
]

warnings = []
written = []


def esc(s):
    return html.escape(s, quote=True)


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(rel, text):
    path = os.path.join(SITE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    written.append(rel)


def asset(rel):
    """A static file's URL with a content hash, so caches never serve a stale one."""
    with open(os.path.join(SITE, rel.lstrip('/')), 'rb') as f:
        h = hashlib.sha256(f.read()).hexdigest()[:10]
    return '%s?v=%s' % (rel, h)


def other_lang(lang):
    return 'pt-BR' if lang == 'en' else 'en'


def url_in(lang, path):
    """The URL of a page (path relative to a language's root) in that language."""
    return LANGS[lang][1] + path


# ---- page layout ---------------------------------------------------------

def svg_inline(name):
    s = read(os.path.join(SITE, 'img', 'logo', name))
    return s.strip()


def layout(lang, path, title, description, main, body_class='', head_extra='', lang_main=None):
    """A whole page. path: relative to the language root ('' for the home page)."""
    t = T[lang]
    hl, prefix, _ = LANGS[lang]
    root = prefix
    is_home = path in ('', 'index.html')

    def nav_href(h):
        if h.startswith('#'):
            return (root + h) if not is_home else h
        if h.startswith('http'):
            return h
        if h == 'ide/':
            return '/ide/'
        return root + h

    nav = '\n'.join('<li><a href="%s">%s</a></li>' % (esc(nav_href(h)), esc(label)) for h, label in t['nav'])
    langs = []
    for code, (chl, cprefix, _) in LANGS.items():
        label, name = ('EN', 'English') if code == 'en' else ('PT', 'Português (Brasil)')
        cur = ' aria-current="true"' if code == lang else ''
        langs.append('<a href="%s" hreflang="%s" lang="%s" data-lang="%s" title="%s"%s>'
                     '<span aria-hidden="true">%s</span><span class="sr">%s</span></a>'
                     % (esc(url_in(code, path)), chl, chl, code, esc(name), cur, label, esc(name)))
    alternates = '\n'.join('<link rel="alternate" hreflang="%s" href="%s%s">' % (LANGS[c][0], DOMAIN, url_in(c, path))
                           for c in LANGS)
    alternates += '\n<link rel="alternate" hreflang="x-default" href="%s%s">' % (DOMAIN, url_in('en', path))
    flinks = ' · '.join('<a href="%s">%s</a>' % (esc(nav_href(h)), esc(label)) for h, label in t['footer_links'])
    src = read(os.path.join(DOCSRC, 'SOURCE')).split()
    commit = src[1]
    mark = svg_inline('%s-mark.svg' % LOGO).replace('<svg ', '<svg class="mark" aria-hidden="true" focusable="false" ', 1)
    fullt = title if title.startswith('GapKeep') else '%s · GapKeep' % title
    return f'''<!DOCTYPE html>
<html lang="{hl}" data-lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="same-origin">
<title>{esc(fullt)}</title>
<meta name="description" content="{esc(description)}">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#1d1c23">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/site.webmanifest">
<link rel="canonical" href="{DOMAIN}{url_in(lang, path)}">
{alternates}
<meta property="og:title" content="{esc(fullt)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{DOMAIN}/img/og.png">
<meta property="og:url" content="{DOMAIN}{url_in(lang, path)}">
<script src="{asset('/js/lang.js')}"></script>
<link rel="preload" href="/fonts/montserrat-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{asset('/css/site.css')}">
{head_extra}
<script src="{asset('/js/site.js')}" defer></script>
</head>
<body class="{body_class}">
<a class="skip" href="#main">{esc(t['skip'])}</a>
<header class="top" id="top">
  <div class="top-in">
    <a class="brand" href="{root}" aria-label="{esc(t['home'])}">{mark}<span class="word">Gap<b>Keep</b></span></a>
    <nav class="nav" aria-label="Main">
      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav-list"><span class="bars" aria-hidden="true"></span><span class="sr">{esc(t['menu'])}</span></button>
      <ul id="nav-list">
{nav}
      </ul>
    </nav>
    <div class="langs" role="group" aria-label="{esc(t['langlabel'])}">{''.join(langs)}</div>
  </div>
</header>
<main id="main"{(' lang="%s"' % lang_main) if lang_main else ''}>
{main}
</main>
<footer class="foot">
  <div class="foot-in">
    <p class="foot-brand"><a href="{root}">{mark}<span class="word">Gap<b>Keep</b></span></a><span>{esc(t['footer_tag'])}</span></p>
    <p class="foot-links">{flinks}</p>
    <p class="foot-privacy">{esc(t['footer_privacy'])}</p>
    <p class="foot-small">{esc(t['footer_licence'])} {esc(t['footer_docs'])} <a href="{GITHUB}/tree/{commit}"><code>{commit[:12]}</code></a>.</p>
  </div>
</footer>
</body>
</html>
'''


# ---- content pages -------------------------------------------------------

def downloads_html(lang):
    data = json.loads(read(os.path.join(ROOT, 'data', 'downloads.json')))
    t = data['strings'][lang]
    cards = []
    for img in data['images']:
        ready = all(img.get(k) for k in ('file', 'sha256', 'url'))
        rows = []
        for key in ('file', 'size', 'sha256', 'version', 'commit', 'date'):
            val = img.get(key)
            label = t['fields'][key]
            if not val:
                shown = '<span class="soon">%s</span>' % esc(t['soon'])
            elif key == 'size':
                shown = '%.1f MB (%s bytes)' % (val / 1e6, format(val, ',').replace(',', ' '))
            elif key == 'commit':
                shown = '<a href="%s/commit/%s"><code>%s</code></a>' % (GITHUB, esc(val), esc(val[:12]))
            elif key == 'sha256':
                shown = '<code class="hash">%s</code>' % esc(val)
            else:
                shown = '<code>%s</code>' % esc(str(val)) if key == 'file' else esc(str(val))
            rows.append('<dt>%s</dt><dd>%s</dd>' % (esc(label), shown))
        if ready:
            button = '<a class="btn btn-primary" href="%s">%s</a>' % (esc(img['url']), esc(t['get']))
        else:
            button = '<span class="btn btn-disabled" aria-disabled="true">%s</span>' % esc(t['soon_button'])
        cards.append('''<article class="dl-card%s">
  <p class="dl-lang">%s</p>
  <h3>%s</h3>
  <p>%s</p>
  <dl>%s</dl>
  %s
</article>''' % ('' if ready else ' is-soon', esc(img['code']), esc(img['name'][lang]), esc(img['about'][lang]),
                 ''.join(rows), button))
    releases = data.get('releases_url') or GITHUB + '/releases'
    return '<div class="dl-grid">%s</div>\n<p class="dl-all"><a href="%s">%s</a></p>' % (
        '\n'.join(cards), esc(releases), esc(t['all_releases']))


def fill(text, lang, extra=None):
    hl, prefix, _ = LANGS[lang]
    src = read(os.path.join(DOCSRC, 'SOURCE')).split()

    def shot(m):
        name = m.group(1)
        rel = 'img/shots/%s/%s.png' % (lang, name)
        if not os.path.exists(os.path.join(SITE, rel)):
            warnings.append('no screenshot %s' % rel)
        return '/' + rel
    text = re.sub(r'\{\{shot:([a-z0-9-]+)\}\}', shot, text)
    text = text.replace('{{lang}}', lang).replace('{{root}}', prefix)
    text = text.replace('{{gk-commit}}', src[1][:12])
    if '{{downloads}}' in text:
        text = text.replace('{{downloads}}', downloads_html(lang))
    if '{{pizero}}' in text:
        text = text.replace('{{pizero}}', read(os.path.join(CONTENT, 'pizero.svg')).strip())
    if '{{logo}}' in text:
        text = text.replace('{{logo}}', svg_inline('%s-mark.svg' % LOGO).replace(
            '<svg ', '<svg aria-hidden="true" focusable="false" ', 1))
    for k, v in (extra or {}).items():
        text = text.replace('{{%s}}' % k, v)
    left = re.findall(r'\{\{[^}]*\}\}', text)
    if left:
        warnings.append('unknown markers: %s' % ', '.join(sorted(set(left))))
    return text


def content_page(lang, name, out, body_class=''):
    folder = LANGS[lang][2]
    text = read(os.path.join(CONTENT, folder, name))
    m = re.match(r'<!--meta (\{.*?\}) -->\n', text, re.S)
    meta = json.loads(m.group(1))
    text = fill(text[m.end():], lang)
    page = layout(lang, out, meta['title'], meta['description'], text, body_class)
    write(LANGS[lang][1].lstrip('/') + (out or 'index.html'), page)


# ---- documentation -------------------------------------------------------

def slugify(text, seen):
    # as GitHub makes heading anchors: lower case, punctuation dropped,
    # spaces to hyphens; repeats get -1, -2...
    s = text.strip().lower()
    s = re.sub(r'[^\w\- ]', '', s, flags=re.U)
    s = s.replace(' ', '-')
    base, n = s, 0
    while s in seen:
        n += 1
        s = '%s-%d' % (base, n)
    seen.add(s)
    return s


def build_docs():
    src = read(os.path.join(DOCSRC, 'SOURCE')).split('\n')
    commit = src[0].split()[1]
    date = src[1].split()[1][:10]
    files = set(read(os.path.join(DOCSRC, 'FILES')).split('\n')) - {''}
    dirs = set()
    for f in files:
        parts = f.split('/')
        for i in range(1, len(parts)):
            dirs.add('/'.join(parts[:i]))
    pages = {repo: page for repo, page, _ in DOCMAP}
    for repo in pages:
        if not os.path.exists(os.path.join(DOCSRC, repo)):
            warnings.append('docs: %s is in DOCMAP but not in docs-src (import again?)' % repo)
    for f in files:
        if f.endswith('.md') and os.path.exists(os.path.join(DOCSRC, f)) and f not in pages:
            warnings.append('docs: %s was imported but has no page in DOCMAP' % f)

    md = MarkdownIt('commonmark', {'html': False, 'linkify': False, 'typographer': False})
    md.enable('table').enable('strikethrough')

    rendered = {}
    for repo, page, group in DOCMAP:
        path = os.path.join(DOCSRC, repo)
        if not os.path.exists(path):
            continue
        text = read(path)
        tokens = md.parse(text)
        seen = set()
        title = None
        here = os.path.dirname(repo)
        for i, tok in enumerate(tokens):
            if tok.type == 'heading_open':
                inline = tokens[i + 1]
                plain = ''.join(c.content for c in inline.children if c.type in ('text', 'code_inline'))
                tok.attrSet('id', slugify(plain, seen))
                if tok.tag == 'h1' and title is None:
                    title = plain
            if tok.type == 'inline' and tok.children:
                for c in tok.children:
                    if c.type == 'link_open':
                        c.attrSet('href', rewrite_link(c.attrGet('href'), here, repo, page, pages, files, dirs, commit))
                        href = c.attrGet('href')
                        if href.startswith('http') and not href.startswith(DOMAIN):
                            c.attrSet('rel', 'noopener')
        body = md.renderer.render(tokens, md.options, {})
        # heading anchors, for linking to a section
        body = re.sub(r'<(h[2-4]) id="([^"]+)">(.*?)</\1>',
                      lambda m: '<%s id="%s"><a class="anchor" href="#%s" aria-hidden="true" tabindex="-1">#</a>%s</%s>'
                      % (m.group(1), m.group(2), m.group(2), m.group(3), m.group(1)), body)
        body = body.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
        rendered[repo] = (page, group, title or repo, body)

    for lang in LANGS:
        t = T[lang]
        prefix = LANGS[lang][1]
        # the sidebar
        side = []
        for gkey, glabel in t['groups']:
            items = [(r, p, ti) for r, (p, g, ti, _) in rendered.items() if g == gkey]
            if not items:
                continue
            side.append('<h2>%s</h2><ul>%s</ul>' % (esc(glabel), ''.join(
                '<li><a href="%sdocs/%s" data-page="%s">%s</a></li>' % (prefix, p, p, esc(ti)) for r, p, ti in items)))
        sidebar = '\n'.join(side)
        note = ('<p class="doc-note" lang="pt-BR">%s</p>' % esc(t['docs_note'])) if t['docs_note'] else ''
        # the index
        intro = t['docs_intro'].format(commit='<a href="%s/tree/%s"><code>%s</code></a>' % (GITHUB, commit, commit[:12]),
                                       date=date, gh=GITHUB)
        cards = []
        for gkey, glabel in t['groups']:
            items = [(p, ti, r) for r, (p, g, ti, _) in rendered.items() if g == gkey]
            if not items:
                continue
            cards.append('<section class="doc-group"><h2>%s</h2><ul>%s</ul></section>' % (esc(glabel), ''.join(
                '<li><a href="%sdocs/%s"><span lang="en">%s</span><code>%s</code></a></li>'
                % (prefix, p, esc(ti), esc(r)) for p, ti, r in items)))
        main = '''<div class="wrap docs-index">
<p class="eyebrow">GapKeep</p>
<h1>%s</h1>
<p class="lede">%s</p>
%s
<div class="doc-groups">%s</div>
</div>''' % (esc(t['docs_title']), intro, note, '\n'.join(cards))
        write(prefix.lstrip('/') + 'docs/index.html',
              layout(lang, 'docs/', t['docs_title'], t['docs_title'] + ': GapKeep', main, 'page-docs'))
        for repo, (page, group, title, body) in rendered.items():
            srcline = t['docs_source'].format(url='%s/blob/main/%s' % (GITHUB, repo), path=esc(repo),
                                              commit_url='%s/blob/%s/%s' % (GITHUB, commit, repo), commit=commit[:12])
            depth_side = sidebar.replace('data-page="%s"' % page, 'data-page="%s" aria-current="page"' % page)
            main = '''<div class="wrap docs-layout">
<aside class="doc-side" aria-label="%s">
<details class="doc-toc" open><summary>%s</summary>
<p><a href="%sdocs/">%s</a></p>
%s
</details>
</aside>
<article class="doc" lang="en">
%s
<div class="doc-body">
%s
</div>
<p class="doc-src">%s</p>
</article>
</div>''' % (esc(t['docs_contents']), esc(t['docs_contents']), prefix, esc(t['docs_title']),
             depth_side, note, body, srcline)
            write(prefix.lstrip('/') + 'docs/' + page,
                  layout(lang, 'docs/' + page, title, '%s: GapKeep documentation' % title, main, 'page-doc'))


def rewrite_link(href, here, repo, page, pages, files, dirs, commit):
    if not href or re.match(r'^[a-z][a-z0-9+.-]*:', href, re.I) or href.startswith('#') or href.startswith('//'):
        return href
    target, _, frag = href.partition('#')
    norm = os.path.normpath(os.path.join(here, target)).replace(os.sep, '/')
    if norm.startswith('..'):
        warnings.append('docs: %s links outside the repository: %s' % (repo, href))
        return GITHUB
    if norm in pages:
        # relative to this page's folder, so it works in both languages
        rel = os.path.relpath(pages[norm], os.path.dirname(page) or '.').replace(os.sep, '/')
        return rel + ('#' + frag if frag else '')
    if norm in files:
        return '%s/blob/main/%s%s' % (GITHUB, norm, '#' + frag if frag else '')
    if norm in dirs or norm == '.':
        return '%s/tree/main/%s' % (GITHUB, '' if norm == '.' else norm)
    warnings.append('docs: %s links to %s, which is not in GapKeep %s' % (repo, href, commit[:12]))
    return '%s/blob/main/%s' % (GITHUB, norm)


# ---- the rest ------------------------------------------------------------

def logo_concepts():
    import importlib.util
    spec = importlib.util.spec_from_file_location('make_logos', os.path.join(HERE, 'make_logos.py'))
    ml = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ml)
    blocks = []
    for key, (title, _, _, why) in ml.CONCEPTS.items():
        def img(name, cls, size=None):
            return '<img src="/img/logo/%s" alt="" class="%s"%s>' % (name, cls, (' width="%d" height="%d"' % (size, size)) if size else '')
        mono = svg_inline('%s-lockup-mono.svg' % key)
        mono_mark = svg_inline('%s-mono.svg' % key)
        used = ' <span class="tag">in use on the site</span>' if key == LOGO else ''
        blocks.append(f'''<section class="concept" id="{key}">
<h2>{esc(title)}{used}</h2>
<p>{esc(why)}</p>
<div class="concept-row">
  <div class="swatch dark">{img(key + '-lockup.svg', 'lockup')}</div>
  <div class="swatch light">{img(key + '-lockup-light.svg', 'lockup')}</div>
</div>
<div class="concept-row small">
  <div class="swatch dark sizes">{img(key + '-mark.svg', 'm64', 64)}{img(key + '-mark.svg', 'm32', 32)}{img(key + '-mark.svg', 'm16', 16)}<span>64 · 32 · 16 px</span></div>
  <div class="swatch teal mono-white">{mono}</div>
  <div class="swatch light mono-black">{mono}</div>
  <div class="swatch amber mono-black">{mono_mark}</div>
</div>
<p class="files">Files: <code>img/logo/{key}-mark.svg</code>, <code>{key}-mono.svg</code>, <code>{key}-lockup.svg</code>, <code>{key}-lockup-light.svg</code>, <code>{key}-lockup-mono.svg</code></p>
</section>''')
    main = '''<div class="wrap logo-page">
<p class="eyebrow">Not linked from the site</p>
<h1>Logo concepts</h1>
<p class="lede">Four directions for GapKeep's logo, each a mark and a wordmark (the letters are paths:
the files need no font). All work in one colour and at favicon size. Colours are GapKeep's own:
teal <code>#00968c</code>, amber <code>#ffc300</code>, on <code>#1d1c23</code>.
They are made by <code>tools/make_logos.py</code>; the one in use is its <code>USE</code>.</p>
%s
</div>''' % '\n'.join(blocks)
    page = layout('en', 'logo-concepts.html', 'Logo concepts', 'GapKeep logo concepts', main, 'page-logos',
                  head_extra='<meta name="robots" content="noindex">')
    # only in English, and only at the root: its PT link goes to the home page
    page = re.sub(r'<link rel="alternate"[^>]*>\n', '', page)
    write('logo-concepts.html', page.replace('/pt-br/logo-concepts.html', '/pt-br/'))


def not_found():
    for lang in LANGS:
        t = T[lang]
        prefix = LANGS[lang][1]
        main = '''<div class="wrap notfound">
<p class="eyebrow">404</p>
<h1>%s</h1>
<p class="lede">%s</p>
<p><a class="btn btn-primary" href="%s">%s</a></p>
</div>''' % (esc(t['notfound_title']), esc(t['notfound']), prefix, esc(t['notfound_home']))
        write(prefix.lstrip('/') + '404.html', layout(lang, '404.html', t['notfound_title'], t['notfound_title'],
                                                      main, 'page-404', head_extra='<meta name="robots" content="noindex">'))


def sitemap():
    urls = []
    for rel in sorted(written):
        if rel.endswith('404.html') or rel == 'logo-concepts.html':
            continue
        u = '/' + rel
        if u.endswith('index.html'):
            u = u[:-len('index.html')]
        urls.append('<url><loc>%s%s</loc></url>' % (DOMAIN, u))
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % '\n'.join(urls))


def service_worker():
    # The pages and the assets they need, cached at install so the site
    # works offline; everything else (screenshots, docs, the IDE) is cached
    # as it is visited. The version changes whenever a listed file does.
    core = ['/', '/pt-br/', '/download.html', '/pt-br/download.html', '/docs/', '/pt-br/docs/',
            '/404.html', '/pt-br/404.html', '/favicon.svg',
            asset('/css/site.css'), asset('/js/site.js'), asset('/js/lang.js'),
            '/fonts/montserrat-var.woff2', '/fonts/jetbrainsmono-regular.woff2',
            '/img/shots/en/launcher.png', '/img/shots/pt-BR/launcher.png']
    h = hashlib.sha256()
    for rel in written + ['css/site.css', 'js/site.js', 'js/lang.js']:
        with open(os.path.join(SITE, rel), 'rb') as f:
            h.update(rel.encode() + f.read())
    tpl = read(os.path.join(CONTENT, 'sw.js'))
    tpl = tpl.replace('__VERSION__', h.hexdigest()[:12]).replace('__CORE__', json.dumps(core, indent=1))
    with open(os.path.join(SITE, 'sw.js'), 'w') as f:
        f.write(tpl)


def main():
    for lang in LANGS:
        content_page(lang, 'index.html', '', 'page-home')
        content_page(lang, 'download.html', 'download.html', 'page-download')
    build_docs()
    logo_concepts()
    not_found()
    sitemap()
    service_worker()
    for w in warnings:
        print('warning:', w, file=sys.stderr)
    print('%d pages written' % len(written))
    return 1 if '--strict' in sys.argv and warnings else 0


if __name__ == '__main__':
    sys.exit(main())
