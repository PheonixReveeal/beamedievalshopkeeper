"""Shields. Front faces -Z (Roblox forward); origin = the hand grip on the back."""
import math

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

from core import Chart, P, gem, lathe, layers, noise, pillow, smooth, tube, engrave_filigree, voronoi
from items_jewelry import DIAMOND, EMERALD, circle, resample
from weapons import (BLACK_LEATHER, GOLD, PALE_GOLD, RUBY, SAPPHIRE, WOOD_DARK, WOOD_MID, bez, gem_chart, sym)
from items_headwear import STEEL, DARK_IRON

IRON = (0.42, 0.43, 0.46)
ROYAL_BLUE = (0.1, 0.18, 0.55)
ROYAL_RED = (0.6, 0.06, 0.08)
IVORY = (0.93, 0.9, 0.82)
PURPLE = (0.3, 0.08, 0.42)
FOREST = (0.12, 0.35, 0.18)


# --------------------------------------------------------------- outlines

def heater(w=2.0, h=2.5):
    t, b = h * 0.45, -h * 0.55
    right = [(0.0, t + 0.06), (w * 0.25, t + 0.045), (w / 2, t)] + \
        bez((w / 2, t), (w / 2, t - 0.45 * h), (w * 0.32, b + 0.25 * h), (0.0, b), 14) + [(0.0, b)]
    return sym(right)


def kite(w=1.7, h=2.9):
    t, b = h * 0.38, -h * 0.62
    right = [(0.0, t + w * 0.3)] + bez((0.0, t + w * 0.3), (w * 0.3, t + w * 0.3), (w / 2, t + 0.1), (w / 2, t - 0.1), 8) + \
        bez((w / 2, t - 0.1), (w / 2, t - 0.6), (w * 0.22, b + 0.4), (0.0, b), 14) + [(0.0, b)]
    return sym(right)


def crown_shape(w=0.7, h=0.5):
    """Heraldic crown silhouette: a band with five points."""
    b = -h / 2
    band_top = b + h * 0.35
    pts = [(-w / 2, b), (w / 2, b), (w / 2, band_top)]
    peaks = [(w / 2 * 1.05, b + h), (w * 0.25, band_top + 0.12 * h), (w * 0.15, b + h * 0.85), (0.0, band_top + 0.18 * h),
             (-w * 0.15, b + h * 0.85), (-w * 0.25, band_top + 0.12 * h), (-w / 2 * 1.05, b + h)]
    pts += [peaks[0]] + [(w * 0.33, band_top + 0.02)] + [peaks[2]] + [(0.07 * w, band_top + 0.1 * h), (0.0, b + h * 1.05),
                                                                         (-0.07 * w, band_top + 0.1 * h)] + \
        [peaks[4], (-w * 0.33, band_top + 0.02), peaks[6], (-w / 2, band_top)]
    return pts


def oak_leaf(L=0.9, W=0.45):
    right = [(0.0, -L / 2)]
    for k, y in enumerate(np.linspace(-L / 2 + 0.08, L / 2 - 0.05, 9)):
        f = math.sin((y + L / 2) / L * math.pi)
        right.append((W / 2 * f * (1.0 if k % 2 == 0 else 0.62), y))
    right.append((0.0, L / 2))
    return sym(right)


# --------------------------------------------------------------- face painters

def shape_dist(outline, nu, nv):
    """Distance (studs) from each texel of a pillow chart to the shape's edge."""
    p = np.asarray(outline, float)
    minx, miny = p.min(0)
    maxx, maxy = p.max(0)
    w, h = maxx - minx, maxy - miny
    img = Image.new("L", (nu, nv), 0)
    ImageDraw.Draw(img).polygon([((x - minx) / w * nu, (maxy - y) / h * nv) for x, y in p], fill=255)
    m = np.asarray(img) > 0
    d = distance_transform_edt(m)
    return d * (w / nu), (minx, miny, w, h)


