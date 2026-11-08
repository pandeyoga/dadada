// Server statis satu-origin untuk uji peramban: menyajikan hasil build frontend dan meneruskan /api ke backend.
//   node scripts/ui/serve.js <folder build> <port UI> <port backend>
// Memakai express + http-proxy-middleware yang sudah ada di frontend/node_modules (tidak ada dependensi baru).
const path = require("path");
const NM = path.join(__dirname, "..", "..", "frontend", "node_modules");
const express = require(path.join(NM, "express"));
const { createProxyMiddleware } = require(path.join(NM, "http-proxy-middleware"));

const [, , buildDir, port, backendPort] = process.argv;
if (!buildDir || !port || !backendPort) {
  console.error("pemakaian: node scripts/ui/serve.js <folder build> <port UI> <port backend>");
  process.exit(2);
}
const dir = path.resolve(buildDir);
const app = express();
const proxy = createProxyMiddleware("/api", { target: `http://127.0.0.1:${backendPort}`, changeOrigin: false, ws: true });
app.use(proxy);
app.use(express.static(dir));
app.get("*", (req, res) => res.sendFile(path.join(dir, "index.html")));
const server = app.listen(port, "127.0.0.1", () => console.log(`menyajikan ${dir} di :${port} -> backend :${backendPort}`));
server.on("upgrade", proxy.upgrade);
