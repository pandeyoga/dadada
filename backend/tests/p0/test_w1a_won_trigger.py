"""Regresi W1-A / keputusan #7 — pemicu lead menjadi PEMBELI (`lead.won_trigger`): bawaan = booking dikonfirmasi,
dapat ditimpa per proyek, dan SEMUA empat opsi (booking_fee_verified · spr_signed · ppjb_signed · ajb_signed) benar-benar jalan.

    API_BASE=http://localhost:8070/api DB_NAME=sipro_w1a MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_w1a_won_trigger.py -n 0 --noconftest -q -p no:cacheprovider

"Terjadi tepat pada peristiwanya" diukur pada DATA (`contracts`, `customers`, `leads.stage`), bukan pada balasan HTTP:
sebelum peristiwa → belum ada kontrak/pembeli/`won`; sesudahnya → tepat SATU kontrak & SATU pembeli; mengulang peristiwa /
konversi manual → tetap satu. Dokumen SPR/PPJB/AJB disemai LANGSUNG ke DB (SPR resmi lahir dari kontrak, PPJB butuh progres
bangun, AJB butuh BAST — semuanya jalur lain yang tak relevan di sini) lalu DITANDATANGANI lewat endpoint sungguhan, sehingga
peristiwa `document.signed` yang diuji adalah peristiwa asli. Penimpaan hanya di tingkat PROYEK uji (tidak menyentuh tes lain);
selalu dikembalikan di `finally`.

Bukti merah di kode lama (4c940d9): bawaan `spr_signed`; pembaca membaca `settings` org saja; peristiwa `document.signed`
dibaca dari kunci `payload` yang tidak ada (muatan event ada di `data`) sehingga pemicu SPR tak pernah jalan; PPJB/AJB tak punya
pemicu sama sekali.
"""
import time
import uuid

import pytest

from test_p0_masuk import FINANCE, OWNER, SALES, World, call, ok, upload_proof
from test_p0_siklus_deal import mdb, now

KEY = "lead.won_trigger"
BOOK = "booking_fee_verified"


@pytest.fixture(scope="module")
def world():
    return World()


@pytest.fixture(scope="module")
def world2():
    return World()


# ------------------------------------------------------------------ pembantu
def put(value, scope="org", scope_id=None):
    body = {"value": value, "reason": "uji W1A pemicu pembeli", "scope": scope}
    if scope_id:
        body["scope_id"] = scope_id
    return call(OWNER, "PUT", f"/settings/{KEY}", json=body)


def reset(scope="org", scope_id=None):
    params = {"scope": scope}
    if scope_id:
        params["scope_id"] = scope_id
    call(OWNER, "POST", f"/settings/{KEY}/reset", params=params)


def contracts_of(deal_id):
    return list(mdb().contracts.find({"deal_id": deal_id}))


def customers_of(lead_id):
    return list(mdb().customers.find({"$or": [{"lead_id": lead_id}, {"lead_ids": lead_id}]}))


def stage_of(lead_id):
    return mdb().leads.find_one({"id": lead_id})["stage"]


def jadi_pembeli(d) -> bool:
    return bool(contracts_of(d["deal_id"])) and bool(customers_of(d["lead_id"]))


def belum_pembeli(d, mengapa=""):
    assert not contracts_of(d["deal_id"]), f"kontrak sudah lahir terlalu dini {mengapa}"
    assert not customers_of(d["lead_id"]), f"pembeli sudah lahir terlalu dini {mengapa}"
    assert stage_of(d["lead_id"]) != "won", f"lead sudah won terlalu dini {mengapa}"


def tepat_satu(d):
    cs = contracts_of(d["deal_id"])
    cu = customers_of(d["lead_id"])
    assert len(cs) == 1 and len(cu) == 1, (len(cs), len(cu))
    assert cs[0]["customer_id"] == cu[0]["id"]
    assert stage_of(d["lead_id"]) == "won"
    return cs[0], cu[0]


def seed_doc(d, code) -> str:
    deal = mdb().deals.find_one({"id": d["deal_id"]})
    did = str(uuid.uuid4())
    mdb().documents.insert_one({
        "id": did, "org_id": deal["org_id"], "deal_id": d["deal_id"], "lead_id": deal.get("lead_id"),
        "unit_id": deal.get("unit_id"), "assigned_to": deal.get("assigned_to"), "template_code": code,
        "doc_number": f"UJI-W1A-{did[:6]}", "title": f"{code} uji W1A", "content": "isi uji W1A", "status": "finalized",
        "signatures": [], "created_by": "uji", "created_at": now(), "updated_at": now()})
    return did


