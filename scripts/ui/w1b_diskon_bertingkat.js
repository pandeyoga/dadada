// Uji peramban W1-B (#8) — Pusat Konfigurasi › Aturan Bisnis: editor tabel tingkat persetujuan diskon (docs/audit/12).
//   node scripts/ui/w1b_diskon_bertingkat.js
// Memeriksa: baris `discount.approval_tiers` memakai editor khusus (bukan "disunting lewat tab khusus"); ringkasan bawaan;
// tambah/hapus tingkat; validasi sisi klien (tumpang tindih, peran menurun) menonaktifkan "Terapkan"; simpan (sensitif → alasan wajib)
// → nilai di backend; penimpaan tingkat PROYEK tidak mengubah organisasi; mode 'bertingkat' tampil sebagai opsi enum.
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const OWNER = "owner@sipro.co.id";
const KEY = "discount.approval_tiers";
const MODE = "discount.approval_mode";
const T = (id) => `[data-testid=${id}]`;
const NAME = `UI W1B ${Date.now().toString(36)}`;

const eff = async (project) => (await api(OWNER, "GET", `/settings/effective?keys=${KEY}${project ? `&project_id=${project}` : ""}`)).body.data[KEY];
const reset = async (scope, id) => api(OWNER, "POST", `/settings/${KEY}/reset?scope=${scope}${id ? `&scope_id=${id}` : ""}`);

