"""Crossbows. Built in the Roblox tool frame: forward = -Z, up = +Y; origin = the trigger hand."""
import math

import numpy as np

from core import Chart, P, gem, lathe, layers, noise, pillow, smooth, tube, voronoi, engrave_filigree, engrave_runes
from items_headwear import DARK_IRON, STEEL
from items_shields import IRON
from weapons import BLACK_LEATHER, CRIMSON, GOLD, RUBY, WOOD_DARK, WOOD_MID, bez, gem_chart, sym


def side_profile(top, bottom):
    """Stock outline from a top edge and a bottom edge, each [(f, y), ...] from butt to front."""
    return list(top) + list(reversed(bottom))


def to_forward(piece):
    """Pieces drawn with x = forward distance -> point them along -Z."""
    return piece.rot([0, 1, 0], 90)


def rect_band(f0, f1, y, hw, hh, chart, chamfer=0.25):
    """A rectangular collar around the stock between forward distances f0..f1."""
    L = f1 - f0
    prof = [(0.0, 0.0), (1 - chamfer * 0.4, 0.0), (1.0, L * 0.15), (1.0, L * 0.85), (1 - chamfer * 0.4, L), (0.0, L)]
    b = lathe(prof, chart, segs=4, phase=math.pi / 4, flat_sides=True, sx=hw / 0.7071, sz=hh / 0.7071, hard=(1, 2, 3, 4))
    # lathe axis Y -> -Z
    return b.rot([1, 0, 0], -90).move(0, y, -f0)


def bolt(f_back, f_tip, y, shaft_chart, head_chart, fletch_chart, r=0.022, head=0.16, broad=False):
    L = f_tip - f_back - head
    shaft = tube(np.array([[0, y, -f_back], [0, y, -(f_back + L)]]), r, chart=shaft_chart, segs=6, up=(0, 1, 0))
    hw = 0.06 if broad else 0.035
    tip = lathe([(0, 0), (hw, 0.0), (hw * 0.9, head * 0.25), (0, head)], head_chart, segs=4, flat_sides=True,
                hard=(1, 2), sz=0.45 if broad else 1.0)
    out = [shaft, tip.rot([1, 0, 0], -90).move(0, y, -(f_back + L))]
    vane = [(0.0, 0.0), (0.16, 0.0), (0.12, 0.05), (0.02, 0.05)]
    for ang in (0, 120, 240):
        v = pillow(vane, 0.004, 0.002, 0.004, chart=fletch_chart).rot([1, 0, 0], 90)
        v = v.move(0, 0, r * 0.6).rot([1, 0, 0], 0)
        out.append(to_forward(v.copy()).rot([0, 0, 1], ang + 90).move(0, y, -f_back - 0.02))
    return out


def prod_path(f, y, span, bend, n=31):
    x = np.linspace(-span, span, n)
    return np.column_stack([x, np.full(n, y), -f + bend * (x / span) ** 2])


def string(tips, nut, chart):
    out = []
    for t in tips:
        out.append(tube(np.array([t, nut]), 0.009, chart=chart, segs=4, up=(0, 1, 0), cap=False))
    return out


def stirrup(f, y, chart, w=0.17, h=0.22, r=0.02):
    t = np.linspace(-math.pi / 2, math.pi / 2, 14)
    path = np.column_stack([w * np.sin(t), y - 0.02 - h * np.cos(t) * 0.0 - h * (1 - np.abs(np.sin(t))) * 0,
                            -f - h * np.cos(t)])
    return tube(path, r, chart=chart, segs=6, up=(0, 1, 0))


def trigger(f, y, chart):
    t = np.linspace(0, 1, 10)
    path = np.column_stack([np.zeros_like(t), y - 0.05 - 0.3 * t, -f + 0.25 * t ** 1.5])
    return tube(path, lambda tt: 0.022 * (1 - 0.3 * tt), chart=chart, segs=6, up=(1, 0, 0), aspect=0.6)


def metal(color, seed=0, rough=0.3, metal_=0.85):
    return Chart(0.8, 0.8, P.metal(color, rough=rough, var=0.25, seed=seed, metal=metal_), "metal")


def string_chart():
    return Chart(0.05, 2.0, P.hair((0.88, 0.84, 0.72), seed=7), "string")


