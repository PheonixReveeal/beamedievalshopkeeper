"""Toolkit for game-ready weapon meshes.

Every weapon is exported as ONE mesh with ONE texture set (a packed atlas), so it costs a
single draw call in Roblox. Shape is carried by efficient geometry; fine detail (leather wrap,
wood grain, engraving, runes, facets) lives in the normal/colour/roughness maps.

Conventions: Y is up (glTF / Roblox), blades point +Y, thickness runs along Z, units are studs.
"""
import math

import numpy as np
import shapely
import trimesh
import triangle as tr
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
from shapely.geometry import Polygon
from trimesh.visual.material import PBRMaterial
from trimesh.visual.texture import TextureVisuals

ATLAS = 1024
PAD = 6


# =============================================================== charts & pieces

class Chart:
    """A rectangle of texture space. Pieces that share a chart share its pixels (e.g. the
    front and back of a blade)."""

    def __init__(self, su, sv, painter, name=""):
        self.su, self.sv = max(su, 1e-3), max(sv, 1e-3)
        self.painter, self.name = painter, name
        self.rect = None


class Piece:
    def __init__(self, verts, faces, uv, chart, smooth=True):
        verts = np.asarray(verts, float)
        faces = np.asarray(faces, int).reshape(-1, 3)
        tri = verts[faces]
        area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        self.faces = faces[area > 1e-10]
        self.verts, self.uv, self.chart = verts, np.asarray(uv, float), chart
        self.smooth_deg = 35.0            # seam welding angle; 0 keeps every facet hard
        if not smooth:
            self.unweld()

    def unweld(self):
        f = self.faces
        self.verts, self.uv = self.verts[f].reshape(-1, 3), self.uv[f].reshape(-1, 2)
        self.faces = np.arange(len(f) * 3).reshape(-1, 3)
        return self

    def orient(self, ref_fn):
        """Flip any face whose normal disagrees with ref_fn(face_centres)."""
        tri = self.verts[self.faces]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        bad = np.einsum("ij,ij->i", n, ref_fn(tri.mean(1))) < 0
        self.faces[bad] = self.faces[bad][:, ::-1]
        return self

    def transform(self, m):
        self.verts = trimesh.transformations.transform_points(self.verts, m)
        if np.linalg.det(m[:3, :3]) < 0:
            self.faces = self.faces[:, ::-1]
        return self

    def move(self, x=0, y=0, z=0):
        self.verts = self.verts + [x, y, z]
        return self

    def rot(self, axis, deg):
        return self.transform(trimesh.transformations.rotation_matrix(math.radians(deg), axis))

    def scale(self, sx, sy=None, sz=None):
        s = np.array([sx, sx if sy is None else sy, sx if sz is None else sz])
        self.verts = self.verts * s
        if np.prod(s) < 0:
            self.faces = self.faces[:, ::-1]
        return self

    def deform(self, fn):
        self.verts = fn(self.verts.copy())
        return self

    def copy(self):
        p = Piece.__new__(Piece)
        p.verts, p.faces, p.uv, p.chart = self.verts.copy(), self.faces.copy(), self.uv.copy(), self.chart
        p.smooth_deg = getattr(self, "smooth_deg", 35.0)
        return p

    def normals(self, smooth_deg=None):
        smooth_deg = getattr(self, "smooth_deg", 35.0) if smooth_deg is None else smooth_deg
        tri = self.verts[self.faces]
        fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])  # area weighted
        vn = np.zeros_like(self.verts)
        for k in range(3):
            np.add.at(vn, self.faces[:, k], fn)
        ln = np.linalg.norm(vn, axis=1, keepdims=True)
        vn = vn / np.where(ln < 1e-12, 1, ln)
        # Weld normals across seams: co-located vertices whose normals are within smooth_deg.
        key = np.round(self.verts / 1e-5).astype(np.int64)
        _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
        inv = inv.ravel()
        multi = np.where(cnt[inv] > 1)[0]
        if len(multi) and smooth_deg > 0:
            cos_t = math.cos(math.radians(smooth_deg))
            out = vn.copy()
            order = multi[np.argsort(inv[multi], kind="stable")]
            groups = np.split(order, np.flatnonzero(np.diff(inv[order])) + 1)
            for g in groups:
                n = vn[g]
                close = (n @ n.T) > cos_t
                acc = close.astype(float) @ n
                out[g] = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
            vn = out
        return vn


def mirror(piece, axis=0):
    s = [1, 1, 1]
    s[axis] = -1
    return piece.copy().scale(*s)


def grid_faces(rows, cols, wrap=False):
    f = []
    for i in range(rows - 1):
        for j in range(cols - 1):
            a, b, c, d = i * cols + j, i * cols + j + 1, (i + 1) * cols + j, (i + 1) * cols + j + 1
            f += [[a, c, b], [b, c, d]]
    return np.array(f, int).reshape(-1, 3)


# =============================================================== geometry builders

def lathe(profile, chart=None, painter=None, segs=16, hard=(), flat_sides=False, sx=1.0, sz=1.0,
          phase=0.0, radius_fn=None, name="lathe"):
    """Revolve an (r, y) profile around Y. Walk the profile counter-clockwise around the solid's
    half-section (bottom axis -> out -> up the side -> in over the top) so normals face out.
    `hard` lists profile indices that get a crease. flat_sides makes the segments faceted."""
    prof = np.asarray(profile, float)
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))]
    total = arc[-1] if arc[-1] > 0 else 1
    if chart is None:
        circ = 2 * math.pi * prof[:, 0].max() * (sx + sz) / 2
        chart = Chart(circ, total, painter, name)
    th = np.linspace(0, 2 * math.pi, segs + 1) + phase
    cuts = sorted(set([0, len(prof) - 1] + [h for h in hard if 0 < h < len(prof) - 1]))
    pieces = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        seg = prof[a:b + 1]
        verts, uvs = [], []
        for (r, y), s in zip(seg, arc[a:b + 1]):
            rr = np.full_like(th, r) if radius_fn is None else radius_fn(r, y, th)
            verts.append(np.column_stack([rr * np.cos(th) * sx, np.full_like(th, y), rr * np.sin(th) * sz]))
            uvs.append(np.column_stack([(th - phase) / (2 * math.pi), np.full_like(th, s / total)]))
        pieces.append(Piece(np.vstack(verts), grid_faces(len(seg), segs + 1), np.vstack(uvs), chart,
                            smooth=not flat_sides))
    return merge_pieces(pieces)


def merge_pieces(pieces):
    """Merge pieces that share a chart into one piece (keeps their separate vertices)."""
    if len(pieces) == 1:
        return pieces[0]
    v, f, uv, off = [], [], [], 0
    for p in pieces:
        v.append(p.verts), uv.append(p.uv), f.append(p.faces + off)
        off += len(p.verts)
    out = Piece.__new__(Piece)
    out.verts, out.faces, out.uv, out.chart = np.vstack(v), np.vstack(f), np.vstack(uv), pieces[0].chart
    out.smooth_deg = min(getattr(p, "smooth_deg", 35.0) for p in pieces)
    return out


