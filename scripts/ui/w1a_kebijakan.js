// Uji peramban W1-A — Pusat Konfigurasi › Aturan Bisnis: keputusan #7 (pemicu pembeli) dan #13 (reservasi kedaluwarsa, booking fee terbayar).
//   node scripts/ui/w1a_kebijakan.js
// Memeriksa: tiga kunci #13 tampil di kelompok Kebijakan dengan bawaan jawaban pemilik dan tiga opsi aktif; ubah enum & angka (sensitif →
// alasan wajib; nilai di luar batas ditolak server dengan pesan terbaca) lalu kembalikan; `lead.won_trigger` kini bisa ditimpa per PROYEK
// (muncul di tampilan proyek, nilai organisasi tak ikut berubah) dan bawaannya "Booking fee terverifikasi".
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const OWNER = "owner@sipro.co.id";
const MODE = "reservation.expiry.paid_booking_fee";
const DAYS = "reservation.expiry.extend_days";
const MAXX = "reservation.expiry.max_extensions";
const WON = "lead.won_trigger";
const T = (id) => `[data-testid=${id}]`;
const NAME = `UI W1A ${Date.now().toString(36)}`;

const eff = async (key, project) => (await api(OWNER, "GET", `/settings/effective?keys=${key}${project ? `&project_id=${project}` : ""}`)).body.data[key];
const reset = async (key, scope, id) => api(OWNER, "POST", `/settings/${key}/reset?scope=${scope}${id ? `&scope_id=${id}` : ""}`);

