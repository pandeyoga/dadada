"""Smoke audit 2026-09-07: R-3a (isolasi detail sampel), R-7 (rnd_gate blanket/RFQ), INV-PERF-01 generator."""
import sys, uuid, requests

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0] + "/api"
PW = "demo12345"


def sess(email, entity="ent_ksc"):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": PW}); r.raise_for_status()
    s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": entity})
    return s


def ok(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit(1)


admin = sess("admin@kainnusantara.id")
tag = uuid.uuid4().hex[:6].upper()

# ── R-3a — KN-A08 (audit 2026-09-21): blok lama memukul /api/sample-requests (rute mati).
# Isolasi pesanan sampel kini diuji di tests/test_kn_audit_2026_09_21.py (dipanggil gate.sh).
made = {}

# ── INV-PERF-01: generator tetap benar (idempoten + tolak SKU bentrok) ───────
colors = admin.get(f"{API}/color-library").json()
colors = colors if isinstance(colors, list) else colors.get("items", [])
axes = [{"key": "color", "label": "Warna", "options": [{"code": c["code"], "label": c["name"], "value": c["code"], "hex": c["hex"]} for c in colors[:2]]},
        {"key": "grade", "label": "Grade", "options": [{"code": "A", "label": "A", "value": "A"}, {"code": "B", "label": "B", "value": "B"}]},
        {"key": "origin", "label": "Asal", "options": [{"code": "IMP", "label": "Impor", "value": "impor"}, {"code": "LOK", "label": "Lokal", "value": "lokal"}]}]
tpl = admin.post(f"{API}/product-templates", json={"name": f"TEST_AUD_{tag}", "fabric_type": "woven", "stage": "finished", "motif": "Polos",
                                                   "gramasi": 120, "lebar": 1.1, "sku_prefix": f"TAU{tag}", "axes": axes})
ok(tpl.status_code == 200, f"buat induk 2×2×2: {tpl.status_code} {tpl.text[:150]}")
tpl = tpl.json()
g1 = admin.post(f"{API}/product-templates/{tpl['id']}/generate-variants", json={"base_price": 50000})
ok(g1.status_code == 200 and g1.json()["created"] == 8, f"generate 8 kombinasi unik: {g1.status_code} {g1.text[:120]}")
g2 = admin.post(f"{API}/product-templates/{tpl['id']}/generate-variants", json={"base_price": 50000})
ok(g2.status_code == 200 and g2.json()["created"] == 0 and g2.json()["skipped"] == 8, f"ulang → idempoten (0 dibuat, 8 dilewati): {g2.text[:120]}")
skus = {v["sku"] for v in admin.get(f"{API}/product-templates/{tpl['id']}").json()["variants"]}
ok(len(skus) == 8, f"8 SKU unik di induk: {len(skus)}")

# ── R-7: SKU R&D (belum dirilis) tidak boleh masuk Blanket PO / RFQ award ────
variants = admin.get(f"{API}/product-templates/{tpl['id']}").json()["variants"]
v = variants[0]
ok(bool(v.get("lifecycle")), f"varian generator lahir dengan lifecycle eksplisit (default konfigurasi): {v.get('lifecycle')}")
# Paksa satu varian ke 'konsep' langsung di DB (simulasi SKU R&D yang belum dirilis).
from pymongo import MongoClient
MongoClient("mongodb://localhost:27017")["test_database"].products.update_one({"id": v["id"]}, {"$set": {"lifecycle": "konsep"}})
wh = admin.get(f"{API}/warehouses").json()
wh = wh if isinstance(wh, list) else wh.get("items", [])
sup = admin.get(f"{API}/suppliers").json()
sup = sup if isinstance(sup, list) else sup.get("items", [])
sup = [s for s in sup if not s.get("interco_entity_id") and not s.get("is_internal") and "kanda" not in s.get("name", "").lower()]
blk = admin.post(f"{API}/purchase-orders/blanket", json={"supplier_id": sup[0]["id"], "warehouse_id": wh[0]["id"],
                                                        "valid_from": "2026-01-01", "valid_until": "2026-12-31",
                                                        "items": [{"product_id": v["id"], "contract_qty": 100, "contract_price": 10000, "unit": v.get("base_unit", "meter")}]})
print("   blanket resp:", blk.status_code, blk.text[:160])
ok(blk.status_code == 400 and "belum boleh masuk blanket po" in blk.text.lower(), "Blanket PO menolak SKU R&D belum dirilis (rnd_gate)")
# Kontrol: PO standar juga menolak (gerbang yang sama → seragam).
po = admin.post(f"{API}/purchase-orders", json={"supplier_id": sup[0]["id"], "warehouse_id": wh[0]["id"],
                                               "items": [{"product_id": v["id"], "quantity": 10, "unit": v.get("base_unit", "meter"), "price": 10000}]})
ok(po.status_code == 400 and "belum boleh masuk" in po.text.lower(), f"PO standar menolak dengan gerbang sama: {po.status_code}")

# bersihkan
for pv in variants:
    admin.delete(f"{API}/products/{pv['id']}")
admin.delete(f"{API}/product-templates/{tpl['id']}")
for ent, m in made.items():
    pass  # KN-A08 — pembersihan sample-requests dihapus bersama bloknya
print("ALL PASS")
