import { __initStoreForTest, getState, setState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { PAY_METHODS, methodLabel, startPayment, confirmPayment } from "@/prototype/services/api/payments";

const dp3 = { targetType: "installment", targetId: "dp-3", amount: 1000000, title: "Uang muka 3 dari 5" };

beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => Date.parse("2026-11-25T03:00:00Z") });
  setLatency(0);
});
afterAll(() => setLatency(null));

test.each([
  ["va_bri", "8800"], ["va_bni", "8277"], ["va_mandiri", "8908"], ["va_btn", "9001"], ["va_permata", "8528"],
])("%s: kode VA = awalan %s + 12 digit", async (method, prefix) => {
  const p = await startPayment(dp3, method);
  expect(p.code).toMatch(new RegExp(`^${prefix}\\d{12}$`));
  expect(p).toMatchObject({ targetType: "installment", targetId: "dp-3", method, amount: 1000000, status: "pending" });
  expect(Date.parse(p.expiresAt)).toBe(Date.parse("2026-11-26T03:00:00Z"));
});

test("startPayment menyimpan pembayaran dan menandai tagihan menunggu", async () => {
  const p = await startPayment(dp3, "qris");
  expect(getState().bills.payments).toEqual([p]);
  expect(getState().buyer.installments.find((i) => i.id === "dp-3").status).toBe("pending");
});

test("wa_link: kode berupa teks tautan wa.me berisi judul dan nominal", async () => {
  const p = await startPayment(dp3, "wa_link");
  expect(p.code).toMatch(/^https:\/\/wa\.me\/\?text=/);
  const text = decodeURIComponent(p.code.split("text=")[1]);
  expect(text).toContain("Uang muka 3 dari 5");
  expect(text).toContain("Rp1.000.000");
});

test("confirmPayment: tagihan lunas, kuitansi di bills.receipts, idempoten", async () => {
  const before = getState().bills.receipts.length;
  const p = await startPayment(dp3, "va_bri");
  const [a, b] = await Promise.all([confirmPayment(p.id), confirmPayment(p.id)]);
  expect(a.receipt.id).toBe(b.receipt.id);
  expect(a.receipt).toMatchObject({ targetType: "installment", targetId: "dp-3", title: "Uang muka 3 dari 5", amount: 1000000, method: "va_bri" });
  expect(a.payment.status).toBe("paid");

  const again = await confirmPayment(p.id);
  expect(again.receipt.id).toBe(a.receipt.id);

  const s = getState();
  expect(s.bills.receipts.length).toBe(before + 1);
  expect(s.bills.receipts.filter((r) => r.id === a.receipt.id)).toHaveLength(1);
  const dp = s.buyer.installments.find((i) => i.id === "dp-3");
  expect(dp).toMatchObject({ status: "paid", receiptId: a.receipt.id, paidAt: a.receipt.paidAt });
});

test("startPayment pada tagihan lunas melempar 'Tagihan ini sudah lunas'", async () => {
  await expect(startPayment({ ...dp3, targetId: "dp-1" }, "va_bri")).rejects.toThrow("Tagihan ini sudah lunas");
  const p = await startPayment(dp3, "va_bri");
  await confirmPayment(p.id);
  await expect(startPayment(dp3, "qris")).rejects.toThrow("Tagihan ini sudah lunas");
});

test("pembayaran lain untuk tagihan yang sudah lunas tidak membuat kuitansi kedua", async () => {
  const p1 = await startPayment(dp3, "va_bri");
  const p2 = await startPayment(dp3, "qris");
  await confirmPayment(p2.id);
  const n = getState().bills.receipts.length;
  await expect(confirmPayment(p1.id)).rejects.toThrow("Tagihan ini sudah lunas");
  expect(getState().bills.receipts.length).toBe(n);
});

test("bill → bills.ipl; ppob → bills.ppobTx; market → community.orders", async () => {
  setState((s) => ({
    ...s,
    bills: { ...s.bills, ppobTx: [{ id: "tx-1", status: "unpaid", amount: 52500 }] },
    community: { ...s.community, orders: [{ id: "or-1", status: "unpaid", amount: 30000 }] },
  }));
  const cases = [
    [{ targetType: "bill", targetId: "ipl-2026-12", amount: 150000, title: "IPL Desember 2026" }, (s) => s.bills.ipl],
    [{ targetType: "ppob", targetId: "tx-1", amount: 52500, title: "Token PLN 50rb" }, (s) => s.bills.ppobTx],
    [{ targetType: "market", targetId: "or-1", amount: 30000, title: "Pesanan pasar warga" }, (s) => s.community.orders],
  ];
  for (const [t, list] of cases) {
    const p = await startPayment(t, "ewallet");
    const { receipt } = await confirmPayment(p.id);
    const item = list(getState()).find((x) => x.id === t.targetId);
    expect(item).toMatchObject({ status: "paid", receiptId: receipt.id });
    expect(getState().bills.receipts[0]).toEqual(receipt);
  }
});

test("target atau metode tidak dikenal ditolak", async () => {
  await expect(startPayment({ ...dp3, targetId: "dp-99" }, "va_bri")).rejects.toThrow("Tagihan tidak ditemukan");
  await expect(startPayment(dp3, "tunai")).rejects.toThrow("Metode bayar tidak dikenal");
  await expect(confirmPayment("pay-x")).rejects.toThrow("Pembayaran tidak ditemukan");
});

test("PAY_METHODS memuat 8 metode dengan label tampilan", () => {
  expect(PAY_METHODS.map((m) => m.id)).toEqual(["va_bri", "va_bni", "va_mandiri", "va_btn", "va_permata", "qris", "ewallet", "wa_link"]);
  expect(methodLabel("va_bri")).toBe("VA BRI");
  expect(methodLabel("qris")).toBe("QRIS");
});
