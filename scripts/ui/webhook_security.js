// Uji peramban layar Pusat Konfigurasi › Keamanan Webhook (H-C).
//   node scripts/ui/webhook_security.js
// Memakai owner (settings:manage) dan sales (hanya settings:view). Rahasia uji SELALU dicabut di akhir.
const { BASE, api, openAs, shot, waitToast, reporter } = require("./lib");

const OWNER = "owner@sipro.co.id";
const SALES = "sales@sipro.co.id";
const URL = `${BASE}/config?tab=webhooks`;
const T = (id) => `[data-testid=${id}]`;
const row = (ch) => `[data-testid=webhook-channel-row][data-channel=${ch}]`;
const SECRET = `uihc-${Date.now().toString(36)}-secret`;
const VERIFY = `uihc-${Date.now().toString(36)}-verify`;

async function resetAll() {
  for (const ch of ["meta_lead", "google_lead", "tiktok_lead"]) {
    await api(OWNER, "PUT", `/webhooks/secrets/${ch}`, ch === "meta_lead"
      ? { secret: "__clear__", verify_token: "__clear__" } : { secret: "__clear__" });
  }
}

(async () => {
  const R = reporter("Keamanan Webhook (UI)");
  await resetAll();
  const { browser, page, log } = await openAs(OWNER);
  try {
    await page.goto(URL);
    await page.waitForSelector(T("webhook-security-panel"));
    R.check("tab Keamanan Webhook tampil", await page.locator(T("config-tab-webhooks")).count() === 1);
    R.check("4 kanal tampil", await page.locator(T("webhook-channel-row")).count() === 4);
    R.check("ringkasan: ada kanal belum aman", (await page.locator(T("webhook-security-summary")).getAttribute("data-state")) === "insecure");
    R.check("peringatan per kanal belum aman (3 kanal selain WhatsApp ikut + WhatsApp)", await page.locator(T("webhook-channel-warning")).count() === 4);
    R.check("catatan operasional menyebut dashboard penyedia",
      /dashboard penyedia/i.test(await page.locator(T("webhook-security-ops-note")).innerText()));
    await shot(page, "hc-webhook-1-awal");

    // --- Google: rahasia pendek ditolak di sisi klien, lalu isi yang sah
    await page.locator(`${row("google_lead")} ${T("webhook-secret-set")}`).click();
    await page.waitForSelector(T("webhook-secret-dialog"));
    R.check("input rahasia bertipe password", (await page.locator(T("webhook-secret-input")).getAttribute("type")) === "password");
    R.check("dialog menyebut ENV alternatif", /GOOGLE_LEAD_WEBHOOK_KEY/.test(await page.locator(T("webhook-env-hint")).innerText()));
    R.check("simpan nonaktif saat kosong", await page.locator(T("webhook-secret-submit")).isDisabled());
    await page.fill(T("webhook-secret-input"), "pendek");
    R.check("simpan nonaktif saat < 8 karakter", await page.locator(T("webhook-secret-submit")).isDisabled());
    await page.fill(T("webhook-secret-input"), SECRET);
    await shot(page, "hc-webhook-2-dialog-isi");
    await page.click(T("webhook-secret-submit"));
    const t1 = await waitToast(page, /disimpan/);
    R.check("toast sukses simpan", !!t1, t1 || "");
    await page.waitForSelector(`${row("google_lead")}[data-secure=true]`);
    R.check("badge Google jadi Aman", /Aman/.test(await page.locator(`${row("google_lead")} ${T("webhook-channel-badge")}`).innerText()));
    R.check("nilai rahasia tidak ada di halaman", !(await page.content()).includes(SECRET));
    R.check("ringkasan masih belum aman (kanal lain)", (await page.locator(T("webhook-security-summary")).getAttribute("data-state")) === "insecure");
    // backend benar-benar menegakkan
    const probe = await fetch(`${BASE}/api/webhooks/google-lead`, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ name: "UIHC", phone: "+628123450001" }) });
    R.check("backend menolak tanpa google_key (401)", probe.status === 401, String(probe.status));

    // --- buka lagi: tombol jadi Ganti, kolom kosong (nilai lama tak pernah ditampilkan)
    await page.locator(`${row("google_lead")} ${T("webhook-secret-set")}`).click();
    await page.waitForSelector(T("webhook-secret-dialog"));
    R.check("tombol 'Ganti' + kolom kosong", (await page.locator(T("webhook-secret-input")).inputValue()) === ""
      && /Ganti/.test(await page.locator(T("webhook-secret-dialog")).innerText()));
    await page.click(T("webhook-secret-cancel"));

    // --- Cabut: wajib konfirmasi
    await page.locator(`${row("google_lead")} ${T("webhook-secret-clear")}`).click();
    await page.waitForSelector(T("webhook-clear-dialog"));
    await shot(page, "hc-webhook-3-konfirmasi-cabut");
    await page.click(T("webhook-clear-cancel"));
    R.check("batal konfirmasi: tetap Aman", (await page.locator(row("google_lead")).getAttribute("data-secure")) === "true");
    await page.locator(`${row("google_lead")} ${T("webhook-secret-clear")}`).click();
    await page.click(T("webhook-clear-confirm"));
    await page.waitForSelector(`${row("google_lead")}[data-secure=false]`);
    R.check("setelah dicabut: Belum aman lagi", true);
    const open = await fetch(`${BASE}/api/webhooks/google-lead`, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ name: "UIHC", phone: "+628123450002" }) });
    R.check("backend kembali menerima (bukan 401)", open.status !== 401, String(open.status));

    // --- Meta: rahasia + verify token; cabut hanya verify token
    await page.locator(`${row("meta_lead")} ${T("webhook-secret-set")}`).click();
    await page.fill(T("webhook-secret-input"), SECRET);
    await page.fill(T("webhook-verify-input"), VERIFY);
    await page.click(T("webhook-secret-submit"));
    await page.waitForSelector(`${row("meta_lead")}[data-secure=true]`);
    R.check("Meta Aman + verify token tersimpan", /Verify token: tersimpan/.test(await page.locator(`${row("meta_lead")} ${T("webhook-channel-source")}`).innerText()));
    R.check("verify token tidak bocor ke halaman", !(await page.content()).includes(VERIFY));
    await page.locator(`${row("meta_lead")} ${T("webhook-secret-clear")}`).click();
    await page.waitForSelector(T("webhook-clear-dialog"));
    R.check("cabut: tanpa pilihan, tombol konfirmasi nonaktif", await page.locator(T("webhook-clear-confirm")).isDisabled());
    await page.click(T("webhook-clear-pick-verify"));
    await page.click(T("webhook-clear-confirm"));
    await waitToast(page, /dicabut/);
    await page.waitForFunction(() => /Verify token: belum diisi/.test(document.body.innerText));
    R.check("hanya verify token yang tercabut, rahasia tetap Aman", (await page.locator(row("meta_lead")).getAttribute("data-secure")) === "true");

    // --- Galat server (409/400) tampil sebagai toast terbaca, dialog tetap terbuka
    await page.route("**/api/webhooks/secrets/tiktok_lead", (route) => route.fulfill({ status: 409, contentType: "application/json",
      body: JSON.stringify({ detail: "Pengaturan webhook baru saja diubah oleh pengguna lain. Muat ulang lalu coba lagi." }) }));
    await page.locator(`${row("tiktok_lead")} ${T("webhook-secret-set")}`).click();
    await page.fill(T("webhook-secret-input"), SECRET);
    await page.click(T("webhook-secret-submit"));
    const t409 = await waitToast(page, /diubah oleh pengguna lain/);
    R.check("409 tampil sebagai toast terbaca", !!t409, t409 || "");
    R.check("dialog tetap terbuka setelah galat", await page.locator(T("webhook-secret-dialog")).count() === 1);
    await page.unroute("**/api/webhooks/secrets/tiktok_lead");
    await page.click(T("webhook-secret-cancel"));

    // --- WhatsApp diatur di tab lain
    R.check("WhatsApp: tombol 'Atur di Integrasi WhatsApp', tanpa Isi/Cabut",
      await page.locator(`${row("whatsapp")} ${T("webhook-wa-link")}`).count() === 1
      && await page.locator(`${row("whatsapp")} ${T("webhook-secret-set")}`).count() === 0);
    await page.locator(`${row("whatsapp")} ${T("webhook-wa-link")}`).click();
    await page.waitForFunction(() => location.search.includes("tab=whatsapp"));
    R.check("pindah ke tab Integrasi WhatsApp", true);

    // --- Peran lain: sales tak bisa membuka Pusat Konfigurasi (RequireAdmin) dan API menolak PUT (403)
    await resetAll();
    const put = await api(SALES, "PUT", "/webhooks/secrets/google_lead", { secret: SECRET });
    R.check("sales: PUT rahasia ditolak 403", put.status === 403, String(put.status));
    const s = await openAs(SALES);
    try {
      await s.page.goto(URL);
      await s.page.waitForTimeout(1500);
      R.check("sales: diarahkan keluar dari /config", !new RegExp("/config").test(s.page.url()), s.page.url());
    } finally { await s.browser.close(); }

    // --- Mode hanya baca (pertahanan berlapis): izin efektif tanpa settings:manage -> tombol ubah tak tampil
    await page.route("**/api/auth/me", async (route) => {
      const res = await route.fetch();
      const j = await res.json();
      j.data.permissions = { permissions: ["manage"], settings: ["view_all"] };
      await route.fulfill({ response: res, json: j });
    });
    await page.goto(URL);
    await page.waitForSelector(T("webhook-security-panel"), { timeout: 10000 });
    R.check("hanya baca: banner tampil", await page.locator(T("webhook-security-readonly")).count() === 1);
    R.check("hanya baca: tanpa tombol Isi/Cabut/Atur WA",
      await page.locator(`${T("webhook-secret-set")}, ${T("webhook-secret-clear")}, ${T("webhook-wa-link")}`).count() === 0);
    await shot(page, "hc-webhook-4-hanya-baca");
  } finally {
    await resetAll();
    await browser.close();
  }
  R.finish(log);
})().catch((e) => { console.error(e); process.exit(2); });
