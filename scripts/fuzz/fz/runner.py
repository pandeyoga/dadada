"""Penjalan: mode sekuensial & konkuren, pengecekan invarian, pengecilan (shrink), putar ulang."""
import json
import os
import random
import threading
import time
from collections import Counter, defaultdict

from pymongo import MongoClient

from . import ops as O
from .core import REGISTRY, Client, V
from .runtime_check import evaluate
from .world import World

ORG = "org-sipro"


class Runner:
    def __init__(self, api, mongo, dbname, outdir, seed, log=print, nudge=True, only=None, skip=None):
        self.api, self.dbname, self.outdir, self.seed = api, dbname, outdir, seed
        self.client = Client(api)
        self.db = MongoClient(mongo)[dbname]
        self.log = log
        self.nudge = nudge
        self.only, self.skip_inv = only, skip
        self.prev = {}
        self.baseline_ids = set()
        self.stats = {"ops": Counter(), "ok": Counter(), "rej": Counter(), "skip": Counter(), "err500": Counter(), "checks": 0, "settled_unreached": 0}
        self.tool_errors = {}
        self.findings = []          # {inv, msg, steps_idx, ...}
        self.seen_msgs = set()
        self.journey = 0.55          # peluang langkah dipilih mengikuti 'perjalanan' (rantai logis) alih-alih acak murni

    # ------------------------------------------------------------------ dispatcher
    def pending_events(self):
        return self.db.events.count_documents({"org_id": ORG, "status": {"$in": ["pending", "processing"]}, "next_retry_at": None})

    def drain(self, w=None, max_wait=14.0, nudge=None):
        nudge = self.nudge if nudge is None else nudge
        t0, tries = time.time(), 0
        while True:
            if self.pending_events() == 0:
                return True
            if nudge and tries < 2:
                tries += 1
                self.client.call("sales", "POST", "/leads", {"name": f"AUDIT-FZ nudge {int(time.time())}", "phone": "0812" + str(int(time.time() * 1000))[-8:], "source": "manual"})
            if time.time() - t0 > max_wait:
                return False
            time.sleep(0.25)

    def api_get(self, role, path):
        return self.client.call(role, "GET", path)

    # ------------------------------------------------------------------ pengecekan
    def check(self, settled=True, tag=""):
        """Hitung semua pelanggaran, kembalikan yang BARU/BERUBAH dibanding pengecekan sebelumnya."""
        vs, errs = evaluate(self.db, ORG, api=self.api_get, settled=settled, only=self.only, skip=self.skip_inv)
        self.stats["checks"] += 1
        for iid, e, tb in errs:
            self.tool_errors[iid] = e
        cur = {v.ident(): v for v in vs}
        for k, v in cur.items():     # invarian agregat: tampilkan perubahan (Δ) sejak pengecekan sebelumnya
            if v.val is not None and k in self.prev and self.prev[k].val is not None and self.prev[k].val != v.val and isinstance(v.val, (int, float)):
                v.msg += f"  [Δ sejak cek sebelumnya = {v.val - self.prev[k].val:,}]"
        evald = {iid for iid, inv in REGISTRY.items() if (settled or not inv.settled) and (not self.only or iid in self.only)}
        new = [v for k, v in cur.items() if k not in self.prev or (v.val is not None and self.prev[k].val != v.val)]
        # perbarui prev hanya untuk invarian yang dievaluasi
        keep = {k: v for k, v in self.prev.items() if k[0] not in evald}
        keep.update(cur)
        self.prev = keep
        return new, cur

    def baseline(self):
        self.drain(nudge=False, max_wait=20)
        new, cur = self.check(True, "baseline")
        self.baseline_ids = set(cur)
        self.baseline_list = [v.to_dict() for v in cur.values()]
        return cur

    # ------------------------------------------------------------------ eksekusi langkah
    def exec_step(self, w, step):
        """Jalankan satu langkah {op,args} atau {par:[…]}; isi step['res']."""
        if "par" in step:
            bar = threading.Barrier(len(step["par"]))
            outs = [None] * len(step["par"])

            def one(k, s):
                bar.wait()
                try:
                    outs[k] = self._run_one(w, s)
                except Exception as e:   # noqa: BLE001
                    outs[k] = {"ok": False, "code": -2, "note": f"EXC {type(e).__name__}: {e}"}
            ts = [threading.Thread(target=one, args=(k, s)) for k, s in enumerate(step["par"])]
            [t.start() for t in ts]
            [t.join() for t in ts]
            for s, o in zip(step["par"], outs):
                s["res"] = o
            return outs
        step["res"] = self._run_one(w, step)
        return step["res"]

    def _run_one(self, w, step):
        o = O.OPS[step["op"]]
        before = set(w.ent)
        if step.get("mk"):
            w._force = dict(step["mk"])
        n500 = len(self.client.http_500)
        try:
            r = o["run"](w, step["args"])
        except Exception as e:   # noqa: BLE001 — galat alat, bukan temuan
            r = {"ok": False, "code": -2, "note": f"TOOLERR {type(e).__name__}: {e}"}
        w._force = {}
        if not step.get("mk"):
            mk = {w.ent[k]["kind"]: k for k in set(w.ent) - before}
            if mk:
                step["mk"] = mk
        name = step["op"]
        self.stats["ops"][name] += 1
        if r["code"] == -1:
            self.stats["skip"][name] += 1
            self.stats.setdefault("why", Counter())[f"{name}: {str(r.get('note'))[:90]}"] += 1
        elif r["ok"]:
            self.stats["ok"][name] += 1
        else:
            self.stats["rej"][name] += 1
            self.stats.setdefault("why", Counter())[f"{name}: {str(r.get('note'))[:90]}"] += 1
        if len(self.client.http_500) > n500:
            self.stats["err500"][name] += 1
            r["http500"] = True
        return r

    def gen_step(self, w, rng, names=None, focus=None):
        if names is None and focus is None and rng.random() < self.journey:
            st = O.advance(w, rng)
            if st:
                return st
        pool = [(n, O.OPS[n]["w"]) for n in (names or O.OPS)]
        for _ in range(12):
            n = rng.choices([p[0] for p in pool], [p[1] for p in pool])[0]
            args = O.OPS[n]["gen"](w, rng, focus)
            if args is not None:
                return {"op": n, "args": args}
        return None

    # ------------------------------------------------------------------ mode sekuensial
    def run_seq(self, n_ops, run_no, check_every=1, settle_every=5, tag=None):
        rng = random.Random(self.seed * 1000 + run_no)
        tag = tag or f"s{self.seed}r{run_no}"
        w = World(self.client, self.db, tag).setup()
        steps, found = [], []
        self.log(f"[seq] run {run_no} tag={tag} proyek={w.pid[:8]} ops={n_ops}")
        last_settled_idx = -1
        for k in range(n_ops):
            st = self.gen_step(w, rng)
            if not st:
                continue
            steps.append(st)
            self.exec_step(w, st)
            idx = len(steps) - 1
            if (idx + 1) % check_every == 0:
                new, _ = self.check(settled=False)
                self._record(w, found, new, steps, idx, "seq", settled=False)
            if (idx + 1) % settle_every == 0:
                ok = self.drain(w)
                if not ok:
                    self.stats["settled_unreached"] += 1
                new, _ = self.check(settled=ok)
                self._record(w, found, new, steps, idx, "seq", settled=ok)
                last_settled_idx = idx
        ok = self.drain(w)
        new, _ = self.check(settled=ok)
        self._record(w, found, new, steps, len(steps) - 1, "seq", settled=ok)
        return w, steps, found

    # ------------------------------------------------------------------ mode konkuren
    def run_conc(self, rounds, run_no, bursts=None):
        from .conc import BURSTS, prep_steps
        rng = random.Random(self.seed * 1000 + 500 + run_no)
        tag = f"s{self.seed}c{run_no}"
        w = World(self.client, self.db, tag, n_units=max(30, rounds * 2 + 10)).setup()
        out = []
        self.log(f"[conc] run {run_no} tag={tag} putaran={rounds}")
        for r in range(rounds):
            spec = rng.choice(bursts or BURSTS)
            steps = []
            for st in prep_steps(self, w, rng, spec["need"]):
                steps.append(st)
            par = []
            for member in spec["par"]:
                nm, fx = member if isinstance(member, tuple) else (member, None)
                focus = fx(w) if fx else {}
                focus = {**{k: v for k, v in w.last.items()}, **focus}
                args = O.OPS[nm]["gen"](w, rng, focus)
                if args is None:
                    continue
                par.append({"op": nm, "args": args})
            if len(par) < 2:
                continue
            bstep = {"par": par}
            steps.append(bstep)
            self.exec_step(w, bstep)
            ok = self.drain(w, nudge=False)
            new, _ = self.check(settled=ok)
            found = []
            self._record(w, found, new, steps, len(steps) - 1, "conc", settled=ok, burst=spec["name"])
            out.append({"burst": spec["name"], "res": [(p["op"], p["res"]["code"]) for p in par], "new": len(new)})
        return w, out

    def run_prep_exec(self, w, rng, need):
        from .conc import prep_steps
        return prep_steps(self, w, rng, need)

    # ------------------------------------------------------------------ pencatatan
    def _record(self, w, found, new, steps, idx, mode, settled, burst=None):
        for v in new:
            key = (v.inv, _norm(v.msg))
            if key in self.seen_msgs:
                self.stats.setdefault("dups", Counter())[v.inv] += 1
                continue
            self.seen_msgs.add(key)
            lo = max(0, idx - 9) if mode == "seq" else 0
            f = {"inv": v.inv, "msg": v.msg, "val": v.val, "mode": mode, "step_idx": idx, "settled": settled, "tag": w.tag,
                 "burst": burst, "window": [_brief(s) for s in steps[lo:idx + 1]], "n_steps": len(steps),
                 "steps": json.loads(json.dumps(steps, default=str)), "known": REGISTRY[v.inv].known, "level": REGISTRY[v.inv].level}
            found.append(f)
            self.findings.append(f)
            self.log(f"  !! {v.inv} @op{idx} [{mode}] {v.msg[:170]}")

    # ------------------------------------------------------------------ replay & shrink
    def replay(self, steps, tag, want_inv=None, drain_wait=14.0, quiet=True):
        """Putar ulang langkah di dunia baru; kembalikan pelanggaran baru. Invarian non-settled dicek tanpa menunggu dispatcher."""
        need_settle = any(REGISTRY[i].settled for i in (want_inv or REGISTRY))
        if need_settle:
            self.drain(nudge=False, max_wait=drain_wait)
        _, cur0 = self.check(settled=need_settle)       # prev ← keadaan sebelum replay
        w = World(self.client, self.db, tag, n_units=max(30, self.n_units_needed(steps))).setup()
        for st in steps:
            st = json.loads(json.dumps(st))
            self.exec_step(w, st)
        ok = self.drain(w) if need_settle else False
        new, cur = self.check(settled=ok)
        if want_inv:
            new = [v for v in new if v.inv in want_inv]
        return new, w

    @staticmethod
    def n_units_needed(steps):
        mx = 0
        for s in steps:
            for x in (s["par"] if "par" in s else [s]):
                for v in (x.get("args") or {}).values():
                    if isinstance(v, str) and v.startswith("unit#"):
                        mx = max(mx, int(v.split("#")[1]))
        return mx

    def shrink(self, steps, inv_id, tag_prefix, max_replays=160, repro_msgs=None):
        """ddmin: (1) buang semua langkah yang ditolak API (tak berefek), (2) buang blok langkah sambil pelanggaran sama tetap muncul."""
        steps = [s for s in steps]
        n_rep = 0

        def bad(cand):
            nonlocal n_rep
            n_rep += 1
            new, _ = self.replay(cand, f"{tag_prefix}x{n_rep}", want_inv={inv_id})
            return len(new) > 0
        if not bad(steps):
            return None, n_rep

        def effective(s):
            if "par" in s:
                return True
            r = s.get("res") or {}
            return bool(r.get("ok")) or r.get("code") == 500
        eff = [s for s in steps if effective(s)]
        if len(eff) < len(steps) and bad(eff):
            steps = eff
        chunk = max(1, len(steps) // 2)
        while chunk >= 1 and n_rep < max_replays:
            i = 0
            changed = False
            while i < len(steps) and n_rep < max_replays:
                cand = steps[:i] + steps[i + chunk:]
                if cand and bad(cand):
                    steps = cand
                    changed = True
                else:
                    i += chunk
            if not changed or chunk > len(steps):
                chunk //= 2
            chunk = min(chunk, max(1, len(steps) // 2)) if steps else 1
        return steps, n_rep


def _norm(msg):
    """Normalisasi pesan untuk dedup lintas entitas (angka & id dibuang)."""
    import re
    m = re.sub(r"[0-9a-f]{6,8}", "#", msg)
    m = re.sub(r"[-+]?\d[\d,.]*", "N", m)
    m = re.sub(r"AUDIT-FZ[^ ]*( [A-Za-z0-9-]+)*", "AUDIT", m)
    return m[:140]


def _brief(s):
    if "par" in s:
        return {"par": [_brief(x) for x in s["par"]]}
    r = s.get("res") or {}
    return {"op": s["op"], "args": s["args"], "res": f"{r.get('code')} {str(r.get('note'))[:80]}"}
