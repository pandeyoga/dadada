"""ITERATION 275 — GELOMBANG 1 audit: alur Admin Sales vs dokumen training.

Cakupan (kode kasus dokumen):
  Orientasi  : desk per peran (sales_admin 8 antrean, finance 5, manajer, gudang)
  Semua-Ent  : mode "Semua Entitas" hanya-baca (aksi tulis ditolak dgn pesan menuntun)
  ALUR A     : A1 end-to-end (buat→verifikasi→setujui→konfirmasi→picking→kirim→selesai)
               A4 konfirmasi tanpa verifikasi ditolak · A6 minimum potong
  ALUR B     : B1/B2 backorder + antrean pemenuhan · B3 tiga kartu + alasan
               B-reorder → PR bertaut · B6 keputusan ulang (jejak lama tetap)
  ALUR C     : C4 kredit terblokir · C5 verifikasi tetap jalan · C1 harga khusus
               C6 approve nilai ditolak saat persetujuan menggantung
  ALUR E     : retur — pengajuan, approve HANYA manajer, antrean dokumen admin sales
  ALUR F     : PIN — antrean, sumber, konversi antar-PT (harga kontrak internal)
  Negatif    : batas wewenang Admin Sales (faktur pajak, kwitansi AR, gudang, QC)

CATATAN: tes ini AUDIT — beberapa assert sengaja longgar; deviasi dicatat di laporan.
"""
import os
import pytest
import requests


def _base():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    url = line.split("=", 1)[1].strip()
    return (url or "").rstrip("/")


BASE = _base()
PWD = "demo12345"
ENT = "ent_ksc"
CUST_OK = "cust_butik_bali"
CUST_BLOCKED = "cust_toko_kain"
ADDR = "addr_001"

STATE = {}


def _login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def T():
    who = {
        "sales": "sales@kainnusantara.id",
        "sales2": "sales2@kainnusantara.id",
        "salesadmin": "salesadmin@kainnusantara.id",
        "manager": "manager@kainnusantara.id",
        "warehouse": "warehouse@kainnusantara.id",
        "finance": "finance@kainnusantara.id",
        "admin": "admin@kainnusantara.id",
    }
    return {k: _login(v) for k, v in who.items()}


def H(tok, entity=ENT):
    h = {"Authorization": f"Bearer {tok}"}
    if entity:
        h["X-Entity-Id"] = entity
    return h


def _detail(r):
    try:
        d = r.json().get("detail")
    except Exception:
        return r.text[:300]
    return d if isinstance(d, str) else str(d)


