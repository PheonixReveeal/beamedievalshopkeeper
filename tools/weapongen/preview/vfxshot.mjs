// node vfxshot.mjs OUT_DIR "preset=Voidrender&model=Voidrender&swing=1.6&burst=1.9" [seconds] [fps] [w] [h]
// Renders frames OUT_DIR/f0000.png ... by stepping the deterministic simulation in vfx.js.
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import {chromium} from 'playwright';
const [, , out, qs, secs = 3.5, fps = 30, w = 560, h = 560] = process.argv;
const root = path.dirname(new URL(import.meta.url).pathname);
const types = {'.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
               '.png': 'image/png', '.glb': 'model/gltf-binary'};
const srv = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, {'Content-Type': types[path.extname(p)] || 'application/octet-stream'}); res.end(d); });
}).listen(0);
const port = srv.address().port;
fs.mkdirSync(out, {recursive: true});
const b = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
const pg = await b.newPage({viewport: {width: +w, height: +h}});
pg.on('pageerror', e => console.log('ERR', e.message));
pg.on('console', m => { if (m.type() === 'error') console.log('console', m.text()); });
await pg.goto(`http://localhost:${port}/vfx.html?w=${w}&h=${h}&${qs}`);
await pg.waitForFunction(() => window.ready, null, {timeout: 120000});
await pg.evaluate(() => window.renderAt(0.02));
await new Promise(r => setTimeout(r, 1500));          // let textures finish decoding
const n = Math.round(secs * fps);
for (let i = 0; i < n; i++) {
  await pg.evaluate(t => window.renderAt(t), 0.5 + i / fps);   // 0.5 s warm-up so the aura is already flowing
  await pg.screenshot({path: path.join(out, `f${String(i).padStart(4, '0')}.png`)});
}
await b.close(); srv.close();
