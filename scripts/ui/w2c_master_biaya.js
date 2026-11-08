// Uji peramban W2-C #16 — satu master komponen biaya: Pusat Konfigurasi › Komponen Biaya (banner jujur + laporan selisih katalog vs aturan,
// migrasi, selaraskan) dan Aturan Bisnis (kunci cost.master_mode / cost.component_max_amount / contract.cost_model /
// contract.cost_free_input_needs_approval; opsi katalog_sumber hanya bila selisih 0).
//   node scripts/ui/w2c_master_biaya.js
// Memakai org utama (owner@sipro.co.id). Awal: migrasi + selaraskan lewat API → nol selisih. Semua pengaturan dikembalikan di akhir.
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const OWNER = "owner@sipro.co.id";
const T = (id) => `[data-testid=${id}]`;
const MODE = "cost.master_mode";
const MAXK = "cost.component_max_amount";

const reset = (key) => api(OWNER, "POST", `/settings/${key}/reset?scope=org`);
const eff = async (key) => (await api(OWNER, "GET", `/settings/effective?keys=${key}`)).body.data[key];
const diff = async () => (await api(OWNER, "GET", "/cost-master/diff")).body.data;

async function settle() {
  await api(OWNER, "POST", "/cost-master/migrate");
  const r = await api(OWNER, "POST", "/cost-master/sync", { reason: "rapikan master untuk uji peramban W2-C" });
  if (r.status !== 200) throw new Error(`sync gagal: ${r.status} ${JSON.stringify(r.body)}`);
}

