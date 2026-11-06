"""Dunia uji: proyek/unit khusus run (awalan AUDIT-), label simbolik entitas, akses baca-saja ke DB."""
import random
import uuid

from .core import Client


class World:
    def __init__(self, client: Client, db, tag: str, n_units=40, n_mat=3, log=print):
        self.c, self.db, self.tag = client, db, tag
        self.log = log
        self.n_units = n_units
        self.ent = {}          # label -> dict
        self.cnt = {}          # kind -> n
        self.last = {}         # kind -> label terakhir dibuat
        self.pid = None
        self.schemes = {}
        self.vendors = []
        self.accounts = []
        self.n_mat = n_mat
        self._phone = 0

    # ----------------------------------------------------------- label
    def new(self, kind, **data):
        n = self.cnt.get(kind, 0) + 1
        self.cnt[kind] = n
        lab = f"{kind}#{n}"
        forced = getattr(self, "_force", {}) or {}
        if kind in forced:           # replay: pertahankan label asli walau langkah pembuat lain dibuang
            lab = forced.pop(kind)
        self.ent[lab] = {"kind": kind, **data}
        self.last[kind] = lab
        return lab

    def get(self, lab):
        return self.ent.get(lab)

    def of_kind(self, kind):
        return [k for k, v in self.ent.items() if v["kind"] == kind]

    def phone(self):
        self._phone += 1
        return "0812" + f"{random.randint(10**3, 10**4 - 1)}{self._phone:04d}"[-8:].zfill(8)

    # ----------------------------------------------------------- setup
    def setup(self):
        c = self.c
        code, r = c.call("owner", "POST", "/projects", {"name": f"AUDIT-FZ {self.tag}", "location": "uji alat fuzz",
                                                        "members": ["owner@sipro.co.id", "pm@sipro.co.id", "site@sipro.co.id"]})
        assert code == 200, (code, r)
        self.pid = r["data"]["id"]
        prefix = "AF" + self.tag.replace("-", "")[-5:].upper()
        code, r = c.call("owner", "POST", f"/projects/{self.pid}/units",
                         {"prefix": prefix, "count": self.n_units, "type": "Tipe 45/90", "price": 600_000_000, "start_index": 1})
        assert code == 200, (code, r)
        code, r = c.call("owner", "GET", "/units", params={"project_id": self.pid, "limit": 500})
        us = sorted(r["data"], key=lambda u: u["code"])
        for k, u in enumerate(us, 1):
            self.ent[f"unit#{k}"] = {"kind": "unit", "id": u["id"], "code": u["code"]}
        self.cnt["unit"] = len(us)
        code, r = c.call("manager", "GET", "/payment-schemes")
        r_list_schemes = r["data"]
        self.schemes = {s["code"]: s["id"] for s in r["data"] if s.get("code")}
        # skema khusus uji: termin sudah LEWAT TEMPO agar denda keterlambatan (apply/waive) dapat dijalankan
        for s in r_list_schemes:
            if s["name"].startswith("AUDIT-FZ telat"):
                self.schemes["telat"] = s["id"]
        code, r = (200, None) if "telat" in self.schemes else c.call("owner", "POST", "/finance/config/payment-schemes", {"name": "AUDIT-FZ telat", "items": [
            {"label": "DP 30%", "basis": "percent", "value": 30, "due_offset_days": -45},
            {"label": "Termin 40%", "basis": "percent", "value": 40, "due_offset_days": -20},
            {"label": "Pelunasan 30%", "basis": "percent", "value": 30, "due_offset_days": 30}]})
        if code == 200 and r:
            self.schemes["telat"] = r["data"]["id"]
        code, r = c.call("owner", "GET", "/kpr-disbursement-schemes")
        self.kpr_scheme = (r.get("data") or [{}])[0].get("id") if code == 200 else None
        self.kpr_tranche = ((r.get("data") or [{}])[0].get("tranches") or [{}])[0].get("code", "T1") if code == 200 else "T1"
        code, r = c.call("owner", "GET", "/vendors")
        self.vendors = [v["name"] for v in r.get("data", [])] or ["AUDIT-FZ Vendor"]
        code, r = c.call("owner", "GET", "/bank/accounts")
        self.accounts = [{"id": a["id"], "name": a["name"]} for a in r.get("data", [])]
        # material proyek untuk jalur pengadaan/stok
        self.mats = []
        for k in range(self.n_mat):
            code, r = c.call("owner", "POST", "/materials", {"project_id": self.pid, "code": f"AF{k + 1}", "name": f"AUDIT-FZ Material {k + 1}",
                                                              "uom": "sak", "budget_qty": 1000})
            if code == 200:
                lab = self.new("mat", id=r["data"]["id"], project=self.pid)
                self.mats.append(lab)
        # proyek kedua (tujuan transfer stok)
        code, r = c.call("owner", "POST", "/projects", {"name": f"AUDIT-FZ {self.tag} B", "location": "uji",
                                                        "members": ["owner@sipro.co.id", "pm@sipro.co.id", "site@sipro.co.id"]})
        self.pid2 = r["data"]["id"] if code == 200 else None
        return self

    # ----------------------------------------------------------- helper panggilan
    def call(self, role, method, path, body=None, params=None):
        code, j = self.c.call(role, method, path, body, params)
        return code, j

    def proof(self, owner_type="deal", owner_id=None, role="finance"):
        return self.c.upload_proof(role, owner_type, owner_id)

    # ----------------------------------------------------------- pembacaan DB (baca-saja)
    def rows(self, coll, q=None, lim=200):
        return list(self.db[coll].find({"org_id": "org-sipro", **(q or {})}, {"_id": 0}).limit(lim))

    def one(self, coll, q):
        return self.db[coll].find_one({"org_id": "org-sipro", **q}, {"_id": 0})
