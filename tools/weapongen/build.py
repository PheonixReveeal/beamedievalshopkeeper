"""Build weapon models.  python build.py [OUT_DIR] [Name ...]"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import build  # noqa: E402
from weapons import WEAPONS  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "assets/weapons"
names = sys.argv[2:] or list(WEAPONS)
stats_path = os.path.join(out, "stats.json")
stats = json.load(open(stats_path)) if os.path.exists(stats_path) else {}
for n in names:
    t = time.time()
    pieces, grip = WEAPONS[n]()
    s = build(n, pieces, os.path.join(out, n), origin=grip)
    stats[n] = s
    print(f"{n:24s} tris={s['tris']:5d} size={[round(b - a, 2) for a, b in zip(s['bbox_min'], s['bbox_max'])]} "
          f"px/stud={s['density']}  ({time.time() - t:.1f}s)")
json.dump(stats, open(stats_path, "w"), indent=1)
