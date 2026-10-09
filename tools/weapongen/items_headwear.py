"""Crowns and helmets. Sized for a default R15 head (about 1.2 studs); origin = head centre,
front faces -Z (Roblox forward), so they can be used as hat accessories."""
import math

import numpy as np

from core import (Chart, P, crown_band, cylinder_wrap, dome_shell, gem, lathe, layers, noise, pillow, smooth, tube,
                  voronoi, engrave_filigree)
from items_jewelry import DIAMOND, EMERALD, circle, star_outline
from items_vessels import SILVER
from weapons import AMETHYST, CYAN, GOLD, PALE_GOLD, RUBY, SAPPHIRE, gem_chart, sym

STEEL = (0.72, 0.74, 0.78)
DARK_IRON = (0.2, 0.19, 0.2)


def metal(color, seed=0, rough=0.25, ornate=False, size=0.8, metal_=0.88, var=0.15):
    return Chart(size, size, P.metal(color, rough=rough, var=var, seed=seed, metal=metal_,
                                     engrave=engrave_filigree(density=4.0, dirt=0.3) if ornate else None), "metal")


def on_ring(piece, theta, R, y, face_out=True):
    """Place a piece built facing +Z onto a ring of radius R at angle theta (0 = front, -Z)."""
    if face_out:
        piece.rot([0, 1, 0], 180)
    return piece.move(0, y, -R).rot([0, 1, 0], -math.degrees(theta))


def ball(r, chart, segs=10):
    a = np.linspace(0, math.pi, 7)
    return lathe([(r * math.sin(t), -r * math.cos(t)) for t in a], chart, segs=segs)


# =============================================================== CROWNS

CROWN_R, CROWN_Y = 0.6, 0.32


def crown():
    gold = metal(GOLD, 200)
    n = 6

    def h(th):
        k = np.abs(((th * n / (2 * math.pi)) % 1) - 0.5) * 2         # 1 at a point, 0 between
        return 0.16 + 0.24 * k ** 1.6

    body = Chart(2 * math.pi * CROWN_R, 0.4, P.metal(GOLD, rough=0.22, var=0.15, seed=201, metal=0.88,
                                                     engrave=engrave_filigree(density=3.0, dirt=0.3)), "band")
    pieces = [crown_band(CROWN_R, h, 0.05, segs=n * 12, chart=body, base=CROWN_Y, flare=0.15)]
    pieces.append(lathe([(CROWN_R - 0.02, CROWN_Y - 0.01), (CROWN_R + 0.045, CROWN_Y), (CROWN_R + 0.05, CROWN_Y + 0.04),
                         (CROWN_R + 0.04, CROWN_Y + 0.05), (CROWN_R - 0.02, CROWN_Y + 0.05)], gold, segs=48, hard=(1, 3)))
    for k in range(n):
        th = k * 2 * math.pi / n
        pieces.append(on_ring(ball(0.04, gold), th, CROWN_R + 0.15 * 0.4, CROWN_Y + 0.43, face_out=False))
    rc = gem_chart(RUBY, 202)
    for k in range(n):
        th = (k + 0.5) * 2 * math.pi / n
        pieces.append(on_ring(gem("brilliant", (0.045, 0.045, 0.03), chart=rc), th, CROWN_R + 0.04, CROWN_Y + 0.13))
    return pieces


