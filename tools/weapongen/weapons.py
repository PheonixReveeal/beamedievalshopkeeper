"""Weapon definitions. Each function returns (pieces, grip_point).

Sizes are in studs and set against a default R15 character (~5.2 studs tall):
daggers/short swords ~3.5, one-handed swords ~4.5, big blades/hammers/axes ~5, staffs ~6.
"""
import math

import numpy as np

from core import (Chart, P, blade, engrave_filigree, engrave_line, engrave_runes, gem, lathe,
                  mirror, pillow, tube, smooth, noise, layers, voronoi)

# --------------------------------------------------------------- palette (sRGB)
GOLD = (0.95, 0.70, 0.28)
PALE_GOLD = (1.0, 0.82, 0.40)
BRONZE = (0.93, 0.71, 0.43)
COPPER = (0.86, 0.45, 0.27)
GUNMETAL = (0.40, 0.42, 0.50)
FROST_STEEL = (0.80, 0.88, 0.95)
WOOD_DARK = (0.30, 0.17, 0.09)
WOOD_MID = (0.50, 0.30, 0.15)
NAVY = (0.10, 0.13, 0.42)
BLACK_LEATHER = (0.09, 0.08, 0.08)
CRIMSON = (0.45, 0.06, 0.07)

SAPPHIRE = (0.15, 0.25, 0.95)
AMETHYST = (0.62, 0.25, 0.95)
CYAN = (0.35, 0.88, 1.0)
PINK = (1.0, 0.35, 0.75)
RUBY = (0.95, 0.12, 0.15)
VIOLET = (0.62, 0.30, 1.0)


# --------------------------------------------------------------- 2D helpers

