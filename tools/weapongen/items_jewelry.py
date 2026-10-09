"""Rings and amulets. Shown at "shop display" scale (about 4x real size) so they read on a
counter; scale the MeshPart down in Studio if you want them life-size.

Rings stand upright with the finger hole along Z and the stone on top (+Y); origin = ring centre.
Amulets face -Z (Roblox front, so they work as chest accessories); origin = pendant centre.
"""
import math

import numpy as np

from core import Chart, P, gem, lathe, pillow, tube, crown_band, engrave_filigree, layers, noise, smooth
from items_vessels import SILVER, crescent
from weapons import AMETHYST, CYAN, GOLD, PALE_GOLD, RUBY, SAPPHIRE, gem_chart, gold_chart, sym

DIAMOND = (0.88, 0.95, 1.0)
EMERALD = (0.1, 0.8, 0.35)
GARNET = (0.75, 0.08, 0.15)
BLACK_METAL = (0.16, 0.14, 0.15)
PLATINUM = (0.9, 0.92, 0.95)
JADE = (0.25, 0.7, 0.35)


def metal(color, seed=0, rough=0.2, ornate=False, size=0.5):
    return Chart(size, size, P.metal(color, rough=rough, var=0.15, seed=seed, metal=0.9,
                                     engrave=engrave_filigree(density=6.0, dirt=0.3) if ornate else None), "metal")


def resample(outline, n):
    """Evenly resample a closed outline to n points."""
    p = np.asarray(outline, float)
    p = np.vstack([p, p[:1]])
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    arc = np.r_[0, np.cumsum(seg)]
    t = np.linspace(0, arc[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, arc, p[:, 0]), np.interp(t, arc, p[:, 1])])


def rim(outline, z, r, chart, n=48, segs=5):
    """A raised wire rim following a closed outline at depth z (front face at +z)."""
    p = resample(outline, n)
    return tube(np.column_stack([p, np.full(n, z)]), r, chart=chart, segs=segs, closed=True, up=(0, 0, 1))


def circle(R, n=48, cx=0.0, cy=0.0):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return list(zip(cx + R * np.sin(t), cy + R * np.cos(t)))


def star_outline(points, R, r, rot=0.0):
    out = []
    for k in range(points * 2):
        a = rot + k * math.pi / points
        rr = R if k % 2 == 0 else r
        out.append((rr * math.sin(a), rr * math.cos(a)))
    return out


def faceted_star(points, R, r, h, edge, chart, radii=None):
    """A star with a raised centre and sharp ridges to each tip; flat-shaded facets catch light.
    radii lets individual tips differ (e.g. a long north point)."""
    outline = star_outline(points, R, r) if radii is None else \
        [(rr * math.sin(k * math.pi / points), rr * math.cos(k * math.pi / points)) for k, rr in enumerate(radii)]
    n = len(outline)
    V, F = [], []
    for side in (1, -1):
        c = len(V)
        V.append((0, 0, side * h))
        for x, y in outline:
            V.append((x, y, side * edge))
        for k in range(n):
            a, b = c + 1 + k, c + 1 + (k + 1) % n
            F.append([c, a, b] if side > 0 else [c, b, a])
    # Rim wall.
    base = len(V)
    for x, y in outline:
        V += [(x, y, edge), (x, y, -edge)]
    for k in range(n):
        a, b = base + 2 * k, base + 2 * ((k + 1) % n)
        F += [[a, a + 1, b], [b, a + 1, b + 1]]
    V = np.array(V, float)
    from core import Piece
    uv = np.column_stack([(V[:, 0] / (2 * R)) + 0.5, 0.5 - V[:, 1] / (2 * R)])
    p = Piece(V, F, uv, chart, smooth=False)
    p.smooth_deg = 0.0
    return p.orient(lambda c: np.column_stack([c[:, 0] * 0.3, c[:, 1] * 0.3, np.sign(c[:, 2]) + 1e-9]))