def silver_circlet():
    silver = metal((0.92, 0.94, 0.98), 203, rough=0.15, metal_=0.7)

    def h(th):
        d = np.abs(np.angle(np.exp(1j * th)))                      # distance from the front
        return 0.06 + 0.3 * np.exp(-(d / 0.3) ** 2) + 0.06 * np.exp(-((d - 0.6) / 0.15) ** 2)

    body = Chart(2 * math.pi * 0.62, 0.36, P.metal((0.92, 0.94, 0.98), rough=0.15, var=0.1, seed=204, metal=0.7,
                                                  engrave=engrave_filigree(density=5.0, dirt=0.3)), "band")
    pieces = [crown_band(0.62, h, 0.03, segs=120, chart=body, base=0.22, flare=0.05)]
    # Filigree swirls rising either side of the stone.
    for side in (1, -1):
        t = np.linspace(0, 1.6 * math.pi, 26)
        r = 0.07 * (1 - t / (2.2 * math.pi))
        path = np.column_stack([side * (0.06 + r * np.cos(t) + 0.04 * t / math.pi), 0.36 + r * np.sin(t), np.zeros_like(t)])
        sw = tube(path, 0.009, chart=silver, segs=5, up=(0, 0, 1))
        pieces.append(sw.deform(cylinder_wrap(0.64)))
    pieces.append(on_ring(gem("brilliant", (0.07, 0.1, 0.05), chart=gem_chart(SAPPHIRE, 205), n=10), 0, 0.65, 0.36))
    t = np.linspace(0, 2 * math.pi, 28, endpoint=False)
    bez = tube(np.column_stack([0.075 * np.sin(t), 0.36 + 0.1 * np.cos(t), np.zeros_like(t)]), 0.012, chart=silver,
               segs=5, closed=True, up=(0, 0, 1))
    pieces.append(bez.deform(cylinder_wrap(0.645)))
    dc = gem_chart(DIAMOND, 206)
    for side in (1, -1):
        for k, th in enumerate((0.45, 0.8, 1.15)):
            pieces.append(on_ring(gem("brilliant", (0.022 - 0.004 * k, 0.022 - 0.004 * k, 0.015), chart=dc),
                                  side * th, 0.64, 0.25 + 0.04 * (k == 0)))
    return pieces


def jeweled_crown():
    gold = metal(GOLD, 207)
    n = 8

    def h(th):
        f = (th * n / (2 * math.pi)) % 1
        k = np.abs(f - 0.5) * 2
        big = (np.floor(th * n / (2 * math.pi)) % 2 == 0)
        return 0.18 + np.where(big, 0.25, 0.14) * smooth(k, 0.55, 1.0)

    body = Chart(2 * math.pi * CROWN_R, 0.45, P.metal(GOLD, rough=0.2, var=0.15, seed=208, metal=0.88,
                                                      engrave=engrave_filigree(density=3.0, dirt=0.3)), "band")
    pieces = [crown_band(CROWN_R, h, 0.05, segs=n * 12, chart=body, base=CROWN_Y, flare=0.1)]
    # Ermine trim.
    def ermine(nu, nv, su, sv):
        L = P.hair((0.95, 0.94, 0.9), seed=209)(nu, nv, su, sv)
        r = np.random.default_rng(210)
        vv, uu = np.mgrid[0:nv, 0:nu]
        for _ in range(14):
            cx, cy = r.uniform(0, nu), r.uniform(0.3, 0.7) * nv
            m = np.exp(-(((uu - cx) / (0.02 * nu)) ** 2 + ((vv - cy) / (0.12 * nv)) ** 2))
            L["color"] *= (1 - 0.9 * m)[..., None]
        L["rough"][:] = 0.9
        return L
    pieces.append(lathe([(CROWN_R - 0.02, CROWN_Y - 0.06), (CROWN_R + 0.06, CROWN_Y - 0.04), (CROWN_R + 0.09, CROWN_Y + 0.02),
                         (CROWN_R + 0.06, CROWN_Y + 0.08), (CROWN_R - 0.02, CROWN_Y + 0.1)], painter=ermine, segs=40,
                        name="ermine"))
    # Velvet cap and arches meeting at an orb and cross.
    vel = Chart(3.0, 1.0, P.velvet((0.55, 0.04, 0.1), seed=211), "velvet")
    cap = [(CROWN_R - 0.03, CROWN_Y + 0.12)] + [(0.57 * math.cos(a), CROWN_Y + 0.12 + 0.42 * math.sin(a))
                                                 for a in np.linspace(0.1, math.pi / 2, 8)]
    pieces.append(lathe(cap, vel, segs=32))
    top = CROWN_Y + 0.62
    for ang in (0, 90):
        a = np.linspace(0.04, math.pi - 0.04, 24)
        path = np.column_stack([0.6 * np.cos(a), CROWN_Y + 0.38 + 0.24 * np.sin(a) ** 0.8 * 1.05, np.zeros_like(a)])
        arch = tube(path, lambda t: 0.03 + 0.008 * math.sin(t * math.pi * 6) ** 2, chart=gold, segs=7, up=(0, 0, 1))
        pieces.append(arch.rot([0, 1, 0], ang + 45))
    pieces.append(ball(0.07, gold, segs=14).move(0, top + 0.05, 0))
    pieces.append(lathe([(0.0, top + 0.1), (0.03, top + 0.1), (0.03, top + 0.13), (0.0, top + 0.13)], gold, segs=8))
    cross = [(-0.018, 0), (0.018, 0), (0.018, 0.09), (0.05, 0.09), (0.05, 0.125), (0.018, 0.125), (0.018, 0.16),
             (-0.018, 0.16), (-0.018, 0.125), (-0.05, 0.125), (-0.05, 0.09), (-0.018, 0.09)]
    pieces.append(pillow(cross, 0.02, 0.012, 0.01, chart=gold).move(0, top + 0.12, 0))
    charts = [gem_chart(RUBY, 212), gem_chart(SAPPHIRE, 213), gem_chart(EMERALD, 214)]
    for k in range(n * 2):
        th = k * math.pi / n
        big = k % 2 == 0
        g = gem("brilliant", (0.05, 0.05, 0.03) if big else (0.03, 0.03, 0.02), chart=charts[k % 3])
        pieces.append(on_ring(g, th, CROWN_R + 0.05, CROWN_Y + 0.2))
    for k in range(n):
        th = (k + 0.5) * 2 * math.pi / n
        hh = 0.18 + (0.25 if k % 2 == 0 else 0.14)
        pieces.append(on_ring(ball(0.028, gold), th, CROWN_R + 0.065, CROWN_Y + hh + 0.02, face_out=False))
    return pieces


