import { useEffect, useState } from "react";
import { Bus, Plus, Wrench, CheckCircle2, UserRound, Save, X } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import ErrorNotice from "../../components/ErrorNotice";
import { askReason } from "../../services/confirmService";
import { fleetAvailability, createVehicle, updateVehicle, setVehicleStatus, VEHICLE_STATUS_PILL } from "./logisticsApi";

// Armada internal: master kendaraan (status tersedia / di jalan / perawatan) + status sopir.
const EMPTY = { plate: "", type: "pickup", name: "", capacity_note: "", default_driver_user_id: "", notes: "" };

export default function FleetPanel({ params, canManage, onOpen, refreshKey }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState(null);   // null | {…} (baru) | {id,…} (ubah)
  const [busy, setBusy] = useState(false);

  async function load() {
    try { setD(await fleetAvailability(params)); setErr(""); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal memuat armada."); }
  }
  useEffect(() => { load(); }, [params, refreshKey]); // eslint-disable-line

  async function save() {
    setBusy(true); setErr(""); setMsg("");
    try {
      if (form.id) { const { id, ...rest } = form; await updateVehicle(id, rest); setMsg("Kendaraan diperbarui."); }
      else { await createVehicle(form); setMsg("Kendaraan ditambahkan."); }
      setForm(null); await load();
    } catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan kendaraan."); }
    finally { setBusy(false); }
  }
  async function toggleStatus(v) {
    const toMaint = v.status === "available";
    const note = toMaint ? await askReason({ title: `Tandai ${v.plate} PERAWATAN?`, description: "Kendaraan tidak bisa dipilih untuk pengiriman sampai ditandai tersedia lagi.", confirmLabel: "Perawatan", reasonPlaceholder: "Contoh: servis rutin / ganti ban" }) : "kembali tersedia";
    if (!note) return;
    setBusy(true); setErr(""); setMsg("");
    try { await setVehicleStatus(v.id, { status: toMaint ? "maintenance" : "available", note }); setMsg(`${v.plate} → ${toMaint ? "Perawatan" : "Tersedia"}.`); await load(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal mengubah status."); }
    finally { setBusy(false); }
  }

  if (err && !d) return <ErrorNotice message={err} onRetry={load} testId="fleet-error" />;
  if (!d) return <div className="section-card !p-10 text-center"><p className="text-[12px] text-[#6B6B73]" data-testid="fleet-loading">Memuat armada…</p></div>;
  const types = Object.entries(d.vehicle_types || {}).map(([value, label]) => ({ value, label }));
  const driverOpts = [{ value: "", label: "— tanpa sopir tetap —" }, ...(d.drivers || []).map((u) => ({ value: u.id, label: u.name }))];
  const driverName = (id) => (d.drivers || []).find((u) => u.id === id)?.name || "";

  return (
    <div className="grid gap-3" data-testid="fleet-panel">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2" data-testid="fleet-summary">
        <Stat id="veh-available" label="Kendaraan tersedia" v={d.vehicle_summary?.available} tone="#1A7A3A" />
        <Stat id="veh-on-trip" label="Di jalan" v={d.vehicle_summary?.on_trip} tone="#C97A00" />
        <Stat id="veh-maintenance" label="Perawatan" v={d.vehicle_summary?.maintenance} tone="#C62828" />
        <Stat id="drv-available" label="Sopir tersedia" v={d.driver_summary?.available} tone="#1A7A3A" />
        <Stat id="drv-on-trip" label="Sopir di jalan" v={d.driver_summary?.on_trip} tone="#C97A00" />
      </div>
      {err && <div className="notice-bar danger !py-1.5" data-testid="fleet-error"><span className="text-[11.5px]">{err}</span></div>}
      {msg && <div className="notice-bar success !py-1.5" data-testid="fleet-msg"><span className="text-[11.5px]">{msg}</span></div>}

      <div className="grid gap-3 lg:grid-cols-3">
        <section className="section-card !p-3 lg:col-span-2" data-testid="fleet-vehicles">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-bold flex items-center gap-1.5"><Bus size={14} className="text-[#C97A00]" /> Kendaraan ({(d.vehicles || []).length})</p>
            {canManage && !form && <button data-testid="fleet-add-button" className="primary-button !py-1 !px-2.5 !text-[11px]" onClick={() => setForm({ ...EMPTY })}><Plus size={12} /> Tambah kendaraan</button>}
          </div>
          {form && (
            <div className="grid gap-2 sm:grid-cols-3 mt-2 rounded-lg border border-[#E1E4EA] p-2.5 bg-[#FAFBFC]" data-testid="fleet-form">
              <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Plat *</label><input data-testid="fleet-plate" className="form-input" placeholder="B 1234 XYZ" value={form.plate} onChange={(e) => setForm({ ...form, plate: e.target.value })} /></div>
              <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Jenis</label><KNSelect data-testid="fleet-type" value={form.type} onValueChange={(v) => setForm({ ...form, type: v })} className="field" options={types} /></div>
              <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Nama / merk</label><input data-testid="fleet-name" className="form-input" placeholder="mis. Hino Dutro" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Kapasitas</label><input data-testid="fleet-capacity" className="form-input" placeholder="mis. 2 ton / 40 roll" value={form.capacity_note} onChange={(e) => setForm({ ...form, capacity_note: e.target.value })} /></div>
              <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Sopir tetap</label><KNSelect data-testid="fleet-driver" value={form.default_driver_user_id} onValueChange={(v) => setForm({ ...form, default_driver_user_id: v })} className="field" options={driverOpts} /></div>
              <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Catatan</label><input data-testid="fleet-notes" className="form-input" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
              <div className="sm:col-span-3 flex justify-end gap-2"><button className="secondary-button" onClick={() => setForm(null)} disabled={busy}><X size={12} /> Batal</button><button data-testid="fleet-save" className="primary-button" onClick={save} disabled={busy || form.plate.trim().length < 3}><Save size={12} /> {busy ? "Menyimpan…" : "Simpan"}</button></div>
            </div>
          )}
          {!(d.vehicles || []).length ? <p className="text-[11.5px] text-[#9A9BA3] mt-3" data-testid="fleet-empty">Belum ada kendaraan. {canManage ? "Tambahkan kendaraan agar bisa dipilih saat membuat pengiriman armada sendiri." : ""}</p> : (
            <div className="grid gap-2 sm:grid-cols-2 mt-2">
              {d.vehicles.map((v) => (
                <div key={v.id} className="rounded-lg border border-[#E1E4EA] p-2.5" data-testid={`fleet-vehicle-${v.id}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-bold text-[13px]">{v.plate}</span>
                    <span className={`status-pill ${VEHICLE_STATUS_PILL[v.status]}`} data-testid={`fleet-vehicle-status-${v.id}`}>{v.status_label}</span>
                  </div>
                  <p className="text-[11px] text-[#3A3B42] mt-0.5">{v.type_label}{v.name ? ` · ${v.name}` : ""}{v.capacity_note ? ` · ${v.capacity_note}` : ""}</p>
                  {v.default_driver_user_id && <p className="text-[10.5px] text-[#6B6B73] flex items-center gap-1"><UserRound size={10} /> {driverName(v.default_driver_user_id) || "sopir tetap"}</p>}
                  {v.status === "on_trip" && v.current_delivery_id && <button className="text-[10.5px] text-[#0058CC] hover:underline" data-testid={`fleet-vehicle-open-${v.id}`} onClick={() => onOpen(v.current_delivery_id)}>Lihat pengiriman berjalan →</button>}
                  {v.status === "maintenance" && v.status_note && <p className="text-[10.5px] text-[#C62828]">{v.status_note}</p>}
                  {canManage && (
                    <div className="flex gap-1.5 mt-1.5">
                      <button className="secondary-button !py-0.5 !px-2 !text-[10.5px]" data-testid={`fleet-vehicle-edit-${v.id}`} onClick={() => setForm({ id: v.id, plate: v.plate, type: v.type, name: v.name || "", capacity_note: v.capacity_note || "", default_driver_user_id: v.default_driver_user_id || "", notes: v.notes || "" })}>Ubah</button>
                      {v.status !== "on_trip" && <button className={`secondary-button !py-0.5 !px-2 !text-[10.5px] ${v.status === "available" ? "!text-[#C62828]" : "!text-[#1A7A3A]"}`} data-testid={`fleet-vehicle-toggle-${v.id}`} disabled={busy} onClick={() => toggleStatus(v)}>{v.status === "available" ? <><Wrench size={10} /> Perawatan</> : <><CheckCircle2 size={10} /> Tersedia lagi</>}</button>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="section-card !p-3" data-testid="fleet-drivers">
          <p className="text-[12px] font-bold flex items-center gap-1.5"><UserRound size={14} className="text-[#0058CC]" /> Sopir ({(d.drivers || []).length})</p>
          {!(d.drivers || []).length ? <p className="text-[11.5px] text-[#9A9BA3] mt-2" data-testid="fleet-drivers-empty">Belum ada akun sopir (peran <b>driver</b>). Tambahkan lewat Pengguna & Peran.</p> : (
            <div className="mt-2 divide-y divide-[#F0F1F3]">
              {d.drivers.map((u) => (
                <div key={u.id} className="flex items-center gap-2 py-1.5 text-[11.5px]" data-testid={`fleet-driver-${u.id}`}>
                  <span className="font-semibold min-w-0 truncate">{u.name}</span>
                  {u.phone && <span className="text-[#6B6B73] font-mono text-[10.5px]">{u.phone}</span>}
                  <span className={`status-pill ${VEHICLE_STATUS_PILL[u.status]} ml-auto`} data-testid={`fleet-driver-status-${u.id}`}>{u.status_label}</span>
                  {u.current_delivery_id && <button className="text-[10.5px] text-[#0058CC] hover:underline" onClick={() => onOpen(u.current_delivery_id)}>{u.current_delivery_no}</button>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Stat({ id, label, v, tone }) {
  return <div className="section-card !p-2.5" data-testid={`fleet-stat-${id}`}><p className="text-[10px] font-bold uppercase text-[#8E8E93]">{label}</p><p className="text-[20px] font-bold tabular-nums" style={{ color: tone }}>{v ?? 0}</p></div>;
}