def standard_stock(scale=1.0):
    s = scale
    top = [(-1.35 * s, 0.06 * s)] + bez((-1.35 * s, 0.06 * s), (-0.9 * s, 0.06 * s), (-0.55 * s, 0.07 * s), (-0.3 * s, 0.07 * s), 6) + \
          [(-0.3 * s, 0.07 * s), (1.2 * s, 0.07 * s), (1.3 * s, 0.05 * s)]
    bot = [(-1.35 * s, -0.33 * s)] + bez((-1.35 * s, -0.33 * s), (-0.9 * s, -0.3 * s), (-0.6 * s, -0.12 * s), (-0.35 * s, -0.08 * s), 7) + \
          [(-0.35 * s, -0.08 * s), (0.9 * s, -0.08 * s), (1.2 * s, -0.1 * s), (1.3 * s, -0.08 * s)]
    return side_profile(top, bot)


# =============================================================== the crossbows

def crossbow():
    wood = Chart(2.8, 0.5, P.wood(WOOD_MID, seed=400), "stock")
    iron, steel = metal(IRON, 401, 0.4), metal(STEEL, 402, 0.25)
    pieces = [to_forward(pillow(standard_stock(), 0.088, 0.06, 0.04, chart=wood, max_area=0.004))]
    fp, yp = 1.18, 0.0
    pp = prod_path(fp, yp, 0.95, 0.32)
    pieces.append(tube(pp, lambda t: 0.04 * (1 - 0.35 * abs(2 * t - 1)), chart=steel, segs=8, up=(0, 1, 0),
                       aspect=lambda t: 1.6))
    pieces.append(rect_band(1.08, 1.3, 0.0, 0.1, 0.11, iron))
    pieces.append(rect_band(-0.05, 0.12, 0.0, 0.098, 0.1, iron))
    pieces.append(lathe([(0, 0), (0.05, 0), (0.05, 0.04), (0, 0.04)], iron, segs=10).rot([0, 0, 1], 90)
                  .move(0.02, 0.09, -0.05))
    pieces += string([pp[0], pp[-1]], np.array([0, 0.09, -0.05]), string_chart())
    pieces.append(stirrup(1.3, 0.0, iron))
    pieces.append(trigger(0.0, -0.05, iron))
    pieces += bolt(0.05, 1.45, 0.1, Chart(0.1, 1.4, P.wood((0.6, 0.45, 0.28), seed=403)), iron,
                   Chart(0.2, 0.06, P.feather((0.85, 0.82, 0.75), barb=0.01, seed=404)))
    return pieces, (0, -0.12, 0.35)


def hunters_crossbow():
    carved = P.wood(WOOD_DARK, seed=410, dark=0.5)

    def carve(nu, nv, su, sv):
        L = carved(nu, nv, su, sv)
        engrave_filigree(density=1.8, depth=0.003, dirt=0.4)(L, nu, nv, su, sv)
        return L

    wood = Chart(2.8, 0.5, carve, "stock")
    bronze = metal((0.75, 0.55, 0.3), 411, 0.3)
    pieces = [to_forward(pillow(standard_stock(), 0.088, 0.06, 0.04, chart=wood, max_area=0.004))]
    # Leather grip wrap and a fur-trimmed cheek pad.
    wrap = Chart(0.6, 0.4, P.wrap((0.3, 0.18, 0.08), pitch=0.05, seed=412), "wrap")
    pieces.append(rect_band(-0.45, -0.1, -0.01, 0.095, 0.09, wrap, chamfer=0.6))
    pad = sym([(0.0, -0.08), (0.2, -0.07), (0.25, 0.0), (0.2, 0.07), (0.0, 0.08)])
    for side in (1, -1):
        p = pillow([(x - 0.95, y - 0.1) for x, y in pad], 0.02, 0.01, 0.02,
                   chart=Chart(0.5, 0.2, P.leather((0.4, 0.25, 0.12), seed=413, stitch=[('v', 0.1), ('v', 0.9)])))
        pieces.append(to_forward(p).move(side * 0.092, 0, 0))
    # Laminated wooden recurve prod with horn tips.
    fp = 1.18
    span = 1.0
    x = np.linspace(-span, span, 31)
    k = np.abs(x) / span
    pp = np.column_stack([x, np.zeros_like(x), -fp + 0.3 * k ** 2 - 0.18 * np.clip((k - 0.8) / 0.2, 0, 1) ** 2])

    def laminate(nu, nv, su, sv):
        L = P.wood((0.6, 0.38, 0.18), seed=414, dark=0.3)(nu, nv, su, sv)
        u = (np.arange(nu) + 0.5) / nu
        stripe = (np.abs(((u * 3) % 1) - 0.5) < 0.1)[None, :, None]
        L["color"] = np.where(stripe, L["color"] * 0.4, L["color"])
        return L
    pieces.append(tube(pp, lambda t: 0.042 * (1 - 0.35 * abs(2 * t - 1)), painter=laminate, segs=8, up=(0, 1, 0),
                       aspect=1.7, name="prod"))
    horn = Chart(0.3, 0.3, P.metal((0.9, 0.85, 0.72), rough=0.4, seed=415, metal=0.1), "horn")
    for side in (1, -1):
        tip = pp[-1] if side > 0 else pp[0]
        pieces.append(lathe([(0, 0), (0.04, 0.01), (0.03, 0.08), (0, 0.12)], horn, segs=8)
                      .rot([0, 0, 1], -side * 90).move(*tip))
    pieces.append(rect_band(1.08, 1.3, 0.0, 0.1, 0.11, bronze))
    pieces += string([pp[1], pp[-2]], np.array([0, 0.09, -0.05]), string_chart())
    pieces.append(trigger(0.0, -0.05, bronze))
    pieces += bolt(0.05, 1.45, 0.1, Chart(0.1, 1.4, P.wood((0.55, 0.4, 0.25), seed=416)), bronze,
                   Chart(0.2, 0.06, P.feather((0.25, 0.5, 0.2), tip=(0.6, 0.75, 0.3), barb=0.01, seed=417)))
    return pieces, (0, -0.12, 0.35)


