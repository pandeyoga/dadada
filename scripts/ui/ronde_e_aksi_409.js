// (e) Aksi yang kini bisa 400/409: setujui/tolak permintaan material, status izin, status komplain, batal PO
// `partially_received`, buka-blokir unit, setujui/tolak transfer kas. Tiap skenario menyiapkan keadaan BASI
// (layar sudah memuat, lalu pihak lain mengubah data lewat API) dan memeriksa: pesan server terbaca di toast,
// tombol yang tak berlaku tidak ditawarkan, dan layar menyegarkan diri sesudah galat.
//   node scripts/ui/ronde_e_aksi_409.js   (butuh data dari: python3 scripts/ui/seed_hc.py)
const fs = require("fs");
const { BASE, api, openAs, shot, waitToast, clearToasts, reporter, seedPath } = require("./lib");

const seed = JSON.parse(fs.readFileSync(seedPath, "utf8"));
const OWNER = "owner@sipro.co.id";
const FINLEAD = "finlead@sipro.co.id";
const T = (id) => `[data-testid=${id}]`;
const GENERIC = /^(Gagal\.?|Aksi gagal\.?|Terjadi kesalahan.*)$/i;

async function pickProject(page, testId, name) {
  await page.click(T(testId));
  await page.getByRole("option", { name: new RegExp(`^${name}( \\(|$)`) }).click();   // opsi berbentuk "Nama (KODE)"
  await page.waitForTimeout(700);
}

/** Jalankan satu skenario; galat tak terduga dicatat sebagai GAGAL tanpa menghentikan skenario lain. */
async function scenario(R, name, fn) {
  console.log(`\n# ${name}`);
  try { await fn(); } catch (e) { R.check(`${name}: skenario selesai tanpa pengecualian`, false, String(e.message || e).split("\n")[0]); }
}

