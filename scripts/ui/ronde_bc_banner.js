// (b) banner tab "Komponen Biaya" (Pusat Konfigurasi) dan (c) GlReconcileBanner (Keuangan › Dashboard).
//   node scripts/ui/ronde_bc_banner.js
// Keadaan merah/indikator/jurnal gagal tidak bisa dibuat lewat API tanpa merusak buku, jadi dipalsukan di sisi
// peramban dengan page.route (respons /finance/reconcile); keadaan hijau memakai data nyata.
const { BASE, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const T = (id) => `[data-testid=${id}]`;
const check = (code, ok, extra = {}) => ({ code, label: `Pemeriksaan ${code}`, gl: 100, subledger: ok ? 100 : 40, diff: ok ? 0 : 60, ok, hint: "petunjuk uji", ...extra });

(async () => {
  const R = reporter("(b)+(c) Banner katalog biaya & rekonsiliasi GL");
  const { browser, page, log } = await openAs("owner@sipro.co.id");
  try {
    // ------------------------------------------------ (b)
    console.log("\n# (b) tab Komponen Biaya");
    await page.goto(`${BASE}/config?tab=price`);
    await page.waitForSelector(T("config-price-panel"));
    const banner = await page.locator(T("config-price-panel")).innerText();
    R.check("banner: katalog referensi, tidak mengubah tagihan/jurnal", /Katalog referensi/.test(banner) && /belum mengubah tagihan maupun jurnal/.test(banner));
    R.check("banner mengarahkan ke tab Biaya All-in", /Biaya All-in/.test(banner));
    R.check("tabel komponen biaya terisi", await page.locator(T("config-price-row")).count() > 0);
    await page.locator(T("config-price-edit")).first().click();
    await page.waitForSelector("[role=dialog]");
    R.check("dialog ubah komponen terbuka", true);
    await page.keyboard.press("Escape");
    await shot(page, "hc-b-banner-komponen-biaya");

    // ------------------------------------------------ (c) keadaan nyata (hijau)
    console.log("\n# (c) rekonsiliasi nyata");
    await page.goto(`${BASE}/finance`);
    await page.waitForSelector(T("gl-reconcile-banner"));
    const state = await page.locator(T("gl-reconcile-banner")).getAttribute("data-state");
    R.check("lampu nyata hijau (rekonsiliasi lulus)", state === "ok", state);
    await page.click(T("gl-reconcile-toggle"));
    const rows = await page.locator("[data-testid^=gl-reconcile-row-]").count();
    R.check("rincian memuat 12 pemeriksaan", rows === 12, String(rows));
    await shot(page, "hc-c-1-nyata");

    // ------------------------------------------------ (c) keadaan palsu: selisih + indikator + jurnal gagal
    console.log("\n# (c) selisih + indikator + jurnal gagal (palsu)");
    const bad = {
      ok: false, failed: 1, indicators_off: 1, events_pending: 2, events_retrying: 1, events_failed: 2, can_retry_events: true,
      checks: [check("2-1100", false, { label: "Utang Usaha vs Σ tagihan AP" }), check("1-1300", false, { indicator: true, label: "Piutang Usaha (indikator)" }), check("TB", true)],
      failed_events: [{ id: "e1", type: "receipt.created", last_error: "akun 4-9999 tidak ada" }, { id: "e2", type: "bast.recorded", last_error: "periode terkunci" }],
    };
    let retryStatus = 200;
    await page.route("**/api/finance/reconcile", (route) => route.fulfill({ json: { data: bad } }));
    await page.route("**/api/finance/events/retry-failed", (route) => (retryStatus === 200
      ? route.fulfill({ json: { total: 2, still_failed: 1 } })
      : route.fulfill({ status: 403, json: { detail: "Hanya Manajer Keuangan yang boleh memproses ulang jurnal." } })));
    await page.reload();
    await page.waitForSelector(T("gl-reconcile-banner"));
    R.check("lampu merah saat ada selisih nyata", (await page.locator(T("gl-reconcile-banner")).getAttribute("data-state")) === "mismatch");
    const head = await page.locator(T("gl-reconcile-banner")).innerText();
    R.check("judul menghitung hanya selisih non-indikator (1 akun)", /1 akun kendali SELISIH/.test(head), head.split("\n")[0]);
    R.check("jumlah jurnal gagal & menunggu tampil", /2 jurnal otomatis GAGAL/.test(head) && /1 jurnal dicoba ulang/.test(head) && /2 jurnal menunggu/.test(head));
    await page.click(T("gl-reconcile-toggle"));
    const rowInd = page.locator(`${T("gl-reconcile-row-1-1300")}`);
    R.check("baris indikator ditandai 'tidak menggagalkan lampu'", /Indikator \(tidak menggagalkan lampu\)/.test(await rowInd.innerText()));
    R.check("daftar event gagal tampil dengan alasannya", /periode terkunci/.test(await page.locator(T("gl-failed-events")).innerText()));
    await shot(page, "hc-c-2-merah-palsu");
    await page.click(T("gl-reconcile-retry"));
    const t1 = await waitToast(page, /masih gagal/);
    R.check("proses ulang sebagian: toast peringatan terbaca", !!t1, t1 || "(tidak ada toast)");
    await clearToasts(page);
    retryStatus = 403;
    await page.click(T("gl-reconcile-retry"));
    const t2 = await waitToast(page, /Manajer Keuangan/);
    R.check("proses ulang ditolak 403: pesan server terbaca", !!t2, t2 || "(tidak ada toast)");

    // ------------------------------------------------ (c) hanya indikator menyimpang (lampu tetap hijau)
    console.log("\n# (c) hanya indikator menyimpang (palsu)");
    const indOnly = { ok: true, failed: 0, indicators_off: 1, events_pending: 0, events_retrying: 0, events_failed: 0,
      checks: [check("2-1100", true), check("1-1300", false, { indicator: true, label: "Piutang Usaha (indikator)" })], failed_events: [] };
    await page.unroute("**/api/finance/reconcile");
    await page.route("**/api/finance/reconcile", (route) => route.fulfill({ json: { data: indOnly } }));
    await page.reload();
    await page.waitForSelector(T("gl-reconcile-banner"));
    R.check("lampu hijau walau ada indikator menyimpang", (await page.locator(T("gl-reconcile-banner")).getAttribute("data-state")) === "ok");
    const headInd = await page.locator(T("gl-reconcile-banner")).innerText();
    R.check("judul memberi tahu ada indikator yang menyimpang (bukan 'semuanya sama')", /indikator/i.test(headInd), headInd.split("\n")[0]);
    await shot(page, "hc-c-3-indikator-saja");
    R.check("tanpa error konsol selain respons 403 palsu", log.console.filter((x) => !/403|Failed to load resource/.test(x)).length === 0, JSON.stringify(log.console));
  } finally { await browser.close(); }
  R.finish(log);
})().catch((e) => { console.error(e); process.exit(2); });
