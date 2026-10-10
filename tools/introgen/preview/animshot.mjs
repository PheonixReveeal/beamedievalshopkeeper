// Renders the R15 previewer headlessly.
//   node animshot.mjs sheet  OUT.png  Anim [views=front,side] [n=10] [cols=5] [cw=230] [ch=270] [prop=broken|intact|none]
//   node animshot.mjs frames OUT_DIR  Anim [view=front] [fps=30] [w=480] [h=480] [prop=...]
//   node animshot.mjs still  OUT.png  Anim [t=0] [view=front] [w=640] [h=640] [prop=...]
// Anim is a file in ../anims (or <Name>Right for a mirrored variant). "-" renders the rest pose.
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import {chromium} from 'playwright';
const [, , mode, out, anim, ...rest] = process.argv;
const o = Object.fromEntries(rest.map(a => a.split('=')));
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const types = {'.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.png': 'image/png'};
const srv = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, {'Content-Type': types[path.extname(p)] || 'application/octet-stream'}); res.end(d); });
}).listen(0);
const port = srv.address().port;
let W, H;
if (mode === 'sheet') {
  const views = (o.views || 'front,side').split(','), n = +(o.n || 10), cols = +(o.cols || 5);
  W = cols * +(o.cw || 230); H = Math.ceil(n / cols) * views.length * +(o.ch || 270);
} else { W = +(o.w || (mode === 'still' ? 640 : 480)); H = +(o.h || W); }
const b = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
const pg = await b.newPage({viewport: {width: W, height: H}});
let failed = false;
pg.on('pageerror', e => { console.log('ERR', e.message); failed = true; });
pg.on('console', m => { if (m.type() === 'error') console.log('console', m.text()); });
const qs = new URLSearchParams({w: W, h: H, ...(anim && anim !== '-' ? {anim} : {}), ...(o.prop ? {prop: o.prop} : {}), ...(o.stamp ? {stamp: o.stamp} : {})});
await pg.goto(`http://localhost:${port}/preview/animview.html?${qs}`);
try { await pg.waitForFunction(() => window.ready, null, {timeout: 60000}); }
catch (e) { console.log('page never became ready'); await b.close(); srv.close(); process.exit(1); }
const info = await pg.evaluate(() => window.info);
if (mode === 'sheet') {
  const views = (o.views || 'front,side').split(','), n = +(o.n || 10), cols = +(o.cols || 5);
  const times = o.times ? o.times.split(',').map(Number) : Array.from({length: n}, (_, i) => n === 1 ? 0 : info.length * i / (n - 1));
  await pg.evaluate(([t, v, c]) => window.renderSheet(t, v, c), [times, views, cols]);
  await pg.screenshot({path: out});
} else if (mode === 'still') {
  await pg.evaluate(([t, v]) => window.renderAt(t, v), [+(o.t || 0), o.view || 'front']);
  await pg.screenshot({path: out});
} else if (mode === 'frames') {
  fs.mkdirSync(out, {recursive: true});
  const fps = +(o.fps || 30), secs = +(o.secs || info.length || 1);
  const nf = Math.max(1, Math.round(secs * fps) + (info.loop ? 0 : 1));
  for (let i = 0; i < nf; i++) {
    await pg.evaluate(([t, v]) => window.renderAt(t, v), [i / fps, o.view || 'front']);
    await pg.screenshot({path: path.join(out, `f${String(i).padStart(4, '0')}.png`)});
  }
}
console.log(JSON.stringify({mode, out, anim, ...info, W, H}));
await b.close(); srv.close();
if (failed) process.exit(1);