def tanda_tangan(doc_id, name="Pembeli Uji", role="buyer"):
    return ok(call(OWNER, "POST", f"/documents/{doc_id}/sign", json={"role": role, "name": name}))


def deal_baru(world, fee=0, book=True):
    return world.new_deal(booking_fee=fee, book=book)


def bayar_bf(deal_id, amount=5_000_000):
    ok(call(FINANCE, "POST", f"/booking-fee/deals/{deal_id}/pay", json={"amount": amount, "proof_file_ids": [upload_proof()]}))


def reconcile_ok(timeout=40):
    end = time.time() + timeout
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            return d["ok"]
        time.sleep(1.5)


# ================================================================== bawaan & metadata
def test_bawaan_booking_fee_verified_dan_bisa_ditimpa_per_proyek():
    row = next(r for r in ok(call(OWNER, "GET", "/settings", params={"q": KEY}))["data"] if r["key"] == KEY)
    assert row["default_value"] == BOOK, row["default_value"]
    assert row["levels"] == ["org", "project"]
    assert row["options"] == ["booking_fee_verified", "spr_signed", "ppjb_signed", "ajb_signed"]
    assert not row.get("unavailable"), "keempat opsi sudah berperilaku — tidak ada yang 'belum tersedia'"


def test_penimpaan_tingkat_proyek_diterima_server_dan_terbaca_efektif(world):
    pid = world.project_id
    try:
        ok(put("ppjb_signed", "project", pid))
        eff = ok(call(OWNER, "GET", "/settings/effective", params={"keys": KEY, "project_id": pid}))["data"]
        assert eff[KEY] == "ppjb_signed"
        assert put("ngawur", "project", pid).status_code == 400
        assert put("spr_signed", "cluster", "c1").status_code == 400, "tingkat klaster tidak diizinkan untuk kunci ini"
    finally:
        reset("project", pid)


# ================================================================== opsi 1 — bawaan: booking dikonfirmasi
def test_booking_fee_verified_pembeli_lahir_tepat_saat_booking_dikonfirmasi(world):
    d = deal_baru(world, fee=5_000_000, book=False)      # reservasi dengan booking fee, belum dibooking
    pre = ok(call(SALES, "GET", f"/deals/{d['deal_id']}/convert-preview"))["data"]
    assert pre["trigger"] == BOOK and pre["trigger_met"] is False
    assert any(b["code"] == "deal_belum_booking" for b in pre["blocks"])
    belum_pembeli(d, "(reservasi)")
    bayar_bf(d["deal_id"])                                # booking fee terverifikasi/lunas — BELUM booking dikonfirmasi
    belum_pembeli(d, "(booking fee lunas tetapi belum dikonfirmasi)")
    ok(call(SALES, "POST", f"/deals/{d['deal_id']}/book", json={}))
    kontrak, pembeli = tepat_satu(d)
    assert pembeli["lead_id"] == d["lead_id"] and kontrak["deal_id"] == d["deal_id"]
    # tugas administrasi hasil konversi ikut lahir sekali
    assert mdb().tasks.count_documents({"source_event": f"contract.costs:{kontrak['id']}"}) == 1
    # idempoten: konversi manual & booking ulang tidak menggandakan apa pun
    again = ok(call(SALES, "POST", f"/deals/{d['deal_id']}/convert", json={}))["data"]
    assert again["created"] is False and again["contract"]["id"] == kontrak["id"] and again["customer"]["id"] == pembeli["id"]
    assert call(SALES, "POST", f"/deals/{d['deal_id']}/book", json={}).status_code == 400
    tepat_satu(d)


def test_booking_fee_verified_event_ganda_tidak_menggandakan(world):
    """Event `deal.booked` yang sama dikirim ulang (retry/dua worker) → dispatcher menanganinya, tetap satu kontrak & satu pembeli."""
    d = deal_baru(world)
    kontrak, pembeli = tepat_satu(d)
    ev_id = str(uuid.uuid4())
    org = mdb().deals.find_one({"id": d["deal_id"]})["org_id"]
    mdb().events.insert_one({"id": ev_id, "org_id": org, "type": "deal.booked", "entity_type": "deal", "entity_id": d["deal_id"],
                             "data": {}, "status": "pending", "retries": 0, "created_at": now()})
    end = time.time() + 40
    while time.time() < end and mdb().events.find_one({"id": ev_id})["status"] != "dispatched":
        time.sleep(1)
    assert mdb().events.find_one({"id": ev_id})["status"] == "dispatched"
    k2, p2 = tepat_satu(d)
    assert k2["id"] == kontrak["id"] and p2["id"] == pembeli["id"]


