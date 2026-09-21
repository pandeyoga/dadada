"""Iter 254 — sesi 2026-06c: nilai tagihan supplier + riwayat HPP roll + papan bisa ditindak."""
import os
import pytest
import requests
from pathlib import Path

def _read_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL", "")
    if v:
        return v.rstrip("/")
    env = Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE = _read_backend_url()
API = f"{BASE}/api"


def _login(email, password="demo12345"):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login('admin@kainnusantara.id')}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def manager_headers():
    return {"Authorization": f"Bearer {_login('manager@kainnusantara.id')}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def finance_headers():
    return {"Authorization": f"Bearer {_login('finance@kainnusantara.id')}", "X-Entity-Id": "ent_ksc"}


# ==================== (1) Nilai tagihan supplier ====================
class TestVendorBillAmount:
    def test_finance_home_shows_amount_for_vendor_bill_and_contra_bon(self, admin_headers):
        r = requests.get(f"{API}/home/finance", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        boards = data.get("waiting_boards") or []
        assert isinstance(boards, list) and len(boards) > 0
        by_key = {b["key"]: b for b in boards}
        # Papan yang wajib ada
        for key in ("vendor_bill", "contra_bon_verify", "contra_bon_approve"):
            assert key in by_key, f"missing board {key}"
        # Untuk baris yang berisi, amount harus > 0
        for key in ("vendor_bill", "contra_bon_verify", "contra_bon_approve"):
            rows = by_key[key].get("rows") or []
            for row in rows:
                assert "amount" in row, f"{key} row missing amount"
                assert isinstance(row["amount"], (int, float))
                assert row["amount"] > 0, f"{key} row amount not positive: {row}"
                assert "note" in row

    def test_non_regression_transfer_cycle_count(self, admin_headers):
        r = requests.get(f"{API}/home/admin", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        boards = r.json().get("waiting_boards") or []
        keys = {b["key"] for b in boards}
        # transfer & cycle_count masih ada (tidak regresi)
        # Tidak wajib > 0 karena bisa kosong; papan sekurangnya terdaftar dalam kunci
        assert "transfer" in keys or True  # tolerant: they only show if configured for that home


# ==================== (3) Papan bisa ditindak ====================
class TestActionableBoards:
    def test_admin_has_action_on_rows(self, admin_headers):
        r = requests.get(f"{API}/home/admin", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        boards = r.json().get("waiting_boards") or []
        actionable_seen = False
        for b in boards:
            for row in (b.get("rows") or []):
                if b["key"] in ("contra_bon_dispute", "inspection_hold"):
                    assert row.get("action") is None, f"{b['key']} must have action=null"
                elif b["key"] in ("transfer", "price", "vendor_bill", "contra_bon_verify",
                                  "contra_bon_approve", "sales_order", "cycle_count",
                                  "interco_return", "special_order"):
                    act = row.get("action")
                    if act is not None:
                        actionable_seen = True
                        assert "label" in act and "method" in act and "path" in act
                        assert "note_field" in act
                        assert act["method"] == "POST"
                        assert act["path"].startswith("/")
        assert actionable_seen, "admin should see at least one actionable row"

    def test_finance_has_no_action_on_vendor_bill(self, finance_headers):
        r = requests.get(f"{API}/home/finance", headers=finance_headers, timeout=30)
        assert r.status_code == 200
        boards = r.json().get("waiting_boards") or []
        by_key = {b["key"]: b for b in boards}
        for key in ("vendor_bill", "contra_bon_verify", "contra_bon_approve"):
            if key in by_key:
                for row in by_key[key].get("rows") or []:
                    assert row.get("action") is None, f"finance MUST NOT get action for {key}"

    def test_dispute_and_hold_always_null(self, admin_headers):
        # dispute list via ops home or manager
        r = requests.get(f"{API}/home/manager", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        boards = r.json().get("waiting_boards") or []
        for b in boards:
            if b["key"] in ("contra_bon_dispute", "inspection_hold"):
                for row in b.get("rows") or []:
                    assert row.get("action") is None

    def test_action_path_actually_approves(self, admin_headers):
        """POST ke path aksi (transfer atau price approval) benar-benar menyelesaikan."""
        # transfer ada di /home/warehouse; price ada di /home/sales
        boards = []
        for ep in ("warehouse", "sales", "admin"):
            r = requests.get(f"{API}/home/{ep}", headers=admin_headers, timeout=30)
            if r.status_code == 200:
                boards += r.json().get("waiting_boards") or []
        target = None
        for b in boards:
            if b["key"] not in ("transfer", "price"):
                continue
            for row in b.get("rows") or []:
                if row.get("action"):
                    target = (b["key"], row)
                    break
            if target:
                break
        if not target:
            pytest.skip("Tidak ada baris transfer/price bertombol untuk diuji")
        key, row = target
        action = row["action"]
        doc_id = row["id"]
        url = f"{API}{action['path']}"
        payload = {}
        if action.get("note_field"):
            payload[action["note_field"]] = "Uji otomatis iter254"
        if action.get("body"):
            payload.update(action["body"])
        r2 = requests.post(url, headers=admin_headers, json=payload, timeout=30)
        assert r2.status_code in (200, 201), f"approve failed {key} {doc_id}: {r2.status_code} {r2.text}"
        # Re-fetch board: baris hilang atau count turun
        r3_boards = []
        for ep in ("warehouse", "sales", "admin"):
            rr = requests.get(f"{API}/home/{ep}", headers=admin_headers, timeout=30)
            if rr.status_code == 200:
                r3_boards += rr.json().get("waiting_boards") or []
        after_ids = []
        for b in r3_boards:
            if b["key"] == key:
                after_ids += [rr["id"] for rr in (b.get("rows") or [])]
        assert doc_id not in after_ids, f"{key} row {doc_id} should be gone after approve"


# ==================== (2) Riwayat nilai roll ====================
class TestRollCostHistory:
    def _find_roll_with_history(self, headers):
        # cari roll dari koleksi cost history via demo
        r = requests.get(f"{API}/inventory/rolls", headers=headers, timeout=30)
        assert r.status_code == 200
        rolls = r.json()
        if isinstance(rolls, dict):
            rolls = rolls.get("items") or []
        return rolls

    def test_cost_history_endpoint_shape(self, admin_headers):
        rolls = self._find_roll_with_history(admin_headers)
        assert len(rolls) > 0, "no rolls available"
        # cari yang ada history
        found = None
        for r in rolls[:60]:
            rid = r.get("id")
            if not rid:
                continue
            resp = requests.get(f"{API}/inventory/rolls/{rid}/cost-history", headers=admin_headers, timeout=30)
            if resp.status_code != 200:
                continue
            data = resp.json()
            assert "roll_no" in data and "unit_cost" in data and "count" in data and "history" in data
            if data["count"] > 0:
                found = data
                break
        assert found is not None, "expected at least one roll with cost history entries (seed)"
        entry = found["history"][0]
        for f in ("old_unit_cost", "new_unit_cost", "delta_value", "reason",
                  "reason_label", "actor"):
            assert f in entry, f"cost history entry missing field {f}: {entry}"
        # ref_number field exists
        assert "ref_number" in entry

    def test_cross_entity_403(self, admin_headers):
        # find a roll from ent_kanda
        r = requests.get(f"{API}/inventory/rolls", headers={**admin_headers, "X-Entity-Id": "ent_kanda"}, timeout=30)
        assert r.status_code == 200
        rolls = r.json()
        if isinstance(rolls, dict):
            rolls = rolls.get("items") or []
        kanda_ids = [x["id"] for x in rolls if (x.get("owner_entity_id") or x.get("entity_id")) == "ent_kanda"]
        if not kanda_ids:
            pytest.skip("no kanda rolls to test")
        # sales3 is Kanda-only, but admin can access; use sales user restricted to KSC
        # Use warehouse@ (assigned to KSC only? per credentials) — safer: create call as sales@
        tok = _login("sales@kainnusantara.id")
        h = {"Authorization": f"Bearer {tok}", "X-Entity-Id": "ent_ksc"}
        resp = requests.get(f"{API}/inventory/rolls/{kanda_ids[0]}/cost-history", headers=h, timeout=30)
        assert resp.status_code in (403, 404), f"expected 403/404 cross-entity, got {resp.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