def bail_and_chain(top_y, chain_chart, bail_chart, w=0.36, h=1.3, r=0.011, z=0.0, cord=False):
    """A ring bail at the pendant's top and a long chain loop rising from it."""
    t = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    br = 0.045
    bail = tube(np.column_stack([np.zeros_like(t), top_y + br + br * np.cos(t), z + br * np.sin(t)]), 0.013,
                chart=bail_chart, segs=8, closed=True, up=(1, 0, 0))
    y0 = top_y + 2 * br
    s = np.linspace(0, 2 * math.pi, 64, endpoint=False)
    x = w * np.sin(s) * (0.25 + 0.75 * np.sin(s / 2) ** 2)
    y = y0 + h * (1 - np.cos(s)) / 2
    chain = tube(np.column_stack([x, y, np.full_like(x, z + 0.01)]), r * (1.6 if cord else 1.0), chart=chain_chart,
                 segs=5, closed=True, up=(0, 0, 1))
    return [bail, chain]


def finish_amulet(pieces):
    """Built facing +Z; turn to face -Z (Roblox front)."""
    for p in pieces:
        p.rot([0, 1, 0], 180)
    return pieces


# =============================================================== RINGS

def band(R, width, thick, chart, n=56, top_thick=1.0, top_width=1.0, shoulder=0.35):
    """Ring band around Z (finger hole along Z). Thicker/wider toward the top (+Y) if asked."""
    t = np.linspace(0, 1, n, endpoint=False)
    a = 2 * math.pi * t
    path = np.column_stack([R * np.sin(a), -R * np.cos(a), np.zeros_like(a)])
    k = lambda tt: np.exp(-((tt - 0.5) / shoulder) ** 2)
    rad = lambda tt: thick * (1 + (top_thick - 1) * k(tt))
    asp = lambda tt: width * (1 + (top_width - 1) * k(tt)) / rad(tt)
    return tube(path, rad, chart=chart, segs=10, closed=True, up=(0, 0, 1), aspect=asp, superellipse=2.6)


def prongs(y0, y1, r0, r1, chart, n=4, phase=45.0, rad=0.009):
    out = []
    for k in range(n):
        a = math.radians(phase + k * 360 / n)
        t = np.linspace(0, 1, 6)
        rr = r0 + (r1 - r0) * t + 0.01 * np.sin(t * math.pi)
        path = np.column_stack([rr * np.sin(a), y0 + (y1 - y0) * t, rr * np.cos(a)])
        out.append(tube(path, lambda tt: rad * (1 - 0.4 * tt), chart=chart, segs=5, up=(1, 0, 0)))
    return out


def ring():
    gold = metal(GOLD, 60)
    R = 0.24
    pieces = [band(R, 0.05, 0.03, gold, top_thick=1.4, top_width=1.3)]
    pieces.append(lathe([(0.0, R + 0.02), (0.045, R + 0.02), (0.055, R + 0.05), (0.05, R + 0.06), (0.0, R + 0.06)],
                        gold, segs=12, hard=(1,)))
    pieces.append(gem("brilliant", (0.05, 0.05, 0.035), chart=gem_chart(GARNET, 61)).rot([1, 0, 0], -90)
                  .move(0, R + 0.085, 0))
    pieces += prongs(R + 0.05, R + 0.1, 0.05, 0.04, gold)
    return pieces


def sapphire_band():
    silver = metal(SILVER, 62)
    R = 0.24
    pieces = [band(R, 0.08, 0.034, silver, top_thick=1.25)]
    sc = gem_chart(SAPPHIRE, 63)
    for k in range(-3, 4):
        if k == 0:
            continue
        a = k * 0.17
        g = gem("brilliant", (0.026, 0.026, 0.02), chart=sc).rot([1, 0, 0], -90)
        pieces.append(g.move(0, R + 0.042 + 0.006 * (abs(k) < 2), 0).rot([0, 0, 1], -math.degrees(a)))
    pieces.append(lathe([(0.0, R + 0.03), (0.06, R + 0.03), (0.072, R + 0.06), (0.066, R + 0.075), (0.0, R + 0.075)],
                        silver, segs=16, hard=(1,), sz=0.7))
    pieces.append(gem("brilliant", (0.065, 0.045, 0.045), chart=sc).rot([1, 0, 0], -90).move(0, R + 0.1, 0))
    pieces += prongs(R + 0.07, R + 0.12, 0.06, 0.05, silver, n=6, phase=0)
    return pieces


