"""Mesin Posting Profile (Fase 1–2): peran akun, evaluator ekspresi terbatas, katalog, dry-run (read-only).

Data profil v0 ada di `posting_profile_v0.py`. Berkas ini TIDAK memposting apa pun dan tidak mengubah perilaku buku besar:
  * `evaluate(event, inputs)`  — murni (tanpa DB): masukan → baris jurnal menurut profil v0.
  * `dry_run(org, event, inputs)` — evaluate + cek keberadaan/aktif/tipe akun di Bagan Akun org + seimbang + peringatan.
  * `catalog(org)` — katalog peristiwa + peran akun + cakupan JUJUR (covered true/false).
Ekspresi nilai/kondisi dievaluasi oleh pengurai AST terbatas (tanpa eval/exec): angka, nama variabel yang dideklarasikan
peristiwa, + − × //, perbandingan, and/or/not, in/not in, if-else, dan min/max/abs.
"""
import ast
import logging
import operator

import coa_rules
import posting_profile_v0 as v0
from db import db

logger = logging.getLogger("sipro.posting_profile")
VERSION = v0.VERSION
CASH_KINDS = ("cash", "bank")


class ProfileError(ValueError):
    """Masukan/profil tidak valid (pesan Indonesia, aman ditampilkan ke pengguna)."""


# ------------------------------------------------------------------------------------------- peran akun
def _parse_roles() -> dict:
    out = {}
    for raw in v0.ROLE_TABLE.strip().splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        name, code, typ, label = raw.split(None, 3)
        out[name] = {"role": name, "code": code, "type": typ, "label": label.strip()}
    return out


ROLES = _parse_roles()
CODE_TO_ROLE = {r["code"]: n for n, r in ROLES.items()}
EVENTS = {e["key"]: e for e in v0.EVENTS}
HEADER_ROLES = ("CASH_DEFAULT", "BANK_DEFAULT")


# ------------------------------------------------------------------------------- ekspresi terbatas (AST)
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv}
_CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
        ast.Gt: operator.gt, ast.GtE: operator.ge, ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}
_FUNCS = {"min": min, "max": max, "abs": abs}
_CACHE: dict = {}


def compile_expr(expr: str):
    """Parse + validasi bentuk ekspresi; kembalikan (AST, himpunan nama yang dipakai)."""
    if expr in _CACHE:
        return _CACHE[expr]
    if not isinstance(expr, str) or not expr.strip() or len(expr) > 240:
        raise ProfileError(f"Ekspresi tidak valid: {expr!r}")
    try:
        tree = ast.parse(expr.strip(), mode="eval").body
    except SyntaxError as e:
        raise ProfileError(f"Ekspresi '{expr}' salah sintaks.") from e
    names = set()

    def walk(n):
        if isinstance(n, ast.Constant):
            if not isinstance(n.value, (int, str, bool, type(None))):
                raise ProfileError(f"Konstanta tidak diizinkan di '{expr}'.")
        elif isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            walk(n.left), walk(n.right)
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.Not)):
            walk(n.operand)
        elif isinstance(n, ast.BoolOp):
            [walk(v) for v in n.values]
        elif isinstance(n, ast.Compare) and all(type(o) in _CMP for o in n.ops):
            walk(n.left), [walk(c) for c in n.comparators]
        elif isinstance(n, ast.IfExp):
            walk(n.test), walk(n.body), walk(n.orelse)
        elif isinstance(n, (ast.List, ast.Tuple)):
            [walk(e) for e in n.elts]
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and not n.keywords:
            [walk(a) for a in n.args]
        else:
            raise ProfileError(f"Bagian ekspresi tidak diizinkan di '{expr}': {ast.dump(n)[:60]}")
    walk(tree)
    _CACHE[expr] = (tree, names)
    return _CACHE[expr]


