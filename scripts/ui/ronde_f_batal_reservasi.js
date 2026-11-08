// (f) Batal reservasi SATU-KLIK (CancelDealDialog): titipan/invoice biaya yang menggantung harus diakui.
//   node scripts/ui/ronde_f_batal_reservasi.js   (butuh data dari seed_hc.py dan backend dengan `cost_holds` di cancel-preview)
const fs = require("fs");
const { BASE, api, openAs, shot, waitToast, reporter, seedPath } = require("./lib");

const seed = JSON.parse(fs.readFileSync(seedPath, "utf8"));
const OWNER = "owner@sipro.co.id";
const T = (id) => `[data-testid=${id}]`;

async function openDialog(page, s) {
  await page.goto(`${BASE}/leads/${s.lead_id}`);
  await page.getByRole("tab", { name: /Unit & SPR/ }).click();
  await page.waitForSelector(T("deal-cancel-button"), { timeout: 15000 });
  await page.click(T("deal-cancel-button"));
  await page.waitForSelector(T("deal-cancel-dialog"));
  await page.waitForSelector(`${T("deal-cancel-summary")}, ${T("deal-cancel-blocked")}`);
}

(async () => {
  const R = reporter("(f) Batal reservasi satu-klik — pengakuan biaya");
  const pv = (await api(OWNER, "GET", `/deals/${seed.deal_cancel_cost.deal_id}/cancel-preview`)).body.data;
  if (!("cost_holds" in pv)) {
    console.log("  ..    backend belum memuat `cost_holds` pada cancel-preview (butuh perubahan H-A) — dilewati");
    return;
  }
  const { browser, page, log } = await openAs(OWNER);
  try {
    console.log("\n# deal dengan titipan biaya + invoice biaya terbuka");
    await openDialog(page, seed.deal_cancel_cost);
    await page.fill(T("deal-cancel-reason"), "Pembeli mundur: uji peramban batal satu-klik");
    R.check("kotak pengakuan biaya tampil", await page.locator(T("cancellation-cost-hold")).count() === 1);
    const submit = page.locator(T("deal-cancel-submit"));
    R.check("tombol Batalkan NONAKTIF sebelum pengakuan", await submit.isDisabled());
    R.check("petunjuk memakai kata kerja batal (bukan 'menyetujui')", /melanjutkan pembatalan/.test(await page.locator(T("cancellation-cost-ack-hint")).innerText()));
    await shot(page, "hc-f-1-dialog-biaya");
    await page.locator(T("cancellation-cost-ack-check")).click();
    await page.fill(T("cancellation-cost-ack-note"), "singkat");
    R.check("masih nonaktif: catatan < 10 huruf", await submit.isDisabled());
    await page.fill(T("cancellation-cost-ack-note"), "titipan biaya Rp 20 jt dikembalikan lewat keputusan pemilik terpisah");
    R.check("aktif setelah pengakuan lengkap", await submit.isEnabled());
    await submit.click();
    const t = await waitToast(page, /dibatalkan|kembali tersedia/i);
    R.check("toast sukses batal", !!t, t || "(tidak ada toast)");
    const d = (await api(OWNER, "GET", `/deals/${seed.deal_cancel_cost.deal_id}`)).body.data;
    R.check("deal benar-benar batal + pengakuan tercatat di deal", d.status === "cancelled" && !!d.cancel_cost_ack, JSON.stringify(d.cancel_cost_ack || null).slice(0, 120));
    await shot(page, "hc-f-2-batal-sukses");

    console.log("\n# deal biasa (tanpa biaya menggantung)");
    await openDialog(page, seed.deal_cancel_plain);
    await page.fill(T("deal-cancel-reason"), "Pembeli mundur: uji peramban deal biasa");
    R.check("tanpa kotak pengakuan", await page.locator(T("cancellation-cost-hold")).count() === 0);
    R.check("tombol Batalkan aktif tanpa pengakuan", await page.locator(T("deal-cancel-submit")).isEnabled());
    await page.click(T("deal-cancel-submit"));
    const t2 = await waitToast(page, /dibatalkan|kembali tersedia/i);
    R.check("toast sukses batal (deal biasa)", !!t2, t2 || "");
    R.check("tanpa respons 5xx", !log.http.some((h) => /^5/.test(h)), JSON.stringify(log.http));
  } finally { await browser.close(); }
  R.finish(log);
})().catch((e) => { console.error(e); process.exit(2); });
