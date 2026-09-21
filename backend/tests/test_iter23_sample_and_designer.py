"""Iterasi 23 tester — cakupan spesifik permintaan review:
- A: Pesanan Sampel (SOS-) create, mixed→400 SAMPLE_MIXED, limit→400 SAMPLE_LIMIT,
     list/desk/stats, confirm-paid-sebelum-approve→409, approve-payment→confirm→cancel
- B: Design Studio revisi (kategori pattern/design, tambah kategori, next-code,
     designer create → SRI-BTK-PG-###, request-revision otomatis buka ronde, 
     approve dengan recommended_product_ids, final flow, RBAC designer 403)
"""
import io, os, re, struct, time, zlib
import pytest
import requests
from pymongo import MongoClient

def _base():
    b = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not b:
        for line in open("/app/frontend/.env"):
            if line.startswith("REACT_APP_BACKEND_URL="):
                b = line.split("=", 1)[1].strip(); break
    return b.rstrip("/")

BASE = _base() + "/api"
ENT = "ent_ksc"
db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]

def _login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "demo12345"}, timeout=15)
    r.raise_for_status()
    tok = r.json().get("token") or r.json().get("access_token")
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT}

def _png():
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + ch(b"IEND", b""))

# ─────────────────────────── FIXTURES ───────────────────────────
@pytest.fixture(scope="module")
def admin_h(): return _login("admin@kainnusantara.id")
@pytest.fixture(scope="module")
def sales_h(): return _login("sales@kainnusantara.id")
@pytest.fixture(scope="module")
def sample_admin_h(): return _login("sampleadmin@kainnusantara.id")
@pytest.fixture(scope="module")
def finance_h(): return _login("finance@kainnusantara.id")
@pytest.fixture(scope="module")
def designer_h(): return _login("designer@kainnusantara.id")

@pytest.fixture(scope="module")
def ctx():
    prod = db.products.find_one({"base_unit": "yard"}, {"_id": 0}) or db.products.find_one({}, {"_id": 0})
    cust = db.customers.find_one({"entity_id": ENT, "addresses": {"$exists": True, "$ne": []}}, {"_id": 0})
    assert prod and cust and cust.get("addresses"), "butuh product & customer ent_ksc"
    return {"prod": prod, "cust": cust}

# ═════════════════════════ BACKEND A: SAMPLE ORDERS ═════════════════════════
def test_a1_create_sample_order_paid(sales_h, ctx):
    """SOS- prefix + order_type sample paid"""
    prod, cust = ctx["prod"], ctx["cust"]
    payload = {"customer_id": cust["id"], "shipping_address_id": cust["addresses"][0]["id"],
               "entity_id": ENT, "order_type": "sample", "sample_billing": "paid",
               "items": [{"product_id": prod["id"], "quantity": 1.0, "unit": prod["base_unit"],
                          "is_sample": True, "sample_price": 15000}]}
    r = requests.post(f"{BASE}/sales-orders", headers=sales_h, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    so = r.json()
    assert "SOS-" in so["number"], f"expected SOS- prefix, got {so['number']}"
    assert so.get("order_type") == "sample" and so.get("sample_billing") == "paid"
    assert so.get("sample_payment_status") in ("awaiting_approval",)
    # store for chain tests
    globals()["_SO_PAID_ID"] = so["id"]

def test_a1_sample_mixed_rejected(sales_h, ctx):
    prod, cust = ctx["prod"], ctx["cust"]
    # order_type default (regular) tapi salah satu item is_sample=True → SAMPLE_MIXED
    r = requests.post(f"{BASE}/sales-orders", headers=sales_h, json={
        "customer_id": cust["id"], "shipping_address_id": cust["addresses"][0]["id"], "entity_id": ENT,
        "items": [{"product_id": prod["id"], "quantity": 1.0, "unit": prod["base_unit"], "is_sample": True},
                  {"product_id": prod["id"], "quantity": 5.0, "unit": prod["base_unit"]}]}, timeout=30)
    assert r.status_code == 400
    assert r.json().get("detail", {}).get("code") == "SAMPLE_MIXED", r.text

def test_a1_sample_limit_rejected(sales_h, ctx):
    prod, cust = ctx["prod"], ctx["cust"]
    # for yard product limit=5 (woven). Push to 6.
    r = requests.post(f"{BASE}/sales-orders", headers=sales_h, json={
        "customer_id": cust["id"], "shipping_address_id": cust["addresses"][0]["id"], "entity_id": ENT,
        "order_type": "sample", "sample_billing": "free",
        "items": [{"product_id": prod["id"], "quantity": 6.0, "unit": prod["base_unit"], "is_sample": True}]}, timeout=30)
    assert r.status_code == 400
    assert r.json().get("detail", {}).get("code") == "SAMPLE_LIMIT", r.text

def test_a1_sample_endpoints_200(sample_admin_h):
    for path in ["/sample-orders", "/sample-orders/desk", "/sample-orders/stats/summary"]:
        r = requests.get(f"{BASE}{path}?entity_id={ENT}", headers=sample_admin_h, timeout=20)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text}"

