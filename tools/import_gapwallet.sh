#!/bin/bash
#
# Copies a build of GapWallet (the watch-only web wallet made for GapKeep's
# Signer, github.com/marcocarnut/GapWallet) from a GapWallet checkout into
# site/gapwallet/, and records where it came from:
#
#   site/gapwallet/index.html   the wallet (or the build's own files)
#   site/gapwallet/SOURCE       the GapWallet commit and each file's SHA-256
#
#   tools/import_gapwallet.sh ../gapwallet
#
# What is copied is the build, not built here: run GapWallet's own build
# first (its README: "node tools/build.mjs writes gapwallet.html"). If the
# checkout has a dist/ folder (a hostable build, with its own
# Content-Security-Policy), all of dist/ is copied; otherwise the single page
# gapwallet.html becomes index.html. GapWallet's LICENSE goes with it, and its
# vendor/ licences and manifest when there is no dist/ to carry them.
#
# The page is not changed in any way: its Content-Security-Policy, which
# names the servers it may connect to, is its own. After importing, run
# tools/build.py: the placeholder pages give way (the Portuguese address
# then forwards to /gapwallet/, which has its own language selector).
#
set -e
GW=$(cd "${1:?usage: tools/import_gapwallet.sh GAPWALLET_CHECKOUT}" && pwd)
SITE=$(cd "$(dirname "$0")/.." && pwd)/site
DEST=$SITE/gapwallet

[ -f "$GW/tools/build.mjs" ] || { echo "import_gapwallet: $GW is not a GapWallet checkout" >&2; exit 1; }

rm -rf "$DEST"
mkdir -p "$DEST"
if [ -d "$GW/dist" ]; then
	FROM=dist/
	(cd "$GW/dist" && tar -cf - .) | (cd "$DEST" && tar -xf -)
	[ -f "$DEST/index.html" ] || { echo "import_gapwallet: dist/ has no index.html" >&2; exit 1; }
elif [ -f "$GW/gapwallet.html" ]; then
	FROM=gapwallet.html
	cp "$GW/gapwallet.html" "$DEST/index.html"
	mkdir -p "$DEST/licences"
	cp "$GW/vendor/MANIFEST.json" "$DEST/licences/" 2>/dev/null || true
	# each library's licence, as vendor/<library>/<LICENSE...>
	(cd "$GW/vendor" && find . -type f \( -iname '*licen[cs]e*' -o -iname 'copying*' \) | while read -r f; do
		mkdir -p "$DEST/licences/$(dirname "$f")"
		cp "$f" "$DEST/licences/$f"
	done)
else
	echo "import_gapwallet: no dist/ and no gapwallet.html in $GW (build it first)" >&2
	exit 1
fi
[ ! -f "$GW/LICENSE" ] || cp "$GW/LICENSE" "$DEST/LICENSE.txt"

COMMIT=$(git -C "$GW" rev-parse HEAD)
DIRTY=$(git -C "$GW" status --porcelain | head -1)
{
	echo "GapWallet commit: $COMMIT${DIRTY:+ (with uncommitted changes)}"
	echo "Imported: $(date -u +%Y-%m-%dT%H:%M:%SZ) by tools/import_gapwallet.sh, from $FROM"
	echo "Files (SHA-256):"
	(cd "$DEST" && find . -type f ! -name SOURCE | sort | xargs sha256sum)
} > "$DEST/SOURCE"
cat "$DEST/SOURCE" | head -8
du -sh "$DEST"
