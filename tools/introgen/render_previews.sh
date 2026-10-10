#!/bin/sh
# Renders animation previews into assets/intro/previews/anims:
#   <Name>.png   contact sheet (front-on camera + side view)
#   <Name>.webp  animated loop from the cutscene-style 3/4 view
# Usage: sh tools/introgen/render_previews.sh [Name ...]
set -e
cd "$(dirname "$0")/../.."
OUT=assets/intro/previews/anims
mkdir -p "$OUT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
if [ $# -gt 0 ]; then names="$*"; else
  names="$(ls tools/introgen/anims | grep -v '^_' | sed 's/\.json$//') $(grep -ho '"mirrorAs": *"[^"]*"' tools/introgen/anims/*.json | sed 's/.*"\([^"]*\)"$/\1/')"
fi
for n in $names; do
  echo "$n"
  node tools/introgen/preview/animshot.mjs sheet "$OUT/$n.png" "$n" views=front0,side n=8 cols=8 cw=200 ch=250 </dev/null >/dev/null
  rm -rf "$TMP/f"; node tools/introgen/preview/animshot.mjs frames "$TMP/f" "$n" view=front fps=24 w=420 h=420 </dev/null >/dev/null
  ffmpeg -nostdin -loglevel error -y -framerate 24 -i "$TMP/f/f%04d.png" -vcodec libwebp -lossless 0 -q:v 70 -loop 0 "$OUT/$n.webp"
done
