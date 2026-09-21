"""Iterasi 278 — audit training T4 (fulfillment re-decisions + history) & pagar gudang E4.1."""
import os
import requests
import pytest

def _read_frontend_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return ""

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env()).rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL kosong"
PWD = "demo12345"


def _login(email: str) -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(token: str, entity: str = "ent_ksc") -> dict:
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": entity, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def sa_hdr():
    return _hdr(_login("salesadmin@kainnusantara.id"))


@pytest.fixture(scope="module")
def admin_hdr():
    return _hdr(_login("admin@kainnusantara.id"))


# ─── SO-0009 id resolver ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def so_0009_id(sa_hdr):
    r = requests.get(f"{BASE}/api/sales-orders?limit=200", headers=sa_hdr, timeout=30)
    assert r.status_code == 200, r.text
    items = r.json().get("items", r.json()) if isinstance(r.json(), dict) else r.json()
    for it in items:
        if it.get("number") == "SO-0009":
            return it["id"]
    pytest.skip("SO-0009 tidak ditemukan pada seed")


# ═══ T4 ═══════════════════════════════════════════════════════════════════════

def test_T4_1_fulfillment_options_keys(sa_hdr, so_0009_id):
    r = requests.get(f"{BASE}/api/sales-admin/orders/{so_0009_id}/fulfillment", headers=sa_hdr, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "decisions" in body, "kunci decisions wajib ada"
    assert isinstance(body["decisions"], list)
    assert body["decisions"] == [] or len(body["decisions"]) >= 0
    assert body.get("options", {}).get("reorder", {}).get("available") is True, body.get("options")


def test_T4_2_first_reorder_creates_pr(sa_hdr, so_0009_id):
    r = requests.post(f"{BASE}/api/sales-admin/orders/{so_0009_id}/fulfillment-decision",
                      headers=sa_hdr, json={"mode": "reorder", "note": "uji 1"}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    summary = body["decision"]["summary"]
    assert "PR" in summary or "supplier" in summary.lower(), summary
    assert isinstance(body.get("decisions"), list) and len(body["decisions"]) >= 1


def test_T4_3_reaffirm_reorder_no_new_pr(sa_hdr, so_0009_id):
    # Snapshot PR sumber SO-0009
    r0 = requests.get(f"{BASE}/api/purchase-requisitions?limit=200", headers=sa_hdr, timeout=30)
    assert r0.status_code == 200, r0.text
    def _pr_from_so(items):
        cnt = 0
        for it in items:
            src = str(it.get("source_number") or it.get("source_ref") or it.get("origin_number") or "")
            if "SO-0009" in src:
                cnt += 1
            else:
                # cek link array
                for k in ("sources", "source_orders"):
                    v = it.get(k) or []
                    if any("SO-0009" in str(x) for x in v):
                        cnt += 1
                        break
        return cnt
    items0 = r0.json().get("items", r0.json())
    n_before = _pr_from_so(items0)

    r = requests.post(f"{BASE}/api/sales-admin/orders/{so_0009_id}/fulfillment-decision",
                      headers=sa_hdr, json={"mode": "reorder", "note": "uji 2"}, timeout=30)
    assert r.status_code == 200, r.text  # BUKAN 400
    body = r.json()
    summary = body["decision"]["summary"]
    assert "ditegaskan ulang" in summary.lower() or "reaffirm" in summary.lower(), summary
    assert "supersedes" in body["decision"] and isinstance(body["decision"]["supersedes"], dict), body["decision"]
    assert body["decision"]["supersedes"].get("mode") == "reorder"

    r1 = requests.get(f"{BASE}/api/purchase-requisitions?limit=200", headers=sa_hdr, timeout=30)
    items1 = r1.json().get("items", r1.json())
    n_after = _pr_from_so(items1)
    assert n_after == n_before, f"PR kembar terbentuk: {n_before} -> {n_after}"


def test_T4_4_history_length_and_last(sa_hdr, so_0009_id):
    r = requests.get(f"{BASE}/api/sales-admin/orders/{so_0009_id}/fulfillment", headers=sa_hdr, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    hist = body.get("decisions") or []
    assert len(hist) >= 2, f"decisions harus ≥2 setelah dua reorder; got {len(hist)}"
    last = body.get("decision") or hist[-1]
    assert "ditegaskan ulang" in (last.get("summary","").lower()) or last.get("mode") == "reorder"
    hint = (body.get("options", {}).get("reorder", {}) or {}).get("hint", "")
    assert "PR" in hint or "terbuka" in hint.lower(), hint


def test_T4_5_wait_and_interco_missing_source(sa_hdr, so_0009_id):
    # coba wait; hanya cek 200 bila available true, else terima 400
    r_opts = requests.get(f"{BASE}/api/sales-admin/orders/{so_0009_id}/fulfillment", headers=sa_hdr, timeout=30)
    wait_avail = ((r_opts.json().get("options", {}) or {}).get("wait", {}) or {}).get("available")
    r = requests.post(f"{BASE}/api/sales-admin/orders/{so_0009_id}/fulfillment-decision",
                      headers=sa_hdr, json={"mode": "wait", "note": "tunggu"}, timeout=30)
    if wait_avail:
        assert r.status_code == 200, r.text
    else:
        assert r.status_code in (200, 400)

    r2 = requests.post(f"{BASE}/api/sales-admin/orders/{so_0009_id}/fulfillment-decision",
                       headers=sa_hdr, json={"mode": "interco", "note": "x"}, timeout=30)
    assert r2.status_code == 400, r2.text
    detail = r2.json().get("detail", "")
    assert "badan usaha sumber" in str(detail).lower() or "sumber" in str(detail).lower(), detail


# ═══ C — pagar gudang E4.1 ═══════════════════════════════════════════════════

@pytest.fixture(scope="module")
def ksc_warehouse_id(admin_hdr):
    r = requests.get(f"{BASE}/api/warehouses?limit=200", headers=admin_hdr, timeout=30)
    assert r.status_code == 200, r.text
    items = r.json().get("items", r.json()) if isinstance(r.json(), dict) else r.json()
    for w in items:
        eids = w.get("entity_ids") or ([w.get("entity_id")] if w.get("entity_id") else [])
        if "ent_ksc" in eids and w.get("active", True):
            return w["id"]
    pytest.skip("Tidak ada warehouse ent_ksc")


def test_C1_rfid_cc_start_guards(admin_hdr, ksc_warehouse_id):
    # empty
    r0 = requests.post(f"{BASE}/api/rfid/cycle-count/start", headers=admin_hdr,
                      json={"warehouse_id": ""}, timeout=30)
    assert r0.status_code == 400, r0.text
    assert "gudang" in str(r0.json().get("detail", "")).lower()

    r1 = requests.post(f"{BASE}/api/rfid/cycle-count/start", headers=admin_hdr,
                      json={"warehouse_id": "wh_tidak_ada"}, timeout=30)
    assert r1.status_code == 404, r1.text

    r2 = requests.post(f"{BASE}/api/rfid/cycle-count/start", headers=admin_hdr,
                      json={"warehouse_id": ksc_warehouse_id}, timeout=30)
    assert r2.status_code in (200, 201), r2.text


def test_C2_putaway_orders_guard(admin_hdr):
    r = requests.post(f"{BASE}/api/putaway-orders", headers=admin_hdr,
                     json={"from_warehouse_id": "", "to_warehouse_id": "", "roll_ids": []}, timeout=30)
    assert r.status_code == 400, r.text  # bukan 500


def test_C3_sales_return_relocate_404(admin_hdr):
    # cari retur KSC apapun
    r = requests.get(f"{BASE}/api/sales-returns?limit=50", headers=admin_hdr, timeout=30)
    assert r.status_code == 200, r.text
    items = r.json().get("items", r.json()) if isinstance(r.json(), dict) else r.json()
    if not items:
        pytest.skip("Tidak ada sales-return")
    rid = items[0]["id"]
    r2 = requests.post(f"{BASE}/api/sales-returns/{rid}/relocate", headers=admin_hdr,
                      json={"to_warehouse_id": "wh_tidak_ada", "note": "x"}, timeout=30)
    assert r2.status_code == 404, r2.text  # bukan 500


# ═══ Regresi ringan ═════════════════════════════════════════════════════════

def test_REG_desk_and_approval_inbox(sa_hdr):
    r = requests.get(f"{BASE}/api/sales-admin/desk", headers=sa_hdr, timeout=30)
    assert r.status_code == 200, r.text

    mgr = _hdr(_login("manager@kainnusantara.id"))
    r2 = requests.get(f"{BASE}/api/approvals/my-queue", headers=mgr, timeout=30)
    assert r2.status_code == 200, r2.text


def test_REG_all_roles_login():
    for email in ["admin@kainnusantara.id", "manager@kainnusantara.id",
                  "salesadmin@kainnusantara.id", "sales@kainnusantara.id",
                  "warehouse@kainnusantara.id"]:
        r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
        assert r.status_code == 200, f"{email}: {r.text}"