def siege_crossbow():
    s = 1.3
    wood = Chart(3.6, 0.6, P.wood((0.32, 0.2, 0.11), seed=420, dark=0.45), "stock")
    iron, steel = metal(DARK_IRON, 421, 0.4), metal(STEEL, 422, 0.25)
    pieces = [to_forward(pillow(standard_stock(s), 0.1, 0.07, 0.05, chart=wood, max_area=0.006))]
    for f0, f1 in ((-1.6, -1.45), (-0.6, -0.42), (0.4, 0.55), (1.2, 1.7)):
        pieces.append(rect_band(f0, f1, -0.01, 0.115, 0.13, iron))
    # Iron side plates with rivets.
    plate = [(-0.3, -0.07), (0.9, -0.07), (0.95, 0.0), (0.9, 0.07), (-0.3, 0.07)]
    for side in (1, -1):
        pl = pillow(plate, 0.01, 0.008, 0.01, chart=iron)
        pieces.append(to_forward(pl).move(side * 0.112, -0.01, 0))
    fp = 1.52
    for k, (dy, sp, th) in enumerate(((0.03, 1.3, 0.055), (-0.07, 1.05, 0.045))):
        pp = prod_path(fp - 0.02 * k, dy, sp, 0.4)
        pieces.append(tube(pp, lambda t, th=th: th * (1 - 0.35 * abs(2 * t - 1)), chart=steel, segs=8, up=(0, 1, 0),
                           aspect=1.6))
    pp = prod_path(fp, 0.03, 1.3, 0.4)
    nut = np.array([0, 0.12, -0.1])
    pieces += string([pp[0], pp[-1]], nut, string_chart())
    pieces.append(lathe([(0, 0), (0.07, 0), (0.07, 0.05), (0, 0.05)], iron, segs=10).rot([0, 0, 1], 90).move(0.025, 0.12, -0.1))
    pieces.append(stirrup(1.72, 0.0, iron, w=0.24, h=0.3, r=0.03))
    pieces.append(trigger(0.0, -0.08, iron))
    # Windlass at the butt.
    drum = lathe([(0.0, -0.2), (0.07, -0.2), (0.07, -0.16), (0.05, -0.15), (0.05, 0.15), (0.07, 0.16), (0.07, 0.2),
                  (0.0, 0.2)], iron, segs=12, hard=(1, 2, 5, 6)).rot([0, 0, 1], 90)
    pieces.append(drum.move(0, 0.16, 1.62))
    for side in (1, -1):
        t = np.linspace(0, 1, 8)
        crank = np.column_stack([side * (0.2 + 0.0 * t), 0.16 - 0.25 * t, 1.62 + 0.0 * t])
        pieces.append(tube(crank, 0.018, chart=iron, segs=6, up=(0, 0, 1)))
        pieces.append(tube(np.array([[side * 0.2, -0.09, 1.62], [side * 0.34, -0.09, 1.62]]), 0.024,
                           chart=Chart(0.2, 0.2, P.wood(WOOD_DARK, seed=423)), segs=8, up=(0, 1, 0)))
    pieces += bolt(-0.05, 1.9, 0.14, Chart(0.12, 1.9, P.wood((0.5, 0.36, 0.22), seed=424)), steel,
                   Chart(0.25, 0.08, P.feather((0.55, 0.12, 0.1), barb=0.012, seed=425)), r=0.03, head=0.22, broad=True)
    return pieces, (0, -0.15, 0.45)


