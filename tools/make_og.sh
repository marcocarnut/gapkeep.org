#!/bin/sh
# Makes site/img/og.png, the picture shown when a link to the site is shared,
# from tools/og.html, with headless Chrome.
set -e
cd "$(dirname "$0")/.."
P=$(mktemp -d)
google-chrome --headless=new --no-sandbox --hide-scrollbars --user-data-dir="$P" --allow-file-access-from-files \
	--force-device-scale-factor=1 --window-size=1200,630 --virtual-time-budget=3000 \
	--screenshot="$PWD/site/img/og.png" "file://$PWD/tools/og.html" >/dev/null 2>&1
rm -rf "$P"
python3 -c "
from PIL import Image
im = Image.open('site/img/og.png').convert('RGB')
im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save('site/img/og.png', optimize=True)"
ls -l site/img/og.png