def tube(path, radius, chart=None, painter=None, segs=10, up=(0, 0, 1), closed=False, aspect=1.0,
         superellipse=2.0, cap=True, name="tube"):
    """Sweep a (super)ellipse along a 3D path. radius may be a function of t in [0, 1].
    aspect scales the section along `up` (the section's first axis)."""
    path = np.asarray(path, float)
    n = len(path)
    t = np.linspace(0, 1, n)
    rad = np.array([radius(x) for x in t]) if callable(radius) else np.full(n, radius)
    asp = np.array([aspect(x) for x in t]) if callable(aspect) else np.full(n, aspect)
    if closed:
        T = np.roll(path, -1, 0) - np.roll(path, 1, 0)
    else:
        T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.asarray(up, float)
    N = up - np.outer(T @ up, np.ones(3)) * T
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    B = np.cross(T, N)
    phi = np.linspace(0, 2 * math.pi, segs + 1)
    c, s = np.cos(phi), np.sin(phi)
    e = 2 / superellipse
    c, s = np.sign(c) * np.abs(c) ** e, np.sign(s) * np.abs(s) ** e
    length = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    if chart is None:
        chart = Chart(2 * math.pi * rad.max() * (1 + asp.max()) / 2, length[-1], painter, name)
    verts, uvs = [], []
    for i in range(n):
        ring = path[i] + np.outer(c * rad[i] * asp[i], N[i]) + np.outer(s * rad[i], B[i])
        verts.append(ring)
        uvs.append(np.column_stack([phi / (2 * math.pi), np.full(segs + 1, length[i] / max(length[-1], 1e-9))]))
    verts = np.vstack(verts)
    faces = grid_faces(n, segs + 1)
    if closed:
        last = (n - 1) * (segs + 1)
        faces = np.vstack([faces, [[last + j, j, last + j + 1] for j in range(segs)] +
                           [[last + j + 1, j, j + 1] for j in range(segs)]])
    p = Piece(verts, faces, np.vstack(uvs), chart)
    ring_of_face = np.minimum(p.faces.min(axis=1) // (segs + 1), n - 1)
    centre = path[ring_of_face]
    tri = p.verts[p.faces]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    bad = np.einsum("ij,ij->i", nrm, tri.mean(1) - centre) < 0
    p.faces[bad] = p.faces[bad][:, ::-1]
    if cap and not closed:
        caps = []
        for i, sign in ((0, -1), (n - 1, 1)):
            if rad[i] < 1e-4:
                continue
            ring = verts[i * (segs + 1):(i + 1) * (segs + 1)][:-1]
            cv = np.vstack([ring, path[i]])
            cf = [[j, (j + 1) % segs, segs] for j in range(segs)]
            cp = Piece(cv, cf, np.full((len(cv), 2), [0.5, 1.0 if sign > 0 else 0.0]), chart)
            caps.append(cp.orient(lambda x, d=T[i] * sign: np.tile(d, (len(x), 1))))
        return merge_pieces([p] + caps)
    return p


def pillow(outline, t_center, t_edge=0.01, ramp=0.1, chart=None, painter=None, holes=(),
           max_area=None, thick_fn=None, name="pillow", back_chart=None):
    """A flat shape in the XY plane, inflated along Z: thick in the middle (t_center, a half
    thickness) easing to t_edge at the rim over `ramp` studs. Great for axe heads, guards,
    leaves, wings. Front and back share one planar-mapped chart."""
    outline = [tuple(q) for i, q in enumerate(np.asarray(outline, float))
               if i == 0 or np.linalg.norm(np.subtract(q, outline[i - 1])) > 1e-6]
    if np.linalg.norm(np.subtract(outline[0], outline[-1])) < 1e-6:
        outline = outline[:-1]
    poly = Polygon(outline, holes)
    poly = shapely.geometry.polygon.orient(poly, 1.0)
    rings = [np.asarray(poly.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in poly.interiors]
    pts, segs_, off = [], [], 0
    for r in rings:
        k = len(r)
        pts.append(r)
        segs_ += [[off + i, off + (i + 1) % k] for i in range(k)]
        off += k
    data = dict(vertices=np.vstack(pts), segments=np.array(segs_))
    if holes:
        data["holes"] = np.array([Polygon(h).representative_point().coords[0] for h in holes])
    minx, miny, maxx, maxy = poly.bounds
    if max_area is None:
        max_area = (poly.area / 50)
    T = tr.triangulate(data, f"pq28a{max_area:.6f}")
    v2, f = T["vertices"], T["triangles"]
    d = shapely.distance(poly.boundary, shapely.points(v2))
    if thick_fn is not None:
        z = thick_fn(v2[:, 0], v2[:, 1], d)
    else:
        k = np.clip(d / ramp, 0, 1)
        z = t_edge + (t_center - t_edge) * (k * k * (3 - 2 * k))
    w, h = maxx - minx, maxy - miny
    if chart is None:
        chart = Chart(w, h, painter, name)
    uv = np.column_stack([(v2[:, 0] - minx) / w, 1 - (v2[:, 1] - miny) / h])
    front = Piece(np.column_stack([v2, z]), f, uv, chart).orient(lambda c: np.tile([0, 0, 1.0], (len(c), 1)))
    back = Piece(np.column_stack([v2, -z]), f, uv, back_chart or chart).orient(lambda c: np.tile([0, 0, -1.0], (len(c), 1)))
    # Rim wall: one hard-edged strip per boundary loop (using the triangulator's own boundary,
    # which may have split the input segments).
    rims = []
    nxt = {}
    for a, b in T["segments"]:
        nxt.setdefault(a, []).append(b)
        nxt.setdefault(b, []).append(a)
    seen = set()
    for startv in list(nxt):
        if startv in seen:
            continue
        loop, prev, cur = [startv], None, startv
        seen.add(startv)
        while True:
            cand = [x for x in nxt[cur] if x != prev]
            if not cand or cand[0] == startv:
                break
            prev, cur = cur, cand[0]
            if cur in seen:
                break
            loop.append(cur)
            seen.add(cur)
        idx = np.array(loop + loop[:1])
        top, bot = np.column_stack([v2[idx], z[idx]]), np.column_stack([v2[idx], -z[idx]])
        vv = np.vstack([bot, top])
        k = len(idx)
        ff = [[i, i + 1, k + i] for i in range(k - 1)] + [[i + 1, k + i + 1, k + i] for i in range(k - 1)]
        ruv = np.column_stack([(vv[:, 0] - minx) / w, 1 - (vv[:, 1] - miny) / h])
        rim = Piece(vv, ff, ruv, chart)
        tri = rim.verts[rim.faces]
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])[:, :2]
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        probe = tri.mean(1)[:, :2] + nrm * 1e-3
        inside = shapely.contains_xy(poly, probe[:, 0], probe[:, 1])
        rim.faces[inside] = rim.faces[inside][:, ::-1]
        rims.append(rim)
    if back_chart is not None:
        return [merge_pieces([front] + rims), back]
    return merge_pieces([front, back] + rims)


