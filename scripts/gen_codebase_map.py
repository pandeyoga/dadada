#!/usr/bin/env python3
"""gen_codebase_map.py — hasilkan CODEBASE_MAP.md dari KODE (T-07 audit 2026-09).

Peta tulisan tangan membusuk (v1.0 28 Mei 2026: 25 router / 106 endpoint, kenyataan
123 router / 1.100+ endpoint). Berkas ini menghitung ulang dari sumber sehingga peta
tidak bisa menyimpang tanpa ketahuan — `scripts/guardrails/verify_codebase_map.py`
(INV-DOC-01) memerah bila angka di peta menyimpang >10% dari hasil hitung ulang.

Pakai:  python3 scripts/gen_codebase_map.py            # tulis CODEBASE_MAP.md
        python3 scripts/gen_codebase_map.py --stdout   # cetak saja
        python3 scripts/gen_codebase_map.py --json     # angka ringkasan (dipakai guard)
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BE = ROOT / "backend"
FE = ROOT / "frontend" / "src"
RE_ROUTE = re.compile(r"@router\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)")
RE_COLL = re.compile(r"\bdb\.([a-z][a-z0-9_]*)\.(?:find|find_one|insert|update|delete|count|aggregate|replace|bulk|create_index|distinct|find_one_and)")
CORE_FILES = ["server.py", "db.py", "core_utils.py", "schemas.py", "schemas_purchasing.py",
              "dependencies.py", "permissions_config.py", "entity_scope.py", "pagination.py",
              "indexes.py", "bootstrap.py"]
LIMITS = {".jsx": 500, ".py": 800, ".js": 300}


def nlines(p: pathlib.Path) -> int:
    return sum(1 for _ in p.open(errors="ignore"))


def routers() -> list[dict]:
    out = []
    for f in sorted((BE / "routers").glob("*.py")):
        if f.name == "__init__.py":
            continue
        src = f.read_text(errors="ignore")
        eps = RE_ROUTE.findall(src)
        out.append({"file": f.name, "lines": nlines(f), "endpoints": len(eps),
                    "paths": sorted({p for _, p in eps})})
    return out


def services() -> list[dict]:
    out = []
    for f in sorted((BE / "services").glob("*.py")):
        if f.name == "__init__.py":
            continue
        doc = ""
        try:
            tree = ast.parse(f.read_text(errors="ignore"))
            doc = (ast.get_docstring(tree) or "").strip().splitlines()[0] if ast.get_docstring(tree) else ""
        except SyntaxError:
            pass
        out.append({"file": f.name, "lines": nlines(f), "doc": doc[:110]})
    return out


def collections() -> list[str]:
    names: set[str] = set()
    for f in BE.rglob("*.py"):
        if "/tests/" in str(f) or f.name.startswith(("test_", "backend_test")) or "_poc" in f.name:
            continue
        names.update(RE_COLL.findall(f.read_text(errors="ignore")))
    return sorted(names)


def func_index(path: pathlib.Path) -> list[tuple[str, str]]:
    rows = []
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except SyntaxError:
        return rows
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_"):
            d = ast.get_docstring(n) or ""
            rows.append((n.name, d.strip().splitlines()[0][:100] if d else ""))
    return rows


def frontend() -> dict:
    feats = []
    for d in sorted((FE / "features").iterdir()):
        if d.is_dir():
            files = list(d.rglob("*.jsx")) + list(d.rglob("*.js"))
            feats.append({"dir": d.name, "files": len(files), "lines": sum(nlines(x) for x in files)})
    comps = sorted(p.name for p in (FE / "components").glob("*.jsx"))
    hooks = sorted(p.name for p in (FE / "hooks").glob("*.js*"))
    utils = sorted(p.name for p in (FE / "utils").glob("*.js*"))
    return {"features": feats, "components": comps, "hooks": hooks, "utils": utils}


def oversize() -> list[tuple[str, int, int]]:
    rows = []
    for base, pat in ((BE / "routers", "*.py"), (FE, "**/*.jsx"), (FE / "utils", "*.js")):
        for f in base.glob(pat):
            lim = LIMITS[f.suffix]
            n = nlines(f)
            if n > lim:
                rows.append((str(f.relative_to(ROOT)), n, lim))
    return sorted(rows, key=lambda r: -r[1])


def summary(rt, sv, cols, fe) -> dict:
    return {
        "routers": len(rt), "endpoints": sum(r["endpoints"] for r in rt),
        "services": len(sv), "collections": len(cols),
        "frontend_feature_dirs": len(fe["features"]),
        "core_lines": {c: nlines(BE / c) for c in CORE_FILES if (BE / c).exists()},
    }


def render() -> str:
    rt, sv, cols, fe = routers(), services(), collections(), frontend()
    s = summary(rt, sv, cols, fe)
    sha = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    L = [
        "<!-- DIHASILKAN OTOMATIS oleh scripts/gen_codebase_map.py — JANGAN EDIT TANGAN -->",
        f"<!-- Dihasilkan dari commit: {sha or '?'} pada {dt.date.today().isoformat()} -->",
        "# CODEBASE MAP — Kain Nusantara (dihasilkan otomatis)",
        "",
        "Peta ini dihitung dari kode oleh `scripts/gen_codebase_map.py`. Kalau angka di sini",
        "tidak cocok lagi dengan kenyataan, `scripts/guardrails/verify_codebase_map.py` (INV-DOC-01)",
        "memerah — jalankan ulang generatornya, jangan sunting tangan.",
        "",
        "**Batas ukuran berkas (dari FRONTEND/ENGINEERING_GUARDRAILS):** `.jsx` ≤ 500 · router `.py` ≤ 800 · util `.js` ≤ 300.",
        "",
        "## Ringkasan angka",
        "",
        "| Ukuran | Nilai |",
        "|---|---:|",
        f"| Router (`backend/routers/*.py`) | {s['routers']} |",
        f"| Endpoint (`@router.<method>`) | {s['endpoints']} |",
        f"| Service (`backend/services/*.py`) | {s['services']} |",
        f"| Koleksi MongoDB disentuh kode produksi | {s['collections']} |",
        f"| Direktori fitur frontend (`src/features/*`) | {s['frontend_feature_dirs']} |",
        "",
        "## Backend — berkas inti",
        "",
        "| Berkas | Baris |",
        "|---|---:|",
    ]
    L += [f"| `{c}` | {n} |" for c, n in s["core_lines"].items()]
    L += ["", "### Fungsi utilitas — JANGAN re-implementasi", ""]
    for f in ("core_utils.py", "dependencies.py", "entity_scope.py", "pagination.py"):
        p = BE / f
        if not p.exists():
            continue
        L += [f"**`backend/{f}`**", "", "| Fungsi | Ringkas (baris pertama docstring) |", "|---|---|"]
        L += [f"| `{n}()` | {d} |" for n, d in func_index(p)]
        L.append("")
    L += ["## Backend — router", "", "| Berkas | Endpoint | Baris | Path |", "|---|---:|---:|---|"]
    for r in rt:
        paths = ", ".join(f"`{p}`" for p in r["paths"][:6]) + (" …" if len(r["paths"]) > 6 else "")
        flag = " ⚠️>800" if r["lines"] > 800 else ""
        L.append(f"| `{r['file']}`{flag} | {r['endpoints']} | {r['lines']} | {paths} |")
    L += ["", "## Backend — service", "", "| Berkas | Baris | Ringkas |", "|---|---:|---|"]
    L += [f"| `{x['file']}` | {x['lines']} | {x['doc']} |" for x in sv]
    L += ["", "## Koleksi MongoDB (dari pola `db.<nama>.<op>` di kode produksi)", "",
          ", ".join(f"`{c}`" for c in cols), "",
          "## Frontend", "", "| Fitur (`src/features/`) | Berkas | Baris |", "|---|---:|---:|"]
    L += [f"| `{x['dir']}` | {x['files']} | {x['lines']} |" for x in fe["features"]]
    L += ["", f"**Komponen bersama (`src/components/*.jsx`, {len(fe['components'])}):** " + ", ".join(f"`{c}`" for c in fe["components"]),
          "", "**Hooks (`src/hooks/`):** " + ", ".join(f"`{c}`" for c in fe["hooks"]),
          "", "**Utils (`src/utils/`):** " + ", ".join(f"`{c}`" for c in fe["utils"]), ""]
    ov = oversize()
    L += ["## Berkas melewati batas ukuran", "", f"{len(ov)} berkas.", "", "| Berkas | Baris | Batas |", "|---|---:|---:|"]
    L += [f"| `{f}` | {n} | {lim} |" for f, n, lim in ov]
    L.append("")
    return "\n".join(L)


def main() -> int:
    if "--json" in sys.argv:
        rt, sv, cols, fe = routers(), services(), collections(), frontend()
        print(json.dumps(summary(rt, sv, cols, fe), indent=1))
        return 0
    text = render()
    if "--stdout" in sys.argv:
        print(text)
        return 0
    (ROOT / "CODEBASE_MAP.md").write_text(text)
    print(f"CODEBASE_MAP.md ditulis ({len(text.splitlines())} baris).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