def frost_queens_crown():
    silver = metal((0.92, 0.95, 1.0), 215, rough=0.12, metal_=0.65)
    body = Chart(2 * math.pi * CROWN_R, 0.2, P.metal((0.92, 0.95, 1.0), rough=0.12, var=0.1, seed=216, metal=0.65,
                                                     engrave=engrave_filigree(density=4.0, dirt=0.2)), "band")
    pieces = [crown_band(CROWN_R, lambda th: 0.1 + 0.04 * np.cos(th * 12) ** 2, 0.04, segs=96, chart=body,
                         base=CROWN_Y, flare=0.1)]
    ice = Chart(0.3, 0.04, P.gem((0.65, 0.9, 1.0), 217), "ice")
    n = 14
    for k in range(n):
        th = k * 2 * math.pi / n
        d = abs(math.atan2(math.sin(th), math.cos(th)))
        hgt = 0.18 + 0.32 * math.exp(-(d / 0.9) ** 2) + 0.06 * (k % 2)
        c = gem("crystal", (0.035 + 0.01 * (k % 2 == 0), hgt / 2, 0.035), chart=ice).move(0, hgt / 2, 0)
        c.rot([1, 0, 0], -12)          # lean outward
        pieces.append(c.move(0, CROWN_Y + 0.08, -CROWN_R - 0.02).rot([0, 1, 0], -math.degrees(th)))
    # Snowflake at the front.
    flake = []
    for k in range(12):
        a = k * math.pi / 6
        r = 0.13 if k % 2 == 0 else 0.05
        flake.append((r * math.sin(a), r * math.cos(a)))
    pieces.append(on_ring(pillow(flake, 0.018, 0.008, 0.012, chart=silver), 0, CROWN_R + 0.05, CROWN_Y + 0.2, face_out=True))
    pieces.append(on_ring(gem("brilliant", (0.045, 0.045, 0.03), chart=gem_chart(DIAMOND, 218)), 0, CROWN_R + 0.075,
                          CROWN_Y + 0.2))
    cc = gem_chart(CYAN, 219)
    for k in range(1, 12):
        if k == 6:
            continue
        pieces.append(on_ring(gem("brilliant", (0.02, 0.02, 0.014), chart=cc), k * math.pi / 6, CROWN_R + 0.04,
                              CROWN_Y + 0.05))
    return pieces


