"""Seed demo Dasbor Pengiriman (idempoten, id berprefix demo_dsp_): SJ tambahan + pengiriman
berbagai moda/status + kendaraan armada. Jalankan: cd /app/backend && python ../scripts/seed_dispatch_demo.py"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
from db import db  # noqa: E402

ENT = "ent_ksc"
NOW = datetime.now(timezone.utc)
iso = lambda d: d.isoformat()  # noqa: E731
day = lambda n: (NOW + timedelta(days=n)).strftime("%Y-%m-%d")  # noqa: E731


def ship(i, so, prod, qty, unit="yard"):
    return {"id": f"demo_dsp_shp_{i}", "shipment_no": f"KSC/SJ-9{i:04d}", "order_id": so["id"], "order_number": so["number"],
            "task_id": "", "allocation_id": None, "warehouse_id": "wh_jakarta", "warehouse_name": "Gudang Jakarta Utara",
            "product_id": prod[0], "product_name": prod[1], "sku": prod[2], "qty": qty, "unit": unit, "qty_rolls": 1,
            "is_partial": False, "status": "dispatched", "created_by": "Demo Dispatch", "entity_id": ENT,
            "created_at": iso(NOW - timedelta(days=3, hours=i)), "updated_at": iso(NOW), "rolls": []}


def deliv(i, so, ships, **kw):
    base = {"id": f"demo_dsp_lgs_{i}", "number": f"KSC/LG-9{i:04d}", "entity_id": ENT, "order_id": so["id"], "order_number": so["number"],
            "customer_id": so.get("customer_id", ""), "customer_name": so["customer_name"],
            "shipment_ids": [s["id"] for s in ships], "shipment_nos": [s["shipment_no"] for s in ships],
            "fulfillment_method": so.get("fulfillment_method") or "kirim",
            "courier_name": "", "service_level": "", "tracking_no": "", "shipping_cost": 0, "vehicle_id": "", "vehicle_plate": "",
            "driver_name": "", "driver_user_id": "", "eta": "", "destination": "", "receiver_phone": "6281234567890",
            "receiver_name_hint": "", "pickup_code": "", "pickup_date": "", "pickup_attempts": 0, "notes": "",
            "photos": [], "positions": [], "pod": None, "fail_reason": "", "timeline": [],
            "created_by": "Demo Dispatch", "created_at": iso(NOW - timedelta(days=2, hours=i)), "updated_at": iso(NOW - timedelta(hours=i))}
    base.update(kw)
    return base


async def main():
    so3 = await db.sales_orders.find_one({"id": "so_003"}, {"_id": 0})
    so4 = await db.sales_orders.find_one({"id": "so_004"}, {"_id": 0})
    so10 = await db.sales_orders.find_one({"number": "KSC/SO-00010"}, {"_id": 0}) or so3
    so1 = await db.sales_orders.find_one({"id": "so_001"}, {"_id": 0})
    if not (so3 and so4 and so1):
        print("Seed realistic belum dijalankan (so_001/so_003/so_004 tidak ada)."); return
    await db.sales_orders.update_one({"id": "so_001"}, {"$set": {"fulfillment_method": "ambil", "pickup_date": day(1)}})
    so1["fulfillment_method"] = "ambil"
    P1 = ("prod_songket_palembang", "Songket Palembang Benang Emas", "SGK-PLB-001")
    P2 = ("prod_batik_solo", "Batik Solo Tulis Premium", "BTK-SLO-001")
    ships = {i: ship(i, so, prod, qty) for i, (so, prod, qty) in enumerate([
        (so3, P1, 24), (so4, P2, 40), (so4, P2, 15), (so10, P1, 30), (so1, P2, 12), (so3, P2, 18), (so4, P1, 20)], start=1)}
    addr3 = "Ibu Komang, Jl. Seminyak No. 88, Denpasar"
    addr4 = "Pak Dedi, Jl. Cihampelas No. 120, Bandung"
    delivs = [
        deliv(1, so3, [ships[1]], mode="expedition", courier_name="JNE", service_level="REG", tracking_no="JNE7788990011",
              shipping_cost=185000, eta=day(-1), destination=addr3, status="in_transit", departed_at=iso(NOW - timedelta(days=1)),
              loaded_at=iso(NOW - timedelta(days=1, hours=2)),
              positions=[{"id": "demo_pos_1", "location": "Hub JNE Cakung", "note": "", "lat": None, "lng": None, "by": "Demo", "at": iso(NOW - timedelta(hours=20))}],
              timeline=[{"id": "demo_evt_1", "action": "created", "by": "Demo Dispatch", "at": iso(NOW - timedelta(days=2)), "note": "Pengiriman disiapkan"}]),
        deliv(2, so4, [ships[2], ships[3]], mode="own_fleet", vehicle_plate="B 9021 KNA", driver_name="Joko Susilo", driver_user_id="user_driver_01",
              eta=day(0), destination=addr4, status="loaded", loaded_at=iso(NOW - timedelta(hours=3)),
              timeline=[{"id": "demo_evt_2", "action": "created", "by": "Demo Dispatch", "at": iso(NOW - timedelta(days=1)), "note": "Pengiriman disiapkan"}]),
        deliv(3, so10, [ships[4]], mode="expedition", courier_name="SiCepat", service_level="Cargo", tracking_no="SC0099887766",
              shipping_cost=240000, eta=day(-2), destination=addr3, status="delivered", delivered_at=iso(NOW - timedelta(days=1, hours=5)),
              departed_at=iso(NOW - timedelta(days=2)), loaded_at=iso(NOW - timedelta(days=2, hours=1)),
              pod={"receiver_name": "Komang Ayu", "received_at": iso(NOW - timedelta(days=1, hours=5)), "note": "", "by": "Demo", "at": iso(NOW - timedelta(days=1, hours=5))}),
        deliv(4, so1, [ships[5]], mode="self_pickup", pickup_code="KN7PQ4", pickup_date=day(1), eta=day(1), status="prepared",
              timeline=[{"id": "demo_evt_4", "action": "created", "by": "Demo Dispatch", "at": iso(NOW - timedelta(hours=6)), "note": "Menunggu diambil pelanggan (kode pickup dibuat)"}]),
        deliv(5, so3, [ships[6]], mode="own_fleet", vehicle_plate="B 7710 KNB", driver_name="Joko Susilo", driver_user_id="user_driver_01",
              eta=day(-3), destination=addr3, status="failed", fail_reason="Toko tutup, penerima tidak ada",
              departed_at=iso(NOW - timedelta(days=3)), loaded_at=iso(NOW - timedelta(days=3, hours=1)),
              timeline=[{"id": "demo_evt_5", "action": "status", "by": "Joko Susilo", "at": iso(NOW - timedelta(days=2, hours=20)), "note": "Toko tutup, penerima tidak ada", "from_status": "in_transit", "to_status": "failed"}]),
    ]
    # ships[7] dibiarkan TANPA pengiriman → muncul di aksi cepat "SJ menunggu".
    assigned = {sid: d for d in delivs for sid in d["shipment_ids"]}
    for s in ships.values():
        d = assigned.get(s["id"])
        if d:
            s.update({"logistics_id": d["id"], "logistics_number": d["number"], "logistics_status": d["status"], "logistics_mode": d["mode"]})
        await db.shipments.replace_one({"id": s["id"]}, s, upsert=True)
    for d in delivs:
        await db.logistics_deliveries.replace_one({"id": d["id"]}, d, upsert=True)
    vehicles = [
        {"id": "demo_dsp_veh_1", "plate": "B 9021 KNA", "type": "cdd", "name": "Mitsubishi Canter", "capacity_note": "4 ton / 80 roll", "default_driver_user_id": "user_driver_01", "status": "available"},
        {"id": "demo_dsp_veh_2", "plate": "B 7710 KNB", "type": "pickup", "name": "Suzuki Carry", "capacity_note": "800 kg / 20 roll", "default_driver_user_id": "", "status": "available"},
        {"id": "demo_dsp_veh_3", "plate": "B 3305 KNC", "type": "box", "name": "Isuzu Elf Box", "capacity_note": "2 ton / 50 roll", "default_driver_user_id": "", "status": "maintenance", "status_note": "Servis rutin 10.000 km"},
    ]
    for v in vehicles:
        v.update({"entity_id": ENT, "notes": "", "current_delivery_id": "", "created_by": "Demo Dispatch", "created_at": iso(NOW), "updated_at": iso(NOW)})
        v.setdefault("status_note", "")
        await db.fleet_vehicles.replace_one({"id": v["id"]}, v, upsert=True)
    print(f"OK — {len(ships)} SJ, {len(delivs)} pengiriman, {len(vehicles)} kendaraan (kode pickup demo: KN7PQ4 pada KSC/LG-90004)")


asyncio.run(main())
