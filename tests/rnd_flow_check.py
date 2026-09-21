import json, os, sys, requests

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL")][0]
TOKEN = open("/app/.tok").read().strip()
H = {"Authorization": f"Bearer {TOKEN}", "X-Entity-Id": "ent_ksc", "Content-Type": "application/json"}
UP = {"Authorization": f"Bearer {TOKEN}", "X-Entity-Id": "ent_ksc"}

def call(m, path, **kw):
    r = requests.request(m, f"{API}/api{path}", headers=UP if "files" in kw else H, **kw)
    try: data = r.json()
    except Exception: data = r.text
    if r.status_code >= 400:
        print("ERR", m, path, r.status_code, str(data)[:300]); sys.exit(1)
    return data

tpls = call("GET", "/product-templates")
tpls = tpls if isinstance(tpls, list) else tpls.get("items", [])
tpl = next((t for t in tpls if t.get("status") == "active" and t.get("axes")), None)
print("template:", tpl and (tpl["id"], tpl["name"], [(a["key"], [o["code"] for o in a["options"]][:3]) for a in tpl["axes"]]))
spec = {"title": "Katun Twill 240 gsm — navy supplier test", "base_unit": "meter", "sku_hint": "TST-TWL-NVY-01",
        "sample_type_hint": "labdip", "target": {"fabric_type": "woven", "gramasi": 240, "lebar": 150},
        "color_target": {"color_id": "col_kn_blu_01"}}
s = call("POST", "/rnd/samples", data=json.dumps({"sample_types": ["labdip"], "title": "Labdip test konsolidasi spec",
        "brief": "uji", "color_target": {"color_id": "col_kn_blu_01"}, "qty_requested": 3, "unit": "meter", "spec": spec}))
print("sample:", s["number"], "spec_id:", s.get("spec_id"), s.get("spec_number"))
s = call("POST", f"/rnd/samples/{s['id']}/send", data=json.dumps({"supplier_ids": ["sup_a05908473e52"], "type_codes": ["labdip"], "note": "uji"}))
rnd = s["rounds"][0]
png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8ffff3f0300050001019cd7b3f30000000049454e44ae426082")
call("POST", f"/rnd/samples/{s['id']}/rounds/{rnd['id']}/attachments", files={"file": ("bukti.png", png, "image/png")})
meta = call("GET", "/rnd/meta?entity_id=ent_ksc")
fields = next((t.get("measurement_fields", []) for t in meta.get("sample_types", []) if t["value"] == "labdip"), [])
meas = {f: 1 for f in fields}
s = call("POST", f"/rnd/samples/{s['id']}/rounds/{rnd['id']}/submit", data=json.dumps({"note": "warna oke", "measurements": meas, "cost": 100000}))
s = call("POST", f"/rnd/samples/{s['id']}/rounds/{rnd['id']}/assess", data=json.dumps({"result": "acc", "score": 90, "note": "ACC uji"}))
print("after assess:", s["status"], s["rounds"][0]["result"], s["rounds"][0].get("received_at", "")[:16], s["rounds"][0].get("assess_note"))
reason = meta["reasons"][0]["value"]
s = call("POST", f"/rnd/samples/{s['id']}/decide", data=json.dumps({"supplier_id": "sup_a05908473e52", "reason_code": reason, "price": 42500,
        "supplier_sku": "PSH-NVY-01", "supplier_color_name": "Navy 07", "supplier_color_code": "NV-07", "approve_spec": True, "product_sku": "TST-TWL-NVY-01", "product_name": "Katun Twill Navy Test"}))
d = s["decision"]
print("decision:", d["supplier_name"], d.get("supplier_color_name"), d.get("color_synced"), "product:", d.get("product_sku"), "err:", d.get("master_error"), "contract:", d.get("contract_number"))
full = call("GET", f"/rnd/samples/{s['id']}")
md = full["master_data"]
print("master_data:", {k: (v if k in ("decided",) else (v and {kk: v[kk] for kk in list(v)[:4]})) for k, v in md.items()})
col = call("GET", "/color-library/col_kn_blu_01")
print("color variants:", col.get("supplier_variants"), "factory:", col.get("factory_name"))