def run_expr(expr: str, env: dict):
    tree, names = compile_expr(expr)

    def ev(n):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id not in env:
                raise ProfileError(f"Variabel '{n.id}' tidak tersedia pada ekspresi '{expr}'.")
            return env[n.id]
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.FloorDiv) and not b:
                raise ProfileError(f"Pembagian nol pada '{expr}'.")
            return _BIN[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else (not ev(n.operand))
        if isinstance(n, ast.BoolOp):
            vals = [ev(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, comp in zip(n.ops, n.comparators):
                right = ev(comp)
                if not _CMP[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, (ast.List, ast.Tuple)):
            return [ev(e) for e in n.elts]
        return _FUNCS[n.func.id](*[ev(a) for a in n.args])
    return ev(tree)


# --------------------------------------------------------------------------------------- validasi katalog
def validate_catalog() -> list:
    """Daftar kesalahan struktur katalog (kosong = sehat). Dipanggil saat impor & oleh tes."""
    errs, seen = [], set()
    for e in v0.EVENTS:
        k = e["key"]
        if k in seen:
            errs.append(f"{k}: kunci ganda")
        seen.add(k)
        if e["covered"] and not e["lines"]:
            errs.append(f"{k}: covered tanpa lines")
        if not e["covered"] and e["lines"]:
            errs.append(f"{k}: tidak covered tetapi punya lines (klaim tanpa bukti)")
        if e["covered"] and not e.get("evidence"):
            errs.append(f"{k}: covered tanpa bukti (evidence)")
        if not e["covered"] and not e.get("why_not"):
            errs.append(f"{k}: tidak covered tanpa alasan (why_not)")
        if not e["sources"]:
            errs.append(f"{k}: sumber (source_type) kosong")
        declared = set(e["vars"]) | set(e["let"]) | {"cash_kind"}
        try:
            for name, expr in e["let"].items():
                bad = compile_expr(expr)[1] - declared
                if bad:
                    errs.append(f"{k}: let.{name} memakai {sorted(bad)} yang tak dideklarasikan")
            for ln in e["lines"] or []:
                for expr in (ln["amount"], ln.get("when")):
                    if expr and compile_expr(expr)[1] - declared:
                        errs.append(f"{k}: baris memakai variabel tak dideklarasikan: {expr}")
                acc = ln["account"]
                if ln["side"] not in ("D", "K"):
                    errs.append(f"{k}: sisi tidak valid {ln['side']}")
                if acc != "cash" and not (acc.startswith("role:") and acc[5:] in ROLES):
                    errs.append(f"{k}: akun tidak dikenal {acc}")
                if acc.startswith("role:") and acc[5:] in HEADER_ROLES:
                    errs.append(f"{k}: induk kas/bank tidak boleh jadi peran baris — pakai 'cash'")
            for name, expr in e["derive"].items():
                if name not in e["vars"]:
                    errs.append(f"{k}: derive.{name} bukan variabel peristiwa")
                for ref in compile_expr(expr)[1]:   # nama jumlah baris terbit: D_/K_ + (PERAN | CASH | BANK)
                    if ref[:2] not in ("D_", "K_") or (ref[2:] not in ROLES and ref[2:] not in ("CASH", "BANK")):
                        errs.append(f"{k}: derive.{name} merujuk nama tak dikenal '{ref}'")
        except ProfileError as ex:
            errs.append(f"{k}: {ex}")
    for n, r in ROLES.items():
        if r["type"] not in ("asset", "liability", "equity", "revenue", "expense"):
            errs.append(f"peran {n}: tipe {r['type']} tidak valid")
        if r["type"] not in coa_rules.PREFIX_TYPES.get(r["code"][0], ()):
            errs.append(f"peran {n}: kode {r['code']} tidak cocok dengan tipe {r['type']}")
    if len(CODE_TO_ROLE) != len(ROLES):
        errs.append("kode akun ganda pada tabel peran (peran harus 1:1 dengan kode di v0)")
    return errs


# Katalog rusak = bug kode. Dicatat KERAS di log + tes `test_katalog_sehat`, tetapi TIDAK menjatuhkan server:
# gl_engine mengimpor modul ini, dan pembukuan tidak boleh berhenti karena data profil bayangan salah ketik.
CATALOG_ERRORS = validate_catalog()
if CATALOG_ERRORS:
    logger.error("Katalog posting profile v0 TIDAK VALID: %s", "; ".join(CATALOG_ERRORS))


# ------------------------------------------------------------------------------------------ evaluasi murni
def _bind(ev: dict, inputs: dict) -> tuple:
    """Gabung masukan dengan deklarasi `vars` (tipe, default, wajib). Return (env, diabaikan)."""
    inputs = inputs or {}
    if not isinstance(inputs, dict):
        raise ProfileError("'inputs' harus berupa objek {variabel: nilai}.")
    env, errs = {}, []
    for name, spec in ev["vars"].items():
        raw = inputs.get(name)
        if raw is None:
            if spec.get("required"):
                errs.append(f"'{name}' ({spec['label']}) wajib diisi")
            env[name] = spec.get("default")
            continue
        if spec["type"] == "int":
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or (
                    isinstance(raw, float) and not raw.is_integer()):
                errs.append(f"'{name}' harus bilangan bulat Rupiah")
                continue
            if int(raw) < 0:
                errs.append(f"'{name}' tidak boleh negatif")
                continue
            env[name] = int(raw)
        else:
            if not isinstance(raw, str):
                errs.append(f"'{name}' harus berupa teks")
                continue
            if spec.get("choices") and raw not in spec["choices"]:
                errs.append(f"'{name}' harus salah satu dari {spec['choices']}")
                continue
            env[name] = raw
    ck = inputs.get("cash_kind")
    if ck is not None and ck not in CASH_KINDS:
        errs.append("'cash_kind' harus 'cash' atau 'bank'")
    if errs:
        raise ProfileError("Masukan tidak valid: " + "; ".join(errs) + ".")
    ignored = sorted(k for k in inputs if k not in ev["vars"] and not (k == "cash_kind" and ev["cash_rule"]))
    return env, ignored


def cash_kind_of(ev: dict, env: dict, inputs: dict) -> str:
    """Jenis rekening untuk baris `cash`: eksplisit > aturan peristiwa (var/nilai kas) > bank."""
    if (inputs or {}).get("cash_kind") in CASH_KINDS:
        return inputs["cash_kind"]
    rule = ev.get("cash_rule") or {}
    if rule.get("fixed"):
        return rule["fixed"]
    if rule.get("var"):
        return "cash" if env.get(rule["var"]) in rule.get("cash_values", ()) else "bank"
    return "bank"


def evaluate(event_key: str, inputs: dict) -> dict:
    """Masukan → baris jurnal menurut profil v0. Murni: tanpa DB, tanpa efek samping."""
    ev = EVENTS.get(event_key)
    if not ev:
        raise ProfileError(f"Peristiwa '{event_key}' tidak ada di katalog.")
    if not ev["covered"]:
        raise ProfileError(f"Peristiwa '{event_key}' belum punya profil v0 yang teruji ({ev['why_not']}).")
    env, ignored = _bind(ev, inputs)
    kind = cash_kind_of(ev, env, inputs)
    env["cash_kind"] = kind
    for name, expr in ev["let"].items():
        env[name] = run_expr(expr, env)
    lines = []
    for ln in ev["lines"]:
        if ln.get("when") and not run_expr(ln["when"], env):
            continue
        amt = run_expr(ln["amount"], env)
        if isinstance(amt, bool) or not isinstance(amt, int):
            raise ProfileError(f"Nilai baris '{ln['amount']}' bukan bilangan bulat.")
        if amt < 0:
            raise ProfileError(f"Nilai baris '{ln['amount']}' negatif ({amt:,}) — masukan tidak konsisten.")
        if amt == 0:
            continue   # sama seperti post_journal: baris bernilai nol tidak diposting
        is_cash = ln["account"] == "cash"
        role = None if is_cash else ln["account"][5:]
        lines.append({"seq": len(lines) + 1, "side": ln["side"], "role": role, "cash": is_cash,
                      "cash_kind": kind if is_cash else None, "code": None if is_cash else ROLES[role]["code"],
                      "amount": amt, "memo": ln.get("memo")})
    return {"event": event_key, "profile_version": VERSION, "cash_kind": kind, "ignored_inputs": ignored,
            "lines": lines, "variables": {k: v for k, v in env.items() if isinstance(v, (int, str, type(None)))}}


def line_key(line: dict) -> str:
    """Kunci pembanding sebuah baris: kode akun, atau '@cash'/'@bank' untuk baris rekening kas/bank."""
    return f"@{line['cash_kind']}" if line.get("cash") else line["code"]


def aggregate(lines: list) -> dict:
    """{(sisi, kunci): total} — urutan & memo diabaikan; beberapa baris pada akun sama dijumlahkan."""
    out: dict = {}
    for ln in lines:
        k = (ln["side"], line_key(ln))
        out[k] = out.get(k, 0) + int(ln["amount"])
    return out


# ------------------------------------------------------------------------------------ katalog & dry-run
def coverage() -> dict:
    evs = list(EVENTS.values())
    by_mod: dict = {}
    for e in evs:
        m = by_mod.setdefault(e["module"], {"module": e["module"], "events": 0, "covered": 0})
        m["events"] += 1
        m["covered"] += 1 if e["covered"] else 0
    cov = sum(1 for e in evs if e["covered"])
    return {"events_total": len(evs), "covered": cov, "uncovered": len(evs) - cov,
            "covered_pct": round(100.0 * cov / len(evs), 1) if evs else 0.0,
            "uncovered_keys": sorted(e["key"] for e in evs if not e["covered"]),
            "by_module": list(by_mod.values())}


def _public_event(e: dict) -> dict:
    return {"key": e["key"], "label": e["label"], "module": e["module"], "trigger": e["trigger"],
            "covered": e["covered"], "sources": e["sources"], "vars": e["vars"], "let": e["let"],
            "cash_rule": e["cash_rule"], "lines": e["lines"], "defects": e["defects"],
            "evidence": e["evidence"], "why_not": e["why_not"], "note": e["note"]}


async def role_status(org_id: str) -> list:
    """Peran akun + status di Bagan Akun org (ada / aktif / tipe cocok) — 1 query."""
    accts = {a["code"]: a for a in await db.accounts.find(
        {"org_id": org_id}, {"_id": 0, "code": 1, "name": 1, "type": 1, "is_active": 1}).to_list(2000)}
    uses: dict = {}
    for e in EVENTS.values():
        for ln in e["lines"] or []:
            if ln["account"].startswith("role:"):
                uses.setdefault(ln["account"][5:], set()).add(e["key"])
    out = []
    for n, r in ROLES.items():
        a = accts.get(r["code"])
        out.append({**r, "exists": bool(a), "name": (a or {}).get("name"),
                    "active": bool(a) and a.get("is_active") is not False,
                    "type_ok": bool(a) and a.get("type") == r["type"], "used_by": sorted(uses.get(n, ()))})
    return out


async def catalog(org_id: str) -> dict:
    return {"profile_version": VERSION, "read_only": True,
            "events": [_public_event(e) for e in v0.EVENTS], "roles": await role_status(org_id),
            "coverage": coverage()}


async def _cash_account(org_id: str, kind: str, cash_account_id, warnings: list, errors: list) -> dict:
    """Rekening kas/bank untuk baris `cash` — HANYA membaca (tidak membuat rekening seperti cash_bank.default_code)."""
    acc = None
    if cash_account_id:
        acc = await db.bank_accounts.find_one({"id": cash_account_id, "org_id": org_id}, {"_id": 0})
        if not acc:
            warnings.append("Rekening/kas yang dipilih tidak ditemukan — kode lama jatuh diam-diam ke rekening "
                            "default jenisnya.")
        elif acc.get("is_active") is False:
            warnings.append(f"Rekening {acc.get('name')} sudah nonaktif — transaksi nyata di jalur ketat ditolak.")
    if not acc:
        acc = (await db.bank_accounts.find_one({"org_id": org_id, "kind": kind, "is_default": True}, {"_id": 0})
               or await db.bank_accounts.find_one({"org_id": org_id, "kind": kind, "is_active": True}, {"_id": 0},
                                                  sort=[("created_at", 1)]))
    if not acc or not acc.get("gl_account_code"):
        errors.append(f"Belum ada rekening/kas {kind} dengan sub-akun GL untuk org ini.")
        return {}
    return acc


async def dry_run(org_id: str, event_key: str, inputs: dict) -> dict:
    """Jurnal hasil menurut profil v0 + cek seimbang, akun ada/aktif/tipe, peringatan. TIDAK menulis apa pun."""
    ev = EVENTS.get(event_key)
    if not ev:
        raise ProfileError(f"Peristiwa '{event_key}' tidak ada di katalog.")
    base = {"event": event_key, "label": ev["label"], "profile_version": VERSION, "read_only": True,
            "covered": ev["covered"], "lines": [], "total_debit": 0, "total_credit": 0, "balanced": False}
    errors, warnings = [], []
    if not ev["covered"]:
        return {**base, "ok": False, "errors": [f"Belum punya profil v0 yang teruji: {ev['why_not']}"], "warnings": []}
    try:
        res = evaluate(event_key, inputs)
    except ProfileError as e:
        return {**base, "ok": False, "errors": [str(e)], "warnings": []}
    if res["ignored_inputs"]:
        warnings.append(f"Masukan diabaikan (bukan variabel peristiwa): {res['ignored_inputs']}.")
    for d in ev["defects"]:
        warnings.append(f"v0 menyalin perilaku kode hari ini yang masih bercacat {d} (lihat docs/audit); "
                        "koreksinya adalah profil terpisah di fase berikutnya.")
    accts = {a["code"]: a for a in await db.accounts.find(
        {"org_id": org_id}, {"_id": 0, "code": 1, "name": 1, "type": 1, "is_active": 1, "parent_code": 1}).to_list(2000)}
    cash_acc = None
    if any(ln["cash"] for ln in res["lines"]):
        cash_acc = await _cash_account(org_id, res["cash_kind"], (inputs or {}).get("cash_account_id"),
                                       warnings, errors)
        if cash_acc and cash_acc.get("kind") and cash_acc["kind"] != res["cash_kind"] and (inputs or {}).get("cash_account_id"):
            res["cash_kind"] = cash_acc["kind"]
    out, td, tc = [], 0, 0
    for ln in res["lines"]:
        role = ROLES.get(ln["role"]) if ln["role"] else None
        code = (cash_acc or {}).get("gl_account_code") if ln["cash"] else ln["code"]
        a = accts.get(code) if code else None
        row = {"seq": ln["seq"], "side": ln["side"], "role": ln["role"], "cash": ln["cash"],
               "account_code": code, "account_name": (a or {}).get("name"), "account_type": (a or {}).get("type"),
               "debit": ln["amount"] if ln["side"] == "D" else 0, "credit": ln["amount"] if ln["side"] == "K" else 0,
               "control": code in coa_rules.CONTROL_ACCOUNTS, "checks": []}
        if code is None:
            row["checks"].append("rekening kas/bank tidak terselesaikan")
        elif not a:
            errors.append(f"Akun {code} ({ln['role'] or 'kas/bank'}) tidak ada di Bagan Akun org ini.")
            row["checks"].append("akun tidak ada")
        else:
            if a.get("is_active") is False:
                errors.append(f"Akun {code} {a.get('name')} NONAKTIF — posting nyata akan ditolak.")
                row["checks"].append("nonaktif")
            want = role["type"] if role else "asset"
            if a.get("type") != want:
                errors.append(f"Akun {code} bertipe {a.get('type')}, peran {ln['role'] or 'kas/bank'} butuh {want}.")
                row["checks"].append("tipe tidak cocok")
            if ln["cash"] and a.get("parent_code") not in coa_rules.CASH_HEADERS:
                errors.append(f"Akun kas/bank {code} bukan sub-akun induk kas/bank.")
                row["checks"].append("bukan sub-akun kas/bank")
        td += row["debit"]
        tc += row["credit"]
        out.append(row)
    if not out:
        errors.append("Tidak ada baris bernilai — masukan menghasilkan jurnal kosong.")
    elif td != tc:
        errors.append(f"Jurnal tidak seimbang: debit Rp {td:,} != kredit Rp {tc:,} — periksa konsistensi masukan.")
    return {**base, "ok": not errors, "lines": out, "total_debit": td, "total_credit": tc,
            "balanced": bool(out) and td == tc, "cash_kind": res["cash_kind"], "variables": res["variables"],
            "errors": errors, "warnings": warnings}