def dragon_crown():
    dark_gold = (0.55, 0.38, 0.16)
    gold = metal(dark_gold, 220, rough=0.3)
    horn_c = Chart(0.4, 1.0, P.metal((0.18, 0.15, 0.14), rough=0.35, var=0.3, seed=221, metal=0.6), "horn")
    scales = P.scales((0.35, 0.08, 0.06), tip=(0.85, 0.3, 0.12), size=0.07, metal=0.75, rough=0.3, seed=222)

    def h(th):
        d = np.abs(np.angle(np.exp(1j * th)))
        spikes = np.abs(((th * 10 / (2 * math.pi)) % 1) - 0.5) * 2
        return 0.14 + 0.1 * spikes ** 2 + 0.16 * np.exp(-(d / 0.25) ** 2)

    body = Chart(2 * math.pi * CROWN_R, 0.4, scales, "scales")
    pieces = [crown_band(CROWN_R, h, 0.055, segs=120, chart=body, base=CROWN_Y, flare=0.08)]
    pieces.append(lathe([(CROWN_R - 0.02, CROWN_Y - 0.02), (CROWN_R + 0.05, CROWN_Y), (CROWN_R + 0.05, CROWN_Y + 0.04),
                         (CROWN_R - 0.02, CROWN_Y + 0.05)], gold, segs=48, hard=(1, 2)))
    # Swept-back horns.
    for side in (1, -1):
        t = np.linspace(0, 1, 18)
        path = np.column_stack([side * (0.55 + 0.18 * np.sin(t * 2)), CROWN_Y + 0.12 + 0.3 * t, 0.05 + 0.4 * t ** 1.5])
        horn = tube(path, lambda tt: 0.09 * (1 - tt) ** 0.8 + 0.004, chart=horn_c, segs=10, up=(0, 1, 0))
        pieces.append(horn)
        for k in range(2):
            t2 = np.linspace(0, 1, 8)
            th = side * (0.9 + 0.5 * k)
            p2 = np.column_stack([np.zeros_like(t2), 0.15 * t2 + 0.05 * t2 ** 2, -0.04 * t2])
            sp = tube(p2, lambda tt: 0.03 * (1 - tt) + 0.003, chart=horn_c, segs=6, up=(0, 0, 1))
            pieces.append(sp.move(0, CROWN_Y + 0.2, -CROWN_R - 0.02).rot([0, 1, 0], -math.degrees(th)))
    # Dragon eye at the front.
    eye = Chart(0.2, 0.2, lambda nu, nv, su, sv: _dragon_eye(nu, nv), "eye")
    pieces.append(on_ring(gem("cabochon", (0.07, 0.05, 0.035), chart=eye), 0, CROWN_R + 0.03, CROWN_Y + 0.17))
    t = np.linspace(0, 2 * math.pi, 28, endpoint=False)
    rimp = tube(np.column_stack([0.08 * np.sin(t), CROWN_Y + 0.17 + 0.06 * np.cos(t), np.zeros_like(t)]), 0.014,
                chart=gold, segs=5, closed=True, up=(0, 0, 1))
    pieces.append(rimp.deform(cylinder_wrap(CROWN_R + 0.04)))
    return pieces


def _dragon_eye(nu, nv):
    vv, uu = np.mgrid[0:nv, 0:nu]
    u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
    n = noise(nv, nu, nu * 0.1, octaves=3, seed=223)
    r = np.hypot(u - 0.5, v - 0.5)
    col = np.array([1.0, 0.6, 0.05]) * (1 - r[..., None]) + np.array([0.7, 0.05, 0.02]) * r[..., None]
    col = col * (0.8 + 0.3 * n)[..., None]
    slit = np.exp(-((u - 0.5) / 0.03) ** 2) * (np.abs(v - 0.5) < 0.42)
    col = col * (1 - slit[..., None])
    return layers(nu, nv, col, 0.0, 0.05, emit=col * 0.8)


# =============================================================== HELMETS

def rivets(points, chart, r=0.02):
    out = []
    for p, n in points:
        rv = lathe([(0, 0), (r, 0), (r * 0.8, r * 0.5), (0, r * 0.7)], chart, segs=6)
        n = np.asarray(n, float) / np.linalg.norm(n)
        # Rotate +Y onto n.
        ax = np.cross([0, 1, 0], n)
        ang = math.degrees(math.acos(np.clip(n[1], -1, 1)))
        if np.linalg.norm(ax) > 1e-6:
            rv.rot(ax, ang)
        out.append(rv.move(*p))
    return out


def shell_point(rx, ry, rz, phi, th, c=(0, 0, 0), peak=0.0):
    y = ry * math.cos(phi) + peak * max(0.0, 1 - phi / 0.9) ** 2
    p = np.array([rx * math.sin(phi) * math.sin(th), y, -rz * math.sin(phi) * math.cos(th)]) + c
    n = np.array([math.sin(phi) * math.sin(th) / rx, math.cos(phi) / ry, -math.sin(phi) * math.cos(th) / rz])
    return p, n