def moonstone_ring():
    silver = metal(SILVER, 64, ornate=True)
    R = 0.24
    pieces = [band(R, 0.06, 0.03, silver, top_thick=1.3, top_width=1.6, shoulder=0.25)]
    dc = gem_chart(DIAMOND, 73)
    for side in (1, -1):
        for k, a in enumerate((0.36, 0.5)):
            g = gem("brilliant", (0.018 - 0.004 * k, 0.018 - 0.004 * k, 0.014), chart=dc).rot([1, 0, 0], -90)
            pieces.append(g.move(0, R + 0.036 - 0.006 * k, 0).rot([0, 0, 1], -side * math.degrees(a)))
    pieces.append(lathe([(0.0, R + 0.02), (0.075, R + 0.02), (0.085, R + 0.05), (0.075, R + 0.06), (0.0, R + 0.06)],
                        silver, segs=20, hard=(1,), sz=0.75))
    stone = gem("cabochon", (0.07, 0.052, 0.05), painter=P.moonstone(seed=65)).rot([1, 0, 0], -90)
    pieces.append(stone.move(0, R + 0.055, 0))
    t = np.linspace(0, 2 * math.pi, 32, endpoint=False)
    pieces.append(tube(np.column_stack([0.074 * np.sin(t), np.full_like(t, R + 0.062), 0.056 * np.cos(t)]), 0.008,
                       chart=silver, segs=6, closed=True, up=(0, 1, 0)))
    return pieces


def emberheart_ring():
    dark = metal(BLACK_METAL, 66, rough=0.35)
    gold = metal(GOLD, 67)
    R = 0.24
    pieces = [band(R, 0.07, 0.034, dark, top_thick=1.3, top_width=1.3)]
    flame = sym([(0, 0), (0.03, 0.02), (0.035, 0.06), (0.018, 0.09), (0.022, 0.12), (0.006, 0.1), (0, 0.15)])
    for side in (1, -1):
        f = pillow(flame, 0.01, 0.004, 0.006, chart=gold).rot([0, 0, 1], -side * 25)
        pieces.append(f.move(side * 0.05, R - 0.05, 0.037))
        pieces.append(f.copy().move(0, 0, -0.074))
    heart_t = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    hx = 16 * np.sin(heart_t) ** 3 / 17 * 0.085
    hy = (13 * np.cos(heart_t) - 5 * np.cos(2 * heart_t) - 2 * np.cos(3 * heart_t) - np.cos(4 * heart_t)) / 17 * 0.085
    heart = list(zip(hx, hy))
    ruby = Chart(0.2, 0.2, lambda nu, nv, su, sv: _ember_gem(nu, nv), "ember")
    h = pillow(heart, 0.04, 0.012, 0.03, chart=ruby).rot([1, 0, 0], -90).rot([0, 1, 0], 0)
    pieces.append(h.rot([1, 0, 0], 90).move(0, R + 0.11, 0.0))
    pieces.append(rim(heart, 0.0, 0.01, gold, n=48).move(0, R + 0.11, 0))
    pieces += prongs(R + 0.03, R + 0.06, 0.03, 0.03, gold, n=2, phase=90, rad=0.012)
    return pieces


def _ember_gem(nu, nv):
    vv, uu = np.mgrid[0:nv, 0:nu]
    u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
    d = np.hypot(u - 0.5, v - 0.45)
    n = noise(nv, nu, nu * 0.2, octaves=3, seed=68)
    core_ = np.clip(1 - d * 2.2, 0, 1)
    col = np.array([0.55, 0.02, 0.04]) * (1 - core_[..., None]) + np.array([1.0, 0.45, 0.1]) * core_[..., None]
    col = col * (0.75 + 0.4 * n)[..., None]
    return layers(nu, nv, col, 0.0, 0.05, emit=col * (0.4 + 0.8 * core_)[..., None])


