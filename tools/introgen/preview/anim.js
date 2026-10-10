// Shared R15 animation maths for the previewer (browser) and the linter (node).
// Mirrors how Roblox plays a KeyframeSequence:
//   Part1.CFrame = Part0.CFrame * C0 * Transform * C1:Inverse()
// where Transform is the Pose CFrame, interpolated per joint between keyframes with the easing of the
// earlier keyframe's Pose. Rotations are authored as CFrame.Angles(x, y, z) in degrees.
import * as THREE from 'three';

const D2R = Math.PI / 180;
// 'Constant' is deliberately not allowed: Roblox snaps "to the keyframe indicated by the PoseEasingDirection", so whether it
// holds or jumps early depends on the direction. For a hold, repeat the pose; for a snap, put two keyframes 1/30 s apart.
export const EASINGS = ['Linear', 'CubicV2'];
export const DIRECTIONS = ['In', 'Out', 'InOut'];

// CFrame.Angles(x, y, z) = Rx * Ry * Rz, which is three.js Euler order 'XYZ'.
export function quatFromDeg(r) {
  return new THREE.Quaternion().setFromEuler(new THREE.Euler(r[0] * D2R, r[1] * D2R, r[2] * D2R, 'XYZ'));
}

export function ease(style, dir, a) {
  if (style === 'Linear') return a;
  if (style === 'CubicV2') {
    if (dir === 'In') return a * a * a;
    if (dir === 'Out') return 1 - Math.pow(1 - a, 3);
    return a < 0.5 ? 4 * a * a * a : 1 - Math.pow(-2 * a + 2, 3) / 2;
  }
  throw new Error(`unsupported easing ${style} (use ${EASINGS.join(', ')})`);
}

// Turns authored JSON into fully keyed keyframes. A keyframe is a full pose: a joint that isn't listed keeps
// its value from the previous keyframe (identity on the first keyframe). r and p carry over independently.
export function prepare(anim, rig) {
  const names = rig.joints.map(j => j.part1);
  const keys = [...anim.keyframes].sort((a, b) => a.t - b.t);
  const prev = {};
  for (const n of names) prev[n] = {r: [0, 0, 0], p: [0, 0, 0]};
  const out = keys.map(k => {
    for (const n of Object.keys(k.poses || {}))
      if (!names.includes(n)) throw new Error(`${anim.name}: unknown joint "${n}" at t=${k.t}`);
    const kf = {t: k.t, name: k.name || 'Keyframe', markers: k.markers || [], poses: {}};
    for (const n of names) {
      const s = (k.poses || {})[n] || {};
      const r = s.r ?? prev[n].r, p = s.p ?? prev[n].p;
      const style = s.ease || k.ease || anim.ease || 'CubicV2';
      const dir = s.dir || k.dir || anim.dir || 'InOut';
      kf.poses[n] = {r, p, ease: style, dir, q: quatFromDeg(r), v: new THREE.Vector3(...p), keyed: !!(k.poses || {})[n]};
      prev[n] = {r, p};
    }
    return kf;
  });
  const length = anim.length ?? keys[keys.length - 1].t;
  return {name: anim.name, loop: !!anim.loop, length, keys: out, joints: names, src: anim};
}

export function sample(prep, t) {
  const L = prep.length, keys = prep.keys;
  if (prep.loop && L > 0) t = ((t % L) + L) % L; else t = Math.min(Math.max(t, 0), L);
  let i = 0;
  while (i < keys.length - 1 && keys[i + 1].t <= t) i++;
  const res = {};
  const k0 = keys[i], k1 = keys[Math.min(i + 1, keys.length - 1)];
  const span = k1.t - k0.t;
  for (const n of prep.joints) {
    const a = k0.poses[n], b = k1.poses[n];
    if (k1 === k0 || span <= 0) { res[n] = {q: a.q.clone(), p: a.v.clone()}; continue; }
    const e = ease(a.ease, a.dir, (t - k0.t) / span);
    res[n] = {q: a.q.clone().slerp(b.q, e), p: a.v.clone().lerp(b.v, e)};
  }
  return res;
}

