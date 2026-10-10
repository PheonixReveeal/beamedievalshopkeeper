// Lints authored R15 animations against the preview rig.
//   node lint.mjs [Name ...]      (default: every anims/*.json, plus mirrored *Right variants listed in "mirrors")
//   add --json for machine-readable output
// Checks: schema/easing, joint-angle sanity, feet through the floor, planted feet sliding, body parts and the
// held prop passing through the body, loop seams, very fast joint snaps.
import fs from 'node:fs'; import path from 'node:path';
import * as THREE from 'three';
import {prepare, sample, fk, obb, obbOverlap, corners, mirror, EASINGS, DIRECTIONS} from './anim.js';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const rig = JSON.parse(fs.readFileSync(path.join(root, 'rig_r15.json')));
const args = process.argv.slice(2), asJson = args.includes('--json');
const load = n => JSON.parse(fs.readFileSync(path.join(root, 'anims', n + '.json')));
let names = args.filter(a => !a.startsWith('--'));
if (!names.length) names = fs.readdirSync(path.join(root, 'anims')).filter(f => f.endsWith('.json')).map(f => f.slice(0, -5)).sort();
const props = {broken: 'Intro_BrokenSword', intact: 'StarterSword'};
const adjacent = new Set();
for (const j of rig.joints) { adjacent.add(j.part0 + '|' + j.part1); adjacent.add(j.part1 + '|' + j.part0); }
// Pairs that sit side by side at rest and only brush each other; ignored for self-intersection.
for (const [a, b] of [['LeftUpperLeg', 'RightUpperLeg'], ['UpperTorso', 'LeftUpperLeg'], ['UpperTorso', 'RightUpperLeg'],
  ['LowerTorso', 'LeftUpperArm'], ['LowerTorso', 'RightUpperArm'], ['LowerTorso', 'LeftLowerArm'], ['LowerTorso', 'RightLowerArm'],
  ['LeftUpperArm', 'LeftLowerArm'], ['RightUpperArm', 'RightLowerArm']]) { adjacent.add(a + '|' + b); adjacent.add(b + '|' + a); }

