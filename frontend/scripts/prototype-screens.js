#!/usr/bin/env node
/*
 * Tangkapan layar semua rute prototipe "Rumah Dalam Genggaman" + cek luapan horizontal.
 *
 * Pemakaian (dari folder frontend, setelah `yarn build`):
 *   NODE_PATH="$(npm root -g)" node scripts/prototype-screens.js \
 *     [--out ../docs/prototype/screens] [--port 4173] [--only W8,S2] [--now 2026-11-25T09:41:00+07:00]
 *
 * Playwright dipakai dari instalasi global (di kontainer pengembang: /usr/local/lib/node_modules_global).
 * - Melayani `frontend/build` dengan server http Node bawaan (fallback SPA ke index.html).
 * - Jam peramban dibekukan (bawaan Rabu 25 Nov 2026 09.41 WIB) agar gambar sama setiap kali dibuat.
 * - Untuk setiap entri screens.json: siapkan state lewat /app/demo + window.__rdgDemo
 *   (persona menurut `surface`; warga = sesudah BAST; S2/W8 kirim SOS dulu, W8 juga diterima
 *   satpam; S1/S3 buat undangan tamu), buka `path`, tunggu [data-screen], jalankan klik
 *   tambahan bila ada (mis. P5 memilih VA), simpan dua PNG ke folder peran:
 *   `<ID2>-<slug>.png` (halaman penuh: tinggi viewport = scrollHeight, maks 8000 px) dan
 *   `<ID2>-<slug>--layar.png` (layar pertama; pengelola 1366×900 @1x, selain itu 390×844 @2x).
 * - Tanpa --only: juga membuat `00-lembar-kontak.png` per folder, `index.json`, dan `README.md` di folder keluaran.
 * - Ukur ulang di lebar 360 px: catat bila scrollWidth > innerWidth.
 * - Cetak "N layar, M overflow"; keluar kode 1 bila ada luapan atau galat halaman.
 * - Permintaan ke luar 127.0.0.1 diblokir (prototipe tidak boleh memakai jaringan).
 */
const http = require("http");
const fs = require("fs");
const path = require("path");

let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (e) {
  console.error('Playwright tidak ditemukan. Jalankan dengan NODE_PATH="$(npm root -g)" (Playwright terpasang global).');
  process.exit(2);
}

const FRONTEND = path.resolve(__dirname, "..");
const BUILD = path.join(FRONTEND, "build");
const SCREENS = require(path.join(FRONTEND, "src/prototype/screens.json"));
const names = require("./screen-names");
const MAX_FULL_HEIGHT = 8000;

function parseArgs(argv) {
  const opts = {
    out: path.resolve(FRONTEND, "../docs/prototype/screens"), port: 4173, only: null,
    now: "2026-11-25T09:41:00+07:00",
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--out") opts.out = path.resolve(argv[(i += 1)]);
    else if (a === "--port") opts.port = Number(argv[(i += 1)]);
    else if (a === "--only") opts.only = new Set(argv[(i += 1)].split(","));
    else if (a === "--now") opts.now = argv[(i += 1)];
    else {
      console.error(`Argumen tidak dikenal: ${a}`);
      process.exit(2);
    }
  }
  return opts;
}

// ---------------------------------------------------------------- server statis
const TYPES = {
  ".html": "text/html; charset=utf-8", ".js": "application/javascript", ".mjs": "application/javascript",
  ".css": "text/css", ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg",
  ".svg": "image/svg+xml", ".ico": "image/x-icon", ".woff": "font/woff", ".woff2": "font/woff2",
  ".txt": "text/plain", ".map": "application/json", ".webmanifest": "application/manifest+json",
};

function send(res, status, file) {
  res.writeHead(status, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
}

function fail(res, status, text) {
  res.writeHead(status, { "Content-Type": "text/plain; charset=utf-8" });
  res.end(text);
}

/** Server statis: berkas yang ada → 200; rute tanpa ekstensi → index.html (SPA); aset hilang → 404; URL rusak → 400. */
function createServer(root) {
  const index = path.join(root, "index.html");
  return http.createServer((req, res) => {
    let urlPath;
    try {
      urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
    } catch (e) {
      return fail(res, 400, "URL tidak valid");
    }
    const file = path.normalize(path.join(root, urlPath));
    if (file !== root && !file.startsWith(root + path.sep)) return fail(res, 404, "Tidak ditemukan");
    return fs.stat(file, (err, st) => {
      if (!err && st.isFile()) return send(res, 200, file);
      // Aset (punya ekstensi) yang hilang harus 404, bukan index.html, agar galat muat terlihat.
      if (path.extname(urlPath)) return fail(res, 404, "Tidak ditemukan");
      return send(res, 200, index); // fallback SPA untuk rute /app/...
    });
  });
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    const onError = (err) => {
      server.removeListener("error", onError);
      if (err.code === "EADDRINUSE" && port !== 0) {
        console.log(`Port ${port} terpakai, memakai port bebas.`);
        resolve(listen(server, 0));
      } else reject(err);
    };
    server.once("error", onError);
    server.listen(port, "127.0.0.1", () => {
      server.removeListener("error", onError);
      resolve(server.address().port);
    });
  });
}

