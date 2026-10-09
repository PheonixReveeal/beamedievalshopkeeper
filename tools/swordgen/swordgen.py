"""Procedural sword generator -> .glb (PBR textures) for Roblox Studio's 3D Importer.

Units are studs. The blade points along +Z, width runs along X, thickness along Y.
The origin is the centre of the crossguard, so the sword's pivot sits where the hand is.

Usage:  python swordgen.py <out_dir>
"""
import os
import sys

import numpy as np
import trimesh
from PIL import Image
from trimesh.visual.material import PBRMaterial
from trimesh.visual.texture import TextureVisuals

TEX = 512
rng = np.random.default_rng(7)


# ---------------------------------------------------------------- textures

def fbm(size, octaves=5, stretch=(1, 1)):
    """Tileable-ish fractal noise in [0, 1], optionally stretched (for brushed metal)."""
    out = np.zeros((size, size))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        res = 4 * 2 ** o
        g = rng.random((max(2, res // stretch[0]) + 1, max(2, res // stretch[1]) + 1))
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        out += amp * np.asarray(img, dtype=float) / 255
        total += amp
        amp *= 0.5
    out /= total
    return (out - out.min()) / (out.max() - out.min() + 1e-9)


def to_img(arr):
    return Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))


def metal_rough(metal, rough):
    """glTF packs metalness in B and roughness in G."""
    h, w = rough.shape
    m = np.zeros((h, w, 3))
    m[..., 1] = rough
    m[..., 2] = metal
    return to_img(m)


def damascus_textures():
    # v (rows) runs along the blade, u (cols) across it.
    v, u = np.mgrid[0:TEX, 0:TEX] / TEX
    warp = fbm(TEX, 4) * 3.0 + 0.6 * np.sin(v * 18 + u * 4)
    bands = np.sin((u * 26 + v * 9 + warp * 2.2) * np.pi)
    ladder = 0.35 * np.sin(v * 70 * np.pi + warp)       # "ladder" pattern ripples
    pat = 0.5 + 0.5 * np.tanh(2.5 * (bands + ladder))
    brushed = fbm(TEX, 5, stretch=(1, 8))
    lum = 0.42 + 0.38 * pat + 0.06 * (brushed - 0.5)
    col = np.stack([lum * 0.96, lum * 0.98, lum * 1.0], -1)
    rough = 0.18 + 0.22 * (1 - pat) + 0.08 * brushed
    return to_img(col), metal_rough(np.ones_like(rough), rough)


def gold_textures():
    n = fbm(TEX, 5)
    scratches = fbm(TEX, 3, stretch=(6, 1)) ** 6
    base = np.array([1.0, 0.76, 0.36])
    col = base * (0.72 + 0.22 * n)[..., None] * (1 - 0.25 * scratches)[..., None]
    rough = 0.22 + 0.25 * n + 0.3 * scratches
    return to_img(col), metal_rough(np.ones_like(rough), rough)


def leather_textures():
    n = fbm(TEX, 6)
    grain = fbm(TEX, 2) * 0.5 + fbm(TEX, 6) ** 3
    base = np.array([0.20, 0.11, 0.07])
    col = base * (0.6 + 0.6 * grain)[..., None]
    rough = 0.55 + 0.35 * n
    return to_img(col), metal_rough(np.zeros_like(rough), rough)


def material(name, maps, **kw):
    base, mr = maps
    return PBRMaterial(name=name, baseColorTexture=base, metallicRoughnessTexture=mr,
                       metallicFactor=1.0, roughnessFactor=1.0, **kw)


# ---------------------------------------------------------------- geometry helpers

def grid_faces(rows, cols):
    """Quads between consecutive rows of a (rows x cols) vertex grid."""
    f = []
    for i in range(rows - 1):
        for j in range(cols - 1):
            a, b = i * cols + j, i * cols + j + 1
            c, d = a + cols, b + cols
            f += [[a, c, b], [b, c, d]]
    return np.array(f)


def make_mesh(verts, uvs, faces, mat, center=None):
    m = trimesh.Trimesh(verts, faces, process=False)
    # Orient outward: compare face normals with direction from a reference centre/axis.
    if center is not None:
        out = m.triangles_center - center(m.triangles_center)
        if (np.einsum("ij,ij->i", m.face_normals, out) < 0).mean() > 0.5:
            m.faces = m.faces[:, ::-1]
    m.visual = TextureVisuals(uv=uvs, material=mat)
    return m


def axis_z(p):
    c = np.zeros_like(p)
    c[:, 2] = p[:, 2]
    return c


def loft_panels(stations, profile_fn, mat):
    """Loft a cross-section along Z. profile_fn(s) returns a list of polylines (hard-edged panels)."""
    meshes = []
    probe = profile_fn(stations[0][0])
    for k in range(len(probe)):
        rows, uvs = [], []
        for s, z in stations:
            pl = np.asarray(profile_fn(s)[k])
            rows.append(np.column_stack([pl[:, 0], pl[:, 1], np.full(len(pl), z)]))
            u = (pl[:, 0] / 0.4 + 0.5) * 0.5 + (0.5 if pl[:, 1].mean() < 0 else 0)
            uvs.append(np.column_stack([u, np.full(len(pl), s)]))
        v = np.vstack(rows)
        meshes.append(make_mesh(v, np.vstack(uvs), grid_faces(len(stations), len(rows[0])), mat, axis_z))
    return meshes


def lathe(profile, mat, segments=48, axis="z", origin=(0, 0, 0), radius_fn=None):
    """Revolve [(r, h), ...] around an axis. radius_fn(r, h, theta) can add surface detail."""
    profile = np.asarray(profile, float)
    th = np.linspace(0, 2 * np.pi, segments + 1)
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(profile, axis=0), axis=1))]
    arc /= arc[-1]
    verts, uvs = [], []
    for (r, h), a in zip(profile, arc):
        rr = np.full_like(th, r) if radius_fn is None else radius_fn(r, h, th)
        c, s = rr * np.cos(th), rr * np.sin(th)
        if axis == "z":
            ring = np.column_stack([c, s, np.full_like(th, h)])
        else:  # around Y (for wheel pommels): profile h runs along Y
            ring = np.column_stack([c, np.full_like(th, h), s])
        verts.append(ring + origin)
        uvs.append(np.column_stack([th / (2 * np.pi), np.full_like(th, a)]))
    v = np.vstack(verts)
    o = np.asarray(origin, float)
    if axis == "z":
        ctr = lambda p: np.column_stack([np.full(len(p), o[0]), np.full(len(p), o[1]), p[:, 2]])
    else:
        ctr = lambda p: np.column_stack([np.full(len(p), o[0]), p[:, 1], np.full(len(p), o[2])])
    return make_mesh(v, np.vstack(uvs), grid_faces(len(profile), segments + 1), mat, ctr)