def meridian(rx, ry, rz, th, phi0, phi1, chart, c=(0, 0, 0), r=0.025, peak=0.0, out=0.012):
    phis = np.linspace(phi0, phi1, 14)
    pts = []
    for ph in phis:
        p, n = shell_point(rx, ry, rz, ph, th, c, peak)
        pts.append(p + out * n / np.linalg.norm(n))
    return tube(np.array(pts), r, chart=chart, segs=6, up=(0, 1, 0) if abs(math.sin(th)) > 0.5 else (1, 0, 0),
                aspect=0.45, superellipse=3)


def helmet():
    steel = Chart(4.5, 1.6, P.metal(STEEL, rough=0.3, var=0.25, seed=230, metal=0.85), "steel")
    bronze = metal((0.82, 0.6, 0.32), 231)
    rx, ry, rz, c = 0.72, 0.74, 0.76, (0, -0.02, 0)
    rim_phi = 1.62
    pieces = dome_shell(rx, ry, rz, rim=lambda th: rim_phi + 0 * th, thick=0.05, segs=40, rings=12, chart=steel,
                        peak=0.12, center=c)
    # Brow band.
    th = np.linspace(0, 2 * math.pi, 49)
    band_y = c[1] + ry * math.cos(rim_phi) + 0.05
    pieces.append(lathe([(rx * math.sin(rim_phi) - 0.01, band_y - 0.07), (rx * math.sin(rim_phi) + 0.025, band_y - 0.06),
                         (rx * math.sin(rim_phi) + 0.025, band_y + 0.05), (rx * math.sin(rim_phi) - 0.01, band_y + 0.06)],
                        bronze, segs=40, hard=(1, 2), sz=rz / rx))
    for t in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
        pieces.append(meridian(rx, ry, rz, t, 0.05, rim_phi - 0.08, bronze, c, peak=0.12))
    # Nasal guard.
    nasal = [(-0.04, -0.3), (0.04, -0.3), (0.05, 0.0), (0.03, 0.08), (-0.03, 0.08), (-0.05, 0.0)]
    n = pillow(nasal, 0.02, 0.012, 0.01, chart=bronze).move(0, band_y - 0.02, 0)
    pieces.append(n.deform(cylinder_wrap(rz * math.sin(rim_phi) + 0.03)))
    rb_x, rb_z = rx * math.sin(rim_phi) + 0.025, rz * math.sin(rim_phi) + 0.025
    pts = []
    for k in range(16):
        t = k * 2 * math.pi / 16 + math.pi / 16
        pts.append(((rb_x * math.sin(t), band_y, -rb_z * math.cos(t)), (math.sin(t), 0, -math.cos(t))))
    pieces += rivets(pts, bronze, 0.018)
    return pieces


def scouts_cap():
    leather = Chart(4.0, 1.4, P.leather((0.42, 0.24, 0.12), seed=232,
                                        stitch=[('u', u) for u in (0.02, 0.25, 0.5, 0.75, 0.98)]), "leather")
    rx, ry, rz, c = 0.69, 0.66, 0.72, (0, -0.02, 0)
    pieces = dome_shell(rx, ry, rz, rim=lambda th: 1.55 + 0.25 * smooth(np.abs(np.angle(np.exp(1j * th))), 0.8, 1.6),
                        thick=0.04, segs=36, rings=10, chart=leather, center=c)
    fur = Chart(0.6, 0.5, P.hair((0.82, 0.74, 0.6), seed=233), "fur")
    flap = sym([(0, 0.1), (0.14, 0.1), (0.15, -0.12), (0.1, -0.22), (0, -0.24)])
    for side in (1, -1):
        f = pillow(flap, 0.03, 0.02, 0.02, chart=leather, back_chart=fur)
        for p in f:
            p.move(0, c[1] - 0.1, 0).deform(cylinder_wrap(0.71)).rot([0, 1, 0], -side * 90)
        pieces += f
    brim = [(-0.42, 0.06), (0.42, 0.06), (0.36, -0.06), (0.0, -0.22), (-0.36, -0.06)]
    b = pillow(brim, 0.018, 0.012, 0.02, chart=leather).rot([1, 0, 0], 90).rot([1, 0, 0], -18)
    pieces.append(b.deform(lambda v: v + np.column_stack([0 * v[:, 0], -0.25 * v[:, 0] ** 2, 0 * v[:, 0]]))
                  .move(0, c[1] + 0.02, -0.64))
    feather = sym([(0, 0), (0.035, 0.06), (0.05, 0.25), (0.035, 0.45), (0, 0.6)])
    fc = Chart(0.12, 0.6, P.feather((0.25, 0.45, 0.2), tip=(0.85, 0.75, 0.4), seed=234, barb=0.025), "feather")
    fp = pillow(feather, 0.008, 0.003, 0.008, chart=fc)
    fp.deform(lambda v: v + np.column_stack([0 * v[:, 0], 0 * v[:, 0], 0.25 * (v[:, 1] / 0.6) ** 2]))
    pieces.append(fp.rot([0, 0, 1], -40).rot([0, 1, 0], 70).move(0.62, 0.25, 0.15))
    pieces.append(lathe([(0, 0), (0.05, 0), (0.04, 0.02), (0, 0.025)], metal(GOLD, 235), segs=10)
                  .rot([0, 0, 1], -90).move(0.67, 0.22, 0.12))
    return pieces


