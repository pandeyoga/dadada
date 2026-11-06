"""Regresi F2b — izin & penyalahgunaan di luar lingkup org (audit AZ-04, AZ-05, AZ-06, AZ-07, AZ-08, AZ-09, AZ-10).

    API_BASE=http://localhost:8061/api python -m pytest backend/tests/p0/test_p0_otorisasi_lain.py -n 0 -q --noconftest

Data uji berawalan "F2b"; tidak ada yang dihapus dari data bersama.
"""
import io
import time
import uuid

import pytest
import requests

from test_p0_masuk import API, MANAGER, OWNER, SALES, World, _login, call, ok

SALES2 = "sales2@sipro.co.id"
DM = "dm@sipro.co.id"
SITE = "site@sipro.co.id"
TAG = uuid.uuid4().hex[:6]


@pytest.fixture(scope="module")
def world():
    return World()


def _phone():
    return "+62812" + str(time.time_ns())[-9:]


# ------------------------------------------------------------------ AZ-04 — KPR milik sales lain
def test_sales_lain_tidak_bisa_mengubah_kpr_milik_sales(world):
    d = world.new_deal()
    fa = ok(call(SALES, "POST", "/financing", json={
        "deal_id": d["deal_id"], "bank_name": "BTN", "plafon": 300_000_000, "dp_amount": 50_000_000}))["data"]
    r1 = call(SALES2, "PUT", f"/financing/{fa['id']}", json={"dp_amount": 1})
    r2 = call(SALES2, "POST", f"/financing/{fa['id']}/slik", json={"slik_status": "rejected"})
    assert r1.status_code in (403, 404) and r2.status_code in (403, 404), (r1.status_code, r1.text[:100], r2.status_code)
    now = ok(call(OWNER, "GET", f"/financing/{fa['id']}"))["data"]
    assert int(now["dp_amount"]) == 50_000_000 and now.get("slik_status") != "rejected"
    # pemilik sah tetap boleh
    assert call(SALES, "PUT", f"/financing/{fa['id']}", json={"dp_amount": 60_000_000}).status_code == 200


# ------------------------------------------------------------------ AZ-05 — nilai referensi master
@pytest.mark.parametrize("peran", [DM, SITE, SALES2])
def test_peran_biasa_tidak_bisa_menambah_nilai_referensi_master(peran):
    r = call(peran, "POST", "/reference/financing_bank/values", json={"value": f"Bank F2b {TAG} {peran[:3]}"})
    assert r.status_code == 403, f"{peran}: {r.status_code} {r.text[:120]}"


def test_pemilik_tetap_boleh_menambah_nilai_referensi_master():
    r = call(OWNER, "POST", "/reference/financing_bank/values", json={"value": f"Bank F2b {TAG}"})
    assert r.status_code == 200, r.text[:160]


# ------------------------------------------------------------------ AZ-06 — kirim WA & template dokumen
def test_sales_lain_tidak_bisa_kirim_dokumen_wa_ke_lead_orang_lain(world):
    lead = ok(call(SALES, "POST", "/leads", json={"name": f"F2b {TAG}", "phone": _phone(), "source": "manual"}))["data"]
    r = call(SALES2, "POST", "/doc-history/send-wa", json={
        "entity_type": "lead", "entity_id": lead["id"], "pdf_url": "/api/documents/x/pdf", "label": "SPKT"})
    assert r.status_code in (403, 404), f"{r.status_code} {r.text[:160]}"


def test_sales_tidak_bisa_mengubah_template_dokumen_buatan_orang_lain():
    code = f"F2B{TAG}".upper()
    t = ok(call(SALES, "POST", "/master/doc-templates", json={"code": code, "name": f"Template {TAG}", "content": "isi"}))["data"]
    r = call(SALES2, "PUT", f"/master/doc-templates/{t['id']}", json={"content": "DIUBAH SALES LAIN"})
    assert r.status_code == 403, f"{r.status_code} {r.text[:160]}"
    r2 = call(SALES2, "DELETE", f"/master/doc-templates/{t['id']}")
    assert r2.status_code in (403, 404), r2.status_code
    assert call(SALES, "PUT", f"/master/doc-templates/{t['id']}", json={"content": "isi baru oleh pembuat"}).status_code == 200


