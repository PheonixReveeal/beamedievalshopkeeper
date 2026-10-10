#!/bin/sh
# Builds the intro assets into a temp folder and runs every check:
#   1. lint every animation (feet, limits, intersections, loop seams)
#   2. build the .rbxm files (reflection-checked) and read them back
#   3. compare every Pose CFrame in the .rbxm with what the previewer shows
#   4. run IntroKit against R15/R6 dummies from the built bundle
# Usage: sh tools/introgen/tests/run_all.sh [path/to/lune]
set -e
LUNE=${1:-lune}
cd "$(dirname "$0")/../../.."
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
names=$(ls tools/introgen/anims | grep -v '^_' | sed 's/\.json$//')
mirrors=$(grep -ho '"mirrorAs": *"[^"]*"' tools/introgen/anims/*.json | sed 's/.*"\([^"]*\)"$/\1/')
echo "== lint"; node tools/introgen/preview/lint.mjs $names $mirrors
echo "== build"; "$LUNE" run tools/introgen/build_rbxm.luau "$OUT/roblox"
echo "== rbxm vs previewer"; "$LUNE" run tools/introgen/tests/dump_poses.luau "$OUT/roblox/Intro_Animations.rbxm" > "$OUT/poses.json"
node tools/introgen/tests/check_builder.mjs "$OUT/poses.json"
echo "== IntroKit"; "$LUNE" run tools/introgen/tests/test_introkit.luau "$OUT/roblox"
