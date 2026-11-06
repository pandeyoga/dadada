"""Sapuan statis POLA bug backend (AST + regex) dengan ratchet.

Pemakaian (dari akar repo):
    python3 -I scripts/pattern_sweep.py                 # cetak hitungan per pola
    python3 -I scripts/pattern_sweep.py --write-baseline # simpan hitungan sekarang sebagai batas
    python3 -I scripts/pattern_sweep.py --check          # gagal (exit 1) bila ada pola yang NAIK

Ratchet: angka boleh turun (perbaikan) tetapi tidak boleh naik. Pola-pola ini asalnya dari audit
docs/audit/11_POLA_BUG_DAN_SAPUAN.md; tiap angka adalah KANDIDAT (bukan bukti bug) — buka
`--detail` untuk melihat lokasinya.
"""
import ast
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.dirname(HERE), "backend")
BASELINE = os.path.join(HERE, "pattern_sweep_baseline.json")
SKIP_PREFIX = ("backend_test", "test_", "seed", "_fixture", "models", "reference")
GUARDS = {"once", "cas", "transition", "mutex", "locked", "reserved", "find_one_and_update",
          "claim", "expect_of", "cash_lock"}
MONEY_OUT_GUARD = "assert_funds"


def pyfiles():
    for base, _d, files in os.walk(ROOT):
        if any(x in base for x in ("/tests", "__pycache__", "/.venv")):
            continue
        for f in files:
            if f.endswith(".py") and not f.startswith(SKIP_PREFIX):
                yield os.path.join(base, f)


def rel(p):
    return p.replace(ROOT + "/", "")


def dict_keys(node):
    if isinstance(node, ast.Dict):
        return {k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    return set()


def call_name(c):
    f = c.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")


def coll_of(c):
    f = c.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) \
            and isinstance(f.value.value, ast.Name) and f.value.value.id == "db":
        return f.value.attr
    return None


def sweep():
    files = sorted(pyfiles())
    src = {p: open(p, encoding="utf-8", errors="ignore").read() for p in files}
    det = collections.defaultdict(list)
    for p in files:
        try:
            tree = ast.parse(src[p])
        except SyntaxError:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call)]
            names = {call_name(c) for c in calls}
            guarded = bool(names & GUARDS)
            finds = {coll_of(c) for c in calls if call_name(c) == "find_one" and coll_of(c)}
            ins = {coll_of(c) for c in calls if call_name(c) == "insert_one" and coll_of(c)}
            upds = [(coll_of(c), c) for c in calls if call_name(c) in ("update_one", "update_many") and coll_of(c)]
            where = f"{rel(p)}::{fn.name}"
            for coll, c in upds:
                if coll in finds and not guarded and dict_keys(c.args[0] if c.args else None) <= {"id", "org_id", "_id"}:
                    det["P1_baca_lalu_tulis_tanpa_penjaga"].append(f"{where}:{coll}")
                if len(c.args) >= 2 and isinstance(c.args[1], ast.Dict) and not guarded:
                    sv = next((v for k, v in zip(c.args[1].keys, c.args[1].values)
                               if isinstance(k, ast.Constant) and k.value == "$set"), None)
                    if sv is not None and dict_keys(sv) & {"status", "stage", "state"} \
                            and not dict_keys(c.args[0]) & {"status", "stage", "state"}:
                        det["P7_set_status_tanpa_syarat_status"].append(f"{where}:{coll}")
            for coll in finds & ins:
                det["P12_find_lalu_insert"].append(f"{where}:{coll}")
            if "/routers/" in p:
                for c in calls:
                    if call_name(c) in ("find_one", "update_one", "delete_one", "update_many", "delete_many") \
                            and coll_of(c) and c.args and "id" in dict_keys(c.args[0]) \
                            and "org_id" not in dict_keys(c.args[0]):
                        det["P11_router_by_id_tanpa_org_id"].append(f"{where}:{coll_of(c)}")
            if MONEY_OUT_GUARD in names and "cash_lock" not in names and "mutex" not in names:
                det["P3_assert_funds_tanpa_kunci"].append(where)
        for h in ast.walk(tree):
            if isinstance(h, ast.ExceptHandler) and h.type is not None and "Exception" in ast.unparse(h.type):
                logs = any(isinstance(n, ast.Call) and call_name(n) in
                           ("exception", "error", "warning", "info", "debug", "record") for n in ast.walk(h))
                if not logs and not any(isinstance(n, ast.Raise) for n in ast.walk(h)):
                    det["P9_except_Exception_ditelan"].append(f"{rel(p)}:{h.lineno}")
        for i, line in enumerate(src[p].split("\n"), 1):
            if re.search(r"(now_iso\(\)|\bts)\[:10\]", line):
                det["P10_tanggal_bisnis_dari_UTC"].append(f"{rel(p)}:{i}")
            m = re.search(r"\.to_list\((\d+)\)", line)
            if m and int(m.group(1)) >= 50000:
                det["P13_pemindaian_besar_50k"].append(f"{rel(p)}:{i}")
            if m and "sort(" in line and ", 1)" in line:
                det["P13_sort_naik_lalu_to_list_N"].append(f"{rel(p)}:{i}")
        for m in re.finditer(r"""["'](\d-\d{4})["']""", src[p]):
            det["P6_kode_akun_GL_literal"].append(f"{rel(p)}:{m.group(1)}")
    return det


def counts(det):
    return {k: len(v) for k, v in sorted(det.items())}


def main(argv):
    det = sweep()
    cur = counts(det)
    if "--detail" in argv:
        print(json.dumps(det, indent=1, ensure_ascii=False))
        return 0
    if "--write-baseline" in argv:
        json.dump(cur, open(BASELINE, "w"), indent=1)
        print("Baseline disimpan:", BASELINE)
    if "--check" in argv:
        base = json.load(open(BASELINE))
        worse = {k: (base.get(k, 0), v) for k, v in cur.items() if v > base.get(k, 0)}
        for k, (b, v) in worse.items():
            print(f"NAIK  {k}: {b} -> {v}")
        better = {k: (base[k], cur.get(k, 0)) for k in base if cur.get(k, 0) < base[k]}
        for k, (b, v) in better.items():
            print(f"turun {k}: {b} -> {v}  (jalankan --write-baseline untuk mengunci)")
        return 1 if worse else 0
    for k, v in cur.items():
        print(f"{k:42s} {v:5d}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