# ═══════════════════ ORIENTASI: papan per peran ═══════════════════
class TestOrientasi:
    def test_desk_sales_admin_8_antrean(self, T):
        r = requests.get(f"{BASE}/api/sales-admin/desk", headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["desk_label"] == "Meja Admin Sales"
        qids = [q["id"] for q in d["queues"]]
        STATE["sales_admin_queues"] = qids
        assert len(qids) == 8, f"antrean={qids}"
        for q in d["queues"]:
            assert q.get("action_label"), f"antrean {q['id']} tanpa tombol tindakan"
        assert d.get("not_my_desk"), "kotak batas wewenang kosong"

    def test_desk_finance_5_antrean(self, T):
        r = requests.get(f"{BASE}/api/finance/desk", headers=H(T["finance"]), timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        STATE["finance_queues"] = [q["id"] for q in d["queues"]]
        assert len(d["queues"]) == 5, STATE["finance_queues"]

    def test_home_boards_per_role(self, T):
        got = {}
        for role, path in (("manager", "manager"),
                           ("finance", "finance"), ("warehouse", "warehouse")):
            r = requests.get(f"{BASE}/api/home/{path}", headers=H(T[role]), timeout=60)
            body = r.json() if r.status_code == 200 else {}
            got[role] = (r.status_code, str(body.get("board_label") or body.get("label")
                                            or body.get("title") or "")[:60])
        STATE["home_boards"] = got
        assert all(v[0] == 200 for v in got.values()), got

    def test_sales_admin_desk_forbidden_for_sales(self, T):
        r = requests.get(f"{BASE}/api/sales-admin/desk", headers=H(T["sales"]), timeout=30)
        assert r.status_code == 403, f"sales bisa buka Meja Admin Sales: {r.status_code}"


# ═══════════════════ MODE SEMUA ENTITAS = HANYA BACA ═══════════════════
class TestSemuaEntitas:
    def test_read_all_ok(self, T):
        r = requests.get(f"{BASE}/api/sales-orders", headers=H(T["salesadmin"], "all"), timeout=60)
        assert r.status_code == 200, r.text[:200]

    def test_write_all_rejected_with_guidance(self, T):
        payload = {"customer_id": CUST_OK, "shipping_address_id": ADDR,
                   "items": [{"product_id": "prod_lurik_classic", "quantity": 5, "unit": "yard"}]}
        r = requests.post(f"{BASE}/api/sales-orders", json=payload,
                          headers=H(T["salesadmin"], "all"), timeout=60)
        msg = _detail(r)
        STATE["all_mode_write"] = (r.status_code, msg[:200])
        assert r.status_code == 409, f"expected 409, got {r.status_code}: {msg[:200]}"
        assert "badan usaha" in msg.lower(), msg[:200]


# ═══════════════════ ALUR A ═══════════════════
def _create_so(tok, customer_id, product_id, qty, allow_backorder=False):
    payload = {"customer_id": customer_id, "shipping_address_id": ADDR, "entity_id": ENT,
               "items": [{"product_id": product_id, "quantity": qty, "unit": "yard"}],
               "allow_backorder": allow_backorder, "confirm_mixed_lot": True}
    return requests.post(f"{BASE}/api/sales-orders", json=payload, headers=H(tok), timeout=90)


class TestAlurA:
    def test_a0_sales_portfolio_visibility(self, T):
        """Dokumen menyuruh sales@ memesan untuk Butik Bali Indah."""
        r = requests.get(f"{BASE}/api/customers?limit=100", headers=H(T["sales"]), timeout=30)
        names = {c["id"] for c in r.json()}
        STATE["sales_customers"] = sorted(names)
        assert CUST_OK in names, ("DEVIASI: sales@ tidak melihat Butik Bali Indah; "
                                 f"hanya {sorted(names)}")

    def test_a1_create_so_reserved(self, T):
        r = _create_so(T["sales2"], CUST_OK, "prod_lurik_classic", 12)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:300]}"
        so = r.json()
        STATE["so_a"] = so["id"]
        STATE["so_a_number"] = so["number"]
        assert so["status"] in ("reserved", "draft"), so["status"]
        assert float(so.get("grand_total") or 0) > 0

    def test_a1_appears_in_perlu_verifikasi(self, T):
        r = requests.get(f"{BASE}/api/sales-admin/desk", headers=H(T["salesadmin"]), timeout=60)
        q = next(x for x in r.json()["queues"] if x["id"] == "perlu_verifikasi")
        assert STATE["so_a"] in [row["ref_id"] for row in q["rows"]], \
            "SO baru tidak muncul di antrean 'Perlu diverifikasi'"

    def test_a4_confirm_before_verify_rejected(self, T):
        c = _create_so(T["sales2"], CUST_OK, "prod_lurik_classic", 3)
        assert c.status_code in (200, 201), c.text[:200]
        STATE["so_a4"] = c.json()["id"]
        STATE["so_a4_number"] = c.json()["number"]
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_a4']}/confirm",
                          headers=H(T["salesadmin"]), timeout=60)
        STATE["a4"] = (r.status_code, _detail(r)[:200])
        assert r.status_code == 409, f"{r.status_code} {r.text[:250]}"
        assert "verifikasi" in _detail(r).lower()

    def test_a1_verification_checklist(self, T):
        r = requests.get(f"{BASE}/api/sales-orders/{STATE['so_a']}/verification",
                         headers=H(T["salesadmin"]), timeout=30)
        assert r.status_code == 200, r.text[:250]
        checks = r.json().get("checks") or []
        labels = " ".join(str(c.get("label", "")) + str(c.get("key", "")) for c in checks).lower()
        STATE["verif_checks"] = [c.get("key") or c.get("label") for c in checks]
        for want in ("alamat", "bayar", "ppn"):
            assert want in labels, f"daftar periksa tanpa '{want}': {STATE['verif_checks']}"

    def test_a1_verify_ok(self, T):
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_a']}/verify",
                          json={"note": "TEST_iter275 verifikasi"},
                          headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"

    def test_a1_normal_customer_should_be_credit_clean(self, T):
        """Dokumen: Butik Bali Indah = pelanggan NORMAL (bukan kasus kredit)."""
        so = requests.get(f"{BASE}/api/sales-orders/{STATE['so_a']}",
                          headers=H(T["salesadmin"]), timeout=30).json()
        kredit = [p for p in (so.get("pending_approvals") or [])
                  if p.get("type") == "kredit" and p.get("status") == "pending"]
        STATE["a1_credit_pending"] = [p.get("reason") for p in kredit]
        assert not kredit, ("DEVIASI: pelanggan 'normal' Butik Bali Indah tetap memicu "
                            f"persetujuan kredit: {STATE['a1_credit_pending']}")

    def test_a1_submit_and_manager_approve(self, T):
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_a']}/submit-for-approval",
                          headers=H(T["sales2"]), timeout=60)
        assert r.status_code == 200, f"submit: {r.status_code} {r.text[:250]}"
        assert r.json()["status"] in ("waiting_approval", "approved"), r.json()["status"]
        # manajer melihatnya di Pusat Persetujuan
        b = requests.get(f"{BASE}/api/approvals/backlog", headers=H(T["manager"]), timeout=60)
        assert b.status_code == 200, b.text[:200]
        # bereskan approval kredit yang menggantung (lihat temuan di atas)
        so = requests.get(f"{BASE}/api/sales-orders/{STATE['so_a']}",
                          headers=H(T["manager"]), timeout=30).json()
        for p in (so.get("pending_approvals") or []):
            if p.get("type") in ("kredit", "special_price") and p.get("status") == "pending":
                requests.post(f"{BASE}/api/sales-orders/{STATE['so_a']}/approvals/"
                              f"{p['id']}/decide",
                              json={"decision": "approve", "note": "TEST_iter275"},
                              headers=H(T["manager"]), timeout=60)
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_a']}/approve",
                          headers=H(T["manager"]), timeout=60)
        STATE["a1_approve"] = (r.status_code, _detail(r)[:160])
        cur = requests.get(f"{BASE}/api/sales-orders/{STATE['so_a']}",
                           headers=H(T["manager"]), timeout=30).json().get("status")
        STATE["a1_status_after_approve"] = cur
        assert cur == "approved", f"status={cur} approve={STATE['a1_approve']}"

    def test_a1_salesadmin_confirm_creates_picking(self, T):
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_a']}/confirm",
                          headers=H(T["salesadmin"]), timeout=90)
        assert r.status_code == 200, f"confirm: {r.status_code} {r.text[:300]}"
        assert r.json()["status"] in ("confirmed", "picking", "ready_to_pick"), r.json()["status"]
        t = requests.get(f"{BASE}/api/outbound/tasks?order_id={STATE['so_a']}",
                         headers=H(T["warehouse"]), timeout=60)
        assert t.status_code == 200, t.text[:250]
        items = t.json() if isinstance(t.json(), list) else t.json().get("items", [])
        mine = [x for x in items if x.get("order_id") == STATE["so_a"]]
        STATE["task_a"] = mine[0]["id"] if mine else None
        assert mine, "tugas picking gudang TIDAK lahir otomatis setelah konfirmasi"

    def test_a1_warehouse_pick_and_dispatch(self, T):
        tid = STATE.get("task_a")
        if not tid:
            pytest.skip("TIDAK-DAPAT-DIUJI: tugas picking tidak ada")
        t = requests.get(f"{BASE}/api/outbound/tasks?order_id={STATE['so_a']}",
                         headers=H(T["warehouse"]), timeout=60).json()
        rows = t if isinstance(t, list) else t.get("items", [])
        task = next(x for x in rows if x["id"] == tid)
        qty = float(task.get("expected_qty") or task.get("qty") or 0) or 12
        if task.get("status") == "scheduled":
            requests.post(f"{BASE}/api/outbound/tasks/{tid}/release",
                          headers=H(T["warehouse"]), timeout=60)
        r = requests.post(f"{BASE}/api/outbound/tasks/{tid}/scan-pick?actual_qty={qty}",
                          headers=H(T["warehouse"]), timeout=90)
        assert r.status_code == 200, f"scan-pick: {r.status_code} {r.text[:300]}"
        d = requests.post(f"{BASE}/api/outbound/tasks/{tid}/dispatch",
                          headers=H(T["warehouse"]), timeout=90)
        assert d.status_code == 200, f"dispatch: {d.status_code} {d.text[:300]}"
        STATE["shipment_no"] = (d.json().get("shipment") or {}).get("shipment_no")
        assert STATE["shipment_no"], "Surat Jalan tidak terbit"
        sj = requests.get(f"{BASE}/api/outbound/so/{STATE['so_a']}/surat-jalan",
                          headers=H(T["salesadmin"]), timeout=60)
        assert sj.status_code == 200, f"surat-jalan: {sj.status_code} {sj.text[:200]}"

    def test_a1_status_shipped_then_delivered(self, T):
        so = requests.get(f"{BASE}/api/sales-orders/{STATE['so_a']}",
                          headers=H(T["salesadmin"]), timeout=30).json()
        STATE["a1_status_after_dispatch"] = so.get("status")
        assert so.get("status") in ("shipped", "delivered", "partially_shipped"), so.get("status")
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_a']}/mark-delivered",
                          headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code == 200, f"mark-delivered: {r.status_code} {r.text[:250]}"
        STATE["a1_final_status"] = r.json().get("status")
        assert r.json().get("status") in ("delivered", "completed", "done"), \
            STATE["a1_final_status"]

    def test_a1_journey_has_stages(self, T):
        r = requests.get(f"{BASE}/api/sales-orders/{STATE['so_a']}/journey",
                         headers=H(T["salesadmin"]), timeout=30)
        assert r.status_code == 200, r.text[:200]

    def test_a6_min_cut_rule(self, T):
        """A6 — qty di bawah minimum potong harus ditolak dengan angka minimum."""
        r = requests.get(f"{BASE}/api/products?limit=200", headers=H(T["admin"]), timeout=30)
        prods = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        withmin = [p for p in prods
                   if float(p.get("min_cut_length") or p.get("min_cut") or 0) > 0]
        if not withmin:
            # cek detail satu produk (mungkin field hanya ada di detail)
            d = requests.get(f"{BASE}/api/products/{prods[0]['id']}",
                             headers=H(T["admin"]), timeout=30).json()
            STATE["min_cut_fields"] = {k: v for k, v in d.items() if "min" in k.lower()}
            pytest.skip(f"TIDAK-DAPAT-DIUJI: tak ada produk ber-minimum potong; "
                        f"field min pada detail: {STATE['min_cut_fields']}")
        p = withmin[0]
        minv = float(p.get("min_cut_length") or p.get("min_cut"))
        r = _create_so(T["sales2"], CUST_OK, p["id"], max(minv - 1, 0.5))
        STATE["a6"] = (r.status_code, _detail(r)[:200])
        assert r.status_code == 400, f"{r.status_code} {_detail(r)[:200]}"
        assert str(int(minv)) in _detail(r)