// ---------------------------------------------------------------- persiapan state
const PERSONA = { buyer: "buyer", resident: "resident", satpam: "satpam", manager: "pengelola", partner: "mitra" };
// Langkah tambahan per layar (dijalankan di halaman lewat window.__rdgDemo).
const EXTRA = { T1: "bast", S2: "sos", W8: "sos-diterima", W7: "tamu", S1: "tamu", S3: "tamu" };
// Klik berurutan setelah layar tampil, agar gambar menunjukkan inti layar.
const AFTER = {
  P5: ["button:has-text('Pilih metode bayar')", ".rdg-pay-method >> nth=0"],
  W7: ["button[aria-label^='Lihat QR']"],
  W13: ["button:has-text('Token listrik')"],
  S3: ["button:has-text('Pindai QR')"],
};

async function prepare(page, base, entry) {
  await page.goto(`${base}/app/demo`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-screen="U1"]', { timeout: 15000 });
  await page.waitForFunction(() => window.__rdgDemo && typeof window.__rdgDemo.reset === "function");
  await page.evaluate(
    async ({ persona, extra }) => {
      const d = window.__rdgDemo;
      d.reset();
      // Warga ditampilkan sesudah serah terima (BAST), seperti alur demo.
      if (extra === "bast" || persona === "resident") d.simulateBast();
      if (persona) d.setPersona(persona);
      if (extra && extra.startsWith("sos")) {
        const sos = await d.sendSos("kemalingan");
        if (extra === "sos-diterima") await d.acceptSos(sos.id);
      }
      if (extra === "tamu") {
        const wib = new Date(Date.now() + 7 * 3600000);
        const h = wib.getUTCHours();
        const pad = (n) => String(n).padStart(2, "0");
        await d.createGuestPass({
          guestName: "Yoga Pradipta",
          date: wib.toISOString().slice(0, 10),
          from: `${pad(Math.max(h - 1, 0))}:00`,
          to: h >= 22 ? "23:59" : `${pad(h + 2)}:00`,
        });
      }
    },
    { persona: PERSONA[entry.surface] || null, extra: EXTRA[entry.id] || null }
  );
}

async function settle(page, id) {
  await page.waitForSelector(`[data-screen="${id}"]`, { timeout: 15000 });
  // Tunggu data dari lapisan layanan selesai dimuat (Loading = role=status "Memuat…").
  await page
    .waitForFunction(
      () => ![...document.querySelectorAll('[role="status"]')].some((el) => /Memuat/.test(el.textContent || "")),
      null,
      { timeout: 8000 }
    )
    .catch(() => {});
  await page.evaluate(() => (document.fonts ? document.fonts.ready : null));
  // Lebih lama dari jeda layanan terpanjang (600 ms) agar layar tanpa indikator Memuat (mis. P1) sudah berisi data.
  await page.waitForTimeout(700);
}

async function overflowAt360(page) {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.waitForTimeout(250);
  return page.evaluate(() => {
    const doc = document.documentElement;
    if (doc.scrollWidth <= window.innerWidth) return null;
    // Penyebab: elemen yang melewati tepi kanan dan tidak berada di dalam wadah gulir/terpotong.
    const clipped = (el) => {
      for (let p = el.parentElement; p && p !== doc; p = p.parentElement) {
        if (getComputedStyle(p).overflowX !== "visible") return true;
      }
      return false;
    };
    const culprits = [...document.querySelectorAll("[data-screen] *")]
      .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 0.5 && !clipped(el))
      .slice(0, 3)
      .map((el) => `${el.tagName.toLowerCase()}.${String(el.className).split(" ").slice(0, 2).join(".")}`);
    return { scrollWidth: doc.scrollWidth, innerWidth: window.innerWidth, culprits };
  });
}

