"""Regresi G-B (1/3) — mesin status & konkurensi: permintaan material, retur GRN, batal PO, transfer stok,
pemakaian vs RAB, dan jalur indeks-unik (audit PK3-18, PK3-22, FZ-06, PG-04, PG-05, PG-06, PG-21).

    API_BASE=http://localhost:8072/api python -m pytest backend/tests/p0/test_p0_status_konkurensi.py -n 0 -q --noconftest

Tiap tes membuat datanya sendiri (material/PO/proyek baru) dan menembakkan permintaan SERENTAK (`race`).
Balapan diulang beberapa putaran supaya kode lama tidak lolos hanya karena urutan kebetulan.
"""
import uuid

import pytest

from test_p0_masuk import FINANCE, OWNER, World, call, codes, ok, race

ROUNDS = 4


def _uid(p="G"):
    return f"{p}{uuid.uuid4().hex[:6].upper()}"


@pytest.fixture(scope="module")
def world():
    return World()


def _material(world, name, stock=100, project_id=None, budget=0):
    pid = project_id or world.project_id
    body = {"project_id": pid, "name": f"{name} {_uid()}", "uom": "sak"}
    mid = ok(call(OWNER, "POST", "/materials", json=body))["data"]["id"]
    if budget:
        ok(call(OWNER, "PUT", f"/materials/{mid}/budget", json={"budget_qty": budget}))
    if stock:
        ok(call(OWNER, "POST", "/materials/txn", json={
            "project_id": pid, "material_id": mid, "type": "in", "qty": stock, "note": "G-B stok awal"}))
    return mid


def _stock(project_id, mid):
    rows = ok(call(OWNER, "GET", f"/materials/project/{project_id}"))["data"]
    return round(float([m for m in rows if m["id"] == mid][0]["stock"]), 2)


def _req(world, mid, qty, approve=True):
    r = ok(call(OWNER, "POST", "/materials/requisitions", json={
        "project_id": world.project_id, "items": [{"material_id": mid, "qty": qty}], "purpose": "G-B uji"}))["data"]
    if approve:
        ok(call(OWNER, "POST", f"/materials/requisitions/{r['id']}/approve"))
    return r["id"]


def _req_get(rid):
    return ok(call(OWNER, "GET", f"/materials/requisitions/{rid}"))["data"]


def _po_grn(world, mid, qty=100, price=55_000, recv=None):
    po = ok(call(FINANCE, "POST", "/procurement/pos", json={
        "project_id": world.project_id, "po_type": "material", "vendor": f"Vendor G-B {_uid()}",
        "items": [{"description": "Semen G-B", "material_id": mid, "uom": "sak", "qty": qty,
                   "unit_price": price}]}))["data"]
    ok(call(OWNER, "POST", f"/procurement/pos/{po['id']}/approve", json={}))
    grn = ok(call(OWNER, "POST", "/procurement/grns", json={
        "po_id": po["id"], "items": [{"po_item_index": 0, "qty_received": recv or qty}]}))["data"]
    return po["id"], grn


def _po(pid):
    return ok(call(OWNER, "GET", f"/procurement/pos/{pid}"))


def _retur(grn_id, qty, idx=0):
    return call(OWNER, "POST", "/procurement/returns", json={
        "grn_id": grn_id, "kind": "rusak", "reason": "barang rusak saat uji G-B",
        "items": [{"grn_item_index": idx, "qty_returned": qty}]})


# ================================================================== PK3-18 — permintaan material
def test_permintaan_setuju_ganda_satu_pemenang(world):
    for _ in range(ROUNDS):
        mid = _material(world, "G-B Setuju")
        rid = _req(world, mid, 10, approve=False)
        rs = race([lambda: call(OWNER, "POST", f"/materials/requisitions/{rid}/approve") for _ in range(2)])
        assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, \
            [(r.status_code, r.text[:120]) for r in rs]    # yang kalah: 409 (balapan) atau 400 (membaca sesudah menang)