# ═══════════════════ ALUR B ═══════════════════
class TestAlurB:
    def test_b1_backorder_created(self, T):
        r = requests.get(f"{BASE}/api/stock/buckets", headers=H(T["admin"]), timeout=60)
        rows = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        pick = next((x for x in rows
                     if float((x.get("totals") or {}).get("available_qty") or 0) > 0
                     and x.get("product_id") == "prod_songket_palembang"), None) or rows[0]
        avail = float((pick.get("totals") or {}).get("available_qty") or 0)
        pid = pick["product_id"]
        r = _create_so(T["sales2"], CUST_OK, pid, avail + 50, allow_backorder=True)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:300]}"
        so = r.json()
        STATE["so_b"] = so["id"]
        STATE["so_b_number"] = so["number"]
        assert so["status"] in ("waiting_stock", "reserved"), so["status"]
        line = so["items"][0]
        assert float(line.get("backorder_qty") or 0) > 0, \
            f"tidak ada backorder_qty pada baris: {list(line.keys())}"

    def test_b2_queue_perlu_dipenuhi(self, T):
        r = requests.get(f"{BASE}/api/sales-admin/desk", headers=H(T["salesadmin"]), timeout=90)
        q = next(x for x in r.json()["queues"] if x["id"] == "perlu_dipenuhi")
        assert q["action_label"] == "Putuskan pemenuhan", q["action_label"]
        assert STATE["so_b"] in [row["ref_id"] for row in q["rows"]], \
            "SO kurang stok tidak masuk antrean 'Perlu dipenuhi (kurang stok)'"

    def test_b3_three_options_with_reasons(self, T):
        r = requests.get(f"{BASE}/api/sales-admin/orders/{STATE['so_b']}/fulfillment",
                         headers=H(T["salesadmin"]), timeout=90)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        opts = d.get("options") or {}
        STATE["b3_modes"] = sorted(opts.keys())
        assert set(opts.keys()) == {"interco", "reorder", "wait"}, STATE["b3_modes"]
        assert d.get("shortages"), "tabel kekurangan kosong"
        bad = []
        for mode, o in opts.items():
            ok = o.get("available", o.get("eligible", True))
            if not ok and not (o.get("reason") or "").strip():
                bad.append(mode)
        STATE["b3_ineligible"] = [(m, o.get("reason"))
                                  for m, o in opts.items()
                                  if not o.get("available", True)]
        assert not bad, f"kartu tak layak TANPA alasan: {bad}"

    def test_b_reorder_creates_pr(self, T):
        r = requests.post(f"{BASE}/api/sales-admin/orders/{STATE['so_b']}/fulfillment-decision",
                          json={"mode": "reorder", "note": "TEST_iter275 reorder ke supplier"},
                          headers=H(T["salesadmin"]), timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        dec = r.json()["decision"]
        STATE["pr_ref"] = dec.get("ref_number") or dec.get("ref_id")
        assert STATE["pr_ref"], f"keputusan tanpa dokumen PR: {dec}"

    def test_b_pr_visible_in_manager_queue(self, T):
        r = requests.get(f"{BASE}/api/purchase-requisitions?limit=100",
                         headers=H(T["manager"]), timeout=60)
        assert r.status_code == 200, r.text[:250]
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        hit = [p for p in items
               if STATE["pr_ref"] in (p.get("number", ""), p.get("id", ""))
               or STATE["so_b_number"] in str(p.get("source_order_number") or p.get("notes") or "")
               or STATE["so_b"] == p.get("source_order_id")]
        STATE["pr_linked"] = bool(hit)
        assert hit, f"PR {STATE['pr_ref']} tak ditemukan/tak bertaut SO di antrean manajer"

    def test_b6_reopen_shows_existing_decision(self, T):
        r = requests.get(f"{BASE}/api/sales-admin/orders/{STATE['so_b']}/fulfillment",
                         headers=H(T["salesadmin"]), timeout=90)
        assert r.status_code == 200, r.text[:250]
        d = r.json()
        dec = d.get("existing_decision") or d.get("decision") or d.get("last_decision")
        STATE["b6"] = dec
        assert dec, f"tak ada info 'Sudah ada keputusan'; kunci: {list(d.keys())}"
        assert (dec.get("decided_by") or dec.get("by") or dec.get("actor")), \
            f"keputusan tanpa nama pemutus: {dec}"

    def test_b6_redecide_allowed(self, T):
        """B6 — memutuskan ulang harus DIPERBOLEHKAN."""
        g = requests.get(f"{BASE}/api/sales-admin/orders/{STATE['so_b']}/fulfillment",
                         headers=H(T["salesadmin"]), timeout=90).json()
        avail = [m for m, o in (g.get("options") or {}).items() if o.get("available")]
        STATE["b6_available_modes"] = avail
        tried = {}
        for mode in ("reorder", "wait", "interco"):
            r = requests.post(
                f"{BASE}/api/sales-admin/orders/{STATE['so_b']}/fulfillment-decision",
                json={"mode": mode, "note": "TEST_iter275 keputusan ulang"},
                headers=H(T["salesadmin"]), timeout=90)
            tried[mode] = (r.status_code, _detail(r)[:140])
            if r.status_code == 200:
                break
        STATE["b6_redecide"] = tried
        assert any(v[0] == 200 for v in tried.values()), \
            f"DEVIASI: keputusan ulang DITOLAK di semua jalur: {tried}"

    def test_b6_history_trail_kept(self, T):
        g = requests.get(f"{BASE}/api/sales-admin/orders/{STATE['so_b']}/fulfillment",
                         headers=H(T["salesadmin"]), timeout=90).json()
        hist = g.get("decisions") or g.get("decision_history") or []
        STATE["b6_history_len"] = len(hist)
        assert len(hist) >= 2, \
            f"jejak keputusan lama tidak terekspos API (n={len(hist)}, kunci={list(g.keys())})"


# ═══════════════════ ALUR C ═══════════════════
class TestAlurC:
    def test_c4_blocked_customer_goes_to_approval(self, T):
        r = _create_so(T["sales"], CUST_BLOCKED, "prod_lurik_classic", 8)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:300]}"
        so = r.json()
        STATE["so_c"] = so["id"]
        pa = so.get("pending_approvals") or []
        kinds = [p.get("type") for p in pa]
        STATE["c4_pending"] = kinds
        assert "kredit" in kinds, f"tidak ada persetujuan kredit: {kinds} status={so['status']}"

    def test_c4_status_waiting_approval(self, T):
        r = requests.get(f"{BASE}/api/sales-orders/{STATE['so_c']}", headers=H(T["salesadmin"]),
                         timeout=30)
        so = r.json()
        STATE["c4_status"] = so.get("status")
        assert so.get("status") in ("waiting_approval", "reserved"), so.get("status")

    def test_c5_verification_still_possible(self, T):
        pv = requests.get(f"{BASE}/api/sales-orders/{STATE['so_c']}/verification",
                          headers=H(T["salesadmin"]), timeout=30).json()
        blocking = [c for c in (pv.get("checks") or [])
                    if "kredit" in str(c.get("label", "")).lower() and c.get("blocking")]
        STATE["c5_credit_blocking"] = blocking
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_c']}/verify",
                          json={"note": "TEST_iter275 C5"}, headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code == 200, f"verifikasi terhalang kredit: {r.status_code} {r.text[:250]}"
        assert not blocking, f"baris kredit ditandai menghalangi: {blocking}"

    def test_c1_request_special_price(self, T):
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_c']}/request-special-price",
                          json={"item_index": 0, "requested_price": 50000,
                                "reason": "TEST_iter275 negosiasi pelanggan"},
                          headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        pa = [p for p in r.json().get("pending_approvals") or []
              if p.get("type") == "special_price" and p.get("status") == "pending"]
        assert pa, "pengajuan harga khusus tidak tercatat"
        STATE["appr_price_id"] = pa[0].get("id")
        STATE["pra_id"] = pa[0].get("ref_id")

    def test_c6_approve_value_blocked_while_pending(self, T):
        requests.post(f"{BASE}/api/sales-orders/{STATE['so_c']}/submit-for-approval",
                      headers=H(T["sales"]), timeout=60)
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_c']}/approve",
                          headers=H(T["manager"]), timeout=60)
        STATE["c6"] = (r.status_code, _detail(r)[:250])
        assert r.status_code == 409, f"{r.status_code} {_detail(r)[:250]}"
        assert "menunggu keputusan" in _detail(r).lower(), _detail(r)[:250]

    def test_c1_manager_sees_price_approval_queue(self, T):
        r = requests.get(f"{BASE}/api/price-approvals?status=pending",
                         headers=H(T["manager"]), timeout=60)
        assert r.status_code == 200, r.text[:250]
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        assert any(p.get("id") == STATE.get("pra_id") for p in items), \
            "pengajuan harga khusus tak muncul di tab Persetujuan Harga manajer"

    def test_c1_manager_approves_price(self, T):
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_c']}/approvals/"
                          f"{STATE['appr_price_id']}/decide",
                          json={"decision": "approve", "note": "TEST_iter275 setuju"},
                          headers=H(T["manager"]), timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"

    def test_c_salesadmin_cannot_decide_approval(self, T):
        r = requests.post(f"{BASE}/api/sales-orders/{STATE['so_c']}/approvals/"
                          f"{STATE['appr_price_id']}/decide",
                          json={"decision": "approve", "note": "TEST_iter275"},
                          headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code in (403, 409), f"admin sales bisa memutuskan approval: {r.status_code}"


# ═══════════════════ ALUR E — RETUR ═══════════════════
class TestAlurE:
    def test_e_demo_returns_exist(self, T):
        r = requests.get(f"{BASE}/api/sales-returns?limit=100", headers=H(T["salesadmin"]),
                         timeout=60)
        assert r.status_code == 200, r.text[:250]
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        STATE["returns"] = [(x["id"], x.get("number"), x.get("status")) for x in items]
        assert items, "tidak ada retur demo di DB"

    def test_e_queue_retur_in_desk(self, T):
        r = requests.get(f"{BASE}/api/sales-admin/desk", headers=H(T["salesadmin"]), timeout=90)
        q = next((x for x in r.json()["queues"] if x["id"] == "retur"), None)
        assert q is not None, "antrean 'Retur menunggu proses dokumen' hilang"
        STATE["retur_queue_count"] = q["count"]

    def test_e_salesadmin_cannot_approve_return(self, T):
        cand = [x for x in STATE["returns"]
                if x[2] in ("submitted", "pending", "draft", "requested",
                            "pending_approval")]
        if not cand:
            pytest.skip("TIDAK-DAPAT-DIUJI: tak ada retur berstatus submitted/draft")
        rid = cand[0][0]
        STATE["ret_id"] = rid
        r = requests.post(f"{BASE}/api/sales-returns/{rid}/approve", json={"note": "TEST_iter275"},
                          headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code == 403, f"admin sales BISA setujui retur: {r.status_code} {r.text[:200]}"

    def test_e_manager_approves_return(self, T):
        rid = STATE.get("ret_id")
        if not rid:
            pytest.skip("TIDAK-DAPAT-DIUJI: tak ada retur yang bisa disetujui")
        st = requests.get(f"{BASE}/api/sales-returns/{rid}", headers=H(T["manager"]),
                          timeout=30).json().get("status")
        if st == "draft":
            requests.post(f"{BASE}/api/sales-returns/{rid}/submit", headers=H(T["sales"]),
                          timeout=60)
        r = requests.post(f"{BASE}/api/sales-returns/{rid}/approve", json={"note": "TEST_iter275"},
                          headers=H(T["manager"]), timeout=60)
        STATE["e_approve"] = (r.status_code, _detail(r)[:200])
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"

    def test_e_reject_requires_reason(self, T):
        cand = [x for x in STATE["returns"]
                if x[2] in ("submitted", "pending", "pending_approval")
                and x[0] != STATE.get("ret_id")]
        if not cand:
            pytest.skip("TIDAK-DAPAT-DIUJI: tak ada retur lain untuk uji alasan wajib")
        r = requests.post(f"{BASE}/api/sales-returns/{cand[0][0]}/reject", json={"reason": ""},
                          headers=H(T["manager"]), timeout=60)
        assert r.status_code in (400, 422), f"tolak retur tanpa alasan diterima: {r.status_code}"


# ═══════════════════ ALUR F — PIN ANTAR-PT ═══════════════════
class TestAlurF:
    def test_f_pin_list_and_queue(self, T):
        r = requests.get(f"{BASE}/api/internal-requests?limit=100", headers=H(T["salesadmin"]),
                         timeout=60)
        assert r.status_code == 200, r.text[:250]
        items = r.json().get("items", r.json() if isinstance(r.json(), list) else [])
        dk = requests.get(f"{BASE}/api/sales-admin/desk", headers=H(T["salesadmin"]),
                          timeout=90).json()
        q = next(x for x in dk["queues"] if x["id"] == "permintaan_internal")
        STATE["pin_queue_rows"] = [(row["ref_id"], row["number"]) for row in q["rows"]]
        STATE["pins_visible_to_salesadmin"] = [(x["id"], x.get("status")) for x in items]
        meta = requests.get(f"{BASE}/api/internal-requests/meta",
                            headers=H(T["salesadmin"]), timeout=30).json()
        STATE["pin_meta_salesadmin"] = {k: meta.get(k)
                                        for k in ("can_decide", "can_pick_source")}
        assert items, ("DEVIASI: daftar Permintaan Internal KOSONG untuk Admin Sales "
                       f"walau antrean meja berisi {STATE['pin_queue_rows']}")

    def test_f_sources_for_open_pin(self, T):
        open_pins = [(rid, num, "submitted") for rid, num in STATE.get("pin_queue_rows", [])]
        if not open_pins:
            pytest.skip("TIDAK-DAPAT-DIUJI: antrean PIN kosong")
        STATE["pin_id"] = open_pins[0][0]
        r = requests.get(f"{BASE}/api/internal-requests/{STATE['pin_id']}/sources",
                         headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:250]}"
        cands = r.json().get("candidates") or r.json().get("sources") or []
        STATE["pin_sources"] = [(c.get("entity_id"), c.get("enough", c.get("available_qty")))
                                for c in cands]
        assert cands, "tak ada kandidat badan usaha sumber"

    def test_f_sales_cannot_see_sources(self, T):
        if not STATE.get("pin_id"):
            pytest.skip("TIDAK-DAPAT-DIUJI")
        r = requests.get(f"{BASE}/api/internal-requests/{STATE['pin_id']}/sources",
                         headers=H(T["sales"]), timeout=30)
        assert r.status_code == 403, r.status_code

    def test_f_convert_to_interco(self, T):
        if not STATE.get("pin_id"):
            pytest.skip("TIDAK-DAPAT-DIUJI: tak ada PIN terbuka")
        src = (STATE["pin_sources"][0][0] if STATE.get("pin_sources") else "")
        r = requests.post(f"{BASE}/api/internal-requests/{STATE['pin_id']}/convert",
                          json={"source_entity_id": src, "submit_now": True,
                                "notes": "TEST_iter275"},
                          headers=H(T["salesadmin"]), timeout=90)
        STATE["f_convert"] = (r.status_code, _detail(r)[:250])
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        interco = r.json().get("interco") or {}
        STATE["interco_id"] = interco.get("id")
        assert interco.get("pair_id") or interco.get("id"), f"transaksi antar-PT tak lahir: {interco}"

    def test_f_pricing_uses_internal_contract(self, T):
        if not STATE.get("interco_id"):
            pytest.skip("TIDAK-DAPAT-DIUJI: konversi PIN gagal")
        r = requests.get(f"{BASE}/api/interco/transactions/{STATE['interco_id']}",
                         headers=H(T["salesadmin"]), timeout=60)
        if r.status_code != 200:
            r = requests.get(f"{BASE}/api/interco/{STATE['interco_id']}",
                             headers=H(T["salesadmin"]), timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        d = r.json()
        basis = str(d.get("pricing_mode") or d.get("price_basis")
                    or (d.get("items") or [{}])[0].get("price_basis") or "").lower()
        STATE["f_pricing_basis"] = basis
        assert basis and "jual" not in basis, f"basis harga bukan kontrak internal: {basis!r}"


# ═══════════════════ NEGATIF — BATAS WEWENANG ADMIN SALES ═══════════════════
class TestBatasWewenang:
    def test_no_tax_invoice_issue(self, T):
        r = requests.post(f"{BASE}/api/tax-invoices", json={"order_id": STATE.get("so_a", "x")},
                          headers=H(T["salesadmin"]), timeout=30)
        assert r.status_code in (403, 404, 405), f"admin sales bisa terbitkan faktur: {r.status_code}"

    def test_no_ar_receipt(self, T):
        r = requests.post(f"{BASE}/api/ar-receipts", json={"amount": 1000},
                          headers=H(T["salesadmin"]), timeout=30)
        STATE["ar_receipt_status"] = (r.status_code, _detail(r)[:120])
        assert r.status_code in (403, 404, 405, 422), f"{r.status_code} {r.text[:150]}"

    def test_no_warehouse_action(self, T):
        if not STATE.get("task_a"):
            pytest.skip("TIDAK-DAPAT-DIUJI: tak ada tugas picking")
        r = requests.post(f"{BASE}/api/outbound/tasks/{STATE['task_a']}/start",
                          headers=H(T["salesadmin"]), timeout=30)
        assert r.status_code in (403, 404, 405), f"admin sales bisa aksi gudang: {r.status_code}"

    def test_no_qc_release(self, T):
        r = requests.get(f"{BASE}/api/qc-inspections?limit=20", headers=H(T["salesadmin"]),
                         timeout=30)
        items = [] if r.status_code != 200 else (
            r.json() if isinstance(r.json(), list) else r.json().get("items", []))
        if not items:
            pytest.skip(f"TIDAK-DAPAT-DIUJI: daftar QC {r.status_code}/kosong")
        r = requests.post(f"{BASE}/api/qc-inspections/{items[0]['id']}/release",
                          json={}, headers=H(T["salesadmin"]), timeout=30)
        assert r.status_code in (403, 404, 405), r.status_code


def test_zz_dump_state():
    print("\n=== STATE iter275 ===")
    for k, v in STATE.items():
        print(f"{k}: {v}")
