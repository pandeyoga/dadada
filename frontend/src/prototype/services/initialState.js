import { buildWorld } from "./fixtures/world";
import { buildBuyer } from "./fixtures/buyer";
import { buildSecurity, buildBills } from "./fixtures/resident";
import { buildCommunity } from "./fixtures/community";
import { buildCare, buildManager, buildNotifications } from "./fixtures/ops";
import { buildPartner } from "./fixtures/partner";

export function buildInitialState(now) {
  const world = buildWorld();
  const care = buildCare(now);
  return {
    version: 1,
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