# ================================================================== opsi 2 — SPR ditandatangani
def test_spr_signed_pembeli_lahir_tepat_saat_spr_pertama_ditandatangani(world):
    pid = world.project_id
    d = None
    try:
        ok(put("spr_signed", "project", pid))
        d = deal_baru(world)                              # booking dikonfirmasi → TIDAK menjadi pembeli (pemicu proyek = SPR)
        belum_pembeli(d, "(booking dikonfirmasi, pemicu = SPR)")
        pre = ok(call(SALES, "GET", f"/deals/{d['deal_id']}/convert-preview"))["data"]
        assert pre["trigger"] == "spr_signed" and pre["trigger_met"] is False and "SPR ditandatangani" in (pre["note"] or "")
        ppjb = seed_doc(d, "PPJB")                        # dokumen lain yang ditandatangani bukan pemicunya
        tanda_tangan(ppjb)
        belum_pembeli(d, "(PPJB ditandatangani, pemicu = SPR)")
        spr = seed_doc(d, "SPR_CASH")
        tanda_tangan(spr)
        kontrak, _ = tepat_satu(d)
        tanda_tangan(spr, name="Penjual Uji", role="seller")   # tanda tangan kedua bukan peristiwa bisnis baru
        k2, _ = tepat_satu(d)
        assert k2["id"] == kontrak["id"]
        assert ok(call(SALES, "GET", f"/deals/{d['deal_id']}/convert-preview"))["data"]["trigger_met"] is True
    finally:
        reset("project", pid)
        if d:
            mdb().documents.delete_many({"title": {"$regex": "uji W1A"}, "deal_id": d["deal_id"]})


# ================================================================== opsi 3 — PPJB ditandatangani
def test_ppjb_signed_pembeli_lahir_tepat_saat_ppjb_ditandatangani_bukan_sebelumnya(world):
    pid = world.project_id
    d = None
    try:
        ok(put("ppjb_signed", "project", pid))
        d = deal_baru(world)
        belum_pembeli(d, "(booking, pemicu = PPJB)")
        spr = seed_doc(d, "SPR_CASH")
        tanda_tangan(spr)
        belum_pembeli(d, "(SPR ditandatangani, pemicu = PPJB)")
        ppjb = seed_doc(d, "PPJB")
        tanda_tangan(ppjb)
        kontrak, _ = tepat_satu(d)
        tanda_tangan(ppjb, name="Penjual Uji", role="seller")
        assert tepat_satu(d)[0]["id"] == kontrak["id"]
    finally:
        reset("project", pid)
        if d:
            mdb().documents.delete_many({"title": {"$regex": "uji W1A"}, "deal_id": d["deal_id"]})


# ================================================================== opsi 4 — AJB ditandatangani
def test_ajb_signed_pembeli_lahir_tepat_saat_ajb_ditandatangani_bukan_sebelumnya(world):
    pid = world.project_id
    d = None
    try:
        ok(put("ajb_signed", "project", pid))
        d = deal_baru(world)
        belum_pembeli(d, "(booking, pemicu = AJB)")
        for kode in ("SPR_CASH", "PPJB"):
            tanda_tangan(seed_doc(d, kode))
            belum_pembeli(d, f"({kode} ditandatangani, pemicu = AJB)")
        ajb = seed_doc(d, "AJB")
        tanda_tangan(ajb)
        kontrak, _ = tepat_satu(d)
        tanda_tangan(ajb, name="Penjual Uji", role="seller")
        assert tepat_satu(d)[0]["id"] == kontrak["id"]
    finally:
        reset("project", pid)
        if d:
            mdb().documents.delete_many({"title": {"$regex": "uji W1A"}, "deal_id": d["deal_id"]})


def test_pemicu_legal_kontrak_ppjb_ajb_idempoten_bila_pembeli_sudah_ada(world):
    """Pemicu `deal.ppjb`/`deal.ajb` (tahap legal kontrak) mengirim event ke penangan konversi: kontrak sudah ada → tak ada yang digandakan."""
    d = deal_baru(world)
    kontrak, pembeli = tepat_satu(d)
    org = mdb().deals.find_one({"id": d["deal_id"]})["org_id"]
    pid = world.project_id
    try:
        for trig, etype in (("ppjb_signed", "deal.ppjb"), ("ajb_signed", "deal.ajb")):
            ok(put(trig, "project", pid))
            ev_id = str(uuid.uuid4())
            mdb().events.insert_one({"id": ev_id, "org_id": org, "type": etype, "entity_type": "deal", "entity_id": d["deal_id"],
                                     "data": {}, "status": "pending", "retries": 0, "created_at": now()})
            end = time.time() + 40
            while time.time() < end and mdb().events.find_one({"id": ev_id})["status"] != "dispatched":
                time.sleep(1)
            assert mdb().events.find_one({"id": ev_id})["status"] == "dispatched", etype
            assert tepat_satu(d)[0]["id"] == kontrak["id"]
    finally:
        reset("project", pid)