def test_permintaan_setuju_vs_tolak_tidak_menghasilkan_status_campur(world):
    """Dulu: status akhir `approved` tetapi `rejected_by` juga terisi (kedua aksi 200)."""
    for _ in range(ROUNDS * 2):
        mid = _material(world, "G-B SetujuTolak")
        rid = _req(world, mid, 10, approve=False)
        rs = race([lambda: call(OWNER, "POST", f"/materials/requisitions/{rid}/approve"),
                   lambda: call(OWNER, "POST", f"/materials/requisitions/{rid}/reject", json={"note": "uji tolak"})])
        r = _req_get(rid)
        assert not (r["status"] == "approved" and r.get("rejected_by")), (r["status"], r.get("rejected_by"))
        assert not (r["status"] == "rejected" and not r.get("rejected_by"))
        assert not (codes(rs) == [200, 200] and r["status"] == "approved")


def test_permintaan_keluarkan_ganda_stok_tidak_negatif(world):
    mid = _material(world, "G-B Keluar", stock=300)
    rid = _req(world, mid, 300)
    rs = race([lambda: call(OWNER, "POST", f"/materials/requisitions/{rid}/issue", json={}) for _ in range(2)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:140]) for r in rs]
    assert all(c in (200, 400, 409) for c in codes(rs))
    assert _stock(world.project_id, mid) == 0, "stok harus 300−300=0 (dulu −300: dikeluarkan dua kali)"
    assert _req_get(rid)["status"] == "issued"


def test_permintaan_keluarkan_vs_tolak_eksklusif(world):
    for _ in range(ROUNDS):
        mid = _material(world, "G-B KeluarTolak", stock=50)
        rid = _req(world, mid, 50)
        rs = race([lambda: call(OWNER, "POST", f"/materials/requisitions/{rid}/issue", json={}),
                   lambda: call(OWNER, "POST", f"/materials/requisitions/{rid}/reject", json={"note": "uji"})])
        assert codes(rs).count(200) == 1, [(r.status_code, r.text[:140]) for r in rs]
        r = _req_get(rid)
        stock = _stock(world.project_id, mid)
        if r["status"] == "issued":
            assert stock == 0 and not r.get("rejected_by")
        else:
            assert r["status"] == "rejected" and stock == 50, "ditolak → stok tidak boleh berkurang"


# ================================================================== FZ-06 / PG-04 / PG-05 — retur GRN
def test_retur_serentak_tidak_melebihi_penerimaan(world):
    mid = _material(world, "G-B Retur", stock=0)
    _, grn = _po_grn(world, mid, qty=100)
    rs = race([lambda: _retur(grn["id"], 100) for _ in range(2)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:140]) for r in rs]
    assert all(c in (200, 400, 409) for c in codes(rs))
    assert _stock(world.project_id, mid) == 0, "stok = 100 diterima − 100 diretur (dulu −100)"
    g = [g for g in ok(call(OWNER, "GET", "/procurement/grns", params={"po_id": grn["po_id"]}))["data"]][0]
    assert g["items"][0]["returned_qty"] == 100


def test_retur_melebihi_stok_ditolak(world):
    """PG-05: 100 diterima, 90 sudah dipakai → stok 10; retur 30 harus ditolak (dulu 200, stok −20)."""
    mid = _material(world, "G-B ReturStok", stock=0)
    _, grn = _po_grn(world, mid, qty=100)
    ok(call(OWNER, "POST", "/materials/txn", json={
        "project_id": world.project_id, "material_id": mid, "type": "out", "qty": 90, "note": "dipakai"}))
    r = _retur(grn["id"], 30)
    assert r.status_code == 400 and "tidak cukup" in r.text, (r.status_code, r.text[:200])
    assert _retur(grn["id"], 10).status_code == 200
    assert _stock(world.project_id, mid) == 0