def test_a2_confirm_paid_before_approve_409(sample_admin_h):
    oid = globals().get("_SO_PAID_ID")
    assert oid, "prior test failed"
    r = requests.post(f"{BASE}/sample-orders/{oid}/confirm", headers=sample_admin_h, json={}, timeout=15)
    assert r.status_code == 409, r.text
    assert r.json().get("detail", {}).get("code") == "SAMPLE_PAYMENT_PENDING"

def test_a2_approve_payment_then_confirm(finance_h, sample_admin_h):
    oid = globals().get("_SO_PAID_ID")
    r = requests.post(f"{BASE}/sample-orders/{oid}/approve-payment", headers=finance_h,
                      json={"note": "uji"}, timeout=15)
    assert r.status_code == 200, r.text
    r2 = requests.post(f"{BASE}/sample-orders/{oid}/confirm", headers=sample_admin_h, json={}, timeout=30)
    assert r2.status_code == 200, r2.text
    # outbound task sample_cut dibuat
    task = db.wms_tasks.find_one({"order_id": oid, "task_subtype": "sample_cut"}, {"_id": 0})
    assert task and task["flow_type"] == "outbound"

def test_a2_cancel_flow(sales_h, sample_admin_h, ctx):
    prod, cust = ctx["prod"], ctx["cust"]
    r = requests.post(f"{BASE}/sales-orders", headers=sales_h, json={
        "customer_id": cust["id"], "shipping_address_id": cust["addresses"][0]["id"], "entity_id": ENT,
        "order_type": "sample", "sample_billing": "free",
        "items": [{"product_id": prod["id"], "quantity": 1.0, "unit": prod["base_unit"], "is_sample": True}]}, timeout=30)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    c = requests.post(f"{BASE}/sample-orders/{oid}/cancel", headers=sample_admin_h, json={"note": "batal"}, timeout=15)
    assert c.status_code == 200, c.text

# ═════════════════════════ BACKEND B: DESIGN STUDIO ═════════════════════════
def test_b1_categories_both_axes(admin_h):
    r = requests.get(f"{BASE}/design-studio/categories", headers=admin_h, params={"design_type": "pattern"}, timeout=15)
    assert r.status_code == 200
    codes = {c["code"] for c in r.json()}
    assert {"SLR", "BTK", "BGA", "PLD", "ABS", "CSMR"} <= codes, codes
    r2 = requests.get(f"{BASE}/design-studio/categories", headers=admin_h, params={"design_type": "design"}, timeout=15)
    codes2 = {c["code"] for c in r2.json()}
    assert {"AO", "PG"} <= codes2, codes2

def test_b1_add_design_category(admin_h):
    code = f"BR{int(time.time()) % 100:02d}"
    r = requests.post(f"{BASE}/design-studio/categories", headers=admin_h,
                      json={"design_type": "design", "code": code, "name": "TEST_Border"}, timeout=15)
    assert r.status_code == 200, r.text
    r2 = requests.get(f"{BASE}/design-studio/categories", headers=admin_h, params={"design_type": "design"}, timeout=15)
    assert code in {c["code"] for c in r2.json()}

def test_b1_reject_bad_design_type(admin_h):
    r = requests.post(f"{BASE}/design-studio/categories", headers=admin_h,
                      json={"design_type": "motif", "code": "XX9", "name": "bad"}, timeout=15)
    assert r.status_code == 400, r.text

def test_b1_next_code_format(admin_h):
    r = requests.get(f"{BASE}/design-studio/next-code", headers=admin_h,
                     params={"category_code": "SLR", "design_category_code": "AO"}, timeout=15)
    assert r.status_code == 200
    assert re.match(r"^BDI-SLR-AO-\d{3}$", r.json()["code"]), r.json()

