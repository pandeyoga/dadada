// Uji peramban W2-C #6 — model biaya kontrak: isian bebas komponen biaya pada kontrak DITAHAN menunggu persetujuan Keuangan (bawaan),
// diputuskan pemegang izin persetujuan lain dari pemohon; pemohon hanya bisa membatalkan.
//   python3 scripts/ui/seed_w2c.py   (sekali per jalan)   lalu   node scripts/ui/w2c_biaya_kontrak.js
// Pemohon: finance@sipro.co.id (staf), penyetuju: finlead@sipro.co.id (manajer keuangan) / owner@sipro.co.id.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const FIN = "finance@sipro.co.id";
const LEAD = "finlead@sipro.co.id";
const OWNER = "owner@sipro.co.id";
const T = (id) => `[data-testid=${id}]`;
const seed = JSON.parse(fs.readFileSync(process.env.SIPRO_UI_SEED_W2C || path.join(os.tmpdir(), "sipro-ui-seed-w2c.json"), "utf8"));
const costs = async (cid) => (await api(OWNER, "GET", `/contracts/${cid}`)).body.data.costs || {};
const openContract = async (page, c) => {
  await page.goto(`${BASE}/customers/${c.customer_id}?tab=kontrak53`);
  await page.waitForSelector(T("contract-panel"), { timeout: 20000 });
};

