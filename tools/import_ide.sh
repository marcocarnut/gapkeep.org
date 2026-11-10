#!/bin/bash
#
# Copies GapKeep's browser IDE (docs/IDE.md in GapKeep) from a GapKeep
# checkout into site/ide/, as tools/gkide.sh assembles it there:
#
#   site/ide/web/          sim/web (the IDE page, its scripts, Monaco)
#   site/ide/build/web/    sim/build/web (the WebAssembly simulator, the
#                          example apps and their index, examples.json)
#   site/ide/SOURCE        the GapKeep commit it came from
#
#   tools/import_ide.sh ../GapKeep
#
# It builds what is missing the way tools/gkide.sh does (the simulator with
# emsdk, if emcc or ~/emsdk is there; Monaco with tools/fetch_monaco.sh),
# and copies the example apps listed in gkide.sh's EXAMPLES. The IDE
# itself is not changed: the page finds the simulator at ../build/web/,
# so the two folders keep their places. site/ide/index.html sends visitors
# to web/index.html.
#
set -e
GK=$(cd "${1:?usage: tools/import_ide.sh GAPKEEP_CHECKOUT}" && pwd)
SITE=$(cd "$(dirname "$0")/.." && pwd)/site
DEST=$SITE/ide

[ -f "$GK/tools/gkide.sh" ] || { echo "import_ide: $GK is not a GapKeep checkout" >&2; exit 1; }

# 1. The simulator, as gkide.sh builds it (make is incremental).
if [ -z "$EMSDK" ] && [ -f "$HOME/emsdk/emsdk_env.sh" ]; then
	. "$HOME/emsdk/emsdk_env.sh" >/dev/null 2>&1
fi
if command -v emcc >/dev/null 2>&1; then
	make -s -C "$GK/sim" web
elif [ ! -f "$GK/sim/build/web/gksim.js" ]; then
	echo "import_ide: no simulator in $GK/sim/build/web and no emsdk to build it" >&2
	exit 1
else
	echo "import_ide: no emsdk: using the simulator already built in $GK/sim/build/web" >&2
fi
# 2. Monaco, pinned and checked by GapKeep's own script.
[ -f "$GK/sim/web/vendor/monaco/vs/loader.js" ] || (cd "$GK" && tools/fetch_monaco.sh)

# 3. Copy. Monaco's tarball stays behind (its unpacked copy is what runs).
rm -rf "$DEST"
mkdir -p "$DEST/web" "$DEST/build/web/examples"
(cd "$GK/sim/web" && tar --exclude='vendor/*.tgz' -cf - .) | (cd "$DEST/web" && tar -xf -)
cp "$GK/sim/build/web/gksim.js" "$GK/sim/build/web/gksim.wasm" "$DEST/build/web/"

# 4. The example apps, from gkide.sh's own list, and their index, as gkide.sh makes it.
EXAMPLES=$(sed -n 's/^EXAMPLES="\(.*\)"$/\1/p' "$GK/tools/gkide.sh")
[ -n "$EXAMPLES" ] || { echo "import_ide: no EXAMPLES list in tools/gkide.sh" >&2; exit 1; }
for id in $EXAMPLES; do
	cp -r "$GK/apps/$id" "$DEST/build/web/examples/$id"
done
python3 -I - "$DEST/build/web/examples" $EXAMPLES > "$DEST/build/web/examples.json" <<'EOF'
import json, os, sys
root, ids = sys.argv[1], sys.argv[2:]
apps = {}
for app in ids:
    files = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(root, app)):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for f in sorted(filenames):
            if not f.startswith("."):
                files.append(os.path.relpath(os.path.join(dirpath, f), os.path.join(root, app)).replace(os.sep, "/"))
    apps[app] = files
json.dump({"apps": apps}, sys.stdout, indent=1)
EOF

# 5. The entry point and the record of where it came from.
cat > "$DEST/index.html" <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'">
<meta http-equiv="refresh" content="0; url=web/index.html">
<title>GapKeep IDE</title>
</head>
<body><p><a href="web/index.html">GapKeep IDE</a></p></body>
</html>
EOF
COMMIT=$(git -C "$GK" rev-parse HEAD)
DIRTY=$(git -C "$GK" status --porcelain -- sim apps tools/gkide.sh | head -1)
{
	echo "GapKeep commit: $COMMIT${DIRTY:+ (with uncommitted changes in sim/, apps/ or tools/gkide.sh)}"
	echo "Imported: $(date -u +%Y-%m-%dT%H:%M:%SZ) by tools/import_ide.sh"
	echo "Simulator: gksim.wasm sha256 $(sha256sum "$DEST/build/web/gksim.wasm" | cut -d' ' -f1)"
	echo "Monaco: $(cat "$DEST/web/vendor/monaco/VERSION" 2>/dev/null || echo unknown)"
	echo "Examples: $EXAMPLES"
} > "$DEST/SOURCE"
cat "$DEST/SOURCE"
du -sh "$DEST"