def field(colors, outline, metal_mask=None, rough=0.4, wear=0.25, seed=0, border=None, filigree=False, glow=None):
    """Painted / enamelled shield face. colors(u, v, x, y) -> (nv, nu, 3); metal_mask likewise -> 0..1.
    border: (distance_from_edge, width, color) for an inlaid gold line."""
    def paint(nu, nv, su, sv):
        ppu = nu / su
        d, (minx, miny, w, h) = shape_dist(outline, nu, nv)
        vv, uu = np.mgrid[0:nv, 0:nu]
        u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
        x, y = minx + u * w, miny + (1 - v) * h
        col = colors(u, v, x, y)
        n = noise(nv, nu, 0.3 * ppu, octaves=4, seed=seed)
        col = col * (0.85 + 0.25 * n)[..., None]
        mm = np.zeros((nv, nu)) if metal_mask is None else metal_mask(u, v, x, y)
        chips = smooth(noise(nv, nu, 0.09 * ppu, octaves=3, seed=seed + 1), 1 - wear * 0.45, 1 - wear * 0.4) * (1 - mm)
        steel = np.array(STEEL)
        col = col * (1 - chips[..., None]) + steel * chips[..., None]
        metal = np.clip(mm + chips, 0, 1)
        L = layers(nu, nv, col, metal * 0.85, rough * (1 - mm) + 0.22 * mm + 0.1 * n, height=0.0015 * n - 0.001 * chips)
        if border is not None:
            d0, bw, bc = border
            g = np.exp(-((d - d0) / bw) ** 2)
            L["color"] = L["color"] * (1 - g[..., None]) + np.asarray(bc) * g[..., None]
            L["metal"] = np.maximum(L["metal"], 0.85 * g)
            L["rough"] = L["rough"] * (1 - g) + 0.22 * g
            L["height"] += 0.003 * g
        if filigree:
            engrave_filigree(density=1.6, depth=0.002, dirt=0.25)(L, nu, nv, su, sv)
        if glow is not None:
            L["emit"] = glow(u, v, x, y)
        return L
    return paint


def planks(color=WOOD_MID, n=6, paint=None, paint_wear=0.35, seed=0):
    """Vertical wooden planks, optionally painted over (with worn-through patches)."""
    def paint_fn(nu, nv, su, sv):
        L = P.wood(color, seed=seed, dark=0.4)(nu, nv, su, sv)
        u = (np.arange(nu) + 0.5) / nu
        seam = np.exp(-((((u * n) % 1) - 0.0) / (0.012 * n)) ** 2) + np.exp(-((((u * n) % 1) - 1.0) / (0.012 * n)) ** 2)
        L["color"] *= (1 - 0.6 * seam)[None, :, None]
        L["height"] -= 0.004 * seam[None, :]
        if paint is not None:
            ppu = nu / su
            keep = noise(nv, nu, 0.25 * ppu, octaves=4, seed=seed + 3) > paint_wear
            L["color"] = np.where(keep[..., None], np.asarray(paint) * (0.8 + 0.3 * noise(nv, nu, 0.1 * ppu, seed=seed + 4))[..., None],
                                  L["color"])
            L["rough"] = np.where(keep, 0.55, L["rough"])
        return L
    return paint_fn


# --------------------------------------------------------------- shield assembly