(async () => {
  const R = reporter("Kebijakan W1-A: pemicu pembeli & reservasi kedaluwarsa (UI)");
  const proj = (await api(OWNER, "POST", "/projects", { name: NAME, location: "uji" })).body.data;
  for (const k of [MODE, DAYS, MAXX, WON]) await reset(k, "org");
  const { browser, page, log } = await openAs(OWNER);
  const row = (key) => page.locator(T("config-rules-row")).filter({ hasText: key });
  const saveWithReason = async (key, reason) => {
    await row(key).locator(T("config-rule-save")).click();
    await page.waitForSelector(T("config-rule-reason"));
    await page.fill(T("config-rule-reason"), reason);
    await page.click(T("config-rule-reason-submit"));
  };
  try {
    // --- #13: tiga kunci di kelompok Kebijakan
    await page.goto(`${BASE}/config?tab=rules&group=kebijakan`);
    await page.waitForSelector(T("config-rules-panel"));
    await row(MODE).first().waitFor();
    for (const k of [MODE, DAYS, MAXX]) R.check(`kunci ${k} tampil di kelompok Kebijakan`, (await row(k).count()) === 1);
    R.check("bawaan pemilik: perpanjang (7 hari, maks. 2 kali)",
      /perpanjang/i.test(await row(MODE).innerText())
      && (await row(DAYS).locator(T("config-rule-input")).inputValue()) === "7"
      && (await row(MAXX).locator(T("config-rule-input")).inputValue()) === "2");
    await shot(page, "w1a-1-kebijakan-reservasi");

    await row(MODE).locator(T("config-rule-select")).click();
    const opts = await page.locator("[data-testid^=config-enum-option-]").all();
    const disabled = [];
    for (const o of opts) if ((await o.getAttribute("data-disabled")) !== null) disabled.push(await o.innerText());
    R.check("tiga opsi tersedia, tidak ada yang nonaktif", opts.length === 3 && disabled.length === 0, JSON.stringify(disabled));
    await page.click(T("config-enum-option-antrean_refund"));
    await saveWithReason(MODE, "uji peramban W1A booking fee antre refund");
    R.check("toast sukses simpan enum", !!(await waitToast(page, /diperbarui/)));
    R.check("backend: organisasi = antrean_refund", (await eff(MODE)) === "antrean_refund");
    await clearToasts(page);

    // --- angka: di luar batas ditolak server dengan pesan terbaca; nilai sah diterima
    await row(DAYS).locator(T("config-rule-input")).fill("0");
    await saveWithReason(DAYS, "uji peramban W1A lama perpanjangan nol");
    R.check("nilai di luar batas ditolak (toast galat terbaca)", !!(await waitToast(page, /minimum 1/i)));
    R.check("backend: extend_days tetap bawaan 7", (await eff(DAYS)) === 7);
    R.check("dialog alasan tetap terbuka setelah galat (nilai tidak hilang diam-diam)", await page.locator(T("config-rule-reason")).isVisible());
    await page.keyboard.press("Escape");           // batal: tutup dialog alasan
    await page.waitForSelector(T("config-rule-reason"), { state: "detached" });
    await clearToasts(page);
    await row(DAYS).locator(T("config-rule-input")).fill("3");
    await saveWithReason(DAYS, "uji peramban W1A perpanjang 3 hari");
    R.check("toast sukses simpan angka", !!(await waitToast(page, /diperbarui/)));
    R.check("backend: extend_days = 3", (await eff(DAYS)) === 3);
    await clearToasts(page);
    await shot(page, "w1a-2-diubah-org");

    // --- kembali ke bawaan
    for (const k of [MODE, DAYS]) {
      await row(k).locator(T("config-rule-reset")).click();
      await waitToast(page, /dikembalikan ke bawaan/);
      await clearToasts(page);
    }
    R.check("backend: kembali ke bawaan (perpanjang, 7)", (await eff(MODE)) === "perpanjang" && (await eff(DAYS)) === 7);

    // --- #7: lead.won_trigger bawaan baru + penimpaan per proyek
    await page.goto(`${BASE}/config?tab=rules&group=lead`);
    await page.waitForSelector(T("config-rules-panel"));
    await row(WON).first().waitFor();
    R.check("bawaan pemicu pembeli: Booking fee terverifikasi", /Booking fee terverifikasi/i.test(await row(WON).innerText()));
    await shot(page, "w1a-3-pemicu-pembeli-org");

    await page.goto(`${BASE}/config?tab=rules`);
    await page.waitForSelector(T("config-rules-panel"));
    await page.locator(T("config-rules-project")).click();
    await page.getByRole("option", { name: `Khusus proyek: ${NAME}` }).click();
    await row(WON).first().waitFor();
    R.check("tampilan proyek menawarkan lead.won_trigger (kini ber-level proyek)", (await row(WON).count()) === 1);
    R.check("tampilan proyek juga menawarkan kunci #13", (await row(MODE).count()) === 1);
    R.check("di proyek: mewarisi organisasi, 'ikuti organisasi' nonaktif",
      /Diubah organisasi|Bawaan/i.test(await row(WON).innerText()) && await row(WON).locator(T("config-rule-reset")).isDisabled());
    await row(WON).locator(T("config-rule-select")).click();
    const wopts = await page.locator("[data-testid^=config-enum-option-]").allInnerTexts();
    R.check("empat opsi pemicu tersedia (SPR, PPJB, AJB, booking)", wopts.length === 4, JSON.stringify(wopts));
    await page.click(T("config-enum-option-ppjb_signed"));
    await saveWithReason(WON, "uji peramban W1A proyek ini menunggu PPJB");
    R.check("toast menyebut proyek", !!(await waitToast(page, /untuk proyek ini/)));
    R.check("backend: proyek = ppjb_signed, organisasi tetap booking_fee_verified",
      (await eff(WON, proj.id)) === "ppjb_signed" && (await eff(WON)) === "booking_fee_verified");
    await shot(page, "w1a-4-pemicu-proyek-ppjb");
    await clearToasts(page);
    await page.waitForTimeout(600);
    await row(WON).locator(T("config-rule-reset")).click();
    R.check("toast kembali mengikuti organisasi", !!(await waitToast(page, /mengikuti pengaturan organisasi/)));
    R.check("backend: proyek kembali mewarisi organisasi", (await eff(WON, proj.id)) === "booking_fee_verified");
  } finally {
    for (const k of [MODE, DAYS, MAXX, WON]) { await reset(k, "org"); await reset(k, "project", proj.id); }
    await browser.close();
  }
  R.finish(log);
})();
