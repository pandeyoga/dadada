// Uji peramban W2-A — Master Pajak & PPN terkonfigurasi (docs/audit/12 keputusan #15 dan #1).
//   node scripts/ui/w2a_master_pajak.js
// Memeriksa: kelompok "Master Pajak & PPN" di Pusat Konfigurasi › Aturan Bisnis (owner; 7 kunci, bawaan = perilaku lama); pemilih proyek →
// penimpaan mode PPN/NPOPTKP/tarif tercatat (alasan wajib) tanpa mengubah organisasi; Keuangan › Konfigurasi › Pajak (lapisan kompatibilitas
// + pemilih proyek) untuk Manajer Keuangan, hanya-baca bagi staf Keuangan; Pusat Konfigurasi tetap tertutup bagi Manajer Keuangan;
// tab Biaya All-in menunjuk Master Pajak (tarif BPHTB tidak lagi diketik di komponen).
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const OWNER = "owner@sipro.co.id";
const FINLEAD = "finlead@sipro.co.id";
const STAF = "finance@sipro.co.id";
const T = (id) => `[data-testid=${id}]`;
const NAME = `UI W2A ${Date.now().toString(36)}`;
const K = {
  mode: "tax.ppn.mode", rate: "tax.ppn.rate", npoptkp: "tax.master.npoptkp", bphtb: "tax.master.bphtb_rate",
  pph: "tax.master.pph_final_rate", njop: "tax.master.njop_per_m2", bank: "tax.master.bank_fee_pct_of_plafon",
};

const eff = async (pid) => (await api(OWNER, "GET", `/finance/config/tax${pid ? `?project_id=${pid}` : ""}`)).body.data;
const reset = async (key, pid) => api(OWNER, "POST", `/settings/${key}/reset?scope=${pid ? "project" : "org"}${pid ? `&scope_id=${pid}` : ""}`);

