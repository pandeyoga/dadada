"""Smoke test: sumbu varian konfigurasi (origin) + kain dasar (base fabric) end-to-end."""
import json, os, sys, uuid, requests

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0] + "/api"
S = requests.Session()
S.headers["X-Entity-Id"] = "ent_ksc"


def login(email):
    r = S.post(f"{API}/auth/login", json={"email": email, "password": "demo12345"}); r.raise_for_status()
    S.headers["Authorization"] = "Bearer " + r.json()["token"]


def ok(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond: sys.exit(1)


login("md@kainnusantara.id")
tag = uuid.uuid4().hex[:6].upper()
meta = S.get(f"{API}/product-catalog/meta").json()
ok(meta["variant_axes"]["default"] == ["color", "grade", "origin"], f"meta axis default = {meta['variant_axes']['default']}")
ok(any(a["key"] == "origin" and len(a["options"]) == 2 for a in meta["variant_axes"]["catalog"]), "origin preset Impor/Lokal")

colors = S.get(f"{API}/color-library").json()
colors = colors if isinstance(colors, list) else colors.get("items", [])
c = colors[0]
base = S.post(f"{API}/product-templates", json={"name": f"TEST_BF_polos_{tag}", "fabric_type": "woven", "stage": "finished", "motif": "Polos", "gramasi": 120, "lebar": 1.1, "sku_prefix": f"TBP{tag}", "axes": []})
ok(base.status_code == 200, f"buat induk kain polos: {base.status_code} {base.text[:200]}")
base = base.json()

axes = [{"key": "color", "label": "Warna", "options": [{"code": c["code"], "label": c["name"], "value": c["code"], "hex": c["hex"]}]},
        {"key": "grade", "label": "Grade", "options": [{"code": "A", "label": "A", "value": "A"}]},
        {"key": "origin", "label": "Asal", "options": [{"code": "IMP", "label": "Impor", "value": "impor"}, {"code": "LOK", "label": "Lokal", "value": "lokal"}]}]
tpl = S.post(f"{API}/product-templates", json={"name": f"TEST_BF_print_{tag}", "fabric_type": "woven", "stage": "finished", "motif": "Print", "gramasi": 120, "lebar": 1.1, "sku_prefix": f"TBQ{tag}", "axes": axes, "base_fabric_template_id": base["id"]})
ok(tpl.status_code == 200, f"buat induk printing dgn kain dasar: {tpl.status_code} {tpl.text[:200]}")
tpl = tpl.json()
ok(tpl["base_fabric_name"] == base["name"], "snapshot base_fabric_name di induk")
bad = S.post(f"{API}/product-templates", json={"name": f"TEST_BF_bad_{tag}", "fabric_type": "woven", "base_fabric_template_id": "ptpl_tidakada"})
ok(bad.status_code == 400, f"kain dasar tidak ada ditolak: {bad.status_code}")
gen = S.post(f"{API}/product-templates/{tpl['id']}/generate-variants", json={"base_price": 25000})
ok(gen.status_code == 200 and gen.json()["created"] == 2, f"generate 2 varian (Impor/Lokal): {gen.status_code} {gen.text[:200]}")
v = gen.json()["variants"][0]
ok(v["origin"] in ("impor", "lokal") and v["variant_attrs"].get("origin") in ("Impor", "Lokal"), f"origin tersimpan di SKU: {v['origin']} / {v['variant_attrs']}")
ok(v["base_fabric_name"] == base["name"], "SKU mewarisi kain dasar induk")
det = S.get(f"{API}/product-templates/{tpl['id']}").json()
ok(det["variant_count"] == 2 and det["variants"][0]["base_fabric_template_id"] == base["id"], "detail induk memuat kain dasar varian")
patch = S.patch(f"{API}/product-templates/{tpl['id']}", json={"base_fabric_template_id": tpl["id"]})
ok(patch.status_code == 400, f"kain dasar = diri sendiri ditolak: {patch.status_code}")

# R&D spec dengan kain dasar → approve → product mewarisi
spec = S.post(f"{API}/rnd/specs", json={"title": f"TEST_BF_spec_{tag}", "category": "Kain", "base_unit": "meter", "sku_hint": f"TBS{tag}", "sample_type_hint": "labdip",
                                       "target": {"stage": "finished", "fabric_type": "woven", "gramasi": 120, "lebar": 110, "grade": "A"},
                                       "color_target": {"color_id": c["id"]}, "base_fabric_template_id": base["id"], "entity_id": "ent_ksc"})
ok(spec.status_code == 200, f"buat spec dgn kain dasar: {spec.status_code} {spec.text[:300]}")
spec = spec.json()
ok(spec["base_fabric_name"] == base["name"], "spec menyimpan snapshot kain dasar")
sub = S.post(f"{API}/rnd/specs/{spec['id']}/submit"); ok(sub.status_code == 200, f"submit: {sub.status_code} {sub.text[:200]}")
login("manager@kainnusantara.id")
app = S.post(f"{API}/rnd/specs/{spec['id']}/approve", json={"sku": f"TBS{tag}", "name": spec["title"], "price": 30000})
ok(app.status_code == 200, f"approve: {app.status_code} {app.text[:300]}")
prod = app.json()["product"]
ok(prod.get("base_fabric_template_id") == base["id"] and prod.get("base_fabric_name") == base["name"], f"produk hasil R&D memuat kain dasar: {prod.get('base_fabric_name')}")
login("sales@kainnusantara.id")
lst = S.get(f"{API}/products").json()
mine = [p for p in lst if p.get("template_id") == tpl["id"]]
ok(len(mine) == 2 and all(p.get("base_fabric_name") == base["name"] and p.get("origin") for p in mine), f"katalog sales memuat origin+kain dasar ({len(mine)} SKU)")
print("ALL PASS", json.dumps({"base": base["id"], "tpl": tpl["id"], "spec": spec["id"], "prod": prod["id"]}))
