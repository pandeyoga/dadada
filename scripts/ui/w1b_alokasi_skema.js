// Uji peramban W1-B (#9) — lembar AR: panel "Ganti skema ditahan" (pemetaan alokasi kuitansi ke termin baru).
//   SIPRO_UI_BASE=http://localhost:3073 PYTHON=<python backend> node scripts/ui/w1b_alokasi_skema.js
// Menyemai deal berbayar-nyata + permintaan ditahan lewat scripts/ui/seed_w1b.py (satu penyemaian = satu kali jalan), lalu memeriksa:
// panel tampil di lembar AR; alokasi yang tidak sama dengan nominal kuitansi / kelebihan termin ditolak di klien (tombol nonaktif);
// alasan wajib; terapkan → toast, panel hilang, AR & kuitansi di backend sesuai pemetaan.
const { execFileSync } = require("child_process");
const path = require("path");
const { BASE, api, openAs, shot, waitToast, reporter } = require("./lib");

const T = (id) => `[data-testid=${id}]`;
const PY = process.env.PYTHON || "python3";

(async () => {
  const R = reporter("Ganti skema ditahan — pemetaan alokasi (UI)");
  const seed = JSON.parse(execFileSync(PY, [path.join(__dirname, "seed_w1b.py")], { env: process.env }).toString().trim().split("\n").pop());
  const { browser, page, log } = await openAs("finlead@sipro.co.id");
  try {
    await page.goto(`${BASE}/finance?tab=ar`);
    await page.waitForSelector(T("finance-ar-panel"));
    await page.fill(T("data-table-search"), seed.unit_code);
    await page.waitForSelector(T("ar-detail-button"), { timeout: 15000 });
    await page.waitForTimeout(600);
    await page.locator(T("ar-detail-button")).first().click();
    await page.waitForSelector(T("scheme-change-panel"), { timeout: 15000 });
    R.check("panel 'ganti skema ditahan' tampil", await page.locator(T("scheme-change-panel")).count() === 1);
    R.check("dua kuitansi tampil untuk dipetakan", await page.locator(T("scheme-change-receipt")).count() === 2);
    R.check("alasan wajib: tombol terapkan nonaktif saat kosong", await page.locator(T("scheme-change-apply")).isDisabled());
    await shot(page, "w1b-ar-1-panel");

    // alokasi kuitansi 1 diubah jadi 90 jt (≠ 100 jt) → galat klien, tombol nonaktif
    await page.fill(T("scheme-change-reason"), "uji peramban W1-B pemetaan alokasi");
    R.check("pemetaan awal sah (tiap kuitansi ke termin 1) → tombol aktif", !(await page.locator(T("scheme-change-apply")).isDisabled()));
    const amount1 = page.locator(T("scheme-change-amount")).first();
    await amount1.fill("90000000");
    R.check("jumlah tak sama dengan kuitansi → galat & tombol nonaktif",
      /harus tepat/.test(await page.locator(T("scheme-change-errors")).innerText()) && await page.locator(T("scheme-change-apply")).isDisabled());
    await shot(page, "w1b-ar-2-galat");
    await amount1.fill("100000000");

    // sah: kuitansi 2 dibelah 40 jt → termin 1, 20 jt → termin 2
    const rec2 = page.locator(T("scheme-change-receipt")).nth(1);
    await rec2.locator(T("scheme-change-amount")).first().fill("40000000");
    await rec2.getByRole("button", { name: /Tambah baris/ }).click();
    const row2 = rec2.locator(T("scheme-change-amount")).nth(1);
    await row2.fill("20000000");
    await rec2.locator(T("scheme-change-term")).nth(1).click();
    await page.getByRole("option", { name: /^2\./ }).click();
    R.check("pemetaan sah → tidak ada galat", await page.locator(T("scheme-change-errors")).count() === 0);
    await shot(page, "w1b-ar-3-sah");
    await page.click(T("scheme-change-apply"));
    R.check("toast sukses", !!(await waitToast(page, /dipetakan/)));
    await page.waitForTimeout(800);
    R.check("panel hilang sesudah diterapkan", await page.locator(T("scheme-change-panel")).count() === 0);

    const inv = (await api("finlead@sipro.co.id", "GET", `/finance/ar/${seed.deal_id}`)).body;
    const items = inv.data.items;
    R.check("backend: termin 1 = 140 jt, termin 2 = 20 jt, total tetap 160 jt",
      items[0].paid_amount === 140000000 && items[1].paid_amount === 20000000 && Number(inv.data.paid) === 160000000, JSON.stringify(items.map((i) => i.paid_amount)));
    const r2 = inv.receipts.find((r) => r.id === seed.r2);
    R.check("backend: kuitansi 2 diarahkan ke termin baru & alokasi lama tersimpan",
      r2.allocations.length === 2 && r2.allocation_history && r2.allocation_history.length === 1);
    await shot(page, "w1b-ar-4-selesai");
  } finally { await browser.close(); }
  R.finish(log);
})().catch((e) => { console.error(e); process.exit(2); });
