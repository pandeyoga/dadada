// Pembantu bersama skrip uji peramban SIPRO (Playwright). Lihat scripts/ui/README.md.
//
// Lingkungan:
//   SIPRO_UI_BASE   alamat UI satu-origin (UI + proksi /api)        bawaan http://localhost:3073
//   SIPRO_API_BASE  alamat API untuk menyiapkan/ mengubah data       bawaan ${SIPRO_UI_BASE}/api
//   SIPRO_UI_SHOTS  folder tangkapan layar (JANGAN di dalam repo)    bawaan <tmp>/sipro-ui-shots
//   SIPRO_UI_SEED_OUT berkas JSON dari seed_hc.py                    bawaan <tmp>/sipro-ui-seed.json
// Playwright dicari lewat NODE_PATH (mis. NODE_PATH=/opt/node-tools/node_modules).
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const BASE = (process.env.SIPRO_UI_BASE || "http://localhost:3073").replace(/\/$/, "");
const API = (process.env.SIPRO_API_BASE || `${BASE}/api`).replace(/\/$/, "");
const SHOTS = process.env.SIPRO_UI_SHOTS || path.join(os.tmpdir(), "sipro-ui-shots");
fs.mkdirSync(SHOTS, { recursive: true });
// Berkas JSON hasil `seed_hc.py` (id data uji).
const seedPath = process.env.SIPRO_UI_SEED_OUT || path.join(os.tmpdir(), "sipro-ui-seed.json");

const passOf = (email) => (email === "superadmin@estora.id" ? "test1234" : "Sipro#2026");

/** Token API (untuk menyiapkan data / mengubah keadaan "dari sisi lain"). */
const tokens = {};
async function token(email) {
  if (!tokens[email]) {
    const r = await fetch(`${API}/auth/login`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password: passOf(email) }),
    });
    if (!r.ok) throw new Error(`login API ${email}: ${r.status}`);
    tokens[email] = (await r.json()).access_token;
  }
  return tokens[email];
}

/** Panggilan API sebagai `email` -> { status, body }. */
async function api(email, method, url, body) {
  const r = await fetch(`${API}${url}`, {
    method, headers: { "content-type": "application/json", authorization: `Bearer ${await token(email)}` },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let json = null;
  try { json = await r.json(); } catch { /* badan kosong */ }
  return { status: r.status, body: json };
}

/** Buka peramban, masuk lewat formulir login sungguhan. Mengumpulkan galat konsol & respons API >= 400. */
async function openAs(email, { viewport = { width: 1440, height: 900 } } = {}) {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport });
  const page = await ctx.newPage();
  const log = { console: [], http: [], pageerrors: [] };
  page.on("console", (m) => {
    if (m.type() === "error") log.console.push(`${page.url().replace(BASE, "")} :: ${m.text().slice(0, 300)}`);
  });
  page.on("pageerror", (e) => log.pageerrors.push(String(e).slice(0, 300)));
  page.on("response", (r) => {
    if (r.status() >= 400 && r.url().includes("/api/")) {
      log.http.push(`${r.status()} ${r.request().method()} ${r.url().replace(BASE, "")}`);
    }
  });
  await page.goto(`${BASE}/login`);
  await page.fill("[data-testid=login-email-input]", email);
  await page.fill("[data-testid=login-password-input]", passOf(email));
  await page.click("[data-testid=login-submit-button]");
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20000 });
  await page.waitForTimeout(800);
  return { browser, ctx, page, log };
}

/** Tangkapan layar ke folder SHOTS; mengembalikan path-nya. */
async function shot(page, name) {
  await page.waitForTimeout(500);   // biarkan animasi sheet/dialog/toast selesai
  const file = path.join(SHOTS, `${name}.png`);
  await page.screenshot({ path: file });
  return file;
}

/** Teks toast (sonner) yang sedang tampil. */
async function toasts(page) {
  return page.locator("[data-sonner-toast]").allInnerTexts();
}

/** Tunggu toast yang memuat `needle` (string/regex) dan kembalikan teksnya (atau null). */
async function waitToast(page, needle, timeout = 8000) {
  const re = needle instanceof RegExp ? needle : new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
  try {
    const el = page.locator("[data-sonner-toast]").filter({ hasText: re }).first();
    await el.waitFor({ timeout });
    return (await el.innerText()).trim();
  } catch { return null; }
}

/** Tunggu sampai semua toast hilang (supaya toast berikutnya tidak tertukar dengan yang lama). */
async function clearToasts(page, timeout = 8000) {
  try { await page.waitForFunction(() => document.querySelectorAll("[data-sonner-toast]").length === 0, null, { timeout }); } catch { /* biarkan */ }
}

/** Pelapor sederhana: check() mencatat, finish() mencetak ringkasan dan mengatur exit code. */
function reporter(title) {
  const rows = [];
  return {
    check(label, cond, detail = "") {
      rows.push({ label, ok: !!cond, detail });
      console.log(`${cond ? "  OK  " : " GAGAL"} ${label}${detail ? ` — ${detail}` : ""}`);
      return !!cond;
    },
    info(msg) { console.log(`  ..    ${msg}`); },
    finish(...logs) {
      // "Failed to load resource" = cadangan peramban untuk respons 4xx/5xx yang SENGAJA dipancing skenario
      // (terlacak di log.http); yang dihitung gagal hanyalah galat JavaScript/React sungguhan di konsol.
      const NETWORK = /Failed to load resource|ERR_TUNNEL_CONNECTION_FAILED/;
      for (const l of logs) {
        if (!l) continue;
        const real = l.console.filter((x) => !NETWORK.test(x));
        if (real.length) { console.log(`  konsol: ${JSON.stringify(real.slice(0, 5))}`); rows.push({ label: "tanpa galat konsol", ok: false }); }
        if (l.pageerrors.length) { console.log(`  pageerror: ${JSON.stringify(l.pageerrors.slice(0, 5))}`); rows.push({ label: "tanpa pageerror", ok: false }); }
      }
      const bad = rows.filter((r) => !r.ok);
      console.log(`\n${title}: ${rows.length - bad.length}/${rows.length} lulus`);
      process.exitCode = bad.length ? 1 : 0;
    },
  };
}

module.exports = { BASE, API, SHOTS, seedPath, token, api, openAs, shot, toasts, waitToast, clearToasts, reporter };