class Shield:
    def __init__(self, outline, thick=0.06, dome=0.12, face=None, back=None, max_area=None):
        self.outline = outline
        p = np.asarray(outline, float)
        self.cx, self.cy = (p.min(0) + p.max(0)) / 2
        self.a, self.b = (p.max(0) - p.min(0)) / 2
        self.dome, self.thick = dome, thick
        area = abs(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])) / 2
        back = back or Chart(2.0, 2.0, planks(WOOD_DARK, 5, seed=300), "back")
        f, b = pillow(outline, thick, thick * 0.7, 0.08, chart=Chart(2 * self.a, 2 * self.b, face, "face"), back_chart=back,
                      max_area=max_area or area / 220)
        self.pieces = [f.deform(self.curve), b.deform(self.curve)]

    def z(self, x, y):
        k = ((x - self.cx) / self.a) ** 2 + ((y - self.cy) / self.b) ** 2
        return self.dome * (1 - np.clip(k, 0, 1.3))

    def curve(self, v):
        v = v.copy()
        v[:, 2] += self.z(v[:, 0], v[:, 1])
        return v

    def on_face(self, piece, lift=0.0):
        """Bend a piece built in the XY plane (front +Z) onto the shield's front surface."""
        def fn(v):
            v = v.copy()
            v[:, 2] += self.z(v[:, 0], v[:, 1]) + self.thick + lift
            return v
        self.pieces.append(piece.deform(fn))
        return piece

    def rim(self, chart, r=0.06, n=120, aspect=1.0, inset=0.0):
        p = resample(self.outline, n)
        if inset:
            from shapely.geometry import Polygon
            q = Polygon(self.outline).buffer(-inset, join_style=2)
            p = resample(list(q.exterior.coords)[:-1], n)
        z = self.z(p[:, 0], p[:, 1]) + (self.thick * 0.7 if inset else 0.0)
        self.pieces.append(tube(np.column_stack([p, z]), r, chart=chart, segs=7, closed=True, up=(0, 0, 1), aspect=aspect))

    def boss(self, chart, r=0.3, h=0.18, spike=0.0, x=0.0, y=None):
        y = self.cy if y is None else y
        prof = [(0.0, 0.0), (r * 1.15, 0.0), (r * 1.15, 0.02), (r, 0.04)] + \
               [(r * math.cos(a), 0.04 + h * math.sin(a)) for a in np.linspace(0.3, math.pi / 2, 6)]
        if spike:
            prof[-1] = (r * 0.25, 0.04 + h * 0.97)
            prof.append((0.0, 0.04 + h + spike))
        b = lathe(prof, chart, segs=24, hard=(2, 3)).rot([1, 0, 0], 90)
        self.pieces.append(b.move(x, y, self.z(x, y) + self.thick - 0.01))

    def studs(self, chart, n=12, inset=0.12, r=0.035):
        from shapely.geometry import Polygon
        q = Polygon(self.outline).buffer(-inset)
        pts = resample(list(q.exterior.coords)[:-1], n)
        for x, y in pts:
            s = lathe([(0, 0), (r, 0), (r * 0.85, r * 0.5), (0, r * 0.75)], chart, segs=8).rot([1, 0, 0], 90)
            self.pieces.append(s.move(x, y, self.z(x, y) + self.thick * 0.95))

    def handle(self, chart, strap_chart):
        zb = -self.thick + self.z(self.cx, self.cy)
        t = np.linspace(0, 1, 12)
        path = np.column_stack([-0.18 + 0.36 * t, self.cy - 0.05 + 0 * t, zb - 0.02 - 0.13 * np.sin(t * math.pi)])
        self.pieces.append(tube(path, 0.035, chart=chart, segs=8, up=(0, 1, 0)))
        strap = [(-0.55, -0.05), (0.55, -0.05), (0.55, 0.05), (-0.55, 0.05)]
        st = pillow(strap, 0.012, 0.008, 0.01, chart=strap_chart)
        self.pieces.append(st.move(0, self.cy + 0.45, zb - 0.015))
        return (0.0, self.cy - 0.05, zb - 0.15)

    def finish(self, grip):
        for p in self.pieces:
            p.move(-grip[0], -grip[1], -grip[2]).rot([0, 1, 0], 180)
        return self.pieces, (0, 0, 0)


def metal(color, seed=0, rough=0.28, metal_=0.85):
    return Chart(0.8, 0.8, P.metal(color, rough=rough, var=0.2, seed=seed, metal=metal_), "metal")


def leather_chart(seed=0):
    return Chart(0.6, 0.6, P.leather((0.35, 0.2, 0.1), seed=seed), "leather")


# =============================================================== the shields

def shield():
    s = Shield(circle(1.15, 64), dome=0.14, face=planks(WOOD_MID, 7, seed=301))
    iron = metal(IRON, 302, rough=0.4)
    s.rim(iron, r=0.075, aspect=1.0)
    s.boss(iron, r=0.3, h=0.16)
    s.studs(iron, n=16, inset=0.12)
    return s.finish(s.handle(iron, leather_chart(303)))


def oak_buckler():
    s = Shield(circle(0.72, 56), thick=0.07, dome=0.16, face=planks((0.42, 0.25, 0.12), 4, seed=304))
    iron = metal(IRON, 305, rough=0.35)
    wrap = Chart(4.6, 0.3, P.wrap((0.3, 0.17, 0.09), pitch=0.08, seed=306), "wrap")
    s.rim(wrap, r=0.085, n=96)
    s.boss(iron, r=0.26, h=0.15, spike=0.14)
    s.studs(iron, n=8, inset=0.15, r=0.04)
    return s.finish(s.handle(iron, leather_chart(307)))