def sweep(path, section, scale_fn, mat, center_fn):
    """Sweep a closed 2D section along a planar (XZ) path; section a -> Y, b -> in-plane normal."""
    path = np.asarray(path, float)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    Y = np.array([0, 1.0, 0])
    B = np.cross(T, Y)
    sec = np.vstack([section, section[:1]])
    n = len(path)
    verts, uvs = [], []
    for i in range(n):
        sa, sb = scale_fn(i / (n - 1))
        verts.append(path[i] + np.outer(sec[:, 0] * sa, Y) + np.outer(sec[:, 1] * sb, B[i]))
        uvs.append(np.column_stack([np.linspace(0, 1, len(sec)), np.full(len(sec), i / (n - 1))]))
    return make_mesh(np.vstack(verts), np.vstack(uvs), grid_faces(n, len(sec)), mat, center_fn)


def superellipse(a, b, n=4, k=48):
    t = np.linspace(0, 2 * np.pi, k, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    return np.column_stack([a * np.sign(c) * np.abs(c) ** (2 / n), b * np.sign(s) * np.abs(s) ** (2 / n)])


# ---------------------------------------------------------------- sword parts

BLADE_LEN = 3.3
BLADE_W = 0.17      # half-width at the base
BLADE_T = 0.034     # half-thickness at the base


def blade_profile(s):
    taper = 1 - 0.32 * s
    hw = BLADE_W * taper
    if s > 0.84:                      # ogive point
        hw *= np.sqrt(max(0.0, 1 - ((s - 0.84) / 0.16) ** 2))
    ht = BLADE_T * (1 - 0.45 * s) * (hw / (BLADE_W * taper) if taper else 1) ** 0.5
    hw, ht = max(hw, 1e-4), max(ht, 1e-4)
    fd = ht * 0.55 * np.clip((0.68 - s) / 0.08, 0, 1) * np.clip(s / 0.04, 0, 1)  # fuller depth
    edge = 0.004 * (hw / BLADE_W)

    def half(sign):
        bevel = [(hw, sign * edge), (0.42 * hw, sign * ht)]
        flat = [(0.42 * hw, sign * ht), (0.24 * hw, sign * ht)]
        xs = np.linspace(0.24 * hw, -0.24 * hw, 13)
        fuller = [(x, sign * (ht - fd * np.cos(np.pi * x / (0.48 * hw)) ** 2)) for x in xs]
        flat2 = [(-0.24 * hw, sign * ht), (-0.42 * hw, sign * ht)]
        bevel2 = [(-0.42 * hw, sign * ht), (-hw, sign * edge)]
        return [bevel, flat, fuller, flat2, bevel2]

    # Thin edge strips close the cutting edges.
    return half(1) + half(-1) + [[(hw, edge), (hw, -edge)], [(-hw, edge), (-hw, -edge)]]


def build_blade(mat):
    s = np.r_[np.linspace(0, 0.84, 60), np.linspace(0.845, 1.0, 24)]
    stations = [(si, 0.05 + si * BLADE_LEN) for si in s]
    return loft_panels(stations, blade_profile, mat)


def build_guard(mat):
    L = 0.72
    x = np.linspace(-L, L, 121)
    t = x / L
    path = np.column_stack([x, np.zeros_like(x), 0.11 * t ** 2 + 0.02 * t ** 4])

    def scale(u):
        tt = abs(2 * u - 1)
        s = 1 - 0.5 * tt + 0.75 * np.exp(-((tt - 0.95) / 0.04) ** 2)
        if tt > 0.95:
            s *= np.sqrt(max(0.0, 1 - ((tt - 0.95) / 0.05) ** 2)) + 1e-3
        return s * 0.075, s * 0.06

    centre = lambda p: np.column_stack([p[:, 0], np.zeros(len(p)), 0.11 * (p[:, 0] / L) ** 2 + 0.02 * (p[:, 0] / L) ** 4])
    arms = sweep(path, superellipse(1, 1, 3.2), scale, mat, centre)

    # Escutcheon: a rounded lozenge block at the centre, swept through the thickness.
    y = np.linspace(-1, 1, 21)
    ypath = np.column_stack([np.zeros_like(y), y * 0.085, np.zeros_like(y)])
    lozenge = superellipse(0.15, 0.17, 1.6, 64)

    def esc_scale(u):
        tt = abs(2 * u - 1)
        return (1 - 0.35 * max(0, tt - 0.7) / 0.3,) * 2

    verts, uvs = [], []
    for i, p in enumerate(ypath):
        sc = esc_scale(i / (len(ypath) - 1))[0]
        ring = np.column_stack([lozenge[:, 0] * sc, np.zeros(len(lozenge)), lozenge[:, 1] * sc]) + p
        ring = np.vstack([ring, ring[:1]])
        verts.append(ring)
        uvs.append(np.column_stack([np.linspace(0, 1, len(ring)), np.full(len(ring), i / 20)]))
    rows = len(ypath)
    v = np.vstack(verts)
    faces = grid_faces(rows, len(lozenge) + 1)
    # Caps on the front/back faces.
    cols = len(lozenge) + 1
    v = np.vstack([v, ypath[0], ypath[-1]])
    uvs.append([[0.5, 0], [0.5, 1]])
    c0, c1 = len(v) - 2, len(v) - 1
    cap = [[c0, j, j + 1] for j in range(cols - 1)] + [[c1, (rows - 1) * cols + j + 1, (rows - 1) * cols + j] for j in range(cols - 1)]
    esc = make_mesh(v, np.vstack(uvs), np.vstack([faces, cap]), mat, lambda p: np.zeros_like(p))
    return [arms, esc]


def build_gems(mat):
    gems = []
    for side in (1, -1):
        g = trimesh.creation.icosphere(subdivisions=1, radius=1.0)
        g.vertices *= [0.075, 0.035, 0.09]
        g.vertices += [0, side * 0.083, 0]
        g = trimesh.Trimesh(g.vertices[g.faces].reshape(-1, 3), np.arange(len(g.faces) * 3).reshape(-1, 3), process=False)
        g.visual = TextureVisuals(uv=np.zeros((len(g.vertices), 2)), material=mat)
        gems.append(g)
    return gems


def build_grip(mat_leather, mat_gold):
    top, bot = -0.07, -0.95
    h = np.linspace(top, bot, 140)
    mid = (top + bot) / 2
    r = 0.068 + 0.012 * (1 - ((h - mid) / ((top - bot) / 2)) ** 2)
    pitch = 0.085

    def wrap(r0, hh, th):
        phase = (hh / pitch + th / (2 * np.pi)) % 1.0
        ridge = 0.006 * np.sin(np.pi * phase) ** 0.6
        risers = sum(0.008 * np.exp(-((hh - z) / 0.012) ** 2) for z in (mid - 0.22, mid, mid + 0.22))
        return r0 + ridge + risers

    grip = lathe(np.column_stack([r, h]), mat_leather, segments=64, radius_fn=wrap)

    ferrule_top = lathe([(0.05, 0.0), (0.09, -0.01), (0.092, -0.04), (0.085, -0.075), (0.078, -0.08)], mat_gold)
    ferrule_bot = lathe([(0.078, -0.94), (0.085, -0.945), (0.09, -0.97), (0.075, -1.0), (0.05, -1.01)], mat_gold)
    return [grip, ferrule_top, ferrule_bot]


def build_pommel(mat):
    cz = -1.15
    R, T = 0.17, 0.065
    prof = [(0.0, T + 0.03), (0.055, T + 0.03), (0.07, T + 0.015), (0.085, T + 0.005), (0.1, T + 0.012),
            (R - 0.02, T), (R, T - 0.02), (R + 0.004, 0), (R, -T + 0.02), (R - 0.02, -T), (0.1, -T - 0.012),
            (0.085, -T - 0.005), (0.07, -T - 0.015), (0.055, -T - 0.03), (0.0, -T - 0.03)]
    prof = [(r, -y) for r, y in prof]  # wind so normals point outward with the Y-axis lathe
    wheel = lathe(prof, mat, segments=72, axis="y", origin=(0, 0, cz))
    peen = lathe([(0.0, cz - R - 0.065), (0.035, cz - R - 0.06), (0.045, cz - R - 0.035), (0.04, cz - R + 0.005)],
                 mat, segments=32)
    return [wheel, peen]


def build_sword():
    steel = material("DamascusSteel", damascus_textures())
    gold = material("Gold", gold_textures())
    leather = material("Leather", leather_textures())
    ruby = PBRMaterial(name="Ruby", baseColorFactor=[110, 0, 10, 255], metallicFactor=0.0,
                       roughnessFactor=0.06, emissiveFactor=[0.06, 0.0, 0.005])

    parts = {
        "Blade": build_blade(steel),
        "Guard": build_guard(gold),
        "Gems": build_gems(ruby),
        "Grip": build_grip(leather, gold)[:1],
        "Ferrules": build_grip(leather, gold)[1:],
        "Pommel": build_pommel(gold),
    }
    scene = trimesh.Scene()
    for name, meshes in parts.items():
        m = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        scene.add_geometry(m, node_name=name, geom_name=name)
    return scene


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    scene = build_sword()
    # glTF (and Roblox's importer) is Y-up: rotate so the blade points up.
    scene.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    path = os.path.join(out, "DamascusLongsword.glb")
    scene.export(path)
    tris = {k: len(g.faces) for k, g in scene.geometry.items()}
    print(path, tris, "total", sum(tris.values()))
