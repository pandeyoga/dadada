import { buildWorld } from "./fixtures/world";
import { buildBuyer } from "./fixtures/buyer";
import { buildSecurity, buildBills } from "./fixtures/resident";
import { buildCommunity } from "./fixtures/community";
import { buildCare, buildManager, buildNotifications } from "./fixtures/ops";
import { buildPartner } from "./fixtures/partner";

// Naikkan setiap kali bentuk state/fixture berubah: state tersimpan dengan versi lain dibuang
// dan diganti fixture baru (lihat store.parse).
// v3: notifikasi ber-audience (pembeli/warga) dan session.demoClock.
export const STATE_VERSION = 3;

/** `demoClock`: 'anchored' (tanggal demo 25 Nov 2026, jam sungguhan) atau 'real' (lihat clock.js). */
export function buildInitialState(now, { demoClock = "anchored" } = {}) {
  const world = buildWorld();
  const care = buildCare(now);
  return {
    version: STATE_VERSION,
    session: { persona: "buyer", loggedIn: false, phone: "", demoClock },
    mode: "buyer",
    onboarding: { done: false },
    location: "inside",
    world,
    buyer: buildBuyer(now),
    security: buildSecurity(now),
    bills: buildBills(now),
    community: buildCommunity(now),
    care,
    manager: buildManager(now, world),
    partner: buildPartner(now),
    notifications: buildNotifications(now),
  };
}