def ring_of_kings():
    gold = metal(GOLD, 69)
    R = 0.25
    pieces = [band(R, 0.075, 0.04, gold, top_thick=1.5, top_width=1.5, shoulder=0.3)]
    # Crown-shaped setting.
    pts = 6
    hfn = lambda th: 0.05 + 0.05 * np.abs(np.cos(th * pts / 2)) ** 3
    cb = crown_band(0.075, hfn, thick=0.012, segs=pts * 8, chart=gold, base=R + 0.03, flare=0.25)
    pieces.append(cb)
    pieces.append(lathe([(0.0, R + 0.03), (0.08, R + 0.03), (0.08, R + 0.045), (0.0, R + 0.045)], gold, segs=24))
    for k in range(pts):
        a = k * 2 * math.pi / pts
        pieces.append(gem("octa", (0.009, 0.009, 0.009), chart=gem_chart(PALE_GOLD, 70))
                      .move(0.1 * math.sin(a) * 1.1, R + 0.135, -0.1 * math.cos(a) * 1.1))
    pieces.append(gem("brilliant", (0.085, 0.085, 0.06), chart=gem_chart(RUBY, 71), n=10).rot([1, 0, 0], -90)
                  .move(0, R + 0.1, 0))
    dc = gem_chart(DIAMOND, 72)
    for side in (1, -1):
        for k, a in enumerate((0.38, 0.55)):
            g = gem("brilliant", (0.022, 0.022, 0.016), chart=dc).rot([1, 0, 0], -90)
            pieces.append(g.move(0, R + 0.05 - 0.008 * k, 0).rot([0, 0, 1], -side * math.degrees(a)))
    return pieces


# =============================================================== AMULETS

def _medallion(outline, thick, face_painter, back_chart, rim_chart, rim_r=0.014, holes=()):
    face = Chart(0.6, 0.6, face_painter, "face")
    f, b = pillow(outline, thick, thick * 0.6, 0.03, chart=face, back_chart=back_chart, holes=holes)
    return [f, b, rim(outline, thick * 0.6, rim_r, rim_chart)]


def concentric(color, rings=4, seed=0):
    """Engraved concentric rings + rays (for planar pillow charts)."""
    base = P.metal(color, rough=0.22, var=0.15, seed=seed, metal=0.9)

    def paint(nu, nv, su, sv):
        L = base(nu, nv, su, sv)
        vv, uu = np.mgrid[0:nv, 0:nu]
        x, y = (uu + 0.5) / nu - 0.5, (vv + 0.5) / nv - 0.5
        r, a = np.hypot(x, y), np.arctan2(y, x)
        g = sum(np.exp(-((r - k * 0.5 / (rings + 1)) / 0.006) ** 2) for k in range(1, rings + 1))
        g += 0.6 * np.exp(-((np.sin(a * 12) * r) / 0.004) ** 2) * (r > 0.15) * (r < 0.32)
        L["height"] -= 0.0015 * g
        L["color"] *= (1 - 0.35 * np.clip(g, 0, 1))[..., None]
        return L
    return paint


def amulet():
    gold = metal(GOLD, 80)
    pieces = _medallion(circle(0.22), 0.03, concentric(GOLD, 3, 81), gold, gold)
    pieces.append(gem("brilliant", (0.06, 0.06, 0.04), chart=gem_chart(RUBY, 82)).move(0, 0, 0.035))
    pieces += bail_and_chain(0.235, Chart(0.05, 2.6, P.chain(GOLD)), gold)
    return finish_amulet(pieces)