def wardens_shield():
    outline = kite()
    s = Shield(outline, dome=0.16, face=planks(WOOD_MID, 6, paint=FOREST, paint_wear=0.3, seed=308))
    silver = metal((0.85, 0.87, 0.9), 309, rough=0.22)
    s.rim(silver, r=0.07)
    leaf = pillow(oak_leaf(1.0, 0.55), 0.03, 0.01, 0.04, chart=silver)
    s.on_face(leaf.move(0, -0.05, 0))
    for side in (1, -1):
        l2 = pillow(oak_leaf(0.55, 0.3), 0.025, 0.008, 0.03, chart=silver)
        s.on_face(l2.rot([0, 0, 1], side * 50).move(side * 0.3, -0.62, 0))
    acorn = lathe([(0, -0.08), (0.06, -0.04), (0.065, 0.02), (0.05, 0.05), (0, 0.06)],
                  Chart(0.3, 0.3, P.metal(GOLD, rough=0.25, seed=310, metal=0.85)), segs=12).rot([1, 0, 0], 90)
    s.on_face(acorn.move(0, -0.78, 0), lift=0.02)
    s.studs(silver, n=10, inset=0.13, r=0.03)
    return s.finish(s.handle(metal(IRON, 311), leather_chart(312)))


def sunburst_shield():
    outline = circle(1.15, 72)

    def colors(u, v, x, y):
        a = np.arctan2(y, x)
        rays = (np.sin(a * 16) > 0.2) & (np.hypot(x, y) > 0.35)
        return np.where(rays[..., None], np.array(GOLD), np.array([0.08, 0.16, 0.5]))

    def mm(u, v, x, y):
        a = np.arctan2(y, x)
        return ((np.sin(a * 16) > 0.2) & (np.hypot(x, y) > 0.35)).astype(float)

    s = Shield(outline, dome=0.14, face=field(colors, outline, mm, rough=0.25, wear=0.1, seed=313,
                                              border=(0.12, 0.012, GOLD)))
    gold = metal(GOLD, 314, rough=0.2)
    s.rim(gold, r=0.07)
    sun = []
    for k in range(24):
        a = k * 2 * math.pi / 24
        r = 0.42 if k % 2 == 0 else 0.3
        sun.append((r * math.sin(a), r * math.cos(a)))
    s.on_face(pillow(sun, 0.04, 0.015, 0.05, chart=gold))
    stone = Chart(0.2, 0.2, P.enamel((1.0, 0.5, 0.08), rough=0.08, glow=0.6), "sun")
    s.on_face(gem("cabochon", (0.2, 0.2, 0.08), chart=stone), lift=0.03)
    s.studs(gold, n=12, inset=0.12)
    return s.finish(s.handle(metal(IRON, 315), leather_chart(316)))


