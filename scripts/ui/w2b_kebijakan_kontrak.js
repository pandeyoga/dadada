// Uji peramban W2-B — panel "Kebijakan kontrak" (BPHTB per kontrak) di lembar Kontrak & Legal pembeli (docs/audit/12 keputusan #3).
//   node scripts/ui/w2b_kebijakan_kontrak.js        (menyemai sendiri lewat API; tidak butuh seed_*.py)
// Memeriksa: nilai efektif + asal tampil (bawaan mengikuti skema), ringkasan BPHTB pembeli/developer, mengubah per kontrak (alasan wajib,
// minimal 10 karakter), pilihan Dibagi + porsi developer, kembali mengikuti proyek/organisasi, riwayat, pesan 400 server tampil sebagai toast
// yang terbaca, kunci terkunci setelah uang bergerak (tombol nonaktif + alasan), dan staf Keuangan hanya bisa membaca (tanpa tombol ubah).
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const OWNER = "owner@sipro.co.id";
const SALES = "sales@sipro.co.id";
const FINLEAD = "finlead@sipro.co.id";
const STAF = "finance@sipro.co.id";
const T = (id) => `[data-testid="w2b-policy-${id}"]`;
const K_BY = "bphtb.borne_by";
const K_PCT = "bphtb.developer_share_pct";
const NAME = `UI W2B ${Date.now().toString(36)}`;
const rp = (n) => `Rp ${Number(n).toLocaleString("id-ID")}`;

async function seedContract(projectId, units, i, schemeId, allinId) {
  const lead = (await api(SALES, "POST", "/leads", { name: `UI W2B ${NAME} ${i}`, phone: `+62813${Date.now().toString().slice(-8)}${i}`, source: "manual" })).body.data;
  const deal = (await api(SALES, "POST", "/deals/reserve", { unit_id: units[i].id, lead_id: lead.id, booking_fee: 0, scheme_id: schemeId, allin_scheme_id: allinId })).body.data;
  await api(SALES, "POST", `/deals/${deal.id}/book`, {});
  let contract = (await api(OWNER, "GET", `/deals/${deal.id}`)).body.data.contract_id;
  if (!contract) contract = (await api(SALES, "POST", `/deals/${deal.id}/convert`, {})).body.data.contract.id;
  const c = (await api(OWNER, "GET", `/contracts/${contract}`)).body.data;
  return { deal: deal.id, id: contract, customer: c.customer_id };
}

const comps = async (cid) => Object.fromEntries(((await api(OWNER, "GET", `/contracts/${cid}`)).body.data.costs.components || []).map((c) => [c.code, [c.treatment, c.amount]]));

async function openPanel(page, k) {
  await page.goto(`${BASE}/customers/${k.customer}`);
  await page.getByRole("tab", { name: /Kontrak & Legal/ }).click();
  await page.waitForSelector(T("panel"), { timeout: 20000 });
}

async function chooseOption(page, rx) {
  await page.click(T("value"));
  await page.getByRole("option", { name: rx }).click();
}

async function submitDialog(page, reason) {
  await page.fill(T("reason"), reason);
  await page.click(T("submit"));
}

