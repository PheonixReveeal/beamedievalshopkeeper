// node shot.mjs out.png "files=a.glb,b.glb&yaw=25" [w] [h]   (serves this folder on a free port)
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import {chromium} from 'playwright';
const [, , out, qs, w = 900, h = 900] = process.argv;
const root = path.dirname(new URL(import.meta.url).pathname);
const types = {'.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary'};
const srv = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, {'Content-Type': types[path.extname(p)] || 'application/octet-stream'}); res.end(d); });
}).listen(0);
const port = srv.address().port;
const b = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
const pg = await b.newPage({viewport: {width: +w, height: +h}});
pg.on('console', m => console.log(m.text())); pg.on('pageerror', e => console.log('ERR', e.message));
await pg.goto(`http://localhost:${port}/index.html?w=${w}&h=${h}&${qs}`);
await pg.waitForFunction(() => window.done, null, {timeout: 120000});
await pg.screenshot({path: out}); await b.close(); srv.close();