(async () => {
  const R = reporter("(e) Aksi 400/409");
  const { browser, page, log } = await openAs(OWNER);
  try {
    // ---------------------------------------------------------------- 1. permintaan material
    await scenario(R, "permintaan material: setujui/tolak basi", async () => {
      await page.goto(`${BASE}/materials`);
      await page.waitForSelector(T("materials-project-select"));
      await pickProject(page, "materials-project-select", seed.project_name);
      await page.click(T("materials-tab-requisitions"));
      const rowOf = (purpose) => page.locator(T("requisition-row")).filter({ hasText: purpose });
      await rowOf("UIHC setuju basi").waitFor();
      await rowOf("UIHC tolak basi").waitFor();
      // pihak lain: satu disetujui, satu ditolak
      // A: pihak lain menyetujui A; layar kita masih mengira "diajukan"
      await api(OWNER, "POST", `/materials/requisitions/${seed.req_approve}/approve`);
      await rowOf("UIHC setuju basi").locator(T("requisition-approve-button")).click();
      const t1 = await waitToast(page, /.+/);
      R.check("setujui permintaan yang sudah disetujui: pesan server terbaca", !!t1 && !/^Permintaan disetujui/.test(t1) && !GENERIC.test(t1), t1 || "(tidak ada toast)");
      await page.waitForTimeout(900);
      R.check("daftar disegarkan: baris A tak lagi menawarkan Setujui/Tolak",
        await rowOf("UIHC setuju basi").locator(T("requisition-approve-button")).count() === 0);
      // B: sesudah daftar disegarkan, pihak lain menolak B; layar masih mengira "diajukan"
      await clearToasts(page);
      await api(OWNER, "POST", `/materials/requisitions/${seed.req_reject}/reject`, { note: "ditolak dari sisi lain" });
      await rowOf("UIHC tolak basi").locator(T("requisition-reject-button")).click();
      const t2 = await waitToast(page, /.+/);
      R.check("tolak permintaan yang sudah ditolak: pesan server terbaca", !!t2 && !/^Permintaan ditolak\.?$/.test(t2) && !GENERIC.test(t2), t2 || "(tidak ada toast)");
      await page.waitForTimeout(900);
      R.check("daftar disegarkan: baris B tak lagi menawarkan Setujui/Tolak",
        await rowOf("UIHC tolak basi").locator(`${T("requisition-approve-button")}, ${T("requisition-reject-button")}`).count() === 0);
      await shot(page, "hc-e-1-material");
    });

    // ---------------------------------------------------------------- 2. status izin
    await scenario(R, "status izin", async () => {
      await page.goto(`${BASE}/permits`);
      await page.waitForSelector(T("permits-page"));
      await pickProject(page, "permits-project-select", seed.project_name);
      await page.locator(T("permit-row")).filter({ hasText: seed.permit_name }).click();
      await page.waitForSelector(T("permit-detail"));
      // a) pilihan status yang tidak berlaku tidak ditawarkan (belum_mulai -> disetujui = tidak boleh)
      await page.click(T("permit-status-select"));
      const opts = await page.getByRole("option").allInnerTexts();
      await page.keyboard.press("Escape");
      R.check("opsi status hanya yang boleh dari status sekarang (tanpa 'Disetujui')", !opts.some((o) => /Disetujui/i.test(o)), JSON.stringify(opts));
      // b) basi: pihak lain memindahkan izin ke 'diajukan'; layar masih mengira 'belum mulai'
      await api(OWNER, "POST", `/permits/${seed.permit}/status`, { status: "submitted" });
      await page.click(T("permit-status-select"));
      await page.getByRole("option", { name: /Diajukan/ }).first().click();
      await page.click(T("permit-status-submit"));
      const t = await waitToast(page, /.+/);
      R.check("status izin basi: pesan server terbaca", !!t && !/^Status →/.test(t) && !GENERIC.test(t), t || "(tidak ada toast)");
      await shot(page, "hc-e-2-izin");
    });

    // ---------------------------------------------------------------- 3. status komplain
    await scenario(R, "status komplain", async () => {
      await page.goto(`${BASE}/complaints`);
      await page.waitForSelector(T("complaints-page"));
      await page.locator(T("complaint-row")).filter({ hasText: seed.complaint_subject }).first().click();
      await page.waitForSelector(T("complaint-detail"));
      await page.getByRole("button", { name: /Tandai Dikerjakan/ }).waitFor();
      await api(OWNER, "PUT", `/complaints/${seed.complaint}/status`, { status: "resolved" });
      await page.getByRole("button", { name: /Tandai Dikerjakan/ }).click();
      const t = await waitToast(page, /.+/);
      R.check("status komplain basi: pesan server terbaca", !!t && !GENERIC.test(t), t || "(tidak ada toast)");
      await page.waitForTimeout(900);
      R.check("sheet disegarkan: komplain tampil selesai (tanpa formulir balasan)", await page.locator(T("complaint-respond-input")).count() === 0);
      R.check("komplain selesai: tidak ada tombol 'Buka Kembali' yang pasti ditolak server", await page.getByRole("button", { name: /Buka Kembali/ }).count() === 0);
      await shot(page, "hc-e-3-komplain");
    });

    // ---------------------------------------------------------------- 4. batal PO partially_received
    await scenario(R, "batal PO diterima sebagian", async () => {
      await page.goto(`${BASE}/procurement?tab=po`);
      await page.waitForSelector(T("po-project-select"));
      await pickProject(page, "po-project-select", seed.project_name);
      await page.locator(T("po-row")).filter({ hasText: seed.po_number }).click();
      await page.waitForSelector(T("grn-receive-button"));
      const cancel = page.locator(T("po-cancel-button"));
      const offered = await cancel.count();
      R.check("PO diterima sebagian: tombol Batalkan tidak ditawarkan", offered === 0, offered ? "tombol ada — server pasti menolak (400)" : "");
      R.check("PO diterima sebagian: catatan 'retur dulu' tampil", /Retur/i.test(await page.locator(T("po-cancel-note")).innerText().catch(() => "")));
      if (offered) {
        await cancel.click();
        const t = await waitToast(page, /.+/);
        R.check("penolakan batal PO terbaca (sebut retur)", !!t && /retur/i.test(t), t || "");
      }
      await shot(page, "hc-e-4-po");
    });

    // ---------------------------------------------------------------- 5. unit: buka-blokir basi + blokir tak berlaku
    await scenario(R, "unit buka-blokir", async () => {
      await page.goto(`${BASE}/units/${seed.unit_block.unit_id}`);
      await page.waitForSelector(T("unit-block-open"));
      R.check("unit diblokir: tombol 'Buka blokir'", /Buka blokir/.test(await page.locator(T("unit-block-open")).innerText()));
      await api(OWNER, "POST", `/masterplan/units/${seed.unit_block.unit_id}/block`, { blocked: false, reason: "dibuka dari sisi lain" });
      await page.click(T("unit-block-open"));
      await page.fill(T("unit-block-reason"), "Buka blokir uji peramban basi");
      await page.click(T("unit-block-submit"));
      const t = await waitToast(page, /.+/);
      R.check("buka-blokir basi: pesan server terbaca", !!t && !GENERIC.test(t), t || "(tidak ada toast)");
      await page.waitForTimeout(900);
      R.check("halaman disegarkan: tombol kini 'Blokir unit'", /Blokir unit/.test(await page.locator(T("unit-block-open")).innerText()));
      R.check("dialog tertutup setelah galat+penyegaran", await page.locator(T("unit-block-reason")).count() === 0);
      await shot(page, "hc-e-5-unit");
      // unit yang sudah dipesan/booked tidak boleh ditawari blokir
      const booked = (await api(OWNER, "GET", `/units?project_id=${seed.project_id}&limit=200`)).body.data.find((x) => x.code === seed.void_ok.unit_code);
      await page.goto(`${BASE}/units/${booked.id}`);
      await page.waitForSelector(T("unit-page")).catch(() => page.waitForSelector(T("unit-detail-page")));
      await page.waitForTimeout(600);
      const btn = page.locator(T("unit-block-open"));
      R.check("unit terjual/dipesan: tombol 'Blokir unit' tidak ditawarkan", (await btn.count()) === 0 || await btn.isDisabled(),
        ((await btn.count()) && await btn.isEnabled()) ? "tombol aktif — server menolak 400" : "");
    });

    // ---------------------------------------------------------------- 6. transfer kas
    await scenario(R, "transfer kas: setujui/tolak basi", async () => {
      const f = await openAs(FINLEAD);
      try {
        const p = f.page;
        await p.goto(`${BASE}/cash-bank?tab=transfers`);
        await p.waitForSelector(T("cashbank-transfer-table"));
        const a = seed.transfer_approve.id, r = seed.transfer_reject.id;
        await p.waitForSelector(T(`cashbank-transfer-approve-${a}`));
        await api(FINLEAD, "POST", `/cash-bank/transfers/${a}/approve`);
        await p.click(T(`cashbank-transfer-approve-${a}`));
        const t1 = await waitToast(p, /.+/);
        R.check("setujui transfer yang sudah diposting: pesan server terbaca", !!t1 && !GENERIC.test(t1), t1 || "(tidak ada toast)");
        await p.waitForTimeout(900);
        R.check("daftar disegarkan: transfer A tak lagi menawarkan Setujui", await p.locator(T(`cashbank-transfer-approve-${a}`)).count() === 0);
        await clearToasts(p);
        await api(FINLEAD, "POST", `/cash-bank/transfers/${r}/reject`, { reason: "ditolak dari sisi lain" });
        p.once("dialog", (d) => d.accept("alasan penolakan uji peramban"));
        await p.click(T(`cashbank-transfer-reject-${r}`));
        const t2 = await waitToast(p, /.+/);
        R.check("tolak transfer yang sudah ditolak: pesan server terbaca", !!t2 && !GENERIC.test(t2), t2 || "(tidak ada toast)");
        await p.waitForTimeout(900);
        R.check("daftar disegarkan: transfer B tak lagi menawarkan Tolak", await p.locator(T(`cashbank-transfer-reject-${r}`)).count() === 0);
        await shot(p, "hc-e-6-transfer");
        log.console.push(...f.log.console);
      } finally { await f.browser.close(); }
    });
  } finally { await browser.close(); }
  R.finish(log);
})().catch((e) => { console.error(e); process.exit(2); });
