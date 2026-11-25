import { __initStoreForTest, getState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { startPayment, confirmPayment } from "@/prototype/services/api/payments";
import {
  getBuyerHome, listInstallments, getProgress, getPlotMap, getKpr, getCancellation,
  listDocuments, getReferral, inviteFriend, askQuestion, listQuestions,
} from "@/prototype/services/api/buyer";

const dp3 = { targetType: "installment", targetId: "dp-3", amount: 1000000, title: "Uang muka 3 dari 5" };

beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => Date.parse("2026-11-25T03:00:00Z") });
  setLatency(0);
});
afterAll(() => setLatency(null));

test("beranda: perjalanan Bangun 72 %, tagihan berikutnya dp-3, foto terbaru, promo", async () => {
  const h = await getBuyerHome();
  expect(h.journey).toMatchObject({ current: 2, progress: 72 });
  expect(h.journey.steps[2]).toBe("Bangun");
  expect(h.nextInstallment).toMatchObject({ id: "dp-3", amount: 1000000, dueDate: "2026-12-10" });
  expect(h.latestPhoto.stage).toBe("Pintu, jendela, dan listrik");
  expect(h.promos.length).toBeGreaterThan(0);
  expect(h.progress.percent).toBe(72);
});

test("bayar dp-3: status paid dan nextInstallment pindah ke dp-4", async () => {
  const p = await startPayment(dp3, "va_bri");
  await confirmPayment(p.id);
  expect(getState().buyer.installments.find((i) => i.id === "dp-3").status).toBe("paid");
  expect((await getBuyerHome()).nextInstallment.id).toBe("dp-4");
  const list = await listInstallments();
  expect(list.find((i) => i.id === "dp-3").status).toBe("paid");
});

test("bayar ulang dp-3 yang sudah lunas melempar error", async () => {
  const p = await startPayment(dp3, "va_bri");
  await confirmPayment(p.id);
  await expect(startPayment(dp3, "qris")).rejects.toThrow("Tagihan ini sudah lunas");
});

test("progres: foto per tahap dan estimasi serah terima", async () => {
  const p = await getProgress();
  expect(p.photos).toHaveLength(6);
  expect(p.percent).toBe(72);
  expect(p.handoverEstimate).toMatch(/\d{4}/);
});

test("peta kavling: >= 20 kavling, C-12 milik-anda, status sah", async () => {
  const m = await getPlotMap();
  expect(m.plots.length).toBeGreaterThanOrEqual(20);
  expect(m.plots.find((x) => x.id === "C-12").status).toBe("milik-anda");
  expect(m.plots.filter((x) => x.status === "milik-anda")).toHaveLength(1);
  m.plots.forEach((x) => expect(["tersedia", "dipesan", "terjual", "milik-anda"]).toContain(x.status));
});

test("KPR: angsuran 1.062.500, 20 tahun, menunggu rumah siap", async () => {
  const k = await getKpr();
  expect(k.monthly).toBe(1062500);
  expect(k).toMatchObject({ tenorYears: 20, status: "menunggu rumah siap", product: "KPR Subsidi · Bank BTN" });
});

test("pembatalan selalu none dengan penjelasan aturan", async () => {
  const c = await getCancellation();
  expect(c.status).toBe("none");
  expect(c.rules.length).toBeGreaterThan(0);
});

test("dokumen memuat kuitansi dari bills.receipts setelah bayar", async () => {
  const before = (await listDocuments()).receipts.length;
  const p = await startPayment(dp3, "qris");
  await confirmPayment(p.id);
  expect((await listDocuments()).receipts.length).toBe(before + 1);
});

test("referral: inviteFriend menambah rujukan; nomor kosong ditolak", async () => {
  const r = await inviteFriend({ name: "Dewi", phone: "0812 9999 0000" });
  expect(r.invited).toHaveLength(1);
  expect((await getReferral()).invited[0]).toMatchObject({ name: "Dewi", status: "diundang" });
  await expect(inviteFriend({ name: "X", phone: "" })).rejects.toThrow();
  await expect(inviteFriend({ name: "X", phone: "123" })).rejects.toThrow();
});

test("askQuestion menambah tiket kind tanya", async () => {
  const n = (await listQuestions()).length;
  await askQuestion({ category: "Administrasi", description: "Kapan akad?" });
  const q = await listQuestions();
  expect(q).toHaveLength(n + 1);
  expect(q[0]).toMatchObject({ kind: "tanya", status: "dibuat" });
  await expect(askQuestion({ category: "x", description: " " })).rejects.toThrow();
});