(async () => {
  const R = reporter("Kebijakan kontrak — BPHTB per kontrak (UI)");
  const proj = (await api(OWNER, "POST", "/projects", { name: NAME, location: "uji" })).body.data;
  await api(OWNER, "POST", `/projects/${proj.id}/units`, { prefix: `W2B${Date.now().toString(36).toUpperCase().slice(-4)}`, count: 6, type: "Tipe 45/90", price: 500000000, start_index: 1 });
  const units = (await api(OWNER, "GET", `/units?project_id=${proj.id}&limit=50`)).body.data.sort((a, b) => a.code.localeCompare(b.code));
  const scheme = (await api(OWNER, "GET", "/finance/config/payment-schemes")).body.data.find((s) => s.name === "Cash Bertahap (3x)").id;
  const allin = (await api(OWNER, "GET", "/allin-schemes")).body.data.find((s) => s.code === "EXCLUDE").id;
  const k1 = await seedContract(proj.id, units, 0, scheme, allin);   // alur utama
  const k2 = await seedContract(proj.id, units, 1, scheme, allin);   // kunci setelah uang bergerak (pesan 400)
  const k3 = await seedContract(proj.id, units, 2, scheme, allin);   // peran staf: hanya baca
  const logs = [];
  try {
    // ======================================================= Manajer Keuangan: alur utama
    {
      const { browser, page, log } = await openAs(FINLEAD); logs.push(log);
      await openPanel(page, k1);
      const row = (key) => page.locator(T(`row-${key}`));
      R.check("panel Kebijakan kontrak tampil dengan dua kunci", await page.locator("[data-testid^=\"w2b-policy-row-\"]").count() === 2);
      R.check("bawaan: Penanggung BPHTB = Pembeli, asal mengikuti skema all-in", await row(K_BY).getAttribute("data-value") === "pembeli"
        && /skema all-in/i.test(await page.locator(T(`origin-${K_BY}`)).innerText()));
      R.check("ringkasan BPHTB: Rp 21.000.000 → pembeli 21.000.000 · developer 0",
        /21\.000\.000/.test(await page.locator(T("summary")).innerText()) && /Rp\s*0/.test(await page.locator(T("summary-dev")).innerText()));
      R.check("tombol 'Ikuti proyek/organisasi' TIDAK ada selama belum ditimpa", await page.locator(T(`clear-${K_BY}`)).count() === 0);
      await shot(page, "w2b-1-panel-bawaan");

      // --- alasan wajib ≥ 10 karakter
      await page.click(T(`edit-${K_BY}`));
      await page.waitForSelector(T("dialog"));
      await chooseOption(page, /^Developer/);
      R.check("simpan NONAKTIF sebelum alasan diisi", await page.locator(T("submit")).isDisabled());
      await page.fill(T("reason"), "pendek");
      R.check("simpan masih NONAKTIF: alasan < 10 karakter", await page.locator(T("submit")).isDisabled());
      await submitDialog(page, "pembeli minta BPHTB ditanggung developer (kesepakatan SPR)");
      R.check("toast sukses 'Kebijakan kontrak diperbarui'", !!(await waitToast(page, /Kebijakan kontrak diperbarui/)));
      R.check("toast info: invoice biaya dibatalkan & diterbitkan ulang", !!(await waitToast(page, /Invoice biaya yang belum dibayar dibatalkan/)));
      await page.waitForSelector(`${T(`row-${K_BY}`)}[data-value=developer]`);
      R.check("nilai = Developer, asal 'Khusus kontrak ini'", /Khusus kontrak ini/.test(await page.locator(T(`origin-${K_BY}`)).innerText()));
      R.check("ringkasan: pembeli Rp 0 · developer Rp 21.000.000",
        /21\.000\.000/.test(await page.locator(T("summary-dev")).innerText()) && /Rp\s*0/.test(await page.locator(T("summary-buyer")).innerText()));
      const c1 = await comps(k1.id);
      R.check("backend: komponen BPHTB = developer_borne 21 jt; notaris tetap pembeli", JSON.stringify(c1.BPHTB) === '["developer_borne",21000000]' && c1.NOTARY_FEE[0] === "customer_pass_through", JSON.stringify(c1));
      R.check("tombol 'Ikuti proyek/organisasi' kini muncul", await page.locator(T(`clear-${K_BY}`)).count() === 1);
      await clearToasts(page);
      await shot(page, "w2b-2-developer");

      // --- Dibagi + porsi developer
      await page.click(T(`edit-${K_BY}`));
      await chooseOption(page, /^Dibagi/);
      await submitDialog(page, "disepakati ulang: BPHTB dibagi dengan developer");
      await waitToast(page, /Kebijakan kontrak diperbarui/);
      await page.waitForSelector(`${T(`row-${K_BY}`)}[data-value=dibagi]`);
      await clearToasts(page);
      await page.click(T(`edit-${K_PCT}`));
      await page.waitForSelector(T("share"));
      await page.fill(T("share"), "30");
      await submitDialog(page, "porsi developer 30 persen sesuai kesepakatan");
      await waitToast(page, /Kebijakan kontrak diperbarui/);
      await page.waitForSelector(`${T(`row-${K_PCT}`)}[data-value="30"]`);
      const c2 = await comps(k1.id);
      R.check("backend: dibagi 70/30 → BPHTB pembeli 14.700.000 + BPHTB_DEV developer 6.300.000",
        JSON.stringify(c2.BPHTB) === '["customer_pass_through",14700000]' && JSON.stringify(c2.BPHTB_DEV) === '["developer_borne",6300000]', JSON.stringify(c2));
      R.check("ringkasan memuat bagian pembeli 14.700.000 dan developer 6.300.000",
        /14\.700\.000/.test(await page.locator(T("summary-buyer")).innerText()) && /6\.300\.000/.test(await page.locator(T("summary-dev")).innerText()));
      await clearToasts(page);
      await shot(page, "w2b-3-dibagi");

      // --- kembali mengikuti proyek/organisasi
      await page.click(T(`clear-${K_BY}`));
      await page.waitForSelector(T("dialog"));
      R.check("cabut penimpaan: alasan tetap wajib", await page.locator(T("submit")).isDisabled());
      await submitDialog(page, "kembali mengikuti pengaturan proyek");
      R.check("toast 'Kembali mengikuti pengaturan proyek/organisasi'", !!(await waitToast(page, /Kembali mengikuti pengaturan proyek/)));
      await page.waitForSelector(`${T(`row-${K_BY}`)}[data-value=pembeli]`);
      R.check("nilai kembali Pembeli (skema), tombol cabut hilang", /skema all-in/i.test(await page.locator(T(`origin-${K_BY}`)).innerText())
        && await page.locator(T(`clear-${K_BY}`)).count() === 0);
      const c3 = await comps(k1.id);
      R.check("backend: BPHTB kembali pembeli 21 jt tanpa baris BPHTB_DEV", JSON.stringify(c3.BPHTB) === '["customer_pass_through",21000000]' && !c3.BPHTB_DEV, JSON.stringify(c3));
      // --- riwayat
      await page.locator(T("history")).locator("summary").click();
      R.check("riwayat memuat ≥ 4 perubahan (aktor, dari → ke, alasan)", await page.locator(T("history-row")).count() >= 4
        && /finlead@sipro\.co\.id/.test(await page.locator(T("history-row")).first().innerText()));
      await shot(page, "w2b-4-riwayat");
      await browser.close();
    }

    // ======================================================= pesan 400 server terbaca (kunci setelah uang bergerak)
    {
      const { browser, page, log } = await openAs(FINLEAD); logs.push(log);
      await openPanel(page, k2);
      await page.click(T(`edit-${K_BY}`));
      await page.waitForSelector(T("dialog"));
      await chooseOption(page, /^Developer/);
      await page.fill(T("reason"), "uji pesan 400 setelah uang bergerak");
      // sementara dialog terbuka, Keuangan menerima kuitansi biaya (uang BPHTB bergerak) → server akan menolak
      const led = (await api(OWNER, "GET", `/contracts/${k2.id}/costs-ledger`)).body.data;
      const inv = led.invoices.find((i) => i.status !== "void");
      const pf = await uploadProof();
      const pay = await api(STAF, "POST", `/cost-invoices/${inv.id}/pay`, { amount: 1000000, proof_file_ids: [pf] });
      R.check("(semai) kuitansi biaya diterima", pay.status === 200, String(pay.status));
      await page.click(T("submit"));
      const msg = await waitToast(page, /kuitansi biaya/i);
      R.check("toast 400 server terbaca: 'Sudah ada kuitansi biaya … tidak bisa diubah'", !!msg && /tidak bisa diubah/.test(msg), msg || "tidak ada toast");
      R.check("dialog tetap terbuka dan komponen tidak berubah", await page.locator(T("dialog")).count() === 1 && (await comps(k2.id)).BPHTB[0] === "customer_pass_through");
      await shot(page, "w2b-5-toast-400");
      await page.keyboard.press("Escape");
      await page.reload();
      await page.getByRole("tab", { name: /Kontrak & Legal/ }).click();
      await page.waitForSelector(T("panel"));
      R.check("sesudah muat ulang: alasan terkunci tampil, tombol ubah nonaktif",
        /kuitansi biaya/.test(await page.locator(T(`locked-${K_BY}`)).innerText()) && await page.locator(T(`edit-${K_BY}`)).isDisabled());
      await shot(page, "w2b-6-terkunci");
      await browser.close();
    }

    // ======================================================= staf Keuangan: hanya membaca
    {
      const { browser, page, log } = await openAs(STAF); logs.push(log);
      await openPanel(page, k3);
      R.check("staf Keuangan melihat nilai efektif", await page.locator(T(`row-${K_BY}`)).getAttribute("data-value") === "pembeli");
      R.check("staf Keuangan TIDAK ditawari tombol ubah (tanpa finance:manage)", await page.locator(T(`edit-${K_BY}`)).count() === 0
        && await page.locator(T(`edit-${K_PCT}`)).count() === 0);
      await shot(page, "w2b-7-staf");
      await browser.close();
    }
  } finally {
    await api(OWNER, "POST", `/settings/${K_BY}/reset?scope=project&scope_id=${proj.id}`);
  }
  R.finish(...logs);
})().catch((e) => { console.error(e); process.exit(1); });

async function uploadProof() {
  // bukti pembayaran mungil (PNG 1×1) lewat API unggah sungguhan
  const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg==", "base64");
  const { token } = require("./lib");
  const fd = new FormData();
  fd.append("file", new Blob([png], { type: "image/png" }), `bukti-${Date.now()}.png`);
  fd.append("owner_type", "generic");
  const API = (process.env.SIPRO_API_BASE || `${BASE}/api`).replace(/\/$/, "");
  const r = await fetch(`${API}/files/upload`, { method: "POST", headers: { authorization: `Bearer ${await token(STAF)}` }, body: fd });
  return (await r.json()).data.id;
}
