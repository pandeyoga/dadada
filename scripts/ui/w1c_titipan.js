// Uji peramban W1-C #12 — titipan biaya (2-1470) & invoice biaya terbuka pada deal batal (docs/audit/12).
//   python3 scripts/ui/seed_w1c.py && node scripts/ui/w1c_titipan.js
// Memeriksa: (1) dialog batal reservasi satu-klik menampilkan KEBIJAKAN (bukan kotak pengakuan) dan tidak menahan tombol;
// (2) Keuangan › Pembatalan & Refund memuat permohonan refund; pemohon tidak diberi tombol setujui (maker-checker);
// (3) Manajer Keuangan menyetujui lalu membayar refund; (4) menolak wajib alasan >= 10 huruf; (5) putusan "basi" (400)
// tampil sebagai toast terbaca dan layar menyegarkan diri; (6) kunci baru tampil di kelompok Kebijakan dengan opsi belum tersedia nonaktif.
const fs = require("fs");
const path = require("path");
const os = require("os");
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const seed = JSON.parse(fs.readFileSync(process.env.SIPRO_UI_SEED_W1C || path.join(os.tmpdir(), "sipro-ui-seed-w1c.json"), "utf8"));
const OWNER = "owner@sipro.co.id";
const FINLEAD = "finlead@sipro.co.id";
const T = (id) => `[data-testid=${id}]`;
const sett = async (id) => (await api(OWNER, "GET", `/cancel-cost-settlements/${id}`)).body.data;