def lucky_charm():
    gold = metal(GOLD, 83)
    jade = Chart(0.3, 0.3, P.enamel(JADE, rough=0.18, seed=84), "jade")
    leaf_t = np.linspace(0, 2 * math.pi, 32, endpoint=False)
    hx = 16 * np.sin(leaf_t) ** 3 / 17 * 0.1
    hy = (13 * np.cos(leaf_t) - 5 * np.cos(2 * leaf_t) - 2 * np.cos(3 * leaf_t) - np.cos(4 * leaf_t)) / 17 * 0.1
    heart = list(zip(hx, hy + 0.088))   # tip at the origin, lobes outward along +Y
    pieces = []
    for k in range(4):
        leaf = pillow(heart, 0.025, 0.008, 0.03, chart=jade)
        pieces.append(leaf.move(0, 0.005, 0).rot([0, 0, 1], 45 + k * 90))
        pieces.append(rim(heart, 0.008, 0.006, gold, n=28, segs=5).rot([0, 0, 1], 45 + k * 90))
    pieces.append(gem("brilliant", (0.03, 0.03, 0.02), chart=gem_chart(PALE_GOLD, 85)).move(0, 0, 0.026))
    t = np.linspace(0, 1, 10)
    stem = np.column_stack([0.04 * t + 0.03 * np.sin(t * 3), -0.05 - 0.17 * t, np.zeros_like(t)])
    pieces.append(tube(stem, lambda tt: 0.013 * (1 - 0.5 * tt), chart=jade, segs=6))
    cord = Chart(0.05, 2.6, P.hair((0.42, 0.26, 0.14), seed=86), "cord")
    pieces += bail_and_chain(0.2, cord, gold, cord=True)
    return finish_amulet(pieces)


def owl_eye_amulet():
    bronze = metal((0.85, 0.6, 0.32), 87)
    owl = [(0.0, -0.24), (0.1, -0.21), (0.17, -0.12), (0.19, 0.0), (0.18, 0.1), (0.2, 0.22), (0.12, 0.15),
           (0.05, 0.16), (0.0, 0.13)]
    owl = sym(owl)
    feathers = P.scales((0.8, 0.55, 0.28), tip=(1.0, 0.82, 0.5), size=0.035, metal=0.85, rough=0.3, seed=88)
    pieces = _medallion(owl, 0.035, feathers, bronze, bronze, rim_r=0.012)
    amber = gem_chart((1.0, 0.65, 0.1), 89)
    dark = Chart(0.1, 0.1, P.enamel((0.04, 0.03, 0.02), rough=0.1), "pupil")
    for side in (1, -1):
        pieces.append(lathe([(0.0, 0.0), (0.07, 0.0), (0.075, 0.015), (0.06, 0.02), (0.0, 0.02)], bronze, segs=20)
                      .rot([1, 0, 0], 90).move(side * 0.085, 0.03, 0.03))
        pieces.append(gem("brilliant", (0.058, 0.058, 0.035), chart=amber, n=10).move(side * 0.085, 0.03, 0.06))
        pieces.append(gem("cabochon", (0.018, 0.03, 0.012), chart=dark).move(side * 0.085, 0.03, 0.082))
    beak = [(0, -0.03), (0.022, 0.01), (0, 0.02), (-0.022, 0.01)]
    pieces.append(pillow(beak, 0.02, 0.006, 0.01, chart=bronze).move(0, -0.06, 0.035))
    pieces += bail_and_chain(0.16, Chart(0.05, 2.6, P.chain((0.85, 0.6, 0.32))), bronze)
    return finish_amulet(pieces)


def wyrmscale_amulet():
    gold = metal(GOLD, 90)
    shape = sym([(0.0, -0.28), (0.09, -0.16), (0.16, -0.02), (0.17, 0.1), (0.12, 0.2), (0.0, 0.24)])
    scales = P.scales((0.08, 0.45, 0.38), tip=(0.35, 0.95, 0.75), size=0.075, metal=0.8, rough=0.25, seed=91)
    pieces = _medallion(shape, 0.04, scales, Chart(0.4, 0.4, P.metal((0.1, 0.3, 0.26), rough=0.3, seed=92)), gold)
    pieces.append(gem("brilliant", (0.07, 0.09, 0.05), chart=gem_chart(EMERALD, 93), n=10).move(0, 0.02, 0.05))
    for k in range(3):
        a = math.radians(90 + k * 120)
        t = np.linspace(0, 1, 8)
        r = 0.12 - 0.05 * t
        path = np.column_stack([r * np.cos(a), 0.02 + r * np.sin(a), 0.035 + 0.05 * np.sin(t * 2.2)])
        pieces.append(tube(path, lambda tt: 0.016 * (1 - 0.7 * tt), chart=gold, segs=6, up=(0, 0, 1)))
    pieces += bail_and_chain(0.24, Chart(0.05, 2.6, P.chain(GOLD)), gold)
    return finish_amulet(pieces)


