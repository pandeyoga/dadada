#!/usr/bin/env python3
"""Penguji invarian + penjalan operasi acak SIPRO/Estora.

  python fuzz_invariants.py --api http://localhost:8052 --seed 1 --ops 300 --mode seq
  python fuzz_invariants.py --api http://localhost:8052 --seed 7 --rounds 100 --mode conc
  python fuzz_invariants.py --api URL --check-only            # hanya evaluasi invarian pada DB saat ini
  python fuzz_invariants.py --api URL --replay repros/FZ-x.json
  python fuzz_invariants.py --list                           # katalog invarian

Alat hanya MENULIS lewat API (data uji berawalan AUDIT-FZ); DB dibaca langsung (pymongo, baca-saja)."""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fz import ops as O                      # noqa: E402
from fz.core import REGISTRY                 # noqa: E402
from fz.runner import Runner                 # noqa: E402
from fz import invariants                    # noqa: E402,F401


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8052")
    ap.add_argument("--mongo", default="mongodb://127.0.0.1:27017")
    ap.add_argument("--db", default="sipro_s2")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mode", choices=["seq", "conc"], default="seq")
    ap.add_argument("--ops", type=int, default=100, help="jumlah operasi per run (seq)")
    ap.add_argument("--runs", type=int, default=1, help="jumlah run (dunia baru per run)")
    ap.add_argument("--rounds", type=int, default=20, help="putaran per run (conc)")
    ap.add_argument("--check-every", type=int, default=1)
    ap.add_argument("--settle-every", type=int, default=5)
    ap.add_argument("--no-nudge", action="store_true")
    ap.add_argument("--journey", type=float, default=0.55, help="peluang (0..1) memilih langkah logis berikutnya suatu perjalanan; 0 = acak murni")
    ap.add_argument("--shrink", action="store_true", help="kecilkan urutan operasi tiap pelanggaran baru (seq)")
    ap.add_argument("--max-shrink", type=int, default=3, help="maks pelanggaran yang di-shrink per run")
    ap.add_argument("--only", help="daftar ID invarian dipisah koma")
    ap.add_argument("--skip", help="invarian yang dilewati")
    ap.add_argument("--out", default=os.path.join(HERE, "runs"))
    ap.add_argument("--replay")
    ap.add_argument("--shrink-file", help="berkas run_*.json; kecilkan temuan pada --inv dari berkas itu")
    ap.add_argument("--inv", help="ID invarian untuk --shrink-file")
    ap.add_argument("--pick", type=int, default=0, help="urutan temuan ke-N untuk invarian itu (default 0)")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        for iid, inv in sorted(REGISTRY.items()):
            print(f"{iid:4} [{inv.area:16}] {'(settled) ' if inv.settled else ''}{inv.level:4} {inv.title}" + (f"   ~{inv.known}" if inv.known else ""))
        print(len(REGISTRY), "invarian")
        return 0

    os.makedirs(a.out, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    skip = set(a.skip.split(",")) if a.skip else None
    r = Runner(a.api, a.mongo, a.db, a.out, a.seed, nudge=not a.no_nudge, only=only, skip=skip)
    r.journey = a.journey
    print(f"# fuzz_invariants seed={a.seed} mode={a.mode} api={a.api} db={a.db}")
    t0 = time.time()

    if a.check_only:
        cur = r.baseline()
        for v in cur.values():
            print(v.inv, v.msg[:200])
        print(len(cur), "pelanggaran")
        return 0

    base = r.baseline()
    print(f"# baseline: {len(base)} pelanggaran sudah ada sebelum run (diabaikan; dicatat di baseline)")

    if a.shrink_file:
        d = json.load(open(a.shrink_file))
        fs = [f for f in d["findings"] if f["inv"] == a.inv]
        f = fs[a.pick]
        cut = f["steps"][: f["step_idx"] + 1]
        print(f"## shrink {a.inv} dari {len(cut)} langkah: {f['msg'][:150]}")
        small, nrep = r.shrink(cut, a.inv, f"sf{int(time.time()) % 100000}")
        if small is None:
            print("tidak direproduksi")
            return 2
        fn = os.path.join(a.out, f"repro_{f['tag']}_{a.inv}_{a.pick}.json")
        json.dump({"seed": a.seed, "inv": a.inv, "msg": f["msg"], "steps": small}, open(fn, "w"), ensure_ascii=False, indent=1, default=str)
        print(f"→ {len(small)} langkah ({nrep} replay) → {fn}")
        return 0

    if a.replay:
        spec = json.load(open(a.replay))
        new, w = r.replay(spec["steps"], f"rp{int(time.time()) % 10000}")
        print("replay:", len(new), "pelanggaran baru")
        for v in new:
            print(" ", v.inv, v.msg[:220])
        return 0 if not new else 1

    all_runs = []
    for run_no in range(1, a.runs + 1):
        if a.mode == "seq":
            w, steps, found = r.run_seq(a.ops, run_no, a.check_every, a.settle_every)
            all_runs.append({"run": run_no, "tag": w.tag, "n_steps": len(steps), "found": len(found)})
            if a.shrink:
                done_inv = set()
                n = 0
                for f in found:
                    if f["inv"] in done_inv or n >= a.max_shrink or f["level"] == "soft" and f["inv"] not in ("G07",):
                        continue
                    done_inv.add(f["inv"])
                    n += 1
                    cut = f["steps"][: f["step_idx"] + 1]
                    print(f"## shrink {f['inv']} dari {len(cut)} langkah…")
                    small, nrep = r.shrink(cut, f["inv"], f"{w.tag}k{n}")
                    if small is None:
                        print("   tidak bisa direproduksi pada replay (flaky/bergantung keadaan lain)")
                        f["shrunk"] = None
                    else:
                        f["shrunk"] = small
                        print(f"   → {len(small)} langkah ({nrep} replay)")
                        json.dump({"seed": a.seed, "inv": f["inv"], "msg": f["msg"], "steps": small},
                                  open(os.path.join(a.out, f"repro_{w.tag}_{f['inv']}.json"), "w"), ensure_ascii=False, indent=1, default=str)
        else:
            w, out = r.run_conc(a.rounds, run_no)
            all_runs.append({"run": run_no, "tag": w.tag, "rounds": len(out), "bursts": out})
    summary = {"seed": a.seed, "mode": a.mode, "secs": int(time.time() - t0), "stats": {k: (dict(v) if hasattr(v, "items") else v) for k, v in r.stats.items()},
               "tool_errors": r.tool_errors, "runs": all_runs, "baseline": r.baseline_list,
               "findings": r.findings, "http_500": r.client.http_500[:50],
               "inv_stats": {i: {"runs": v.runs, "viol": v.viol, "skipped": v.skipped} for i, v in REGISTRY.items()}}
    fn = os.path.join(a.out, f"run_{a.mode}_seed{a.seed}_{int(time.time())}.json")
    json.dump(summary, open(fn, "w"), ensure_ascii=False, indent=1, default=str)
    print(f"# selesai {int(time.time() - t0)} dtk; ops={sum(r.stats['ops'].values())} pelanggaran-baru={len(r.findings)} 500={len(r.client.http_500)} → {fn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