def test_batal_po_setelah_penerimaan_ditolak_dan_retur_tidak_menghidupkan_po_batal(world):
    """PG-06 + PG-05: PO yang sudah menerima barang tidak boleh dibatalkan; PO batal tidak bisa 'dihidupkan' retur."""
    mid = _material(world, "G-B BatalPO", stock=0)
    pid, grn = _po_grn(world, mid, qty=100, recv=60)          # diterima sebagian → `partially_received`
    c = call(OWNER, "POST", f"/procurement/pos/{pid}/cancel", json={})
    assert c.status_code == 400, (c.status_code, c.text[:200])
    assert _po(pid)["data"]["status"] == "partially_received"
    # bila (data lama) PO terlanjur batal, retur tidak boleh menghidupkannya kembali
    r = _retur(grn["id"], 5)
    assert _po(pid)["data"]["status"] != "cancelled" or r.status_code == 400
    assert _po(pid)["data"]["status"] != "partially_received" or r.status_code == 200


def test_batal_po_dengan_tagihan_aktif_ditolak(world):
    mid = _material(world, "G-B BatalTagihan", stock=0)
    pid, _ = _po_grn(world, mid, qty=10, price=100_000, recv=5)
    ok(call(FINANCE, "POST", "/procurement/bills", json={"po_id": pid, "claimed": 500_000, "retention_pct": 0}))
    c = call(OWNER, "POST", f"/procurement/pos/{pid}/cancel", json={})
    assert c.status_code == 400, (c.status_code, c.text[:200])


def test_batal_po_vs_setuju_eksklusif(world):
    """PK3-18: batal ‖ setuju pada PO draft → satu pemenang. (Batal SESUDAH setuju selesai adalah urutan sah —
    `approved → cancelled` — sehingga hasil 2×200 hanya boleh muncul sesekali karena jitter; kode lama selalu
    menimpa tanpa syarat, jadi 2×200 + `cancelled` berisi `approved_by` muncul di ±separuh putaran.)"""
    both = 0
    for _ in range(12):
        po = ok(call(FINANCE, "POST", "/procurement/pos", json={
            "project_id": world.project_id, "po_type": "general", "vendor": f"Vendor BS {_uid()}",
            "items": [{"description": "Barang BS", "uom": "pcs", "qty": 1, "unit_price": 1_000_000}]}))["data"]
        rs = race([lambda: call(OWNER, "POST", f"/procurement/pos/{po['id']}/cancel", json={}),
                   lambda: call(OWNER, "POST", f"/procurement/pos/{po['id']}/approve", json={})])
        d = _po(po["id"])["data"]
        assert 500 not in codes(rs)
        if codes(rs).count(200) == 2:
            both += 1
            continue
        assert codes(rs).count(200) == 1, [(r.status_code, r.text[:140]) for r in rs]
        assert not (d["status"] == "cancelled" and d.get("approved_by")), d["status"]
    assert both <= 1, f"{both} dari 12 putaran sama-sama sukses (batal menimpa setuju)"


# ================================================================== PG-04 — transfer antar proyek
def test_transfer_paralel_tidak_membuat_stok_negatif(world):
    """Stok 100, empat transfer @40 serentak → paling banyak dua yang sah (stok sisa 20), tidak pernah negatif."""
    dst = ok(call(OWNER, "POST", "/projects", json={"name": f"G-B Tujuan {_uid()}", "location": "uji"}))["data"]["id"]
    for _ in range(ROUNDS + 2):
        mid = _material(world, "G-B Transfer", stock=100)
        body = {"from_project_id": world.project_id, "to_project_id": dst, "material_id": mid, "qty": 40,
                "reason": "pindah stok uji G-B"}
        rs = race([lambda: call(OWNER, "POST", "/materials/transfers", json=body) for _ in range(4)])
        assert codes(rs).count(200) == 2, [(r.status_code, r.text[:140]) for r in rs]
        assert _stock(world.project_id, mid) == 20, "stok asal = 100 − 2×40 (dulu bisa negatif)"