def heart_of_the_sun():
    gold = metal(GOLD, 94)
    rays = []
    for k in range(32):
        a = k * 2 * math.pi / 32
        r = 0.27 if k % 2 == 0 else 0.16
        r += 0.03 * math.sin(k * 1.7) * (k % 2 == 0)
        rays.append((r * math.sin(a), r * math.cos(a)))
    pieces = _medallion(rays, 0.03, P.metal(GOLD, rough=0.2, var=0.15, seed=95, metal=0.9), gold, gold, rim_r=0.008)
    pieces.append(rim(circle(0.13), 0.035, 0.014, gold))
    sun = Chart(0.2, 0.2, lambda nu, nv, su, sv: _sunstone(nu, nv), "sunstone")
    pieces.append(gem("cabochon", (0.12, 0.12, 0.05), chart=sun).move(0, 0, 0.02))
    rc = gem_chart(RUBY, 96)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        pieces.append(gem("brilliant", (0.018, 0.018, 0.012), chart=rc).move(0.16 * math.sin(a), 0.16 * math.cos(a), 0.035))
    pieces += bail_and_chain(0.27, Chart(0.05, 2.6, P.chain(GOLD)), gold)
    return finish_amulet(pieces)


def _sunstone(nu, nv):
    vv, uu = np.mgrid[0:nv, 0:nu]
    u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
    n = noise(nv, nu, nu * 0.15, octaves=4, seed=97)
    sw = 0.5 + 0.5 * np.sin(u * 2 * math.pi * 3 + n * 6)
    col = np.array([1.0, 0.42, 0.05]) * (0.7 + 0.3 * sw)[..., None] + np.array([0.0, 0.35, 0.1]) * (v ** 2)[..., None]
    col = np.clip(col, 0, 1)
    return layers(nu, nv, col, 0.0, 0.06, emit=col * (0.6 + 0.6 * v)[..., None])


def _star(points, R, r, metal_col, seed, h=0.05, edge=0.012, radii=None):
    return faceted_star(points, R, r, h, edge, Chart(0.4, 0.4, P.metal(metal_col, rough=0.15, var=0.1, seed=seed,
                                                                         metal=0.92)), radii=radii)


def star_amulet():
    pewter = metal((0.7, 0.71, 0.72), 100, rough=0.4)
    outline = star_outline(5, 0.22, 0.095)
    pieces = [pillow(outline, 0.025, 0.018, 0.02, chart=pewter)]
    pieces += bail_and_chain(0.225, Chart(0.05, 2.6, P.hair((0.35, 0.22, 0.12), seed=101)), pewter, cord=True)
    return finish_amulet(pieces)


def polished_star_amulet():
    gold = metal(GOLD, 102)
    pieces = [_star(5, 0.23, 0.1, GOLD, 103)]
    pieces += bail_and_chain(0.235, Chart(0.05, 2.6, P.chain(GOLD)), gold)
    return finish_amulet(pieces)


def moonstone_star_amulet():
    silver = metal(SILVER, 104)
    pieces = [_star(5, 0.21, 0.09, SILVER, 105, h=0.04)]
    moon = pillow(crescent(0.27, 0.23, 0.09), 0.02, 0.008, 0.015, chart=silver).rot([0, 0, 1], -30).move(-0.03, 0.0, -0.03)
    pieces.append(moon)
    pieces.append(gem("cabochon", (0.055, 0.055, 0.03), painter=P.moonstone(seed=106)).move(0, 0, 0.035))
    t = np.linspace(0, 2 * math.pi, 28, endpoint=False)
    pieces.append(tube(np.column_stack([0.058 * np.sin(t), 0.058 * np.cos(t), np.full_like(t, 0.04)]), 0.008,
                       chart=silver, segs=6, closed=True, up=(0, 0, 1)))
    pieces += bail_and_chain(0.215, Chart(0.05, 2.6, P.chain(SILVER)), silver)
    return finish_amulet(pieces)