# ================================================================== penimpaan per proyek
def test_penimpaan_proyek_mengalahkan_org_dan_proyek_lain_mengikuti_org(world, world2):
    try:
        ok(put("ajb_signed"))                                           # org: AJB
        ok(put(BOOK, "project", world.project_id))                       # proyek 1: booking dikonfirmasi
        a = deal_baru(world)                                             # proyek 1 → langsung jadi pembeli
        tepat_satu(a)
        b = deal_baru(world2)                                            # proyek 2 → ikut org (AJB) → belum
        belum_pembeli(b, "(proyek 2 mengikuti org = AJB)")
        eff2 = ok(call(OWNER, "GET", "/settings/effective", params={"keys": KEY, "project_id": world2.project_id}))["data"][KEY]
        assert eff2 == "ajb_signed"
        # konversi manual tetap sah kapan pun (keputusan sadar petugas), dengan catatan pemicu belum terjadi
        pre = ok(call(SALES, "GET", f"/deals/{b['deal_id']}/convert-preview"))["data"]
        assert pre["can_convert"] and pre["trigger"] == "ajb_signed" and pre["trigger_met"] is False and "AJB ditandatangani" in pre["note"]
        ok(call(SALES, "POST", f"/deals/{b['deal_id']}/convert", json={}))["data"]
        tepat_satu(b)
    finally:
        reset("project", world.project_id)
        reset()


# ================================================================== efek samping
def test_konversi_otomatis_tertahan_membuat_tugas_sales_sekali_dan_ditutup_saat_berhasil(world):
    d = deal_baru(world, book=False)
    src = f"convert.auto_blocked:{d['deal_id']}"
    mdb().leads.update_one({"id": d["lead_id"]}, {"$set": {"name": ""}})     # data diri kosong → konversi tertahan
    try:
        ok(call(SALES, "POST", f"/deals/{d['deal_id']}/book", json={}))
        belum_pembeli(d, "(data diri kosong)")
        tugas = list(mdb().tasks.find({"source_event": src}))
        assert len(tugas) == 1 and tugas[0]["status"] == "open" and tugas[0]["priority"] == "high", tugas
        assert tugas[0]["assigned_to"] == mdb().deals.find_one({"id": d["deal_id"]}).get("assigned_to")
    finally:
        mdb().leads.update_one({"id": d["lead_id"]}, {"$set": {"name": f"Uji W1A pulih {uuid.uuid4().hex[:5]}"}})
    ok(call(SALES, "POST", f"/deals/{d['deal_id']}/convert", json={}))["data"]
    tepat_satu(d)
    assert mdb().tasks.find_one({"source_event": src})["status"] == "done"


def test_dedup_pembeli_lama_membeli_unit_kedua_otomatis_satu_pembeli_dua_kontrak(world):
    a = deal_baru(world, book=False)
    b = deal_baru(world, book=False)
    la = mdb().leads.find_one({"id": a["lead_id"]})
    nik = "32" + str(uuid.uuid4().int)[:14]
    ok(call(SALES, "POST", f"/deals/{a['deal_id']}/book", json={}))            # pembeli A lahir otomatis saat booking
    _, pa = tepat_satu(a)
    mdb().customers.update_one({"id": pa["id"]}, {"$set": {"nik": nik}})      # KYC pembeli dilengkapi kemudian
    # orang yang SAMA membeli unit kedua (telepon lead unik per org, jadi kesamaan dibuktikan lewat NIK + nama)
    mdb().leads.update_one({"id": b["lead_id"]}, {"$set": {"nik": nik, "name": la["name"]}})
    ok(call(SALES, "POST", f"/deals/{b['deal_id']}/book", json={}))
    pembeli = list(mdb().customers.find({"$or": [{"lead_ids": a["lead_id"]}, {"lead_ids": b["lead_id"]}]}))
    assert len(pembeli) == 1, f"satu manusia = satu baris pembeli, dapat {len(pembeli)}"
    assert set(pembeli[0]["lead_ids"]) == {a["lead_id"], b["lead_id"]}
    ca, cb = contracts_of(a["deal_id"]), contracts_of(b["deal_id"])
    assert len(ca) == 1 and len(cb) == 1 and ca[0]["customer_id"] == cb[0]["customer_id"] == pembeli[0]["id"]


