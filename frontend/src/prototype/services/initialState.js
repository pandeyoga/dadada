import { buildWorld } from "./fixtures/world";
import { buildBuyer } from "./fixtures/buyer";
import { buildSecurity, buildBills } from "./fixtures/resident";
import { buildCommunity } from "./fixtures/community";
import { buildCare, buildManager, buildNotifications } from "./fixtures/ops";
import { buildPartner } from "./fixtures/partner";

// Naikkan setiap kali bentuk state/fixture berubah: state tersimpan dengan versi lain dibuang
// dan diganti fixture baru (lihat store.parse).
export const STATE_VERSION = 2;

export function buildInitialState(now) {
  const world = buildWorld();
  const care = buildCare(now);
  return {
    version: STATE_VERSION,
    session: { persona: "buyer", loggedIn: false, phone: "" },
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
