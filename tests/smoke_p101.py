"""Smoke test cepat: batalkan reservasi + modul pengajuan (lokal)."""
import json
import sys

import requests

B = "http://localhost:8001/api"
PW = "Sipro#2026"


def login(email):
    s = requests.Session()
    r = s.post(f"{B}/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


def main():
    sa = login("superadmin@sipro.co.id")
    fin = login("finance@sipro.co.id")
    sales = login("sales@sipro.co.id")

    # ---- reservation cancel
    units = sa.get(f"{B}/units", params={"status": "available", "limit": 2}).json()["data"]
    leads = sa.get(f"{B}/leads", params={"limit": 5}).json()["data"]
    lead = next((l for l in leads if l.get("stage") in ("acquisition", "nurturing", "appointment")), leads[0])
    print("unit", units[0]["code"], "lead", lead["name"], lead.get("stage"))
    r = sa.post(f"{B}/deals/reserve", json={"unit_id": units[0]["id"], "lead_id": lead["id"],
                                             "booking_fee": 5000000, "notes": "smoke"})
    print("reserve", r.status_code, r.text[:200])
    deal = r.json()["data"]
    pv = sa.get(f"{B}/deals/{deal['id']}/cancel-preview").json()["data"]
    print("preview unpaid:", json.dumps({k: pv[k] for k in ("can_cancel", "requires_admin", "blocked_reason")}))
    # pay booking fee
    r = fin.post(f"{B}/booking-fee/deals/{deal['id']}/pay", json={"amount": 5000000, "method": "transfer", "note": "smoke"})
    print("pay bf", r.status_code, r.text[:150])
    pv_sales = sales.get(f"{B}/deals/{deal['id']}/cancel-preview")
    print("preview sales (paid):", pv_sales.status_code, pv_sales.text[:250])
    pv = sa.get(f"{B}/deals/{deal['id']}/cancel-preview").json()["data"]
    print("preview admin (paid):", pv["can_cancel"], pv["requires_admin"], pv["refund_modes"], pv["booking_fee"])
    r = sa.post(f"{B}/deals/{deal['id']}/cancel", json={"reason": "smoke test batal", "refund_mode": "partial", "refund_amount": 2000000})
    print("cancel", r.status_code, r.text[:300])
    u = sa.get(f"{B}/units/{units[0]['id']}").json().get("data", {})
    print("unit after:", u.get("status"), u.get("reserved_by_deal"))
    bf = sa.get(f"{B}/booking-fee/deals/{deal['id']}").json()["data"]["invoice"]
    print("bf after:", bf["status"], bf["refunded_total"], bf["forfeited_total"])
    ld = sa.get(f"{B}/leads/{lead['id']}").json()["data"]
    print("lead stage after:", ld.get("stage"))

    # ---- second: unpaid cancel by sales (own lead)
    my_leads = sales.get(f"{B}/leads", params={"limit": 20}).json()["data"]
    ml = next((l for l in my_leads if l.get("stage") in ("acquisition", "nurturing", "appointment")), None)
    if ml:
        r = sales.post(f"{B}/deals/reserve", json={"unit_id": units[1]["id"], "lead_id": ml["id"], "booking_fee": 1000000})
        print("sales reserve", r.status_code, r.text[:120])
        if r.status_code == 200:
            d2 = r.json()["data"]
            r = sales.post(f"{B}/deals/{d2['id']}/cancel", json={"reason": "pembeli mundur"})
            print("sales cancel unpaid", r.status_code, r.text[:200])

    # ---- fund requests
    r = sales.post(f"{B}/fund-requests", json={"type": "expense", "title": "Listrik kantor pemasaran", "amount": 1500000, "category": "atk_kantor"})
    print("create fr", r.status_code, r.text[:150])
    fr = r.json()["data"]
    r = sales.post(f"{B}/fund-requests", json={"type": "reimbursement", "title": "Bensin", "amount": 100000})
    print("reimb no attachment ->", r.status_code, r.json().get("detail"))
    r = sales.post(f"{B}/fund-requests", json={"type": "advance", "title": "Kas bon survey", "amount": 500000, "category": "transport"})
    adv = r.json()["data"]
    print("list sales:", len(sales.get(f"{B}/fund-requests").json()["data"]), "can_approve", sales.get(f"{B}/fund-requests").json()["can_approve"])
    print("summary fin:", fin.get(f"{B}/fund-requests/summary").json()["data"])
    print("approve", fin.post(f"{B}/fund-requests/{fr['id']}/approve", json={"approved_amount": 1400000}).status_code)
    r = fin.post(f"{B}/fund-requests/{fr['id']}/disburse", json={"amount": 1400000, "source": "bank"})
    print("disburse", r.status_code, r.json()["data"]["status"], r.json()["data"]["journal_ids"])
    fin.post(f"{B}/fund-requests/{adv['id']}/approve", json={})
    r = fin.post(f"{B}/fund-requests/{adv['id']}/disburse", json={"source": "kas"})
    print("adv disburse", r.status_code, r.json()["data"]["status"])
    r = sales.post(f"{B}/fund-requests/{adv['id']}/settle", json={"items": [{"category": "transport", "description": "Grab", "amount": 350000}]})
    d = r.json()["data"]
    print("settle", r.status_code, d["status"], d["returned_amount"], d["reimburse_amount"])
    print("sales approve own ->", sales.post(f"{B}/fund-requests/{adv['id']}/approve", json={}).status_code)


if __name__ == "__main__":
    main()
