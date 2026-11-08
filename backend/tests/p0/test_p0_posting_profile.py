"""Regresi H-D — Posting Profile Fase 1–2: katalog peristiwa, profil v0, dry-run, resolver BAYANGAN.

    API_BASE=http://localhost:8074/api DB_NAME=<db> MONGO_URL=<url> python -m pytest backend/tests/p0/test_p0_posting_profile.py -n 0 -q --noconftest

Bagian A (API, merah di kode lama karena endpoint belum ada): katalog, dry-run, read-only, izin.
Bagian B (dalam-proses, tanpa server): evaluator ekspresi terbatas, kesehatan katalog, properti seimbang, pembanding
bayangan (mendeteksi jurnal yang SALAH), `observe` tidak pernah melempar galat, cap jejak.
Ekuivalensi profil v0 ≡ kode lama ada di `test_p0_posting_profile_2.py`.
"""
import os
import random
import re
import sys

import pytest

from test_p0_masuk import FINANCE, OWNER, SALES, call, ok

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

# Contoh masukan konsisten per peristiwa `covered` (dipakai uji dry-run seluruh katalog).
SAMPLES = {
    "sales.receipt": {"amount": 100_000_000, "split_ar": 30_000_000, "split_penalty": 10_000_000},
    "sales.deposit_in": {"amount": 5_000_000},
    "sales.deposit_apply": {"amount": 5_000_000, "split_ar": 1_000_000},
    "sales.deposit_refund": {"amount": 2_000_000},
    "sales.revrec": {"revenue": 500_000_000, "cogs": 350_000_000, "cleared": 400_000_000, "wip_balance": 100_000_000},
    "sales.late_fee": {"amount": 750_000},
    "sales.late_fee_waive": {"amount": 750_000},
    "sales.receipt_void": {"amount": 60_000_000, "split_ar": 10_000_000},
    "cancel.decision": {"received_total": 100_000_000, "deposit_balance": 5_000_000, "cut_amount": 35_000_000,
                        "payable_total": 70_000_000},
    "cancel.refund_pay": {"amount": 30_000_000, "method": "tunai"},
    "ap.approve": {"claimed": 100_000_000, "net": 80_000_000, "retention": 5_000_000, "po_type": "subcon",
                   "accrual_balance": 40_000_000, "ded_advance": 10_000_000, "ded_penalty": 5_000_000},
    "ap.pay": {"amount": 50_000_000, "withheld": 1_000_000},
    "ap.pay_void": {"amount": 50_000_000, "withheld": 1_000_000},
    "commission.approve": {"amount": 12_000_000},
    "commission.pay": {"amount": 12_000_000},
    "mktfee.approve": {"gross": 10_000_000, "net": 9_750_000, "pph": 250_000},
    "mktfee.pay": {"amount": 9_750_000, "source": "kas"},
    "tax.accrue": {"amount": 8_000_000},
    "tax.deposit": {"amount": 8_000_000},
    "staff.advance_disburse": {"amount": 3_000_000, "source": "kas"},
    "staff.advance_settle": {"disbursed": 3_000_000, "exp_general": 2_000_000, "exp_wip": 1_500_000},
    "fixed_asset.acquire": {"cost": 20_000_000, "funding": "utang_usaha"},
    "fixed_asset.depreciate": {"amount": 416_667},
    "fixed_asset.dispose": {"cost": 20_000_000, "accum": 5_000_000, "proceeds": 17_000_000},
}


def dry(inputs_event, inputs, user=FINANCE):
    r = call(user, "POST", "/gl/posting-profile/dry-run", json={"event": inputs_event, "inputs": inputs})
    return r


