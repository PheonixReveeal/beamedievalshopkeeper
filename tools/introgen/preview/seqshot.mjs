// Renders a cutscene animatic (preview/seqview.html) to numbered frames.
//   node seqshot.mjs OUT_DIR [seq=Opening] [fps=30] [w=960] [h=540] [from=0] [to=length]
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import {chromium} from 'playwright';
const [, , out, ...rest] = process.argv;
const o = Object.fromEntries(rest.map(a => a.split('=')));
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const types = {'.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png'};
const srv = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, {'Content-Type': types[path.extname(p)] || 'application/octet-stream'}); res.end(d); });
}).listen(0);
const W = +(o.w || 960), H = +(o.h || 540), fps = +(o.fps || 30);
const b = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
const pg = await b.newPage({viewport: {width: W, height: H}});
let failed = false;
pg.on('pageerror', e => { console.log('ERR', e.message); failed = true; });
await pg.goto(`http://localhost:${srv.address().port}/preview/seqview.html?w=${W}&h=${H}&seq=${o.seq || 'Opening'}`);
await pg.waitForFunction(() => window.ready, null, {timeout: 60000});
const info = await pg.evaluate(() => window.info);
fs.mkdirSync(out, {recursive: true});
const from = +(o.from || 0), to = +(o.to || info.length);
const n = Math.round((to - from) * fps);
for (let i = 0; i <= n; i++) {
  await pg.evaluate(t => window.renderAt(t), from + i / fps);
  await pg.screenshot({path: path.join(out, `f${String(i).padStart(4, '0')}.png`)});
}
console.log(JSON.stringify({frames: n + 1, ...info}));
await b.close(); srv.close();
if (failed) process.exit(1);
