#!/usr/bin/env bash
# Uji cepat API dispatch: pickup validation, leak fix, armada, own_fleet.
cd /app
API=$(grep REACT_APP_BACKEND_URL frontend/.env | cut -d= -f2)
login() { curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"$1\",\"password\":\"demo12345\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])"; }
TOKEN=$(login admin@kainnusantara.id); WT=$(login warehouse@kainnusantara.id)
c() { curl -s "$@" -H "Authorization: Bearer $TOKEN" -H "X-Entity-Id: ent_ksc" -H "Content-Type: application/json"; }
w() { curl -s "$@" -H "Authorization: Bearer $WT" -H "X-Entity-Id: ent_ksc" -H "Content-Type: application/json"; }
SJ1=$(mongosh --quiet test_database --eval 'print(db.shipments.findOne({shipment_no:/SJ-00001/}).id)')
SJ4=$(mongosh --quiet test_database --eval 'print(db.shipments.findOne({shipment_no:/SJ-00004/}).id)')
mkdir -p /app/.tmp
echo "--- unassigned (leak: ambil harus shipping_address kosong)"; c "$API/api/logistics/shipments/unassigned?entity_id=ent_ksc" | python3 -c "import sys,json;[print(u['shipment_no'],u['fulfillment_method'],repr(u['shipping_address']),u['suggested_mode'],u['pickup_date']) for u in json.load(sys.stdin)]"
echo "--- pickup order + expedition → tolak"; c -X POST "$API/api/logistics/deliveries" -d "{\"shipment_ids\":[\"$SJ1\"],\"mode\":\"expedition\"}"; echo
echo "--- kirim order + self_pickup → tolak"; c -X POST "$API/api/logistics/deliveries" -d "{\"shipment_ids\":[\"$SJ4\"],\"mode\":\"self_pickup\"}"; echo
echo "--- create self_pickup"; c -X POST "$API/api/logistics/deliveries" -d "{\"shipment_ids\":[\"$SJ1\"],\"mode\":\"self_pickup\",\"destination\":\"HARUS KOSONG\"}" > /app/.tmp/pk.json; python3 -c "import json;d=json.load(open('/app/.tmp/pk.json'));print(d['id'],d['number'],d['mode'],d['status_label'],'code=',d['pickup_code'],'dest=',repr(d['destination']),'eta=',d['eta'])"
PK=$(python3 -c "import json;print(json.load(open('/app/.tmp/pk.json'))['id'])"); CODE=$(python3 -c "import json;print(json.load(open('/app/.tmp/pk.json'))['pickup_code'])")
echo "--- transition loaded pada pickup → tolak"; c -X POST "$API/api/logistics/deliveries/$PK/transition" -d '{"to":"loaded"}'; echo
echo "--- kode salah → tolak"; w -X POST "$API/api/logistics/deliveries/$PK/pickup-handover" -d '{"pickup_code":"XXXXXX","picker_name":"Budi"}'; echo
echo "--- warehouse lihat detail: kode tersembunyi?"; w "$API/api/logistics/deliveries/$PK" | python3 -c "import sys,json;d=json.load(sys.stdin);print('code=',repr(d.get('pickup_code')),'hidden=',d.get('pickup_code_hidden'),'attempts=',d.get('pickup_attempts'))"
echo "--- warehouse serah terima kode benar"; w -X POST "$API/api/logistics/deliveries/$PK/pickup-handover" -d "{\"pickup_code\":\"$CODE\",\"picker_name\":\"Budi Santoso\",\"picker_id_no\":\"3171XXXX\"}" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['status'],d['status_label'],d['pod'])"
echo "--- vehicle create"; c -X POST "$API/api/logistics/fleet/vehicles" -d '{"plate":"B 1234 KN","type":"box","name":"Hino Dutro","capacity_note":"2 ton","default_driver_user_id":"user_driver_01"}' > /app/.tmp/veh.json; python3 -c "import json;d=json.load(open('/app/.tmp/veh.json'));print(d.get('id'),d.get('plate'),d.get('status'),d.get('detail'))"
VEH=$(python3 -c "import json;print(json.load(open('/app/.tmp/veh.json')).get('id',''))")
echo "--- plat duplikat → tolak"; c -X POST "$API/api/logistics/fleet/vehicles" -d '{"plate":"b 1234  kn"}'; echo
echo "--- own_fleet + kendaraan"; c -X POST "$API/api/logistics/deliveries" -d "{\"shipment_ids\":[\"$SJ4\"],\"mode\":\"own_fleet\",\"vehicle_id\":\"$VEH\",\"driver_user_id\":\"user_driver_01\",\"driver_name\":\"Joko Susilo\",\"eta\":\"2026-09-19\"}" > /app/.tmp/of.json; python3 -c "import json;d=json.load(open('/app/.tmp/of.json'));print(d.get('id'),d.get('number'),d.get('vehicle_plate'),d.get('driver_name'),str(d.get('destination'))[:40],d.get('detail'))"
echo "--- maintenance saat tidak on_trip → ok"; c -X POST "$API/api/logistics/fleet/vehicles/$VEH/status" -d '{"status":"maintenance","note":"servis"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('status'))"
c -X POST "$API/api/logistics/fleet/vehicles/$VEH/status" -d '{"status":"available"}' > /dev/null
echo "--- history"; c "$API/api/logistics/history?entity_id=ent_ksc" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['total'],d['stats'])"
echo "--- dashboard"; c "$API/api/logistics/dashboard?entity_id=ent_ksc" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['kpi']);print(d['by_mode_active'],d['fleet']['vehicle_summary'],d['fleet']['driver_summary'])"