const results = [];
for (const name of names) {
  let src;
  try { src = load(name); }
  catch { src = mirror(load(name.replace(/Right$/, '')), name); }
  const R = {name, errors: [], warnings: [], info: {}};
  results.push(R);
  // ---- schema ----
  if (src.name !== name) R.errors.push(`"name" is ${src.name}, expected ${name}`);
  if (!['Idle', 'Movement', 'Action', 'Action2', 'Action3', 'Action4', 'Core'].includes(src.priority || 'Action')) R.errors.push(`bad priority ${src.priority}`);
  const ts = src.keyframes.map(k => k.t);
  if (ts[0] !== 0) R.errors.push('first keyframe must be at t=0');
  for (let i = 1; i < ts.length; i++) if (!(ts[i] > ts[i - 1])) R.errors.push(`keyframe times must increase (t=${ts[i]})`);
  for (const k of src.keyframes) {
    for (const e of [k.ease, k.dir]) if (e && ![...EASINGS, ...DIRECTIONS].includes(e)) R.errors.push(`bad easing "${e}" at t=${k.t}`);
    for (const [j, s] of Object.entries(k.poses || {})) {
      if (s.ease && !EASINGS.includes(s.ease)) R.errors.push(`${j} at t=${k.t}: easing "${s.ease}" not allowed (use ${EASINGS.join('/')})`);
      if (s.dir && !DIRECTIONS.includes(s.dir)) R.errors.push(`${j} at t=${k.t}: bad direction ${s.dir}`);
      const lim = rig.limits[j];
      if (s.r && lim) ['x', 'y', 'z'].forEach((ax, i) => {
        const v = s.r[i], [lo, hi] = lim[ax];
        if (v < lo || v > hi) R.warnings.push(`${j}.${ax}=${v} at t=${k.t} outside sane range [${lo}, ${hi}]`);
      });
      if (s.p && Math.hypot(...s.p) > 1.6) R.warnings.push(`${j} translation ${JSON.stringify(s.p)} at t=${k.t} is large`);
      if (s.p && j !== 'LowerTorso' && Math.hypot(...s.p) > 0.05) R.warnings.push(`${j} has a translation at t=${k.t}; only LowerTorso (Root) should normally move`);
    }
    for (const m of k.markers || []) if (!(typeof m === 'string' || (m && typeof m.name === 'string'))) R.errors.push(`bad marker at t=${k.t}`);
  }
  if (R.errors.length) continue;   // fix the schema first; sampling would throw
  let prep;
  try { prep = prepare(src, rig); } catch (e) { R.errors.push(String(e.message)); continue; }
  R.info.length = prep.length; R.info.loop = prep.loop; R.info.keyframes = prep.keys.length;
  R.info.markers = prep.keys.flatMap(k => k.markers.map(m => `${typeof m === 'string' ? m : m.name}@${k.t}`));
  if (prep.length < 0.2) R.errors.push('animation is shorter than 0.2 s');
  // ---- loop seam ----
  if (prep.loop) {
    const a = prep.keys[0].poses, b = prep.keys[prep.keys.length - 1].poses;
    for (const j of prep.joints) {
      const ang = THREE.MathUtils.radToDeg(a[j].q.angleTo(b[j].q)), dp = a[j].v.distanceTo(b[j].v);
      if (ang > 0.5 || dp > 0.01) R.errors.push(`loop seam: ${j} differs between first and last keyframe (${ang.toFixed(1)} deg, ${dp.toFixed(2)} studs)`);
    }
  }
  // ---- sampled checks ----
  const fps = 60, n = Math.max(2, Math.round(prep.length * fps) + 1);
  const propSpec = props[src.prop] ? JSON.parse(fs.readFileSync(path.join(root, 'props', props[src.prop] + '.json'))) : null;
  const allow = new Set((src.allowContact || []).flatMap(([a, b]) => [a + '|' + b, b + '|' + a]));
  const bodyParts = Object.keys(rig.parts).filter(p => !rig.parts[p].hidden);
  let minFoot = Infinity, maxSlide = 0, slideAt = 0, maxSpeed = {}, worstSelf = {}, worstProp = {};
  let prevFoot = {}, prevQ = null, airborne = 0;
  const propFloor = {y: Infinity};
  for (let i = 0; i < n; i++) {
    const t = Math.min(prep.length, i / fps);
    const poses = sample(prep, t);
    const w = fk(rig, poses);
    // feet
    let anyPlanted = false;
    for (const f of ['LeftFoot', 'RightFoot']) {
      const cs = corners(obb(w[f], rig.parts[f].size));
      let low = cs[0]; for (const c of cs) if (c.y < low.y) low = c;
      minFoot = Math.min(minFoot, low.y);
      const planted = low.y < 0.06;
      anyPlanted ||= planted;
      if (planted && prevFoot[f]) {
        const d = Math.hypot(low.x - prevFoot[f].x, low.z - prevFoot[f].z) * fps;
        if (d > maxSlide) { maxSlide = d; slideAt = t; }
      }
      prevFoot[f] = planted ? low : null;
    }
    if (!anyPlanted) airborne++;
    // joint speed
    if (prevQ) for (const j of prep.joints) {
      const sp = THREE.MathUtils.radToDeg(poses[j].q.angleTo(prevQ[j])) * fps;
      if (!maxSpeed[j] || sp > maxSpeed[j].v) maxSpeed[j] = {v: sp, t};
    }
    prevQ = Object.fromEntries(prep.joints.map(j => [j, poses[j].q]));
    // self intersection
    const boxes = Object.fromEntries(bodyParts.map(p => [p, obb(w[p], rig.parts[p].size, 0.9)]));
    for (let a = 0; a < bodyParts.length; a++) for (let b = a + 1; b < bodyParts.length; b++) {
      const A = bodyParts[a], B = bodyParts[b], key = A + '|' + B;
      if (adjacent.has(key) || allow.has(key)) continue;
      const d = obbOverlap(boxes[A], boxes[B]);
      if (d > 0.12 && (!worstSelf[key] || d > worstSelf[key].d)) worstSelf[key] = {d, t};
    }
    // prop vs body
    if (propSpec) for (const pt of propSpec.parts) {
      const m = w.__grip.clone().multiply(new THREE.Matrix4().compose(new THREE.Vector3(...pt.pos),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(...(pt.rot || [0, 0, 0]).map(v => v * Math.PI / 180), 'XYZ')), new THREE.Vector3(1, 1, 1)));
      const pb = obb(m, pt.size, 0.95);
      for (const c of corners(obb(m, pt.size))) if (c.y < propFloor.y) { propFloor.y = c.y; propFloor.t = t; propFloor.part = pt.name; }
      for (const p of bodyParts) {
        if (p === 'RightHand' || p === 'RightLowerArm' || allow.has('Prop|' + p)) continue;
        const d = obbOverlap(pb, boxes[p]);
        const key = pt.name + '>' + p;
        if (d > 0.06 && (!worstProp[key] || d > worstProp[key].d)) worstProp[key] = {d, t};
      }
    }
  }
  R.info.lowestFoot = +minFoot.toFixed(3);
  if (minFoot < -0.08) R.warnings.push(`a foot goes ${(-minFoot).toFixed(2)} studs through the floor`);
  if (minFoot > 0.12 && !src.airborne) R.warnings.push(`neither foot ever touches the floor (lowest ${minFoot.toFixed(2)}); the character will look like it floats`);
  if (airborne / n > 0.05 && !src.airborne && !src.locomotion) R.warnings.push(`both feet off the floor for ${(100 * airborne / n).toFixed(0)}% of frames`);
  R.info.maxFootSlide = +maxSlide.toFixed(2);
  if (!src.locomotion && maxSlide > 1.2) R.warnings.push(`a planted foot slides at ${maxSlide.toFixed(1)} studs/s near t=${slideAt.toFixed(2)}`);
  for (const [k, v] of Object.entries(worstSelf)) R.warnings.push(`body intersection ${k.replace('|', ' / ')} ${v.d.toFixed(2)} studs at t=${v.t.toFixed(2)}`);
  if (propFloor.y < -0.03) R.warnings.push(`prop ${propFloor.part} goes ${(-propFloor.y).toFixed(2)} studs through the floor at t=${propFloor.t.toFixed(2)}`);
  for (const [k, v] of Object.entries(worstProp)) R.warnings.push(`prop ${k.replace('>', ' passes through ')} ${v.d.toFixed(2)} studs at t=${v.t.toFixed(2)}`);
  for (const [j, s] of Object.entries(maxSpeed)) if (s.v > 1500) R.warnings.push(`${j} snaps at ${s.v.toFixed(0)} deg/s near t=${s.t.toFixed(2)}`);
  R.info.fastestJoint = Object.entries(maxSpeed).sort((a, b) => b[1].v - a[1].v).slice(0, 3).map(([j, s]) => `${j} ${s.v.toFixed(0)}deg/s`);
}
if (asJson) console.log(JSON.stringify(results, null, 1));
else for (const R of results) {
  console.log(`\n== ${R.name}  ${R.errors.length ? 'FAIL' : R.warnings.length ? 'WARN' : 'PASS'}  ${JSON.stringify(R.info)}`);
  for (const e of R.errors) console.log('  ERROR ' + e);
  for (const w of R.warnings) console.log('  warn  ' + w);
}
process.exit(results.some(r => r.errors.length) ? 1 : 0);
