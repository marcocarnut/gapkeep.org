#!/bin/sh
#
# Screenshots of the site with headless Chrome, at phone and desktop sizes,
# in both languages, into screenshots/: the first screen (as a visitor sees
# it) and the whole page (a tall window). Serve the site first:
#
#   python3 -m http.server 8047 --bind 127.0.0.1 --directory site &
#   tools/screenshot_site.sh [http://127.0.0.1:8047] [page]
#
# Dark theme (the default); THEME=light for the light one; FULL=12000 for
# whole pages too.
#
set -e
BASE=${1:-http://127.0.0.1:8047}
PAGE=${2:-}
OUT=$(cd "$(dirname "$0")/.." && pwd)/screenshots
NAME=$(echo "${PAGE:-home}" | sed 's/[^a-z0-9]/-/g; s/-html$//; s/-$//')
mkdir -p "$OUT"
DARK=--force-dark-mode
if [ "$THEME" = light ]; then DARK=; NAME=$NAME-light; fi
CHROME=$(command -v google-chrome || command -v chromium || command -v chromium-browser)
shot() { # lang path size file
	PROFILE=$(mktemp -d)
	"$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --user-data-dir="$PROFILE" \
		--lang="$1" --accept-lang="$1" $DARK --force-device-scale-factor=1 --virtual-time-budget=6000 \
		--window-size="$3" --screenshot="$4" "$BASE$2" >/dev/null 2>&1
	rm -rf "$PROFILE"
	echo "$4"
}
for L in en pt-BR; do
	case $L in en) P=/ ;; *) P=/pt-br/ ;; esac
	shot $L "$P$PAGE" 390,844 "$OUT/$NAME-$L-phone.png"
	shot $L "$P$PAGE" 1440,900 "$OUT/$NAME-$L-desktop.png"
	[ -n "$FULL" ] || continue
	DARK="$DARK --force-prefers-reduced-motion"
	shot $L "$P$PAGE" 390,$FULL "$OUT/$NAME-$L-phone-full.png"
	shot $L "$P$PAGE" 1440,$FULL "$OUT/$NAME-$L-desktop-full.png"
done
