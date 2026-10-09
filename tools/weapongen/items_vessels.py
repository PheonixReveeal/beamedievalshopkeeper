"""Potions, elixirs and goblets. Origin = bottom centre; everything stands on Y = 0."""
import math

import numpy as np

from core import Chart, P, gem, lathe, layers, noise, pillow, smooth, tube, cylinder_wrap, engrave_runes, \
    engrave_filigree
from weapons import (AMETHYST, CRIMSON, CYAN, GOLD, PALE_GOLD, RUBY, SAPPHIRE, bez, gem_chart, gold_chart, sym)

SILVER = (0.86, 0.88, 0.92)
PEWTER = (0.62, 0.64, 0.66)
BRASS = (0.88, 0.66, 0.34)
IRON = (0.36, 0.37, 0.4)
EMERALD = (0.15, 0.85, 0.4)
AMBER = (1.0, 0.62, 0.12)


def silver_chart(seed=0, color=SILVER, rough=0.2, ornate=False):
    return Chart(0.6, 0.6, P.metal(color, rough=rough, var=0.15, seed=seed, metal=0.9,
                                   engrave=engrave_filigree(density=2.5, dirt=0.25) if ornate else None), "silver")


def engrave_rings_y(count=3, width=0.006, depth=0.002):
    """Simple turned rings for plain pewter."""
    def apply(L, nu, nv, su, sv):
        v = (np.arange(nv) + 0.5) / nv
        g = sum(np.exp(-((v - p) / (width / sv)) ** 2) for p in np.linspace(0.62, 0.8, count))
        L["height"] -= depth * g[:, None]
        L["color"] *= (1 - 0.3 * g)[:, None, None]
    return apply


