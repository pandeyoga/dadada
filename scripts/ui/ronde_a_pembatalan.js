// (a) CancellationPanel: kotak pengakuan biaya (acknowledge_costs / cost_note) pada keputusan pembatalan.
//   node scripts/ui/ronde_a_pembatalan.js   (butuh data dari: python3 scripts/ui/seed_hc.py)
// Tiga skenario: (1) setujui dengan pengakuan lengkap (tombol menunggu pengakuan), (2) TOLAK tanpa pengakuan tetap
// boleh, (3) titipan biaya muncul sesudah layar memuat (kotak tak tampil) -> server menolak 400 -> pesan terbaca.
const fs = require("fs");
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter, seedPath } = require("./lib");

const seed = JSON.parse(fs.readFileSync(seedPath, "utf8"));
const OWNER = "owner@sipro.co.id";
const T = (id) => `[data-testid=${id}]`;

async function openDecide(page, s) {
  const cust = (await api(OWNER, "GET", `/contracts/${s.contract_id}`)).body.data.customer_id;
  await page.goto(`${BASE}/customers/${cust}`);
  await page.getByRole("tab", { name: /Kontrak & Legal/ }).click();
  await page.waitForSelector(T("cancellation-panel"), { timeout: 15000 });
  await page.click(T("cancellation-decide-button"));
  await page.waitForSelector(T("cancellation-decide-dialog"));
}

(async () => {
  const R = reporter("(a) Pembatalan — pengakuan biaya");
  // W1-C: bawaan baru `refund_dan_batalkan_invoice` menangani titipan/invoice biaya; skrip ini menguji gerbang pengakuan LAMA,
  // jadi kebijakan org dipasang `manual_dengan_pengakuan` dan DIKEMBALIKAN di akhir.
  await api(OWNER, "PUT", "/settings/cancel.cost_deposit.policy", { value: "manual_dengan_pengakuan", reason: "uji peramban gerbang pengakuan lama", scope: "org" });
  const { browser, page, log } = await openAs(OWNER);
  try {
    // ---- (1) setujui: tombol menunggu pengakuan lengkap
    console.log("\n# setujui dengan pengakuan biaya");
    await openDecide(page, seed.cancel_cost);
    R.check("kotak pengakuan biaya tampil", await page.locator(T("cancellation-cost-hold")).count() === 1);
    await page.fill(T("cancellation-decide-note"), "Setuju dengan catatan keputusan uji peramban");
    const approve = page.locator(T("cancellation-decide-approve"));
    R.check("setujui NONAKTIF sebelum pengakuan dicentang", await approve.isDisabled());
    R.check("petunjuk pengakuan tampil", await page.locator(T("cancellation-cost-ack-hint")).count() === 1);
    await shot(page, "hc-a-1-dialog-biaya");
    await page.locator(T("cancellation-cost-ack-check")).click();
    R.check("masih nonaktif: catatan penanganan kosong", await approve.isDisabled());
    await page.fill(T("cancellation-cost-ack-note"), "singkat");
    R.check("masih nonaktif: catatan penanganan < 10 huruf", await approve.isDisabled());
    await page.fill(T("cancellation-cost-ack-note"), "titipan biaya Rp 20 jt dikembalikan lewat keputusan pemilik terpisah");
    R.check("aktif setelah pengakuan lengkap", await approve.isEnabled());
    await approve.click();
    const ok = await waitToast(page, /Pembatalan disetujui/i);
    R.check("toast sukses persetujuan", !!ok, ok || "(tidak ada toast)");
    await page.waitForFunction(() => document.querySelector("[data-testid=cancellation-row]")?.getAttribute("data-state") === "disetujui");
    R.check("baris pembatalan berstatus disetujui", true);
    await shot(page, "hc-a-2-disetujui");

    // ---- (2) tolak tanpa pengakuan tetap boleh
    console.log("\n# tolak tanpa pengakuan");
    await clearToasts(page);
    await openDecide(page, seed.cancel_cost_reject);
    await page.fill(T("cancellation-decide-note"), "Ditolak: uji peramban tolak tanpa pengakuan");
    R.check("tolak AKTIF tanpa pengakuan biaya", await page.locator(T("cancellation-decide-reject")).isEnabled());
    await page.click(T("cancellation-decide-reject"));
    const rej = await waitToast(page, /ditolak/i);
    R.check("toast tolak", !!rej, rej || "");
    await page.waitForFunction(() => document.querySelector("[data-testid=cancellation-row]")?.getAttribute("data-state") === "ditolak");
    R.check("baris pembatalan berstatus ditolak", true);

    // ---- (3) titipan biaya muncul SESUDAH layar memuat: kotak tak tampil, server menolak, pesan terbaca
    console.log("\n# titipan biaya muncul belakangan (server menolak)");
    await clearToasts(page);
    await page.route("**/api/cancellations/preview**", async (route) => {
      const res = await route.fetch(); const j = await res.json();
      const off = { has_holds: false, titipan_balance: 0, open_invoice_total: 0 };
      j.data.cost_holds = off;
      (j.data.history || []).forEach((h) => { if (h.basis_at_request) h.basis_at_request.cost_holds = off; });
      await route.fulfill({ response: res, json: j });
    });
    await openDecide(page, seed.cancel_cost_stale);
    R.check("kotak pengakuan TIDAK tampil (keadaan basi)", await page.locator(T("cancellation-cost-hold")).count() === 0);
    await page.unroute("**/api/cancellations/preview**");   // sesudah ini pemuatan ulang membawa keadaan sebenarnya
    await page.fill(T("cancellation-decide-note"), "Setuju: uji peramban keadaan basi");
    await page.click(T("cancellation-decide-approve"));
    const err = await waitToast(page, /titipan biaya/i);
    R.check("galat server terbaca di toast", !!err, err || "(tidak ada toast)");
    R.check("toast tak memuat nama kolom teknis 'acknowledge_costs'", !/acknowledge_costs/.test(err || ""), err || "");
    await page.waitForSelector(T("cancellation-cost-hold"), { timeout: 8000 }).catch(() => {});
    R.check("sesudah galat, kotak pengakuan muncul supaya bisa diisi", await page.locator(T("cancellation-cost-hold")).count() === 1);
    await shot(page, "hc-a-3-keadaan-basi");
    R.check("tanpa respons 5xx", !log.http.some((h) => /^5/.test(h)), JSON.stringify(log.http));
  } finally {
    await api(OWNER, "POST", "/settings/cancel.cost_deposit.policy/reset?scope=org");
    await browser.close();
  }
  R.finish(log);
})().catch((e) => { console.error(e); process.exit(2); });
