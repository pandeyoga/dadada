#!/usr/bin/env python3
"""
run_corpus.py — Runner korpus uji Kain Nusantara (T-05 audit 2026-09).

Menjalankan SEMUA skrip uji/POC secara BERURUTAN (bukan paralel — POC N dan POC M
tidak boleh berjalan bersamaan, lihat SESSION_HANDOFF.md) lalu menulis ringkasan
JSON + tabel Markdown yang bisa dihasilkan ulang kapan saja.

Pakai:
  python3 scripts/run_corpus.py                       # semua skrip yang ditemukan
  python3 scripts/run_corpus.py --historical          # hanya berkas di coverage_data/corpus_summary.json
  python3 scripts/run_corpus.py --only price_approval # substring pada path
  python3 scripts/run_corpus.py --list                # cetak daftar saja, tidak menjalankan
  python3 scripts/run_corpus.py --out coverage_data/corpus_run.json --md memory/TRIASE_KORPUS.md

Prasyarat: backend hidup (supervisor) + DB sudah di-seed (bash .restore_env.sh).
JANGAN jalankan gate.sh / verify_* bersamaan dengan runner ini.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRECT_GLOBS = [
    "backend/backend_test*.py", "backend/test_*.py", "backend/*_test.py",
    "tests/*.py", "forensic/fa_*.py", "scripts/poc_*.py",
    "scripts/health_check.py", "scripts/audit_endpoint_sweep.py",
]
PYTEST_GLOB = "backend/tests/test_*.py"
# Skrip asyncio `main()` di folder tests (bukan pytest) → dijalankan langsung (T-05 sesi 4).
DIRECT_IN_TESTS = {"backend/tests/test_config_clear_layer.py"}
EXCLUDE = {"tests/__init__.py", "tests/t1_ui_fixture.py", "backend/test_utils.py"}

RE_PYTEST_SUMMARY = re.compile(r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed)")
RE_DIRECT = [
    re.compile(r"HASIL:\s*(\d+)\s*PASS\s*\|\s*(\d+)\s*FAIL", re.I),
    re.compile(r"(\d+)\s*PASS(?:ED)?\s*[|/,·]\s*(\d+)\s*FAIL", re.I),
    re.compile(r"PASS(?:ED)?\s*[:=]\s*(\d+).*?FAIL(?:ED)?\s*[:=]\s*(\d+)", re.I | re.S),
    re.compile(r"(\d+)\s*lulus\D+(\d+)\s*gagal", re.I),
    re.compile(r"(\d+)\s*/\s*(\d+)\s*(?:PASS|lulus|passed)", re.I),
]


def discover(historical: bool, only: str | None) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    if historical:
        hist = json.loads((ROOT / "coverage_data/corpus_summary.json").read_text())
        for r in hist["results"]:
            if (ROOT / r["file"]).exists():
                files.append((r["file"], r["mode"]))
    else:
        seen = set()
        for p in sorted(ROOT.glob(PYTEST_GLOB)):
            rel = str(p.relative_to(ROOT))
            seen.add(rel)
            files.append((rel, "direct" if rel in DIRECT_IN_TESTS else "pytest"))
        for g in DIRECT_GLOBS:
            for p in sorted(ROOT.glob(g)):
                rel = str(p.relative_to(ROOT))
                if rel in seen or rel in EXCLUDE or "/_legacy/" in rel:
                    continue
                seen.add(rel)
                files.append((rel, "direct"))
    if only:
        files = [f for f in files if only in f[0]]
    return files


def parse_counts(mode: str, out: str) -> tuple[int | None, int | None]:
    """Kembalikan (lulus, total) bila bisa ditebak dari keluaran; (None, None) bila tidak."""
    if mode == "pytest":
        tail = out.strip().splitlines()[-1] if out.strip() else ""
        counts = {k: int(v) for v, k in RE_PYTEST_SUMMARY.findall(tail)}
        if not counts:
            return None, None
        passed = counts.get("passed", 0)
        total = passed + counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)
        return passed, total
    for rx in RE_DIRECT:
        m = rx.search(out)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if rx.pattern.startswith(r"(\d+)\s*/"):
                return a, b
            return a, a + b
    return None, None


def first_errors(mode: str, out: str, n: int = 3) -> list[str]:
    lines = out.splitlines()
    if mode == "pytest":
        hits = [l for l in lines if l.startswith(("FAILED ", "ERROR "))]
    else:
        hits = [l for l in lines if re.search(r"❌|FAIL|Traceback|Error|GAGAL|MERAH", l)]
    return [h[:220] for h in hits[:n]]


def run_one(rel: str, mode: str, timeout: int) -> dict:
    env = {**os.environ}
    if not env.get("REACT_APP_BACKEND_URL"):
        # Banyak skrip membaca REACT_APP_BACKEND_URL dari env (bukan dari frontend/.env);
        # tanpa ini mereka gagal 'NoneType'/'must be set' — kegagalan LINGKUNGAN, bukan kode.
        for line in (ROOT / "frontend/.env").read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                env["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
    if mode == "pytest":
        cmd = [sys.executable, "-m", "pytest", rel.split("backend/", 1)[1],
               "-p", "no:randomly", "-n", "0", "-q", "--tb=line", "-rfE"]
        cwd = ROOT / "backend"
    else:
        cmd = [sys.executable, rel]
        cwd = ROOT
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        rc, out, to = p.returncode, p.stdout + p.stderr, False
    except subprocess.TimeoutExpired as e:
        rc, out, to = 124, (e.stdout or "") + (e.stderr or ""), True
    dur = round(time.time() - t0, 1)
    passed, total = parse_counts(mode, out)
    return {"file": rel, "mode": mode, "rc": rc, "timeout": to, "dur": dur,
            "passed": passed, "total": total,
            "errors": first_errors(mode, out), "tail": out[-1500:]}


def to_md(res: list[dict], meta: dict) -> str:
    ok = sum(1 for r in res if r["rc"] == 0)
    lines = [
        f"# Hasil runner korpus — {meta['when']}",
        "",
        f"- commit: `{meta['commit']}` · skrip: **{len(res)}** · rc=0: **{ok}** · rc≠0: **{len(res) - ok}** · timeout: {sum(1 for r in res if r['timeout'])}",
        f"- perintah: `{meta['cmd']}`",
        "",
        "| # | Skrip | Mode | RC | Lulus/Total | Detik | Galat pertama |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(res, 1):
        lt = f"{r['passed']}/{r['total']}" if r["total"] is not None else "?"
        err = r["errors"][0].replace("|", "\\|") if r["errors"] else ""
        lines.append(f"| {i} | `{r['file']}` | {r['mode']} | {r['rc']} | {lt} | {r['dur']} | {err} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--historical", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--out", default=f"coverage_data/corpus_run_{dt.date.today().isoformat()}.json")
    ap.add_argument("--md")
    a = ap.parse_args()

    files = discover(a.historical, a.only)
    if a.list:
        for f, m in files:
            print(f"{m:7s} {f}")
        print(f"total: {len(files)}")
        return 0

    commit = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    meta = {"when": dt.datetime.now().isoformat(timespec="seconds"), "commit": commit,
            "cmd": " ".join(sys.argv)}
    res: list[dict] = []
    for i, (f, m) in enumerate(files, 1):
        r = run_one(f, m, a.timeout)
        res.append(r)
        lt = f"{r['passed']}/{r['total']}" if r["total"] is not None else "?"
        print(f"[{i:3d}/{len(files)}] rc={r['rc']:<3} {lt:>8} {r['dur']:>6.1f}s  {f}", flush=True)
        (ROOT / a.out).write_text(json.dumps({**meta, "total": len(res),
                                              "ok": sum(1 for x in res if x["rc"] == 0),
                                              "results": res}, indent=1, ensure_ascii=False))
    ok = sum(1 for r in res if r["rc"] == 0)
    print(f"\ntotal/ok/failed/timeouts: {len(res)} {ok} {len(res) - ok} {sum(1 for r in res if r['timeout'])}")
    print(f"json: {a.out}")
    if a.md:
        (ROOT / a.md).write_text(to_md(res, meta))
        print(f"md  : {a.md}")
    return 0 if ok == len(res) else 1


if __name__ == "__main__":
    sys.exit(main())
