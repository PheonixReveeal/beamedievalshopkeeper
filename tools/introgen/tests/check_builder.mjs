// Verifies the .rbxm KeyframeSequences match what the previewer shows:
// same keyframe times, markers, easing, Pose hierarchy, and Pose CFrames equal to the previewer's rotations.
//   node tests/check_builder.mjs <poses.json from dump_poses.luau>
import fs from 'node:fs'; import path from 'node:path';
import * as THREE from '../preview/node_modules/three/build/three.module.js';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const {prepare, mirror} = await import('../preview/anim.js');
const rig = JSON.parse(fs.readFileSync(path.join(root, 'rig_r15.json')));
const dumped = JSON.parse(fs.readFileSync(process.argv[2]));
const parentOf = Object.fromEntries(rig.joints.map(j => [j.part1, j.part0]));
let bad = 0, checked = 0;
const fail = m => { bad++; if (bad < 30) console.log('  FAIL ' + m); };
const sources = {};
for (const f of fs.readdirSync(path.join(root, 'anims')).filter(f => f.endsWith('.json') && !f.startsWith('_'))) {
  const a = JSON.parse(fs.readFileSync(path.join(root, 'anims', f)));
  sources[a.name] = a;
  if (a.mirrorAs) sources[a.mirrorAs] = mirror(a, a.mirrorAs);
}
for (const [name, src] of Object.entries(sources)) {
  const d = dumped[name];
  if (!d) { fail(`${name} missing from rbxm`); continue; }
  const prep = prepare(src, rig);
  if (d.loop !== !!src.loop) fail(`${name}: Loop ${d.loop}`);
  if (d.priority !== (src.priority || 'Action')) fail(`${name}: Priority ${d.priority}`);
  if (Math.abs(d.hip - rig.hipHeight) > 1e-6) fail(`${name}: AuthoredHipHeight ${d.hip}`);
  if (d.frames.length !== prep.keys.length) { fail(`${name}: ${d.frames.length} keyframes vs ${prep.keys.length}`); continue; }
  prep.keys.forEach((k, i) => {
    const fr = d.frames[i];
    if (Math.abs(fr.t - k.t) > 1e-4) fail(`${name}: keyframe ${i} time ${fr.t} vs ${k.t}`);
    const mk = k.markers.map(m => typeof m === 'string' ? m : m.name).sort().join(',');
    const got = (Array.isArray(fr.markers) ? fr.markers : []).sort().join(',');   // an empty Luau table encodes as {}
    if (got !== mk) fail(`${name} t=${k.t}: markers ${got} vs ${mk}`);
    if (fr.poses.HumanoidRootPart?.parent !== 'Keyframe' && fr.poses.HumanoidRootPart?.parent !== fr.name) fail(`${name}: HumanoidRootPart pose not at the keyframe root`);
    for (const j of prep.joints) {
      const p = fr.poses[j], e = k.poses[j];
      if (!p) { fail(`${name} t=${k.t}: no Pose ${j}`); continue; }
      if (p.parent !== parentOf[j]) fail(`${name} t=${k.t}: Pose ${j} parented to ${p.parent}, expected ${parentOf[j]}`);
      if (p.ease !== e.ease || p.dir !== e.dir) fail(`${name} t=${k.t} ${j}: easing ${p.ease}/${p.dir} vs ${e.ease}/${e.dir}`);
      // CFrame components: x y z R00 R01 R02 R10 R11 R12 R20 R21 R22 (row-major)
      const c = p.cf, m = new THREE.Matrix4().makeRotationFromQuaternion(e.q).elements; // column-major
      const R = [[m[0], m[4], m[8]], [m[1], m[5], m[9]], [m[2], m[6], m[10]]];
      let err = Math.abs(c[0] - e.p[0]) + Math.abs(c[1] - e.p[1]) + Math.abs(c[2] - e.p[2]);
      for (let r = 0; r < 3; r++) for (let q = 0; q < 3; q++) err += Math.abs(c[3 + r * 3 + q] - R[r][q]);
      checked++;
      if (err > 1e-3) fail(`${name} t=${k.t} ${j}: CFrame differs from the previewer (err ${err.toFixed(4)})`);
    }
  });
}
console.log(`${checked} poses compared across ${Object.keys(sources).length} animations: ${bad ? bad + ' problems' : 'all match'}`);
process.exit(bad ? 1 : 0);