// ---------------------------------------------------------------- utama
/** Potret setiap entri; hasil luapan/galat/permintaan terblokir dikumpulkan ke larik/set yang diberikan. */
async function capture({ browser, base, opts, entries, blocked, overflow, failures }) {
  const newPage = async (viewport, deviceScaleFactor) => {
    const context = await browser.newContext({
      viewport, deviceScaleFactor, serviceWorkers: "block", reducedMotion: "reduce",
      locale: "id-ID", timezoneId: "Asia/Jakarta",
    });
    if (opts.now) await context.clock.setFixedTime(new Date(opts.now));
    await context.route("**/*", (route) => {
      const url = new URL(route.request().url());
      if (url.hostname === "127.0.0.1") return route.continue();
      blocked.add(`${route.request().resourceType()} ${url.origin}${url.pathname}`);
      return route.abort();
    });
    const page = await context.newPage();
    page.errors = [];
    page.on("pageerror", (err) => page.errors.push(err.message));
    return page;
  };
  const pages = {
    mobile: await newPage({ width: 390, height: 844 }, 2),
    desktop: await newPage({ width: 1366, height: 900 }, 1),
  };

  for (const entry of entries) {
    const desktop = entry.surface === "manager";
    const page = desktop ? pages.desktop : pages.mobile;
    const viewport = desktop ? { width: 1366, height: 900 } : { width: 390, height: 844 };
    page.errors.length = 0;
    try {
      await page.setViewportSize(viewport);
      await prepare(page, base, entry);
      await page.goto(`${base}${entry.path}`, { waitUntil: "domcontentloaded" });
      await settle(page, entry.id);
      for (const selector of AFTER[entry.id] || []) {
        await page.click(selector, { timeout: 5000 });
        await page.waitForTimeout(900); // jeda lapisan layanan 200–600 ms
      }
      if (AFTER[entry.id]) await page.evaluate(() => window.scrollTo(0, 0));
      const dir = path.join(opts.out, names.folderFor(entry.id));
      fs.mkdirSync(dir, { recursive: true });
      const base0 = path.join(dir, names.screenFileName(entry));
      await page.screenshot({ path: `${base0}--layar.png` });
      // Halaman penuh: perbesar viewport setinggi isi agar elemen fixed (menu bawah, SOS) tetap di dasar.
      const height = await page.evaluate(() => document.documentElement.scrollHeight);
      await page.setViewportSize({ width: viewport.width, height: Math.min(Math.max(height, viewport.height), MAX_FULL_HEIGHT) });
      await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
      await page.waitForTimeout(150);
      await page.screenshot({ path: `${base0}.png` });
      await page.setViewportSize(viewport);
      const over = await overflowAt360(page);
      if (over) overflow.push({ id: entry.id, ...over });
      if (page.errors.length) failures.push({ id: entry.id, error: page.errors.join(" | ") });
      const flag = over ? `  LUAPAN ${over.scrollWidth}>${over.innerWidth} ${over.culprits.join(", ")}` : "";
      console.log(`${entry.id.padEnd(4)} ${entry.path}${flag}`);
    } catch (err) {
      failures.push({ id: entry.id, error: err.message.split("\n")[0] });
      console.log(`${entry.id.padEnd(4)} ${entry.path}  GAGAL: ${err.message.split("\n")[0]}`);
    }
  }
}

// ---------------------------------------------------------------- lembar kontak, index, README
const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;");

async function contactSheets(browser, out) {
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const folders = [...new Set(SCREENS.map((s) => names.folderFor(s.id)))];
  for (const folder of folders) {
    const items = SCREENS.filter((s) => names.folderFor(s.id) === folder);
    const desktop = items[0].surface === "manager";
    const cells = items
      .map((e) => {
        const f = path.join(out, folder, `${names.screenFileName(e)}--layar.png`);
        const uri = `data:image/png;base64,${fs.readFileSync(f).toString("base64")}`;
        return `<figure><figcaption>${esc(names.id2(e.id))} · ${esc(e.title)}</figcaption><img src="${uri}"></figure>`;
      })
      .join("");
    const cols = desktop ? 3 : 6;
    const html = `<!doctype html><meta charset="utf-8"><style>
      body{margin:0;padding:24px;width:1552px;background:#f1f5f9;font-family:system-ui,sans-serif}
      h1{margin:0 0 16px;font-size:22px;color:#0f172a}
      .g{display:grid;grid-template-columns:repeat(${cols},1fr);gap:20px 16px}
      figure{margin:0}figcaption{font-size:${desktop ? 16 : 14}px;font-weight:600;color:#0f172a;margin-bottom:6px}
      img{width:100%;display:block;border:1px solid #cbd5e1;border-radius:6px;background:#fff}
    </style><h1>${esc(folder)} · lembar kontak (layar pertama)</h1><div class="g">${cells}</div>`;
    await page.setContent(html, { waitUntil: "load" });
    await page.screenshot({ path: path.join(out, folder, "00-lembar-kontak.png"), fullPage: true });
  }
  await context.close();
}