def _visor_paint(nu, nv, su, sv):
    L = P.metal(STEEL, rough=0.25, var=0.2, seed=236, metal=0.85)(nu, nv, su, sv)
    vv, uu = np.mgrid[0:nv, 0:nu]
    u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
    slit = np.zeros((nv, nu))
    for vc in (0.3, 0.38):                       # two eye slits across the visor
        slit += (np.abs(v - vc) < 0.018) * (np.abs(u - 0.5) < 0.36) * (np.abs(u - 0.5) > 0.03)
    holes = np.zeros((nv, nu))
    for row, vc in enumerate((0.58, 0.66, 0.74)):
        for k in range(-3, 4):
            cu = 0.5 + k * 0.06 + (0.03 if row % 2 else 0)
            holes += np.exp(-(((u - cu) / 0.012) ** 2 + ((v - vc) / 0.02) ** 2) * 3) > 0.5
    m = np.clip(slit + holes, 0, 1)
    L["color"] *= (1 - 0.95 * m)[..., None]
    L["height"] -= 0.006 * m
    L["rough"] = L["rough"] * (1 - m) + m
    L["metal"] *= (1 - m)
    return L


def knights_visor():
    steel = Chart(4.5, 1.8, P.metal(STEEL, rough=0.22, var=0.2, seed=237, metal=0.88), "steel")
    gold = metal(GOLD, 238)
    rx, ry, rz, c = 0.7, 0.78, 0.74, (0, -0.02, 0)
    pieces = dome_shell(rx, ry, rz, rim=lambda th: 2.25 + 0 * th, thick=0.045, segs=40, rings=14, chart=steel,
                        peak=0.28, center=c)
    # Snouted visor over the face.
    tv, p0, p1 = 1.15, 1.0, 2.3

    def visor(U, V):
        th = (U - 0.5) * 2 * tv
        ph = p0 + (p1 - p0) * V
        snout = 0.16 * np.cos(np.clip(th / tv, -1, 1) * math.pi / 2) ** 2 * np.sin(np.clip((ph - p0) / (p1 - p0), 0, 1) * math.pi) ** 1.2
        k = 1.06 + snout
        x = rx * k * np.sin(ph) * np.sin(th)
        y = c[1] + ry * 1.02 * np.cos(ph)
        z = -rz * k * np.sin(ph) * np.cos(th)
        return x, y, z

    vchart = Chart(1.6, 1.4, _visor_paint, "visor")
    from core import surface
    pieces.append(surface(visor, 21, 15, vchart, ref=lambda q: q - np.array(c)))
    pieces.append(surface(lambda U, V: tuple(np.asarray(a) for a in _shrink(visor(U, V), c, 0.97)), 21, 15, steel,
                          ref=lambda q: np.array(c) - q))
    # Visor pivots.
    for side in (1, -1):
        pieces.append(lathe([(0, 0), (0.06, 0), (0.06, 0.025), (0.03, 0.04), (0, 0.04)], gold, segs=12, hard=(1,))
                      .rot([0, 0, 1], -side * 90).move(side * (rx + 0.02), c[1] + ry * math.cos(p0 + 0.05), 0.0))
    # Gold rim trim and plume.
    th = np.linspace(0, 2 * math.pi, 64, endpoint=False)
    yr = c[1] + ry * math.cos(2.25) + 0.02
    pieces.append(tube(np.column_stack([rx * math.sin(2.25) * np.sin(th), np.full_like(th, yr),
                                        -rz * math.sin(2.25) * np.cos(th)]), 0.022, chart=gold, segs=6, closed=True,
                       up=(0, 1, 0)))
    plume_c = Chart(0.4, 1.2, P.hair((0.75, 0.06, 0.08), seed=239), "plume")
    t = np.linspace(0, 1, 20)
    path = np.column_stack([np.zeros_like(t), c[1] + ry + 0.3 + 0.25 * np.sin(t * 2.2) - 0.1 * t, 0.05 + 0.9 * t])
    pieces.append(tube(path, lambda tt: 0.05 + 0.1 * math.sin(tt * math.pi) ** 0.7, chart=plume_c, segs=10,
                       up=(1, 0, 0), aspect=0.5))
    pieces.append(lathe([(0, 0), (0.05, 0), (0.035, 0.12), (0.045, 0.14), (0, 0.15)], gold, segs=10)
                  .move(0, c[1] + ry + 0.18, 0.05))
    return pieces