# ================================================================ A. API: katalog
def test_katalog_menampilkan_peristiwa_dan_cakupan_jujur():
    d = ok(call(FINANCE, "GET", "/gl/posting-profile/catalog"))["data"]
    assert d["read_only"] is True and d["profile_version"] == "v0"
    evs = {e["key"]: e for e in d["events"]}
    cov = d["coverage"]
    assert cov["events_total"] == len(evs) and cov["covered"] + cov["uncovered"] == len(evs)
    assert cov["covered"] == sum(1 for e in evs.values() if e["covered"])
    assert sorted(cov["uncovered_keys"]) == sorted(k for k, e in evs.items() if not e["covered"])
    # peristiwa sentral yang diminta tugas HARUS ada dan covered
    for k in ("sales.receipt", "sales.deposit_in", "sales.revrec", "ap.approve", "ap.pay", "commission.approve",
              "mktfee.approve", "staff.advance_disburse", "fixed_asset.depreciate", "tax.accrue", "cancel.refund_pay"):
        assert evs[k]["covered"] is True, k
    for k, e in evs.items():   # kejujuran: covered ⇒ punya baris + bukti; tidak covered ⇒ tanpa baris + alasan
        if e["covered"]:
            assert e["lines"] and e["evidence"], k
        else:
            assert not e["lines"] and e["why_not"], k
    roles = {r["role"]: r for r in d["roles"]}
    assert roles["CONTRACT_LIABILITY"]["code"] == "2-1400" and roles["CONTRACT_LIABILITY"]["exists"]
    assert all(r["active"] and r["type_ok"] for r in roles.values()), [r for r in roles.values() if not r["type_ok"]]
    assert any("sales.receipt" in r["used_by"] for r in roles.values())


def test_katalog_memuat_semua_source_type_yang_diposting_kode():
    """Pagar anti-drift: setiap `source_type` yang diposting modul uang HARUS dikenal katalog (covered atau tidak)."""
    d = ok(call(FINANCE, "GET", "/gl/posting-profile/catalog"))["data"]
    known = {s[0] for e in d["events"] for s in e["sources"]}
    found = set()
    consts = {}
    for base, _dirs, files in os.walk(BACKEND):
        if any(x in base for x in ("/tests", "__pycache__", "/.venv")):
            continue
        for f in files:
            if not f.endswith(".py") or f.startswith(("seed", "backend_test", "test_")):
                continue
            src = open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()
            found |= set(re.findall(r"source_type\s*=\s*\"([a-z_]+)\"", src))
            for name, val in re.findall(r"^(SOURCE_TYPE|YEAR_CLOSING_SOURCE)\s*=\s*\"([a-z_]+)\"", src, re.M):
                consts[name] = val
    found |= set(consts.values())
    assert found, "pemindaian tidak menemukan satu pun source_type — uji ini rusak"
    assert not (found - known), f"source_type diposting kode tetapi tidak ada di katalog posting profile: {found - known}"


def test_dry_run_penerimaan_dengan_split_piutang_dan_denda():
    r = ok(dry("sales.receipt", {"amount": 100_000_000, "split_ar": 30_000_000, "split_penalty": 10_000_000}))["data"]
    assert r["ok"] and r["balanced"] and r["read_only"] and r["covered"]
    assert r["total_debit"] == r["total_credit"] == 100_000_000
    by = {(ln["side"], ln["account_code"]): ln for ln in r["lines"]}
    assert by[("K", "2-1400")]["credit"] == 60_000_000 and by[("K", "1-1300")]["credit"] == 40_000_000
    cash = next(ln for ln in r["lines"] if ln["cash"])
    assert cash["side"] == "D" and cash["debit"] == 100_000_000 and cash["account_code"].startswith("1-12")
    assert cash["account_name"] and cash["account_type"] == "asset" and not cash["checks"]
    assert any(w for w in r["warnings"] if "GL-01" in w), "cacat yang disalin v0 harus diberi peringatan"


def test_dry_run_metode_tunai_memilih_kas_bukan_bank():
    r = ok(dry("sales.receipt", {"amount": 1_000_000, "method": "tunai"}))["data"]
    cash = next(ln for ln in r["lines"] if ln["cash"])
    assert r["cash_kind"] == "cash" and cash["account_code"].startswith("1-11"), cash


def test_dry_run_setiap_peristiwa_covered_menghasilkan_jurnal_seimbang_di_coa_nyata():
    cat = ok(call(FINANCE, "GET", "/gl/posting-profile/catalog"))["data"]
    covered = {e["key"] for e in cat["events"] if e["covered"]}
    assert covered == set(SAMPLES), f"contoh uji harus lengkap: {covered ^ set(SAMPLES)}"
    for key, inp in SAMPLES.items():
        r = ok(dry(key, inp))["data"]
        assert r["ok"] and r["balanced"], (key, r["errors"])
        assert r["total_debit"] == r["total_credit"] > 0, key
        assert all(not ln["checks"] for ln in r["lines"]), (key, r["lines"])


