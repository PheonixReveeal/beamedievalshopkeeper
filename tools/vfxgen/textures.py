"""Particle / trail / beam textures for the weapon VFX.

Every texture is white with the shape in the alpha channel, so one texture can be tinted any
colour by the ParticleEmitter/Trail/Beam Color. Flipbooks use Roblox's grid layouts
(FlipbookLayout = Grid2x2 / Grid4x4) and are square.

Usage:  python textures.py <out_dir>
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

rng = np.random.default_rng(11)


def grid(n):
    y, x = np.mgrid[0:n, 0:n]
    return (x + 0.5) / n * 2 - 1, (y + 0.5) / n * 2 - 1        # -1..1, y down


def noise(h, w, cell, octaves=4, seed=0):
    r = np.random.default_rng(seed)
    out, amp, tot = np.zeros((h, w)), 1.0, 0.0
    for o in range(octaves):
        gh, gw = max(2, int(h / cell * 2 ** o)) + 1, max(2, int(w / cell * 2 ** o)) + 1
        g = r.random((gh, gw)).astype(np.float32)
        out += amp * np.asarray(Image.fromarray(g, "F").resize((w, h), Image.BICUBIC))
        tot += amp
        amp *= 0.5
    out /= tot
    return (out - out.min()) / (np.ptp(out) + 1e-9)


def tile_noise(h, w, cell, octaves=4, seed=0):
    """Horizontally tileable noise (for beams/trails that wrap along U)."""
    n = noise(h, w * 2, cell, octaves, seed)
    t = np.linspace(0, 1, w)[None, :]
    return n[:, :w] * (1 - t) + n[:, w:] * t


def save(alpha, path, rgb=None):
    a = np.clip(alpha, 0, 1)
    h, w = a.shape
    out = np.ones((h, w, 4))
    if rgb is not None:
        out[..., :3] = rgb
    out[..., 3] = a
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA").save(path, optimize=True)


def sheet(frames, n):
    """Arrange n*n frames (each HxW) into a flipbook grid, row-major from the top-left."""
    h, w = frames[0].shape
    out = np.zeros((h * n, w * n))
    for i, f in enumerate(frames):
        r, c = divmod(i, n)
        out[r * h:(r + 1) * h, c * w:(c + 1) * w] = f
    return out


def edge_fade(a, margin=0.08):
    """Force the border to transparent so sprites never show hard square edges."""
    h, w = a.shape
    y = np.minimum(np.arange(h), np.arange(h)[::-1]) / (h * margin)
    x = np.minimum(np.arange(w), np.arange(w)[::-1]) / (w * margin)
    return a * np.clip(y, 0, 1)[:, None] * np.clip(x, 0, 1)[None, :]


# ------------------------------------------------------------------ sprites

def glow(n=256):
    x, y = grid(n)
    r = np.hypot(x, y)
    return edge_fade(np.exp(-(r / 0.42) ** 2) * 0.9 + 0.1 * np.exp(-(r / 0.85) ** 2))


def spark(n=256):
    x, y = grid(n)
    r = np.hypot(x, y)
    cross = np.maximum(np.exp(-np.abs(x) * 7) * np.exp(-(y / 0.035) ** 2),
                       np.exp(-np.abs(y) * 7) * np.exp(-(x / 0.035) ** 2))
    xd, yd = (x + y) / math.sqrt(2), (x - y) / math.sqrt(2)
    diag = np.maximum(np.exp(-np.abs(xd) * 14) * np.exp(-(yd / 0.03) ** 2),
                      np.exp(-np.abs(yd) * 14) * np.exp(-(xd / 0.03) ** 2)) * 0.5
    return edge_fade(np.clip(cross + diag + np.exp(-(r / 0.12) ** 2), 0, 1))


def star(n=256):
    """Long-rayed sun flare."""
    x, y = grid(n)
    r, a = np.hypot(x, y), np.arctan2(y, x)
    rays = np.zeros_like(r)
    for k, (ang, length) in enumerate([(0, 1.0), (math.pi / 2, 1.0), (math.pi / 4, 0.55), (3 * math.pi / 4, 0.55),
                                        (math.pi / 8, 0.35), (3 * math.pi / 8, 0.35), (5 * math.pi / 8, 0.35),
                                        (7 * math.pi / 8, 0.35)]):
        d = np.abs(np.sin(a - ang)) * r
        rays = np.maximum(rays, np.exp(-(d / 0.02) ** 2) * np.exp(-r / (0.35 * length)))
    return edge_fade(np.clip(rays + np.exp(-(r / 0.16) ** 2) + 0.3 * np.exp(-(r / 0.45) ** 2), 0, 1))


def ember(n=128):
    x, y = grid(n)
    r = np.hypot(x, y)
    return edge_fade(np.clip(np.exp(-(r / 0.18) ** 2) * 1.2 + 0.35 * np.exp(-(r / 0.5) ** 2), 0, 1))


def orb(n=256):
    x, y = grid(n)
    r = np.hypot(x, y)
    core = np.exp(-(r / 0.25) ** 2)
    rim = np.exp(-((r - 0.55) / 0.06) ** 2) * 0.5
    halo = 0.35 * np.exp(-(r / 0.8) ** 2)
    return edge_fade(np.clip(core + rim + halo, 0, 1))


def ring(n=256):
    x, y = grid(n)
    r = np.hypot(x, y)
    return edge_fade(np.exp(-((r - 0.78) / 0.05) ** 2) + 0.35 * np.exp(-((r - 0.74) / 0.16) ** 2))


def bubble(n=128):
    x, y = grid(n)
    r = np.hypot(x, y)
    a = np.exp(-((r - 0.78) / 0.07) ** 2) * 0.9 + 0.12 * (r < 0.78)
    hl = np.exp(-(((x + 0.32) / 0.14) ** 2 + ((y + 0.32) / 0.09) ** 2))
    return edge_fade(np.clip(a + hl, 0, 1))


def droplet(n=128):
    x, y = grid(n)
    yy = y + 0.25
    w = np.where(yy > 0, np.sqrt(np.clip(1 - (yy / 0.55) ** 2, 0, 1)) * 0.5, 0.5 * np.clip(1 + yy / 0.9, 0, 1) ** 1.5)
    inside = np.clip((w - np.abs(x)) / 0.05, 0, 1) * (yy < 0.55) * (yy > -0.9)
    hl = np.exp(-(((x + 0.15) / 0.07) ** 2 + ((yy - 0.05) / 0.15) ** 2))
    return edge_fade(np.clip(inside * 0.55 + hl * 0.8 + inside * 0.3 * np.clip(-x, 0, 1), 0, 1))


def snowflake(n=256):
    img = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(img)
    c = n / 2
    for k in range(6):
        a = k * math.pi / 3
        ex, ey = c + math.cos(a) * n * 0.42, c + math.sin(a) * n * 0.42
        d.line([(c, c), (ex, ey)], fill=255, width=max(2, n // 40))
        for t, l in ((0.45, 0.14), (0.7, 0.1)):
            px, py = c + math.cos(a) * n * 0.42 * t, c + math.sin(a) * n * 0.42 * t
            for s in (1, -1):
                b = a + s * math.pi / 4
                d.line([(px, py), (px + math.cos(b) * n * l, py + math.sin(b) * n * l)], fill=255, width=max(2, n // 56))
    a = np.asarray(img.filter(ImageFilter.GaussianBlur(n / 160)), float) / 255
    x, y = grid(n)
    return edge_fade(np.clip(a + 0.25 * np.exp(-(np.hypot(x, y) / 0.15) ** 2), 0, 1))


def shards(n=512):
    """2x2 flipbook of ice-shard silhouettes (use FlipbookMode Random)."""
    frames = []
    for k in range(4):
        f = n // 2
        img = Image.new("L", (f, f), 0)
        d = ImageDraw.Draw(img)
        r = np.random.default_rng(100 + k)
        pts = []
        m = r.integers(5, 8)
        for i in range(m):
            a = i * 2 * math.pi / m + r.uniform(-0.2, 0.2)
            rad = f * (0.42 if i % 2 == 0 else r.uniform(0.12, 0.22)) * (1.0 if i != 0 else 1.1)
            pts.append((f / 2 + math.cos(a) * rad * 0.55, f / 2 + math.sin(a) * rad))
        d.polygon(pts, fill=200)
        for i in range(0, m, 2):
            d.line([(f / 2, f / 2), pts[i]], fill=255, width=2)
        a = np.asarray(img.filter(ImageFilter.GaussianBlur(1.2)), float) / 255
        frames.append(edge_fade(a, 0.04))
    return sheet(frames, 2)


def runes(n=512):
    """4x4 flipbook of glowing rune glyphs (use FlipbookMode Random)."""
    f = n // 4
    frames = []
    for k in range(16):
        r = np.random.default_rng(200 + k)
        img = Image.new("L", (f, f), 0)
        d = ImageDraw.Draw(img)
        lat = [(f * (0.3 + 0.2 * i), f * (0.2 + 0.2 * j)) for j in range(4) for i in range(3)]
        sp = r.integers(0, 3)
        strokes = [(sp, sp + 9)]
        for _ in range(r.integers(2, 4)):
            a = int(r.integers(0, 12))
            b = int(r.choice([x for x in range(12) if x != a and abs(x % 3 - a % 3) <= 1 and abs(x // 3 - a // 3) <= 2]))
            strokes.append((a, b))
        for a, b in strokes:
            d.line([lat[a], lat[b]], fill=255, width=max(2, f // 14))
        core = np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)), float) / 255
        halo = np.asarray(img.filter(ImageFilter.GaussianBlur(f / 14)), float) / 255
        frames.append(edge_fade(np.clip(core + 1.6 * halo, 0, 1), 0.04))
    return sheet(frames, 4)


def zaps(n=512):
    """2x2 flipbook of small forked electric arcs."""
    f = n // 2
    frames = []
    for k in range(4):
        r = np.random.default_rng(300 + k)
        img = Image.new("L", (f, f), 0)
        d = ImageDraw.Draw(img)

        def bolt(x0, y0, x1, y1, w, depth):
            pts = [(x0, y0)]
            for t in np.linspace(0, 1, 9)[1:-1]:
                pts.append((x0 + (x1 - x0) * t + r.normal(0, f * 0.05), y0 + (y1 - y0) * t + r.normal(0, f * 0.05)))
            pts.append((x1, y1))
            d.line(pts, fill=255, width=w)
            if depth:
                i = r.integers(2, 6)
                bx, by = pts[i]
                bolt(bx, by, bx + r.normal(0, f * 0.25), by + r.normal(0, f * 0.25), max(1, w - 1), depth - 1)

        a = r.uniform(0, math.pi)
        bolt(f / 2 - math.cos(a) * f * 0.42, f / 2 - math.sin(a) * f * 0.42, f / 2 + math.cos(a) * f * 0.42,
             f / 2 + math.sin(a) * f * 0.42, 3, 2)
        core = np.asarray(img.filter(ImageFilter.GaussianBlur(0.7)), float) / 255
        halo = np.asarray(img.filter(ImageFilter.GaussianBlur(f / 20)), float) / 255
        frames.append(edge_fade(np.clip(core + 2.0 * halo, 0, 1), 0.04))
    return sheet(frames, 2)


def flames(n=1024):
    """4x4 flipbook: a flame tongue licking upward and breaking apart."""
    f = n // 4
    base = noise(f * 4, f, f / 3, octaves=5, seed=7)
    frames = []
    y, x = np.mgrid[0:f, 0:f]
    u, v = (x + 0.5) / f * 2 - 1, (y + 0.5) / f              # v: 0 top .. 1 bottom
    for k in range(16):
        t = k / 16
        off = int(t * f * 3)
        nz = base[off:off + f] if off + f <= base.shape[0] else base[-f:]
        wob = (nz - 0.5) * 0.5
        height = 0.85 - 0.25 * t
        prof = np.clip((v - (1 - height)) / height, 0, 1)        # 0 at the tip .. 1 at the base
        width = 0.55 * np.sin(np.clip(prof, 0, 1) * math.pi * 0.85) ** 0.7 * (1 - 0.35 * t)
        d = np.abs(u + wob * (1 - prof) * 1.2) / np.maximum(width, 1e-3)
        body = np.clip(1 - d, 0, 1) ** 0.8 * (prof > 0)
        holes = np.clip((nz - 0.25 - 0.5 * t) * 3, 0, 1)
        a = body * (0.5 + 0.5 * holes) * (1 - 0.6 * t * (1 - prof))
        frames.append(edge_fade(np.clip(a * 1.3, 0, 1), 0.03))
    return sheet(frames, 4)


def smoke(n=1024):
    """4x4 flipbook: a soft puff that billows out and thins away."""
    f = n // 4
    frames = []
    x, y = grid(f)
    for k in range(16):
        t = k / 15
        nz = noise(f, f, f / 4, octaves=5, seed=50 + k // 2)
        r = np.hypot(x, y) / (0.62 + 0.3 * t)
        puff = np.clip(1 - r, 0, 1) ** 0.9
        a = puff * (0.6 + 0.8 * nz) * (1 - 0.7 * t) * 1.3
        frames.append(edge_fade(np.clip(a, 0, 1), 0.03))
    return sheet(frames, 4)


def mist(n=512):
    x, y = grid(n)
    nz = noise(n, n, n / 3, octaves=5, seed=60)
    r = np.hypot(x, y * 1.4)
    return edge_fade(np.clip((1 - r) * 1.2, 0, 1) ** 1.5 * (0.35 + 0.8 * nz) * 0.85)


def swirl(n=256):
    x, y = grid(n)
    r, a = np.hypot(x, y), np.arctan2(y, x)
    arms = 0.5 + 0.5 * np.cos(3 * a + r * 9)
    return edge_fade(np.clip(arms ** 3 * np.exp(-(r / 0.7) ** 2) * (1 - np.exp(-(r / 0.12) ** 2)) * 1.4 +
                             0.4 * np.exp(-(r / 0.15) ** 2), 0, 1))


def magic_circle(n=512):
    img = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(img)
    c = n / 2
    for rad, w in ((0.47, 3), (0.42, 2), (0.3, 2), (0.27, 1)):
        d.ellipse([c - rad * n, c - rad * n, c + rad * n, c + rad * n], outline=255, width=w)
    for off in (0.0, math.pi / 4):            # two overlapping squares -> eight-point star
        pts = [(c + math.cos(off + k * math.pi / 2) * 0.3 * n, c + math.sin(off + k * math.pi / 2) * 0.3 * n) for k in range(5)]
        d.line(pts, fill=255, width=2)
    r = np.random.default_rng(400)
    for k in range(24):                       # tick-runes between the outer rings
        a = k * 2 * math.pi / 24
        r0, r1 = 0.425 * n, 0.465 * n
        d.line([(c + math.cos(a) * r0, c + math.sin(a) * r0), (c + math.cos(a) * r1, c + math.sin(a) * r1)], fill=255, width=2)
        if r.random() < 0.6:
            b = a + 0.06
            d.line([(c + math.cos(a) * r1, c + math.sin(a) * r1), (c + math.cos(b) * r0, c + math.sin(b) * r0)], fill=255, width=1)
    core = np.asarray(img.filter(ImageFilter.GaussianBlur(0.6)), float) / 255
    halo = np.asarray(img.filter(ImageFilter.GaussianBlur(n / 80)), float) / 255
    return edge_fade(np.clip(core + 1.5 * halo, 0, 1), 0.02)


# ------------------------------------------------------------------ beams & trails (U wraps along the length)

def lightning(w=512, h=128):
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    r = np.random.default_rng(500)
    for strand, width in ((0, 4), (1, 2), (2, 1)):
        ys = np.cumsum(r.normal(0, h * 0.06, 33))
        ys = ys - np.linspace(ys[0], ys[-1], 33)           # start and end at the centre -> tiles along U
        ys = h / 2 + ys * (1.0 if strand == 0 else 0.8)
        xs = np.linspace(0, w, 33)
        d.line(list(zip(xs, ys)), fill=255 if strand == 0 else 170, width=width)
    core = np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)), float) / 255
    halo = np.asarray(img.filter(ImageFilter.GaussianBlur(h / 14)), float) / 255
    v = (np.arange(h) + 0.5) / h
    fade = np.exp(-((v - 0.5) / 0.4) ** 2)[:, None]
    return np.clip(core + 1.8 * halo, 0, 1) * fade


def trail_streak(w=512, h=128):
    v = (np.arange(h) + 0.5) / h
    nz = tile_noise(h, w, 24, octaves=3, seed=600)
    streaks = tile_noise(h, w, 6, octaves=2, seed=601)
    lines = 0.5 + 0.5 * np.sin(v[:, None] * 40 + streaks * 6)
    core = np.exp(-((v - 0.5) / 0.32) ** 2)[:, None]
    return np.clip(core * (0.45 + 0.55 * lines * nz) * 1.25, 0, 1)


def trail_wisp(w=512, h=128):
    v = (np.arange(h) + 0.5) / h
    nz = tile_noise(h, w, 48, octaves=5, seed=610)
    core = np.exp(-((v - 0.5) / 0.38) ** 2)[:, None]
    return np.clip(core * smooth_step(nz, 0.25, 0.85) * 1.3, 0, 1)


def ray(w=256, h=128):
    """Soft light shaft for Beams: bright along the middle, ragged edges."""
    v = (np.arange(h) + 0.5) / h
    nz = tile_noise(h, w, 20, octaves=3, seed=620)
    shaft = np.exp(-((v[:, None] - 0.5) / (0.22 + 0.06 * (nz - 0.5))) ** 2)
    return np.clip(shaft * (0.6 + 0.5 * nz), 0, 1)


def smooth_step(x, a, b):
    k = np.clip((x - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)


TEXTURES = {
    "Glow": glow, "Spark": spark, "Star": star, "Ember": ember, "Orb": orb, "Ring": ring, "Bubble": bubble,
    "Droplet": droplet, "Snowflake": snowflake, "Shards": shards, "Runes": runes, "Zaps": zaps,
    "Flames": flames, "Smoke": smoke, "Mist": mist, "Swirl": swirl, "MagicCircle": magic_circle,
    "Lightning": lightning, "TrailStreak": trail_streak, "TrailWisp": trail_wisp, "Ray": ray,
}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/vfx/textures"
    os.makedirs(out, exist_ok=True)
    for name, fn in TEXTURES.items():
        a = fn()
        save(a, os.path.join(out, f"{name}.png"))
        print(f"{name:12s} {a.shape[1]}x{a.shape[0]}")