def _shrink(xyz, c, k):
    x, y, z = xyz
    return (c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k, c[2] + (z - c[2]) * k)


def ember_helm():
    def ember(nu, nv, su, sv):
        ppu = nu / su
        L = P.metal(DARK_IRON, rough=0.4, var=0.35, seed=240, metal=0.75)(nu, nv, su, sv)
        e, _ = voronoi(nv, nu, 0.18 * ppu, seed=241, aspect=0.7)
        n = noise(nv, nu, 0.3 * ppu, octaves=3, seed=242)
        crack = np.exp(-e / 1.3) * smooth(n, 0.45, 0.7)
        glow = np.array([1.0, 0.4, 0.06])
        L["color"] = L["color"] * (1 - crack[..., None]) + glow * crack[..., None]
        L["emit"] = glow * 1.5 * crack[..., None]
        L["height"] -= 0.004 * crack
        return L

    shell_c = Chart(4.5, 1.8, ember, "shell")
    rx, ry, rz, c = 0.72, 0.74, 0.76, (0, -0.02, 0)

    def rim(th):
        d = np.abs(np.angle(np.exp(1j * th)))
        return 1.5 + 0.7 * smooth(d, 0.35, 0.8) - 0.15 * smooth(d, 2.0, 3.0)

    pieces = dome_shell(rx, ry, rz, rim=rim, thick=0.05, segs=48, rings=12, chart=shell_c, peak=0.08, center=c)
    horn_c = Chart(0.5, 1.4, P.metal((0.85, 0.78, 0.65), rough=0.45, var=0.3, seed=243, metal=0.2), "horn")
    for side in (1, -1):
        t = np.linspace(0, 1, 22)
        path = np.column_stack([side * (0.6 + 0.45 * np.sin(t * 1.6)), 0.15 + 0.25 * t + 0.55 * t ** 2.2,
                                -0.05 - 0.25 * np.sin(t * 2.5)])
        pieces.append(tube(path, lambda tt: 0.11 * (1 - tt) ** 0.85 + 0.004, chart=horn_c, segs=12, up=(0, 0, 1)))
    flame = [(0.0, 0.0), (0.2, 0.0), (0.42, 0.06), (0.5, 0.2), (0.4, 0.14), (0.35, 0.3), (0.26, 0.16), (0.18, 0.34),
             (0.1, 0.17), (0.0, 0.3), (-0.08, 0.14), (-0.2, 0.24), (-0.2, 0.08), (-0.35, 0.12), (-0.3, 0.0)]
    fc = Chart(0.9, 0.4, P.feather((1.0, 0.35, 0.03), tip=(1.0, 0.85, 0.3), barb=0.05, glow=(1.0, 0.45, 0.05), seed=244),
               "flame")
    crest = pillow(flame, 0.03, 0.008, 0.03, chart=fc).rot([0, 1, 0], 90)
    pieces.append(crest.move(0, c[1] + ry + 0.05, 0.05))
    gold = metal((0.9, 0.55, 0.2), 245)
    th = np.linspace(-1.2, 1.2, 30)
    pieces.append(tube(np.column_stack([(rx + 0.012) * np.sin(1.5) * np.sin(th), c[1] + ry * math.cos(1.5) + 0.0 * th,
                                        -(rz + 0.012) * math.sin(1.5) * np.cos(th)]), 0.022, chart=gold, segs=6,
                       up=(0, 1, 0)))
    pieces.append(on_ring(gem("brilliant", (0.055, 0.055, 0.035), chart=gem_chart((1.0, 0.35, 0.05), 246)), 0, rz + 0.01,
                          c[1] + ry * math.cos(1.25)))
    return pieces


