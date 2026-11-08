// (d) ArDetailSheet: void kuitansi sah + penolakan void pada deal yang sudah batal.
//   node scripts/ui/ronde_d_void.js   (butuh data dari: python3 scripts/ui/seed_hc.py)
const fs = require("fs");
const { BASE, openAs, shot, waitToast, reporter, seedPath } = require("./lib");

const seed = JSON.parse(fs.readFileSync(seedPath, "utf8"));
const T = (id) => `[data-testid=${id}]`;

async function openAr(page, unitCode) {
  await page.goto(`${BASE}/finance?tab=ar`);
  await page.waitForSelector(T("finance-ar-panel"));
  await page.fill(T("data-table-search"), unitCode);
  await page.waitForSelector(`${T("ar-detail-button")}`, { timeout: 15000 });
  await page.waitForTimeout(600);
  await page.locator(T("ar-detail-button")).first().click();
  await page.waitForSelector(T("ar-receipt-void-badge") + ", " + T("ar-receipt-void-btn"), { timeout: 15000 });
}

(async () => {
  const R = reporter("(d) Void kuitansi");
  const { browser, page, log } = await openAs("finlead@sipro.co.id");
  try {
    // --- void yang sah (alasan wajib >= 10 huruf)
    await openAr(page, seed.void_ok.unit_code);
    await shot(page, "hc-d-1-sheet");
    await page.click(T("ar-receipt-void-btn"));
    await page.waitForSelector(T("ar-receipt-void-dialog"));
    R.check("konfirmasi void nonaktif tanpa alasan", await page.locator(T("ar-receipt-void-confirm")).isDisabled());
    await page.fill(T("ar-receipt-void-reason"), "Salah input nominal uji peramban");
    await page.click(T("ar-receipt-void-confirm"));
    const ok1 = await waitToast(page, /dibatalkan/);
    R.check("toast sukses void", !!ok1, ok1 || "");
    await page.waitForSelector(T("ar-receipt-void-badge"));
    R.check("kuitansi berlabel DIBATALKAN, tombol void hilang", await page.locator(T("ar-receipt-void-btn")).count() === 0);
    await shot(page, "hc-d-2-void-ok");
    await page.keyboard.press("Escape");

    // --- deal batal: tombol void tidak boleh ditawarkan; bila server menolak, pesannya terbaca
    await openAr(page, seed.void_batal.unit_code);
    await shot(page, "hc-d-3-deal-batal");
    R.check("deal batal: catatan penjelasan tampil (refund lewat Pembatalan & Refund)", await page.locator(T("ar-void-blocked-note")).count() === 1);
    const voidBtn = page.locator(T("ar-receipt-void-btn"));
    const offered = (await voidBtn.count()) > 0 && (await voidBtn.first().isEnabled());
    R.check("deal batal: tombol batalkan pembayaran tidak aktif/ditawarkan", !offered,
      offered ? "tombol masih aktif — server akan menolak dengan 400" : "");
    if (offered) {
      await voidBtn.first().click();
      await page.fill(T("ar-receipt-void-reason"), "Uji penolakan void pada deal batal");
      await page.click(T("ar-receipt-void-confirm"));
      const err = await waitToast(page, /DIBATALKAN|dibatalkan/i);
      R.check("galat server terbaca di toast", !!err && !/Gagal membatalkan pembayaran\.?$/.test(err), err || "");
      await shot(page, "hc-d-4-void-ditolak");
    }
  } finally { await browser.close(); }
  R.finish(log);
})().catch((e) => { console.error(e); process.exit(2); });