function cf(pos, rotDeg) {
  const m = new THREE.Matrix4();
  if (rotDeg) m.makeRotationFromQuaternion(quatFromDeg(rotDeg));
  m.setPosition(pos[0], pos[1], pos[2]);
  return m;
}

// World matrices for every rig part, plus the grip frame (sword frame: +Y toward the tip).
export function fk(rig, poses, rootOffset) {
  const world = {};
  const r = rig.root.pos;
  world[rig.root.part] = cf(rootOffset ? [r[0] + rootOffset[0], r[1] + rootOffset[1], r[2] + rootOffset[2]] : r);
  for (const j of rig.joints) {
    const pz = poses[j.part1];
    const T = new THREE.Matrix4().makeRotationFromQuaternion(pz ? pz.q : new THREE.Quaternion());
    if (pz) T.setPosition(pz.p);
    const C0 = cf(j.c0, j.c0r), C1inv = cf(j.c1, j.c1r).invert();
    world[j.part1] = world[j.part0].clone().multiply(C0).multiply(T).multiply(C1inv);
  }
  world.__grip = world[rig.grip.part].clone().multiply(cf(rig.grip.pos, rig.grip.rot));
  return world;
}

// ---------- geometry helpers used by the linter ----------
export function obb(matrix, size, shrink = 1) {
  const c = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
  matrix.decompose(c, q, s);
  const ax = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)].map(v => v.applyQuaternion(q));
  return {c, ax, h: size.map(x => x * 0.5 * shrink)};
}

export function corners(o) {
  const out = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1])
    out.push(o.c.clone().addScaledVector(o.ax[0], sx * o.h[0]).addScaledVector(o.ax[1], sy * o.h[1]).addScaledVector(o.ax[2], sz * o.h[2]));
  return out;
}

// Separating-axis test. Returns penetration depth along the best axis (0 when separated).
export function obbOverlap(a, b) {
  const axes = [...a.ax, ...b.ax];
  for (const u of a.ax) for (const v of b.ax) {
    const x = new THREE.Vector3().crossVectors(u, v);
    if (x.lengthSq() > 1e-6) axes.push(x.normalize());
  }
  const d = new THREE.Vector3().subVectors(b.c, a.c);
  let best = Infinity;
  for (const L of axes) {
    const ra = a.h[0] * Math.abs(a.ax[0].dot(L)) + a.h[1] * Math.abs(a.ax[1].dot(L)) + a.h[2] * Math.abs(a.ax[2].dot(L));
    const rb = b.h[0] * Math.abs(b.ax[0].dot(L)) + b.h[1] * Math.abs(b.ax[1].dot(L)) + b.h[2] * Math.abs(b.ax[2].dot(L));
    const pen = ra + rb - Math.abs(d.dot(L));
    if (pen <= 0) return 0;
    best = Math.min(best, pen);
  }
  return best;
}

// Mirror an animation left<->right (used for *_Right variants). For a reflection across the YZ plane,
// CFrame.Angles(x, y, z) becomes CFrame.Angles(x, -y, -z) and positions flip X.
export function mirror(anim, newName) {
  const swap = n => n.startsWith('Left') ? 'Right' + n.slice(4) : n.startsWith('Right') ? 'Left' + n.slice(5) : n;
  const m = JSON.parse(JSON.stringify(anim));
  m.name = newName;
  for (const k of m.keyframes) {
    const poses = {};
    for (const [n, s] of Object.entries(k.poses || {})) {
      const t = {...s};
      if (s.r) t.r = [s.r[0], -s.r[1], -s.r[2]];
      if (s.p) t.p = [-s.p[0], s.p[1], s.p[2]];
      poses[swap(n)] = t;
    }
    k.poses = poses;
    if (k.markers) k.markers = k.markers.map(mk => (typeof mk === 'string' ? swapMarker(mk) : {...mk, name: swapMarker(mk.name)}));
  }
  return m;
}
function swapMarker(s) { return s.replace(/Left|Right/g, w => (w === 'Left' ? 'Right' : 'Left')); }