def blade(stations, section, chart=None, painter=None, name="blade"):
    """Loft a blade along +Y.
    stations: list of (y, cx, wl, wr, t): spine offset cx, half-widths to the left/right edge,
              half-thickness t. The last station usually has zero width (the point).
    section(s): list of polylines [(xf, tf), ...] for the TOP half from left edge (xf=-1) to the
              right edge (xf=+1); tf is a fraction of t. Each polyline is a hard-edged panel.
    Front and back share one chart (mirrored), so blade art is painted once. The chart's u runs
    edge to edge (0.5 is the centre line) and v runs tip (0) to base (1), so details follow the
    blade's shape."""
    st = np.asarray(stations, float)
    y0, y1 = st[0, 0], st[-1, 0]
    wmax = max(st[:, 2].max(), st[:, 3].max())
    xmin = (st[:, 1] - st[:, 2]).min()
    xmax = (st[:, 1] + st[:, 3]).max()
    if chart is None:
        chart = Chart(xmax - xmin, y1 - y0, painter, name)
    n_st = len(st)
    s_param = (st[:, 0] - y0) / (y1 - y0)
    panels_per = None
    pieces = []

    def pt(row, xf, tf, top):
        y, cx, wl, wr, t = row
        x = cx + xf * (wl if xf < 0 else wr)
        return [x, y, (tf * t) if top else -(tf * t)]

    secs = [section(s) for s in s_param]
    panels_per = len(secs[0])
    for top in (True, False):
        for k in range(panels_per):
            verts, uvs = [], []
            for i in range(n_st):
                pl = secs[i][k]
                for xf, tf in pl:
                    p = pt(st[i], xf, tf, top)
                    verts.append(p)
                    uvs.append([(xf + 1) / 2, 1 - s_param[i]])
            cols = len(secs[0][k])
            pc = Piece(verts, grid_faces(n_st, cols), uvs, chart)
            sign = 1.0 if top else -1.0
            pieces.append(pc.orient(lambda c, sg=sign: np.tile([0, 0, sg], (len(c), 1))))
    # Edge walls (left and right), joining the top and bottom rims.
    for side in (-1, 1):
        verts, uvs = [], []
        for i in range(n_st):
            pl_first = secs[i][0][0] if side < 0 else secs[i][-1][-1]
            for top in (True, False):
                p = pt(st[i], pl_first[0], pl_first[1], top)
                verts.append(p)
                uvs.append([np.clip((pl_first[0] + 1) / 2 - side * (0.01 if top else 0.03), 0, 1), 1 - s_param[i]])
        pc = Piece(verts, grid_faces(n_st, 2), uvs, chart)
        pieces.append(pc.orient(lambda c, sd=side: np.tile([sd, 0, 0.0], (len(c), 1))))
    return merge_pieces(pieces)



def surface(fn, nu, nv, chart=None, painter=None, su=1.0, sv=1.0, ref=None, name="surface"):
    """Parametric surface. fn(U, V) -> (X, Y, Z) for U, V grids in [0, 1] (rows = v).
    ref(face_centres) -> outward directions, used to fix the winding."""
    U, V = np.meshgrid(np.linspace(0, 1, nu), np.linspace(0, 1, nv))
    X, Y, Z = fn(U, V)
    if chart is None:
        chart = Chart(su, sv, painter, name)
    p = Piece(np.column_stack([np.ravel(X), np.ravel(Y), np.ravel(Z)]), grid_faces(nv, nu),
              np.column_stack([U.ravel(), V.ravel()]), chart)
    return p.orient(ref) if ref is not None else p


def dome_shell(rx, ry, rz, rim=lambda th: 1.6, thick=0.05, segs=32, rings=10, chart=None, painter=None,
               inner_chart=None, peak=0.0, bulge=None, center=(0, 0, 0), name="dome"):
    """Helmet-style shell. Polar angle phi runs from 0 (top) to rim(theta) (radians from the
    top), so the rim can sit higher at the face. theta = 0 is the FRONT, which faces -Z.
    peak lifts the crown into a point; bulge(phi, theta) -> radius multiplier."""
    c = np.asarray(center, float)

    def pts(U, V, inset):
        th = U * 2 * math.pi
        phi = (1 - V) * rim(th)
        k = 1.0 if bulge is None else bulge(phi, th)
        sx, sy, sz = (rx - inset) * k, (ry - inset) * k, (rz - inset) * k
        y = sy * np.cos(phi) + peak * np.clip(1 - phi / 0.9, 0, 1) ** 2 * (1 - inset / max(ry, 1e-6))
        return (c[0] + sx * np.sin(phi) * np.sin(th), c[1] + y, c[2] - sz * np.sin(phi) * np.cos(th))

    if chart is None:
        chart = Chart(2 * math.pi * max(rx, rz), max(rx, ry) * 2.2, painter, name)
    outward = lambda q: q - c
    outer = surface(lambda U, V: pts(U, V, 0.0), segs + 1, rings + 1, chart, ref=outward)
    inner = surface(lambda U, V: pts(U, V, thick), segs + 1, rings + 1, inner_chart or chart,
                    ref=lambda q: c - q)
    # Rim strip joining the two shells.
    U = np.linspace(0, 1, segs + 1)
    o = np.column_stack(pts(U, np.zeros_like(U), 0.0))
    i_ = np.column_stack(pts(U, np.zeros_like(U), thick))
    rv = np.vstack([o, i_])
    rf = grid_faces(2, segs + 1)
    ruv = np.column_stack([np.r_[U, U], np.r_[np.zeros(segs + 1), np.full(segs + 1, 0.02)]])
    rim_p = Piece(rv, rf, ruv, chart)
    mid = (o + i_) / 2
    down = lambda q: (q - c) * [1, 0, 1] * 0.2 + [0, -1, 0]
    rim_p.orient(down)
    return [merge_pieces([outer, rim_p]), inner]


def crown_band(R, height, thick=0.035, segs=96, chart=None, painter=None, flare=0.0, base=0.0, name="band"):
    """A crown/circlet band around Y. height(theta) gives the top edge (so points, arches and
    peaks are just a function); flare widens the band toward the top. theta = 0 faces -Z."""
    th = np.linspace(0, 2 * math.pi, segs + 1)
    H = np.maximum(np.asarray(height(th), float), 1e-3)
    hmax = H.max()
    if chart is None:
        chart = Chart(2 * math.pi * R, hmax, painter, name)

    def ring(y, r):
        return np.column_stack([r * np.sin(th), np.full_like(th, 0) + y, -r * np.cos(th)])

    rows_o, rows_i, uvs = [], [], []
    fr = [0.0, 0.5, 1.0]
    for f in fr:
        y = base + H * f
        ro, ri = R + thick / 2 + flare * H * f, R - thick / 2 + flare * H * f
        rows_o.append(np.column_stack([ro * np.sin(th), y, -ro * np.cos(th)]))
        rows_i.append(np.column_stack([ri * np.sin(th), y, -ri * np.cos(th)]))
        uvs.append(np.column_stack([th / (2 * math.pi), 1 - H * f / hmax]))
    out_dir = lambda q: q * [1, 0, 1]
    outer = Piece(np.vstack(rows_o), grid_faces(3, segs + 1), np.vstack(uvs), chart).orient(out_dir)
    inner = Piece(np.vstack(rows_i), grid_faces(3, segs + 1), np.vstack(uvs), chart).orient(lambda q: -out_dir(q))
    top = Piece(np.vstack([rows_o[-1], rows_i[-1]]), grid_faces(2, segs + 1), np.vstack([uvs[-1], uvs[-1]]), chart)
    top.orient(lambda q: np.tile([0, 1.0, 0], (len(q), 1)))
    bot = Piece(np.vstack([rows_o[0], rows_i[0]]), grid_faces(2, segs + 1), np.vstack([uvs[0], uvs[0]]), chart)
    bot.orient(lambda q: np.tile([0, -1.0, 0], (len(q), 1)))
    return merge_pieces([outer, inner, top, bot])


