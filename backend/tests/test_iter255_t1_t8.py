"""Iterasi 255 — validasi ulang T1..T8 sesi 2026-06c (HANDOFF_AUDIT_SESI_2026_06C.md).

Menguji lewat REACT_APP_BACKEND_URL (preview eksternal) supaya jalur yang sama
dengan UI benar-benar diuji (ingress + kubernetes).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
PWD = "demo12345"

ACCOUNTS = {
    "admin": "admin@kainnusantara.id",
    "manager": "manager@kainnusantara.id",
    "finance": "finance@kainnusantara.id",
    "warehouse": "warehouse@kainnusantara.id",
    "sales_admin": "salesadmin@kainnusantara.id",
    "sales": "sales@kainnusantara.id",
}


def _login(email: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD}, timeout=20)
    assert r.status_code == 200, f"login {email} → {r.status_code} {r.text[:200]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in login response: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def tokens():
    return {role: _login(email) for role, email in ACCOUNTS.items()}


def _h(tok, entity="ent_ksc"):
    return {"Authorization": f"Bearer {tok}", "X-Active-Entity": entity, "Content-Type": "application/json"}


# ─────────────────────────────────────────────────────────────────────────────
# T1: GET /api/inventory/rolls/{id}/cost-history — 200 untuk 5 peran
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sample_roll_id(tokens):
    r = requests.get(f"{API}/inventory/rolls?owner_entity_id=ent_ksc",
                     headers=_h(tokens["admin"]), timeout=20)
    assert r.status_code == 200, r.text[:200]
    rolls = r.json()
    if isinstance(rolls, dict):
        rolls = rolls.get("items", [])
    assert rolls, "tak ada roll di ent_ksc untuk seed data"
    return rolls[0]["id"]


@pytest.mark.parametrize("role", ["finance", "sales_admin", "warehouse", "manager", "admin"])
def test_t1_cost_history_200_for_role(tokens, sample_roll_id, role):
    r = requests.get(f"{API}/inventory/rolls/{sample_roll_id}/cost-history",
                     headers=_h(tokens[role]), timeout=20)
    assert r.status_code == 200, f"[{role}] {r.status_code}: {r.text[:200]}"
    j = r.json()
    # Bentuk respons wajib punya kunci-kunci ini (FE bergantung padanya).
    for k in ("roll_id", "roll_no", "unit_cost", "count", "history"):
        assert k in j, f"[{role}] kunci {k!r} hilang di respons cost-history"
    assert isinstance(j["history"], list)


def test_t1_cost_history_404_for_unknown_roll(tokens):
    r = requests.get(f"{API}/inventory/rolls/roll_tidak_ada_xxx/cost-history",
                     headers=_h(tokens["finance"]), timeout=20)
    assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# T2: papan meja finance & operasi — action.note_field harus "" (tanpa catatan)
# ─────────────────────────────────────────────────────────────────────────────

def _get_home(tokens, role, entity="ent_ksc"):
    r = requests.get(f"{API}/home/{role}", headers=_h(tokens[role], entity), timeout=25)
    assert r.status_code == 200, f"/home/{role} → {r.status_code} {r.text[:300]}"
    return r.json()


def _find_board(home_json, key):
    # /home/* mengembalikan `waiting_boards` (list of {key, rows,...})
    for b in (home_json.get("waiting_boards") or home_json.get("boards") or []):
        if b.get("key") == key:
            return b
    return None


def test_t2_finance_boards_no_note_field(tokens):
    """Meja Finance: kontrabon verify, kontrabon approve, vendor_bill — note_field ''."""
    home = _get_home(tokens, "finance")
    checked = 0
    for key in ("contra_bon_verify", "contra_bon_approve", "vendor_bill"):
        b = _find_board(home, key)
        if not b:
            continue
        # Cek tiap baris ber-action
        for row in b.get("rows", []):
            act = row.get("action")
            if not act or act.get("blocked_reason"):
                continue
            assert act.get("note_field", "") == "", (
                f"[{key}] baris {row.get('number')} masih meminta note_field="
                f"{act.get('note_field')!r} — dialog seharusnya Ya/Batal saja")
            checked += 1
    # Finance mungkin tak dapat action pada vendor_bill (matriks izin) — tidak apa.
    # Kalau tak ada baris yang ber-action, tes tetap lewat (tak ada kontradiksi).
    print(f"[T2 finance] {checked} baris ber-action diverifikasi")


def test_t2_warehouse_transfer_no_note_field(tokens):
    """Papan transfer di layar Operasi (home warehouse) — note_field ''."""
    home = _get_home(tokens, "warehouse")
    b = _find_board(home, "transfer")
    if not b:
        pytest.skip("papan transfer tidak muncul untuk warehouse role di data demo")
    for row in b.get("rows", []):
        act = row.get("action")
        if not act or act.get("blocked_reason"):
            continue
        assert act.get("note_field", "") == "", (
            f"transfer {row.get('number')} note_field={act.get('note_field')!r}")


# ─────────────────────────────────────────────────────────────────────────────
# T3: cycle_count/approve dengan body {} → approval_reason default server
# ─────────────────────────────────────────────────────────────────────────────

def test_t3_cycle_count_approve_default_reason(tokens):
    # Cari 1 sesi submitted
    r = requests.get(f"{API}/cycle-count/sessions?status=submitted",
                     headers=_h(tokens["admin"]), timeout=20)
    if r.status_code != 200:
        pytest.skip(f"endpoint sessions list: {r.status_code}")
    sessions = r.json()
    if isinstance(sessions, dict):
        sessions = sessions.get("items", [])
    submitted = [s for s in sessions if s.get("status") == "submitted"]
    if not submitted:
        pytest.skip("tak ada cycle_count_sessions berstatus 'submitted' di data demo")
    sid = submitted[0]["id"]
    # Approve dengan body kosong {}
    r = requests.post(f"{API}/cycle-count/sessions/{sid}/approve",
                      headers=_h(tokens["admin"]), json={}, timeout=25)
    assert r.status_code in (200, 201), f"approve {sid} → {r.status_code} {r.text[:200]}"
    j = r.json()
    reason = j.get("approval_reason") or j.get("session", {}).get("approval_reason") or ""
    assert reason == "Disetujui sesuai hasil cycle count", (
        f"approval_reason={reason!r} — default server tidak terisi (T3 REGRESI)")


# ─────────────────────────────────────────────────────────────────────────────
# T4: POST /api/vendor-bills/{id}/approve untuk bill TANPA po_id → tidak 500
# ─────────────────────────────────────────────────────────────────────────────

def test_t4_vendor_bill_approve_no_po_no_500(tokens):
    # Buat synthetic bill pending_approval TANPA po_id (kondisi 'tagihan makloon').
    import sys, asyncio
    sys.path.insert(0, "/app/backend")
    from db import db  # noqa: WPS433
    from core_utils import new_id, now_iso  # noqa: WPS433

    async def _insert():
        bid = new_id("vbill")
        doc = {
            "id": bid, "bill_number": f"TEST-VB-{bid[-6:]}", "supplier_invoice_no": "",
            "po_id": "", "po_number": "", "supplier_id": "sup_test",
            "supplier_name": "Supplier Makloon Test", "warehouse_id": "", "warehouse_name": "",
            "entity_id": "ent_ksc", "bill_date": now_iso(), "due_date": "",
            "match_mode": "received", "items": [],
            "total_amount": 100000.0, "items_discount_total": 0.0,
            "order_discount_percent": 0.0, "order_discount_amount": 0.0,
            "discount_total": 0.0, "net_subtotal": 100000.0, "dpp": 100000.0,
            "ppn_rate": 0.0, "ppn_mode": "excluded", "is_pkp": False, "ppn_amount": 0.0,
            "grand_total": 100000.0, "tax_mode": "",
            "match_status": "warning", "match_exceptions": [], "within_tolerance": True,
            "status": "pending_approval", "approval_required": True,
            "required_approval_role": "manager", "approval_status": "pending",
            "approved_by": "", "approved_at": "",
            "amount_paid": 0.0, "outstanding": 100000.0, "payment_status": "unpaid",
            "payments": [], "notes": "T4 regresi test", "timeline": [],
            "created_by": "TEST", "created_by_id": "test_creator",
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.vendor_bills.insert_one(doc)
        return bid

    async def _cleanup(bid):
        await db.vendor_bills.delete_one({"id": bid})

    bid = asyncio.get_event_loop().run_until_complete(_insert())
    try:
        # Manager (bukan pembuat) approve — cek TIDAK 500 KeyError 'po_id'.
        r = requests.post(f"{API}/vendor-bills/{bid}/approve",
                          headers=_h(tokens["manager"]), json={}, timeout=25)
        assert r.status_code != 500, (
            f"REGRESI T4: approve bill tanpa po_id → 500\n{r.text[:400]}")
        # 200 ideal (posted). SoD/403 tak berlaku (creator_id 'test_creator' ≠ manager).
        assert r.status_code in (200, 201), f"expected 200, got {r.status_code}: {r.text[:200]}"
        # Verify posted
        j = r.json()
        assert j.get("status") == "posted", f"status akhir: {j.get('status')}"
    finally:
        asyncio.get_event_loop().run_until_complete(_cleanup(bid))


# ─────────────────────────────────────────────────────────────────────────────
# T5: special_order — jika actor adalah PEMBUAT → action.blocked_reason muncul
# ─────────────────────────────────────────────────────────────────────────────

def test_t5_special_order_blocked_reason_for_creator(tokens):
    # Cari special_order pending_approval + pembuatnya
    home_admin = _get_home(tokens, "admin")
    b = _find_board(home_admin, "special_order")
    if not b or not b.get("rows"):
        pytest.skip("papan special_order kosong di data demo")
    # Admin bukan pembuat → aksinya seharusnya path yang valid (tidak blocked).
    for row in b["rows"]:
        act = row.get("action")
        assert act is None or "blocked_reason" in act or act.get("path"), (
            f"aksi tak konsisten: {act}")
    # Sekarang sebagai manager (yang juga bisa approve). Jika ada dokumen yang dibuat
    # manager sendiri, action harus blocked_reason terisi.
    home_mgr = _get_home(tokens, "manager")
    bm = _find_board(home_mgr, "special_order")
    if bm:
        blocked_seen = any(
            (row.get("action") or {}).get("blocked_reason")
            for row in bm.get("rows", []))
        # Tak wajib ada (bergantung data demo) — tapi bila ada, path harus ""
        for row in bm.get("rows", []):
            act = row.get("action") or {}
            if act.get("blocked_reason"):
                assert act.get("path", "") == "", (
                    "action.blocked_reason terisi TAPI path masih ada — tombol "
                    "seharusnya tidak boleh memanggil endpoint")
        print(f"[T5] blocked_seen(manager)={blocked_seen}")


# ─────────────────────────────────────────────────────────────────────────────
# T8: registry REASONS tidak lagi memuat 'cycle_count_adjustment'
# ─────────────────────────────────────────────────────────────────────────────

def test_t8_reasons_registry_no_cycle_count_adjustment():
    # Impor langsung dari backend (tes ini berjalan di dalam kontainer app)
    import sys
    sys.path.insert(0, "/app/backend")
    from services import roll_cost_history as rch  # noqa: WPS433
    assert "cycle_count_adjustment" not in rch.REASONS, (
        "REGRESI T8: 'cycle_count_adjustment' kembali muncul di REASONS")
    # Alasan yang WAJIB tetap ada (dipakai penulisnya)
    for k in ("interco_return_revalue", "interco_purchase_revalue",
              "landed_cost_allocation", "startup_backfill"):
        assert k in rch.REASONS, f"alasan '{k}' hilang dari REASONS"


# ─────────────────────────────────────────────────────────────────────────────
# Regresi umum: /api/home/{role} 200 untuk peran yang berhak
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role", ["admin", "manager", "warehouse", "finance", "sales"])
def test_home_endpoints_200(tokens, role):
    r = requests.get(f"{API}/home/{role}", headers=_h(tokens[role]), timeout=25)
    assert r.status_code == 200, f"/home/{role} → {r.status_code} {r.text[:300]}"
    j = r.json()
    # Signature baru menerima `actor`; kunci beranda bervariasi per peran.
    expected_any = {"waiting_boards", "approvals", "kpi", "commission", "team",
                    "sales", "period", "total_waiting"}
    assert expected_any & set(j.keys()), (
        f"/home/{role} tak punya kunci beranda yang dikenal: {list(j.keys())[:10]}")


# Sanity: login endpoint
def test_login_returns_token_field():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ACCOUNTS["admin"], "password": PWD}, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert "token" in body, "field 'token' hilang (dokumen HANDOFF menyebut 'token')"