(async () => {
  const R = reporter("W1-C #12 titipan biaya deal batal (UI)");
  // ---------------------------------------------------------------- (1) dialog batal satu-klik: kebijakan, bukan pengakuan
  let o = await openAs(OWNER);
  try {
    const s = seed.dialog_deal;
    await o.page.goto(`${BASE}/leads/${s.lead_id}`);
    await o.page.getByRole("tab", { name: /Unit & SPR/ }).click();
    await o.page.waitForSelector(T("deal-cancel-button"), { timeout: 15000 });
    await o.page.click(T("deal-cancel-button"));
    await o.page.waitForSelector(T("deal-cancel-dialog"));
    await o.page.waitForSelector(`${T("deal-cancel-summary")}, ${T("deal-cancel-blocked")}`);
    await o.page.fill(T("deal-cancel-reason"), "Pembeli mundur: uji peramban W1-C kebijakan titipan biaya");
    R.check("pemberitahuan kebijakan tampil", await o.page.locator(T("cancel-cost-policy-notice")).count() === 1);
    R.check("kotak pengakuan lama TIDAK tampil", await o.page.locator(T("cancellation-cost-hold")).count() === 0);
    R.check("tombol Batalkan aktif tanpa pengakuan", await o.page.locator(T("deal-cancel-submit")).isEnabled());
    R.check("notice menyebut persetujuan Keuangan", /disetujui Keuangan/.test(await o.page.locator(T("cancel-cost-policy-notice")).innerText()));
    await shot(o.page, "w1c-1-dialog-kebijakan");
    await o.page.click(T("deal-cancel-submit"));
    R.check("toast sukses batal", !!(await waitToast(o.page, /dibatalkan|kembali tersedia/i)));
    const rows = (await api(OWNER, "GET", `/cancel-cost-settlements?deal_id=${s.deal_id}`)).body.data;
    R.check("permohonan refund lahir otomatis (diajukan)", rows.length === 1 && rows[0].state === "diajukan");

    // ---------------------------------------------------------------- (2) pemohon tidak melihat tombol setujui
    await o.page.goto(`${BASE}/finance?tab=cancellations`);
    await o.page.waitForSelector(T("cost-settlement-panel"), { timeout: 15000 });
    const mine = o.page.locator(T("cost-settlement-row")).filter({ hasText: seed.req_approve.number });
    await mine.waitFor();
    R.check("baris permohonan tampil", await mine.count() === 1);
    R.check("pemohon (OWNER) tidak ditawari Setujui/Tolak", await mine.locator(T("cost-settlement-approve")).count() === 0
      && /Diajukan Anda/.test(await mine.innerText()));
    R.check("ringkasan menyebut yang menunggu persetujuan", /menunggu persetujuan/.test(await o.page.locator(T("cost-settlement-summary")).innerText()));
    await shot(o.page, "w1c-2-pemohon");
  } finally { await o.browser.close(); }

  // ---------------------------------------------------------------- (3) Manajer Keuangan: setujui lalu bayar
  const f = await openAs(FINLEAD);
  try {
    await f.page.goto(`${BASE}/finance?tab=cancellations`);
    await f.page.waitForSelector(T("cost-settlement-panel"), { timeout: 15000 });
    const row = (n) => f.page.locator(T("cost-settlement-row")).filter({ hasText: n });
    const A = seed.req_approve;
    await row(A.number).waitFor();
    R.check("penyetuju melihat Setujui & Tolak", await row(A.number).locator(T("cost-settlement-approve")).count() === 1
      && await row(A.number).locator(T("cost-settlement-reject")).count() === 1);
    await row(A.number).locator(T("cost-settlement-approve")).click();
    await f.page.click(T("cost-settlement-decide-confirm"));
    R.check("toast setuju", !!(await waitToast(f.page, /Disetujui — titipan biaya menjadi utang refund/)));
    await clearToasts(f.page);
    let d = await sett(A.settlement_id);
    R.check("backend: disetujui, refund 17 jt (20 jt dikurangi 3 jt yang sudah disalurkan)", d.state === "disetujui" && d.settlement.refund_amount === 17000000, JSON.stringify(d.settlement && d.settlement.refund_amount));
    await row(A.number).locator(T("cost-settlement-pay")).waitFor();
    R.check("sesudah disetujui muncul Bayar refund", await row(A.number).locator(T("cost-settlement-pay")).count() === 1);
    await shot(f.page, "w1c-3-disetujui");
    await row(A.number).locator(T("cost-settlement-pay")).click();
    await f.page.waitForSelector(T("cost-settlement-pay-confirm"));
    await f.page.waitForTimeout(800);   // pemilih rekening memilih default
    await f.page.click(T("cost-settlement-pay-confirm"));
    R.check("toast refund dibayar", !!(await waitToast(f.page, /Refund titipan biaya dibayar/)));
    await clearToasts(f.page);
    d = await sett(A.settlement_id);
    R.check("backend: refund selesai & lunas", d.state === "selesai" && d.refund_paid_total === 17000000);
    R.check("tombol Bayar hilang sesudah lunas", await row(A.number).locator(T("cost-settlement-pay")).count() === 0);

    // ---------------------------------------------------------------- (4) tolak wajib alasan
    const B = seed.req_reject;
    await row(B.number).locator(T("cost-settlement-reject")).click();
    await f.page.waitForSelector(T("cost-settlement-decide-confirm"));
    R.check("konfirmasi tolak nonaktif tanpa alasan", await f.page.locator(T("cost-settlement-decide-confirm")).isDisabled());
    await f.page.fill(T("cost-settlement-decide-note"), "singkat");
    R.check("masih nonaktif: alasan < 10 huruf", await f.page.locator(T("cost-settlement-decide-confirm")).isDisabled());
    await f.page.fill(T("cost-settlement-decide-note"), "ditolak: dana ditahan untuk sengketa notaris");
    await f.page.click(T("cost-settlement-decide-confirm"));
    R.check("toast tolak", !!(await waitToast(f.page, /Permohonan ditolak/)));
    await clearToasts(f.page);
    d = await sett(B.settlement_id);
    R.check("backend: ditolak", d.state === "ditolak");

    // ---------------------------------------------------------------- (5) putusan basi: 400 terbaca + layar menyegarkan diri
    const C = seed.req_stale;
    await row(C.number).locator(T("cost-settlement-approve")).waitFor();
    const apiOk = await api(FINLEAD, "POST", `/cancel-cost-settlements/${C.settlement_id}/decision`, { approved: true, note: "disetujui dari sisi lain" });
    R.check("(prasyarat) disetujui dari sisi lain", apiOk.status === 200);
    await row(C.number).locator(T("cost-settlement-approve")).click();     // layar belum tahu
    await f.page.click(T("cost-settlement-decide-confirm"));
    const t = await waitToast(f.page, /tidak bisa diputus dua kali/i);
    R.check("toast galat 400 terbaca (bukan 'Network Error')", !!t, t || "(tidak ada toast)");
    await f.page.waitForTimeout(800);
    R.check("layar menyegarkan diri: tombol Setujui basi hilang", await row(C.number).locator(T("cost-settlement-approve")).count() === 0);
    await shot(f.page, "w1c-4-basi");
    R.check("tanpa respons 5xx", !f.log.http.some((h) => /^5/.test(h)), JSON.stringify(f.log.http));

    // ---------------------------------------------------------------- (6) kunci baru di Pusat Konfigurasi › Aturan Bisnis › Kebijakan
    const own = await openAs(OWNER);
    try {
      await own.page.goto(`${BASE}/config?tab=rules&group=kebijakan`);
      await own.page.waitForSelector(T("config-rules-panel"));
      const rule = (k) => own.page.locator(T("config-rules-row")).filter({ hasText: k });
      await rule("cancel.cost_deposit.policy").first().waitFor();
      for (const k of ["cancel.accrual_reversal.commission", "cancel.accrual_reversal.marketing_fee", "cancel.accrual_reversal.tax",
        "cancel.cost_deposit.policy", "cancel.cost_deposit.forfeit_pct", "cancel.cost_deposit.requires_approval"]) {
        R.check(`kunci ${k} tampil generik`, await rule(k).count() === 1);
      }
      R.check("bawaan titipan biaya = refund + batalkan invoice", /Refund titipan ke pembeli/.test(await rule("cancel.cost_deposit.policy").innerText()));
      await rule("cancel.accrual_reversal.commission").locator(T("config-rule-select")).click();
      const semua = own.page.locator(T("config-enum-option-balik_otomatis_semua"));
      R.check("opsi 'balik otomatis semua' ditandai belum tersedia", /belum tersedia/.test(await semua.innerText()));
      R.check("…dan nonaktif", (await semua.getAttribute("data-disabled")) !== null);
      R.check("opsi 'belum dibayar' bisa dipilih", (await own.page.locator(T("config-enum-option-balik_otomatis_yang_belum_dibayar")).getAttribute("data-disabled")) === null);
      await shot(own.page, "w1c-5-kunci-kebijakan");
      await own.page.keyboard.press("Escape");
      await rule("cancel.accrual_reversal.tax").locator(T("config-rule-select")).click();
      R.check("pajak: kedua opsi otomatis nonaktif", (await own.page.locator(T("config-enum-option-balik_otomatis_yang_belum_dibayar")).getAttribute("data-disabled")) !== null
        && (await own.page.locator(T("config-enum-option-balik_otomatis_semua")).getAttribute("data-disabled")) !== null);
      R.finish(own.log, f.log);
    } finally { await own.browser.close(); }
  } finally { await f.browser.close(); }
})().catch((e) => { console.error(e); process.exit(2); });
