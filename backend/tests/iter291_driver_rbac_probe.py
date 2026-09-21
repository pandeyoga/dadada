"""Iterasi 291 — probe RBAC sopir pada pengiriman yang BUKAN tugasnya (dengan PATCH sementara).

Skenario: admin melepas driver_user_id sebuah pengiriman aktif -> sopir mencoba
unggah foto / catat posisi / ubah tahapan -> lalu admin memulihkan driver_user_id.
"""
import os
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
ENT = "ent_ksc"
PW = "demo12345"
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d4944415478da63f8cfc0000003010100189db4ec0000000049454e44ae426082")


def sess(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PW}, timeout=30)
    d = r.json()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {d.get('token') or d.get('access_token')}",
                      "X-Entity-Id": ENT, "Content-Type": "application/json"})
    return s, d.get("user", {})


def main():
    admin, _ = sess("admin@kainnusantara.id")
    driver, du = sess("driver@kainnusantara.id")
    print("driver id:", du.get("id"), du.get("role"))
    rows = admin.get(f"{BASE}/api/logistics/deliveries", params={"entity_id": ENT}, timeout=30).json()
    for r in rows:
        print(r["number"], r["status"], "driver=", r.get("driver_user_id"), "route_order=", r.get("route_order"),
              "eta=", r.get("eta"), "mode=", r.get("mode"))
    target = next((r for r in rows if r["status"] == "prepared" and r.get("driver_user_id") == du["id"]), None)
    if not target:
        print("NO prepared delivery owned by driver -> abort")
        return
    orig = target.get("driver_user_id")
    did, num = target["id"], target["number"]
    p = admin.patch(f"{BASE}/api/logistics/deliveries/{did}", json={"driver_user_id": ""}, timeout=30)
    print(f"PATCH unassign {num} -> {p.status_code}")
    try:
        r1 = requests.post(f"{BASE}/api/logistics/deliveries/{did}/photos",
                           files={"file": ("probe.png", PNG, "image/png")},
                           data={"kind": "other", "note": "TEST_audit_probe"},
                           headers={"Authorization": driver.headers["Authorization"], "X-Entity-Id": ENT},
                           timeout=60)
        print("driver upload photo on UNASSIGNED ->", r1.status_code, r1.text[:200])
        if r1.status_code in (200, 201):
            pid = r1.json()["id"]
            d = admin.delete(f"{BASE}/api/logistics/deliveries/{did}/photos/{pid}", timeout=30)
            print("  cleanup photo ->", d.status_code)
        r2 = driver.post(f"{BASE}/api/logistics/deliveries/{did}/positions",
                         json={"location": "TEST_audit posisi"}, timeout=30)
        print("driver add position (prepared) ->", r2.status_code, r2.text[:160])
        r3 = driver.post(f"{BASE}/api/logistics/deliveries/{did}/transition",
                         json={"to": "delivered"}, timeout=30)
        print("driver transition prepared->delivered ->", r3.status_code, r3.text[:200])
        r4 = driver.get(f"{BASE}/api/logistics/deliveries/{did}", timeout=30)
        print("driver GET unassigned delivery ->", r4.status_code)
        r5 = driver.post(f"{BASE}/api/logistics/my-route", json={"ids": [did]}, timeout=30)
        print("driver my-route on unassigned ->", r5.status_code, r5.text[:160])
    finally:
        back = admin.patch(f"{BASE}/api/logistics/deliveries/{did}",
                           json={"driver_user_id": orig}, timeout=30)
        print(f"RESTORE driver_user_id={orig} -> {back.status_code}",
              back.json().get("driver_user_id") if back.status_code == 200 else back.text[:150])


main()