def cylinder_wrap(R, front=-1):
    """Deform: wrap a flat XY shape (thickness on Z) around a vertical cylinder of radius R,
    with its centre at the front (front=-1 -> -Z)."""
    def fn(v):
        a = v[:, 0] / R
        r = R - front * v[:, 2]
        return np.column_stack([r * np.sin(a), v[:, 1], front * r * np.cos(a)])
    return fn

def gem(kind="brilliant", size=(0.1, 0.1, 0.06), chart=None, painter=None, n=8, name="gem"):
    """Faceted, flat-shaded gem. Each facet samples a different shade of the gem chart, which
    reads as sparkle even under flat lighting."""
    if kind == "brilliant":          # round/oval cut, table facing +Z
        a = np.linspace(0, 2 * math.pi, n, endpoint=False)
        a2 = a + math.pi / n
        pts = np.vstack([np.column_stack([0.55 * np.cos(a), 0.55 * np.sin(a), np.full(n, 0.45)]),
                         np.column_stack([np.cos(a2), np.sin(a2), np.full(n, 0.0)]),
                         np.column_stack([0.85 * np.cos(a), 0.85 * np.sin(a), np.full(n, 0.2)]),
                         [[0, 0, -0.75]]])
    elif kind == "crystal":          # hexagonal prism with pointed ends, along +Y
        a = np.linspace(0, 2 * math.pi, 6, endpoint=False)
        ring = np.column_stack([np.cos(a), np.zeros(6), np.sin(a)])
        pts = np.vstack([ring + [0, -0.55, 0], ring + [0, 0.55, 0], [[0, -1, 0], [0, 1, 0]]])
    elif kind == "octa":             # diamond-shaped inlay / lozenge
        pts = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1.0]])
    elif kind == "cabochon":         # smooth dome (moonstone, opal); not faceted
        a = np.linspace(0, math.pi / 2, 7)
        prof = [(0.0, 0.0)] + [(math.cos(t), math.sin(t)) for t in a]
        if chart is None:
            chart = Chart(0.2, 0.2, painter, name)
        return lathe([(r * size[0], h * size[2]) for r, h in prof], chart, segs=20, sz=size[1] / size[0]) \
            .rot([1, 0, 0], 90)
    elif kind == "heart":
        t = np.linspace(0, 2 * math.pi, 24, endpoint=False)
        x, y = 16 * np.sin(t) ** 3, 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
        ring = np.column_stack([x / 17, y / 17, np.zeros_like(t)])
        pts = np.vstack([ring * [1, 1, 0] + [0, 0, 0.0], ring * 0.6 + [0, 0, 0.6], ring * 0.55 + [0, 0, -0.5],
                         [[0, 0.05, 0.75], [0, 0.05, -0.7]]])
    elif kind == "bipyramid":        # long double-terminated crystal along +Y
        a = np.linspace(0, 2 * math.pi, n, endpoint=False)
        pts = np.vstack([np.column_stack([np.cos(a), np.full(n, 0.0), np.sin(a)]), [[0, 1, 0], [0, -1, 0]]])
    else:
        raise ValueError(kind)
    hull = trimesh.convex.convex_hull(pts * np.asarray(size))
    if chart is None:
        chart = Chart(0.25, 0.05, painter, name)
    rng = np.random.default_rng(len(hull.faces))
    u = rng.uniform(0.05, 0.95, len(hull.faces))
    uv = np.repeat(np.column_stack([u, np.full(len(u), 0.5)]), 3, axis=0)
    v = hull.vertices[hull.faces].reshape(-1, 3)
    p = Piece(v, np.arange(len(v)).reshape(-1, 3), uv, chart)
    p.smooth_deg = 0.0
    return p


# =============================================================== textures

def _f(img_arr, w, h):
    return np.asarray(Image.fromarray(img_arr.astype(np.float32), "F").resize((w, h), Image.BICUBIC))


def noise(h, w, fx, fy=None, octaves=4, seed=0):
    """Value noise in [0,1] with feature size fx, fy in pixels."""
    fy = fx if fy is None else fy
    r = np.random.default_rng(seed)
    out, amp, tot = np.zeros((h, w)), 1.0, 0.0
    for o in range(octaves):
        gx = int(min(w, max(2, w / fx * 2 ** o))) + 2
        gy = int(min(h, max(2, h / fy * 2 ** o))) + 2
        out += amp * _f(r.random((gy, gx)), w, h)
        tot += amp
        amp *= 0.5
    out /= tot
    return (out - out.min()) / (np.ptp(out) + 1e-9)


def voronoi(h, w, cell_px, seed=0, aspect=1.0):
    """Returns (edge distance in px, cell id) for a jittered Voronoi pattern."""
    r = np.random.default_rng(seed)
    n = max(4, int(w * h / (cell_px ** 2 * aspect)))
    pts = r.random((n, 2)) * [w, h]
    yy, xx = np.mgrid[0:h, 0:w]
    q = np.column_stack([xx.ravel(), yy.ravel() * aspect])
    d, i = cKDTree(pts * [1, aspect]).query(q, k=2)
    edge = ((d[:, 1] - d[:, 0]) / 2).reshape(h, w)
    return edge, i[:, 0].reshape(h, w)