(async () => {
  const R = reporter("W2-C #16 — satu master komponen biaya (UI)");
  for (const k of [MODE, MAXK, "contract.cost_model", "contract.cost_free_input_needs_approval"]) await reset(k);
  await settle();
  const { browser, page, log } = await openAs(OWNER);
  const rulesRow = (key) => page.locator(T("config-rules-row")).filter({ hasText: key });
  let notary = null;
  try {
    // ---------------------------------------------------------------- banner & laporan selisih (nol)
    await page.goto(`${BASE}/config?tab=price`);
    await page.waitForSelector(T("config-price-panel"));
    await page.waitForSelector(T("w2c-diff-summary"));
    const banner = await page.locator(T("w2c-master-banner")).innerText();
    R.check("banner jujur: mode bayangan, belum mengubah tagihan/jurnal, rujuk tab Biaya All-in",
      (await page.locator(T("w2c-master-banner")).getAttribute("data-mode")) === "bayangan"
      && /Mode bayangan/.test(banner) && /belum mengubah tagihan maupun jurnal/.test(banner) && /Biaya All-in/.test(banner), banner.slice(0, 80));
    R.check("banner lama ('Katalog referensi — belum mengubah …') tidak lagi dipakai", !/Katalog referensi —/.test(banner));
    R.check("laporan selisih: nol selisih setelah selaraskan", (await page.locator(T("w2c-diff-summary")).getAttribute("data-zero")) === "1");
    R.check("opsi 'Katalog sebagai sumber' tersedia", (await page.locator(T("w2c-katalog-sumber-status")).getAttribute("data-available")) === "1");
    R.check("peta field tampil (≥ 8 baris)", await page.locator(`${T("w2c-field-map")} tbody tr`).count() >= 8);
    R.check("tabel katalog memuat baris bermuatan biaya (ditagih/ditalangi + cara hitung)", await page.locator(T("w2c-cost-bill")).count() >= 4);
    await shot(page, "w2c-1-selisih-nol");

    // ---------------------------------------------------------------- selisih nyata → tampil → selaraskan lewat UI
    notary = (await api(OWNER, "GET", "/catalog/price-components")).body.data.find((r) => r.code === "NOTARY_FEE");
    const before = notary.cost.amount;
    const put = await api(OWNER, "PUT", `/catalog/price-components/${notary.id}`, { cost: { amount: before + 500000 } });
    R.check("(API) mengubah blok biaya katalog diterima (mode bayangan: tidak memengaruhi tagihan)", put.status === 200, JSON.stringify(put.body).slice(0, 120));
    await page.reload();
    await page.waitForSelector(T("w2c-diff-summary"));
    R.check("selisih terdeteksi: ringkasan merah/kuning, data-zero=0", (await page.locator(T("w2c-diff-summary")).getAttribute("data-zero")) === "0");
    const rowN = page.locator(T("w2c-diff-row")).filter({ has: page.locator('[data-field="amount"]') });
    R.check("baris NOTARY_FEE menampilkan butir 'amount' katalog → aturan", (await rowN.count()) === 1 && /NOTARY_FEE/.test(await rowN.innerText())
      && new RegExp(`${before + 500000}`).test(await rowN.innerText()) && new RegExp(`${before}`).test(await rowN.innerText()), (await rowN.first().innerText()).replace(/\s+/g, " "));
    R.check("opsi katalog_sumber ditandai belum tersedia + alasan", (await page.locator(T("w2c-katalog-sumber-status")).getAttribute("data-available")) === "0"
      && /belum tersedia/.test(await page.locator(T("w2c-katalog-sumber-status")).innerText()));
    await shot(page, "w2c-2-selisih-terdeteksi");

    // Aturan Bisnis: opsi katalog_sumber nonaktif dengan alasan (dihitung server dari bukti data)
    await page.goto(`${BASE}/config?tab=rules&group=kebijakan`);
    await page.waitForSelector(T("config-rules-panel"));
    await rulesRow(MODE).first().waitFor();
    await rulesRow(MODE).locator(T("config-rule-select")).click();
    const opt = page.locator(T("config-enum-option-katalog_sumber"));
    R.check("Aturan Bisnis: 'katalog_sumber' nonaktif + 'belum tersedia' saat selisih ≠ 0", /belum tersedia/.test(await opt.innerText())
      && (await opt.getAttribute("data-disabled")) !== null);
    R.check("'bayangan' tetap bisa dipilih", (await page.locator(T("config-enum-option-bayangan")).getAttribute("data-disabled")) === null);
    await page.keyboard.press("Escape");

    await page.goto(`${BASE}/config?tab=price`);
    await page.waitForSelector(T("w2c-diff-summary"));
    await page.click(T("w2c-sync"));
    R.check("dialog selaraskan: tombol nonaktif bila alasan < 10 huruf", await page.locator(T("w2c-sync-confirm")).isDisabled());
    await page.fill(T("w2c-sync-reason"), "uji peramban: samakan katalog dengan aturan");
    await page.click(T("w2c-sync-confirm"));
    R.check("toast: katalog diselaraskan, tagihan tidak berubah", !!(await waitToast(page, /Katalog diselaraskan/)));
    await page.waitForFunction((sel) => document.querySelector(sel)?.getAttribute("data-zero") === "1", T("w2c-diff-summary"));
    R.check("setelah selaraskan: selisih nol lagi", (await diff()).summary.nol === true);
    await clearToasts(page);
    await page.click(T("w2c-migrate"));
    R.check("migrasi diulang idempoten: 'tidak ada perubahan'", !!(await waitToast(page, /tidak ada perubahan/)));

    // ---------------------------------------------------------------- dialog ubah: baris biaya vs baris harga
    const costRow = page.locator(T("config-price-row")).filter({ hasText: "NOTARY_FEE" });
    await costRow.locator(T("config-price-edit")).click();
    await page.waitForSelector(T("w2c-cost-form"));
    R.check("dialog baris biaya: blok biaya (cara hitung, ditagih/ditalangi, GL beban/titipan/AP)",
      await page.locator(T("w2c-cost-calc")).count() === 1 && await page.locator(T("w2c-cost-treatment")).count() === 1 && await page.locator(T("w2c-cost-form-gl")).count() === 1);
    R.check("kolom turunan (nilai bawaan lama) tidak bisa diedit di baris biaya", await page.locator(T("config-price-form-value")).count() === 0);
    await shot(page, "w2c-3-dialog-biaya");
    await page.keyboard.press("Escape");
    await page.locator(T("config-price-row")).filter({ hasText: "UNIT_PRICE" }).locator(T("config-price-edit")).click();
    await page.waitForSelector(T("config-price-form-value"));
    R.check("dialog baris harga (bukan komponen biaya) tetap bentuk lama", await page.locator(T("w2c-cost-form")).count() === 0);
    await page.keyboard.press("Escape");

    // ---------------------------------------------------------------- pindah ke katalog_sumber lewat Aturan Bisnis
    await page.goto(`${BASE}/config?tab=rules&group=kebijakan`);
    await rulesRow(MODE).first().waitFor();
    await rulesRow(MODE).locator(T("config-rule-select")).click();
    R.check("setelah nol selisih: 'katalog_sumber' bisa dipilih", (await page.locator(T("config-enum-option-katalog_sumber")).getAttribute("data-disabled")) === null);
    await page.click(T("config-enum-option-katalog_sumber"));
    await rulesRow(MODE).locator(T("config-rule-save")).click();
    await page.fill(T("config-rule-reason"), "uji peramban W2-C katalog jadi sumber");
    await page.click(T("config-rule-reason-submit"));
    R.check("toast sukses memilih katalog_sumber", !!(await waitToast(page, /diperbarui/)));
    R.check("backend: mode = katalog_sumber", (await eff(MODE)) === "katalog_sumber");
    await clearToasts(page);

    await page.goto(`${BASE}/config?tab=price`);
    await page.waitForSelector(T("w2c-master-banner"));
    R.check("banner berubah: 'Katalog adalah SUMBER'", (await page.locator(T("w2c-master-banner")).getAttribute("data-mode")) === "katalog_sumber"
      && /SUMBER master komponen biaya/.test(await page.locator(T("w2c-master-banner")).innerText()));
    await shot(page, "w2c-4-katalog-sumber");
    await page.goto(`${BASE}/config?tab=allin`);
    await page.waitForSelector(T("w2c-rules-note"));
    R.check("tab Biaya All-in menjelaskan: definisi dimiliki katalog", (await page.locator(T("w2c-rules-note")).getAttribute("data-mode")) === "katalog_sumber"
      && /Katalog adalah sumber/.test(await page.locator(T("w2c-rules-note")).innerText()));
    const allin = await api(OWNER, "GET", "/cost-components?include_inactive=true");
    const comp = allin.body.data.find((c) => c.code === "NOTARY_FEE");
    const rej = await api(OWNER, "PUT", `/cost-components/${comp.id}`, { amount: comp.amount + 1 });
    R.check("(API) mengubah komponen di Biaya All-in ditolak 400 menunjuk katalog", rej.status === 400 && /KATALOG/.test(JSON.stringify(rej.body)), JSON.stringify(rej.body).slice(0, 120));
    await shot(page, "w2c-5-allin-catatan");

    // edit lewat katalog (dialog): berlaku tembus ke aturan
    await page.goto(`${BASE}/config?tab=price`);
    await page.waitForSelector(T("w2c-diff-summary"));
    await page.locator(T("config-price-row")).filter({ hasText: "NOTARY_FEE" }).locator(T("config-price-edit")).click();
    await page.waitForSelector(T("w2c-cost-form"));
    await page.fill(T("w2c-cost-amount"), "8000000");
    await page.click(T("config-price-submit"));
    R.check("toast: komponen biaya diperbarui", !!(await waitToast(page, /diperbarui/)));
    const after = (await api(OWNER, "GET", "/cost-components?include_inactive=true")).body.data.find((c) => c.code === "NOTARY_FEE");
    R.check("tulis tembus: master All-in ikut 8.000.000 dan selisih tetap nol", after.amount === 8000000 && (await diff()).summary.nol === true, `amount=${after.amount}`);
    await clearToasts(page);

    // ---------------------------------------------------------------- kunci lain di Aturan Bisnis
    await page.goto(`${BASE}/config?tab=rules&group=kebijakan`);
    await rulesRow(MAXK).first().waitFor();
    R.check("kunci batas nominal tampil dengan bawaan 10 miliar", /10\.?000\.?000\.?000/.test(await rulesRow(MAXK).innerText()) || /10000000000/.test(await rulesRow(MAXK).innerText()));
    await rulesRow(MAXK).locator(T("config-rule-input")).fill("12000000000");
    await rulesRow(MAXK).locator(T("config-rule-save")).click();
    await page.fill(T("config-rule-reason"), "uji peramban W2-C naikkan batas");
    await page.click(T("config-rule-reason-submit"));
    R.check("batas nominal diubah lewat UI", !!(await waitToast(page, /diperbarui/)) && (await eff(MAXK)) === 12000000000);
    await clearToasts(page);
    await rulesRow("contract.cost_model").first().waitFor();
    await rulesRow("contract.cost_model").locator(T("config-rule-select")).click();
    const opts = await page.locator("[data-testid^=config-enum-option-]").allInnerTexts();
    R.check("model biaya kontrak: tiga opsi, tidak ada yang nonaktif", opts.length === 3 && !opts.some((o) => /belum tersedia/.test(o)), JSON.stringify(opts));
    await page.keyboard.press("Escape");
    R.check("kunci persetujuan input bebas tampil (bawaan aktif)", (await rulesRow("contract.cost_free_input_needs_approval").count()) === 1
      && await rulesRow("contract.cost_free_input_needs_approval").locator(T("config-rule-switch")).getAttribute("aria-checked") === "true");
    await shot(page, "w2c-6-aturan-bisnis");
  } finally {
    for (const k of [MODE, MAXK, "contract.cost_model", "contract.cost_free_input_needs_approval"]) await reset(k);
    if (notary) { // kembalikan nominal notaris (lewat katalog lalu aturan)
      await api(OWNER, "PUT", `/catalog/price-components/${notary.id}`, { cost: { amount: notary.cost.amount } });
      const c = (await api(OWNER, "GET", "/cost-components?include_inactive=true")).body.data.find((x) => x.code === "NOTARY_FEE");
      if (c && c.amount !== notary.cost.amount) await api(OWNER, "PUT", `/cost-components/${c.id}`, { amount: notary.cost.amount });
      await api(OWNER, "POST", "/cost-master/sync", { reason: "kembalikan master setelah uji peramban W2-C" });
    }
    await browser.close();
  }
  R.finish(log);
})();
