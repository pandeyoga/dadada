import { useEffect, useState } from "react";
import KNDatePicker from "../../components/KNDatePicker";
import { X, KeyRound, Truck, Package } from "lucide-react";
import { useEscapeClose } from "../../utils/escapeLayers";
import KNSelect from "../../components/KNSelect";
import MoneyInput from "../../components/MoneyInput";
import { createDelivery, fleetAvailability, unassignedShipments, MODE_LABEL } from "./logisticsApi";

// FB-02 — buat pengiriman dari Surat Jalan yang belum diangkut (satu pesanan per pengiriman).
// Moda mengikuti metode pemenuhan pesanan: pesanan AMBIL → "Diambil pelanggan" (kode pickup),
// pesanan KIRIM → ekspedisi (resi + biaya) atau armada sendiri (kendaraan master + sopir).
const EMPTY = { courier_name: "", service_level: "", tracking_no: "", shipping_cost: 0, vehicle_id: "", vehicle_plate: "", driver_name: "", driver_user_id: "", eta: "", destination: "", receiver_phone: "", notes: "" };

export default function DeliveryCreateModal({ params, onClose, onCreated, preselectShipmentId = "" }) {
  const [ships, setShips] = useState([]);
  const [fleet, setFleet] = useState({ vehicles: [], drivers: [] });
  const [picked, setPicked] = useState([]);
  const [mode, setMode] = useState("expedition");
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [loadingShips, setLoadingShips] = useState(true);

  useEffect(() => {
    unassignedShipments(params).then((rows) => {
      setShips(rows);
      const pre = rows.find((r) => r.id === preselectShipmentId);
      if (pre) { setPicked([pre.id]); applyShipment(pre, rows); }
    }).catch((e) => setErr(e.response?.data?.detail || "Gagal memuat Surat Jalan.")).finally(() => setLoadingShips(false));
    fleetAvailability(params).then(setFleet).catch(() => setFleet({ vehicles: [], drivers: [] }));
  }, []); // eslint-disable-line
  useEscapeClose(true, onClose, busy);

  const pickedShip = ships.find((s) => picked.includes(s.id));
  const pickedOrder = pickedShip?.order_id;
  const isPickupOrder = pickedShip?.fulfillment_method === "ambil";

  function applyShipment(s) {
    if (s.fulfillment_method === "ambil") { setMode("self_pickup"); setF((x) => ({ ...x, destination: "", eta: s.pickup_date || "" })); }
    else { setMode((m) => (m === "self_pickup" ? "expedition" : m)); setF((x) => ({ ...x, destination: x.destination || s.shipping_address || "", eta: x.eta || s.delivery_date || "" })); }
  }
  function toggle(s) {
    if (picked.includes(s.id)) { const next = picked.filter((x) => x !== s.id); setPicked(next); if (!next.length) { setMode("expedition"); setF(EMPTY); } return; }
    if (pickedOrder && s.order_id !== pickedOrder) { setErr("Satu pengiriman hanya untuk Surat Jalan dari SATU pesanan."); return; }
    setErr(""); setPicked([...picked, s.id]); if (!picked.length) applyShipment(s);
  }
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  function pickDriver(uid) {
    const u = fleet.drivers.find((x) => x.id === uid);
    setF({ ...f, driver_user_id: uid, driver_name: u ? u.name : f.driver_name });
  }
  function pickVehicle(vid) {
    const v = fleet.vehicles.find((x) => x.id === vid);
    const drv = v?.default_driver_user_id ? fleet.drivers.find((x) => x.id === v.default_driver_user_id) : null;
    setF({ ...f, vehicle_id: vid, vehicle_plate: v ? v.plate : f.vehicle_plate, ...(drv && !f.driver_user_id ? { driver_user_id: drv.id, driver_name: drv.name } : {}) });
  }

  async function save() {
    if (!picked.length) { setErr("Pilih minimal 1 Surat Jalan."); return; }
    setBusy(true); setErr("");
    try { const d = await createDelivery({ shipment_ids: picked, mode, ...f, shipping_cost: Number(f.shipping_cost) || 0 }); onCreated(d.id); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal membuat pengiriman."); }
    finally { setBusy(false); }
  }

  const vehicleOpts = [{ value: "", label: "— pilih kendaraan (atau ketik plat manual) —" }, ...fleet.vehicles.map((v) => ({ value: v.id, label: `${v.plate} · ${v.type_label}${v.status !== "available" ? ` (${v.status_label})` : ""}`, disabled: v.status !== "available" }))];
  const modeOpts = isPickupOrder
    ? [{ value: "self_pickup", label: MODE_LABEL.self_pickup }]
    : [{ value: "expedition", label: "Ekspedisi (kurir pihak ketiga)" }, { value: "own_fleet", label: "Armada sendiri" }];

  return (
    <div className="modal-overlay" data-testid="logistics-create-modal" onClick={(e) => { if (e.target === e.currentTarget && !busy) onClose(); }}>
      <div className="modal-card !max-w-[720px]">
        <div className="flex items-center justify-between"><p className="modal-title !mb-0">Buat Pengiriman</p><button className="icon-button" onClick={onClose}><X size={16} /></button></div>
        {err && <div className="notice-bar danger !my-2 !py-1.5" data-testid="logistics-create-error"><span className="text-[11.5px]">{err}</span></div>}
        <div className="grid gap-1 mt-2">
          <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Surat Jalan yang diangkut *</label>
          {loadingShips ? <p className="text-[11.5px] text-[#9A9BA3]">Memuat Surat Jalan…</p>
            : ships.length === 0 ? <p className="text-[11.5px] text-[#9A9BA3]" data-testid="logistics-no-shipments">Tidak ada Surat Jalan yang menunggu diangkut (semua sudah punya pengiriman).</p> : (
            <div className="max-h-[200px] overflow-auto rounded-lg border border-[#E1E4EA] divide-y divide-[#F0F1F3]">
              {ships.map((s) => (
                <label key={s.id} className={`flex items-center gap-2 px-2.5 py-1.5 text-[11.5px] cursor-pointer hover:bg-[#F7F9FC] ${pickedOrder && s.order_id !== pickedOrder ? "opacity-50" : ""}`} data-testid={`logistics-ship-${s.id}`}>
                  <input type="checkbox" checked={picked.includes(s.id)} onChange={() => toggle(s)} className="h-4 w-4 accent-[#0058CC]" />
                  <span className="font-mono font-bold text-[#0058CC]">{s.shipment_no}</span>
                  <span className={`status-pill ${s.fulfillment_method === "ambil" ? "pill-purple" : "pill-info"}`}>{s.fulfillment_method === "ambil" ? "Ambil sendiri" : "Kirim"}</span>
                  <span className="font-semibold">{s.order_number}</span>
                  <span className="text-[#6B6B73] truncate">{s.customer_name} · {s.product_name} · {s.qty} {s.unit}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {isPickupOrder && (
          <div className="notice-bar info !mt-3 !py-1.5" data-testid="logistics-pickup-notice"><KeyRound size={13} />
            <span className="text-[11.5px]">Pesanan ini <b>diambil sendiri oleh pelanggan</b>{pickedShip?.pickup_date ? ` (tgl ${pickedShip.pickup_date})` : ""}. Sistem akan membuat <b>kode pickup</b>; tidak ada alamat kirim, sopir, atau kendaraan.</span></div>
        )}

        <div className="grid gap-2.5 sm:grid-cols-2 mt-3">
          <div className="grid gap-1"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">Jenis pengiriman</label>
            <KNSelect data-testid="logistics-mode" value={mode} onValueChange={setMode} className="field" disabled={isPickupOrder || !picked.length} options={modeOpts} /></div>
          <div className="grid gap-1"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">{mode === "self_pickup" ? "Tanggal ambil" : "ETA (perkiraan tiba)"}</label>
            <KNDatePicker data-testid="logistics-eta" value={f.eta} onChange={(v) => setF((x) => ({ ...x, eta: v }))} placeholder={mode === "self_pickup" ? "Tanggal pelanggan datang" : "Pilih tanggal ETA"} /></div>

          {mode === "expedition" && (<>
            <div className="grid gap-1"><label className="text-[11px] font-bold uppercase text-[#6B6B73] flex items-center gap-1"><Package size={11} /> Nama kurir / ekspedisi</label>
              <input data-testid="logistics-courier" className="form-input" placeholder="mis. JNE, SiCepat, Indah Cargo" value={f.courier_name} onChange={set("courier_name")} /></div>
            <div className="grid gap-1"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">No. Resi</label>
              <input data-testid="logistics-tracking" className="form-input" placeholder="boleh diisi nanti, wajib sebelum berangkat" value={f.tracking_no} onChange={set("tracking_no")} /></div>
            <div className="grid gap-1"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">Layanan</label>
              <input data-testid="logistics-service" className="form-input" placeholder="mis. REG, YES, Cargo" value={f.service_level} onChange={set("service_level")} /></div>
            <div className="grid gap-1"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">Biaya kirim (Rp)</label>
              <MoneyInput testId="logistics-shipping-cost" value={f.shipping_cost} onChange={(v) => setF((x) => ({ ...x, shipping_cost: v }))} /></div>
          </>)}
          {mode === "own_fleet" && (<>
            <div className="grid gap-1"><label className="text-[11px] font-bold uppercase text-[#6B6B73] flex items-center gap-1"><Truck size={11} /> Kendaraan</label>
              {fleet.vehicles.length ? <KNSelect data-testid="logistics-vehicle-select" value={f.vehicle_id} onValueChange={pickVehicle} className="field" options={vehicleOpts} /> : null}
              <input data-testid="logistics-plate" className="form-input" placeholder="Plat kendaraan (manual bila belum terdaftar)" value={f.vehicle_plate} onChange={(e) => setF({ ...f, vehicle_plate: e.target.value, vehicle_id: "" })} />
              {!fleet.vehicles.length && <p className="text-[10px] text-[#9A9BA3]">Belum ada kendaraan di master Armada — plat diketik manual.</p>}</div>
            <div className="grid gap-1"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">Sopir</label>
              {fleet.drivers.length ? (
                <KNSelect data-testid="logistics-driver-select" value={f.driver_user_id} onValueChange={pickDriver} className="field"
                  options={[{ value: "", label: "— pilih akun sopir —" }, ...fleet.drivers.map((u) => ({ value: u.id, label: `${u.name}${u.status === "on_trip" ? " (di jalan)" : ""}` }))]} />
              ) : null}
              <input data-testid="logistics-driver" className="form-input" placeholder="Nama sopir (bila tidak punya akun)" value={f.driver_name} onChange={set("driver_name")} /></div>
          </>)}
          {mode !== "self_pickup" && (
            <div className="grid gap-1 sm:col-span-2"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">Alamat tujuan</label>
              <input data-testid="logistics-destination" className="form-input" value={f.destination} onChange={set("destination")} /></div>
          )}
          <div className="grid gap-1 sm:col-span-2"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">{mode === "self_pickup" ? "Telepon pelanggan (untuk mengirim kode pickup)" : "Telepon penerima"}</label>
            <input data-testid="logistics-receiver-phone" type="tel" className="form-input" placeholder="kosong → otomatis dari kontak pelanggan" value={f.receiver_phone} onChange={set("receiver_phone")} /></div>
          <div className="grid gap-1 sm:col-span-2"><label className="text-[11px] font-bold uppercase text-[#6B6B73]">Catatan</label>
            <input data-testid="logistics-notes" className="form-input" value={f.notes} onChange={set("notes")} /></div>
        </div>
        <div className="modal-actions mt-3">
          <button className="btn-secondary" onClick={onClose} disabled={busy}>Batal</button>
          <button data-testid="logistics-create-submit" className="btn-primary" onClick={save} disabled={busy || !ships.length || !picked.length}>{busy ? "Menyimpan…" : mode === "self_pickup" ? "Siapkan pengambilan" : "Buat Pengiriman"}</button>
        </div>
      </div>
    </div>
  );
}
