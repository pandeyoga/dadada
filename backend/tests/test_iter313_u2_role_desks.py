"""U-2 (2026-09) — Uji Meja Saya /api/desks/me untuk 6 peran + T-11 (approve idempoten)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://knhost-preview.preview.emergentagent.com").rstrip("/")
ENTITY = "ent_ksc"

CREDS = {
    "admin": ("admin@kainnusantara.id", "demo12345"),
    "manager": ("manager@kainnusantara.id", "demo12345"),
    "sales": ("sales@kainnusantara.id", "demo12345"),
    "warehouse": ("warehouse@kainnusantara.id", "demo12345"),
    "finance": ("finance@kainnusantara.id", "demo12345"),
    "salesadmin": ("salesadmin@kainnusantara.id", "demo12345"),
    "md": ("md@kainnusantara.id", "demo12345"),
}


def _login(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    return r.json().get("token") or r.json().get("access_token")


def _headers(token, entity=ENTITY):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": entity, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    out = {}
    for role, (email, pw) in CREDS.items():
        try:
            out[role] = _login(email, pw)
        except AssertionError as e:
            print(f"[skip] {role}: {e}")
    return out


# ── U-2: role desks ─────────────────────────────────────────────────────────
EXPECTED_QUEUES = {
    "manager": {"giliran_saya", "so_acc", "po_acc", "retur_acc", "harga_khusus"},
    "sales": {"giliran_saya", "so_menunggu", "so_konfirmasi", "so_ditolak", "sampel_saya"},
    "warehouse": {"giliran_saya", "tugas_wms", "po_terima", "sampel_potong"},
    "admin": {"giliran_saya", "so_acc", "po_acc", "retur_acc", "harga_khusus", "tugas_wms", "po_terima", "sampel_potong"},
}
EXPECTED_TITLE = {"manager": "Meja Manajer", "sales": "Meja Sales", "warehouse": "Meja Operator Gudang", "admin": "Meja Admin"}


@pytest.mark.parametrize("role", ["manager", "sales", "warehouse", "admin"])
def test_desks_me_role(role, tokens):
    if role not in tokens:
        pytest.skip(f"no token for {role}")
    r = requests.get(f"{BASE_URL}/api/desks/me", headers=_headers(tokens[role]), timeout=20)
    assert r.status_code == 200, f"{role}: {r.status_code} {r.text[:300]}"
    data = r.json()
    assert data["role"] == role
    assert data["title"] == EXPECTED_TITLE[role]
    qids = {q["id"] for q in data["queues"]}
    assert EXPECTED_QUEUES[role].issubset(qids), f"{role} missing queues: {EXPECTED_QUEUES[role] - qids}"
    # total_items = sum rows
    assert data["total_items"] == sum(len(q["rows"]) for q in data["queues"])
    # each row schema
    for q in data["queues"]:
        for row in q["rows"]:
            for k in ("ref_type", "ref_id", "number", "title", "badge", "age_days"):
                assert k in row, f"{role}/{q['id']} missing row field {k}"


@pytest.mark.parametrize("role", ["finance", "salesadmin", "md"])
def test_desks_me_other_roles_return_404(role, tokens):
    if role not in tokens:
        pytest.skip(f"no {role} account")
    r = requests.get(f"{BASE_URL}/api/desks/me", headers=_headers(tokens[role]), timeout=20)
    assert r.status_code == 404, f"expected 404 for {role}, got {r.status_code}"


def test_sales_desk_only_own_sos(tokens):
    if "sales" not in tokens:
        pytest.skip("no sales token")
    r = requests.get(f"{BASE_URL}/api/desks/me", headers=_headers(tokens["sales"]), timeout=20)
    assert r.status_code == 200
    # Get sales user id
    me = requests.get(f"{BASE_URL}/api/auth/me", headers=_headers(tokens["sales"]), timeout=10)
    if me.status_code != 200:
        pytest.skip("cannot resolve /auth/me")
    sales_id = me.json().get("id")
    sales_email = me.json().get("email")
    sales_name = me.json().get("name")
    data = r.json()
    for q in data["queues"]:
        if q["id"].startswith("so_"):
            for row in q["rows"]:
                # Fetch SO to check ownership
                so = requests.get(f"{BASE_URL}/api/sales-orders/{row['ref_id']}", headers=_headers(tokens["sales"]), timeout=10)
                if so.status_code == 200:
                    s = so.json()
                    owners = {s.get("sales_id"), s.get("created_by")}
                    assert owners & {sales_id, sales_email, sales_name}, f"SO {row['ref_id']} not owned by sales"


# ── U-2: sample flow dipindah ke SO ber-is_sample (endpoint /sample-requests dihapus) ──

def test_giliran_saya_sample_flow(tokens):
    """admin creates sample_request → warehouse desk giliran_saya has row."""
    if "admin" not in tokens or "warehouse" not in tokens:
        pytest.skip("need admin+warehouse")
    # KN-A08 (audit 2026-09-21) — rute /api/sample-requests SUDAH DIHAPUS; uji ini
    # menunjuk endpoint mati. Isolasi sampel kini diuji di tests/test_kn_audit_2026_09_21.py.
    pytest.skip("endpoint /sample-requests dihapus — lihat tests/test_kn_audit_2026_09_21.py")
    payload = {"customer_id": "cust_toko_kain", "product_id": "prod_batik_mega", "length": 0.5, "entity_id": ENTITY}
    r = requests.post(f"{BASE_URL}/api/sample-requests", headers=_headers(tokens["admin"]), json=payload, timeout=15)
    assert r.status_code in (200, 201), f"sample create failed: {r.status_code} {r.text[:300]}"
    sample = r.json()
    sample_id = sample.get("id")
    number = sample.get("number", "")
    time.sleep(3)

    wh = requests.get(f"{BASE_URL}/api/desks/me", headers=_headers(tokens["warehouse"]), timeout=20)
    assert wh.status_code == 200
    giliran = next((q for q in wh.json()["queues"] if q["id"] == "giliran_saya"), None)
    assert giliran is not None, "no giliran_saya queue"
    # find row matching sample
    matches = [r for r in giliran["rows"] if sample_id in (r.get("ref_id"), "") or number and number in (r.get("number") or r.get("title") or "")]
    assert matches or any("Potong" in (r.get("title") or "") for r in giliran["rows"]), \
        f"giliran_saya has no matching turn for sample {sample_id}/{number}; rows={giliran['rows'][:3]}"
    if matches:
        row = matches[0]
        assert "Potong" in row.get("title", "") or "Potong" in row.get("subtitle", ""), f"unexpected title: {row.get('title')}"
        # extra.link should be 'operations' (spread top-level by _row)
        link = row.get("link", "")
        assert link == "operations", f"expected link=operations, got {link!r}"

    # Cleanup: cancel + run turn_scan
    cancel = requests.post(f"{BASE_URL}/api/sample-requests/{sample_id}/cancel", headers=_headers(tokens["admin"]), json={"reason": "TEST cleanup"}, timeout=15)
    print(f"[cleanup] cancel status={cancel.status_code}")
    scan = requests.post(f"{BASE_URL}/api/scheduler/jobs/turn_scan/run", headers=_headers(tokens["admin"]), timeout=30)
    print(f"[cleanup] turn_scan status={scan.status_code}")
    time.sleep(2)

    wh2 = requests.get(f"{BASE_URL}/api/desks/me", headers=_headers(tokens["warehouse"]), timeout=20)
    if wh2.status_code == 200:
        giliran2 = next((q for q in wh2.json()["queues"] if q["id"] == "giliran_saya"), None)
        remaining = [r for r in (giliran2 or {}).get("rows", []) if r.get("ref_id") == sample_id]
        assert not remaining, f"turn row still present after cancel+scan: {remaining}"


# ── T-11: approve idempotent on already-approved SO ────────────────────────
def test_t11_approve_already_approved_idempotent(tokens):
    if "manager" not in tokens:
        pytest.skip("no manager")
    hdr = _headers(tokens["manager"])
    # find already-approved SO
    r = requests.get(f"{BASE_URL}/api/sales-orders?status=approved&limit=5", headers=hdr, timeout=15)
    assert r.status_code == 200
    payload = r.json()
    items = payload if isinstance(payload, list) else payload.get("items") or payload.get("data") or []
    if not items:
        pytest.skip("no approved SO to retest idempotency")
    so = items[0]
    so_id = so["id"]
    ap = requests.post(f"{BASE_URL}/api/sales-orders/{so_id}/approve", headers=hdr, json={}, timeout=15)
    assert ap.status_code == 200, f"expected 200 idempotent, got {ap.status_code}: {ap.text[:300]}"
    body = ap.json()
    status = body.get("status") or (body.get("order") or {}).get("status")
    assert status == "approved", f"unexpected status after idempotent approve: {status}"