def repeating_crossbow():
    lacquer = Chart(2.8, 0.5, P.wood((0.45, 0.1, 0.06), seed=430, dark=0.3), "stock")
    brass = metal((0.88, 0.66, 0.34), 431, 0.25)
    steel = metal(STEEL, 432, 0.25)
    pieces = [to_forward(pillow(standard_stock(), 0.088, 0.06, 0.04, chart=lacquer, max_area=0.004))]
    # Magazine box on top.
    mag = [(0.0, 0.0), (0.95, 0.0), (1.0, 0.06), (1.0, 0.26), (0.92, 0.3), (0.05, 0.3), (0.0, 0.24)]
    m = pillow(mag, 0.075, 0.065, 0.015, chart=lacquer)
    pieces.append(to_forward(m).move(0, 0.07, -0.05))
    for f in (0.12, 0.55, 0.95):
        pieces.append(rect_band(f, f + 0.06, 0.2, 0.083, 0.15, brass))
    # Bolt heads peeking out of the magazine.
    for k in range(3):
        pieces.append(lathe([(0, 0), (0.025, 0), (0, 0.08)], steel, segs=4, flat_sides=True).rot([1, 0, 0], -90)
                      .move(-0.03 + 0.03 * k, 0.33, -1.0))
    # Cocking lever: a U-shaped arm from the magazine front down to the stock.
    t = np.linspace(0, 1, 16)
    for side in (1, -1):
        arm = np.column_stack([np.full_like(t, side * 0.095), 0.3 - 0.5 * t, -0.9 + 1.25 * t])
        pieces.append(tube(arm, 0.02, chart=brass, segs=6, up=(1, 0, 0)))
    pieces.append(tube(np.array([[-0.095, -0.2, 0.35], [0.095, -0.2, 0.35]]), 0.024, chart=brass, segs=8, up=(0, 1, 0)))
    fp = 1.18
    pp = prod_path(fp, 0.0, 0.85, 0.28)
    pieces.append(tube(pp, lambda tt: 0.038 * (1 - 0.35 * abs(2 * tt - 1)), chart=Chart(0.3, 2.0, P.wood((0.25, 0.14, 0.08), seed=433)),
                       segs=8, up=(0, 1, 0), aspect=1.8))
    pieces.append(rect_band(1.08, 1.3, 0.0, 0.1, 0.11, brass))
    pieces += string([pp[0], pp[-1]], np.array([0, 0.08, -0.15]), string_chart())
    pieces.append(trigger(0.0, -0.05, brass))
    return pieces, (0, -0.12, 0.35)