(async () => {
  const R = reporter("W2-C #6 — model biaya kontrak (UI)");
  for (const k of ["contract.cost_model", "contract.cost_free_input_needs_approval"]) await api(OWNER, "POST", `/settings/${k}/reset?scope=org`);
  const A = seed.ajukan, B = seed.tolak;

  // ---------------------------------------------------------------- pemohon (staf Keuangan) mengisi lewat dialog → ditahan
  const logs = [];
  let s = await openAs(FIN);
  logs.push(s.log);
  try {
    await openContract(s.page, A);
    await s.page.click(T("contract-costs-button"));
    await s.page.waitForSelector(T("contract-costs-dialog"));
    await s.page.fill("#cost-bphtb", "40000000");
    await s.page.fill("#cost-notary_fee", "7500000");
    await s.page.click(T("contract-costs-submit"));
    const toast = await waitToast(s.page, /DITAHAN/);
    R.check("toast: isian DITAHAN menunggu persetujuan Keuangan (bukan 'diperbarui')", !!toast, toast || "(tidak ada)");
    R.check("angka lama tetap berlaku: BPHTB belum tersimpan", (await costs(A.contract_id)).bphtb === undefined);
    await s.page.waitForSelector(T("w2c-request-box"));
    const pending = s.page.locator(`${T("w2c-request-row")}[data-status=pending]`);
    R.check("kotak permohonan menampilkan butir yang diajukan", /BPHTB/.test(await pending.innerText()) && /40\.000\.000/.test(await pending.innerText()), (await pending.innerText()).replace(/\s+/g, " ").slice(0, 160));
    R.check("pemohon tidak melihat tombol setujui/tolak", await s.page.locator(T("w2c-request-approve")).count() === 0 && await s.page.locator(T("w2c-request-reject")).count() === 0);
    R.check("pemohon bisa membatalkan permohonannya", await s.page.locator(T("w2c-request-cancel")).count() === 1);
    await shot(s.page, "w2c-b1-ditahan-pemohon");
  } finally { await s.browser.close(); }
  const first = (await api(FIN, "GET", `/contracts/${A.contract_id}/cost-requests`)).body.data[0];

  // ---------------------------------------------------------------- penyetuju lain (manajer keuangan) menyetujui di UI
  s = await openAs(LEAD);
  logs.push(s.log);
  try {
    await openContract(s.page, A);
    await s.page.waitForSelector(T("w2c-request-approve"));
    R.check("penyetuju melihat tombol setujui & tolak", await s.page.locator(T("w2c-request-reject")).count() === 1);
    await s.page.click(T("w2c-request-approve"));
    R.check("toast: disetujui, isian biaya berlaku", !!(await waitToast(s.page, /Disetujui/)));
    const c = await costs(A.contract_id);
    R.check("backend: BPHTB 40 jt & notaris 7,5 jt kini berlaku", c.bphtb === 40000000 && c.notary_fee === 7500000, JSON.stringify(c).slice(0, 120));
    await s.page.waitForSelector(`${T("w2c-request-row")}[data-status=approved]`);
    R.check("riwayat: baris 'Disetujui' tampil", /Disetujui/.test(await s.page.locator(`${T("w2c-request-row")}[data-status=approved]`).innerText()));
    await shot(s.page, "w2c-b2-disetujui");
  } finally { await s.browser.close(); }
  R.check("permohonan tercatat dengan pemohon ≠ penyetuju", first && first.requested_by === FIN);

  // ---------------------------------------------------------------- pemohon = pemegang izin: tidak boleh menyetujui sendiri; ditolak wajib alasan
  const req = await api(LEAD, "POST", `/contracts/${B.contract_id}/costs`, { insurance: 3000000, bphtb: 20000000 });
  R.check("(API) manajer keuangan sebagai pemohon: 202 ditahan", req.status === 202, String(req.status));
  s = await openAs(LEAD);
  logs.push(s.log);
  try {
    await openContract(s.page, B);
    await s.page.waitForSelector(T("w2c-request-box"));
    R.check("pemohon yang memegang izin persetujuan TIDAK melihat tombol setujui sendiri", await s.page.locator(T("w2c-request-approve")).count() === 0);
    R.check("... tetapi bisa membatalkan", await s.page.locator(T("w2c-request-cancel")).count() === 1);
  } finally { await s.browser.close(); }
  s = await openAs(OWNER);
  logs.push(s.log);
  try {
    await openContract(s.page, B);
    await s.page.waitForSelector(T("w2c-request-reject"));
    await s.page.click(T("w2c-request-reject"));
    const t1 = await waitToast(s.page, /Alasan penolakan/);
    R.check("menolak tanpa alasan: pesan server terbaca di toast", !!t1, t1 || "(tidak ada)");
    await clearToasts(s.page);
    await s.page.fill(T("w2c-request-note"), "angka tidak sesuai invoice notaris");
    await s.page.click(T("w2c-request-reject"));
    R.check("ditolak dengan alasan: toast", !!(await waitToast(s.page, /ditolak/i)));
    R.check("backend: biaya kontrak tetap kosong", (await costs(B.contract_id)).bphtb === undefined);
    await s.page.waitForSelector(`${T("w2c-request-row")}[data-status=rejected]`);
    await shot(s.page, "w2c-b3-ditolak");
  } finally { await s.browser.close(); }

  // ---------------------------------------------------------------- tanpa persetujuan: isian langsung berlaku (perilaku lama), toast biasa
  await api(OWNER, "PUT", "/settings/contract.cost_free_input_needs_approval", { value: false, reason: "uji peramban W2-C langsung berlaku", scope: "org" });
  s = await openAs(FIN);
  logs.push(s.log);
  try {
    await openContract(s.page, B);
    await s.page.click(T("contract-costs-button"));
    await s.page.waitForSelector(T("contract-costs-dialog"));
    await s.page.fill("#cost-bphtb", "12000000");
    await s.page.click(T("contract-costs-submit"));
    R.check("toast 'diperbarui' (bukan ditahan) bila kunci persetujuan nonaktif", !!(await waitToast(s.page, /diperbarui/)));
    R.check("backend: BPHTB langsung berlaku", (await costs(B.contract_id)).bphtb === 12000000);
  } finally {
    await api(OWNER, "POST", "/settings/contract.cost_free_input_needs_approval/reset?scope=org");
    await s.browser.close();
  }
  R.finish(...logs);
})();