def arc_fraction(profile, y):
    """Fraction of a lathe profile's arc length at which it first reaches height y (for liquid fill)."""
    p = np.asarray(profile, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    arc = np.r_[0, np.cumsum(seg)]
    for i in range(len(p) - 1):
        (r0, y0), (r1, y1) = p[i], p[i + 1]
        if (y0 - y) * (y1 - y) <= 0 and y1 != y0:
            t = (y - y0) / (y1 - y0)
            return (arc[i] + t * seg[i]) / arc[-1]
    return 1.0


def outer_r(prof, y):
    """Outer radius of a goblet profile at height y (the cup, not the stem)."""
    p = np.asarray(prof, float)
    best = None
    for i in range(int(np.argmax(p[:, 1]))):
        (r0, y0), (r1, y1) = p[i], p[i + 1]
        if (y0 - y) * (y1 - y) <= 0 and y1 != y0:
            best = r0 + (r1 - r0) * (y - y0) / (y1 - y0)
    return best


def crescent(R, r, dx, res=10):
    from shapely.geometry import Point
    shape = Point(0, 0).buffer(R, res).difference(Point(dx, 0).buffer(r, res))
    return list(shape.exterior.coords)[:-1]


def sphere_arc(cx, cy, R, a0, a1, n):
    """Points on a circle (r, y) from polar angle a0 to a1 measured from straight down."""
    return [(cx + R * math.sin(a), cy - R * math.cos(a)) for a in np.linspace(a0, a1, n)]


def liquid_surface(color, glow=0.5, sparkle=0.0, seed=0):
    color = np.asarray(color, float)

    def paint(nu, nv, su, sv):
        vv, uu = np.mgrid[0:nv, 0:nu]
        u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
        n = noise(nv, nu, nu * 0.12, octaves=3, seed=seed)
        sw = 0.5 + 0.5 * np.sin(u * 2 * math.pi * 2 + v * 8 + n * 5)
        col = color * (0.7 + 0.45 * sw * v)[..., None]
        emit = color * glow * (0.5 + 0.5 * v)[..., None]
        if sparkle:
            r = np.random.default_rng(seed)
            sp = np.zeros((nv, nu))
            idx = r.integers(0, nv * nu, int(sparkle * 60))
            sp.flat[idx] = 1
            from scipy.ndimage import gaussian_filter
            sp = np.clip(gaussian_filter(sp, 0.8) * 5, 0, 1)
            col = np.clip(col + sp[..., None], 0, 1)
            emit += sp[..., None]
        return layers(nu, nv, col, 0.0, 0.04, emit=emit)
    return paint


def bottle(profile, fill_y, segs=20, radius_fn=None, flat_sides=False, sx=1.0, sz=1.0, **potion):
    v = arc_fraction(profile, fill_y)
    return lathe(profile, painter=P.potion(fill=v, **potion), segs=segs, radius_fn=radius_fn, flat_sides=flat_sides,
                 sx=sx, sz=sz, name="glass")


def cork(y0, y1, r0, r1, segs=14, seed=0):
    return lathe([(0, y0), (r0, y0), (r1 * 1.02, y1 - 0.03), (r1 * 0.9, y1), (0, y1 + 0.005)],
                 painter=P.cork(seed), segs=segs, hard=(1,), name="cork")


def twine(y, r, color=(0.8, 0.7, 0.5), turns=2, seed=0):
    t = np.linspace(0, 2 * math.pi * turns, 40 * turns)
    path = np.column_stack([r * np.sin(t), y + 0.012 * t / (2 * math.pi), -r * np.cos(t)])
    return tube(path, 0.009, painter=P.flat(color, rough=0.9), segs=5, up=(0, 1, 0), name="twine")


def ring_band(y, r, h, chart, segs=20):
    return lathe([(r * 0.92, y - h / 2), (r, y - h / 2 + h * 0.15), (r, y + h / 2 - h * 0.15), (r * 0.92, y + h / 2)],
                 chart, segs=segs, hard=(1, 2))


def label_parchment(symbol="cross", ink=(0.6, 0.08, 0.08), paper=(0.92, 0.85, 0.66)):
    from PIL import Image, ImageDraw

    def draw(nu, nv, u, v, a, b):
        out = np.zeros((nv, nu, 4))
        band = (v > a) & (v < b)
        # Label covers the front half (u 0.55..0.95) of the bottle.
        m = band & (u > 0.55) & (u < 0.95)
        out[..., :3] = paper
        out[..., 3] = m
        ys, xs = np.where(m)
        if len(xs):
            img = Image.new("L", (nu, nv), 0)
            d = ImageDraw.Draw(img)
            cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
            s = min(xs.max() - xs.min(), ys.max() - ys.min()) * 0.32
            if symbol == "cross":
                d.rectangle([cx - s * 0.3, cy - s, cx + s * 0.3, cy + s], fill=255)
                d.rectangle([cx - s, cy - s * 0.3, cx + s, cy + s * 0.3], fill=255)
            d.rectangle([xs.min() + 3, ys.min() + 3, xs.max() - 3, ys.max() - 3], outline=200, width=2)
            ink_m = np.asarray(img, float) / 255
            out[..., :3] = out[..., :3] * (1 - ink_m[..., None]) + np.asarray(ink) * ink_m[..., None]
        n = np.random.default_rng(1).random((nv, nu))
        out[..., :3] *= (0.9 + 0.1 * n)[..., None]
        return out
    return draw


# =============================================================== POTIONS

def potion():
    prof = [(0.0, 0.0), (0.12, 0.004)] + sphere_arc(0, 0.36, 0.34, 0.45, 2.75, 14) + \
           [(0.085, 0.66), (0.08, 0.84), (0.1, 0.86), (0.1, 0.9), (0.07, 0.905)]
    pieces = [bottle(prof, 0.42, liquid=(0.95, 0.12, 0.18), seed=1)]
    pieces.append(cork(0.84, 1.0, 0.07, 0.085, seed=2))
    pieces.append(twine(0.7, 0.088, seed=3))
    return pieces


def healers_draught():
    def rsq(r, y, th):  # rounded-square cross-section
        n = 5.0
        return r / (np.abs(np.cos(th)) ** n + np.abs(np.sin(th)) ** n) ** (1 / n)

    prof = [(0.0, 0.0), (0.24, 0.0), (0.27, 0.03), (0.28, 0.12), (0.28, 0.5), (0.25, 0.58), (0.16, 0.65),
            (0.09, 0.69), (0.08, 0.8), (0.1, 0.82), (0.1, 0.86), (0.07, 0.865)]
    pieces = [bottle(prof, 0.42, segs=28, radius_fn=rsq, liquid=(0.3, 0.92, 0.42), glow=0.4, seed=4,
                     label=label_parchment("cross", ink=(0.75, 0.1, 0.1)),
                     label_band=(arc_fraction(prof, 0.16), arc_fraction(prof, 0.4)))]
    pieces.append(cork(0.8, 0.95, 0.07, 0.082, seed=5))
    # Red wax seal over the cork.
    pieces.append(lathe([(0.0, 0.93), (0.095, 0.93), (0.1, 0.96), (0.07, 0.99), (0.0, 1.0)],
                        painter=P.enamel((0.7, 0.06, 0.08), rough=0.35), segs=14, name="wax"))
    pieces.append(twine(0.71, 0.092, seed=6))
    leaf = sym([(0, 0), (0.035, 0.03), (0.04, 0.08), (0, 0.13)])
    lc = Chart(0.1, 0.15, P.feather((0.2, 0.6, 0.18), tip=(0.4, 0.8, 0.25), barb=0.012, seed=7), "leaf")
    for ang in (-35, 25):
        p = pillow(leaf, 0.008, 0.003, 0.01, chart=lc)
        pieces.append(p.rot([0, 0, 1], ang).move(0.0, 0.7, -0.1).rot([0, 1, 0], 20 if ang < 0 else -10))
    return pieces


def swiftfoot_tonic():
    def ribs(r, y, th):
        return r * (1 + 0.05 * np.cos(6 * th + y * 9) ** 2)

    prof = [(0.0, 0.0), (0.14, 0.0), (0.17, 0.04), (0.17, 0.75), (0.13, 0.88), (0.065, 0.97), (0.06, 1.12),
            (0.075, 1.14), (0.06, 1.15)]
    pieces = [bottle(prof, 0.62, segs=30, radius_fn=ribs, liquid=(0.15, 0.85, 0.9), glow=0.55, swirl=0.6, seed=8)]
    gold = gold_chart(9)
    pieces.append(lathe([(0.0, 1.08), (0.085, 1.08), (0.09, 1.16), (0.07, 1.22), (0.03, 1.25), (0.0, 1.26)], gold,
                        segs=14, hard=(1,)))
    pieces.append(ring_band(0.9, 0.12, 0.03, gold))
    wing = [(0, 0), (0.06, 0.02), (0.14, 0.08), (0.2, 0.17), (0.15, 0.14), (0.16, 0.19), (0.11, 0.14), (0.11, 0.18),
            (0.06, 0.11), (0.02, 0.08)]
    for side in (1, -1):
        w = pillow([(side * x, y) for x, y in wing], 0.012, 0.004, 0.01, chart=gold).scale(1.2)
        pieces.append(w.rot([0, 0, 1], -side * 15).rot([0, 1, 0], side * 25).move(side * 0.07, 1.1, 0.01))
    return pieces


def giants_strength_brew():
    prof = [(0.0, 0.0), (0.3, 0.0), (0.36, 0.04)] + sphere_arc(0, 0.42, 0.43, 0.9, 2.45, 12) + \
           [(0.17, 0.86), (0.15, 0.95), (0.18, 0.97), (0.18, 1.01), (0.13, 1.015)]
    pieces = [bottle(prof, 0.55, segs=24, liquid=(1.0, 0.45, 0.08), glow=0.5, seed=10, swirl=0.4)]
    iron = Chart(0.6, 0.6, P.metal(IRON, rough=0.45, var=0.3, seed=11), "iron")
    pieces += [ring_band(0.18, 0.415, 0.06, iron, segs=24), ring_band(0.62, 0.412, 0.06, iron, segs=24)]
    # Rivets on the bands.
    for k in range(8):
        a = k * math.pi / 4
        for y, r in ((0.18, 0.44), (0.62, 0.437)):
            pieces.append(lathe([(0, 0), (0.018, 0), (0.014, 0.012), (0, 0.016)], iron, segs=6)
                          .rot([1, 0, 0], -90).move(0, y, -r).rot([0, 1, 0], math.degrees(a)))
    pieces.append(cork(0.94, 1.12, 0.13, 0.155, seed=12))
    # Thick iron ring handle on the side.
    t = np.linspace(0.15 * math.pi, 1.85 * math.pi, 30)
    path = np.column_stack([0.38 + 0.12 * np.sin(t), 0.62 + 0.13 * np.cos(t), np.zeros_like(t)])
    pieces.append(tube(path, 0.022, chart=iron, segs=8, up=(0, 0, 1)))
    return pieces


def phoenix_tears():
    # Teardrop body: round at the bottom, tapering into the neck.
    body = [(0.0, 0.0), (0.12, 0.01)] + sphere_arc(0, 0.28, 0.27, 0.5, 1.9, 9) + \
           [(0.2, 0.55), (0.13, 0.7), (0.075, 0.82), (0.06, 0.9), (0.075, 0.92), (0.055, 0.925)]
    pieces = [bottle(body, 0.4, segs=22, liquid=(1.0, 0.55, 0.1), deep=(0.85, 0.15, 0.05), glow=0.9, sparkle=1.5,
                     swirl=0.5, seed=13)]
    gold = gold_chart(14)
    pieces.append(ring_band(0.88, 0.075, 0.04, gold, segs=16))
    pieces.append(lathe([(0.0, 0.9), (0.08, 0.9), (0.085, 0.95), (0.05, 0.98), (0.0, 0.985)], gold, segs=14))
    flame = sym([(0, 0), (0.05, 0.03), (0.06, 0.09), (0.03, 0.13), (0.04, 0.18), (0.012, 0.15), (0.0, 0.26)])
    fc = Chart(0.15, 0.3, P.feather((1.0, 0.45, 0.05), tip=(1.0, 0.85, 0.3), barb=0.03, glow=(1.0, 0.5, 0.1), seed=15),
               "flame")
    for ang in (0, 90):
        pieces.append(pillow(flame, 0.015, 0.004, 0.01, chart=fc).rot([0, 1, 0], ang).move(0, 0.97, 0))
    # Gold phoenix wings hugging the shoulders.
    wing = [(0.0, 0.0), (0.05, 0.06), (0.12, 0.1), (0.2, 0.17), (0.17, 0.1), (0.22, 0.12), (0.18, 0.05), (0.22, 0.04),
            (0.15, -0.01), (0.06, -0.03)]
    for side in (1, -1):
        w = pillow([(side * x, y) for x, y in wing], 0.012, 0.004, 0.01, chart=gold)
        pieces.append(w.scale(1.25).rot([0, 0, 1], side * 10).rot([0, 1, 0], side * 20).move(side * 0.2, 0.36, 0.02))
    return pieces


# =============================================================== ELIXIRS

def elixir():
    prof = [(0.0, 0.0), (0.1, 0.0), (0.12, 0.02), (0.12, 0.95), (0.1, 1.0), (0.07, 1.03), (0.065, 1.12),
            (0.05, 1.125)]
    pieces = [bottle(prof, 0.72, segs=18, liquid=(0.62, 0.2, 0.95), glow=0.6, seed=20, swirl=0.4)]
    silver = silver_chart(21)
    pieces.append(lathe([(0.0, 1.08), (0.08, 1.08), (0.085, 1.2), (0.06, 1.23), (0.0, 1.235)], silver, segs=14, hard=(1,)))
    pieces.append(ring_band(0.06, 0.128, 0.06, silver))
    pieces.append(ring_band(0.97, 0.125, 0.035, silver))
    t = np.linspace(0, 2 * math.pi, 20)
    pieces.append(tube(np.column_stack([np.zeros_like(t), 1.28 + 0.045 * np.cos(t), 0.045 * np.sin(t)]), 0.008,
                       chart=silver, segs=6, closed=True, up=(1, 0, 0)))
    return pieces


def elixir_of_clarity():
    prof = [(0.0, 0.0), (0.16, 0.0), (0.22, 0.08), (0.24, 0.35), (0.2, 0.62), (0.09, 0.78), (0.07, 0.86),
            (0.085, 0.88), (0.06, 0.885)]
    pieces = [bottle(prof, 0.5, segs=8, flat_sides=True, liquid=(0.55, 0.85, 1.0), glass=(0.82, 0.92, 0.98),
                     glow=0.5, seed=22)]
    silver = silver_chart(23, ornate=True)
    pieces.append(ring_band(0.84, 0.08, 0.04, silver, segs=8))
    pieces.append(lathe([(0.0, 0.86), (0.07, 0.86), (0.06, 0.9), (0.0, 0.9)], silver, segs=8))
    pieces.append(gem("brilliant", (0.13, 0.13, 0.13), chart=gem_chart((0.75, 0.95, 1.0), 24), n=8)
                  .rot([1, 0, 0], -90).move(0, 1.0, 0))
    return pieces


def moonwell_elixir():
    prof = [(0.0, 0.0), (0.16, 0.0)] + sphere_arc(0, 0.32, 0.31, 0.6, 2.6, 12) + \
           [(0.075, 0.66), (0.07, 0.8), (0.085, 0.82), (0.06, 0.825)]
    pieces = [bottle(prof, 0.5, segs=22, liquid=(0.2, 0.35, 1.0), deep=(0.05, 0.05, 0.3), glow=0.7, sparkle=2.0,
                     swirl=0.5, seed=25)]
    silver = silver_chart(26, ornate=True)
    pieces.append(ring_band(0.78, 0.082, 0.05, silver))
    pieces.append(lathe([(0.0, 0.8), (0.075, 0.8), (0.07, 0.86), (0.0, 0.86)], silver, segs=14))
    # Crescent moon stopper.
    moon = pillow(crescent(0.15, 0.12, 0.07), 0.02, 0.008, 0.015, chart=silver)
    pieces.append(moon.rot([0, 0, 1], 90).move(0, 1.0, 0))
    pieces.append(gem("cabochon", (0.055, 0.055, 0.025), painter=P.moonstone(seed=27)).rot([0, 1, 0], 180).move(0, 0.3, -0.3))
    return pieces


def elixir_of_ages():
    prof = [(0.0, 0.0), (0.2, 0.0), (0.23, 0.06), (0.22, 0.22), (0.14, 0.36), (0.06, 0.44), (0.14, 0.52),
            (0.22, 0.66), (0.23, 0.82), (0.16, 0.9), (0.07, 0.94), (0.06, 1.0), (0.075, 1.02), (0.05, 1.025)]
    pieces = [bottle(prof, 0.3, segs=22, liquid=(1.0, 0.72, 0.2), deep=(0.55, 0.25, 0.02), glow=0.65,
                     sparkle=1.0, seed=28)]
    gold = gold_chart(29, ornate=True)
    pieces.append(lathe([(0.0, -0.03), (0.28, -0.03), (0.3, 0.0), (0.27, 0.03), (0.0, 0.03)], gold, segs=24, hard=(1, 3)))
    pieces.append(lathe([(0.0, 0.86), (0.27, 0.86), (0.29, 0.89), (0.25, 0.91), (0.07, 0.92), (0.0, 0.92)], gold,
                        segs=24, hard=(1, 3)))
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.3
        y = np.linspace(0.02, 0.87, 12)
        path = np.column_stack([0.27 * np.sin(a) * np.ones_like(y), y, -0.27 * np.cos(a) * np.ones_like(y)])
        pieces.append(tube(path, lambda tt: 0.016 + 0.006 * math.sin(tt * math.pi * 3) ** 2, chart=gold, segs=8,
                           up=(1, 0, 0)))
    gear = lambda r, y, th: r * (1 + 0.08 * (np.cos(12 * th) > 0.3))
    pieces.append(lathe([(0.0, 0.98), (0.09, 0.98), (0.095, 1.06), (0.06, 1.1), (0.0, 1.11)], gold, segs=48, hard=(1,),
                        radius_fn=gear))
    pieces.append(gem("brilliant", (0.04, 0.04, 0.025), chart=gem_chart(AMBER, 30)).rot([1, 0, 0], -90).move(0, 1.11, 0))
    return pieces


def starlight_elixir():
    def star(r, y, th):
        return r * (0.88 + 0.12 * np.cos(5 * th))

    prof = [(0.0, 0.0), (0.2, 0.0), (0.22, 0.04), (0.22, 0.7), (0.15, 0.85), (0.07, 0.95), (0.06, 1.05),
            (0.075, 1.07), (0.05, 1.075)]
    pieces = [bottle(prof, 0.62, segs=40, radius_fn=star, liquid=(0.5, 0.3, 1.0), deep=(0.05, 0.03, 0.25),
                     glow=0.7, sparkle=3.0, swirl=0.6, seed=31)]
    silver = silver_chart(32, ornate=True)
    pieces.append(lathe([(0.0, -0.02), (0.24, -0.02), (0.25, 0.03), (0.22, 0.06), (0.0, 0.06)], silver, segs=40,
                        radius_fn=star, hard=(1,)))
    pieces.append(ring_band(1.03, 0.08, 0.05, silver))
    pts = []
    for k in range(10):
        a = k * math.pi / 5
        r = 0.16 if k % 2 == 0 else 0.07
        pts.append((r * math.sin(a), r * math.cos(a)))
    pieces.append(pillow(pts, 0.03, 0.01, 0.03, chart=silver).move(0, 1.22, 0))
    pieces.append(gem("brilliant", (0.035, 0.035, 0.02), chart=gem_chart((0.8, 0.85, 1.0), 33)).move(0, 1.22, 0.035))
    return pieces


# =============================================================== GOBLETS

def goblet_profile(foot_r, foot_h, stem_r, knop, cup_y, cup_r, top_y, rim_r, wall=0.025, base_flat=0.02,
                   inner_bottom=None, flare=1.0, belly=0.0, n_cup=8):
    """A goblet profile (outer + inner surface). knop = (y, r) bulge on the stem."""
    ib = inner_bottom if inner_bottom is not None else cup_y + 0.08
    prof = [(0.0, 0.0), (foot_r - 0.02, 0.0), (foot_r, base_flat), (foot_r * 0.8, foot_h * 0.6), (stem_r * 1.4, foot_h)]
    ky, kr = knop
    prof += [(stem_r, foot_h + (ky - foot_h) * 0.5), (kr, ky - 0.03), (kr, ky + 0.03), (stem_r, ky + 0.06),
             (stem_r * 1.3, cup_y - 0.02)]
    for t in np.linspace(0, 1, n_cup):
        r = cup_r * (math.sin(t * math.pi / 2) ** 0.6) + (rim_r - cup_r) * t ** 2 + belly * math.sin(t * math.pi)
        prof.append((max(r, stem_r * 1.3), cup_y + (top_y - cup_y) * t ** flare))
    prof += [(rim_r + 0.008, top_y + 0.01), (rim_r - wall, top_y + 0.012)]
    for t in np.linspace(1, 0, n_cup - 2):
        r = (cup_r * (math.sin(t * math.pi / 2) ** 0.6) + (rim_r - cup_r) * t ** 2 + belly * math.sin(t * math.pi)) - wall
        prof.append((max(r, 0.02), ib + (top_y - ib) * t ** flare))
    prof.append((0.0, ib))
    return prof


def liquid_disc(prof, y, color, glow=0.4, sparkle=0.0, seed=0, segs=24):
    """Liquid surface inside a goblet profile at height y (radius from the inner wall)."""
    p = np.asarray(prof)
    inner = p[np.argmax(p[:, 1]) + 1:]
    r = np.interp(y, inner[::-1, 1], inner[::-1, 0]) - 0.004
    return lathe([(r, y), (r * 0.5, y + 0.001), (0.0, y)], painter=liquid_surface(color, glow, sparkle, seed),
                 segs=segs, name="liquid")


def goblet():
    prof = goblet_profile(0.26, 0.06, 0.04, (0.3, 0.07), 0.48, 0.25, 0.95, 0.28)
    return [lathe(prof, painter=P.metal((0.74, 0.75, 0.76), rough=0.4, var=0.2, seed=40, metal=0.8,
                                        engrave=engrave_rings_y()), segs=24, hard=(2,))]


def feast_goblet():
    brass = Chart(0.6, 0.6, P.metal(BRASS, rough=0.3, var=0.2, seed=41, metal=0.85), "brass")
    prof = goblet_profile(0.32, 0.07, 0.06, (0.22, 0.1), 0.34, 0.34, 1.0, 0.38, belly=0.03)
    pieces = [lathe(prof, painter=P.metal(BRASS, rough=0.3, var=0.2, seed=41, metal=0.85,
                                          engrave=engrave_filigree(density=3.0, dirt=0.3)), segs=28, hard=(2,))]
    for y in (0.6, 0.86):
        pieces.append(ring_band(y, outer_r(prof, y) + 0.004, 0.035, brass, segs=28))
    for k in range(8):
        pieces.append(lathe([(0, 0), (0.018, 0), (0.014, 0.012), (0, 0.016)], brass, segs=6).rot([1, 0, 0], -90)
                      .move(0, 0.73, -outer_r(prof, 0.73)).rot([0, 1, 0], k * 45))
    pieces.append(liquid_disc(prof, 0.9, (0.55, 0.05, 0.12), glow=0.15, seed=42))
    return pieces


def moonlit_goblet():
    silver = silver_chart(43)
    prof = goblet_profile(0.24, 0.05, 0.035, (0.42, 0.07), 0.7, 0.22, 1.25, 0.27, flare=0.9)
    pieces = [lathe(prof, painter=P.metal(SILVER, rough=0.18, var=0.15, seed=43, metal=0.9,
                                          engrave=engrave_filigree(density=3.0, dirt=0.25)), segs=24, hard=(2,))]
    enamel = Chart(0.2, 0.2, P.enamel((0.2, 0.4, 0.95), rough=0.12, glow=0.2), "enamel")
    pieces.append(liquid_disc(prof, 1.18, (0.4, 0.75, 1.0), glow=0.9, sparkle=2, seed=44))
    bc = gem_chart((0.45, 0.7, 1.0), 45)
    for k in range(3):
        a = k * 120
        moon = pillow(crescent(0.075, 0.06, 0.035), 0.008, 0.003, 0.008, chart=enamel).rot([0, 0, 1], 90)
        r = outer_r(prof, 0.98)
        pieces.append(moon.move(0, 0.98, 0).deform(cylinder_wrap(r)).rot([0, 1, 0], a))
        pieces.append(gem("brilliant", (0.022, 0.022, 0.015), chart=bc).rot([0, 1, 0], 180).move(0, 0.98, -r - 0.012)
                      .rot([0, 1, 0], a + 0))
    return pieces


def royal_chalice():
    gold = gold_chart(46)
    prof = goblet_profile(0.3, 0.08, 0.045, (0.3, 0.1), 0.5, 0.27, 1.05, 0.32)
    twist = lambda r, y, th: r * (1 + 0.12 * np.cos(4 * th + y * 30) ** 4 * ((y > 0.1) & (y < 0.48)))
    pieces = [lathe(prof, painter=P.metal(GOLD, rough=0.22, var=0.2, seed=46, metal=0.85,
                                          engrave=engrave_filigree(density=3.0, dirt=0.25)), segs=32, hard=(2,),
                    radius_fn=twist)]
    pieces.append(liquid_disc(prof, 0.98, (0.55, 0.04, 0.1), glow=0.15, seed=47))
    gems = [gem_chart(RUBY, 48), gem_chart(SAPPHIRE, 49)]
    y = 0.78
    r = outer_r(prof, y)
    for k in range(6):
        pieces.append(gem("brilliant", (0.04, 0.04, 0.025), chart=gems[k % 2]).rot([0, 1, 0], 180)
                      .move(0, y, -r - 0.01).rot([0, 1, 0], k * 60))
    pieces.append(ring_band(y, r + 0.008, 0.11, gold, segs=32))
    return pieces


def grail_of_ages():
    gold = gold_chart(50)
    prof = goblet_profile(0.34, 0.09, 0.055, (0.28, 0.1), 0.48, 0.3, 1.0, 0.35, belly=0.04)
    pieces = [lathe(prof, painter=P.metal((0.9, 0.7, 0.35), rough=0.3, var=0.3, seed=50, metal=0.85,
                                          engrave=engrave_filigree(density=2.6, dirt=0.4)), segs=32, hard=(2,))]
    pieces.append(liquid_disc(prof, 0.94, (1.0, 0.78, 0.25), glow=1.0, sparkle=3, seed=51))
    # Rune band (glowing) around the cup.
    y = 0.72
    r = outer_r(prof, y)

    def runes(nu, nv, su, sv):
        L = P.metal(GOLD, rough=0.25, var=0.2, seed=52, metal=0.85)(nu, nv, su, sv)
        LT = {k: np.swapaxes(a, 0, 1).copy() for k, a in L.items()}
        engrave_runes(14, color=(1.0, 0.75, 0.3), strength=1.6, width=0.7, seed=53)(LT, nv, nu, sv, su)
        return {k: np.swapaxes(a, 0, 1) for k, a in LT.items()}
    pieces.append(lathe([(r + 0.005, y - 0.05), (r + 0.015, y - 0.04), (r + 0.015, y + 0.04), (r + 0.005, y + 0.05)],
                        painter=runes, segs=32, hard=(1, 2), name="runes"))
    # Two handles.
    y0, y1 = 0.88, 0.55
    r0, r1 = outer_r(prof, y0) - 0.01, outer_r(prof, y1) - 0.01
    for side in (1, -1):
        t = np.linspace(0, 1, 18)
        x = r0 + (r1 - r0) * t + 0.2 * np.sin(t * math.pi) ** 0.8
        path = np.column_stack([side * x, y0 + (y1 - y0) * t + 0.05 * np.sin(t * math.pi), np.zeros_like(t)])
        pieces.append(tube(path, lambda tt: 0.034 - 0.012 * math.sin(tt * math.pi), chart=gold, segs=10, up=(0, 0, 1),
                           aspect=0.8))
    pieces.append(gem("brilliant", (0.07, 0.07, 0.04), chart=gem_chart(EMERALD, 54)).rot([0, 1, 0], 180)
                  .move(0, 0.6, -0.345))
    return pieces


POTIONS = {"Potion": potion, "HealersDraught": healers_draught, "SwiftfootTonic": swiftfoot_tonic,
           "GiantsStrengthBrew": giants_strength_brew, "PhoenixTears": phoenix_tears}
ELIXIRS = {"Elixir": elixir, "ElixirOfClarity": elixir_of_clarity, "MoonwellElixir": moonwell_elixir,
           "ElixirOfAges": elixir_of_ages, "StarlightElixir": starlight_elixir}
GOBLETS = {"Goblet": goblet, "FeastGoblet": feast_goblet, "MoonlitGoblet": moonlit_goblet,
           "RoyalChalice": royal_chalice, "GrailOfAges": grail_of_ages}
