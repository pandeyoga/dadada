#!/usr/bin/env python3
"""Jalankan ulang subset korpus (daftar berkas dari JSON) memakai run_one dari run_corpus.
Pakai: python3 scripts/run_corpus_subset.py /tmp/tt_files.json coverage_data/out.json"""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from run_corpus import ROOT, run_one  # noqa: E402

files = json.loads(pathlib.Path(sys.argv[1]).read_text())
out = ROOT / sys.argv[2]
commit = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
res = []
for i, (f, m) in enumerate(files, 1):
    r = run_one(f, m, 300)
    res.append(r)
    lt = f"{r['passed']}/{r['total']}" if r["total"] is not None else "?"
    print(f"[{i:3d}/{len(files)}] rc={r['rc']:<3} {lt:>8} {r['dur']:>6.1f}s  {f}", flush=True)
    out.write_text(json.dumps({"commit": commit, "cmd": " ".join(sys.argv), "total": len(res),
                               "ok": sum(1 for x in res if x["rc"] == 0), "results": res},
                              indent=1, ensure_ascii=False))
print("selesai:", out)