def dragonbane_arbalest():
    def obsidian(nu, nv, su, sv):
        L = P.metal((0.12, 0.09, 0.1), rough=0.3, var=0.3, seed=440, metal=0.75)(nu, nv, su, sv)
        LT = {k: np.swapaxes(a, 0, 1).copy() for k, a in L.items()}
        engrave_runes(7, color=(1.0, 0.25, 0.08), strength=1.8, width=0.25, seed=441)(LT, nv, nu, sv, su)
        return {k: np.swapaxes(a, 0, 1) for k, a in LT.items()}

    stock = Chart(2.9, 0.5, obsidian, "stock")
    gold = metal((0.9, 0.62, 0.25), 442, 0.22)
    pieces = [to_forward(pillow(standard_stock(1.05), 0.09, 0.062, 0.04, chart=stock, max_area=0.004))]
    for f0, f1 in ((-0.55, -0.45), (-0.05, 0.08), (1.1, 1.36)):
        pieces.append(rect_band(f0, f1, -0.005, 0.1, 0.11, gold))
    # Dragon-wing prod: membranes with bony spars.
    wing = [(0.0, 0.05), (0.35, 0.12), (0.75, 0.25), (1.15, 0.42), (1.05, 0.25), (0.95, 0.3), (0.85, 0.12), (0.7, 0.17),
            (0.6, 0.02), (0.45, 0.06), (0.32, -0.06), (0.15, -0.03), (0.05, -0.06)]

    def membrane(nu, nv, su, sv):
        ppu = nu / su
        vv, uu = np.mgrid[0:nv, 0:nu]
        u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
        n = noise(nv, nu, 0.1 * ppu, octaves=4, seed=443)
        veins = np.exp(-(np.abs(np.sin((u * 5 + v * 2 + n) * math.pi)) / 0.06) ** 2)
        col = np.array([0.45, 0.04, 0.04]) * (0.7 + 0.5 * n)[..., None]
        col = col * (1 - 0.5 * veins[..., None]) + np.array([1.0, 0.35, 0.05]) * 0.5 * veins[..., None]
        return layers(nu, nv, col, 0.2, 0.45, height=0.002 * veins, emit=np.array([1.0, 0.3, 0.05]) * 0.8 * veins[..., None])

    mc = Chart(1.2, 0.5, membrane, "membrane")
    fp = 1.22
    tips = []
    for side in (1, -1):
        w = pillow([(side * x * 1.25, y * 1.4) for x, y in wing], 0.024, 0.008, 0.03, chart=mc)
        w.rot([1, 0, 0], 90).move(0, 0.0, -fp)             # lie flat, swept back toward the shooter
        w.deform(lambda v: v + np.column_stack([0 * v[:, 0], 0.12 * v[:, 0] ** 2, 0 * v[:, 0]]))
        pieces.append(w)
        X = 1.15 * 1.25
        tip = np.array([side * X, 0.12 * X ** 2, -fp + 0.42 * 1.4])
        tips.append(tip)
        t = np.linspace(0, 1, 12)
        spar = np.column_stack([side * X * t, 0.12 * (X * t) ** 2 + 0.025, -fp + 0.42 * 1.4 * t ** 1.6])
        pieces.append(tube(spar, lambda tt: 0.035 * (1 - 0.7 * tt), chart=gold, segs=6, up=(0, 1, 0)))
    pieces += string(tips, np.array([0, 0.095, -0.05]), Chart(0.05, 2.0, P.hair((0.95, 0.4, 0.1), seed=444, glow=(1, 0.4, 0.1)), "string"))
    # Dragon head at the muzzle.
    head = [(0.0, -0.1), (0.25, -0.08), (0.42, -0.02), (0.45, 0.04), (0.3, 0.07), (0.15, 0.13), (0.0, 0.11)]
    hc = Chart(0.5, 0.3, P.scales((0.12, 0.08, 0.08), tip=(0.5, 0.15, 0.1), size=0.05, metal=0.75, rough=0.3, seed=445), "head")
    hp = pillow(head, 0.07, 0.03, 0.05, chart=hc)
    pieces.append(to_forward(hp).move(0, 0.0, -1.3))
    horn = Chart(0.3, 0.6, P.metal((0.85, 0.78, 0.65), rough=0.45, seed=446, metal=0.2), "horn")
    for side in (1, -1):
        t = np.linspace(0, 1, 10)
        hpth = np.column_stack([side * (0.05 + 0.1 * t), 0.1 + 0.12 * t, -1.38 + 0.35 * t])
        pieces.append(tube(hpth, lambda tt: 0.03 * (1 - tt) + 0.003, chart=horn, segs=6, up=(0, 1, 0)))
        pieces.append(gem("brilliant", (0.025, 0.025, 0.018), chart=gem_chart(RUBY, 447)).rot([0, 1, 0], side * 90)
                      .move(side * 0.07, 0.04, -1.58))
    flame = Chart(0.3, 0.04, P.gem((1.0, 0.45, 0.08), 448), "flame")
    pieces += bolt(0.05, 1.5, 0.1, Chart(0.1, 1.4, P.metal((0.15, 0.12, 0.12), rough=0.35, seed=449)), gold,
                   Chart(0.2, 0.06, P.feather((0.6, 0.05, 0.05), tip=(1.0, 0.5, 0.1), barb=0.01, seed=450)))
    pieces.append(gem("crystal", (0.035, 0.1, 0.035), chart=flame).rot([1, 0, 0], -90).move(0, 0.1, -1.62))
    pieces.append(trigger(0.0, -0.05, gold))
    return pieces, (0, -0.12, 0.35)


CROSSBOWS = {"Crossbow": crossbow, "HuntersCrossbow": hunters_crossbow, "SiegeCrossbow": siege_crossbow,
             "RepeatingCrossbow": repeating_crossbow, "DragonbaneArbalest": dragonbane_arbalest}