function writeIndex(out) {
  const rel = (f) => path.relative(path.resolve(FRONTEND, ".."), path.join(out, f)).split(path.sep).join("/");
  const index = SCREENS.map((e) => {
    const folder = names.folderFor(e.id);
    const n = names.screenFileName(e);
    return {
      id: e.id, id2: names.id2(e.id), title: e.title, desc: e.desc, route: e.path, role: names.roleFor(e.id),
      folder, full: rel(`${folder}/${n}.png`), first: rel(`${folder}/${n}--layar.png`),
    };
  });
  fs.writeFileSync(path.join(out, "index.json"), `${JSON.stringify(index, null, 2)}\n`);
  const lines = [
    "# Tangkapan layar prototipe",
    "",
    "Tangkapan layar semua halaman prototipe \"Rumah Dalam Genggaman\", dikelompokkan per peran. Dibuat otomatis oleh `frontend/scripts/prototype-screens.js` dari `frontend/src/prototype/screens.json`.",
    "",
    "**Penamaan.** Setiap halaman punya dua berkas di folder perannya: `<ID>-<judul>.png` dan `<ID>-<judul>--layar.png`. ID = huruf peran + nomor dua digit (mis. `W18`); judul ditulis huruf kecil dan disambung tanda hubung.",
    "",
    "- **Halaman penuh** (`W18-pasar-warga.png`): seluruh isi halaman dari atas sampai bawah (maksimal 8000 px), menu bawah di dasar gambar. Halaman penuh ponsel diperkecil ke lebar 488 px (sekitar @1,25) agar ukuran folder wajar; dasbor pengelola 1366 px.",
    "- **Layar pertama** (`W18-pasar-warga--layar.png`): yang terlihat sekilas saat halaman dibuka. Ponsel 390×844 @2x; dasbor pengelola 1366×900 @1x.",
    "- `00-lembar-kontak.png` di tiap folder: kumpulan layar pertama untuk dilihat sekilas.",
    "- `index.json`: daftar mesin-baca (ID, judul, penjelasan, rute, peran, jalur berkas) untuk bahan presentasi.",
    "",
    "**Membuat ulang** (dari folder `frontend`):",
    "",
    "```bash",
    "REACT_APP_BACKEND_URL=http://127.0.0.1:9 yarn build",
    "NODE_PATH=\"$(npm root -g)\" node scripts/prototype-screens.js",
    "python3 scripts/optimize-screens.py",
    "```",
    "",
  ];
  const folders = [...new Set(index.map((i) => i.folder))];
  folders.forEach((folder) => {
    const rows = index.filter((i) => i.folder === folder);
    lines.push(`## ${rows[0].role} (\`${folder}/\`)`, "", `[Lembar kontak](${folder}/00-lembar-kontak.png)`, "");
    lines.push("| ID | Halaman | Penjelasan | Rute | Berkas |", "|---|---|---|---|---|");
    rows.forEach((r) => {
      const base = `${folder}/${path.basename(r.full)}`;
      lines.push(`| ${r.id2} | ${r.title.replace(/\|/g, "\\|")} | ${r.desc} | \`${r.route}\` | [halaman penuh](${base}), [layar pertama](${base.replace(/\.png$/, "--layar.png")}) |`);
    });
    lines.push("");
  });
  fs.writeFileSync(path.join(out, "README.md"), lines.join("\n"));
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (!fs.existsSync(path.join(BUILD, "index.html"))) {
    console.error("frontend/build belum ada. Jalankan `yarn build` dulu.");
    process.exit(2);
  }
  fs.mkdirSync(opts.out, { recursive: true });
  const server = createServer(BUILD);
  const port = await listen(server, opts.port);
  const base = `http://127.0.0.1:${port}`;
  let browser = null;
  const blocked = new Set();
  const overflow = [];
  const failures = [];
  const entries = SCREENS.filter((s) => !opts.only || opts.only.has(s.id));
  try {
    browser = await chromium.launch();
    await capture({ browser, base, opts, entries, blocked, overflow, failures });
    if (!opts.only && !failures.length) {
      await contactSheets(browser, opts.out);
      writeIndex(opts.out);
    }
  } finally {
    // Selalu tutup peramban dan server, juga bila ada galat di tengah jalan.
    if (browser) await browser.close().catch(() => {});
    server.close();
  }

  if (blocked.size) {
    console.log("\nPermintaan ke luar yang diblokir:");
    [...blocked].sort().forEach((b) => console.log(`  ${b}`));
  }
  if (failures.length) {
    console.log("\nGalat:");
    failures.forEach((f) => console.log(`  ${f.id}: ${f.error}`));
  }
  overflow.forEach((o) => console.log(`Luapan ${o.id}: ${o.scrollWidth}px > ${o.innerWidth}px (${o.culprits.join(", ")})`));
  console.log(`\n${entries.length} layar, ${overflow.length} overflow`);
  console.log(`PNG: ${path.relative(process.cwd(), opts.out) || "."}`);
  process.exit(overflow.length || failures.length ? 1 : 0);
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { createServer, listen };
