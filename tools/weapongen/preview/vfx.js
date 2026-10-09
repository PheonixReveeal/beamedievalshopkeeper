// Browser approximation of Roblox ParticleEmitter / Beam / Trail / PointLight for previewing
// the WeaponVFX presets. Deterministic: window.renderAt(t) steps the simulation to time t.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';

const q = new URLSearchParams(location.search);
const W = +q.get('w') || 640, H = +q.get('h') || 640;
const presetName = q.get('preset');
const model = q.get('model');
const yawDeg = +(q.get('yaw') ?? 20);
const swingAt = q.get('swing') ? +q.get('swing') : null;     // seconds
const burstAt = q.get('burst') ? +q.get('burst') : null;
const swingAxis = q.get('axis') || 'z';
const DT = 1 / 60;

// ---------------------------------------------------------------- deterministic RNG
let seed = 1234567;
const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
const range = (a, b) => a + (b - a) * rand();

// ---------------------------------------------------------------- sequences
const evalNum = (seq, t, env = 0) => {
  for (let i = 1; i < seq.length; i++) if (t <= seq[i][0]) {
    const [t0, v0, e0 = 0] = seq[i - 1], [t1, v1, e1 = 0] = seq[i];
    const k = (t - t0) / Math.max(t1 - t0, 1e-6);
    return v0 + (v1 - v0) * k + env * (e0 + (e1 - e0) * k);
  }
  return seq[seq.length - 1][1];
};
const evalCol = (seq, t) => {
  for (let i = 1; i < seq.length; i++) if (t <= seq[i][0]) {
    const [t0, c0] = seq[i - 1], [t1, c1] = seq[i];
    const k = (t - t0) / Math.max(t1 - t0, 1e-6);
    return [0, 1, 2].map(j => c0[j] + (c1[j] - c0[j]) * k);
  }
  return seq[seq.length - 1][1];
};

// ---------------------------------------------------------------- scene
const renderer = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});
renderer.setPixelRatio(1); renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
{
  const c = document.createElement('canvas'); c.width = 2; c.height = 256;
  const g = c.getContext('2d'), grd = g.createLinearGradient(0, 0, 0, 256);
  grd.addColorStop(0, '#3a4256'); grd.addColorStop(0.65, '#20242f'); grd.addColorStop(1, '#14161c');
  g.fillStyle = grd; g.fillRect(0, 0, 2, 256);
  scene.background = new THREE.CanvasTexture(c); scene.background.colorSpace = THREE.SRGBColorSpace;
}
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;
const key = new THREE.DirectionalLight(0xffffff, 0.9); key.position.set(3, 5, 6); scene.add(key);
const camera = new THREE.PerspectiveCamera(30, W / H, 0.05, 200);
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), 0.4, 0.45, 0.88));
composer.addPass(new OutputPass());

const texLoader = new THREE.TextureLoader();
const texCache = {};
const tex = name => texCache[name] ??= texLoader.load(`vfxtex/${name}.png`, t => { t.colorSpace = THREE.SRGBColorSpace; });

const pivot = new THREE.Group();     // rotates for sway/swing; weapon hangs off it at the grip
scene.add(pivot);
const weapon = new THREE.Group();
pivot.add(weapon);

// ---------------------------------------------------------------- particle systems
const FACES = {Top: [0, 1, 0], Bottom: [0, -1, 0], Front: [0, 0, -1], Back: [0, 0, 1], Right: [1, 0, 0], Left: [-1, 0, 0]};