def test_dry_run_menolak_masukan_buruk_dengan_pesan_jelas():
    assert call(FINANCE, "POST", "/gl/posting-profile/dry-run", json={"event": "tidak.ada", "inputs": {}}).status_code == 404
    r = ok(dry("sales.receipt", {}))["data"]
    assert not r["ok"] and "wajib" in r["errors"][0] and r["lines"] == []
    assert not ok(dry("sales.receipt", {"amount": -5}))["data"]["ok"]
    assert "bilangan bulat" in ok(dry("sales.receipt", {"amount": "seratus"}))["data"]["errors"][0]
    assert "bilangan bulat" in ok(dry("sales.receipt", {"amount": 10.5}))["data"]["errors"][0]
    # piutang melebihi jumlah → baris negatif ditolak, bukan jurnal ngawur
    bad = ok(dry("sales.receipt", {"amount": 10, "split_ar": 50}))["data"]
    assert not bad["ok"] and "negatif" in bad["errors"][0]
    # masukan tidak konsisten (klaim ≠ neto + retensi) → tidak seimbang
    unb = ok(dry("ap.approve", {"claimed": 100, "net": 80, "retention": 5}))["data"]
    assert not unb["ok"] and not unb["balanced"] and "tidak seimbang" in " ".join(unb["errors"])
    # peristiwa belum dicakup → tidak ada klaim palsu
    unc = ok(dry("loan.disburse", {"principal": 1}))["data"]
    assert not unc["ok"] and not unc["covered"] and "Belum punya profil" in unc["errors"][0]
    # isian bersarang ditolak; isian tak dikenal hanya peringatan
    assert call(FINANCE, "POST", "/gl/posting-profile/dry-run",
                json={"event": "sales.receipt", "inputs": {"amount": {"x": 1}}}).status_code == 400
    extra = ok(dry("sales.receipt", {"amount": 5, "ngawur": 1}))["data"]
    assert extra["ok"] and any("ngawur" in w for w in extra["warnings"])


def test_profil_tidak_bisa_diubah_lewat_api_pada_fase_ini():
    for method in ("PUT", "PATCH", "DELETE", "POST"):
        r = call(OWNER, method, "/gl/posting-profile/catalog", json={"events": []})
        assert r.status_code in (404, 405), (method, r.status_code)
    r = call(OWNER, "GET", "/gl/posting-profile/catalog")
    assert r.status_code == 200
    # katalog sama sebelum & sesudah percobaan menulis
    assert r.json()["data"]["coverage"]["covered"] == ok(call(FINANCE, "GET", "/gl/posting-profile/catalog"))["data"]["coverage"]["covered"]


def test_izin_tanpa_hak_gl_ditolak():
    for method, path, body in [("GET", "/gl/posting-profile/catalog", None),
                               ("POST", "/gl/posting-profile/dry-run", {"event": "sales.receipt", "inputs": {"amount": 1}}),
                               ("GET", "/gl/posting-profile/shadow-report", None),
                               ("GET", "/gl/posting-profile/verify/xyz", None)]:
        r = call(SALES, method, path, json=body)
        assert r.status_code == 403, (path, r.status_code)
    import requests
    base = os.environ.get("API_BASE", "http://localhost:8074/api").rstrip("/")
    assert requests.get(base + "/gl/posting-profile/catalog", timeout=20).status_code in (401, 403)


def test_laporan_bayangan_bentuk_dan_verifikasi_jurnal_tidak_ada():
    rep = ok(call(FINANCE, "GET", "/gl/posting-profile/shadow-report"))["data"]
    assert rep["profile_version"] == "v0" and isinstance(rep["enabled"], bool) and rep["env_flag"] == "POSTING_SHADOW"
    assert {e["event"] for e in rep["events"]} >= set(SAMPLES) and "diffs_total" in rep
    assert call(FINANCE, "GET", "/gl/posting-profile/verify/jurnal-tidak-ada").status_code == 404


# ================================================================ B. dalam-proses: evaluator & katalog
pytest.importorskip("motor")


def _pp():
    import posting_profile as pp
    return pp


def test_ekspresi_hanya_aritmetika_terbatas_tanpa_eval():
    pp = _pp()
    for jahat in ("__import__('os').system('id')", "amount.real", "(1).__class__", "[x for x in amount]",
                  "lambda: 1", "open('/etc/passwd')", "amount ** 9", "amount / 3", "x" * 300, "", "amount;1"):
        with pytest.raises(pp.ProfileError):
            pp.compile_expr(jahat)
    assert pp.run_expr("max(0, a - b) + min(a, b)", {"a": 7, "b": 3}) == 7
    assert pp.run_expr("'x' if a > 1 else 'y'", {"a": 2}) == "x"
    assert pp.run_expr("t not in ['a', 'b']", {"t": "c"}) is True
    with pytest.raises(pp.ProfileError):
        pp.run_expr("zzz + 1", {"a": 1})