def test_skema_bawaan_sistem_tidak_ditebak_konversi_otomatis_menunggu_pilihan_sales(world):
    """KT-21: skema yang hanya BAWAAN (sales tidak memilih) boleh disesuaikan saat 'Jadikan Pembeli' — pemicu otomatis tidak
    membuat kontrak dari tebakan; sales diberi tugas, lalu konversi manual dengan skema pilihannya berhasil."""
    unit = world.units[world.next_unit]
    world.next_unit += 1
    phone = "+62812" + str(int(time.time() * 1000))[-9:]
    lead = ok(call(SALES, "POST", "/leads", json={"name": f"Uji W1A tanpa skema {uuid.uuid4().hex[:5]}", "phone": phone,
                                                  "source": "manual"}))["data"]
    deal = ok(call(SALES, "POST", "/deals/reserve", json={"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0}))["data"]
    d = {"deal_id": deal["id"], "lead_id": lead["id"], "unit_id": unit["id"]}
    ok(call(SALES, "POST", f"/deals/{d['deal_id']}/book", json={}))
    belum_pembeli(d, "(skema masih bawaan sistem)")
    t = mdb().tasks.find_one({"source_event": f"convert.auto_blocked:{d['deal_id']}"})
    assert t and t["status"] == "open" and "BAWAAN" in t["description"], t
    pre = ok(call(SALES, "GET", f"/deals/{d['deal_id']}/convert-preview"))["data"]
    assert pre["deal_scheme_explicit"] is False and pre["can_convert"] is True
    conv = ok(call(SALES, "POST", f"/deals/{d['deal_id']}/convert", json={"scheme": "cash_keras"}))["data"]
    assert conv["created"] is True and conv["contract"]["scheme"] == "cash_keras"
    tepat_satu(d)
    assert mdb().tasks.find_one({"source_event": f"convert.auto_blocked:{d['deal_id']}"})["status"] == "done"


def test_batal_reservasi_sesudah_konversi_otomatis_saat_booking_tetap_bersih(world):
    """Dampak bawaan baru: kontrak sudah ada sejak booking. Pembatalan satu klik deal tanpa pembayaran termin menutup kontrak,
    tugas administrasi hasil konversi, melepas unit — dan lead yang sempat `won` mundur (bukan pembeli lagi)."""
    d = deal_baru(world)
    kontrak, pembeli = tepat_satu(d)
    kyc = f"customer.kyc:{pembeli['id']}"
    biaya = f"contract.costs:{kontrak['id']}"
    assert mdb().tasks.find_one({"source_event": biaya, "status": "open"}), "tugas hasil konversi lahir"
    ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji W1A batal setelah konversi otomatis"}))
    assert mdb().contracts.find_one({"id": kontrak["id"]})["state"] == "cancelled"
    assert mdb().units.find_one({"id": d["unit_id"]})["status"] == "available"
    assert mdb().deals.find_one({"id": d["deal_id"]})["status"] == "cancelled"
    assert mdb().tasks.find_one({"source_event": biaya})["status"] == "cancelled"
    assert all(t["status"] == "cancelled" for t in mdb().tasks.find({"source_event": kyc}))
    assert stage_of(d["lead_id"]) == "nurturing", "lead tidak boleh tertinggal `won` padahal reservasinya batal"


def test_batal_satu_klik_deal_berbayar_yang_sudah_jadi_pembeli_menunjuk_pembatalan_formal(world):
    """Booking fee yang dialihkan ke piutang termin + kontrak sudah ada (bawaan baru) → pesan menunjuk Pembatalan Kontrak formal."""
    d = deal_baru(world, fee=5_000_000, book=False)
    bayar_bf(d["deal_id"])
    ok(call(SALES, "POST", f"/deals/{d['deal_id']}/book", json={}))
    tepat_satu(d)
    pv = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}/cancel-preview"))["data"]
    if pv["can_cancel"]:
        pytest.skip("instance ini tidak mengalihkan booking fee ke piutang termin")
    assert "Pembatalan Kontrak formal" in pv["blocked_reason"], pv["blocked_reason"]


def test_rekonsiliasi_hijau_setelah_semua_skenario_pemicu():
    assert reconcile_ok(), ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