# ── B2: designer create, submit; admin notif ────────────────────────────
@pytest.fixture(scope="module")
def sri_design(designer_h):
    payload = {"title": f"TEST_sri_{int(time.time())}", "category_code": "BTK", "design_category_code": "PG"}
    r = requests.post(f"{BASE}/design-gallery", headers=designer_h, json=payload, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert re.match(r"^SRI-BTK-PG-\d{3}$", d["code"]), d["code"]
    assert d["round_label"] == "Pengajuan awal" and d["revision_count"] == 0
    assert d["final_color_count"] == 4
    assert d["design_category_name"] == "Pinggiran"
    return d

def test_b2_create_and_submit(designer_h, admin_h, sri_design):
    gid = sri_design["id"]
    # bad dcode
    bad = requests.post(f"{BASE}/design-gallery", headers=designer_h,
                       json={"title": "TEST_bad", "category_code": "BTK", "design_category_code": "ZZZ"}, timeout=15)
    assert bad.status_code == 400, bad.text
    # submit no file -> 400
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/submit", headers=designer_h, json={}, timeout=15)
    assert r.status_code == 400
    # upload 2 artworks
    for i in range(2):
        u = requests.post(f"{BASE}/design-gallery/{gid}/files-kind/artwork",
                          headers=designer_h, files={"file": (f"a{i}.png", _png(), "image/png")}, timeout=15)
        assert u.status_code == 200, u.text
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/submit", headers=designer_h, json={}, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "pending_approval"
    # admin notification exists
    time.sleep(0.5)
    nr = requests.get(f"{BASE}/notifications", headers=admin_h, params={"limit": 30}, timeout=15)
    assert nr.status_code == 200
    titles = [(n.get("title") or "") for n in (nr.json() if isinstance(nr.json(), list) else nr.json().get("items", []))]
    assert any(sri_design["code"] in t and "diajukan" in t for t in titles), f"no notif; got titles={titles[:5]}"

# ── B3: full assess flow with request-revision + approve + final ─────────
def test_b3_full_revision_and_final(admin_h, designer_h, sri_design):
    gid = sri_design["id"]
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/start-review", headers=admin_h, json={}, timeout=15)
    assert r.status_code == 200
    # request-revision → auto ronde baru
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/request-revision", headers=admin_h,
                      json={"note": "perbaiki", "score": 1.25}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "revision" and d["version"] == 2 and d["round_label"] == "Revisi 1"
    assert d["revision_count"] == 1 and d["rounds"][0]["result"] == "revision"
    # new-version manual saat revision → 400
    r = requests.post(f"{BASE}/design-gallery/{gid}/new-version", headers=admin_h, json={"note": "x"}, timeout=15)
    assert r.status_code == 400
    # designer submit v2 no file → 400
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/submit", headers=designer_h, json={}, timeout=15)
    assert r.status_code == 400
    # upload + submit
    requests.post(f"{BASE}/design-gallery/{gid}/files-kind/artwork", headers=designer_h,
                  files={"file": ("v2.png", _png(), "image/png")}, timeout=15)
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/submit", headers=designer_h, json={}, timeout=15)
    assert r.status_code == 200
    # get one valid product id
    pr = requests.get(f"{BASE}/products", headers=admin_h, params={"entity_id": ENT, "limit": 3}, timeout=15)
    assert pr.status_code == 200
    plist = pr.json() if isinstance(pr.json(), list) else pr.json().get("items", [])
    pid = plist[0].get("id") if plist else None
    assert pid, "need a product id"
    # admin approve with recommended_product_ids + final_color_count=2
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/approve", headers=admin_h,
                      json={"score": 1.75, "final_color_count": 2, "recommended_product_ids": [pid]}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "approved" and d["final_color_count"] == 2
    assert d["final"]["complete"] is False
    assert pid in (d.get("recommended_product_ids") or [])
    # activate before final -> 400
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/activate", headers=admin_h, json={}, timeout=15)
    assert r.status_code == 400
    # submit-final no mockup -> 400 containing "Mockup"
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/submit-final", headers=designer_h, json={}, timeout=15)
    assert r.status_code == 400 and "Mockup" in r.text
    for i in range(2):
        requests.post(f"{BASE}/design-gallery/{gid}/files-kind/colorway", headers=designer_h,
                      files={"file": (f"cw{i}.png", _png(), "image/png")}, timeout=15)
    requests.post(f"{BASE}/design-gallery/{gid}/files-kind/mockup", headers=designer_h,
                  files={"file": ("mockup.png", _png(), "image/png")}, timeout=15)
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/submit-final", headers=designer_h, json={}, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "final_submitted"
    assert r.json()["final"]["complete"] is True
    # return-final no note -> 400
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/return-final", headers=admin_h, json={}, timeout=15)
    assert r.status_code == 400
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/return-final", headers=admin_h,
                     json={"note": "revisi mockup"}, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/submit-final", headers=designer_h, json={}, timeout=15)
    assert r.status_code == 200
    r = requests.post(f"{BASE}/design-gallery/{gid}/lifecycle/activate", headers=admin_h, json={}, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "active"

# ── B4: RBAC designer forbidden ──────────────────────────────────────────
def test_b4_designer_forbidden(designer_h, sri_design):
    gid = sri_design["id"]
    for path, body in [
        (f"/design-gallery/{gid}/lifecycle/approve", {"score": 1.75}),
        (f"/design-gallery/{gid}/lifecycle/activate", {}),
        (f"/design-gallery/{gid}/lifecycle/return-final", {"note": "x"}),
    ]:
        r = requests.post(f"{BASE}{path}", headers=designer_h, json=body, timeout=15)
        assert r.status_code == 403, f"{path}: {r.status_code} {r.text[:120]}"