def champions_helm():
    steel = Chart(4.5, 1.8, P.metal((0.86, 0.88, 0.92), rough=0.14, var=0.15, seed=250, metal=0.9), "steel")
    gold = metal(GOLD, 251, ornate=True)
    rx, ry, rz, c = 0.72, 0.76, 0.76, (0, -0.02, 0)

    def rim(th):
        d = np.abs(np.angle(np.exp(1j * th)))
        return 2.25 - 0.62 * np.exp(-(d / 0.2) ** 4)            # Corinthian slot at the front

    pieces = dome_shell(rx, ry, rz, rim=rim, thick=0.05, segs=56, rings=14, chart=steel, center=c)
    # Gold brow ridge.
    th = np.linspace(-1.9, 1.9, 40)
    ph = 1.45
    pieces.append(tube(np.column_stack([(rx + 0.015) * math.sin(ph) * np.sin(th), np.full_like(th, c[1] + ry * math.cos(ph)),
                                        -(rz + 0.015) * math.sin(ph) * np.cos(th)]), 0.028, chart=gold, segs=6,
                       up=(0, 1, 0), aspect=1.6))
    # Feathered gold wings.
    wing = [(0.0, 0.0), (0.12, 0.08), (0.28, 0.2), (0.45, 0.42), (0.36, 0.36), (0.4, 0.5), (0.28, 0.36), (0.3, 0.48),
            (0.18, 0.32), (0.18, 0.42), (0.08, 0.25), (0.02, 0.12)]
    wc = Chart(0.5, 0.5, P.feather(GOLD, tip=PALE_GOLD, barb=0.03, metal=0.85, rough=0.25, seed=252), "wing")
    for side in (1, -1):
        w = pillow([(side * x, y) for x, y in wing], 0.022, 0.006, 0.02, chart=wc).scale(1.7)
        pieces.append(w.rot([0, 0, 1], side * 10).rot([0, 1, 0], -side * 75).move(side * (rx - 0.02), c[1] - 0.02, 0.1))
    # Horsehair crest from brow to nape.
    crest = []
    for a in np.linspace(0.25, math.pi - 0.15, 20):
        crest.append((0.95 * math.cos(a) - 0.1, 1.12 * math.sin(a)))
    for a in np.linspace(math.pi - 0.15, 0.25, 20):
        crest.append((0.7 * math.cos(a) - 0.02, 0.7 * math.sin(a)))
    hc = Chart(2.0, 1.0, P.hair((0.78, 0.07, 0.07), seed=253), "crest")
    cr = pillow(crest, 0.07, 0.03, 0.05, chart=hc).rot([0, 1, 0], 90)
    pieces.append(cr.move(0, c[1] - 0.05, 0))
    pieces.append(meridian(rx, ry, rz, 0.0, 0.1, 1.3, gold, c, r=0.03))
    pieces.append(on_ring(gem("brilliant", (0.06, 0.06, 0.035), chart=gem_chart(SAPPHIRE, 254)), 0, rz + 0.04,
                          c[1] + ry * math.cos(1.28)))
    return pieces


CROWNS = {"Crown": crown, "SilverCirclet": silver_circlet, "JeweledCrown": jeweled_crown,
          "FrostQueensCrown": frost_queens_crown, "DragonCrown": dragon_crown}
HELMETS = {"Helmet": helmet, "ScoutsCap": scouts_cap, "KnightsVisor": knights_visor, "EmberHelm": ember_helm,
           "ChampionsHelm": champions_helm}