def test_katalog_sehat_dan_selaras_dengan_bagan_akun_standar():
    pp = _pp()
    import gl_engine
    assert pp.CATALOG_ERRORS == [] and pp.validate_catalog() == []
    std = {c: t for c, _n, t in gl_engine.STANDARD_COA}
    roles = {r["code"]: r["type"] for r in pp.ROLES.values()}
    assert roles == std, f"peran akun v0 harus 1:1 dengan CoA standar: {set(roles) ^ set(std)}"
    for e in pp.EVENTS.values():
        if e["covered"]:
            assert os.path.exists(os.path.join(BACKEND, e["evidence"])), e["key"]
            assert e["key"] in SAMPLES
    # profil v0 tidak mengandung kode akun literal di baris — hanya nama peran
    assert not any(re.search(r"\d-\d{4}", str(ln)) for e in pp.EVENTS.values() for ln in (e["lines"] or []))


def test_evaluate_menolak_peristiwa_tak_dicakup_dan_masukan_salah():
    pp = _pp()
    with pytest.raises(pp.ProfileError):
        pp.evaluate("loan.disburse", {})
    with pytest.raises(pp.ProfileError):
        pp.evaluate("tidak.ada", {})
    with pytest.raises(pp.ProfileError):
        pp.evaluate("fixed_asset.acquire", {"cost": 5, "funding": "barter"})
    with pytest.raises(pp.ProfileError):
        pp.evaluate("sales.receipt", {"amount": True})