(async () => {
  const R = reporter("Master Pajak & PPN (UI)");
  const proj = (await api(OWNER, "POST", "/projects", { name: NAME, location: "uji" })).body.data;
  for (const k of Object.values(K)) await reset(k);
  const logs = [];
  try {
    // ======================================================= Pemilik: kelompok, proyek, penimpaan
    {
      const { browser, page, log } = await openAs(OWNER); logs.push(log);
      const row = (key) => page.locator(T("config-rules-row")).filter({ hasText: key });
      await page.goto(`${BASE}/config?tab=rules&group=master_pajak`);
      await page.waitForSelector(T("config-rules-panel"));
      await row(K.mode).first().waitFor();
      R.check("kelompok Master Pajak & PPN memuat 7 kunci", await page.locator(T("config-rules-row")).count() === 7);
      R.check("label kelompok tampil", /Master Pajak & PPN/.test(await row(K.mode).innerText()));
      R.check("bawaan mode PPN = Eksklusif (perilaku lama)", /Eksklusif/.test(await row(K.mode).innerText()));
      R.check("bawaan tarif PPN 12% & NPOPTKP 80.000.000 tampil",
        /12%/.test(await row(K.rate).innerText()) && /80\.000\.000/.test(await row(K.npoptkp).innerText()));
      await shot(page, "w2a-1-master-pajak-org");

      await page.locator(T("config-rules-project")).click();
      await page.getByRole("option", { name: `Khusus proyek: ${NAME}` }).click();
      await row(K.mode).first().waitFor();
      R.check("tampilan proyek: ketujuh kunci pajak ditawarkan (level proyek)", await page.locator(T("config-rules-row")).count() === 7);

      // --- mode PPN: tiga opsi, semua tersedia
      await row(K.mode).locator(T("config-rule-select")).click();
      const opts = page.locator("[data-testid^=config-enum-option-]");
      R.check("tiga mode PPN tersedia, tidak ada yang nonaktif",
        await opts.count() === 3 && (await opts.evaluateAll((els) => els.filter((e) => e.getAttribute("data-disabled") !== null).length)) === 0);
      await page.click(T("config-enum-option-inklusif"));
      await row(K.mode).locator(T("config-rule-save")).click();
      await page.waitForSelector(T("config-rule-reason"));
      R.check("alasan wajib (tombol simpan nonaktif saat kosong)", await page.locator(T("config-rule-reason-submit")).isDisabled());
      await page.fill(T("config-rule-reason"), "harga jual proyek ini sudah termasuk PPN");
      await page.click(T("config-rule-reason-submit"));
      R.check("toast menyebut proyek", !!(await waitToast(page, /untuk proyek ini/)));
      const e1 = await eff(proj.id), eo = await eff();
      R.check("backend: proyek = inklusif, organisasi tetap eksklusif", e1.ppn_mode === "inklusif" && eo.ppn_mode === "eksklusif",
        JSON.stringify([e1.ppn_mode, eo.ppn_mode]));
      R.check("asal nilai proyek tercatat", e1.origins.ppn_mode === "project");
      await clearToasts(page);

      // --- NPOPTKP dan tarif BPHTB per proyek
      await row(K.npoptkp).locator(T("config-rule-input")).fill("60000000");
      await row(K.npoptkp).locator(T("config-rule-save")).click();
      await page.fill(T("config-rule-reason"), "NPOPTKP Perda kabupaten Rp 60 juta");
      await page.click(T("config-rule-reason-submit"));
      R.check("toast NPOPTKP proyek", !!(await waitToast(page, /untuk proyek ini/)));
      await clearToasts(page);
      await row(K.bphtb).locator(T("config-rule-input")).fill("2.5");
      await row(K.bphtb).locator(T("config-rule-save")).click();
      await page.fill(T("config-rule-reason"), "tarif BPHTB daerah 2,5%");
      await page.click(T("config-rule-reason-submit"));
      R.check("toast tarif BPHTB proyek", !!(await waitToast(page, /untuk proyek ini/)));
      const e2 = await eff(proj.id);
      R.check("backend: NPOPTKP 60 jt & BPHTB 2,5% di proyek; organisasi tak berubah",
        e2.npoptkp === 60000000 && e2.bphtb_rate === 2.5 && (await eff()).npoptkp === 80000000 && (await eff()).bphtb_rate === 5);
      await page.waitForTimeout(600);
      R.check("asal nilai: Khusus proyek", /Khusus proyek/.test(await row(K.npoptkp).innerText()));
      await shot(page, "w2a-2-proyek-ditimpa");

      // --- riwayat memuat alasan
      await row(K.npoptkp).locator(T("config-rule-history")).click();
      let hist = false;
      try { await page.getByText(/Alasan: NPOPTKP Perda kabupaten/).first().waitFor({ timeout: 8000 }); hist = true; } catch { /* gagal */ }
      R.check("riwayat memuat alasan penimpaan", hist);
      await page.keyboard.press("Escape");

      // --- kembali mengikuti organisasi
      await clearToasts(page);
      await row(K.mode).locator(T("config-rule-reset")).click();
      R.check("toast kembali mengikuti organisasi", !!(await waitToast(page, /mengikuti pengaturan organisasi/)));
      R.check("backend: mode proyek kembali eksklusif", (await eff(proj.id)).ppn_mode === "eksklusif");
      await browser.close();
    }

    // ======================================================= Biaya All-in: tarif BPHTB tidak diketik di komponen
    {
      const { browser, page, log } = await openAs(OWNER); logs.push(log);
      await page.goto(`${BASE}/config?tab=allin`);
      await page.waitForSelector(T("cost-component-tax-note"));
      R.check("catatan tab Biaya All-in menunjuk Master Pajak", /Master Pajak/.test(await page.locator(T("cost-component-tax-note")).innerText()));
      const bphtb = page.locator("[data-testid=p75-component-row][data-code=BPHTB], tr[data-code=BPHTB]").first();
      R.check("baris BPHTB: tarif ikut Master Pajak", /tarif ikut Master Pajak/.test(await bphtb.innerText()));
      await page.click(T("cost-component-edit-BPHTB"));
      const locked = page.locator(T("cost-component-bphtb-master"));
      await locked.waitFor();
      R.check("dialog komponen BPHTB: persen terkunci (ikut Master Pajak)", await locked.isDisabled());
      await shot(page, "w2a-3-komponen-bphtb");
      await browser.close();
    }

    // ======================================================= Manajer Keuangan: Keuangan › Konfigurasi › Pajak (dengan pemilih proyek)
    {
      const { browser, page, log } = await openAs(FINLEAD); logs.push(log);
      await page.goto(`${BASE}/finance?tab=config`);
      await page.waitForSelector(T("finance-tax-section"));
      R.check("Manajer Keuangan: tombol Simpan Pajak aktif", await page.locator(T("finance-tax-submit")).isEnabled());
      R.check("bentuk lama (PPN 12%, BPHTB 5%, PPh 2,5%, NPOPTKP 80 jt) tampil sebagai nilai efektif organisasi",
        (await page.inputValue(T("tax-ppn"))) === "12" && (await page.inputValue(T("tax-bphtb"))) === "5"
        && (await page.inputValue(T("tax-pph"))) === "2.5" && /80\.000\.000/.test(await page.inputValue(T("tax-npoptkp"))));
      R.check("petunjuk mode PPN bawaan (eksklusif) tampil", /BELUM termasuk PPN/.test(await page.locator(T("tax-ppn-mode-hint")).innerText()));
      // pemilih proyek → nilai efektif proyek (mewarisi organisasi)
      await page.locator(T("tax-project")).click();
      await page.getByRole("option", { name: `Khusus proyek: ${NAME}` }).click();
      await page.waitForFunction(() => /Pajak Proyek/.test(document.querySelector("[data-testid=finance-tax-submit]")?.innerText || ""));
      // penimpaan proyek WAJIB alasan (diblok di layar)
      await page.fill(T("tax-pph"), "1");
      await page.click(T("finance-tax-submit"));
      R.check("penimpaan proyek tanpa alasan ditolak dengan pesan terbaca", !!(await waitToast(page, /wajib beralasan/)));
      R.check("backend: belum ada penimpaan (PPh proyek tetap 2,5%)", (await eff(proj.id)).pph_rate === 2.5);
      await clearToasts(page);
      await page.fill(T("tax-reason"), "proyek rumah sederhana: PPh final 1%");
      await page.locator(T("tax-ppn-mode")).click();
      await page.getByRole("option", { name: /Bebas PPN/ }).click();
      R.check("petunjuk mode berganti ke Bebas PPN", /tanpa catatan PPN/.test(await page.locator(T("tax-ppn-mode-hint")).innerText()));
      await page.click(T("finance-tax-submit"));
      R.check("toast proyek tersimpan", !!(await waitToast(page, /pajak proyek disimpan/)));
      const ep = await eff(proj.id);
      R.check("backend: PPh 1% & mode Bebas PPN di proyek; organisasi tetap 2,5% / eksklusif",
        ep.pph_rate === 1 && ep.ppn_mode === "bebas_ppn" && (await eff()).pph_rate === 2.5 && (await eff()).ppn_mode === "eksklusif");
      R.check("asal nilai proyek tampil di layar", /Khusus proyek/.test(await page.locator(T("finance-tax-section")).innerText()));
      await shot(page, "w2a-4-manajer-keuangan");
      await clearToasts(page);
      // tingkat organisasi lewat bentuk lama
      await page.locator(T("tax-project")).click();
      await page.getByRole("option", { name: "Seluruh organisasi" }).click();
      await page.waitForFunction(() => document.querySelector("[data-testid=tax-pph]")?.value === "2.5");
      await page.fill(T("tax-pph"), "3");
      await page.fill(T("tax-reason"), "uji peramban: PPh final organisasi 3%");
      await page.click(T("finance-tax-submit"));
      R.check("toast konfigurasi pajak organisasi tersimpan", !!(await waitToast(page, /Konfigurasi pajak disimpan/)));
      const eo = await eff();
      R.check("backend: master organisasi PPh 3% (lewat lapisan kompatibilitas)", eo.pph_rate === 3 && eo.origins.pph_final_rate === "org");
      // Pusat Konfigurasi hanya untuk owner/super admin (RequireAdmin) — Manajer Keuangan TIDAK diberi jalan masuk baru
      await page.goto(`${BASE}/config?tab=rules`);
      await page.waitForTimeout(1500);
      R.check("Pusat Konfigurasi tetap tertutup bagi Manajer Keuangan (tidak melonggarkan)", (await page.locator(T("config-rules-panel")).count()) === 0);
      await browser.close();
    }

    // ======================================================= Staf Keuangan: hanya-baca
    {
      const { browser, page, log } = await openAs(STAF); logs.push(log);
      await page.goto(`${BASE}/finance?tab=config`);
      await page.waitForSelector(T("finance-tax-section"));
      R.check("staf Keuangan: Simpan Pajak & kolom pajak nonaktif + keterangan izin",
        await page.locator(T("finance-tax-submit")).isDisabled() && await page.locator(T("tax-pph")).isDisabled()
        && /Hanya Manajer Keuangan atau owner/.test(await page.locator(T("finance-tax-section")).innerText()));
      await shot(page, "w2a-5-staf-keuangan");
      await browser.close();
    }
    const s403 = await api(STAF, "PUT", `/settings/${K.mode}`, { value: "bebas_ppn", reason: "uji", scope: "project", scope_id: proj.id });
    R.check("server menolak staf Keuangan (403) walau memanggil API langsung", s403.status === 403, String(s403.status));
  } finally {
    for (const k of Object.values(K)) { await reset(k); await reset(k, proj.id); }
  }
  R.finish(...logs);
})();