# ================================================================== PG-21 — pemakaian vs RAB
def test_pemakaian_vs_rab_tidak_menghitung_transfer(world):
    dst = ok(call(OWNER, "POST", "/projects", json={"name": f"G-B Tujuan2 {_uid()}", "location": "uji"}))["data"]["id"]
    mid = _material(world, "G-B RAB", stock=100, budget=50)
    ok(call(OWNER, "POST", "/materials/transfers", json={
        "from_project_id": world.project_id, "to_project_id": dst, "material_id": mid, "qty": 80,
        "reason": "pindah stok uji RAB"}))
    ok(call(OWNER, "POST", "/materials/txn", json={
        "project_id": world.project_id, "material_id": mid, "type": "out", "qty": 10, "note": "dipakai"}))
    bud = [b for b in ok(call(OWNER, "GET", f"/materials/project/{world.project_id}/budget"))["data"]
           if b["material_id"] == mid][0]
    lst = [m for m in ok(call(OWNER, "GET", f"/materials/project/{world.project_id}"))["data"] if m["id"] == mid][0]
    assert bud["consumed_qty"] == 10 and bud["over_budget"] is False, bud
    assert lst["consumed_qty"] == 10 and lst["over_budget"] is False, (lst["consumed_qty"], lst["over_budget"])


# ================================================================== PK3-22 — indeks unik: 409, bukan 500
def test_jalur_indeks_unik_menjawab_409_bukan_500(world):
    """Pembuatan unit dengan kode sama serentak: satu menang; yang kalah 400/409 — TIDAK PERNAH 500."""
    for _ in range(ROUNDS):
        prefix = _uid("U")
        body = {"prefix": prefix, "count": 1, "type": "Tipe 36", "price": 300_000_000, "start_index": 1}
        rs = race([lambda: call(OWNER, "POST", f"/projects/{world.project_id}/units", json=body) for _ in range(3)])
        assert 500 not in codes(rs), [(r.status_code, r.text[:160]) for r in rs]
        made = sum(r.json()["data"]["count"] for r in rs if r.status_code == 200)
        assert made == 1, "tepat satu unit tercipta"


def test_nomor_grn_tidak_hangus_saat_kalah_balapan(world):
    """Lima GRN serentak atas PO yang sama: satu menang, empat 409. Nomor GRN berikutnya harus langsung
    menyambung (dulu nomor diambil SEBELUM klaim PO, jadi yang kalah menghanguskan nomor)."""
    def new_po():
        mid = _material(world, "G-B Nomor", stock=0)
        po = ok(call(FINANCE, "POST", "/procurement/pos", json={
            "project_id": world.project_id, "po_type": "material", "vendor": f"Vendor NO {_uid()}",
            "items": [{"description": "Semen NO", "material_id": mid, "uom": "sak", "qty": 100,
                       "unit_price": 55_000}]}))["data"]
        ok(call(OWNER, "POST", f"/procurement/pos/{po['id']}/approve", json={}))
        return {"po_id": po["id"], "items": [{"po_item_index": 0, "qty_received": 100}]}

    def num(r):
        return int(r.json()["data"]["grn_number"].split("/")[-1])

    for _ in range(3):
        body = new_po()
        rs = race([lambda: call(OWNER, "POST", "/procurement/grns", json=body) for _ in range(5)])
        assert codes(rs).count(200) == 1, [(r.status_code, r.text[:100]) for r in rs]
        winner = num([r for r in rs if r.status_code == 200][0])
        nxt = call(OWNER, "POST", "/procurement/grns", json=new_po())
        assert num(ok_resp(nxt)) == winner + 1, "ada nomor GRN yang hangus karena kalah balapan"


def ok_resp(r):
    assert r.status_code == 200, (r.status_code, r.text[:200])
    return r
