#!/bin/sh
# render_previews.sh OUT_DIR [mode]   mode = strip (4 key frames, fast) | anim (mp4 + webp per weapon)
# Needs: node + playwright, ffmpeg, and `npm i` in tools/weapongen/preview.
set -e
OUT=$(realpath -m "$1"); MODE=${2:-strip}
cd "$(dirname "$0")/../weapongen/preview"
mkdir -p models "$OUT"
ln -sfn ../../../assets/vfx/textures vfxtex
ln -sf ../../../assets/vfx/presets.json vfxpresets.json
# name | model file | query
cat > /tmp/vfx_jobs.$$ <<JOBS
Voidrender|weapons/Voidrender/Voidrender|swing=1.6&burst=1.95&yaw=20
Emberfang|weapons/Emberfang/Emberfang|swing=1.6&burst=1.95&yaw=20
Frostbrand|weapons/Frostbrand/Frostbrand|swing=1.6&burst=1.95&yaw=20
TidecrystalShard|weapons/TidecrystalShard/TidecrystalShard|swing=1.6&burst=1.95&yaw=20
SunsteelFalchion|weapons/SunsteelFalchion/SunsteelFalchion|swing=1.6&burst=1.95&yaw=20
GlacierCleaver|weapons/GlacierCleaver/GlacierCleaver|swing=1.6&burst=1.95&yaw=10
DuskforgedWarhammer|weapons/DuskforgedWarhammer/DuskforgedWarhammer|swing=1.6&burst=1.95&yaw=25
RoyalSapphireScepter|weapons/RoyalSapphireScepter/RoyalSapphireScepter|swing=1.6&burst=1.95&yaw=20
ArcaneAmethystStaff|weapons/ArcaneAmethystStaff/ArcaneAmethystStaff|swing=1.6&burst=1.95&yaw=20
GlacierBow|weapons/GlacierBow/GlacierBow|axis=x&burst=1.9&yaw=15
DragonbaneArbalest|items/Crossbows/DragonbaneArbalest/DragonbaneArbalest|axis=x&burst=1.9&yaw=215
JOBS
while IFS='|' read name file query; do
  cp "../../../assets/$file.glb" "models/$name.glb"
  tmp="$OUT/.frames_$name"; rm -rf "$tmp"
  if [ "$MODE" = strip ]; then
    node vfxshot.mjs "$tmp" "preset=$name&model=$name&$query" 2.6 4 420 420 >/dev/null </dev/null
    python3 - "$tmp" "$OUT/$name.png" <<PY
import sys; from PIL import Image
fs = [f"{sys.argv[1]}/f{i:04d}.png" for i in (2, 5, 6, 8)]
ims = [Image.open(f) for f in fs]; w, h = ims[0].size
out = Image.new("RGB", (w * 4, h)); [out.paste(im, (i * w, 0)) for i, im in enumerate(ims)]; out.save(sys.argv[2])
PY
  else
    node vfxshot.mjs "$tmp" "preset=$name&model=$name&$query" 3.6 24 480 480 >/dev/null </dev/null
    ffmpeg -nostdin -loglevel error -y -framerate 24 -i "$tmp/f%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 23 "$OUT/$name.mp4"
    ffmpeg -nostdin -loglevel error -y -framerate 24 -i "$tmp/f%04d.png" -vf "scale=360:-1" -loop 0 -c:v libwebp -quality 70 "$OUT/$name.webp"
    cp "$tmp/f0084.png" "$OUT/$name.png"           # calm end of the clip: aura fully built up
  fi
  rm -rf "$tmp"
  echo "$name done"
done < /tmp/vfx_jobs.$$
rm -f /tmp/vfx_jobs.$$
if [ "$MODE" = anim ]; then
  python3 - "$OUT" <<PY
import sys; from PIL import Image
order = ["Voidrender", "Emberfang", "Frostbrand", "TidecrystalShard", "SunsteelFalchion", "GlacierCleaver",
         "DuskforgedWarhammer", "RoyalSapphireScepter", "ArcaneAmethystStaff", "GlacierBow", "DragonbaneArbalest"]
ims = [Image.open(f"{sys.argv[1]}/{n}.png").resize((320, 320)) for n in order]
out = Image.new("RGB", (4 * 320, 3 * 320), (20, 22, 28))
for i, im in enumerate(ims):
    out.paste(im, ((i % 4) * 320, (i // 4) * 320))
out.save(f"{sys.argv[1]}/overview.png")
PY
fi
