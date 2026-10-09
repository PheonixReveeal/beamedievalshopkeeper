"""Build shop item models.  python build_items.py [OUT_DIR] [Category or Name ...]"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import build  # noqa: E402
from items import CATEGORIES, ATLAS_SIZE  # noqa: E402


def flatten(xs):
    for x in xs:
        if isinstance(x, (list, tuple)):
            yield from flatten(x)
        else:
            yield x


out = sys.argv[1] if len(sys.argv) > 1 else "assets/items"
wanted = set(sys.argv[2:])
stats_path = os.path.join(out, "stats.json")
stats = json.load(open(stats_path)) if os.path.exists(stats_path) else {}
for cat, items in CATEGORIES.items():
    for name, fn in items.items():
        if wanted and cat not in wanted and name not in wanted:
            continue
        t = time.time()
        res = fn()
        pieces, origin = (res if isinstance(res, tuple) else (res, (0, 0, 0)))
        s = build(name, list(flatten(pieces)), os.path.join(out, cat, name), atlas=ATLAS_SIZE[cat], origin=origin)
        s["category"] = cat
        stats[name] = s
        size = [round(b - a, 2) for a, b in zip(s["bbox_min"], s["bbox_max"])]
        print(f"{cat:10s} {name:24s} tris={s['tris']:5d} size={size} ({time.time() - t:.1f}s)", flush=True)
json.dump(stats, open(stats_path, "w"), indent=1)
