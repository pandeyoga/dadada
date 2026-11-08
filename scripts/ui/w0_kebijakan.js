// Uji peramban W0 — Pusat Konfigurasi › Aturan Bisnis: kebijakan terkonfigurasi (docs/audit/12).
//   node scripts/ui/w0_kebijakan.js
// Memeriksa: kunci percontohan `deposit.on_cancelled_deal` tampil di kelompok Kebijakan; ubah (sensitif → alasan wajib) & kembalikan
// bawaan; pemilih tingkat PROYEK (hanya aturan yang mendeklarasikan level proyek yang ditawarkan, nilai org tak ikut berubah);
// opsi "belum tersedia" tampil nonaktif (respons /settings dipalsukan di peramban karena belum ada kunci nyata dengan opsi demikian).
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter } = require("./lib");

const OWNER = "owner@sipro.co.id";
const KEY = "deposit.on_cancelled_deal";
const T = (id) => `[data-testid=${id}]`;
const NAME = `UI W0 ${Date.now().toString(36)}`;

const eff = async (project) => (await api(OWNER, "GET", `/settings/effective?keys=${KEY}${project ? `&project_id=${project}` : ""}`)).body.data[KEY];
const reset = async (scope, id) => api(OWNER, "POST", `/settings/${KEY}/reset?scope=${scope}${id ? `&scope_id=${id}` : ""}`);

(async () => {
  const R = reporter("Kebijakan terkonfigurasi (UI)");
  const proj = (await api(OWNER, "POST", "/projects", { name: NAME, location: "uji" })).body.data;
  await reset("org");
  const { browser, page, log } = await openAs(OWNER);
  const row = () => page.locator(T("config-rules-row")).filter({ hasText: KEY });
  try {
    await page.goto(`${BASE}/config?tab=rules&group=kebijakan`);
    await page.waitForSelector(T("config-rules-panel"));
    await row().first().waitFor();
    R.check("kunci percontohan tampil di kelompok Kebijakan", await row().count() === 1);
    R.check("nilai bawaan 'bebas' tampil", /bebas/i.test(await row().innerText()));
    await shot(page, "w0-1-kelompok-kebijakan");

    // --- ubah di tingkat organisasi: sensitif => alasan wajib
    await row().locator(T("config-rule-select")).click();
    const opts = await page.locator("[data-testid^=config-enum-option-]").allInnerTexts();
    R.check("tiga opsi tersedia (tidak ada yang nonaktif)", opts.length === 3, JSON.stringify(opts));
    await page.click(T("config-enum-option-tolak"));
    await row().locator(T("config-rule-save")).click();
    await page.waitForSelector(T("config-rule-reason"));
    R.check("alasan wajib: tombol simpan nonaktif saat kosong", await page.locator(T("config-rule-reason-submit")).isDisabled());
    await page.fill(T("config-rule-reason"), "uji peramban W0 tolak titipan deal batal");
    await page.click(T("config-rule-reason-submit"));
    R.check("toast sukses", !!(await waitToast(page, /diperbarui/)));
    R.check("backend: organisasi = tolak", (await eff()) === "tolak");
    await clearToasts(page);
    await shot(page, "w0-2-org-tolak");

    // --- tingkat proyek: hanya aturan ber-level proyek, tidak mengubah organisasi
    await page.goto(`${BASE}/config?tab=rules`);
    await page.waitForSelector(T("config-rules-panel"));
    await page.locator(T("config-rules-project")).click();
    await page.getByRole("option", { name: `Khusus proyek: ${NAME}` }).click();
    await row().first().waitFor();
    const n = await page.locator(T("config-rules-row")).count();
    // jumlah aturan ber-level proyek bertambah tiap gelombang kebijakan (W1: reservasi kedaluwarsa, pemicu pembeli) — bandingkan dgn API
    const expected = ((await api(OWNER, "GET", "/settings")).body.data || []).filter((r) => (r.levels || []).includes("project")).length;
    R.check("tampilan proyek hanya memuat aturan ber-level proyek", n >= 1 && n === expected, `baris=${n} diharapkan=${expected}`);
    R.check("aturan lama (reservation.hold_days) tidak ditawarkan di tampilan proyek",
      await page.locator(T("config-rules-row")).filter({ hasText: "reservation.hold_days" }).count() === 0);
    R.check("di proyek: nilai mewarisi organisasi, tombol 'ikuti organisasi' nonaktif",
      /Diubah organisasi/.test(await row().innerText()) && await row().locator(T("config-rule-reset")).isDisabled());
    await row().locator(T("config-rule-select")).click();
    await page.click(T("config-enum-option-bebas"));
    await row().locator(T("config-rule-save")).click();
    await page.fill(T("config-rule-reason"), "uji peramban W0 proyek ini boleh bebas");
    await page.click(T("config-rule-reason-submit"));
    R.check("toast menyebut proyek", !!(await waitToast(page, /untuk proyek ini/)));
    R.check("backend: proyek = bebas, organisasi tetap tolak", (await eff(proj.id)) === "bebas" && (await eff()) === "tolak");
    await page.waitForTimeout(600);
    R.check("asal nilai: Khusus proyek", /Khusus proyek/.test(await row().innerText()));
    await shot(page, "w0-3-proyek-bebas");
    await clearToasts(page);
    await row().locator(T("config-rule-reset")).click();
    R.check("toast kembali mengikuti organisasi", !!(await waitToast(page, /mengikuti pengaturan organisasi/)));
    R.check("backend: proyek kembali mewarisi organisasi", (await eff(proj.id)) === "tolak");

    // --- opsi belum tersedia: respons dipalsukan di peramban
    await page.route("**/api/settings?**", async (route) => {
      const r = await route.fetch();
      const j = await r.json();
      j.data = (j.data || []).map((x) => (x.key === KEY ? { ...x, unavailable: { tolak: "belum dibangun" } } : x));
      await route.fulfill({ response: r, json: j });
    });
    await page.goto(`${BASE}/config?tab=rules&group=kebijakan`);
    await row().first().waitFor();
    await row().locator(T("config-rule-select")).click();
    const tolak = page.locator(T("config-enum-option-tolak"));
    R.check("opsi belum tersedia ditandai", /belum tersedia/.test(await tolak.innerText()));
    R.check("opsi belum tersedia nonaktif (tidak bisa dipilih)", (await tolak.getAttribute("data-disabled")) !== null);
    R.check("opsi lain tetap bisa dipilih", (await page.locator(T("config-enum-option-bebas")).getAttribute("data-disabled")) === null);
    await shot(page, "w0-4-opsi-belum-tersedia");
  } finally {
    await reset("org"); await reset("project", proj.id);
    await browser.close();
  }
  R.finish(log);
})();
