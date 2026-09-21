"""ITERATION 276 — GELOMBANG 2 audit alur MD vs dokumen training.

Cakupan kode kasus:
  ALUR G (reorder→PR→PO, revisi/amandemen)      : G1..G7
  ALUR H (Papan PO per lini + pagar lini)        : H1..H6
  ALUR I (R&D spesifikasi & sample)              : I1..I7
  ALUR J (Permintaan Desain / DSR)               : J1..J6
  ALUR K (Inspeksi QC)                           : K1..K7
  ALUR L (Makloon)                               : L1..L6
  ALUR D (Pesanan khusus / OD)                   : D1..D5
  Pusat Persetujuan + DATA DEMO bab 33           : PP1, DD1..DD4

CATATAN: tes ini AUDIT — kegagalan = deviasi terhadap dokumen, bukan tes rusak.
Jalankan: python -m pytest tests/test_iter276_g2_md_audit.py -p no:randomly -n 0 -q -s
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
STATE = {}


def _login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=60)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def T():
    who = {
        "manager": "manager@kainnusantara.id",
        "mgrprint": "manager.printing@kainnusantara.id",
        "designer": "designer@kainnusantara.id",
        "warehouse": "warehouse@kainnusantara.id",
        "sales": "sales@kainnusantara.id",
        "sales2": "sales2@kainnusantara.id",
        "admin": "admin@kainnusantara.id",
    }
    return {k: _login(v) for k, v in who.items()}


def H(tok, entity=ENT):
    h = {"Authorization": f"Bearer {tok}"}
    if entity:
        h["X-Entity-Id"] = entity
    return h


def D(r):
    try:
        d = r.json().get("detail")
    except Exception:
        return r.text[:300]
    return d if isinstance(d, str) else str(d)[:400]


def GET(tok, path, **kw):
    return requests.get(f"{BASE}{path}", headers=H(tok, kw.pop("entity", ENT)), timeout=90, **kw)


def POST(tok, path, body=None, **kw):
    return requests.post(f"{BASE}{path}", headers=H(tok, kw.pop("entity", ENT)),
                         json=body or {}, timeout=90, **kw)


def PATCH(tok, path, body=None, **kw):
    return requests.patch(f"{BASE}{path}", headers=H(tok, kw.pop("entity", ENT)),
                          json=body or {}, timeout=90, **kw)


# ═══════════════════════ ALUR G — Reorder → PR → PO ═══════════════════════
class TestAlurG:
    def test_G1_saran_reorder_menghitung_stok_menipis(self, T):
        r = GET(T["manager"], "/api/purchase-requisitions/reorder-suggestions")
        assert r.status_code == 200, D(r)
        items = r.json().get("items", r.json() if isinstance(r.json(), list) else [])
        assert items, "tidak ada saran reorder"
        row = items[0]
        for k in ("product_id", "available", "reorder_point", "suggested_qty"):
            assert k in row, f"kolom {k} tidak ada di saran"
        assert row["available"] <= row["reorder_point"], "saran memuat barang yang tidak menipis"
        assert row["suggested_qty"] > 0
        STATE["sugg"] = row
        print(f"G1 saran={len(items)} contoh={row['sku']} avail={row['available']} "
              f"rop={row['reorder_point']} usul={row['suggested_qty']}")

    def test_G2_buat_pr_dari_saran(self, T):
        sugg = GET(T["manager"], "/api/purchase-requisitions/reorder-suggestions").json()["items"]
        rejected = []
        r = None
        for s in sugg:
            body = {"items": [{"product_id": s["product_id"], "quantity": s["suggested_qty"],
                               "unit": s.get("unit", ""),
                               "notes": "TEST_iter276 dari saran reorder"}],
                    "entity_id": ENT, "source": "reorder", "warehouse_id": "wh_jakarta",
                    "reason": "TEST_iter276 audit alur G reorder", "submit_now": True}
            r = POST(T["admin"], "/api/purchase-requisitions", body)
            if r.status_code in (200, 201):
                STATE["sugg"] = s
                break
            rejected.append((s["sku"], r.status_code, D(r)[:120]))
        print(f"G2 saran yang DITOLAK saat dibuat PR ({len(rejected)}/{len(sugg)}): {rejected}")
        assert r.status_code in (200, 201), f"{r.status_code} {D(r)}"
        pr = r.json()
        STATE["pr_id"] = pr.get("id")
        STATE["pr_status"] = pr.get("status")
        print(f"G2 PR dibuat id={STATE['pr_id']} no={pr.get('number') or pr.get('pr_number')} "
              f"status={pr.get('status')}")
        assert STATE["pr_id"]

    def test_G3_setujui_pr_lalu_realisasikan_jadi_po(self, T):
        pr_id = STATE["pr_id"]
        if STATE.get("pr_status") != "approved":
            r = POST(T["manager"], f"/api/purchase-requisitions/{pr_id}/approve",
                     {"notes": "TEST_iter276 disetujui MD"})
            assert r.status_code == 200, f"approve PR: {r.status_code} {D(r)}"
            print(f"G3 PR disetujui status={r.json().get('status')}")
        src = GET(T["manager"], f"/api/purchase-requisitions/{pr_id}/sourcing")
        supplier = ""
        if src.status_code == 200:
            body = src.json()
            cand = (body.get("lines") or [{}])[0].get("candidates") or []
            if cand:
                supplier = cand[0].get("supplier_id", "")
        if not supplier:
            sup = GET(T["manager"], "/api/suppliers").json()
            rows = sup.get("items", sup) if isinstance(sup, dict) else sup
            supplier = [s for s in rows if s["id"] != "sup_grp_ksc_kanda"][0]["id"]
        r = POST(T["manager"], f"/api/purchase-requisitions/{pr_id}/realize-po",
                 {"supplier_id": supplier, "warehouse_id": "wh_jakarta",
                  "notes": "TEST_iter276"})
        assert r.status_code in (200, 201), f"realize-po: {r.status_code} {D(r)}"
        out = r.json()
        po_id = out.get("po_id") or out.get("id") or (out.get("po") or {}).get("id")
        STATE["po_id"] = po_id
        print(f"G3 PO lahir id={po_id} no={out.get('po_number') or (out.get('po') or {}).get('po_number')}")
        assert po_id, f"tidak ada po_id di jawaban: {str(out)[:300]}"

    def test_G4_po_baru_tampil_di_papan(self, T):
        r = GET(T["manager"], "/api/purchase-orders/board")
        assert r.status_code == 200, D(r)
        ids = [i["po_id"] for i in r.json()["items"]]
        assert STATE["po_id"] in ids, "PO hasil realisasi PR tidak tampil di papan"
        print("G4 PO baru tampil di papan")

    def test_G5_pr_tidak_bisa_disetujui_oleh_sales(self, T):
        body = {"items": [{"product_id": STATE["sugg"]["product_id"], "quantity": 10,
                           "notes": "TEST_iter276 pr sales"}],
                "entity_id": ENT, "reason": "TEST_iter276 pagar peran", "submit_now": True}
        r = POST(T["sales"], "/api/purchase-requisitions", body)
        print(f"G5 sales buat PR -> {r.status_code} {D(r) if r.status_code>=400 else ''}")
        if r.status_code in (200, 201):
            pid = r.json()["id"]
            STATE["pr_sales"] = pid
            r2 = POST(T["sales"], f"/api/purchase-requisitions/{pid}/approve", {"notes": "x"})
            print(f"G5 sales setujui PR sendiri -> {r2.status_code} {D(r2)}")
            assert r2.status_code in (401, 403), "sales BOLEH menyetujui PR sendiri (deviasi)"

    def test_G6_amandemen_po_disetujui_menuntut_alasan(self, T):
        pos = GET(T["manager"], "/api/purchase-orders?status=approved").json()
        rows = pos.get("items", pos) if isinstance(pos, dict) else pos
        target = rows[0] if rows else None
        if not target:
            pytest.skip("tidak ada PO berstatus approved untuk diamandemen")
        pid = target["id"]
        STATE["po_approved"] = pid
        r = POST(T["manager"], f"/api/purchase-orders/{pid}/amend",
                 {"notes": "TEST_iter276 tanpa alasan"})
        print(f"G6 amend tanpa alasan -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 422), "amandemen tanpa alasan DITERIMA (deviasi)"
        r2 = POST(T["manager"], f"/api/purchase-orders/{pid}/amend",
                  {"reason": "TEST_iter276 audit — geser tanggal kirim",
                   "notes": "TEST_iter276 amandemen audit"})
        print(f"G6 amend dengan alasan -> {r2.status_code} {D(r2) if r2.status_code>=400 else 'ok'}")
        assert r2.status_code in (200, 201, 409), f"{r2.status_code} {D(r2)}"

    def test_G7_revisi_baris_yang_sudah_diterima_ditolak(self, T):
        pos = GET(T["manager"], "/api/purchase-orders?limit=200").json()
        rows = pos.get("items", pos) if isinstance(pos, dict) else pos
        partial = [p for p in rows if p.get("status") in ("partially_received", "received", "receiving")]
        if not partial:
            pytest.skip("TIDAK-DAPAT-DIUJI: tak ada PO diterima sebagian di data demo")
        po = GET(T["manager"], f"/api/purchase-orders/{partial[0]['id']}").json()
        items = po.get("items", [])
        recv = [i for i in items if float(i.get("received_qty") or
                                          i.get("received_quantity") or 0) > 0]
        print(f"G7 PO {po.get('po_number')} status={po.get('status')} baris diterima={len(recv)} "
              f"dari {len(items)}")
        if not recv:
            pytest.skip("TIDAK-DAPAT-DIUJI: PO tanpa baris ber-received_quantity")
        new_items = []
        for i in items:
            new_items.append({"product_id": i["product_id"],
                              "quantity": float(i.get("quantity") or 0) / 2 or 1,
                              "unit_price": float(i.get("unit_price") or 0),
                              "unit": i.get("unit", "")})
        r = POST(T["manager"], f"/api/purchase-orders/{po['id']}/amend",
                 {"reason": "TEST_iter276 coba turunkan qty baris yang sudah diterima",
                  "items": new_items})
        print(f"G7 revisi baris diterima -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 409, 422), "revisi baris yang sudah diterima DITERIMA (deviasi)"
        assert any(w in D(r).lower() for w in ("terima", "diterima")), \
            f"pesan tidak menuntun: {D(r)}"


# ═══════════════════════ ALUR H — Papan PO per lini ═══════════════════════
class TestAlurH:
    def test_H6_urutan_tab_lini_ikut_master(self, T):
        b = GET(T["manager"], "/api/purchase-orders/board").json()
        codes = [l.get("code") for l in b.get("lines", [])]
        print(f"H6 tab lini = {codes}")
        assert codes == ["woven", "knit", "printing"], f"urutan tab: {codes}"
        print("H6 CATATAN: API tidak mengirim tab 'Semua' — tab itu ditambah layar (dicek via UI)")

    def test_H2_nama_sales_runutan_vs_po_rutin(self, T):
        b = GET(T["manager"], "/api/purchase-orders/board").json()
        chain = [i for i in b["items"] if i.get("pr_number") and i.get("sales_name")]
        routine = [i for i in b["items"] if not i.get("pr_id")]
        print(f"H2 rantai berselos nama sales={len(chain)} "
              f"{[ (i['po_number'], i['sales_name']) for i in chain ]}")
        print(f"H2 PO rutin (sales_name kosong) = {len(routine)}")
        assert len(chain) >= 3, "rantai demo dengan nama sales < 3"
        assert routine and all(not i.get("sales_name") for i in routine)

    def test_H3_chip_inspect_terkunci_dan_patch_ditolak(self, T):
        b = GET(T["manager"], "/api/purchase-orders/board").json()
        po = b["items"][0]
        insp = [s for s in po["stages"] if s["code"] == "inspect"]
        assert insp, "tahap inspect tidak ada di papan"
        assert insp[0]["locked"] is True and insp[0]["derived"] is True, insp[0]
        r = PATCH(T["manager"], f"/api/purchase-orders/{po['po_id']}/stage",
                  {"stage_code": "inspect", "status": "done", "note": "TEST_iter276"})
        print(f"H3 patch inspect -> {r.status_code} {D(r)}")
        assert r.status_code == 409, "chip Inspect BISA ditandai manual (deviasi)"

    def test_H1_tandai_tahap_celup_tercatat_siapa_kapan(self, T):
        b = GET(T["manager"], "/api/purchase-orders/board").json()
        po = [i for i in b["items"] if any(s["code"] == "celup" for s in i["stages"])][0]
        r = PATCH(T["manager"], f"/api/purchase-orders/{po['po_id']}/stage",
                  {"stage_code": "celup", "status": "in_progress",
                   "note": "TEST_iter276 celup mulai"})
        assert r.status_code == 200, f"{r.status_code} {D(r)}"
        b2 = GET(T["manager"], "/api/purchase-orders/board").json()
        row = [i for i in b2["items"] if i["po_id"] == po["po_id"]][0]
        st = [s for s in row["stages"] if s["code"] == "celup"][0]
        print(f"H1 celup -> status={st['status']} by={st['by']} at={st['at'][:19]} note={st['note']}")
        assert st["status"] == "in_progress" and st["by"] and st["at"]
        assert st["note"] == "TEST_iter276 celup mulai"
        STATE["h1_po"] = po["po_id"]

    def test_H4_tab_knit_kosong(self, T):
        r = GET(T["manager"], "/api/purchase-orders/board?line=knit")
        assert r.status_code == 200, D(r)
        n = len(r.json()["items"])
        print(f"H4 papan lini knit = {n} PO")
        assert n == 0, f"tab Knit tidak kosong ({n} PO)"

    def test_H5_pagar_lini_printing(self, T):
        r = GET(T["mgrprint"], "/api/purchase-orders/board")
        assert r.status_code == 200, D(r)
        b = r.json()
        lines = set()
        for i in b["items"]:
            lines |= set(i.get("line_codes") or [])
        print(f"H5 papan manager.printing: {len(b['items'])} PO, lini={lines}, "
              f"line_restricted={b.get('line_restricted')}, tab={[l.get('code') for l in b.get('lines',[])]}")
        assert b.get("line_restricted"), "penanda 'akses lini terbatas' tidak ada"
        assert b["items"] and all("printing" in (i.get("line_codes") or [])
                                  for i in b["items"]), "papan memuat PO tanpa lini printing"
        assert [l.get("code") for l in b.get("lines", [])] == ["printing"]
        woven = [i for i in GET(T["manager"], "/api/purchase-orders/board?line=woven").json()["items"]]
        r2 = PATCH(T["mgrprint"], f"/api/purchase-orders/{woven[0]['po_id']}/stage",
                   {"stage_code": "celup", "status": "done", "note": "TEST_iter276 lintas lini"})
        msg = D(r2)
        print(f"H5 tandai tahap PO woven oleh akun printing -> {r2.status_code} {msg}")
        assert r2.status_code == 403, "akun berpagar lini BISA menandai PO lini lain (deviasi)"
        assert "woven" in msg.lower() and "printing" in msg.lower(), \
            f"pesan tidak menyebut lini dokumen vs lini akun: {msg}"


# ═══════════════════════ ALUR I — R&D spesifikasi & sample ═══════════════════════
class TestAlurI:
    def test_I1_spesifikasi_draf_ajukan_setujui(self, T):
        colors = GET(T["manager"], "/api/color-library").json()
        rows = colors.get("items", colors) if isinstance(colors, dict) else colors
        col = rows[0]
        body = {"title": "TEST_iter276 Katun Combed Warna Audit", "base_unit": "yard",
                "sample_type_hint": "labdip", "line_code": "woven",
                "target": {"stage": "finished", "fabric_type": "woven",
                           "gramasi": 150, "lebar": 150},
                "color_target": {"color_id": col["id"], "code": col.get("code", ""),
                                 "name": col.get("name", "")},
                "notes": "TEST_iter276"}
        r = POST(T["admin"], "/api/rnd/specs", body)
        assert r.status_code in (200, 201), f"{r.status_code} {D(r)}"
        spec = r.json()
        sid = spec.get("id")
        STATE["spec_id"] = sid
        print(f"I1 spec dibuat {spec.get('number')} status={spec.get('status')}")
        assert spec.get("status") in ("draft",), f"status awal {spec.get('status')} bukan draf"
        r2 = POST(T["admin"], f"/api/rnd/specs/{sid}/submit")
        assert r2.status_code == 200, f"submit: {r2.status_code} {D(r2)}"
        print(f"I1 setelah ajukan status={r2.json().get('status')}")
        assert r2.json().get("status") in ("review", "waiting_approval", "submitted")
        r3 = POST(T["manager"], f"/api/rnd/specs/{sid}/approve", {"note": "TEST_iter276 ACC"})
        print(f"I1 approve -> {r3.status_code} {D(r3) if r3.status_code>=400 else r3.json().get('status')}")
        assert r3.status_code == 200, D(r3)
        j3 = r3.json()
        st = j3.get("status") or (j3.get("spec") or {}).get("status")
        print(f"I1 status setelah ACC = {st} (kunci jawaban={list(j3.keys())})")
        assert st == "approved"

    def test_I3_buat_permintaan_sample(self, T):
        body = {"spec_id": STATE.get("spec_id", ""), "sample_types": ["labdip"],
                "title": "TEST_iter276 labdip audit", "brief": "TEST_iter276"}
        r = POST(T["admin"], "/api/rnd/samples", body)
        assert r.status_code in (200, 201), f"{r.status_code} {D(r)}"
        s = r.json()
        STATE["smp_id"] = s["id"]
        print(f"I3 sample {s.get('number')} status={s.get('status')} types={s.get('sample_types')}")
        assert s.get("status") in ("draft", "requested", "new")

    def test_I4_kirim_tanpa_supplier_ditolak(self, T):
        r = POST(T["manager"], f"/api/rnd/samples/{STATE['smp_id']}/send", {"supplier_ids": []})
        print(f"I4 kirim tanpa supplier -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 422), "kirim tanpa supplier DITERIMA (deviasi)"
        assert "supplier" in D(r).lower()

    def test_I4b_kirim_dengan_supplier(self, T):
        sup = GET(T["manager"], "/api/suppliers").json()
        rows = sup.get("items", sup) if isinstance(sup, dict) else sup
        sid = [s for s in rows if s["id"] != "sup_grp_ksc_kanda"][0]["id"]
        STATE["sup_id"] = sid
        r = POST(T["manager"], f"/api/rnd/samples/{STATE['smp_id']}/send",
                 {"supplier_ids": [sid], "note": "TEST_iter276"})
        assert r.status_code == 200, f"{r.status_code} {D(r)}"
        print(f"I4b kirim -> status={r.json().get('status')}")
        assert r.json().get("status") == "sent"

    def test_I2_tutup_round_tanpa_lampiran_ditolak(self, T):
        s = GET(T["manager"], f"/api/rnd/samples/{STATE['smp_id']}").json()
        rounds = s.get("rounds") or []
        if not rounds:
            r = POST(T["manager"], f"/api/rnd/samples/{STATE['smp_id']}/rounds",
                     {"supplier_id": STATE["sup_id"], "type_code": "labdip"})
            print(f"I2 buka round -> {r.status_code} {D(r) if r.status_code>=400 else ''}")
            assert r.status_code in (200, 201), D(r)
            s = GET(T["manager"], f"/api/rnd/samples/{STATE['smp_id']}").json()
            rounds = s.get("rounds") or []
        rid = rounds[-1]["id"] if isinstance(rounds[-1], dict) else rounds[-1]
        STATE["round_id"] = rid
        r = POST(T["manager"], f"/api/rnd/samples/{STATE['smp_id']}/rounds/{rid}/submit",
                 {"note": "TEST_iter276 tanpa lampiran", "measurements": {"delta_e": 0.8}})
        print(f"I2 setor/tutup round tanpa lampiran -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 409, 422), "tutup round tanpa lampiran DITERIMA (deviasi)"
        assert "lampiran" in D(r).lower(), f"pesan tidak menyebut lampiran: {D(r)}"

    def test_I5_nilai_acc_dan_putuskan_pemenang(self, T):
        sid, rid = STATE["smp_id"], STATE["round_id"]
        png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        files = {"file": ("TEST_iter276.png", png, "image/png")}
        up = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/attachments",
                           headers={"Authorization": H(T['manager'])["Authorization"],
                                    "X-Entity-Id": ENT}, files=files, timeout=90)
        print(f"I5 unggah lampiran -> {up.status_code} {D(up) if up.status_code>=400 else ''}")
        assert up.status_code in (200, 201), D(up)
        types = {t["value"]: t for t in GET(T["manager"], "/api/rnd/meta").json()["sample_types"]}
        fields = types["labdip"]["measurement_fields"]
        meas = {f: (0.8 if f == "delta_e" else 4) for f in fields}
        r = POST(T["manager"], f"/api/rnd/samples/{sid}/rounds/{rid}/submit",
                 {"note": "TEST_iter276 dengan lampiran", "measurements": meas})
        print(f"I5 setor round -> {r.status_code} {D(r) if r.status_code>=400 else ''}")
        assert r.status_code == 200, D(r)
        r2 = POST(T["manager"], f"/api/rnd/samples/{sid}/rounds/{rid}/assess",
                  {"result": "acc", "score": 4.5, "note": "TEST_iter276 acc"})
        print(f"I5 nilai -> {r2.status_code} {D(r2) if r2.status_code>=400 else r2.json().get('status')}")
        assert r2.status_code == 200, D(r2)
        meta = GET(T["manager"], "/api/rnd/meta").json()
        reason_code = ""
        rs = meta.get("reasons") or {}
        pool = rs if isinstance(rs, list) else (rs.get("decide") or rs.get("winner") or [])
        if isinstance(pool, list) and pool:
            first = pool[0]
            reason_code = (first.get("value") or first.get("code") or "") \
                if isinstance(first, dict) else str(first)
        print(f"I5 reason_code dipakai={reason_code!r}")
        r3 = POST(T["manager"], f"/api/rnd/samples/{sid}/decide",
                  {"supplier_id": STATE["sup_id"], "reason_code": reason_code or "harga",
                   "note": "TEST_iter276 pemenang", "price": 25000, "moq": 100})
        print(f"I5 putuskan -> {r3.status_code} {D(r3) if r3.status_code>=400 else r3.json().get('status')}")
        assert r3.status_code == 200, D(r3)
        assert r3.json().get("status") in ("decided", "winner_selected"), r3.json().get("status")

    def test_I7_catat_pengiriman_sebelum_jadi_ditolak(self, T):
        sid = STATE["smp_id"]
        r = POST(T["manager"], f"/api/rnd/samples/{sid}/deliver",
                 {"to": "customer", "to_name": "TEST_iter276", "note": "TEST_iter276 kirim dini"})
        print(f"I7 deliver sebelum finish -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 409, 422), "pengiriman sebelum 'jadi' DITERIMA (deviasi)"


# ═══════════════════════ ALUR J — Permintaan Desain ═══════════════════════
class TestAlurJ:
    def test_J1_empat_dsr_demo(self, T):
        d = GET(T["manager"], "/api/design-requests").json()
        rows = {i["number"]: i for i in d["items"]}
        print("J1 " + str({k: (v["status"], v.get("assigned_to")) for k, v in rows.items()}))
        assert len(d["items"]) >= 4
        assert rows["KSC/DSR-00001"]["status"] == "submitted"
        assert not rows["KSC/DSR-00001"].get("assigned_to")
        assert rows["KSC/DSR-00002"]["status"] == "in_progress"
        assert rows["KSC/DSR-00003"]["status"] in ("delivered", "approved"), \
            rows["KSC/DSR-00003"]["status"]
        assert rows["KSC/DSR-00004"]["status"] == "approved"
        STATE["dsr3"] = rows["KSC/DSR-00003"]["id"]

    def test_J5_designer_hanya_melihat_tiga(self, T):
        d = GET(T["designer"], "/api/design-requests")
        assert d.status_code == 200, D(d)
        nums = [i["number"] for i in d.json()["items"]]
        print(f"J5 designer melihat {len(nums)} DSR: {nums}")
        assert "KSC/DSR-00001" not in nums, "designer melihat DSR yang belum ditugaskan (deviasi)"
        assert len(nums) == 3, f"designer melihat {len(nums)} DSR (dokumen: 3)"

    def test_J2_sumber_dari_so_menuntut_nomor_so(self, T):
        r = POST(T["manager"], "/api/design-requests",
                 {"source": "so", "target_type": "motif", "brief": "TEST_iter276 tanpa SO",
                  "submit_now": True})
        print(f"J2 DSR sumber SO tanpa so_id -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 422), "DSR sumber SO tanpa nomor SO DITERIMA (deviasi)"

    def test_J3_dsr_tanpa_desainer_berhenti_di_menunggu_penugasan(self, T):
        r = POST(T["manager"], "/api/design-requests",
                 {"source": "internal", "target_type": "motif",
                  "brief": "TEST_iter276 audit DSR tanpa desainer", "line_code": "printing",
                  "submit_now": True})
        assert r.status_code in (200, 201), f"{r.status_code} {D(r)}"
        j = r.json()
        STATE["dsr_new"] = j["id"]
        print(f"J3 DSR baru {j.get('number')} status={j.get('status')} assigned={j.get('assigned_to')!r}")
        assert j.get("status") == "submitted" and not j.get("assigned_to")

    def test_J4_minta_revisi_menuntut_alasan_lalu_acc(self, T):
        d = GET(T["manager"], "/api/design-requests").json()["items"]
        cand = [x for x in d if x["status"] == "delivered"]
        if not cand:
            pytest.skip("tidak ada DSR berstatus 'Menunggu keputusan' (sudah di-ACC audit sebelumnya)")
        did = cand[0]["id"]
        print(f"J4 memakai {cand[0]['number']}")
        r = POST(T["manager"], f"/api/design-requests/{did}/reject", {"reason": ""})
        print(f"J4 minta revisi tanpa alasan -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 422), "minta revisi tanpa alasan DITERIMA (deviasi)"
        r2 = POST(T["manager"], f"/api/design-requests/{did}/approve", {"note": "TEST_iter276 ACC"})
        print(f"J4 ACC DSR-00003 -> {r2.status_code} {D(r2) if r2.status_code>=400 else r2.json().get('status')}")
        assert r2.status_code == 200, D(r2)
        assert r2.json().get("status") == "approved"

    def test_J6_designer_tidak_boleh_acc(self, T):
        r = POST(T["designer"], f"/api/design-requests/{STATE['dsr_new']}/approve", {})
        print(f"J6 designer ACC -> {r.status_code} {D(r)}")
        assert r.status_code in (401, 403), "designer BISA meng-ACC DSR (deviasi)"


# ═══════════════════════ ALUR K — Inspeksi QC ═══════════════════════
class TestAlurK:
    def test_K1_ins00001_punya_baris_ditahan(self, T):
        d = GET(T["manager"], "/api/inspections").json()
        rows = {i["number"]: i for i in d["items"]}
        ins = rows["KSC/INS-00001"]
        STATE["ins1"] = ins["id"]
        STATE["ins2"] = rows["KSC/INS-00002"]["id"]
        held = [l for l in ins["lines"] if l.get("hold") or l.get("held") or
                l.get("status") == "hold" or l.get("on_hold")]
        print(f"K1 INS-00001 status={ins['status']} baris={len(ins['lines'])} "
              f"ditahan={len(held)} contoh={ {k: held[0].get(k) for k in ('id','color_result','hold_reason','quantity')} if held else None}")
        assert ins["status"] == "in_progress"
        if not held:
            pytest.skip("tahanan sudah dilepas oleh jalankan audit sebelumnya "
                        "(pada seed bersih baris DITAHAN ADA — lihat laporan K1)")
        STATE["hold_line"] = held[0]["id"]

    def test_K2_gudang_tanpa_tombol_lepas_tahanan(self, T):
        if "hold_line" not in STATE:
            pytest.skip("tahanan sudah dilepas jalankan sebelumnya (lihat K1)")
        m_wh = GET(T["warehouse"], "/api/inspections/meta").json()
        m_mgr = GET(T["manager"], "/api/inspections/meta").json()
        print(f"K2 can_release_hold gudang={m_wh.get('can_release_hold')} "
              f"manajer={m_mgr.get('can_release_hold')} role={m_wh.get('role')}")
        assert m_wh.get("can_release_hold") is False
        assert m_mgr.get("can_release_hold") is True
        r = POST(T["warehouse"],
                 f"/api/inspections/{STATE['ins1']}/lines/{STATE['hold_line']}/release-hold",
                 {"reason": "TEST_iter276 gudang mencoba melepas tahanan barang"})
        print(f"K2 gudang lepas tahanan -> {r.status_code} {D(r)}")
        assert r.status_code in (401, 403), "gudang BISA melepas tahanan (deviasi)"

    def test_K3_lepas_tahanan_menuntut_alasan_min15(self, T):
        if "hold_line" not in STATE:
            pytest.skip("tahanan sudah dilepas jalankan sebelumnya (lihat K1)")
        url = f"/api/inspections/{STATE['ins1']}/lines/{STATE['hold_line']}/release-hold"
        r = POST(T["manager"], url, {"reason": "jelek"})
        print(f"K3 alasan 'jelek' -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 422), "alasan 5 huruf DITERIMA (deviasi)"
        assert "15" in D(r), f"pesan tak menyebut ambang 15: {D(r)}"
        r2 = POST(T["manager"], url,
                  {"reason": "TEST_iter276 beda shade masih dalam toleransi pelanggan, dilepas 200 yard"})
        print(f"K3 alasan panjang -> {r2.status_code} {D(r2) if r2.status_code>=400 else 'ok'}")
        assert r2.status_code == 200, D(r2)

    def test_K4_keputusan_tolak_menuntut_alasan_min15(self, T):
        r = POST(T["manager"], f"/api/inspections/{STATE['ins1']}/finish",
                 {"decision": "tolak", "remark": "jelek"})
        print(f"K4 finish tolak alasan pendek -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 422), "keputusan Ditolak tanpa alasan panjang DITERIMA (deviasi)"
        assert "15" in D(r), D(r)

    def test_K5_buka_kembali_dokumen_selesai_menuntut_alasan_min15(self, T):
        url = f"/api/inspections/{STATE['ins2']}/reopen"
        r = POST(T["manager"], url, {"reason": "salah"})
        print(f"K5 reopen alasan pendek -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 422), "reopen tanpa alasan panjang DITERIMA (deviasi)"
        assert "15" in D(r), D(r)

    def test_K6_gudang_tidak_boleh_membuat_spk_inspeksi(self, T):
        r = POST(T["warehouse"], "/api/inspections",
                 {"kind": "inbound", "ref_doc_id": "po_010", "entity_id": ENT})
        print(f"K6 gudang buat SPK inspeksi -> {r.status_code} {D(r)}")
        assert r.status_code in (401, 403), "gudang BISA membuat SPK inspeksi (deviasi)"

    def test_K7_sudah_ada_spk_pada_pilihan_dokumen(self, T):
        kinds = [k["value"] for k in GET(T["manager"], "/api/inspections/meta").json()["kinds"]]
        flagged, total = [], 0
        for k in kinds:
            r = GET(T["manager"], f"/api/inspections/meta/ref-docs?kind={k}")
            assert r.status_code == 200, D(r)
            rows = r.json()
            rows = rows.get("items", rows) if isinstance(rows, dict) else rows
            total += len(rows)
            flagged += [(k, x["label"]) for x in rows if "sudah ada spk" in x["label"].lower()]
        print(f"K7 kind={kinds} total dokumen={total}; ber-tanda 'sudah ada SPK'={flagged}")
        assert total, "tidak ada dokumen kandidat SPK inspeksi"
        assert flagged, "tidak ada penanda 'Sudah ada SPK' (dokumen ber-SPK berjalan tak ditandai)"


# ═══════════════════════ ALUR L — Makloon ═══════════════════════
class TestAlurL:
    def test_L1_lima_order_demo(self, T):
        d = GET(T["manager"], "/api/makloon-orders").json()
        rows = d.get("items", d) if isinstance(d, dict) else d
        st = [r["status"] for r in rows]
        print(f"L1 order makloon={len(rows)} status={st}")
        seedrows = [r for r in rows if "TEST_iter276" not in (r.get("notes") or "")]
        assert len(seedrows) == 5, f"order makloon demo = {len(seedrows)} (dokumen: 5)"

    def test_L2_ada_order_diterima_sebagian(self, T):
        d = GET(T["manager"], "/api/makloon-orders").json()
        rows = d.get("items", d) if isinstance(d, dict) else d
        part = [r for r in rows if r["status"] == "partially_received"]
        print(f"L2 order status 'Sebagian' = {len(part)}")
        assert part, "tidak ada order makloon berstatus Sebagian"
        STATE["mko_part"] = part[0]["id"]

    def test_L3_estimasi_sebelum_simpan(self, T):
        r = POST(T["manager"], "/api/makloon-orders/estimate",
                 {"input_product_id": "prod_pfp_katun", "makloon_id": "mak_seed_printing",
                  "process_type": "printing", "stage_code": "printing",
                  "input_qty": 200, "input_uom": "yard"})
        print(f"L3 estimate -> {r.status_code} {str(r.json())[:400] if r.status_code==200 else D(r)}")
        assert r.status_code == 200, D(r)
        j = r.json()
        est = j.get("estimate") or {}
        print(f"L3 estimate={ {k: est.get(k) for k in list(est)[:12]} } tariff={str(j.get('tariff'))[:200]}")
        assert any(k in est for k in ("output_qty", "expected_output_qty", "estimated_output")), \
            f"tidak ada perkiraan hasil: {list(est.keys())}"
        assert j.get("tariff") or est.get("cost") or est.get("total_cost"), \
            "tidak ada perkiraan biaya"

    def test_L4_buat_keluarkan_terima_sebagian_lalu_klaim(self, T):
        wh = GET(T["manager"], "/api/warehouses").json()
        wrows = wh.get("items", wh) if isinstance(wh, dict) else wh
        wid = wrows[0]["id"]
        STATE["wh_ids"] = [w["id"] for w in wrows]
        body = {"mode": "process_only", "material_product_id": "prod_pfp_katun",
                "material_qty": 4, "material_unit": "yard",
                "from_warehouse_id": wid, "target_warehouse_id": wid,
                "entity_id": ENT, "notes": "TEST_iter276 audit makloon",
                "steps": [{"seq": 1, "process_type": "printing", "stage_code": "printing",
                           "makloon_id": "mak_seed_printing",
                           "input_product_id": "prod_pfp_katun",
                           "output_product_id": "prod_batik_mega", "input_qty": 4}]}
        r = POST(T["manager"], "/api/makloon-orders", body)
        print(f"L4 buat order -> {r.status_code} {D(r) if r.status_code>=400 else r.json().get('number')}")
        if r.status_code not in (200, 201):
            pytest.fail(f"buat order makloon gagal: {r.status_code} {D(r)}")
        mko = r.json()
        mid = mko["id"]
        STATE["mko_new"] = mid
        r2 = None
        for cand in STATE["wh_ids"]:
            r2 = POST(T["manager"], f"/api/makloon-orders/{mid}/issue",
                      {"step_seq": 1, "from_warehouse_id": cand})
            print(f"L4 keluarkan bahan dari {cand} -> {r2.status_code} "
                  f"{D(r2) if r2.status_code>=400 else r2.json().get('status')}")
            if r2.status_code == 200:
                wid = cand
                break
        assert r2.status_code == 200, D(r2)
        assert r2.json().get("status") == "in_process"
        r3 = POST(T["manager"], f"/api/makloon-orders/{mid}/receive",
                  {"step_seq": 1, "actual_output_qty": 1.5, "tariff": 5000,
                   "output_warehouse_id": wid,
                   "rolls": [{"lot": "TEST-ITER276-L1", "length": 1.5, "grade": "A"}]})
        print(f"L4 terima sebagian (1.5 dari perkiraan ~3.9) -> {r3.status_code} "
              f"{D(r3) if r3.status_code>=400 else r3.json().get('status')}")
        assert r3.status_code == 200, D(r3)
        STATE["l4_status_after_partial"] = r3.json().get("status")
        r4 = POST(T["manager"], f"/api/makloon-orders/{mid}/claim",
                  {"step_seq": 1, "action": "potong_bon", "amount": 5000,
                   "reason": "TEST_iter276 hasil kurang dari perkiraan estimasi"})
        print(f"L4 klaim selisih -> {r4.status_code} {D(r4) if r4.status_code>=400 else 'ok'}")
        assert r4.status_code in (200, 201), D(r4)

    def test_L4b_status_sebagian_setelah_terima_kurang(self, T):
        st = STATE.get("l4_status_after_partial")
        print(f"L4b status order setelah terima 8 dari ~19.4 = {st}")
        assert st == "partially_received", (
            f"dokumen menjanjikan status 'Sebagian' saat hasil kurang, tetapi status={st} "
            "(status hanya melihat tahap yang sudah diterima, bukan kuantitas)")

    def test_L5_klaim_muncul_di_antrean_dan_diputuskan(self, T):
        r = GET(T["manager"], "/api/makloon-orders/claims")
        assert r.status_code == 200, D(r)
        body = r.json()
        rows = body.get("items", body) if isinstance(body, dict) else body
        mine = [c for c in rows if c.get("order_id") == STATE.get("mko_new") or
                c.get("mko_id") == STATE.get("mko_new")]
        print(f"L5 klaim (semua)={len(rows)} klaim uji ditemukan={len(mine)} "
              f"status={[c.get('status') or (c.get('claim') or {}).get('status') for c in mine]}")
        stats = GET(T["manager"], "/api/makloon-orders/claims/stats").json()
        print(f"L5 stats klaim={stats}")
        assert mine, "klaim uji tidak muncul di antrean persetujuan klaim"
        q = GET(T["manager"], "/api/approvals/my-queue")
        kinds = []
        if q.status_code == 200:
            qb = q.json()
            qrows = qb.get("items", qb) if isinstance(qb, dict) else qb
            kinds = sorted({(x.get("doc_type") or x.get("kind") or x.get("type"))
                            for x in qrows if isinstance(x, dict)})
        print(f"L5 /api/approvals/my-queue -> {q.status_code} jenis={kinds}")
        bl = GET(T["manager"], "/api/approvals/backlog").json()
        blkeys = [i.get("key") for i in (bl.get("items") or [])]
        print(f"PP/L5 kunci backlog persetujuan={blkeys}")
        assert any("makloon" in str(k) for k in blkeys) or \
            any("makloon" in str(k) for k in kinds), \
            "klaim makloon TIDAK muncul di Pusat Persetujuan (my-queue/backlog)"
        r2 = POST(T["manager"], f"/api/makloon-orders/{STATE['mko_new']}/claim/approve",
                  {"step_seq": 1, "note": "TEST_iter276 setujui klaim"})
        print(f"L5 putuskan klaim -> {r2.status_code} {D(r2) if r2.status_code>=400 else 'ok'}")
        assert r2.status_code == 200, D(r2)


# ═══════════════════════ ALUR D — Pesanan khusus (OD) ═══════════════════════
class TestAlurD:
    def test_D1_tiga_od_demo(self, T):
        d = GET(T["manager"], "/api/special-orders").json()
        rows = d.get("items", d) if isinstance(d, dict) else d
        print(f"D1 OD demo={len(rows)} status={[r['status'] for r in rows]} "
              f"ambang={d.get('approval_threshold') if isinstance(d, dict) else ''}")
        assert len(rows) >= 3, f"OD demo={len(rows)} (dokumen: 3)"
        pend = [r for r in rows if r["status"] == "pending_approval"]
        STATE["od_pending"] = pend[0]["id"] if pend else ""
        print(f"D1 OD menunggu ACC = {len(pend)}")

    def test_D2_sales_membuat_od(self, T):
        cust = GET(T["sales"], "/api/customers").json()
        rows = cust.get("items", cust) if isinstance(cust, dict) else cust
        cid = rows[0]["id"]
        body = {"customer_id": cid, "entity_id": ENT,
                "custom_item": {"description": "TEST_iter276 kain custom audit",
                                "quantity": 400, "unit": "yard",
                                "target_price": 60000, "notes": "TEST_iter276"},
                "expected_delivery": "2026-10-30", "notes": "TEST_iter276 OD audit",
                "submit_for_approval": True}
        r = POST(T["sales"], "/api/special-orders", body)
        print(f"D2 sales buat OD -> {r.status_code} {D(r) if r.status_code>=400 else r.json().get('status')}")
        assert r.status_code in (200, 201), D(r)
        j = r.json()
        STATE["od_new"] = j["id"]
        print(f"D2 nilai={j.get('total_amount')} status={j.get('status')} "
              f"approval_status={j.get('approval_status')}")
        assert j.get("status") == "pending_approval", \
            f"OD nilai besar + submit_for_approval TIDAK masuk antrean manajer (status={j.get('status')})"

    def test_D3_tolak_od_menuntut_alasan(self, T):
        r = POST(T["manager"], f"/api/special-orders/{STATE['od_new']}/reject", {"reason": ""})
        print(f"D3 tolak tanpa alasan -> {r.status_code} {D(r)}")
        assert r.status_code in (400, 422), "tolak OD tanpa alasan DITERIMA (deviasi)"

    def test_D4_manajer_setujui_od(self, T):
        oid = STATE.get("od_pending") or STATE.get("od_new")
        if not oid:
            pytest.skip("tidak ada OD menunggu persetujuan")
        r = POST(T["manager"], f"/api/special-orders/{oid}/approve",
                 {"notes": "TEST_iter276 disetujui MD"})
        print(f"D4 approve OD -> {r.status_code} {D(r) if r.status_code>=400 else r.json().get('status')}")
        assert r.status_code == 200, D(r)
        j = r.json()
        print(f"D4 status={j.get('status')} approval_status={j.get('approval_status')}")
        assert j.get("approval_status") == "approved" or \
            j.get("status") in ("approved", "confirmed", "in_production")
        STATE["od_approved"] = oid

    def test_D5_lanjut_pr_dan_sku(self, T):
        oid = STATE["od_approved"]
        r = POST(T["manager"], f"/api/special-orders/{oid}/create-pr", {})
        print(f"D5 create-pr -> {r.status_code} {D(r) if r.status_code>=400 else str(r.json())[:200]}")
        r2 = POST(T["manager"], f"/api/special-orders/{oid}/create-sku", {})
        print(f"D5 create-sku -> {r2.status_code} {D(r2) if r2.status_code>=400 else str(r2.json())[:200]}")
        assert r.status_code in (200, 201, 400, 409), D(r)
        assert r2.status_code in (200, 201, 400, 409), D(r2)

    def test_D6_sales_tidak_boleh_setujui_od(self, T):
        r = POST(T["sales"], f"/api/special-orders/{STATE['od_new']}/approve", {"notes": "x"})
        print(f"D6 sales approve OD -> {r.status_code} {D(r)}")
        assert r.status_code in (401, 403), "sales BISA menyetujui OD (deviasi)"


# ═══════════════════════ Pusat Persetujuan & DATA DEMO ═══════════════════════
class TestPusatPersetujuanDanDataDemo:
    def test_PP1_antrean_manajer_memuat_beragam_jenis(self, T):
        r = GET(T["manager"], "/api/approvals/my-queue")
        print(f"PP1 my-queue -> {r.status_code}")
        assert r.status_code == 200, D(r)
        body = r.json()
        rows = body.get("items", body) if isinstance(body, dict) else body
        kinds = sorted({str(x.get("doc_type") or x.get("kind") or x.get("type"))
                        for x in rows if isinstance(x, dict)})
        print(f"PP1 antrean={len(rows)} jenis={kinds}")
        b = GET(T["manager"], "/api/approvals/backlog")
        print(f"PP1 backlog -> {b.status_code} {str(b.json())[:400] if b.status_code==200 else D(b)}")
        assert kinds, "antrean persetujuan manajer kosong"

    def test_DD1_galeri_desain_1_disahkan_1_menunggu(self, T):
        g = GET(T["manager"], "/api/design-gallery").json()
        rows = g.get("items", g) if isinstance(g, dict) else g
        st = {}
        for x in rows:
            st[x["status"]] = st.get(x["status"], 0) + 1
        print(f"DD1 galeri={len(rows)} per-status={st}")
        assert st.get("approved", 0) >= 1 and st.get("pending_approval", 0) >= 1

    def test_DD2_isolasi_inspeksi_kanda_dari_ksc(self, T):
        d = GET(T["manager"], "/api/inspections").json()
        nums = [i["number"] for i in d["items"]]
        print(f"DD2 inspeksi terlihat dari KSC: {nums}")
        assert all(not n.startswith("KANDA/") for n in nums), "dokumen KANDA terlihat dari KSC"
        kanda = GET(T["admin"], "/api/inspections", entity="ent_kanda")
        knums = [i["number"] for i in kanda.json()["items"]] if kanda.status_code == 200 else []
        print(f"DD2 inspeksi entitas KANDA ({kanda.status_code}): {knums}")
        if knums:
            kid = kanda.json()["items"][0]["id"]
            rm = GET(T["manager"], f"/api/inspections/{kid}")
            rw = GET(T["warehouse"], f"/api/inspections/{kid}")
            print(f"DD2 buka dokumen KANDA saat scope KSC: manager(2 entitas)={rm.status_code} "
                  f"gudang(1 entitas)={rw.status_code}")
            assert rw.status_code in (403, 404), "akun 1-entitas bisa membaca dokumen PT lain"
            assert rm.status_code in (403, 404), (
                "GET detail mengabaikan badan usaha aktif (X-Entity-Id) untuk akun "
                "multi-entitas — daftar terisolasi tetapi detail/PDF tetap terbuka")
        else:
            print("DD2 CATATAN: entitas KANDA tidak punya dokumen inspeksi (klaim KANDA/INS-00001 tidak terbukti)")

    def test_DD3_produk_eksklusif_hanya_pemiliknya(self, T):
        def skus(tok):
            p = GET(tok, "/api/products?limit=500").json()
            rows = p.get("items", p) if isinstance(p, dict) else p
            return {x.get("sku") for x in rows}
        own, other = skus(T["sales"]), skus(T["sales2"])
        mgr = skus(T["manager"])
        print(f"DD3 ENK-BALI-001 pada sales@={('ENK-BALI-001' in own)} "
              f"sales2@={('ENK-BALI-001' in other)} manager={('ENK-BALI-001' in mgr)}")
        assert "ENK-BALI-001" in own, "pemilik tidak melihat produk eksklusifnya"
        assert "ENK-BALI-001" not in other, "sales lain MELIHAT produk eksklusif (deviasi)"

    def test_DD4_tiga_rantai_so_pr_po(self, T):
        b = GET(T["manager"], "/api/purchase-orders/board").json()
        chain = [(i["po_number"], i["pr_number"], i["so_numbers"], i["sales_name"])
                 for i in b["items"] if i.get("source") == "pr" and i.get("so_numbers")]
        print(f"DD4 rantai SO→PR→PO = {len(chain)}: {chain}")
        assert len(chain) >= 3
        assert all(c[3] for c in chain), "ada rantai tanpa nama sales"