def dragonscale_aegis():
    outline = heater(2.1, 2.7)
    scales = P.scales((0.45, 0.06, 0.05), tip=(1.0, 0.45, 0.18), size=0.24, metal=0.7, rough=0.3, seed=317)
    s = Shield(outline, dome=0.18, face=scales)
    black = metal(DARK_IRON, 318, rough=0.35)
    s.rim(black, r=0.08)
    horn = Chart(0.4, 1.0, P.metal((0.85, 0.78, 0.65), rough=0.45, var=0.3, seed=319, metal=0.2), "horn")
    p = np.asarray(outline)
    top = p[:, 1].max()
    for side in (1, -1):
        for k, (x, y, ang) in enumerate(((0.95, top - 0.05, 40), (1.0, top - 0.55, 70), (0.85, top - 1.1, 95))):
            t = np.linspace(0, 1, 9)
            path = np.column_stack([side * (x + 0.28 * t * math.sin(math.radians(ang))),
                                    y + 0.28 * t * math.cos(math.radians(ang)) - 0.05 * t ** 2, 0.05 * t])
            spk = tube(path, lambda tt: 0.06 * (1 - tt) + 0.004, chart=horn, segs=8, up=(0, 0, 1))
            s.pieces.append(spk.deform(lambda v: v + np.column_stack([0 * v[:, 0], 0 * v[:, 0], s.z(v[:, 0], v[:, 1])])))
    gold = metal((0.75, 0.5, 0.2), 320)
    ring = [(0.48 * math.sin(a), 0.32 * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    hole = [(0.3 * math.sin(a), 0.18 * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 32, endpoint=False)]
    s.on_face(pillow(ring, 0.045, 0.015, 0.03, chart=gold, holes=[hole]).move(0, 0.1, 0))
    from items_headwear import _dragon_eye
    eye = Chart(0.2, 0.2, lambda nu, nv, su, sv: _dragon_eye(nu, nv), "eye")
    s.on_face(gem("cabochon", (0.31, 0.19, 0.09), chart=eye).move(0, 0.1, 0), lift=0.0)
    return s.finish(s.handle(metal(IRON, 321), leather_chart(322)))


# ---------------------------------------------------------------- royal shield tiers

def _royal(field_painter, rim_chart, rim_r, crown_chart, crown_size=(0.8, 0.6), crown_y=0.25, gems=None,
           extra=None, studs=None, seed=0):
    outline = heater()
    s = Shield(outline, dome=0.15, face=field_painter(outline))
    s.rim(rim_chart, r=rim_r)
    c = pillow(crown_shape(*crown_size), 0.045, 0.015, 0.04, chart=crown_chart)
    s.on_face(c.move(0, crown_y, 0))
    if gems:
        for (x, y, size, chart_) in gems:
            s.on_face(gem("brilliant", (size, size, size * 0.65), chart=chart_).move(x, crown_y + y, 0), lift=0.04)
    if studs:
        s.studs(*studs)
    if extra:
        extra(s)
    return s.finish(s.handle(metal(IRON, seed + 9), leather_chart(seed + 10)))


def royal_shield():
    paint = lambda o: field(lambda u, v, x, y: np.broadcast_to(np.array(ROYAL_BLUE), x.shape + (3,)), o, rough=0.5,
                            wear=0.22, seed=330)
    return _royal(paint, metal(STEEL, 331, rough=0.35), 0.07, metal(GOLD, 332, rough=0.3), seed=330)


def polished_royal_shield():
    paint = lambda o: field(lambda u, v, x, y: np.broadcast_to(np.array((0.12, 0.22, 0.65)), x.shape + (3,)), o,
                            rough=0.15, wear=0.0, seed=333, border=(0.13, 0.014, GOLD))
    gems = [(0.0, 0.33, 0.045, gem_chart(RUBY, 334)), (0.26, 0.22, 0.03, gem_chart(SAPPHIRE, 335)),
            (-0.26, 0.22, 0.03, gem_chart(SAPPHIRE, 335))]
    return _royal(paint, metal((0.92, 0.94, 0.97), 336, rough=0.12, metal_=0.9), 0.075, metal(GOLD, 337, rough=0.16),
                  gems=gems, seed=333)


def kingsguard_royal_shield():
    def colors(u, v, x, y):
        q = ((x > 0) ^ (y > 0.0))
        return np.where(q[..., None], np.array(ROYAL_RED), np.array(ROYAL_BLUE))

    paint = lambda o: field(colors, o, rough=0.25, wear=0.08, seed=340, border=(0.12, 0.012, GOLD))
    gold = metal(GOLD, 341, rough=0.2)

    def swords(s):
        blade = [(-0.035, -0.55), (0.035, -0.55), (0.035, 0.4), (0.0, 0.5), (-0.035, 0.4)]
        steel = metal((0.9, 0.92, 0.95), 342, rough=0.15)
        for side in (1, -1):
            b = pillow(blade, 0.02, 0.006, 0.02, chart=steel).rot([0, 0, 1], side * 35).move(0, -0.25, 0)
            s.on_face(b)
            guard = [(-0.13, -0.025), (0.13, -0.025), (0.13, 0.025), (-0.13, 0.025)]
            g = pillow(guard, 0.025, 0.012, 0.01, chart=gold).move(0, -0.42, 0).rot([0, 0, 1], side * 35)
            s.on_face(g.move(0, -0.25, 0), lift=0.01)
        p = np.asarray(s.outline)
        top = p[:, 1].max()
        for side in (1, -1):
            cap = [(0, 0), (0.25, 0), (0, -0.25)]
            c = pillow([(side * x, y) for x, y in cap], 0.03, 0.015, 0.02, chart=gold)
            s.on_face(c.move(side * 0.98, top - 0.04, 0), lift=0.0)

    gems = [(0.0, 0.33, 0.045, gem_chart(SAPPHIRE, 343))]
    return _royal(paint, gold, 0.08, gold, crown_y=0.48, crown_size=(0.7, 0.5), gems=gems, extra=swords,
                  studs=(gold, 14, 0.06, 0.03), seed=340)


def sunward_royal_shield():
    def colors(u, v, x, y):
        a = np.arctan2(y - 0.25, x)
        rays = (np.sin(a * 20) > 0.35) & (np.hypot(x, y - 0.25) > 0.45)
        return np.where(rays[..., None], np.array(PALE_GOLD), np.array(IVORY))

    def mm(u, v, x, y):
        a = np.arctan2(y - 0.25, x)
        return ((np.sin(a * 20) > 0.35) & (np.hypot(x, y - 0.25) > 0.45)).astype(float)

    paint = lambda o: field(colors, o, mm, rough=0.2, wear=0.0, seed=350, border=(0.13, 0.016, GOLD))
    gold = metal(GOLD, 351, rough=0.18)

    def orbs(s):
        p = np.asarray(s.outline)
        top = p[:, 1].max()
        oc = Chart(0.2, 0.2, P.enamel((1.0, 0.55, 0.1), rough=0.08, glow=0.5), "orb")
        for side in (1, -1):
            s.on_face(gem("cabochon", (0.08, 0.08, 0.05), chart=oc).move(side * 0.72, top - 0.2, 0), lift=0.0)
        halo = [(0.5 * math.sin(a), 0.5 * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
        hole = [(0.44 * math.sin(a), 0.44 * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
        s.on_face(pillow(halo, 0.02, 0.01, 0.01, chart=gold, holes=[hole]).move(0, 0.25, 0))

    gems = [(0.0, 0.33, 0.05, gem_chart(RUBY, 352)), (0.26, 0.22, 0.03, gem_chart(RUBY, 353)),
            (-0.26, 0.22, 0.03, gem_chart(RUBY, 353))]
    return _royal(paint, gold, 0.08, gold, gems=gems, extra=orbs, seed=350)


def sovereign_royal_shield():
    def colors(u, v, x, y):
        n = np.sin(x * 9) * np.sin(y * 9)
        return np.array(PURPLE) * (1 + 0.15 * n)[..., None]

    paint = lambda o: field(colors, o, rough=0.18, wear=0.0, seed=360, border=(0.16, 0.018, GOLD), filigree=True)
    gold = metal(GOLD, 361, rough=0.16)
    silver = metal((0.92, 0.94, 0.97), 362, rough=0.12, metal_=0.9)

    def regalia(s):
        s.rim(silver, r=0.03, n=120, inset=0.2)
        p = np.asarray(s.outline)
        top = p[:, 1].max()
        crest = pillow(crown_shape(1.0, 0.55), 0.06, 0.02, 0.04, chart=gold)
        s.pieces.append(crest.move(0, top + 0.27, s.z(0, top) + 0.0))
        for k, x in enumerate((-0.25, 0.0, 0.25)):
            s.pieces.append(gem("brilliant", (0.045, 0.045, 0.03), chart=gem_chart(SAPPHIRE if k == 1 else RUBY, 363 + k))
                            .move(x, top + 0.18, s.z(0, top) + 0.06))
        wing = [(0.0, 0.0), (0.15, 0.1), (0.35, 0.35), (0.45, 0.6), (0.35, 0.5), (0.38, 0.65), (0.26, 0.48), (0.26, 0.6),
                (0.15, 0.4), (0.08, 0.2)]
        wc = Chart(0.5, 0.7, P.feather(GOLD, tip=PALE_GOLD, barb=0.035, metal=0.85, rough=0.25, seed=366), "wing")
        for side in (1, -1):
            w = pillow([(side * x, y) for x, y in wing], 0.03, 0.008, 0.03, chart=wc).scale(1.3)
            s.pieces.append(w.rot([0, 0, 1], -side * 15).move(side * 0.95, top - 0.75, s.z(1.0, top - 0.5) - 0.02))
        dc = gem_chart(DIAMOND, 367)
        q = resample(s.outline, 10)
        for x, y in q:
            s.on_face(gem("brilliant", (0.035, 0.035, 0.025), chart=dc).move(x * 0.86, y * 0.86 + s.cy * 0.14, 0),
                      lift=0.02)

    gems = [(0.0, 0.4, 0.07, gem_chart(SAPPHIRE, 368)), (0.3, 0.27, 0.04, gem_chart(RUBY, 369)),
            (-0.3, 0.27, 0.04, gem_chart(RUBY, 369)), (0.0, 0.06, 0.04, gem_chart(EMERALD, 370))]
    return _royal(paint, gold, 0.09, gold, crown_size=(0.95, 0.7), crown_y=0.2, gems=gems, extra=regalia, seed=360)


SHIELDS = {"Shield": shield, "OakBuckler": oak_buckler, "WardensShield": wardens_shield,
           "SunburstShield": sunburst_shield, "DragonscaleAegis": dragonscale_aegis, "RoyalShield": royal_shield,
           "PolishedRoyalShield": polished_royal_shield, "KingsguardRoyalShield": kingsguard_royal_shield,
           "SunwardRoyalShield": sunward_royal_shield, "SovereignRoyalShield": sovereign_royal_shield}