def smooth(x, a, b):
    k = np.clip((x - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)


def layers(nu, nv, color, metal, rough, height=None, emit=None):
    c = np.broadcast_to(np.asarray(color, float), (nv, nu, 3)).copy()
    return dict(color=c, metal=np.broadcast_to(metal, (nv, nu)).astype(float).copy(),
                rough=np.broadcast_to(rough, (nv, nu)).astype(float).copy(),
                height=np.zeros((nv, nu)) if height is None else height,
                emit=np.zeros((nv, nu, 3)) if emit is None else emit)


def rune_mask(w, h, n, seed=0, stroke=0.13, vertical=True):
    """A column (or row) of procedurally generated rune glyphs."""
    r = np.random.default_rng(seed)
    img = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(img)
    if vertical:
        cell_h = h / n
        gw, gh = min(w * 0.8, cell_h * 0.6), cell_h * 0.75
        for k in range(n):
            ox, oy = (w - gw) / 2, k * cell_h + (cell_h - gh) / 2
            lat = [(ox + gw * i / 2, oy + gh * j / 3) for j in range(4) for i in range(3)]
            spine = r.integers(0, 3)
            strokes = [(spine, spine + 9)]
            for _ in range(r.integers(2, 4)):
                a = r.integers(0, 12)
                b = r.choice([x for x in range(12) if x != a and abs(x % 3 - a % 3) <= 1 and abs(x // 3 - a // 3) <= 2])
                strokes.append((a, b))
            for a, b in strokes:
                dr.line([lat[a], lat[b]], fill=255, width=max(1, int(gw * stroke)))
    m = np.asarray(img.filter(ImageFilter.GaussianBlur(max(0.6, w * 0.004))), float) / 255
    return m


def wrap_pattern(nu, nv, su, sv, pitch, strap_frac=0.85, seed=0):
    """Spiral leather/cloth wrap for a lathe chart (u around, v along). Returns height, groove."""
    vv, uu = np.mgrid[0:nv, 0:nu]
    v_st = (vv + 0.5) / nv * sv
    phase = (v_st / pitch + (uu + 0.5) / nu) % 1.0
    strap = np.sin(np.pi * np.clip(phase / strap_frac, 0, 1)) ** 0.5
    groove = 1 - strap
    return strap, groove


class P:
    """Painter factories. Each returns fn(nu, nv, su, sv) -> layer dict."""

    @staticmethod
    def metal(color, rough=0.3, brushed=True, var=0.12, seed=0, engrave=None, rough_var=0.12, metal=1.0):
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            big = noise(nv, nu, 0.5 * ppu, octaves=3, seed=seed)
            fine = noise(nv, nu, 0.004 * ppu, 0.35 * ppu if brushed else 0.004 * ppu, octaves=2, seed=seed + 1)
            scratch = noise(nv, nu, 0.006 * ppu, 0.12 * ppu, octaves=2, seed=seed + 2) ** 10
            lum = 1 - var + var * big + 0.05 * (fine - 0.5) - 0.12 * scratch
            L = layers(nu, nv, color * lum[..., None], metal,
                       rough + rough_var * (big - 0.5) + 0.06 * (fine - 0.5) + 0.15 * scratch,
                       height=0.0003 * fine - 0.0008 * scratch)
            if engrave:
                engrave(L, nu, nv, su, sv)
            return L
        return paint

    @staticmethod
    def blade(color, rough=0.28, edge=0.1, edge_color=None, seed=0, var=0.12, etch=None, metal=0.85):
        """Steel-like blade: matte flats, a bright honed edge band. Uses the blade chart layout
        (u: edge to edge, v: tip to base)."""
        color = np.asarray(color, float)
        edge_color = np.minimum(color * 1.25 + 0.08, 1) if edge_color is None else np.asarray(edge_color, float)

        def paint(nu, nv, su, sv):
            L = P.metal(color, rough=rough, var=var, seed=seed, engrave=etch, metal=metal, brushed=False)(nu, nv, su, sv)
            u = (np.arange(nu) + 0.5) / nu
            band = smooth(np.abs(u - 0.5), 0.5 - edge, 0.5 - edge * 0.6)[None, :]
            L["color"] = L["color"] * (1 - band[..., None]) + edge_color * band[..., None]
            L["rough"] = L["rough"] * (1 - 0.6 * band)
            return L
        return paint

    @staticmethod
    def wood(color=(0.36, 0.2, 0.1), rough=0.62, seed=0, dark=0.45):
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            warp = noise(nv, nu, 0.15 * ppu, 0.6 * ppu, octaves=3, seed=seed)
            vv, uu = np.mgrid[0:nv, 0:nu]
            grain = 0.5 + 0.5 * np.sin((uu / ppu * 160 + warp * 14))
            fine = noise(nv, nu, 0.006 * ppu, 0.3 * ppu, octaves=2, seed=seed + 1)
            g = 0.55 * grain + 0.45 * fine
            lum = 1 - dark * g
            return layers(nu, nv, color * lum[..., None], 0.0, rough + 0.15 * g, height=-0.002 * g)
        return paint

    @staticmethod
    def wrap(color=(0.08, 0.1, 0.32), pitch=0.16, rough=0.7, seed=0, metal=0.0, leather=True):
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            strap, groove = wrap_pattern(nu, nv, su, sv, pitch)
            grain = noise(nv, nu, 0.01 * ppu, octaves=3, seed=seed) if leather else \
                0.5 + 0.5 * np.sin(np.mgrid[0:nv, 0:nu][1] * 2.2) * 0.5
            lum = (0.55 + 0.45 * strap) * (0.85 + 0.3 * grain)
            return layers(nu, nv, color * lum[..., None], metal, rough + 0.2 * groove - 0.1 * grain,
                          height=0.006 * strap + 0.0008 * grain)
        return paint

    @staticmethod
    def ice(color=(0.62, 0.86, 0.95), deep=(0.18, 0.5, 0.72), seed=0, glow=(0.15, 0.55, 0.8), core=True):
        color, deep, glow = (np.asarray(c, float) for c in (color, deep, glow))

        def paint(nu, nv, su, sv):
            ppu = nu / su
            vv, uu = np.mgrid[0:nv, 0:nu]
            u = (uu + 0.5) / nu
            edge, cid = voronoi(nv, nu, 0.22 * ppu, seed=seed, aspect=0.5)
            crack = np.exp(-edge / (0.006 * ppu + 0.6))
            frost = noise(nv, nu, 0.05 * ppu, octaves=4, seed=seed + 3)
            centre = np.exp(-((u - 0.5) / 0.16) ** 2) if core else np.zeros_like(u)
            cell = np.random.default_rng(seed).random(cid.max() + 1)[cid]
            mix = np.clip(0.55 * centre + 0.25 * cell + 0.2 * frost, 0, 1)
            col = color * (1 - mix[..., None]) + deep * mix[..., None]
            col = col * (1 - 0.35 * crack[..., None]) + 0.35 * crack[..., None]
            emit = glow * (0.35 * crack * (0.4 + 0.6 * centre) + 0.25 * centre)[..., None]
            h = 0.004 * (cell - 0.5) * (vv / nv) - 0.002 * crack
            return layers(nu, nv, col, 0.0, 0.06 + 0.25 * frost ** 3 + 0.1 * crack, height=h, emit=emit)
        return paint

    @staticmethod
    def crystal(color=(0.25, 0.75, 0.78), dark=(0.04, 0.3, 0.38), cell=0.18, seed=0, glow=None):
        color, dark = np.asarray(color, float), np.asarray(dark, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            edge, cid = voronoi(nv, nu, cell * ppu, seed=seed, aspect=0.6)
            r = np.random.default_rng(seed)
            k = cid.max() + 1
            shade, gx, gy = r.random(k)[cid], r.normal(0, 1, k)[cid], r.normal(0, 1, k)[cid]
            vv, uu = np.mgrid[0:nv, 0:nu]
            facet = 0.004 * (gx * uu + gy * vv) / ppu * 4          # tilted facets in the normal map
            line = np.exp(-edge / 1.2)
            col = color * (0.65 + 0.45 * shade)[..., None] * (1 - 0.3 * line[..., None]) + dark * 0.3 * line[..., None]
            emit = np.zeros((nv, nu, 3)) if glow is None else np.asarray(glow) * (0.25 * line + 0.1)[..., None]
            return layers(nu, nv, col, 0.0, 0.05 + 0.12 * shade, height=facet - 0.002 * line, emit=emit)
        return paint

    @staticmethod
    def gem(color, seed=0):
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            u = np.linspace(0, 1, nu)
            shade = 0.45 + 0.9 * (0.5 + 0.5 * np.sin(u * 23 + seed))
            col = np.clip(color[None, None, :] * shade[None, :, None] + 0.25 * (shade[None, :, None] > 1.25), 0, 1)
            col = np.broadcast_to(col, (nv, nu, 3)).copy()
            return layers(nu, nv, col, 0.0, 0.04, emit=col * 0.18)
        return paint

    @staticmethod
    def potion(liquid, fill=0.6, glass=None, glow=0.45, bubbles=True, swirl=0.0, sparkle=0.0,
               label=None, label_band=(0.3, 0.5), seed=0, deep=None):
        """Stylized glass bottle for lathe charts (u around, v from the bottom centre up the
        profile). Opaque on purpose (cheap, no sorting issues): liquid below `fill`, tinted glass
        above it, painted highlight streaks. label: fn(img_L, nu, nv) drawing onto a label band."""
        liquid = np.asarray(liquid, float)
        deep = liquid * 0.35 if deep is None else np.asarray(deep, float)
        glass = (np.clip(0.48 + 0.16 * liquid, 0, 1) * [0.92, 0.98, 1.0]) if glass is None else np.asarray(glass, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            vv, uu = np.mgrid[0:nv, 0:nu]
            u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
            depth = np.clip(v / max(fill, 1e-3), 0, 1)
            n = noise(nv, nu, 0.08 * ppu, octaves=3, seed=seed)
            sw = 0.5 + 0.5 * np.sin((u * 2 * math.pi * 3 + v * 9 + n * 4))
            liq = deep[None, None] * (1 - depth[..., None] ** 0.8) + liquid[None, None] * depth[..., None] ** 0.8
            liq = liq * (1 + swirl * (sw[..., None] - 0.5))
            inside = (v < fill).astype(float)
            col = liq * inside[..., None] + glass * (1 - inside[..., None])
            emit = liquid * glow * (0.35 + 0.65 * depth[..., None]) * inside[..., None]
            line = np.exp(-((v - fill) / 0.012) ** 2)
            col = col * (1 - 0.7 * line[..., None]) + np.minimum(liquid * 1.5 + 0.3, 1) * 0.7 * line[..., None]
            emit += liquid * glow * line[..., None]
            if bubbles:
                r = np.random.default_rng(seed + 1)
                yy, xx = vv.astype(float), uu.astype(float)
                bub = np.zeros((nv, nu))
                for _ in range(int(22 * su * sv) + 5):
                    cx, cy = r.uniform(0, nu), r.uniform(0.05, fill * 0.95) * nv
                    rad = r.uniform(0.005, 0.012) * ppu
                    d = np.hypot(xx - cx, yy - cy)
                    bub = np.maximum(bub, np.exp(-(d / rad) ** 2) * 0.8 + 0.4 * np.exp(-((d - rad) / (0.3 * rad + 0.5)) ** 2))
                bub = np.clip(bub, 0, 1)
                col = col * (1 - 0.45 * bub[..., None]) + np.minimum(liquid + 0.45, 1) * 0.45 * bub[..., None]
                emit += liquid * 0.4 * bub[..., None]
            if sparkle:
                r = np.random.default_rng(seed + 2)
                sp = np.zeros((nv, nu))
                for _ in range(int(120 * sparkle * su * sv) + 4):
                    cx, cy = r.integers(0, nu), r.uniform(0, fill) * nv
                    sp[int(cy) % nv, cx] = 1
                sp = gaussian_filter(sp, 0.9) * 6
                col = np.clip(col + sp[..., None], 0, 1)
                emit += np.clip(sp, 0, 1)[..., None] * 1.2
            hl = np.exp(-((u - 0.14) / 0.018) ** 2) + 0.6 * np.exp(-((u - 0.2) / 0.006) ** 2) + 0.35 * np.exp(-((u - 0.62) / 0.01) ** 2)
            hl = hl * smooth(v, 0.05, 0.12)
            col = col * (1 - 0.55 * hl[..., None]) + 0.55 * hl[..., None]
            emit += 0.12 * hl[..., None]
            L = layers(nu, nv, col, 0.0, 0.05 + 0.03 * n, height=0.0003 * n, emit=emit)
            if label is not None:
                a, b = label_band
                band = ((v > a) & (v < b))
                lab = np.clip(label(nu, nv, u, v, a, b), 0, 1)       # returns (nv, nu, 4) RGBA
                m = lab[..., 3] * band
                L["color"] = L["color"] * (1 - m[..., None]) + lab[..., :3] * m[..., None]
                L["emit"] = L["emit"] * (1 - m[..., None])
                L["rough"] = L["rough"] * (1 - m) + 0.8 * m
                L["height"] += 0.002 * m
            return L
        return paint

    @staticmethod
    def velvet(color, seed=0):
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            n = noise(nv, nu, 0.15 * ppu, octaves=4, seed=seed)
            fine = noise(nv, nu, 0.006 * ppu, octaves=2, seed=seed + 1)
            lum = 0.65 + 0.5 * n + 0.1 * fine
            return layers(nu, nv, color * lum[..., None], 0.0, 0.85, height=0.002 * n + 0.0003 * fine)
        return paint

    @staticmethod
    def leather(color, seed=0, stitch=None, rough=0.65):
        """Leather. stitch: list of ('u'|'v', position) lines of stitching."""
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            grain = noise(nv, nu, 0.008 * ppu, octaves=3, seed=seed)
            blotch = noise(nv, nu, 0.25 * ppu, octaves=3, seed=seed + 1)
            lum = 0.7 + 0.35 * blotch + 0.15 * grain
            L = layers(nu, nv, color * lum[..., None], 0.0, rough + 0.15 * grain, height=0.0008 * grain)
            for axis, pos in (stitch or []):
                vv, uu = np.mgrid[0:nv, 0:nu]
                u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
                along, across = (v * sv, u) if axis == 'u' else (u * su, v)
                dash = (np.sin(along / 0.03 * 2 * math.pi) > 0.3)
                m = np.exp(-((across - pos) / 0.004) ** 2) * dash
                L["color"] = L["color"] * (1 - m[..., None]) + np.array([0.85, 0.75, 0.55]) * m[..., None]
                L["height"] += 0.002 * m
            return L
        return paint

    @staticmethod
    def scales(color, tip=None, size=0.06, metal=0.6, rough=0.3, seed=0, glow=None):
        """Overlapping dragon/fish scales; rows run along u, each row offset by half a scale."""
        color = np.asarray(color, float)
        tip = np.minimum(color * 1.6 + 0.1, 1) if tip is None else np.asarray(tip, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            vv, uu = np.mgrid[0:nv, 0:nu]
            x, y = uu / ppu / size, vv / ppu / size / 0.75
            row = np.floor(y)
            x2 = x + 0.5 * (row % 2)
            fx, fy = x2 - np.floor(x2) - 0.5, y - row
            d = np.hypot(fx, fy * 1.1)
            inside = d < 0.62
            h = np.clip(1 - d / 0.62, 0, 1) * fy
            g = np.clip(fy, 0, 1)
            col = color * (0.55 + 0.45 * (1 - g))[..., None] + (tip - color) * (g ** 2 * inside)[..., None] * 0.8
            edge = np.exp(-((d - 0.6) / 0.05) ** 2)
            col = col * (1 - 0.5 * edge[..., None])
            emit = np.zeros((nv, nu, 3)) if glow is None else np.asarray(glow) * (edge * 0.8)[..., None]
            return layers(nu, nv, col, metal, rough + 0.2 * edge, height=0.004 * h - 0.001 * edge, emit=emit)
        return paint

    @staticmethod
    def chain(color, link=0.06, metal=0.9, rough=0.25):
        """Chain links painted onto a thin tube (u around, v along): cheap stand-in for real links."""
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            vv, uu = np.mgrid[0:nv, 0:nu]
            u, v = (uu + 0.5) / nu, (vv + 0.5) / nv * sv
            k = np.floor(v / link)
            f = v / link - k
            ring = np.sin(math.pi * f) ** 0.5
            face = (k % 2 == 0)
            slot = face * np.exp(-((f - 0.5) / 0.22) ** 2) * (np.exp(-((u % 0.5 - 0.25) / 0.09) ** 2))
            gap = np.exp(-(np.minimum(f, 1 - f) / 0.06) ** 2)
            h = 0.004 * ring * (1 - slot) - 0.003 * gap
            col = color * (0.6 + 0.4 * ring - 0.5 * slot - 0.4 * gap)[..., None]
            return layers(nu, nv, col, metal, rough + 0.3 * gap, height=h)
        return paint

    @staticmethod
    def feather(color, tip=None, seed=0, barb=0.02, metal=0.0, rough=0.7, glow=None):
        """Feather/plume art for planar (pillow) charts: rachis up the middle (u=0.5)."""
        color = np.asarray(color, float)
        tip = color * 1.4 if tip is None else np.asarray(tip, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            vv, uu = np.mgrid[0:nv, 0:nu]
            u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
            du = (u - 0.5) * su
            barbs = 0.5 + 0.5 * np.sin((v * sv + np.abs(du) * 0.8) / barb * 2 * math.pi + noise(nv, nu, 0.05 * ppu, seed=seed) * 3)
            rachis = np.exp(-(du / 0.006) ** 2)
            g = 1 - v
            col = color * (1 - g[..., None]) + tip * g[..., None]
            col = col * (0.75 + 0.25 * barbs)[..., None] * (1 - 0.3 * rachis[..., None]) + 0.25 * rachis[..., None]
            emit = np.zeros((nv, nu, 3)) if glow is None else np.asarray(glow) * (g ** 2 * 0.6)[..., None]
            return layers(nu, nv, col, metal, rough, height=0.0015 * barbs + 0.002 * rachis, emit=emit)
        return paint

    @staticmethod
    def hair(color, seed=0, glow=None):
        """Horsehair/plume strands running along v."""
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            ppu = nu / su
            strands = noise(nv, nu, 0.004 * ppu, 0.3 * ppu, octaves=3, seed=seed)
            clump = noise(nv, nu, 0.05 * ppu, 0.5 * ppu, octaves=2, seed=seed + 1)
            lum = 0.5 + 0.5 * strands * (0.6 + 0.4 * clump)
            emit = np.zeros((nv, nu, 3)) if glow is None else np.asarray(glow) * (strands ** 3)[..., None]
            return layers(nu, nv, color * lum[..., None], 0.0, 0.6, height=0.002 * strands, emit=emit)
        return paint

    @staticmethod
    def moonstone(base=(0.62, 0.72, 0.9), sheen=(0.35, 0.6, 1.0), seed=0):
        base, sheen = np.asarray(base, float), np.asarray(sheen, float)

        def paint(nu, nv, su, sv):
            vv, uu = np.mgrid[0:nv, 0:nu]
            u, v = (uu + 0.5) / nu, (vv + 0.5) / nv
            n = noise(nv, nu, max(nu, nv) * 0.3, octaves=3, seed=seed)
            g = np.clip(1 - np.hypot(u - 0.4, v - 0.35) * 1.4, 0, 1) * (0.6 + 0.4 * n)
            col = base * (1 - 0.7 * g[..., None]) + sheen * 0.7 * g[..., None]
            return layers(nu, nv, col * 0.85, 0.0, 0.08, emit=sheen * 0.45 * g[..., None])
        return paint

    @staticmethod
    def enamel(color, rough=0.15, seed=0, glow=0.0):
        color = np.asarray(color, float)

        def paint(nu, nv, su, sv):
            n = noise(nv, nu, max(nu, nv) * 0.25, octaves=3, seed=seed)
            col = color * (0.85 + 0.25 * n)[..., None]
            return layers(nu, nv, col, 0.0, rough, emit=col * glow)
        return paint

    @staticmethod
    def cork(seed=0):
        def paint(nu, nv, su, sv):
            ppu = nu / su
            n = noise(nv, nu, 0.01 * ppu, octaves=3, seed=seed)
            pits = (noise(nv, nu, 0.006 * ppu, octaves=1, seed=seed + 1) > 0.78).astype(float)
            col = np.array([0.72, 0.52, 0.32]) * (0.75 + 0.35 * n - 0.35 * pits)[..., None]
            return layers(nu, nv, col, 0.0, 0.85, height=0.0015 * n - 0.002 * pits)
        return paint

    @staticmethod
    def flat(color, metal=0.0, rough=0.6):
        def paint(nu, nv, su, sv):
            return layers(nu, nv, color, metal, rough)
        return paint


# --------------------------------------------------------------- engraving overlays

def engrave_filigree(depth=0.002, density=1.0, dirt=0.3):
    """Scrollwork engraved into gold: darkened grooves."""
    def apply(L, nu, nv, su, sv):
        ppu = nu / su
        vv, uu = np.mgrid[0:nv, 0:nu] / ppu
        a = np.sin(uu * 28 * density + 2.5 * np.sin(vv * 22 * density)) * np.sin(vv * 30 * density + 2 * np.sin(uu * 17 * density))
        g = np.exp(-(a / 0.07) ** 2)
        L["height"] -= depth * g
        L["color"] *= (1 - dirt * g)[..., None]
        L["rough"] += 0.25 * g
    return apply


def engrave_runes(n, color=(0.7, 0.3, 1.0), strength=1.6, width=0.22, depth=0.004, seed=0, axis="v"):
    """A glowing rune column down the middle of a chart (blade fullers)."""
    color = np.asarray(color, float)

    def apply(L, nu, nv, su, sv):
        cw = max(8, int(nu * width))
        m = rune_mask(cw, nv, n, seed=seed)
        full = np.zeros((nv, nu))
        x0 = (nu - cw) // 2
        full[:, x0:x0 + cw] = m
        L["height"] -= depth * full
        L["color"] = L["color"] * (1 - full[..., None]) + color * full[..., None]
        L["emit"] = np.maximum(L["emit"], color * strength * full[..., None] * 0.6)
        L["rough"] = L["rough"] * (1 - full) + 0.3 * full
        L["metal"] = L["metal"] * (1 - full)
    return apply


def engrave_line(u0=0.5, width=0.02, depth=0.002, dirt=0.4, v0=0.12, v1=0.92):
    """An etched line along v at u0 (e.g. down a blade's ridge), fading out toward v0 / v1."""
    def apply(L, nu, nv, su, sv):
        u = (np.arange(nu) + 0.5) / nu
        v = (np.arange(nv) + 0.5) / nv
        g = np.exp(-((u - u0) / width) ** 2)[None, :] * (smooth(v, v0, v0 + 0.08) * (1 - smooth(v, v1 - 0.05, v1)))[:, None]
        L["height"] -= depth * g
        L["color"] *= (1 - dirt * g)[..., None]
    return apply


def engrave_rings(positions, width=0.012, depth=0.003):
    """Grooved rings across the v axis (for bands on lathed metal)."""
    def apply(L, nu, nv, su, sv):
        v = (np.arange(nv) + 0.5) / nv
        g = sum(np.exp(-((v - p) / (width / sv)) ** 2) for p in positions)[:, None] * np.ones((1, nu))
        L["height"] -= depth * g
        L["color"] *= (1 - 0.35 * g)[..., None]
    return apply


# =============================================================== atlas + export

def pack(charts, atlas=ATLAS):
    """Uniform texel density shelf packer, long side horizontal. Returns density used."""
    def sizes(d):
        out = []
        for c in charts:
            rot = c.sv > c.su
            L, S = (c.sv, c.su) if rot else (c.su, c.sv)
            w = int(min(max(4, math.ceil(L * d)), atlas - 2 * PAD))
            h = int(min(max(4, math.ceil(S * d)), atlas - 2 * PAD))
            out.append((w, h, rot))
        return out

    def place(sz):
        order = sorted(range(len(sz)), key=lambda i: -sz[i][1])
        x = y = shelf = 0
        rects = [None] * len(sz)
        for i in order:
            w, h, rot = sz[i]
            W, H = w + 2 * PAD, h + 2 * PAD
            if x + W > atlas:
                x, y, shelf = 0, y + shelf, 0
            if y + H > atlas:
                return None
            rects[i] = (x, y, w, h, rot)
            x += W
            shelf = max(shelf, H)
        return rects

    lo, hi = 10.0, 3000.0
    best = None
    for _ in range(40):
        mid = (lo + hi) / 2
        r = place(sizes(mid))
        if r:
            lo, best = mid, r
        else:
            hi = mid
    for c, r in zip(charts, best):
        c.rect = r
    return lo


def normal_from_height(h, ppx, ppy, strength=1.0):
    dx = np.gradient(h, axis=1) * ppx
    dy = np.gradient(h, axis=0) * ppy
    n = np.dstack([-dx * strength, dy * strength, np.ones_like(h)])  # +Y up (OpenGL / glTF / Roblox)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def build(name, pieces, out_dir, atlas=ATLAS, origin=(0, 0, 0)):
    charts = []
    for p in pieces:
        if p.chart not in charts:
            charts.append(p.chart)
    density = pack(charts, atlas)

    A = {k: np.zeros((atlas, atlas, 3)) for k in ("color", "emit", "normal")}
    A["normal"][:] = [0.5, 0.5, 1.0]
    A["metal"], A["rough"] = np.zeros((atlas, atlas)), np.full((atlas, atlas), 0.5)
    for c in charts:
        x, y, w, h, rot = c.rect
        nu, nv = (h, w) if rot else (w, h)
        L = c.painter(nu, nv, c.su, c.sv)
        ppu, ppv = nu / c.su, nv / c.sv
        for k in L:
            if rot:
                L[k] = np.swapaxes(L[k], 0, 1)
        ppx, ppy = (ppv, ppu) if rot else (ppu, ppv)
        L["normal"] = normal_from_height(L.pop("height"), ppx, ppy)
        for k, arr in L.items():
            pad = ((PAD, PAD), (PAD, PAD)) + (((0, 0),) if arr.ndim == 3 else ())
            A[k][y:y + h + 2 * PAD, x:x + w + 2 * PAD] = np.pad(arr, pad, mode="edge")

    V, F, UV, N, off = [], [], [], [], 0
    for p in pieces:
        x, y, w, h, rot = p.chart.rect
        u, v = np.clip(p.uv[:, 0], 0, 1), np.clip(p.uv[:, 1], 0, 1)
        if rot:
            u, v = v, u
        px, py = x + PAD + u * w, y + PAD + v * h
        UV.append(np.column_stack([px / atlas, 1 - py / atlas]))   # trimesh flips V on export
        V.append(p.verts - np.asarray(origin))
        N.append(p.normals())
        F.append(p.faces + off)
        off += len(p.verts)
    V, F, UV, N = np.vstack(V), np.vstack(F), np.vstack(UV), np.vstack(N)

    to8 = lambda a: Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
    col_img, emit_img = to8(A["color"]), to8(A["emit"])          # colours are authored in sRGB
    mr = np.zeros((atlas, atlas, 3))
    mr[..., 1], mr[..., 2] = np.clip(A["rough"], 0.02, 1), np.clip(A["metal"], 0, 1)
    mr_img, nrm_img = to8(mr), to8(A["normal"])
    has_emit = A["emit"].max() > 0.01
    mat = PBRMaterial(name=name, baseColorTexture=col_img, metallicRoughnessTexture=mr_img,
                      normalTexture=nrm_img, metallicFactor=1.0, roughnessFactor=1.0,
                      emissiveTexture=emit_img if has_emit else None,
                      emissiveFactor=[1.0, 1.0, 1.0] if has_emit else None)
    mesh = trimesh.Trimesh(V, F, vertex_normals=N, process=False)
    mesh.visual = TextureVisuals(uv=UV, material=mat)
    scene = trimesh.Scene()
    scene.add_geometry(mesh, node_name=name, geom_name=name)

    import os
    os.makedirs(os.path.join(out_dir, "textures"), exist_ok=True)
    scene.export(os.path.join(out_dir, f"{name}.glb"))
    # Separate maps for Roblox SurfaceAppearance (ColorMap / MetalnessMap / RoughnessMap / NormalMap).
    t = os.path.join(out_dir, "textures", name)
    col_img.save(f"{t}_color.png")
    to8(A["metal"]).save(f"{t}_metalness.png")
    to8(A["rough"]).save(f"{t}_roughness.png")
    nrm_img.save(f"{t}_normal.png")
    if has_emit:
        emit_img.save(f"{t}_emissive.png")
    return dict(name=name, tris=len(F), verts=len(V), density=round(density),
                bbox_min=V.min(0).round(3).tolist(), bbox_max=V.max(0).round(3).tolist(),
                grip_offset=(-(V.min(0) + V.max(0)) / 2).round(3).tolist())
