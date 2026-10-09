#!/bin/sh
# render.sh OUT.png "Name1,Name2" [extra query] [w] [h]  -- renders built weapons from assets/weapons
cd "$(dirname "$0")"; mkdir -p models
files=""
for n in $(echo "$2" | tr ',' ' '); do cp "../../../assets/weapons/$n/$n.glb" models/; files="$files${files:+,}models/$n.glb"; done
node shot.mjs "$1" "files=$files&$3" "${4:-900}" "${5:-900}"