def test_properti_semua_rumus_menghasilkan_jurnal_seimbang():
    pp = _pp()
    rnd = random.Random(20261108)
    for _ in range(300):
        a = rnd.randint(1, 900) * 1_000
        ar, pen = rnd.randint(0, a // 2000) * 1000, rnd.randint(0, a // 2000) * 1000
        cases = [
            ("sales.receipt", {"amount": a, "split_ar": ar, "split_penalty": pen}),
            ("sales.deposit_apply", {"amount": a, "split_ar": ar}),
            ("sales.receipt_void", {"amount": a, "split_ar": ar}),
            ("sales.revrec", {"revenue": a, "cogs": rnd.randint(0, 900) * 1000, "cleared": rnd.randint(0, 900) * 1000,
                              "wip_balance": rnd.randint(0, 900) * 1000}),
            ("fixed_asset.dispose", {"cost": a, "accum": rnd.randint(0, a // 1000) * 1000,
                                     "proceeds": rnd.randint(0, 1000) * 1000}),
            ("staff.advance_settle", {"disbursed": a, "exp_general": rnd.randint(0, 900) * 1000,
                                      "exp_wip": rnd.randint(0, 300) * 1000, "exp_marketing": rnd.randint(0, 100) * 1000}),
            ("ap.pay", {"amount": a, "withheld": rnd.randint(0, a // 1000) * 100}),
        ]
        for key, inp in cases:
            if key == "fixed_asset.dispose" and inp["accum"] > inp["cost"]:
                continue
            lines = pp.evaluate(key, inp)["lines"]
            d = sum(x["amount"] for x in lines if x["side"] == "D")
            k = sum(x["amount"] for x in lines if x["side"] == "K")
            assert d == k, (key, inp, lines)


class _RO:
    """DB palsu READ-ONLY: hanya find/find_one pada accounts & bank_accounts; metode lain = galat (tulis dilarang)."""
    calls = []

    def __init__(self):
        from posting_profile import ROLES
        self._acc = [{"code": r["code"], "name": r["label"], "type": r["type"], "is_active": True,
                          "parent_code": None} for r in ROLES.values()]
        self._acc += [{"code": "1-1201", "name": "Bank uji", "type": "asset", "is_active": True, "parent_code": "1-1200"},
                          {"code": "1-1101", "name": "Kas uji", "type": "asset", "is_active": True, "parent_code": "1-1100"}]
        self._banks = {"bank": {"id": "b1", "kind": "bank", "gl_account_code": "1-1201", "is_default": True, "name": "B"},
                      "cash": {"id": "k1", "kind": "cash", "gl_account_code": "1-1101", "is_default": True, "name": "K"}}

    def __getattr__(self, coll):
        outer = self

        class C:
            def find(self, q=None, proj=None):
                _RO.calls.append((coll, "find"))

                class Cur:
                    async def to_list(_s, n):
                        return outer._acc
                return Cur()

            async def find_one(self, q, proj=None, **kw):
                _RO.calls.append((coll, "find_one"))
                return outer._banks.get((q or {}).get("kind")) if coll == "bank_accounts" else None

            def __getattr__(self, m):
                raise AssertionError(f"dry-run tidak boleh memanggil {coll}.{m} (read-only)")
        return C()


def test_dry_run_hanya_membaca_tidak_pernah_menulis(monkeypatch):
    import aio
    import posting_profile as pp
    monkeypatch.setattr(pp, "db", _RO())
    for key, inp in SAMPLES.items():
        r = aio.run(pp.dry_run("o-uji", key, inp))
        assert r["ok"] and r["balanced"], (key, r["errors"])
    assert {c for _c, c in _RO.calls} <= {"find", "find_one"} and {c for c, _m in _RO.calls} <= {"accounts", "bank_accounts"}


def test_dry_run_menolak_akun_tak_ada_nonaktif_dan_tipe_salah(monkeypatch):
    import aio
    import posting_profile as pp
    ro = _RO()
    for a in ro._acc:
        if a["code"] == "2-1400":
            a["is_active"] = False          # nonaktif
        if a["code"] == "1-1300":
            a["type"] = "expense"           # tipe salah
    ro._acc = [a for a in ro._acc if a["code"] != "2-1450"]   # akun hilang
    monkeypatch.setattr(pp, "db", ro)
    r = aio.run(pp.dry_run("o-uji", "sales.receipt", {"amount": 10, "split_ar": 3}))
    msg = " ".join(r["errors"])
    assert not r["ok"] and "NONAKTIF" in msg and "bertipe expense" in msg
    r = aio.run(pp.dry_run("o-uji", "sales.deposit_in", {"amount": 10}))
    assert not r["ok"] and "tidak ada di Bagan Akun" in " ".join(r["errors"])
    ro._banks = {}
    r = aio.run(pp.dry_run("o-uji", "ap.pay", {"amount": 10}))
    assert not r["ok"] and "Belum ada rekening/kas bank" in " ".join(r["errors"])


# ================================================================ B. pembanding bayangan
def _view(lines):
    """Baris jurnal minimal -> format post_journal (untuk uji pembanding murni)."""
    return [{"account_code": c, "debit": d, "credit": k} for c, d, k in lines]


ACCTS = {"1-1201": {"parent_code": "1-1200"}, "1-1101": {"parent_code": "1-1100"}}


def test_pembanding_menyatakan_sama_untuk_jurnal_yang_benar_dan_mendeteksi_yang_salah():
    import posting_shadow as ps
    ok_lines = _view([("1-1201", 100, 0), ("2-1400", 0, 70), ("1-1300", 0, 30)])
    r = ps.compare("sales.receipt", ok_lines, ACCTS, {"amount": 100, "split_ar": 30, "split_penalty": 0})
    assert r["equal"] and r["diff"] == [] and r["mode"] == "hint"
    # kode lama keliru: piutang tertulis ke pendapatan -> SELISIH harus terdeteksi dan menyebut akunnya
    salah = _view([("1-1201", 100, 0), ("2-1400", 0, 70), ("4-1100", 0, 30)])
    r = ps.compare("sales.receipt", salah, ACCTS, {"amount": 100, "split_ar": 30, "split_penalty": 0})
    assert not r["equal"]
    assert {(d["side"], d["key"]) for d in r["diff"]} == {("K", "1-1300"), ("K", "4-1100")}
    # kas masuk ke KAS padahal masukan menyebut bank -> terdeteksi lewat kelas kas/bank
    r = ps.compare("sales.deposit_in", _view([("1-1101", 5, 0), ("2-1450", 0, 5)]), ACCTS,
                   {"amount": 5, "cash_kind": "bank"})
    assert not r["equal"] and {d["key"] for d in r["diff"]} == {"@cash", "@bank"}
    # tanpa petunjuk: masukan diturunkan dari baris -> jurnal benar tetap 'sama' (mode derived)
    r = ps.compare("ap.pay", _view([("2-1100", 50, 0), ("1-1201", 0, 49), ("2-1300", 0, 1)]), ACCTS)
    assert r["equal"] and r["mode"] == "derived" and r["inputs"]["withheld"] == 1
    # rumus keliru (kas tidak dikurangi PPh) -> terdeteksi
    r = ps.compare("ap.pay", _view([("2-1100", 50, 0), ("1-1201", 0, 50), ("2-1300", 0, 1)]), ACCTS)
    assert not r["equal"]
    # AP material tapi debit tertulis ke WIP -> hanya terdeteksi karena petunjuk eksplisit dari dokumen sumber
    wip = _view([("1-1600", 100, 0), ("2-1100", 0, 100)])
    hint = {"claimed": 100, "net": 100, "po_type": "material"}
    assert not ps.compare("ap.approve", wip, ACCTS, hint)["equal"]
    assert ps.compare("ap.approve", wip, ACCTS)["equal"], "tanpa petunjuk, jalur turunan tidak bisa tahu tipe PO"
    # masukan profil tak valid dilaporkan sebagai selisih bergalat, bukan exception
    r = ps.compare("sales.receipt", ok_lines, ACCTS, {"amount": 10, "split_ar": 50})
    assert not r["equal"] and "negatif" in r["error"]


def test_event_key_dan_cap_jejak():
    import posting_shadow as ps
    assert ps.event_key_of("receipt", "ev:123") == "sales.receipt"
    assert ps.event_key_of("deposit", "ev:1") is None, "tiga peristiwa berbagi sumber: butuh petunjuk"
    assert ps.event_key_of("deposit", "ev:1", "sales.deposit_refund") == "sales.deposit_refund"
    assert ps.event_key_of("cash_advance", "cashbon.settle:9") == "staff.advance_settle"
    assert ps.event_key_of("pdc", "pdc.clear.cash:9") == "pdc.clear_no_deal"
    assert ps.event_key_of("pdc", "pdc.bounced:9") == "pdc.reverse"
    assert ps.event_key_of("commission", "seed:komisi") is None and ps.event_key_of("zzz", "ev:1") is None
    doc = {"source_type": "tax_accrual", "source_event": "tax.accrue:1"}
    ps.stamp(doc)
    assert doc["profile_event"] == "tax.accrue" and doc["profile_version"] == "v0"
    unc = {"source_type": "loan", "source_event": "loan.activate:1"}
    ps.stamp(unc)
    assert unc["profile_event"] == "loan.disburse" and "profile_version" not in unc, "belum dicakup: tanpa versi profil"
    none = {"source_type": "manual", "source_event": None}
    ps.stamp(none, ("sales.receipt", {}))
    assert none["profile_event"] == "sales.receipt"
    ps.stamp({"source_type": "zzz", "source_event": "x"})   # tidak melempar


class _Boom:
    """db palsu: setiap akses koleksi melempar — membuktikan jalur mati tidak menyentuh DB & jalur hidup tidak melempar."""
    def __getattr__(self, name):
        raise RuntimeError("DB tidak boleh disentuh")


def test_observe_mati_tidak_menyentuh_db_dan_hidup_tidak_pernah_melempar(monkeypatch, caplog):
    import logging
    import aio
    import posting_shadow as ps
    doc = {"id": "j1", "entry_no": "JV-X", "source_type": "tax_accrual", "source_event": "tax.accrue:1",
           "lines": _view([("6-1400", 5, 0), ("2-1300", 0, 5)])}
    monkeypatch.setattr(ps, "db", _Boom())
    monkeypatch.delenv("POSTING_SHADOW", raising=False)
    assert ps.enabled() is False
    assert aio.run(ps.observe("o", doc, {})) is None            # mati: nol akses DB
    monkeypatch.setenv("POSTING_SHADOW", "1")
    with caplog.at_level(logging.ERROR, logger="sipro.posting_shadow"):
        assert aio.run(ps.observe("o", doc, {})) is None        # hidup + DB rusak: tetap tidak melempar
        assert aio.run(ps.observe("o", {"id": "x"}, {})) is None  # dokumen cacat: tetap tidak melempar
    assert any("gagal membandingkan" in r.getMessage() for r in caplog.records), "galat harus dicatat lewat logger"
    monkeypatch.setenv("POSTING_SHADOW", "0")
    assert ps.enabled() is False