class Emitter {
  constructor(def, source, scaleK) {
    this.def = def; this.source = source; this.k = scaleK;
    this.parts = []; this.acc = 0;
    const max = 1600;
    this.geo = new THREE.BufferGeometry();
    this.pos = new Float32Array(max * 4 * 3); this.uv = new Float32Array(max * 4 * 2); this.col = new Float32Array(max * 4 * 4);
    const idx = new Uint32Array(max * 6);
    for (let i = 0; i < max; i++) idx.set([i * 4, i * 4 + 1, i * 4 + 2, i * 4, i * 4 + 2, i * 4 + 3], i * 6);
    this.geo.setIndex(new THREE.BufferAttribute(idx, 1));
    this.geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    this.geo.setAttribute('uv', new THREE.BufferAttribute(this.uv, 2));
    this.geo.setAttribute('color', new THREE.BufferAttribute(this.col, 4));
    const additive = (def.lightEmission ?? 0) >= 0.5;
    this.mat = new THREE.MeshBasicMaterial({map: tex(def.texture), vertexColors: true, transparent: true, depthWrite: false,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending, side: THREE.DoubleSide, toneMapped: true});
    this.mesh = new THREE.Mesh(this.geo, this.mat);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = additive ? 2 : 1 + (def.zOffset || 0) * 0.01;
    scene.add(this.mesh);
    this.grid = def.flipbook === '4x4' ? 4 : def.flipbook === '2x2' ? 2 : 1;
    this.max = max;
  }
  // world-space spawn point / direction from the source (a region box or an attachment)
  spawnPoint() {
    const s = this.source;
    let p;
    if (s.box) {
      const [sx, sy, sz] = s.box.size;
      if (this.def.shapeStyle === 'Surface') {
        const faces = [[sy * sz, 0], [sx * sz, 1], [sx * sy, 2]];
        const tot = faces.reduce((a, f) => a + f[0], 0) * 2;
        let r = rand() * tot, axis = 0;
        for (const [a, ax] of faces) { if ((r -= 2 * a) <= 0) { axis = ax; break; } }
        p = [range(-sx / 2, sx / 2), range(-sy / 2, sy / 2), range(-sz / 2, sz / 2)];
        p[axis] = ([sx, sy, sz][axis] / 2) * (rand() < 0.5 ? -1 : 1);
      } else p = [range(-sx / 2, sx / 2), range(-sy / 2, sy / 2), range(-sz / 2, sz / 2)];
      p = new THREE.Vector3(...p).add(new THREE.Vector3(...s.box.center));
    } else p = s.point.clone();
    return weapon.localToWorld(p);
  }
  spawn(n) {
    const d = this.def, q = new THREE.Quaternion();
    weapon.getWorldQuaternion(q);
    for (let i = 0; i < n && this.parts.length < this.max; i++) {
      const dir = new THREE.Vector3(...FACES[d.direction || 'Top']);
      const sx = THREE.MathUtils.degToRad(range(-d.spread[0], d.spread[0]));
      const sy = THREE.MathUtils.degToRad(range(-d.spread[1], d.spread[1]));
      const perp1 = Math.abs(dir.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
      const perp2 = new THREE.Vector3().crossVectors(dir, perp1).normalize();
      dir.applyAxisAngle(perp1, sx).applyAxisAngle(perp2, sy).applyQuaternion(q);
      const life = range(d.lifetime[0], d.lifetime[1]);
      const local = this.spawnPoint();
      this.parts.push({
        p: local, v: dir.multiplyScalar(range(d.speed[0], d.speed[1]) * this.k), age: 0, life,
        rot: range(d.rotation[0], d.rotation[1]), rs: range(d.rotSpeed[0], d.rotSpeed[1]),
        env: rand() * 2 - 1, frame: Math.floor(rand() * this.grid * this.grid), fps: d.fps ? range(d.fps[0], d.fps[1]) : 24,
        lockOffset: d.locked ? weapon.worldToLocal(local.clone()) : null,
      });
    }
  }
  step(dt, rateMul) {
    const d = this.def;
    if (d.mode === 'idle' || (d.mode === 'swing' && this.swinging)) {
      this.acc += d.rate * rateMul * dt;
      const n = Math.floor(this.acc); this.acc -= n; this.spawn(n);
    }
    const acc = new THREE.Vector3(...d.accel).multiplyScalar(this.k);
    const drag = Math.pow(2, -(d.drag || 0) * dt);
    this.parts = this.parts.filter(p => (p.age += dt) < p.life);
    for (const p of this.parts) {
      p.v.addScaledVector(acc, dt).multiplyScalar(drag);
      if (p.lockOffset) { p.lockOffset.addScaledVector(p.v, dt); p.p = weapon.localToWorld(p.lockOffset.clone()); }
      else p.p.addScaledVector(p.v, dt);
      p.rot += p.rs * dt;
    }
  }
  draw(cam) {
    const d = this.def, n = this.grid;
    const camR = new THREE.Vector3(), camU = new THREE.Vector3(), camF = new THREE.Vector3();
    cam.matrixWorld.extractBasis(camR, camU, camF);
    let i = 0;
    for (const p of this.parts) {
      const t = p.age / p.life;
      const size = Math.max(evalNum(d.size, t, p.env), 0) * this.k;
      const alpha = 1 - Math.min(Math.max(evalNum(d.transparency, t), 0), 1);
      if (alpha <= 0.002 || size <= 0) continue;
      const c = evalCol(d.color, t), b = d.brightness ?? 1;
      const sq = d.squash ? evalNum(d.squash, t) : 0;
      let ax = camR.clone(), ay = camU.clone();
      const o = d.orientation || 'FacingCamera';
      if (o === 'FacingCameraWorldUp') {
        ay = new THREE.Vector3(0, 1, 0); ax = new THREE.Vector3().crossVectors(ay, camF).normalize();
      } else if (o === 'VelocityParallel' && p.v.lengthSq() > 1e-6) {
        ay = p.v.clone().normalize(); ax = new THREE.Vector3().crossVectors(ay, camF).normalize();
      } else if (o === 'VelocityPerpendicular' && p.v.lengthSq() > 1e-8) {
        const nrm = p.v.clone().normalize();
        ax = new THREE.Vector3().crossVectors(nrm, Math.abs(nrm.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0)).normalize();
        ay = new THREE.Vector3().crossVectors(nrm, ax).normalize();
      }
      if (o !== 'VelocityParallel') {
        const r = THREE.MathUtils.degToRad(p.rot), cr = Math.cos(r), sr = Math.sin(r);
        const nx = ax.clone().multiplyScalar(cr).addScaledVector(ay, sr), ny = ay.clone().multiplyScalar(cr).addScaledVector(ax, -sr);
        ax = nx; ay = ny;
      }
      const hx = size / 2 * Math.pow(2, -sq), hy = size / 2 * Math.pow(2, sq);
      const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
      let frame = 0;
      if (n > 1) {
        const N = n * n, mode = d.flipMode || 'Loop';
        if (mode === 'Random') frame = p.frame;
        else if (mode === 'OneShot') frame = Math.min(N - 1, Math.floor(t * N));
        else if (mode === 'PingPong') { const f = Math.floor(p.age * p.fps) % (2 * N - 2); frame = f < N ? f : 2 * N - 2 - f; }
        else frame = (Math.floor(p.age * p.fps) + (d.flipRandomStart ? p.frame : 0)) % N;
      }
      const fr = Math.floor(frame / n), fc = frame % n;
      const u0 = fc / n, v0 = 1 - (fr + 1) / n, du = 1 / n;
      const uvs = [[u0, v0], [u0 + du, v0], [u0 + du, v0 + du], [u0, v0 + du]];
      for (let k = 0; k < 4; k++) {
        const [cx, cy] = corners[k];
        const v = p.p.clone().addScaledVector(ax, cx * hx).addScaledVector(ay, cy * hy);
        this.pos.set([v.x, v.y, v.z], (i * 4 + k) * 3);
        this.uv.set(uvs[k], (i * 4 + k) * 2);
        this.col.set([c[0] * b, c[1] * b, c[2] * b, alpha], (i * 4 + k) * 4);
      }
      i++;
    }
    this.geo.setDrawRange(0, i * 6);
    for (const a of ['position', 'uv', 'color']) this.geo.attributes[a].needsUpdate = true;
  }
}

// Ribbon used for Beams and Trails: a strip through world points with per-point width/colour/alpha.
class Ribbon {
  constructor(def, maxPts = 256) {
    this.def = def;
    this.geo = new THREE.BufferGeometry();
    this.pos = new Float32Array(maxPts * 2 * 3); this.uv = new Float32Array(maxPts * 2 * 2); this.col = new Float32Array(maxPts * 2 * 4);
    const idx = [];
    for (let i = 0; i < maxPts - 1; i++) idx.push(i * 2, i * 2 + 1, i * 2 + 3, i * 2, i * 2 + 3, i * 2 + 2);
    this.geo.setIndex(idx);
    this.geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    this.geo.setAttribute('uv', new THREE.BufferAttribute(this.uv, 2));
    this.geo.setAttribute('color', new THREE.BufferAttribute(this.col, 4));
    const t = tex(def.texture).clone(); t.needsUpdate = true; t.wrapS = THREE.RepeatWrapping;
    this.mat = new THREE.MeshBasicMaterial({map: t, vertexColors: true, transparent: true, depthWrite: false,
      blending: (def.lightEmission ?? 1) >= 0.5 ? THREE.AdditiveBlending : THREE.NormalBlending, side: THREE.DoubleSide});
    this.mesh = new THREE.Mesh(this.geo, this.mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 3;
    scene.add(this.mesh); this.max = maxPts;
  }
  // pts: [{p, side (unit vector across), w, u, c:[r,g,b], a}]
  set(pts) {
    const n = Math.min(pts.length, this.max);
    for (let i = 0; i < n; i++) {
      const {p, side, w, u, c, a} = pts[i];
      for (let s = 0; s < 2; s++) {
        const v = p.clone().addScaledVector(side, (s ? 0.5 : -0.5) * w);
        this.pos.set([v.x, v.y, v.z], (i * 2 + s) * 3);
        this.uv.set([u, s], (i * 2 + s) * 2);
        this.col.set([c[0], c[1], c[2], a], (i * 2 + s) * 4);
      }
    }
    this.geo.setDrawRange(0, Math.max(0, n - 1) * 6);
    for (const a of ['position', 'uv', 'color']) this.geo.attributes[a].needsUpdate = true;
  }
}

// ---------------------------------------------------------------- load + build
const preset = (await (await fetch('vfxpresets.json')).json())[presetName];
const gltf = await new GLTFLoader().loadAsync(`models/${model}.glb`);
weapon.add(gltf.scene);
const bb = new THREE.Box3().setFromObject(gltf.scene);
const center = bb.getCenter(new THREE.Vector3());
const toLocal = a => new THREE.Vector3(...a).add(center);            // preset offsets are from the mesh centre
const k = 1;
const anchors = {};
for (const [n, p] of Object.entries(preset.anchors || {})) anchors[n] = toLocal(p);
const regions = {};
for (const [n, r] of Object.entries(preset.regions || {})) regions[n] = {center: toLocal(r.center).toArray(), size: r.size};

const orbitSets = [];
for (const o of preset.orbits || []) {
  const axis = new THREE.Vector3(...o.axis).normalize();
  const ref = Math.abs(axis.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
  const u0 = new THREE.Vector3().crossVectors(axis, ref).normalize();
  const list = [];
  for (let i = 1; i <= o.count; i++) {
    const tilt = (o.tilt || 0) * (((i - 1) % 3) - 1);
    const ax = axis.clone().applyAxisAngle(u0, tilt);
    const r2 = Math.abs(ax.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
    const u = new THREE.Vector3().crossVectors(ax, r2).normalize(), v = new THREE.Vector3().crossVectors(ax, u).normalize();
    list.push({point: new THREE.Vector3(), axis: ax, u, v, phase: (i - 1) * 2 * Math.PI / o.count});
  }
  orbitSets.push({def: o, center: toLocal(o.center), list});
}
const orbitByName = Object.fromEntries(orbitSets.map(s => [s.def.name, s.list]));

const emitters = [];
for (const d of preset.emitters) {
  let sources = [];
  if (d.at.startsWith('orbit:')) sources = orbitByName[d.at.slice(6)].map(o => ({point: o.point}));
  else if (regions[d.at]) sources = [{box: regions[d.at]}];
  else sources = [{point: anchors[d.at]}];
  for (const s of sources) emitters.push(new Emitter(d, s, k));
}

const ribbons = [];
const bolts = [], raySets = [], staticBeams = [];
const boxOrPoint = spec => typeof spec === 'string' ? {point: anchors[spec]} : {box: {center: toLocal(spec.center).toArray(), size: spec.size}};
for (const b of preset.beams || []) {
  if (b.kind === 'beam') staticBeams.push({def: b, r: new Ribbon({...b, lightEmission: b.lightEmission}, 40)});
  else if (b.kind === 'bolt') bolts.push({def: b, r: new Ribbon(b, 40), from: boxOrPoint(b.frm), to: boxOrPoint(b.to), a: null, z: null, c0: 0, c1: 0, on: true, next: 0, ts: 1});
  else if (b.kind === 'rays') {
    const axis = new THREE.Vector3(...b.axis).normalize();
    const ref = Math.abs(axis.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
    const u = new THREE.Vector3().crossVectors(axis, ref).normalize(), v = new THREE.Vector3().crossVectors(axis, u).normalize();
    const list = [];
    for (let i = 1; i <= b.count; i++) list.push({r: new Ribbon(b, 40), tilt: THREE.MathUtils.degToRad(b.cone) * (0.35 + 0.65 * ((i * 0.618) % 1)), phase: (i - 1) * 2 * Math.PI / b.count});
    raySets.push({def: b, axis, u, v, list});
  }
}
const trails = (preset.trails || []).map(d => ({def: d, r: new Ribbon(d, 200), hist: []}));
const lights = (preset.lights || []).map(d => {
  const l = new THREE.PointLight(new THREE.Color(...d.color), d.brightness, d.range * k, 1.2);
  weapon.add(l); l.position.copy(anchors[d.at]); return {def: d, l};
});

// ---------------------------------------------------------------- framing
pivot.rotation.y = THREE.MathUtils.degToRad(yawDeg);
const size = bb.getSize(new THREE.Vector3());
let look = center.clone(), fitR = Math.max(size.x, size.y, size.z) * 0.6 + 0.45;
if (swingAxis === 'x') fitR *= 1.3;          // bows / crossbows: leave room for the burst
if (swingAt !== null) {                       // the blade sweeps around the grip: frame that circle
  const reach = Math.max(...[bb.min, bb.max].flatMap(a => [bb.min, bb.max].map(b => new THREE.Vector3(a.x, b.y, 0).length())));
  look = new THREE.Vector3(0, reach * 0.42, 0); fitR = reach * 0.68 + 0.25;
}
camera.position.set(look.x, look.y + fitR * 0.15, look.z + fitR / Math.tan(THREE.MathUtils.degToRad(15)));
camera.lookAt(look);

// ---------------------------------------------------------------- simulation
let t = 0;
const bezier = (p0, p1, p2, p3, s) => {
  const a = 1 - s;
  return p0.clone().multiplyScalar(a * a * a).addScaledVector(p1, 3 * a * a * s).addScaledVector(p2, 3 * a * s * s).addScaledVector(p3, s * s * s);
};
const attachAxis = () => new THREE.Vector3(1, 0, 0).applyQuaternion(weapon.getWorldQuaternion(new THREE.Quaternion()));

function ribbonAlong(rb, p0, p3, c0, c1, def, uOff, segs = 24, width = def.width) {
  const ax = attachAxis();
  const p1 = p0.clone().addScaledVector(ax, c0), p2 = p3.clone().addScaledVector(ax, -c1);
  const camPos = camera.position;
  const pts = [];
  for (let i = 0; i <= segs; i++) {
    const s = i / segs, p = bezier(p0, p1, p2, p3, s);
    const tan = bezier(p0, p1, p2, p3, Math.min(1, s + 0.01)).sub(bezier(p0, p1, p2, p3, Math.max(0, s - 0.01))).normalize();
    const side = new THREE.Vector3().crossVectors(tan, camPos.clone().sub(p)).normalize();
    const len = p0.distanceTo(p3);
    const col = evalCol(def.color, s), b = def.brightness ?? 1;
    pts.push({p, side, w: (width[0] + (width[1] - width[0]) * s) * k, u: s * len / ((def.textureLength || 1) * k) + uOff,
              c: col.map(x => x * b), a: 1 - evalNum(def.transparency, s)});
  }
  rb.set(pts);
}

function swingAngle(time) {
  if (swingAt === null) return 0;
  const d = time - swingAt, ease = x => (1 - Math.cos(Math.min(Math.max(x, 0), 1) * Math.PI)) / 2;
  if (d < -0.5) return 0;
  if (d < 0) return 0.7 * ease((d + 0.5) / 0.5);
  if (d < 0.28) return 0.7 - 2.3 * ease(d / 0.28);
  return -1.6 * (1 - ease((d - 0.28) / 1.0));
}

function step() {
  t += DT;
  // pose: gentle sway, plus wind-up -> strike -> recover around the grip
  const sway = Math.sin(t * 1.3) * 0.05;
  pivot.rotation.set(swingAxis === 'x' ? sway : 0, THREE.MathUtils.degToRad(yawDeg) + (swingAxis === 'x' ? Math.sin(t * 0.8) * 0.06 : 0),
                     (swingAxis === 'z' ? sway + swingAngle(t) : 0));
  pivot.updateMatrixWorld(true);
  const swinging = swingAt !== null && t >= swingAt && t < swingAt + 0.35;

  for (const set of orbitSets) {
    const o = set.def;
    for (const it of set.list) {
      const a = it.phase + o.speed * t;
      const r = o.radius * k * (1 + 0.15 * (o.wobble || 0) * Math.sin(a * 1.7));
      it.point.copy(set.center).addScaledVector(it.u, Math.cos(a) * r).addScaledVector(it.v, Math.sin(a) * r)
        .addScaledVector(it.axis, o.radius * 0.35 * (o.wobble || 0) * Math.sin(a * 2.3 + it.phase));
    }
  }
  for (const e of emitters) { e.swinging = swinging; e.step(DT, 1); }
  if (burstAt !== null && Math.abs(t - burstAt) < DT / 2) {
    for (const e of emitters) if (e.def.mode === 'burst') e.spawn(e.def.burst);
  }
  for (const tr of trails) {
    const a0 = weapon.localToWorld(anchors[tr.def.a0].clone()), a1 = weapon.localToWorld(anchors[tr.def.a1].clone());
    if (swinging || tr.def.mode === 'always') tr.hist.unshift({a0, a1, t});
    tr.hist = tr.hist.filter(h => t - h.t < tr.def.lifetime);
  }
  for (const l of lights) {
    const d = l.def; let b = d.brightness;
    if (d.pulse[1] > 0) b *= 1 + d.pulse[1] * Math.sin(t * d.pulse[0] * 2 * Math.PI);
    if (d.flicker > 0) b *= 1 + d.flicker * (Math.sin(t * 23.1) * 0.3 + Math.sin(t * 37.7) * 0.2);
    l.l.intensity = Math.max(b, 0) * 1.6;
  }
}

function draw() {
  camera.updateMatrixWorld();
  for (const e of emitters) e.draw(camera);
  for (const b of bolts) {
    if (t >= b.next) {
      const d = b.def; b.next = t + range(d.interval[0], d.interval[1]);
      const pick = s => s.point ? s.point.clone() : new THREE.Vector3(...s.box.center).add(new THREE.Vector3(range(-.5, .5) * s.box.size[0], range(-.5, .5) * s.box.size[1], range(-.5, .5) * s.box.size[2]));
      b.a = pick(b.from); b.z = pick(b.to); b.c0 = range(-d.curve, d.curve); b.c1 = range(-d.curve, d.curve);
      b.on = rand() < d.chance; b.ts = rand() < 0.5 ? -1 : 1;
    }
    if (b.on) ribbonAlong(b.r, weapon.localToWorld(b.a.clone()), weapon.localToWorld(b.z.clone()), b.c0, b.c1, b.def, b.ts * b.def.textureSpeed * t, b.def.segments * 2);
    else b.r.set([]);
  }
  for (const sb of staticBeams) {
    ribbonAlong(sb.r, weapon.localToWorld(anchors[sb.def.a0].clone()), weapon.localToWorld(anchors[sb.def.a1].clone()),
      sb.def.curve[0], sb.def.curve[1], sb.def, sb.def.textureSpeed * t, 16);
  }
  for (const set of raySets) {
    const d = set.def, base = anchors[d.at];
    set.list.forEach((r, i) => {
      const a = r.phase + d.speed * t, len = d.length * k * (0.85 + 0.15 * Math.sin(t * 1.3 + i + 1));
      const dir = set.axis.clone().multiplyScalar(Math.cos(r.tilt)).addScaledVector(set.u.clone().multiplyScalar(Math.cos(a)).addScaledVector(set.v, Math.sin(a)), Math.sin(r.tilt));
      ribbonAlong(r.r, weapon.localToWorld(base.clone()), weapon.localToWorld(base.clone().addScaledVector(dir, len)), 0, 0, d, d.speed * t, 12);
    });
  }
  for (const tr of trails) {
    const d = tr.def, pts = [];
    tr.hist.forEach((h, i) => {
      const age = (t - h.t) / d.lifetime;
      const mid = h.a0.clone().add(h.a1).multiplyScalar(0.5), across = h.a1.clone().sub(h.a0);
      const col = evalCol(d.color, age), b = d.brightness ?? 1;
      pts.push({p: mid, side: across.clone().normalize(), w: across.length() * evalNum(d.width, age), u: age,
                c: col.map(x => x * b), a: 1 - evalNum(d.transparency, age)});
    });
    tr.r.set(pts);
  }
  composer.render();
}

window.renderAt = target => { while (t + 1e-9 < target) step(); draw(); return t; };
window.ready = true;