def celestial_star_amulet():
    gold, silver = metal(GOLD, 107), metal(SILVER, 108)

    def sky(nu, nv, su, sv):
        vv, uu = np.mgrid[0:nv, 0:nu]
        n = noise(nv, nu, nu * 0.2, octaves=4, seed=109)
        col = np.array([0.05, 0.08, 0.35]) * (0.7 + 0.6 * n)[..., None] + np.array([0.2, 0.0, 0.3]) * (n ** 3)[..., None]
        r = np.random.default_rng(110)
        st = np.zeros((nv, nu))
        st.flat[r.integers(0, nv * nu, 90)] = 1
        from scipy.ndimage import gaussian_filter
        st = np.clip(gaussian_filter(st, 0.8) * 6, 0, 1)
        col = np.clip(col + st[..., None], 0, 1)
        return layers(nu, nv, col, 0.0, 0.1, emit=st[..., None] * 1.2 + col * 0.2)

    disc = Chart(0.4, 0.4, sky, "sky")
    pieces = [pillow(circle(0.17), 0.02, 0.015, 0.02, chart=disc), rim(circle(0.17), 0.015, 0.012, gold)]
    pieces.append(_star(4, 0.3, 0.07, GOLD, 111, h=0.06, edge=0.014))
    pieces.append(_star(4, 0.21, 0.06, SILVER, 112, h=0.05, edge=0.012).rot([0, 0, 1], 45).move(0, 0, -0.008))
    sc = gem_chart(SAPPHIRE, 113)
    pieces.append(gem("brilliant", (0.05, 0.05, 0.035), chart=sc).move(0, 0, 0.055))
    for k in range(4):
        a = k * math.pi / 2
        pieces.append(gem("brilliant", (0.02, 0.02, 0.014), chart=gem_chart(DIAMOND, 114))
                      .move(0.2 * math.sin(a), 0.2 * math.cos(a), 0.03))
    pieces += bail_and_chain(0.305, Chart(0.05, 2.6, P.chain(GOLD)), gold)
    return finish_amulet(pieces)


def north_star_amulet():
    plat = metal(PLATINUM, 115)
    radii = [0.36, 0.06, 0.22, 0.06, 0.26, 0.06, 0.22, 0.06]
    pieces = [_star(4, 0.36, 0.06, PLATINUM, 116, h=0.065, edge=0.014, radii=radii)]
    pieces.append(_star(4, 0.15, 0.04, PALE_GOLD, 117, h=0.045, edge=0.01).rot([0, 0, 1], 45).move(0, 0, -0.005))
    t = np.linspace(0, 2 * math.pi, 48, endpoint=False)
    pieces.append(tube(np.column_stack([0.19 * np.sin(t), 0.19 * np.cos(t), np.full_like(t, -0.01)]), 0.012,
                       chart=plat, segs=6, closed=True, up=(0, 0, 1)))
    glow = Chart(0.2, 0.4, P.enamel((0.75, 0.88, 1.0), rough=0.1, glow=0.9), "glow")
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        ray = [(-0.008, 0.07), (0.008, 0.07), (0.0, 0.25)]
        pieces.append(pillow(ray, 0.006, 0.003, 0.004, chart=glow).rot([0, 0, 1], -math.degrees(a)).move(0, 0, -0.012))
    pieces.append(gem("brilliant", (0.065, 0.065, 0.045), chart=gem_chart(DIAMOND, 118), n=10).move(0, 0, 0.06))
    pieces += bail_and_chain(0.36, Chart(0.05, 2.6, P.chain(PLATINUM)), plat)
    return finish_amulet(pieces)


RINGS = {"Ring": ring, "SapphireBand": sapphire_band, "MoonstoneRing": moonstone_ring,
         "EmberheartRing": emberheart_ring, "RingOfKings": ring_of_kings}
AMULETS = {"Amulet": amulet, "LuckyCharm": lucky_charm, "OwlEyeAmulet": owl_eye_amulet,
           "WyrmscaleAmulet": wyrmscale_amulet, "HeartOfTheSun": heart_of_the_sun, "StarAmulet": star_amulet,
           "PolishedStarAmulet": polished_star_amulet, "MoonstoneStarAmulet": moonstone_star_amulet,
           "CelestialStarAmulet": celestial_star_amulet, "NorthStarAmulet": north_star_amulet}
