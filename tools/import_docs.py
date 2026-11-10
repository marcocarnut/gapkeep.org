#!/usr/bin/env python3
"""
Copies GapKeep's documentation (its Markdown files) from a GapKeep
checkout into docs-src/, for tools/build.py to turn into the site's
documentation section. Never edit docs-src/ by hand: change the docs in
GapKeep, then import them again.

    python3 tools/import_docs.py ../GapKeep

What is mirrored is in DOCS below: README, SECURITY, CONTRIBUTING, AGENTS,
every docs/**/*.md and each app's README. Only files committed in the
checkout are copied, as they are at its HEAD (git show), so the record in
docs-src/SOURCE (the commit) says exactly what the pages hold.
docs-src/FILES lists every file of that commit, so the build can tell a
link to a file from a link to a folder, and a broken link from both.
"""

import fnmatch
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(os.path.dirname(HERE), 'docs-src')
DOCS = ['README.md', 'SECURITY.md', 'CONTRIBUTING.md', 'AGENTS.md', 'docs/*.md', 'docs/*/*.md',
        'apps/*/README.md', 'lib/js/README.md']


def git(gk, *args):
    return subprocess.run(['git', '-C', gk] + list(args), check=True, capture_output=True).stdout


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    gk = os.path.abspath(sys.argv[1])
    commit = git(gk, 'rev-parse', 'HEAD').decode().strip()
    files = git(gk, 'ls-tree', '-r', '--name-only', 'HEAD').decode().split('\n')
    files = [f for f in files if f]
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    os.makedirs(DEST)
    n = 0
    for f in files:
        if any(fnmatch.fnmatchcase(f, p) and f.count('/') == p.count('/') for p in DOCS):
            os.makedirs(os.path.join(DEST, os.path.dirname(f)), exist_ok=True)
            with open(os.path.join(DEST, f), 'wb') as out:
                out.write(git(gk, 'show', '%s:%s' % (commit, f)))
            n += 1
    with open(os.path.join(DEST, 'FILES'), 'w') as out:
        out.write('\n'.join(files) + '\n')
    date = git(gk, 'show', '-s', '--format=%cI', commit).decode().strip()
    with open(os.path.join(DEST, 'SOURCE'), 'w') as out:
        out.write('commit %s\ndate %s\n' % (commit, date))
    print('%d documents from GapKeep %s (%s)' % (n, commit[:12], date))


if __name__ == '__main__':
    main()