def bez(p0, p1, p2, p3, n=10, end=False):
    t = np.linspace(0, 1, n, endpoint=end)[:, None]
    p0, p1, p2, p3 = map(np.asarray, (p0, p1, p2, p3))
    return list((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def sym(right):
    """Right half (x >= 0) from bottom-centre to top-centre -> full symmetric outline."""
    right = [tuple(p) for p in right]
    left = [(-x, y) for x, y in reversed(right[1:-1])]
    return right + left


def gold_chart(seed=0, ornate=False, color=GOLD, rough=0.24):
    return Chart(0.7, 0.7, P.metal(color, rough=rough, var=0.2, seed=seed, metal=0.85,
                                   engrave=engrave_filigree(density=2.2) if ornate else None), "gold")


def gem_chart(color, seed=0):
    return Chart(0.3, 0.04, P.gem(color, seed), "gem")


def band(y, r, h, chart, segs=16, lip=0.12, flat=False):
    """A metal band/ferrule around the Y axis with chamfered lips."""
    e = h * lip
    return lathe([(r * 0.85, y - h / 2), (r, y - h / 2 + e), (r, y + h / 2 - e), (r * 0.85, y + h / 2)],
                 chart, segs=segs, hard=(1, 2), flat_sides=flat)


def wrap_grip(y0, y1, r, chart, segs=12, bulge=0.06):
    n = 8
    ys = np.linspace(y0, y1, n)
    mid = (y0 + y1) / 2
    rs = r * (1 + bulge * (1 - ((ys - mid) / ((y1 - y0) / 2)) ** 2))
    return lathe(list(zip(rs, ys)), chart, segs=segs)


# --------------------------------------------------------------- blade helpers

def sec_diamond(edge=0.07, mid=0.5, midt=0.62):
    return lambda s: [[(-1, edge), (-mid, midt)], [(-mid, midt), (0, 1)], [(0, 1), (mid, midt)], [(mid, midt), (1, edge)]]


def sec_fuller(edge=0.07, bev=0.62, fw=0.3, depth=lambda s: 0.5, n=7):
    def f(s):
        d = depth(s)
        xs = np.linspace(-fw, fw, n)
        groove = [(x, 1 - d * math.cos(math.pi * x / (2 * fw)) ** 2) for x in xs]
        return [[(-1, edge), (-bev, 1)], [(-bev, 1), (-fw, 1)], groove, [(fw, 1), (bev, 1)], [(bev, 1), (1, edge)]]
    return f


def stations(y0, length, s_list, left, right, thick):
    """left/right(s) -> x of each edge; thick(s) -> half thickness."""
    out = []
    for s in s_list:
        L, R = left(s), right(s)
        w = max((R - L) / 2, 0.0)
        out.append((y0 + s * length, (L + R) / 2, w, w, max(thick(s), 0.0)))
    return out


def point_taper(s, start):
    """1 until `start`, then an ogive curve down to 0 at s=1."""
    if s <= start:
        return 1.0
    k = (s - start) / (1 - start)
    return math.sqrt(max(0.0, 1 - k ** 2))


TIP_S = lambda start, n=7: list(np.linspace(start, 1, n + 1)[1:])


# =============================================================== 1. Bronze Gladius

def bronze_gladius():
    gold, wood = gold_chart(1), Chart(0.5, 0.8, P.wood(WOOD_DARK, seed=3), "wood")
    L = 2.3

    def hw(s):
        base = 0.145 - 0.03 * math.sin(math.pi * min(s / 0.8, 1)) ** 1.5 * 0.6
        return base * point_taper(s, 0.8)

    ss = [0, 0.1, 0.25, 0.4, 0.55, 0.7, 0.8] + TIP_S(0.8, 8)
    st = stations(0.0, L, ss, lambda s: -hw(s), hw, lambda s: 0.036 * (1 - 0.4 * s) * (0.3 + 0.7 * point_taper(s, 0.8)))
    bronze = P.blade(BRONZE, rough=0.22, seed=2, edge=0.2, edge_color=(1.0, 0.86, 0.6),
                     etch=engrave_line(0.5, 0.025))
    pieces = [blade(st, sec_diamond(0.08, 0.38, 0.72), painter=bronze, name="blade")]

    guard = sym([(0, -0.06), (0.18, -0.06), (0.25, -0.045), (0.29, -0.0), (0.285, 0.05), (0.25, 0.075),
                 (0.16, 0.065), (0, 0.06)])
    pieces.append(pillow(guard, 0.085, 0.035, 0.05, chart=gold))
    # Ridged wooden grip (four finger ridges) between two gold collars.
    ys = np.linspace(-0.72, -0.08, 17)
    pieces.append(lathe([(0.072 * (1 + 0.07 * math.sin((y + 0.08) / 0.64 * 4 * math.pi) ** 2), y) for y in ys],
                        wood, segs=12))
    pieces += [band(-0.1, 0.09, 0.06, gold), band(-0.72, 0.09, 0.06, gold)]
    # Ball pommel with a peen button.
    prof = [(0.0, -0.98), (0.03, -0.975), (0.035, -0.955)] + \
           [(0.12 * math.sin(a), -0.86 - 0.1 * math.cos(a)) for a in np.linspace(0.45, math.pi - 0.6, 8)] + \
           [(0.06, -0.755), (0.05, -0.74), (0.0, -0.74)]
    pieces.append(lathe(prof, gold, segs=14, hard=(2,)))
    return pieces, (0, -0.4, 0)


# =============================================================== 2. Sunsteel Falchion

def sunsteel_falchion():
    gold, wrap = gold_chart(4), Chart(0.5, 0.7, P.wrap(BLACK_LEATHER, pitch=0.12, seed=5), "wrap")
    L = 2.55

    def left(s):   # the spine; drops toward the edge for the clipped point
        x = -0.10 + 0.01 * s
        if s > 0.72:
            k = (s - 0.72) / 0.28
            x += 0.2 * k ** 1.6
        return x

    def right(s):  # the cutting edge, widening toward the tip, then sweeping up to the point
        x = 0.13 + 0.12 * smooth(np.array(s), 0.0, 0.8)
        if s > 0.8:
            k = (s - 0.8) / 0.2
            x = 0.25 - (0.25 - 0.10) * (1 - math.sqrt(max(0, 1 - k ** 2)))
        return float(x)

    ss = [0, 0.08, 0.2, 0.35, 0.5, 0.62, 0.72, 0.8, 0.85, 0.9, 0.93, 0.96, 0.98, 1.0]

    def thick(s):
        return 0.04 * (1 - 0.5 * s) if s < 1 else 0.0

    st = stations(0, L, ss, left, right, thick)
    st[-1] = (L, 0.10, 0.0, 0.0, 0.0)

    def sec(s):
        d = 0.45 * smooth(np.array(s), 0.02, 0.08) * (1 - smooth(np.array(s), 0.55, 0.7))
        xs = np.linspace(-0.85, -0.45, 6)
        groove = [(x, 1 - float(d) * math.sin(math.pi * (x + 0.85) / 0.4) ** 2) for x in xs]
        return [[(-1, 1), (-0.85, 1)], groove, [(-0.45, 1), (0.15, 0.95)], [(0.15, 0.95), (1, 0.08)]]

    sun = P.blade(PALE_GOLD, rough=0.2, seed=6, edge=0.18, edge_color=(1.0, 0.95, 0.78),
                  etch=engrave_filigree(density=1.6, dirt=0.18))
    pieces = [blade(st, sec, painter=sun, name="blade")]

    right_half = [(0, -0.07), (0.14, -0.07)] + bez((0.14, -0.07), (0.26, -0.07), (0.34, -0.12), (0.36, -0.2), 8) + \
                 bez((0.36, -0.2), (0.43, -0.2), (0.45, -0.1), (0.39, -0.05), 8) + \
                 bez((0.39, -0.05), (0.33, 0.0), (0.2, 0.05), (0.13, 0.06), 8) + [(0.1, 0.17), (0, 0.2)]
    pieces.append(pillow(sym(right_half), 0.075, 0.03, 0.045, chart=gold))
    pieces.append(wrap_grip(-0.78, -0.06, 0.07, wrap))
    pieces += [band(-0.08, 0.085, 0.05, gold), band(-0.78, 0.085, 0.05, gold)]
    # Faceted scent-stopper pommel.
    pieces.append(lathe([(0, -1.08), (0.05, -1.07), (0.11, -0.98), (0.1, -0.88), (0.06, -0.82),
                         (0.06, -0.79), (0, -0.79)], gold, segs=8, flat_sides=True))
    return pieces, (0, -0.42, 0)


# =============================================================== 3. Frostbrand

def frostbrand():
    gold, wrap = gold_chart(7), Chart(0.5, 0.8, P.wrap(NAVY, pitch=0.13, seed=8), "wrap")
    L = 3.0

    def hw(s):
        leaf = 0.14 + 0.065 * math.sin(math.pi * min(max((s - 0.08) / 0.75, 0), 1)) ** 1.3
        return leaf * point_taper(s, 0.72)

    ss = [0, 0.08, 0.2, 0.3, 0.4, 0.5, 0.6, 0.72] + TIP_S(0.72, 9)
    st = stations(0, L, ss, lambda s: -hw(s), hw, lambda s: 0.05 * (1 - 0.35 * s) * (0.25 + 0.75 * point_taper(s, 0.72)))
    ice = P.ice(seed=9)
    pieces = [blade(st, sec_diamond(0.06, 0.5, 0.6), painter=ice, name="blade")]

    # Gold clasp around the blade with a violet gem on both faces.
    yc, hwc = 0.95, hw(0.95 / L) + 0.012
    clasp = lathe([(0.8, yc - 0.05), (1.0, yc - 0.035), (1.0, yc + 0.035), (0.8, yc + 0.05)], gold, segs=8,
                  phase=math.pi / 8, flat_sides=True, sx=hwc / 0.924, sz=0.068 / 0.924, hard=(1, 2))
    pieces.append(clasp)
    gc = gem_chart(VIOLET, 1)
    for z in (1, -1):
        g = gem("octa", (0.045, 0.06, 0.022), chart=gc).move(0, yc, z * 0.068)
        pieces.append(g)

    # Crown guard: arms sweeping up into three prongs on each side.
    rh = [(0, -0.08), (0.2, -0.08)] + bez((0.2, -0.08), (0.34, -0.08), (0.42, -0.02), (0.44, 0.08), 6) + \
         [(0.44, 0.08), (0.46, 0.2), (0.39, 0.1), (0.36, 0.18), (0.31, 0.06), (0.25, 0.14), (0.2, 0.05), (0.12, 0.06),
          (0.08, 0.13), (0, 0.15)]
    pieces.append(pillow(sym(rh), 0.08, 0.025, 0.05, chart=gold))
    cg = gem_chart(CYAN, 2)
    for z in (1, -1):
        pieces.append(gem("brilliant", (0.055, 0.055, 0.03), chart=cg).rot([1, 0, 0], 0 if z > 0 else 180).move(0, 0.02, z * 0.075))
    pieces.append(wrap_grip(-0.82, -0.07, 0.072, wrap))
    pieces += [band(-0.09, 0.088, 0.05, gold), band(-0.82, 0.088, 0.05, gold)]
    # Pommel: gold cup holding a downward ice crystal.
    pieces.append(lathe([(0.05, -0.97), (0.1, -0.93), (0.11, -0.88), (0.09, -0.85), (0.06, -0.83), (0.0, -0.83)],
                        gold, segs=12, hard=(1,)))
    pieces.append(gem("bipyramid", (0.08, 0.16, 0.08), chart=gem_chart(CYAN, 3), n=6).move(0, -1.02, 0))
    return pieces, (0, -0.45, 0)


# =============================================================== 4. Tidecrystal Shard

def tidecrystal_shard():
    gold, wrap = gold_chart(10), Chart(0.5, 0.8, P.wrap(BLACK_LEATHER, pitch=0.12, seed=11), "wrap")
    L = 3.05
    # Crystal barbs: (s_start, s_end, extra width) per edge, offset so the edges don't mirror.
    barbs_r = [(0.12, 0.27, 0.095), (0.42, 0.53, 0.08), (0.64, 0.73, 0.06)]
    barbs_l = [(0.24, 0.36, 0.09), (0.52, 0.62, 0.07)]

    def base(s):
        return (0.16 - 0.04 * s) * point_taper(s, 0.78)

    def barb(s, bs):
        for a, b, e in bs:
            if a <= s <= b:
                k = (s - a) / (b - a)
                return e * (k / 0.7 if k < 0.7 else (1 - k) / 0.3)   # tooth leaning toward the tip
        return 0.0

    knots = {0, 1, 0.78} | {x for a, b, _ in barbs_r + barbs_l for x in (a, a + 0.7 * (b - a), b)}
    ss = sorted(knots | set(TIP_S(0.78, 7)) | set(np.linspace(0, 0.78, 8)))
    st = stations(0, L, ss, lambda s: -base(s) - barb(s, barbs_l), lambda s: base(s) + barb(s, barbs_r),
                  lambda s: 0.055 * (1 - 0.35 * s) * (0.25 + 0.75 * point_taper(s, 0.78)))

    def sec(s):
        return [[(-1, 0.06), (-0.42, 0.55)], [(-0.42, 0.55), (-0.12, 1)], [(-0.12, 1), (0.12, 1)],
                [(0.12, 1), (0.42, 0.55)], [(0.42, 0.55), (1, 0.06)]]

    shard = P.crystal((0.28, 0.78, 0.8), seed=12, glow=(0.1, 0.5, 0.55))
    pieces = [blade(st, sec, painter=shard, name="blade")]

    # Gold diamond setting with a pink gem.
    yc = 0.55 * L
    setting = sym([(0, yc - 0.15), (0.1, yc), (0, yc + 0.15)])
    pieces.append(pillow(setting, 0.07, 0.04, 0.03, chart=gold))
    pc = gem_chart(PINK, 4)
    for z in (1, -1):
        pieces.append(gem("octa", (0.055, 0.09, 0.03), chart=pc).move(0, yc, z * 0.068))
    # Gold barb caps on three of the crystal barbs.
    for (a, b, e), side in ((barbs_r[0], 1), (barbs_l[0], -1), (barbs_r[2], 1)):
        b = a + 0.7 * (b - a)
        y = b * L
        x = side * (base(b) + e)
        tri = [(side * px, py) for px, py in [(0, -0.09), (0.06, 0.0), (0, 0.035), (-0.035, -0.02)]]
        p = pillow(tri, 0.035, 0.015, 0.02, chart=gold)
        pieces.append(p.move(x - side * 0.02, y - 0.01, 0))

    rh = [(0, -0.08), (0.12, -0.08), (0.3, -0.03), (0.47, 0.16), (0.36, 0.1), (0.28, 0.06), (0.18, 0.07),
          (0.1, 0.13), (0, 0.13)]
    pieces.append(pillow(sym(rh), 0.08, 0.025, 0.05, chart=gold))
    # Crystal shards growing out of the guard.
    tc = Chart(0.3, 0.04, P.gem((0.3, 0.85, 0.85), 9), "shards")
    for x, ang, sc in ((0.2, -28, 1.0), (-0.2, 28, 0.85), (0.3, -40, 0.6), (-0.29, 42, 0.55)):
        c = gem("crystal", (0.04 * sc, 0.16 * sc, 0.04 * sc), chart=tc).move(0, 0.13 * sc, 0)
        pieces.append(c.rot([0, 0, 1], ang).move(x, 0.05, 0))
    pieces.append(wrap_grip(-0.8, -0.07, 0.07, wrap))
    pieces += [band(-0.09, 0.086, 0.05, gold), band(-0.8, 0.086, 0.05, gold)]
    pieces.append(lathe([(0.0, -1.0), (0.06, -0.99), (0.11, -0.92), (0.1, -0.86), (0.06, -0.82), (0.0, -0.82)],
                        gold, segs=10, flat_sides=True))
    vc = gem_chart(AMETHYST, 5)
    for z in (1, -1):
        pieces.append(gem("brilliant", (0.045, 0.045, 0.03), chart=vc).rot([1, 0, 0], 0 if z > 0 else 180)
                      .move(0, -0.92, z * 0.085))
    return pieces, (0, -0.44, 0)


# =============================================================== 5. Voidrender

def voidrender():
    gold, wrap = gold_chart(13), Chart(0.5, 0.8, P.wrap(BLACK_LEATHER, pitch=0.11, seed=14), "wrap")
    L = 3.25

    def hw(s):
        w = 0.225 - 0.025 * s
        if s > 0.9:  # rounded, clipped tip
            k = (s - 0.9) / 0.1
            w *= math.sqrt(max(0, 1 - k ** 2)) * 0.85 + 0.15 * (1 - k)
        return w

    ss = [0, 0.06, 0.2, 0.4, 0.6, 0.8, 0.9] + TIP_S(0.9, 7)

    def thick(s):
        return 0.055 * (1 - 0.3 * s) * (0.3 + 0.7 * (hw(s) / (0.225 - 0.025 * s)))

    st = stations(0, L, ss, lambda s: -hw(s), hw, thick)
    depth = lambda s: 0.55 * float(smooth(np.array(s), 0.02, 0.07) * (1 - smooth(np.array(s), 0.8, 0.9)))

    def void_paint(nu, nv, su, sv):
        base = P.metal((0.13, 0.11, 0.2), rough=0.32, var=0.35, seed=15,
                       engrave=engrave_runes(9, color=(0.75, 0.35, 1.0), strength=2.0, width=0.2, seed=16))(nu, nv, su, sv)
        u = (np.arange(nu) + 0.5) / nu
        sheen = np.exp(-((np.abs(u - 0.5) - 0.47) / 0.04) ** 2)[None, :, None]   # violet edge sheen
        base["color"] = base["color"] * (1 - 0.6 * sheen) + np.array([0.55, 0.4, 0.95]) * 0.6 * sheen
        return base

    pieces = [blade(st, sec_fuller(0.07, 0.7, 0.36, depth), painter=void_paint, name="blade")]

    # Gold claws curling out of both edges near the base.
    for side in (1, -1):
        a = np.linspace(0, 1, 14)
        path = np.column_stack([side * (0.19 + 0.2 * np.sin(a * 1.9)), 0.28 + 0.32 * a - 0.12 * a ** 3, np.zeros_like(a)])
        pieces.append(tube(path, lambda t: 0.045 * (1 - t) + 0.004, chart=gold, segs=8, aspect=0.75))

    rh = [(0, -0.09), (0.16, -0.09)] + bez((0.16, -0.09), (0.32, -0.09), (0.44, 0.0), (0.5, 0.2), 7) + \
         bez((0.5, 0.2), (0.42, 0.12), (0.36, 0.06), (0.26, 0.06), 6) + [(0.24, 0.06), (0.12, 0.09), (0, 0.11)]
    pieces.append(pillow(sym(rh), 0.085, 0.025, 0.05, chart=gold))
    vc = gem_chart(VIOLET, 6)
    for z in (1, -1):
        pieces.append(gem("brilliant", (0.06, 0.06, 0.035), chart=vc).rot([1, 0, 0], 0 if z > 0 else 180).move(0, 0.0, z * 0.08))
    pieces.append(wrap_grip(-0.85, -0.08, 0.075, wrap))
    pieces += [band(-0.1, 0.09, 0.05, gold), band(-0.5, 0.088, 0.035, gold), band(-0.85, 0.09, 0.05, gold)]
    pieces.append(lathe([(0.05, -0.96), (0.1, -0.93), (0.1, -0.9), (0.07, -0.87), (0.0, -0.87)], gold, segs=10, hard=(1, 2)))
    pieces.append(gem("bipyramid", (0.085, 0.15, 0.085), chart=gem_chart(VIOLET, 7), n=6).move(0, -1.05, 0))
    return pieces, (0, -0.47, 0)


# =============================================================== 6. Emberfang (flamberge)

def emberfang():
    gold, wrap = gold_chart(17), Chart(0.5, 0.8, P.wrap(CRIMSON, pitch=0.12, seed=18), "wrap")
    L = 3.1
    waves = 5.5

    def amp(s):
        return 0.032 * smooth(np.array(s), 0.12, 0.25) * (1 - smooth(np.array(s), 0.75, 0.95))

    def cx(s):
        return float(amp(s)) * math.sin(2 * math.pi * waves * s)

    def hw(s):
        return (0.15 - 0.03 * s) * point_taper(s, 0.85)

    ss = sorted(set(np.linspace(0, 0.85, 44)) | set(TIP_S(0.85, 7)))
    st = stations(0, L, ss, lambda s: cx(s) - hw(s), lambda s: cx(s) + hw(s),
                  lambda s: 0.045 * (1 - 0.35 * s) * (0.3 + 0.7 * point_taper(s, 0.85)))

    def ember_paint(nu, nv, su, sv):
        ppu = nu / su
        base = P.metal(COPPER, rough=0.3, var=0.25, seed=19, metal=0.85, brushed=False)(nu, nv, su, sv)
        u = (np.arange(nu) + 0.5) / nu
        v = (np.arange(nv) + 0.5) / nv
        heat = np.exp(-((u - 0.5) / 0.2) ** 2)[None, :] * smooth(v, 0.0, 0.25)[:, None]  # v=0 is the tip
        tint = np.array([0.35, 0.1, 0.25])
        edge = 1 - np.exp(-((u - 0.5) / 0.32) ** 2)[None, :]
        base["color"] = base["color"] * (1 - 0.45 * edge[..., None]) + tint * 0.45 * edge[..., None]
        e, _ = voronoi(nv, nu, 0.16 * ppu, seed=20, aspect=0.6)
        crack = np.exp(-e / 1.4) * heat
        glow = np.array([1.0, 0.45, 0.08])
        base["emit"] = glow * 1.6 * crack[..., None]
        base["color"] = base["color"] * (1 - crack[..., None]) + glow * crack[..., None]
        base["height"] -= 0.003 * crack
        return base

    pieces = [blade(st, sec_diamond(0.08, 0.42, 0.8), painter=ember_paint, name="blade")]

    # Flame guard.
    rh = [(0, -0.08), (0.18, -0.08)] + bez((0.18, -0.08), (0.3, -0.08), (0.38, -0.04), (0.42, 0.04), 5) + \
         [(0.42, 0.04), (0.47, 0.17), (0.38, 0.09), (0.36, 0.2), (0.29, 0.07), (0.24, 0.15), (0.19, 0.05),
          (0.12, 0.07), (0.09, 0.16), (0.05, 0.1), (0, 0.13)]
    pieces.append(pillow(sym(rh), 0.08, 0.025, 0.05, chart=gold))
    rc = gem_chart(RUBY, 8)
    for z in (1, -1):
        pieces.append(gem("brilliant", (0.05, 0.05, 0.03), chart=rc).rot([1, 0, 0], 0 if z > 0 else 180).move(0, 0.0, z * 0.075))
    pieces.append(wrap_grip(-0.84, -0.07, 0.07, wrap))
    pieces += [band(-0.09, 0.086, 0.05, gold), band(-0.84, 0.086, 0.05, gold)]
    # Flame-shaped pommel: a gold teardrop holding a ruby.
    prof = [(0.0, -1.1), (0.04, -1.07)] + [(0.115 * math.sin(a), -0.97 - 0.09 * math.cos(a)) for a in np.linspace(0.6, 2.4, 6)] + \
           [(0.06, -0.86), (0.0, -0.86)]
    pieces.append(lathe(prof, gold, segs=12))
    for z in (1, -1):
        pieces.append(gem("brilliant", (0.045, 0.045, 0.03), chart=rc).rot([1, 0, 0], 0 if z > 0 else 180).move(0, -0.96, z * 0.105))
    return pieces, (0, -0.45, 0)


# =============================================================== 7. Glacier Cleaver (double axe)

def glacier_axe():
    gold = gold_chart(21)
    wood = Chart(0.5, 3.0, P.wood(WOOD_DARK, seed=22), "wood")
    wrap = Chart(0.5, 1.0, P.wrap(BLACK_LEATHER, pitch=0.14, seed=23), "wrap")
    H = 5.0
    yh = 4.1
    pieces = [lathe([(0.072, 0.12), (0.072, 2.0), (0.066, 4.55)], wood, segs=12)]
    pieces.append(wrap_grip(0.18, 1.35, 0.082, wrap, bulge=0.02))
    pieces += [band(0.2, 0.098, 0.07, gold), band(1.35, 0.098, 0.07, gold), band(2.2, 0.09, 0.05, gold),
               band(2.3, 0.09, 0.035, gold)]
    pieces.append(lathe([(0.0, 0.0), (0.06, 0.0), (0.1, 0.05), (0.1, 0.16), (0.08, 0.2), (0.0, 0.2)], gold, segs=8,
                        flat_sides=True))
    for z in (1, -1):
        pieces.append(gem("brilliant", (0.045, 0.045, 0.03), chart=gem_chart(CYAN, 9)).rot([1, 0, 0], 0 if z > 0 else 180)
                      .move(0, 0.1, z * 0.1))

    # Socket + spike.
    pieces.append(lathe([(0.1, yh - 0.42), (0.13, yh - 0.37), (0.13, yh + 0.37), (0.1, yh + 0.42)], gold, segs=8,
                        flat_sides=True, hard=(1, 2)))
    pieces.append(lathe([(0.0, yh + 0.4), (0.09, yh + 0.42), (0.07, yh + 0.55), (0.0, H)], gold, segs=4,
                        flat_sides=True, phase=math.pi / 4))
    cc = gem_chart(CYAN, 10)
    for z in (1, -1):
        pieces.append(gem("brilliant", (0.07, 0.07, 0.04), chart=cc).rot([1, 0, 0], 0 if z > 0 else 180).move(0, yh, z * 0.13))

    # Crescent blade (right); the left one is a mirror sharing the same texture.
    right = [(0.1, yh + 0.2)] + bez((0.1, yh + 0.2), (0.4, yh + 0.25), (0.75, yh + 0.45), (0.98, yh + 0.78), 10) + \
            bez((0.98, yh + 0.78), (1.15, yh + 0.35), (1.15, yh - 0.35), (0.98, yh - 0.78), 14) + \
            bez((0.98, yh - 0.78), (0.75, yh - 0.45), (0.4, yh - 0.25), (0.1, yh - 0.2), 10)
    right = right[::-1]

    def thick(x, y, d):
        tx = 0.012 + 0.07 * (1 - smooth(x, 0.25, 1.05))
        k = np.clip(d / 0.035, 0, 1)
        return 0.008 + (tx - 0.008) * (k * k * (3 - 2 * k))

    def axe_paint(nu, nv, su, sv):
        base = P.metal(FROST_STEEL, rough=0.22, var=0.15, seed=24, metal=0.8, brushed=False)(nu, nv, su, sv)
        u = (np.arange(nu) + 0.5) / nu
        v = (np.arange(nv) + 0.5) / nv
        strip = smooth(np.abs(v - 0.5), 0.1, 0.085)[:, None] * smooth(u, 0.18, 0.24)[None, :] * (1 - smooth(u, 0.72, 0.78))[None, :]
        base["color"] = base["color"] * (1 - 0.25 * strip[..., None]) + np.array([0.55, 0.72, 0.9]) * 0.25 * strip[..., None]
        LT = {k: np.swapaxes(a, 0, 1).copy() for k, a in base.items()}   # runes run along u
        engrave_runes(5, color=(0.35, 0.9, 1.0), strength=1.8, width=0.14, seed=25)(LT, nv, nu, sv, su)
        out = {k: np.swapaxes(a, 0, 1) for k, a in LT.items()}
        fade = (smooth(u, 0.2, 0.26) * (1 - smooth(u, 0.7, 0.76)))[None, :]
        out["emit"] = out["emit"] * fade[..., None]
        edge = smooth(u, 0.86, 0.97)[None, :]
        out["color"] = out["color"] * (1 - 0.25 * edge[..., None]) + 0.25 * edge[..., None]
        out["rough"] = out["rough"] * (1 - 0.5 * edge)
        return out

    head = pillow(right, 0.0, thick_fn=thick, painter=axe_paint, max_area=0.004)
    pieces += [head, mirror(head, 0)]
    return pieces, (0, 0.8, 0)


# =============================================================== 8. Duskforged Warhammer

def duskforged_hammer():
    gold = gold_chart(26)
    wood = Chart(0.5, 3.0, P.wood(WOOD_DARK, seed=27), "wood")
    wrap = Chart(0.5, 1.0, P.wrap(BLACK_LEATHER, pitch=0.13, seed=28), "wrap")
    steel = Chart(1.0, 1.0, P.metal(GUNMETAL, rough=0.36, var=0.3, seed=29, metal=0.85,
                                    engrave=engrave_filigree(density=1.8, depth=0.002, dirt=0.4)), "steel")
    yh = 4.2
    pieces = [lathe([(0.075, 0.15), (0.072, 2.4), (0.068, yh)], wood, segs=12)]
    pieces.append(wrap_grip(0.2, 1.3, 0.083, wrap, bulge=0.02))
    pieces += [band(0.22, 0.098, 0.07, gold), band(1.3, 0.098, 0.07, gold), band(1.42, 0.094, 0.04, gold),
               band(yh - 0.38, 0.094, 0.06, gold)]
    pieces.append(lathe([(0.0, 0.0), (0.05, 0.0), (0.1, 0.06), (0.1, 0.17), (0.08, 0.2), (0.0, 0.2)], gold, segs=8,
                        flat_sides=True))

    # Head: a chamfered block along X with a recessed waist for the gold band.
    a, b, Lh = 0.3, 0.27, 0.6
    R = 1 / 0.7071
    prof = [(0.0, -Lh), (0.82 * R, -Lh), (R, -Lh + 0.05), (R, -0.14), (0.9 * R, -0.12), (0.9 * R, 0.12),
            (R, 0.14), (R, Lh - 0.05), (0.82 * R, Lh), (0.0, Lh)]
    head = lathe(prof, steel, segs=4, phase=math.pi / 4, flat_sides=True, sx=a, sz=b)
    head.rot([0, 0, 1], -90).move(0, yh, 0)
    pieces.append(head)
    bandp = lathe([(0.0, -0.13), (0.95 * R, -0.13), (1.06 * R, -0.1), (1.06 * R, 0.1), (0.95 * R, 0.13), (0, 0.13)],
                  gold, segs=4, phase=math.pi / 4, flat_sides=True, sx=a, sz=b)
    pieces.append(bandp.rot([0, 0, 1], -90).move(0, yh, 0))
    for xe in (-Lh + 0.08, Lh - 0.08):
        rimp = lathe([(0.0, -0.05), (0.96 * R, -0.05), (1.05 * R, -0.03), (1.05 * R, 0.03), (0.96 * R, 0.05), (0, 0.05)],
                     gold, segs=4, phase=math.pi / 4, flat_sides=True, sx=a, sz=b)
        pieces.append(rimp.rot([0, 0, 1], -90).move(xe, yh, 0))
    vc = gem_chart(VIOLET, 11)
    for z in (1, -1):
        pieces.append(gem("brilliant", (0.075, 0.075, 0.045), chart=vc).rot([1, 0, 0], 0 if z > 0 else 180)
                      .move(0, yh, z * (b * 1.06 + 0.005)))
    # Striking face: a 2x2 grid of pyramid studs.
    for dy in (-0.13, 0.13):
        for dz in (-0.12, 0.12):
            pyr = lathe([(0.0, 0.0), (0.15, 0.0), (0.15, 0.025), (0.0, 0.16)], steel, segs=4, phase=math.pi / 4,
                        flat_sides=True, hard=(1, 2))
            pieces.append(pyr.rot([0, 0, 1], -90).move(Lh, yh + dy, dz))
    # Back face: an amethyst crystal cluster.
    ac = gem_chart(AMETHYST, 12)
    for ang, tilt, sc, oy, oz in ((0, 0, 1.0, 0, 0), (60, 30, 0.75, 0.1, 0.08), (160, 32, 0.7, -0.09, 0.1),
                                  (250, 28, 0.65, -0.08, -0.1), (320, 36, 0.55, 0.11, -0.08)):
        c = gem("crystal", (0.09 * sc, 0.24 * sc, 0.09 * sc), chart=ac).move(0, 0.19 * sc, 0)
        c.rot([0, 0, 1], 90)                                   # point along -X
        a_ = math.radians(ang)
        c.rot([0, 0, 1], tilt * math.cos(a_)).rot([0, 1, 0], tilt * math.sin(a_))
        pieces.append(c.move(-Lh + 0.03, yh + oy, oz))
    # Top spike.
    pieces.append(lathe([(0.0, yh + b), (0.07, yh + b), (0.05, yh + b + 0.06), (0.0, yh + b + 0.3)], gold, segs=4,
                        flat_sides=True, phase=math.pi / 4))
    return pieces, (0, 0.75, 0)


# =============================================================== 9. Royal Sapphire Scepter

def royal_scepter():
    gold = gold_chart(30)
    shaft_c = Chart(0.4, 2.0, P.metal(GOLD, rough=0.24, var=0.18, seed=31, metal=0.85,
                                      engrave=engrave_filigree(density=1.0, depth=0.003)), "shaft")
    wrap = Chart(0.5, 0.8, P.wrap(NAVY, pitch=0.12, seed=32), "wrap")
    pieces = [lathe([(0.06, 0.18), (0.058, 2.6), (0.052, 4.45)], shaft_c, segs=12)]
    pieces.append(wrap_grip(0.22, 1.05, 0.07, wrap, bulge=0.02))
    pieces += [band(0.24, 0.085, 0.06, gold), band(1.05, 0.085, 0.06, gold), band(1.15, 0.08, 0.03, gold)]
    pieces.append(lathe([(0.0, 0.0), (0.04, 0.0), (0.09, 0.08), (0.08, 0.19), (0.0, 0.19)], gold, segs=8, flat_sides=True))
    sc = gem_chart(SAPPHIRE, 13)
    pieces.append(gem("bipyramid", (0.05, 0.1, 0.05), chart=sc, n=6).move(0, -0.02, 0))
    # Knot on the shaft with an inlaid sapphire.
    pieces.append(lathe([(0.055, 2.5), (0.085, 2.56), (0.09, 2.64), (0.055, 2.72)], gold, segs=8, flat_sides=True))
    for z in (1, -1):
        pieces.append(gem("octa", (0.04, 0.055, 0.025), chart=sc).move(0, 2.61, z * 0.088))

    # Head: collar, crown ring, six prongs, big sapphire, small finial gem.
    pieces.append(lathe([(0.05, 4.4), (0.09, 4.45), (0.11, 4.55), (0.2, 4.62), (0.21, 4.68), (0.0, 4.66)], gold,
                        segs=12, hard=(3, 4)))
    pieces.append(band(4.68, 0.215, 0.07, gold, segs=16))
    prong = [(0, 0)] + bez((0.08, 0), (0.11, 0.18), (0.12, 0.3), (0.06, 0.48), 7) + [(0.03, 0.56), (0.0, 0.66)]
    prong = sym(prong)
    for k in range(6):
        p = pillow(prong, 0.028, 0.012, 0.025, chart=gold)
        p.deform(lambda v: v + np.column_stack([np.zeros(len(v)), np.zeros(len(v)), 0.25 * np.clip(v[:, 1], 0, None) ** 2]))
        p.rot([1, 0, 0], 12).move(0, 4.64, 0.2).rot([0, 1, 0], k * 60)
        pieces.append(p)
    pieces.append(gem("bipyramid", (0.17, 0.32, 0.17), chart=sc, n=8).rot([0, 1, 0], 22.5).move(0, 5.0, 0))
    pieces.append(gem("octa", (0.06, 0.08, 0.06), chart=gem_chart(SAPPHIRE, 14)).move(0, 5.42, 0))
    return pieces, (0, 0.62, 0)


# =============================================================== 10. Arcane Amethyst Staff

def amethyst_staff():
    gold = gold_chart(33)
    wood = Chart(0.5, 3.0, P.wood(WOOD_DARK, seed=34, dark=0.5), "wood")
    wrap = Chart(0.5, 1.0, P.wrap(BLACK_LEATHER, pitch=0.13, seed=35), "wrap")
    top = 4.95

    def gnarl(r, y, th):
        return r * (1 + 0.06 * np.sin(th * 3 + y * 2.3) * np.sin(y * 3.1) + 0.05 * np.exp(-((y - 3.3) / 0.06) ** 2)
                    + 0.05 * np.exp(-((y - 2.2) / 0.05) ** 2) * np.cos(th - 1))

    ys = np.linspace(0.15, top, 26)
    pieces = [lathe([(0.078 - 0.012 * (y / top), y) for y in ys], wood, segs=12, radius_fn=gnarl)]
    pieces.append(wrap_grip(1.6, 2.6, 0.082, wrap, bulge=0.03))
    pieces += [band(1.6, 0.097, 0.07, gold), band(2.6, 0.097, 0.07, gold), band(0.5, 0.09, 0.05, gold)]
    pieces.append(lathe([(0.0, -0.05), (0.04, 0.02), (0.085, 0.12), (0.09, 0.2), (0.0, 0.2)], gold, segs=8, flat_sides=True))
    # Head: collar, two crossing teardrop loops forming a cage, crystal inside, leaves at the base.
    pieces.append(lathe([(0.06, top - 0.1), (0.1, top - 0.03), (0.13, top + 0.06), (0.09, top + 0.1), (0.0, top + 0.1)],
                        gold, segs=12, hard=(2,)))
    t = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    loop = np.column_stack([0.27 * np.sin(t) * (1 - 0.45 * (1 + np.cos(t)) / 2) ** 1.0,
                            top + 0.55 - 0.48 * np.cos(t), np.zeros_like(t)])
    for ang in (0, 90):
        c = tube(loop, 0.024, chart=gold, segs=8, up=(0, 0, 1), closed=True, aspect=1.3, superellipse=3)
        pieces.append(c.rot([0, 1, 0], ang) if ang else c)
    pieces.append(lathe([(0.0, top + 1.0), (0.05, top + 1.02), (0.035, top + 1.07), (0.0, top + 1.16)], gold, segs=8,
                        flat_sides=True))
    ac = gem_chart(AMETHYST, 15)
    pieces.append(gem("bipyramid", (0.13, 0.3, 0.13), chart=ac, n=6).rot([0, 1, 0], 30).move(0, top + 0.5, 0))
    leaf = sym([(0, 0), (0.06, 0.05), (0.07, 0.15), (0.0, 0.3)])
    for k in range(4):
        p = pillow(leaf, 0.02, 0.008, 0.02, chart=gold)
        p.rot([1, 0, 0], 35).move(0, top + 0.04, 0.1).rot([0, 1, 0], 45 + k * 90)
        pieces.append(p)
    return pieces, (0, 2.1, 0)


# =============================================================== bows

def _bow(limb_painter, grip_color, tip_gem, half=2.35, bend=0.42, recurve=0.24, crystals=None, seed=0):
    gold = gold_chart(seed + 1)
    wrap = Chart(0.5, 0.6, P.wrap(grip_color, pitch=0.09, seed=seed + 2), "wrap")
    string_c = Chart(0.05, 1.0, P.flat((0.92, 0.9, 0.82), rough=0.7), "string")
    yy = np.linspace(-half, half, 61)
    k = np.abs(yy) / half
    x = bend * k ** 1.8 - recurve * np.clip((k - 0.76) / 0.24, 0, 1) ** 2
    path = np.column_stack([x, yy, np.zeros_like(yy)])
    width = lambda t: 0.055 * (1 - 0.45 * abs(2 * t - 1) ** 1.2)          # half-width along Z
    thick = lambda t: 0.034 * (1 - 0.35 * abs(2 * t - 1))                 # half-thickness in-plane
    limb = tube(path, thick, painter=limb_painter, segs=10, up=(0, 0, 1), aspect=lambda t: width(t) / thick(t),
                superellipse=2.6, name="limb")
    pieces = [limb]
    # Riser grip.
    pieces.append(lathe([(0.055, -0.3), (0.062, -0.2), (0.064, 0.0), (0.062, 0.2), (0.055, 0.3)], wrap, segs=12,
                        sx=1.0, sz=1.2))
    pieces += [band(-0.31, 0.07, 0.05, gold), band(0.31, 0.07, 0.05, gold)]
    # Tip caps with gems + string.
    for sgn in (1, -1):
        tip = path[-1] if sgn > 0 else path[0]
        cap = lathe([(0.0, -0.02), (0.045, 0.0), (0.04, 0.09), (0.0, 0.16)], gold, segs=8, flat_sides=True)
        if sgn < 0:
            cap.rot([1, 0, 0], 180)
        pieces.append(cap.move(tip[0], tip[1] - sgn * 0.06, 0))
        pieces.append(gem("brilliant", (0.03, 0.03, 0.02), chart=tip_gem).move(tip[0], tip[1] - sgn * 0.02, 0.04))
    a, b = path[2], path[-3]
    s_path = np.linspace(a, b, 2) + [0.0, 0, 0]
    pieces.append(tube(s_path, 0.009, chart=string_c, segs=5, up=(0, 0, 1), cap=False))
    if crystals is not None:
        ccol = crystals
        for t, scl in ((0.18, 1.0), (0.3, 0.7), (0.7, 0.7), (0.82, 1.0)):
            i = int(t * (len(path) - 1))
            p = path[i]
            tang = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
            ang = math.degrees(math.atan2(tang[1], tang[0]))
            c = gem("crystal", (0.035 * scl, 0.12 * scl, 0.035 * scl), chart=ccol).move(0, 0.1 * scl, 0)
            c.rot([0, 0, 1], 90).rot([0, 0, 1], ang - 90)    # stick out of the back of the limb
            pieces.append(c.move(p[0] - 0.02, p[1], 0))
    return pieces, (0, 0, 0)


def glacier_bow():
    return _bow(P.ice(seed=40, core=False), NAVY, gem_chart(CYAN, 41), half=2.4, bend=0.45, recurve=0.26,
                crystals=Chart(0.3, 0.04, P.gem(CYAN, 42), "crystal"), seed=40)


def hunters_recurve():
    def laminated(nu, nv, su, sv):
        L = P.wood(WOOD_MID, seed=50, dark=0.35)(nu, nv, su, sv)
        u = (np.arange(nu) + 0.5) / nu
        stripe = (np.abs(((u * 4) % 1) - 0.5) < 0.08)[None, :, None]
        L["color"] = np.where(stripe, L["color"] * 0.45, L["color"])
        return L
    return _bow(laminated, CRIMSON, gem_chart(RUBY, 51), half=2.15, bend=0.4, recurve=0.28, seed=50)


WEAPONS = {
    "BronzeGladius": bronze_gladius,
    "SunsteelFalchion": sunsteel_falchion,
    "Frostbrand": frostbrand,
    "TidecrystalShard": tidecrystal_shard,
    "Voidrender": voidrender,
    "Emberfang": emberfang,
    "GlacierCleaver": glacier_axe,
    "DuskforgedWarhammer": duskforged_hammer,
    "RoyalSapphireScepter": royal_scepter,
    "ArcaneAmethystStaff": amethyst_staff,
    "GlacierBow": glacier_bow,
    "HuntersRecurveBow": hunters_recurve,
}