(async () => {
  const R = reporter("Persetujuan diskon bertingkat (UI)");
  const proj = (await api(OWNER, "POST", "/projects", { name: NAME, location: "uji" })).body.data;
  await reset("org");
  const { browser, page, log } = await openAs(OWNER);
  const row = (k = KEY) => page.locator(T("config-rules-row")).filter({ hasText: k });
  try {
    await page.goto(`${BASE}/config?tab=rules&group=kebijakan`);
    await page.waitForSelector(T("config-rules-panel"));
    await row().first().waitFor();
    R.check("baris tabel tingkat tampil di kelompok Kebijakan", await row().count() === 1);
    R.check("memakai editor khusus (bukan teks 'tab khusus')", await row().locator(T("approval-tiers-editor")).count() === 1);
    R.check("ringkasan bawaan = satu tingkat Manajer Penjualan", /semua nilai Manajer Penjualan/.test(await row().locator(T("approval-tiers-summary")).innerText()));
    R.check("mode persetujuan tampil sebagai enum dengan dua opsi", await row(MODE).locator(T("config-rule-select")).count() === 1);
    await shot(page, "w1b-1-baris-tingkat");

    // --- buka editor: satu tingkat tak terbatas
    await row().locator(T("approval-tiers-open")).click();
    await page.waitForSelector(T("approval-tier-row"));
    R.check("satu baris; hapus dinonaktifkan", await page.locator(T("approval-tier-row")).count() === 1
      && await page.locator(T("approval-tier-remove")).first().isDisabled());
    R.check("baris terakhir 'sampai tak terbatas'", /tak terbatas/.test(await page.locator(T("approval-tier-max")).first().innerText()));

    // --- tambah tingkat, isi: ≤ 10 jt Manajer Penjualan, selebihnya Owner
    await page.click(T("approval-tier-add"));
    R.check("dua baris setelah tambah", await page.locator(T("approval-tier-row")).count() === 2);
    const max1 = page.locator(T("approval-tier-max")).first();
    await max1.fill("10000000");
    R.check("masker rupiah memformat angka", (await max1.inputValue()).includes("10.000.000"));
    await page.locator(T("approval-tier-role")).nth(1).click();
    await page.click(T("approval-tier-role-owner"));
    R.check("sah: tidak ada galat & 'Terapkan' aktif", await page.locator(T("approval-tier-errors")).count() === 0
      && !(await page.locator(T("approval-tier-apply")).isDisabled()));
    await shot(page, "w1b-2-editor-sah");

    // --- validasi klien: tumpang tindih (batas 2 ≤ batas 1) dan peran menurun
    await page.click(T("approval-tier-add"));                      // sisip tingkat di antara; bawaannya 2× batas sebelumnya
    const maxes = page.locator(T("approval-tier-max"));
    await maxes.nth(1).fill("5000000");                             // lebih kecil dari batas tingkat 1 → tumpang tindih
    R.check("tumpang tindih → galat & 'Terapkan' nonaktif", /tumpang tindih/.test(await page.locator(T("approval-tier-errors")).innerText())
      && await page.locator(T("approval-tier-apply")).isDisabled());
    await maxes.nth(1).fill("25000000");
    await page.locator(T("approval-tier-role")).nth(1).click();    // tingkat 2 = Manajer Penjualan, tingkat 3 = Owner → sah
    await page.click(T("approval-tier-role-sales_manager"));
    await page.locator(T("approval-tier-role")).first().click();   // tingkat 1 = Owner > tingkat 2 → peran menurun
    await page.click(T("approval-tier-role-owner"));
    R.check("peran menurun → galat & nonaktif", /lebih rendah/.test(await page.locator(T("approval-tier-errors")).innerText())
      && await page.locator(T("approval-tier-apply")).isDisabled());
    await shot(page, "w1b-3-editor-galat");
    await page.locator(T("approval-tier-role")).first().click();
    await page.click(T("approval-tier-role-sales_manager"));
    await page.locator(T("approval-tier-role")).nth(1).click();
    await page.click(T("approval-tier-role-finance_manager"));
    R.check("diperbaiki → sah lagi", await page.locator(T("approval-tier-errors")).count() === 0);
    // hapus tingkat tengah → kembali dua tingkat
    await page.locator(T("approval-tier-remove")).nth(1).click();
    R.check("hapus tingkat → dua baris", await page.locator(T("approval-tier-row")).count() === 2);
    await page.click(T("approval-tier-apply"));
    R.check("ringkasan memuat batas & peran", /≤ Rp 10\.000\.000 Manajer Penjualan · di atas itu Owner/.test(await row().locator(T("approval-tiers-summary")).innerText()));

    // --- simpan (sensitif → alasan wajib)
    await row().locator(T("config-rule-save")).click();
    await page.waitForSelector(T("config-rule-reason"));
    R.check("alasan wajib: tombol simpan nonaktif saat kosong", await page.locator(T("config-rule-reason-submit")).isDisabled());
    await page.fill(T("config-rule-reason"), "uji peramban W1-B tingkat persetujuan diskon");
    await page.click(T("config-rule-reason-submit"));
    R.check("toast sukses", !!(await waitToast(page, /diperbarui/)));
    const v = await eff();
    R.check("backend: tabel tersimpan ternormalisasi", JSON.stringify(v) === JSON.stringify([{ max_amount: 10000000, role: "sales_manager" }, { max_amount: null, role: "owner" }]), JSON.stringify(v));
    await clearToasts(page);
    await shot(page, "w1b-4-tersimpan");

    // --- tingkat proyek: ubah peran terakhir → Manajer Keuangan hanya untuk proyek ini
    await page.goto(`${BASE}/config?tab=rules`);
    await page.waitForSelector(T("config-rules-panel"));
    await page.locator(T("config-rules-project")).click();
    await page.getByRole("option", { name: `Khusus proyek: ${NAME}` }).click();
    await row().first().waitFor();
    R.check("tabel tingkat ditawarkan di tampilan proyek (level proyek)", await row().count() === 1);
    await row().locator(T("approval-tiers-open")).click();
    await page.waitForSelector(T("approval-tier-row"));
    await page.locator(T("approval-tier-role")).nth(1).click();
    await page.click(T("approval-tier-role-finance_manager"));
    await page.click(T("approval-tier-apply"));
    await row().locator(T("config-rule-save")).click();
    await page.fill(T("config-rule-reason"), "uji peramban W1-B penimpaan proyek");
    await page.click(T("config-rule-reason-submit"));
    R.check("toast menyebut proyek", !!(await waitToast(page, /untuk proyek ini/)));
    const vp = await eff(proj.id);
    R.check("backend: proyek = finance_manager, organisasi tetap owner",
      vp[1].role === "finance_manager" && (await eff())[1].role === "owner", JSON.stringify(vp));
    await shot(page, "w1b-5-proyek");
  } finally {
    await reset("org"); await reset("project", proj.id);
    await browser.close();
  }
  R.finish(log);
})();
