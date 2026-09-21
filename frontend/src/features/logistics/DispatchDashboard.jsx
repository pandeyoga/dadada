import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { PackagePlus, PackageCheck, Truck, AlertTriangle, Clock, CheckCircle2, ChevronRight, Bus, UserRound, ArrowRight, KeyRound } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import { formatDateId } from "../../components/KNDatePicker";
import { logisticsDashboard, MODE_LABEL, MODE_PILL, STATUS_PILL, carrierText } from "./logisticsApi";

// Dasbor Pengiriman — aksi cepat (SJ menunggu, serah terima pickup), visual status & moda,
// ketersediaan armada, daftar yang sedang diproses, dan yang baru selesai.
const MODE_COLORS = { expedition: "#0058CC", own_fleet: "#C97A00", self_pickup: "#6B219A" };
const FLOW = [["prepared", "Disiapkan", "#8E8E93"], ["loaded", "Dimuat", "#0058CC"], ["in_transit", "Perjalanan", "#C97A00"], ["delivered", "Terkirim", "#1A7A3A"], ["completed", "Selesai", "#126E2C"], ["failed", "Gagal", "#C62828"]];

export default function DispatchDashboard({ params, refreshKey, canManage, canUpdate, onOpen, onCreate, onGotoList, onGotoFleet }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try { setD(await logisticsDashboard(params)); setErr(""); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal memuat dasbor pengiriman."); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [params, refreshKey]); // eslint-disable-line

  if (err) return <ErrorNotice message={err} onRetry={load} testId="dispatch-error" />;
  if (loading && !d) return <div className="section-card !p-10 text-center"><p className="text-[12px] text-[#6B6B73]" data-testid="dispatch-loading">Memuat dasbor pengiriman…</p></div>;
  if (!d) return null;

  const k = d.kpi || {};
  const pickups = (d.active || []).filter((r) => r.mode === "self_pickup");
  const shipping = (d.active || []).filter((r) => r.mode !== "self_pickup");
  const modeData = Object.keys(MODE_LABEL).map((m) => ({ key: m, name: MODE_LABEL[m], value: d.by_mode_active?.[m] || 0 })).filter((x) => x.value > 0);
  const flowTotal = FLOW.reduce((s, [key]) => s + (d.counts?.[key] || 0), 0);

  return (
    <div className="grid gap-3" data-testid="dispatch-dashboard">
      {/* KPI */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2" data-testid="dispatch-kpi">
        <Kpi id="unassigned" label="SJ menunggu" value={k.unassigned_sj} icon={PackagePlus} tone="#0058CC" hint="belum dibuat pengiriman" onClick={canManage && k.unassigned_sj ? () => onCreate("") : undefined} />
        <Kpi id="waiting-pickup" label="Menunggu diambil" value={k.waiting_pickup} icon={KeyRound} tone="#6B219A" hint="pelanggan ambil sendiri" />
        <Kpi id="active" label="Diproses" value={k.active} icon={Truck} tone="#1C1C1E" hint="disiapkan · dimuat · jalan" onClick={() => onGotoList("")} />
        <Kpi id="in-transit" label="Di jalan" value={k.in_transit} icon={ArrowRight} tone="#C97A00" onClick={() => onGotoList("in_transit")} />
        <Kpi id="eta-today" label="ETA hari ini" value={k.eta_today} icon={Clock} tone="#0058CC" hint={formatDateId(d.today, "dd MMM")} />
        <Kpi id="late" label="Terlambat" value={k.late} icon={AlertTriangle} tone={k.late ? "#C62828" : "#8E8E93"} hint="lewat ETA" />
        <Kpi id="delivered-today" label="Terkirim hari ini" value={k.delivered_today} icon={CheckCircle2} tone="#1A7A3A" onClick={() => onGotoList("delivered")} />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        {/* Aksi cepat: SJ menunggu pengiriman */}
        <section className="section-card !p-3 lg:col-span-2" data-testid="dispatch-quick-actions">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-bold flex items-center gap-1.5"><PackagePlus size={14} className="text-[#0058CC]" /> Aksi cepat — Surat Jalan menunggu pengiriman <span className="tabular-nums text-[#6B6B73] font-semibold">({k.unassigned_sj})</span></p>
            {canManage && k.unassigned_sj > 0 && <button data-testid="dispatch-create-any" className="secondary-button !py-1 !px-2 !text-[11px]" onClick={() => onCreate("")}>Buat pengiriman…</button>}
          </div>
          {!(d.unassigned || []).length ? (
            <p className="text-[11.5px] text-[#9A9BA3] mt-2" data-testid="dispatch-unassigned-empty">Semua Surat Jalan yang keluar gudang sudah punya pengiriman.</p>
          ) : (
            <div className="mt-2 divide-y divide-[#F0F1F3] max-h-[300px] overflow-auto">
              {d.unassigned.map((s) => (
                <div key={s.id} className="flex items-center gap-2 py-1.5 text-[11.5px]" data-testid={`dispatch-sj-${s.id}`}>
                  <span className="font-mono font-bold text-[#0058CC] shrink-0">{s.shipment_no}</span>
                  <span className={`status-pill ${s.fulfillment_method === "ambil" ? "pill-purple" : "pill-info"} shrink-0`}>{s.fulfillment_method === "ambil" ? "Ambil sendiri" : "Kirim"}</span>
                  <span className="min-w-0 truncate"><b>{s.order_number}</b> · {s.customer_name} · {s.product_name} · <span className="tabular-nums">{s.qty} {s.unit}</span>{s.pickup_date ? ` · ambil ${s.pickup_date}` : ""}</span>
                  {canManage && <button data-testid={`dispatch-create-${s.id}`} className="primary-button !py-1 !px-2.5 !text-[11px] ml-auto shrink-0" onClick={() => onCreate(s.id)}>{s.fulfillment_method === "ambil" ? "Siapkan pickup" : "Buat pengiriman"} <ChevronRight size={11} /></button>}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Armada */}
        <section className="section-card !p-3" data-testid="dispatch-fleet">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-bold flex items-center gap-1.5"><Bus size={14} className="text-[#C97A00]" /> Armada internal</p>
            <button data-testid="dispatch-goto-fleet" className="text-[11px] font-semibold text-[#0058CC] hover:underline" onClick={onGotoFleet}>Kelola →</button>
          </div>
          <div className="grid grid-cols-3 gap-1.5 mt-2 text-center">
            <Mini label="Tersedia" v={d.fleet?.vehicle_summary?.available} tone="#1A7A3A" id="veh-available" />
            <Mini label="Di jalan" v={d.fleet?.vehicle_summary?.on_trip} tone="#C97A00" id="veh-on-trip" />
            <Mini label="Perawatan" v={d.fleet?.vehicle_summary?.maintenance} tone="#C62828" id="veh-maintenance" />
          </div>
          <div className="flex items-center gap-2 mt-2 text-[11px] text-[#3A3B42]" data-testid="dispatch-drivers">
            <UserRound size={12} className="text-[#0058CC]" /> Sopir: <b className="tabular-nums">{d.fleet?.driver_summary?.available ?? 0}</b> tersedia · <b className="tabular-nums">{d.fleet?.driver_summary?.on_trip ?? 0}</b> di jalan
          </div>
          {!(d.fleet?.vehicles || []).length && <p className="text-[10.5px] text-[#9A9BA3] mt-1.5">Belum ada kendaraan terdaftar — tambahkan di tab Armada.</p>}
          <div className="flex flex-wrap gap-1 mt-2">
            {(d.fleet?.vehicles || []).slice(0, 8).map((v) => (
              <span key={v.id} className={`status-pill ${v.status === "available" ? "pill-success" : v.status === "on_trip" ? "pill-warning" : "pill-danger"}`} title={`${v.type_label} · ${v.status_label}`} data-testid={`dispatch-veh-${v.id}`}>{v.plate}</span>
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        {/* Visual alur status */}
        <section className="section-card !p-3" data-testid="dispatch-flow">
          <p className="text-[12px] font-bold">Alur status (semua pengiriman)</p>
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-[#F0F1F3] mt-2">
            {FLOW.map(([key, , color]) => { const n = d.counts?.[key] || 0; return n ? <div key={key} style={{ width: `${(n / flowTotal) * 100}%`, background: color }} title={`${key}: ${n}`} /> : null; })}
          </div>
          <div className="grid grid-cols-3 gap-1.5 mt-2">
            {FLOW.map(([key, label, color]) => (
              <button key={key} type="button" data-testid={`dispatch-flow-${key}`} onClick={() => onGotoList(key)} className="flex items-center gap-1.5 text-left text-[11px] hover:underline">
                <span className="h-2 w-2 rounded-full shrink-0" style={{ background: color }} /> {label} <b className="tabular-nums ml-auto">{d.counts?.[key] || 0}</b>
              </button>
            ))}
          </div>
        </section>

        {/* Visual moda */}
        <section className="section-card !p-3" data-testid="dispatch-modes">
          <p className="text-[12px] font-bold">Jenis pengiriman yang diproses</p>
          {modeData.length === 0 ? <p className="text-[11.5px] text-[#9A9BA3] mt-2">Tidak ada pengiriman aktif.</p> : (
            <div className="flex items-center gap-2 mt-1">
              <div className="h-[110px] w-[110px] shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart><Pie data={modeData} dataKey="value" nameKey="name" innerRadius={30} outerRadius={50} paddingAngle={2}>
                    {modeData.map((m) => <Cell key={m.key} fill={MODE_COLORS[m.key]} />)}
                  </Pie><Tooltip formatter={(v, n) => [`${v} pengiriman`, n]} /></PieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid gap-1 text-[11px] flex-1">
                {Object.keys(MODE_LABEL).map((m) => (
                  <div key={m} className="flex items-center gap-1.5" data-testid={`dispatch-mode-${m}`}><span className="h-2 w-2 rounded-full" style={{ background: MODE_COLORS[m] }} /> {MODE_LABEL[m]} <b className="tabular-nums ml-auto">{d.by_mode_active?.[m] || 0}</b><span className="text-[#9A9BA3] tabular-nums">/ {d.by_mode?.[m] || 0}</span></div>
                ))}
                <p className="text-[9.5px] text-[#9A9BA3]">aktif / total</p>
              </div>
            </div>
          )}
        </section>

        {/* Serah terima pickup */}
        <section className="section-card !p-3" data-testid="dispatch-pickups">
          <p className="text-[12px] font-bold flex items-center gap-1.5"><KeyRound size={14} className="text-[#6B219A]" /> Menunggu diambil pelanggan <span className="tabular-nums text-[#6B6B73] font-semibold">({pickups.length})</span></p>
          {!pickups.length ? <p className="text-[11.5px] text-[#9A9BA3] mt-2">Tidak ada barang menunggu diambil.</p> : (
            <div className="mt-2 divide-y divide-[#F0F1F3] max-h-[200px] overflow-auto">
              {pickups.map((r) => (
                <div key={r.id} className="flex items-center gap-2 py-1.5 text-[11.5px]" data-testid={`dispatch-pickup-${r.id}`}>
                  <span className="min-w-0 truncate"><b>{r.order_number}</b> · {r.customer_name}{r.pickup_date ? ` · tgl ${r.pickup_date}` : ""}</span>
                  <button data-testid={`dispatch-handover-${r.id}`} className={`${canUpdate ? "primary-button" : "secondary-button"} !py-1 !px-2.5 !text-[11px] ml-auto shrink-0 ${canUpdate ? "!bg-[#6B219A]" : ""}`} onClick={() => onOpen(r.id)}>{canUpdate ? "Serah terima" : "Lihat"}</button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {/* Sedang diproses */}
        <section className="section-card !p-3" data-testid="dispatch-active">
          <p className="text-[12px] font-bold flex items-center gap-1.5"><Truck size={14} className="text-[#0058CC]" /> Pengiriman sedang diproses <span className="tabular-nums text-[#6B6B73] font-semibold">({shipping.length})</span></p>
          {!shipping.length ? <p className="text-[11.5px] text-[#9A9BA3] mt-2">Tidak ada pengiriman berjalan.</p> : (
            <div className="mt-2 divide-y divide-[#F0F1F3] max-h-[320px] overflow-auto">
              {shipping.map((r) => <ActiveRow key={r.id} r={r} onOpen={onOpen} />)}
            </div>
          )}
        </section>

        {/* Baru selesai */}
        <section className="section-card !p-3" data-testid="dispatch-recent">
          <div className="flex items-center justify-between"><p className="text-[12px] font-bold flex items-center gap-1.5"><PackageCheck size={14} className="text-[#1A7A3A]" /> Baru selesai / gagal</p>
            <button data-testid="dispatch-goto-history" className="text-[11px] font-semibold text-[#0058CC] hover:underline" onClick={() => onGotoList("delivered")}>Semua terkirim →</button></div>
          {!(d.recent || []).length ? <p className="text-[11.5px] text-[#9A9BA3] mt-2">Belum ada riwayat.</p> : (
            <div className="mt-2 divide-y divide-[#F0F1F3]">
              {d.recent.map((r) => <ActiveRow key={r.id} r={r} onOpen={onOpen} />)}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Kpi({ id, label, value, icon: Icon, tone, hint, onClick }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag type={onClick ? "button" : undefined} onClick={onClick} data-testid={`dispatch-kpi-${id}`} className={`section-card !p-2.5 text-left ${onClick ? "hover:bg-[#F7F9FC] transition-colors" : ""}`}>
      <div className="flex items-center justify-between"><p className="text-[10px] font-bold uppercase text-[#8E8E93]">{label}</p><Icon size={13} style={{ color: tone }} /></div>
      <p className="text-[20px] font-bold tabular-nums leading-tight" style={{ color: tone }}>{value ?? 0}</p>
      {hint && <p className="text-[9.5px] text-[#9A9BA3] truncate">{hint}</p>}
    </Tag>
  );
}

function Mini({ id, label, v, tone }) {
  return <div className="rounded-md bg-[#F7F9FC] py-1.5" data-testid={`dispatch-${id}`}><p className="text-[16px] font-bold tabular-nums" style={{ color: tone }}>{v ?? 0}</p><p className="text-[9.5px] uppercase font-bold text-[#8E8E93]">{label}</p></div>;
}

function ActiveRow({ r, onOpen }) {
  return (
    <button type="button" data-testid={`dispatch-row-${r.id}`} onClick={() => onOpen(r.id)} className="w-full flex items-center gap-2 py-1.5 text-left text-[11.5px] hover:bg-[#F7F9FC] rounded px-1">
      <span className="font-mono font-bold text-[#0058CC] shrink-0">{r.number}</span>
      <span className={`status-pill ${MODE_PILL[r.mode]} shrink-0`}>{r.mode_label}</span>
      <span className="min-w-0 truncate"><b>{r.order_number}</b> · {r.customer_name} · <span className="text-[#6B6B73]">{carrierText(r)}</span></span>
      {r.is_late && <span className="text-[#C62828] text-[10px] font-bold inline-flex items-center gap-0.5 shrink-0"><AlertTriangle size={10} /> lewat ETA</span>}
      {r.eta && !r.is_late && <span className="text-[10px] text-[#6B6B73] tabular-nums shrink-0">ETA {formatDateId(r.eta, "dd MMM")}</span>}
      <span className={`status-pill ${STATUS_PILL[r.status]} ml-auto shrink-0`}>{r.status_label}</span>
    </button>
  );
}
