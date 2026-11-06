"""Inti alat: klien HTTP, snapshot DB (baca-saja), tipe pelanggaran, registri invarian."""
import json
import os
import threading
import time
import uuid
from collections import defaultdict

import requests

PW = "Sipro#2026"
LOGINS = {"superadmin": ("superadmin@estora.id", "test1234")}
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002"
    "0001e221bc330000000049454e44ae426082")


# ------------------------------------------------------------------ pelanggaran & registri
class V:
    """Satu pelanggaran invarian. `key` = identitas subjek (stabil antar pengecekan);
    `val` = nilai selisih (untuk invarian agregat: berubah = pelanggaran baru)."""
    __slots__ = ("inv", "key", "msg", "val")

    def __init__(self, inv, key, msg, val=None):
        self.inv, self.key, self.msg, self.val = inv, str(key), msg, val

    def ident(self):
        return (self.inv, self.key)

    def to_dict(self):
        return {"inv": self.inv, "key": self.key, "msg": self.msg, "val": self.val}


REGISTRY = {}   # id -> Inv


class Inv:
    def __init__(self, id, area, title, fn, settled, known=None, level="hard"):
        self.id, self.area, self.title, self.fn = id, area, title, fn
        self.settled = settled     # True = butuh antrean event GL sudah kosong (dispatcher selesai)
        self.known = known         # ID temuan audit lama bila pelanggaran = varian temuan lama
        self.level = level         # hard | soft (soft = indikator, bukan bukti kerugian)
        self.runs = 0
        self.skipped = 0
        self.viol = 0


def invariant(id, area, title, settled=False, known=None, level="hard"):
    """Dekorator: daftarkan fungsi f(snap) -> list[V]. Tambah invarian baru = tambah fungsi + dekorator."""
    def deco(fn):
        REGISTRY[id] = Inv(id, area, title, fn, settled, known, level)
        return fn
    return deco


# ------------------------------------------------------------------ snapshot DB
class Snap:
    """Pembacaan DB (pymongo, baca-saja), di-cache selama satu putaran pengecekan."""

    def __init__(self, db, org="org-sipro"):
        self.db, self.org = db, org
        self._rows, self._idx, self._grp = {}, {}, {}
        self._gl = None
        self.api = None   # diisi runner: callable(role, path) untuk invarian yang butuh API

    def rows(self, coll):
        if coll not in self._rows:
            self._rows[coll] = list(self.db[coll].find({"org_id": self.org}, {"_id": 0}))
        return self._rows[coll]

    def idx(self, coll, key="id"):
        k = (coll, key)
        if k not in self._idx:
            self._idx[k] = {r.get(key): r for r in self.rows(coll) if r.get(key) is not None}
        return self._idx[k]

    def grp(self, coll, key):
        k = (coll, key)
        if k not in self._grp:
            g = defaultdict(list)
            for r in self.rows(coll):
                g[r.get(key)].append(r)
            self._grp[k] = g
        return self._grp[k]

    def gl(self):
        """{kode_akun: [debit, kredit]} dari semua baris jurnal."""
        if self._gl is None:
            g = defaultdict(lambda: [0, 0])
            for je in self.rows("journal_entries"):
                for ln in je.get("lines") or []:
                    g[ln.get("account_code")][0] += int(ln.get("debit") or 0)
                    g[ln.get("account_code")][1] += int(ln.get("credit") or 0)
            self._gl = g
        return self._gl

    def gl_cr(self, code):   # saldo sisi kredit (liabilitas/pendapatan)
        d, c = self.gl().get(code, [0, 0])
        return c - d

    def gl_dr(self, code):   # saldo sisi debit (aset/beban)
        d, c = self.gl().get(code, [0, 0])
        return d - c


def i(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


# ------------------------------------------------------------------ klien HTTP
class Client:
    def __init__(self, api):
        self.api = api.rstrip("/")
        self._tok = {}
        self._lock = threading.Lock()
        self.log = []          # log HTTP (dipakai laporan/reproduksi)
        self.s = requests.Session()
        self.http_500 = []

    def _email(self, who):
        return LOGINS.get(who, (f"{who}@sipro.co.id", PW))

    def token(self, who):
        with self._lock:
            if who not in self._tok:
                em, pw = self._email(who)
                r = requests.post(f"{self.api}/api/auth/login", json={"email": em, "password": pw}, timeout=60)
                if r.status_code != 200:
                    raise RuntimeError(f"login {em} gagal {r.status_code} {r.text[:100]}")
                self._tok[who] = r.json()["access_token"]
            return self._tok[who]

    def call(self, who, method, path, body=None, params=None, files=None, data=None, timeout=120):
        h = {"Authorization": "Bearer " + self.token(who)}
        t0 = time.time()
        try:
            r = requests.request(method, f"{self.api}/api{path}", headers=h, json=body if files is None else None,
                                 params=params, files=files, data=data, timeout=timeout)
            try:
                j = r.json()
            except ValueError:
                j = {"raw": r.text[:300]}
            code = r.status_code
        except requests.RequestException as e:   # noqa: BLE001
            code, j = 0, {"detail": f"EXC {e}"}
        ent = {"who": who, "m": method, "p": path, "b": body, "q": params, "code": code,
               "ms": int((time.time() - t0) * 1000), "resp": json.dumps(j, ensure_ascii=False)[:400]}
        self.log.append(ent)
        if code >= 500 or code == 0:
            self.http_500.append(ent)
        return code, j

    def upload_proof(self, who="finance", owner_type="deal", owner_id=None):
        h = {"Authorization": "Bearer " + self.token(who)}
        d = {"owner_type": owner_type, "optimize": "false"}
        if owner_id:
            d["owner_id"] = owner_id
        # PNG unik per panggilan (hindari penolakan "bukti dipakai ulang")
        png = PNG[:-12] + uuid.uuid4().bytes[:4] + PNG[-8:] if False else PNG
        r = requests.post(f"{self.api}/api/files/upload", headers=h, timeout=60, data=d,
                          files={"file": (f"AUDIT-{uuid.uuid4().hex[:8]}.png", _png_unique(), "image/png")})
        if r.status_code not in (200, 201):
            return None
        return r.json().get("data", {}).get("id")


def _png_unique():
    """PNG 1x1 valid dengan chunk tEXt acak → hash berkas berbeda tiap unggahan."""
    import struct
    import zlib

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    raw = b"\x00" + bytes([200, 100, 50, 255])
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"tEXt", b"Comment\x00" + uuid.uuid4().hex.encode()) +
            chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
