"""Iter 46 — Special Order FASE 2:
Customer decision (acc/revisi/tolak) + evidence, pricing lock/unlock + role guards,
exclusivity (POST /api/sales-orders), proofing verification.
"""
import io
import os
import uuid

import pytest
import requests

def _read_backend_url():
    env = os.environ.get("REACT_APP_BACKEND_URL")
    if env:
        return env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return ""


BASE = _read_backend_url().rstrip("/")
ENTITY = "ent_ksc"


def _login(email, pwd="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(email):
    return {"Authorization": f"Bearer {_login(email)}", "X-Entity-Id": ENTITY}


@pytest.fixture(scope="module")
def admin_h():
    return _h("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def manager_h():
    return _h("manager@kainnusantara.id")


@pytest.fixture(scope="module")
def sales_h():
    return _h("sales@kainnusantara.id")


def _tiny_png():
    return bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
    )


def _get_od(oid, headers):
    r = requests.get(f"{BASE}/api/special-orders/{oid}", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ─── (A) VERIFIKASI OD sord_3cea851d93c6 (sudah confirmed & locked) ─────────
class TestExistingConfirmedOD:
    OID = "sord_3cea851d93c6"

    def test_confirmed_and_locked(self, admin_h):
        od = _get_od(self.OID, admin_h)
        assert od["status"] == "confirmed"
        chain = od.get("chain") or {}
        assert chain.get("phase") == "confirmed", chain
        pricing = chain.get("pricing") or od.get("pricing") or {}
        assert pricing.get("locked") is True
        # Cost/final may drift if OD was unlocked/relocked previously — assert margin+relation.
        assert float(pricing.get("margin_pct")) == 35.0
        assert float(pricing.get("final_unit_price")) == round(
            float(pricing.get("cost_price")) * 1.35, 2)
        # 2 customer_decisions
        decs = od.get("customer_decisions") or []
        assert len(decs) == 2, decs
        kinds = [d.get("decision") for d in decs]
        assert kinds.count("revisi") >= 1 and kinds.count("acc") >= 1

    def test_customer_decision_blocked_when_locked(self, admin_h):
        r = requests.post(f"{BASE}/api/special-orders/{self.OID}/customer-decision",
                          headers=admin_h, json={"decision": "acc"}, timeout=30)
        assert r.status_code == 400, r.text
        assert "dikunci" in r.text.lower() or "locked" in r.text.lower()

    def test_manager_cannot_unlock(self, manager_h):
        r = requests.post(f"{BASE}/api/special-orders/{self.OID}/unlock-price",
                          headers=manager_h, json={"reason": "coba"}, timeout=30)
        assert r.status_code == 403, r.text

    def test_admin_unlock_then_relock(self, admin_h):
        r = requests.post(f"{BASE}/api/special-orders/{self.OID}/unlock-price",
                          headers=admin_h, json={"reason": "retest iter46"}, timeout=30)
        assert r.status_code == 200, r.text
        od = _get_od(self.OID, admin_h)
        chain = od.get("chain") or {}
        assert chain.get("phase") == "pricing", chain
        assert (od.get("pricing") or {}).get("locked") is False

        # Re-lock at same margin used originally (cost may have drifted from other flows;
        # only assert lock succeeded and phase confirmed).
        r2 = requests.post(f"{BASE}/api/special-orders/{self.OID}/lock-price",
                           headers=admin_h, json={"margin_pct": 35}, timeout=30)
        assert r2.status_code == 200, r2.text
        p = r2.json()["pricing"]
        assert p["locked"] is True
        # final = cost * 1.35
        assert float(p["final_unit_price"]) == round(float(p["cost_price"]) * 1.35, 2)
        od2 = _get_od(self.OID, admin_h)
        assert (od2.get("chain") or {}).get("phase") == "confirmed"


# ─── (B) EKSKLUSIVITAS SKU pada POST /api/sales-orders ──────────────────────
class TestExclusivity:
    PRODUCT_ID = "prod_9497b822a098"

    def _payload(self, customer_id):
        return {"customer_id": customer_id, "shipping_address_id": "",
                "items": [{"product_id": self.PRODUCT_ID, "quantity": 10, "unit": "meter"}],
                "entity_id": ENTITY, "allow_backorder": True}

    def test_wrong_customer_400(self, admin_h):
        r = requests.post(f"{BASE}/api/sales-orders",
                          headers=admin_h, json=self._payload("cust_toko_kain"), timeout=30)
        assert r.status_code == 400, r.text
        assert "EKSKLUSIF" in r.text or "eksklusif" in r.text.lower()

    def test_right_customer_ok(self, admin_h):
        r = requests.post(f"{BASE}/api/sales-orders",
                          headers=admin_h, json=self._payload("cust_textile_medan"), timeout=30)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body.get("id") or body.get("number"), body


# ─── (C) FULL FLOW pada sord_607ea61709a4 (labdip smp_1213cb9c0c99) ─────────
class TestFullSamplingFlow:
    OID = "sord_607ea61709a4"
    SAMPLE_ID = "smp_1213cb9c0c99"

    def _run_sample_round(self, sample_id, admin_h, manager_h,
                          price=40000, color_name="Biru K", color_code="KB-1", note="r1"):
        """send → attach → submit → assess acc → decide (using non-creator). Returns round id."""
        # Fetch sample: pick decider != creator
        rget = requests.get(f"{BASE}/api/rnd/samples/{sample_id}", headers=admin_h, timeout=30)
        assert rget.status_code == 200, rget.text
        cur = rget.json()
        creator = (cur.get("created_by") or "").lower()
        # Dewi Rahayu = manager · Budi Santoso = admin
        decider_h = admin_h if "dewi" in creator else manager_h

        if cur.get("status") in ("draft", "sent", "in_progress", "assessed"):
            # Skip send if already in progress
            if cur.get("status") == "draft":
                r = requests.post(f"{BASE}/api/rnd/samples/{sample_id}/send", headers=admin_h,
                                  json={"supplier_ids": ["sup_grp_ksc_kanda"],
                                        "type_codes": ["labdip"]}, timeout=30)
                assert r.status_code == 200, r.text
                cur = r.json()

            # Find an open labdip round
            rounds = [r for r in (cur.get("rounds") or [])
                      if r.get("type_code") == "labdip"
                      and r.get("status") not in ("assessed", "decided")]
            if rounds:
                rid = rounds[0]["id"]
                st = rounds[0].get("status")
                if st in ("open", "pending", "sent"):
                    files = {"file": (f"round_{rid}.png", _tiny_png(), "image/png")}
                    ra = requests.post(
                        f"{BASE}/api/rnd/samples/{sample_id}/rounds/{rid}/attachments",
                        headers=admin_h, files=files, timeout=30)
                    assert ra.status_code == 200, ra.text
                    rs = requests.post(
                        f"{BASE}/api/rnd/samples/{sample_id}/rounds/{rid}/submit",
                        headers=admin_h,
                        json={"note": note, "measurements": {
                            "delta_e": 0.8, "colorfastness_wash": 4,
                            "colorfastness_rub": 4}}, timeout=30)
                    assert rs.status_code == 200, rs.text
                if st != "assessed":
                    rasess = requests.post(
                        f"{BASE}/api/rnd/samples/{sample_id}/rounds/{rid}/assess",
                        headers=admin_h,
                        json={"result": "acc", "score": 90, "note": "ok"}, timeout=30)
                    assert rasess.status_code == 200, rasess.text

        # Decide (non-creator)
        rdec = requests.post(f"{BASE}/api/rnd/samples/{sample_id}/decide",
                             headers=decider_h,
                             json={"supplier_id": "sup_grp_ksc_kanda",
                                   "reason_code": "warna_paling_dekat",
                                   "price": price,
                                   "supplier_color_name": color_name,
                                   "supplier_color_code": color_code},
                             timeout=30)
        assert rdec.status_code == 200, rdec.text
        return rdec.json()

    def test_full_flow(self, admin_h, manager_h, sales_h):
        # Guard: skip if already progressed past sampling (test is destructive)
        od = _get_od(self.OID, admin_h)
        if (od.get("chain") or {}).get("phase") in ("confirmed",):
            pytest.skip(f"OD {self.OID} already confirmed; cannot re-run destructive flow.")

        # Skip if sample is already decided
        rs = requests.get(f"{BASE}/api/rnd/samples/{self.SAMPLE_ID}", headers=admin_h, timeout=30)
        assert rs.status_code == 200, rs.text
        smp = rs.json()

        if smp.get("status") != "decided":
            self._run_sample_round(self.SAMPLE_ID, admin_h, manager_h,
                                   price=40000, color_name="Biru K", color_code="KB-1")

        od = _get_od(self.OID, admin_h)
        chain = od.get("chain") or {}
        assert chain.get("review", {}).get("ready") is True, chain
        # Cost_price should be 40000, final 52000 default margin 30
        pv = requests.get(f"{BASE}/api/special-orders/{self.OID}/pricing",
                          headers=admin_h, timeout=30).json()
        assert float(pv["cost_price"]) == 40000.0, pv
        assert float(pv["final_unit_price"]) == 52000.0, pv

        # Lock BEFORE customer ACC → 400
        rl = requests.post(f"{BASE}/api/special-orders/{self.OID}/lock-price",
                           headers=admin_h, json={"margin_pct": 30}, timeout=30)
        assert rl.status_code == 400, rl.text

        # Revisi without note → 400
        rn = requests.post(f"{BASE}/api/special-orders/{self.OID}/customer-decision",
                           headers=admin_h, json={"decision": "revisi"}, timeout=30)
        assert rn.status_code == 400, rn.text

        # Revisi with note → 200; new sample spawned
        prev_sample_count = len(od.get("sample_ids") or [])
        rr = requests.post(f"{BASE}/api/special-orders/{self.OID}/customer-decision",
                           headers=admin_h,
                           json={"decision": "revisi", "note": "terlalu gelap"}, timeout=30)
        assert rr.status_code == 200, rr.text
        dec_entry = rr.json()["decision"]
        assert dec_entry.get("revision_sample_number"), dec_entry
        new_sample_id = dec_entry["revision_sample_id"]

        od2 = _get_od(self.OID, admin_h)
        assert len(od2.get("sample_ids") or []) == prev_sample_count + 1
        chain2 = od2.get("chain") or {}
        assert chain2.get("phase") == "sampling", chain2
        assert chain2.get("review", {}).get("ready") is False

        # Run round on the new revision sample → decide again
        self._run_sample_round(new_sample_id, admin_h, manager_h,
                               price=40000, color_name="Biru K2", color_code="KB-2")

        od3 = _get_od(self.OID, admin_h)
        assert (od3.get("chain") or {}).get("review", {}).get("ready") is True

        # ACC pelanggan
        ra = requests.post(f"{BASE}/api/special-orders/{self.OID}/customer-decision",
                           headers=admin_h,
                           json={"decision": "acc", "note": "ok", "contact_name": "Ibu Rina"},
                           timeout=30)
        assert ra.status_code == 200, ra.text
        acc_entry = ra.json()["decision"]
        acc_id = acc_entry["id"]

        od4 = _get_od(self.OID, admin_h)
        assert (od4.get("chain") or {}).get("phase") == "pricing"

        # Upload evidence
        files = {"file": ("acc.png", _tiny_png(), "image/png")}
        rev = requests.post(f"{BASE}/api/special-orders/{self.OID}/customer-decision/evidence",
                            headers=admin_h, files=files, data={"decision_id": acc_id}, timeout=30)
        assert rev.status_code == 200, rev.text
        ev_id = rev.json()["evidence"]["id"]

        # Fetch evidence back
        rget = requests.get(
            f"{BASE}/api/special-orders/{self.OID}/customer-decision/evidence/{ev_id}",
            headers=admin_h, timeout=30)
        assert rget.status_code == 200, rget.text
        assert rget.headers.get("content-type", "").startswith("image/")

        # Preview pricing at margin 40
        pv2 = requests.get(f"{BASE}/api/special-orders/{self.OID}/pricing?margin_pct=40",
                           headers=admin_h, timeout=30).json()
        assert float(pv2["final_unit_price"]) == round(pv2["cost_price"] * 1.4, 2), pv2

        # Lock (sales role allowed)
        rl2 = requests.post(f"{BASE}/api/special-orders/{self.OID}/lock-price",
                            headers=sales_h, json={"margin_pct": 40}, timeout=30)
        assert rl2.status_code == 200, rl2.text
        p = rl2.json()["pricing"]
        assert p["locked"] is True
        expected_final = round(p["cost_price"] * 1.4, 2)
        assert float(p["final_unit_price"]) == expected_final
        od5 = _get_od(self.OID, admin_h)
        assert (od5.get("chain") or {}).get("phase") == "confirmed"
        qty = float((od5.get("custom_item") or {}).get("quantity") or 0)
        assert float(od5.get("total_amount")) == round(expected_final * qty, 2)


# ─── (D) REJECT flow pada sord_0224809cca99 ─────────────────────────────────
class TestRejectFlow:
    OID = "sord_0224809cca99"
    SAMPLE_ID = "smp_d016417c74c6"

    def test_reject_cancels_od(self, admin_h, manager_h):
        od = _get_od(self.OID, admin_h)
        if od.get("status") == "cancelled":
            pytest.skip("OD already cancelled")

        # Run sample flow if not decided yet
        rs = requests.get(f"{BASE}/api/rnd/samples/{self.SAMPLE_ID}", headers=admin_h, timeout=30)
        smp = rs.json()
        if smp.get("status") != "decided":
            TestFullSamplingFlow._run_sample_round(
                TestFullSamplingFlow(), self.SAMPLE_ID, admin_h, manager_h,
                price=38000, color_name="Merah", color_code="MR-1")

        r = requests.post(f"{BASE}/api/special-orders/{self.OID}/customer-decision",
                          headers=admin_h, json={"decision": "tolak", "note": "batal"}, timeout=30)
        assert r.status_code == 200, r.text
        od2 = _get_od(self.OID, admin_h)
        assert od2["status"] == "cancelled", od2["status"]


# ─── (E) Proofing otomatis verify (sord_8ebb294be059) ───────────────────────
class TestProofingAuto:
    OID = "sord_8ebb294be059"

    def test_has_proofing_sample(self, admin_h):
        od = _get_od(self.OID, admin_h)
        sample_ids = od.get("sample_ids") or []
        assert sample_ids, od
        # Find at least one proofing sample
        found_proofing = False
        for sid in sample_ids:
            r = requests.get(f"{BASE}/api/rnd/samples/{sid}", headers=admin_h, timeout=30)
            if r.status_code != 200:
                continue
            s = r.json()
            if "proofing" in (s.get("sample_types") or []):
                found_proofing = True
                # Should be KSC/SMP-00047 per spec
                assert s.get("number", "").startswith("KSC/SMP-"), s
                break
        assert found_proofing, "No proofing sample tied to OD"
        assert (od.get("chain") or {}).get("phase") == "sampling"
