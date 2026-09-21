/**
 * logisticsDeepLink.js — jembatan "buka pengiriman ini" / "buka pesanan ini" dari layar mana pun.
 * Pola sama dengan `caseDeepLink.js` (event global + nonce), tanpa dependensi.
 */
export const LOGISTICS_EVENT = "kn-open-logistics";
export const ORDER_EVENT = "kn-open-order";

/** Buka modul Logistik, opsional langsung pada satu pengiriman. */
export function openLogistics(target = {}) {
  const d = typeof target === "string" ? { deliveryId: target } : (target || {});
  window.dispatchEvent(new CustomEvent(LOGISTICS_EVENT, { detail: d }));
}

/** Buka Pesanan (SO) → detail pesanan terpilih (tab Perjalanan Pesanan tersedia di sana). */
export function openOrderJourney(orderId) {
  if (!orderId) return;
  window.dispatchEvent(new CustomEvent(ORDER_EVENT, { detail: { orderId } }));
}