# ------------------------------------------------------------------ AZ-07 — berkas HTML tidak dirender
def _png():
    import struct
    import zlib

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * 8 for _ in range(8))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _upload(name, data, ctype):
    r = requests.post(f"{API}/files/upload", headers={"Authorization": f"Bearer {_login(SALES)}"},
                      files={"file": (name, io.BytesIO(data), ctype)},
                      data={"owner_type": "generic", "optimize": "false"}, timeout=60)
    assert r.status_code == 200, r.text[:200]
    return r.json()["data"]["id"] if "data" in r.json() else r.json()["id"]


def _get(fid):
    return requests.get(f"{API}/files/{fid}", headers={"Authorization": f"Bearer {_login(SALES)}"}, timeout=60)


def test_html_dan_svg_disajikan_sebagai_unduhan_bukan_dirender():
    for name, ctype, body in (("xss.html", "text/html", b"<script>document.title='x'</script>"),
                              ("xss.svg", "image/svg+xml", b"<svg xmlns='http://www.w3.org/2000/svg'><script>1</script></svg>")):
        r = _get(_upload(name, body, ctype))
        assert r.status_code == 200
        assert r.headers.get("Content-Disposition", "").startswith("attachment"), (name, r.headers.get("Content-Disposition"))
        assert r.headers.get("X-Content-Type-Options") == "nosniff"


def test_gambar_png_tetap_inline_untuk_tampilan_ui():
    r = _get(_upload("bukti.png", _png(), "image/png"))
    assert r.status_code == 200
    assert r.headers.get("Content-Disposition", "").startswith("inline"), r.headers.get("Content-Disposition")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


# ------------------------------------------------------------------ AZ-08 — regex pencarian tidak menjatuhkan server
@pytest.mark.parametrize("path", ["/permits", "/subcon/subcontractors", "/gl/journals", "/fund-requests",
                                  "/bank/transactions", "/vendors", "/contracts", "/masterplan/units"])
def test_pencarian_dengan_karakter_regex_tidak_500(path):
    for q in ("[", "(", "a(b", ".*+?"):
        r = call(OWNER, "GET", path, params={"q": q})
        assert r.status_code < 500, f"{path}?q={q}: {r.status_code} {r.text[:120]}"


# ------------------------------------------------------------------ AZ-09 — formulir web publik dibatasi laju
def test_formulir_web_publik_dibatasi_laju():
    statuses = []
    for i in range(70):
        r = requests.post(f"{API}/webhooks/web", json={"name": f"F2b {TAG} {i}", "phone": _phone(),
                                                       "message": "uji batas laju"}, timeout=30)
        statuses.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in statuses, f"70 kiriman beruntun tidak pernah dibatasi: {sorted(set(statuses))}"


# ------------------------------------------------------------------ AZ-10 — OTP portal terkunci setelah 5 salah
def test_otp_portal_terkunci_setelah_lima_kode_salah():
    phone = _phone()
    ok(call(SALES, "POST", "/customers", json={"name": f"Pembeli F2b {TAG}", "phone": phone}))
    r = requests.post(f"{API}/portal/auth/request-otp", json={"identifier": phone}, timeout=30)
    if r.status_code != 200 or not (r.json().get("dev_code")):
        pytest.skip(f"OTP tidak tersedia pada mode ini: {r.status_code} {r.text[:100]}")
    code = r.json()["dev_code"]
    # .env uji memasang PORTAL_MASTER_OTP=000000 — kode salah harus BUKAN master dan BUKAN kode asli
    wrong = next(c for c in ("918273", "364758") if c != code)
    res = [requests.post(f"{API}/portal/auth/verify-otp", json={"identifier": phone, "code": wrong}, timeout=30).status_code
           for _ in range(5)]
    assert res[:4] == [400] * 4 and res[4] == 429, res
    good = requests.post(f"{API}/portal/auth/verify-otp", json={"identifier": phone, "code": code}, timeout=30)
    assert good.status_code in (400, 429), f"kode benar masih berlaku setelah dikunci: {good.status_code} {good.text[:100]}"
