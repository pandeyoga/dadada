import { useEffect, useState } from "react";
import { Route, ArrowUp, ArrowDown, MapPin, Clock, CheckCircle2, AlertTriangle, Navigation, Phone, MessageCircle } from "lucide-react";
import { listDeliveries, setMyRoute, STATUS_LABEL, STATUS_PILL, mapsUrl, telUrl, waUrl, todayWib } from "./logisticsApi";
import { formatDateId } from "../../components/KNDatePicker";

// Tugas sopir hari ini: pengiriman milik sopir yang login, berurutan tujuan (bisa disusun ulang).
const ACTIVE = ["prepared", "loaded", "in_transit"];

export default function DriverTodayPanel({ params, onOpen, refreshKey }) {
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const today = todayWib();

  async function load() {
    try { setRows(await listDeliveries({ ...params, mine: true })); setErr(""); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal memuat tugas."); }
  }
  useEffect(() => { load(); }, [refreshKey]); // eslint-disable-line

  const tasks = rows.filter((d) => ACTIVE.includes(d.status));
  const doneToday = rows.filter((d) => ["delivered", "completed"].includes(d.status) && String(d.delivered_at || d.completed_at || "").slice(0, 10) === today);

  async function move(i, dir) {
    const j = i + dir;
    if (j < 0 || j >= tasks.length) return;
    const next = [...tasks]; [next[i], next[j]] = [next[j], next[i]];
    setBusy(true); setErr("");
    try { await setMyRoute(next.map((d) => d.id)); await load(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan urutan."); }
    finally { setBusy(false); }
  }

  return (
    <section className="section-card !p-3" data-testid="driver-today-panel">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="flex items-center gap-1.5 text-[13px] font-bold"><Route size={15} className="text-[#0058CC]" /> Tugas Saya Hari Ini <span className="text-[#6B6B73] font-normal">· {today}</span></span>
        <span className="text-[11px] text-[#6B6B73] flex items-center gap-1" data-testid="driver-today-summary"><b>{tasks.length}</b> tujuan aktif · <CheckCircle2 size={12} className="text-[#1F7A45]" /> <b>{doneToday.length}</b> terkirim hari ini</span>
      </div>
      {err && <div className="notice-bar danger !my-2 !py-1.5" data-testid="driver-today-error"><span className="text-[11.5px]">{err}</span></div>}
      {tasks.length === 0 ? (
        <p className="text-[12px] text-[#9A9BA3] mt-2" data-testid="driver-today-empty">Tidak ada pengiriman aktif yang ditugaskan kepada Anda.</p>
      ) : (
        <ol className="grid gap-1.5 mt-2" data-testid="driver-today-list">
          {tasks.map((d, i) => {
            const late = d.eta && d.eta < today;
            return (
              <li key={d.id} data-testid={`driver-task-${d.id}`} className="flex flex-wrap sm:flex-nowrap items-stretch gap-2 rounded-lg border border-[#E1E4EA] bg-white hover:bg-[#F7F9FC]">
                <div className="w-9 flex items-center justify-center rounded-l-lg bg-[#0058CC] text-white text-[15px] font-bold tabular-nums" data-testid={`driver-task-order-${d.id}`}>{i + 1}</div>
                <button type="button" className="flex-1 text-left py-2 min-w-0" onClick={() => onOpen(d.id)}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-[11px] font-bold text-[#0058CC]">{d.number}</span>
                    <span className="text-[12px] font-semibold truncate">{d.customer_name}</span>
                    <span className={`status-pill ${STATUS_PILL[d.status]}`}>{STATUS_LABEL[d.status]}</span>
                    {late && <span className="flex items-center gap-1 text-[10px] font-bold text-[#C0341D]" data-testid={`driver-task-late-${d.id}`}><AlertTriangle size={11} /> Lewat ETA</span>}
                  </div>
                  <div className="text-[11px] text-[#6B6B73] mt-0.5 flex items-center gap-1 truncate"><MapPin size={11} className="shrink-0" /> {d.destination || "Tujuan belum diisi"}</div>
                  {d.receiver_phone && (
                    <div className="text-[11px] text-[#3A3B42] mt-0.5 flex items-center gap-1 flex-wrap" data-testid={`driver-task-phone-${d.id}`}>
                      <Phone size={11} className="shrink-0 text-[#0058CC]" /> {d.receiver_name_hint ? `${d.receiver_name_hint} · ` : ""}<span className="font-mono">{d.receiver_phone}</span>
                    </div>
                  )}
                  <div className="text-[10.5px] text-[#9A9BA3] mt-0.5 flex items-center gap-2 flex-wrap">
                    <span className="flex items-center gap-1"><Clock size={10} /> ETA {d.eta ? formatDateId(d.eta, "dd MMM yyyy") : "—"}</span>
                    <span>SJ {(d.shipment_nos || []).join(", ")}</span>
                    {d.vehicle_plate && <span>{d.vehicle_plate}</span>}
                    {d.last_position && <span>Posisi: {d.last_position.location}</span>}
                  </div>
                </button>
                <div className="flex items-center gap-1 pr-1.5 pl-1.5 sm:pl-0 pb-1.5 sm:pb-0 w-full sm:w-auto flex-wrap">
                  {d.receiver_phone && (<>
                    <a data-testid={`driver-task-call-${d.id}`} href={telUrl(d.receiver_phone)} onClick={(e) => e.stopPropagation()}
                      className="secondary-button !py-1.5 !px-2.5 !text-[11px] whitespace-nowrap" title={`Telepon ${d.receiver_phone}`}><Phone size={13} /> Telepon</a>
                    <a data-testid={`driver-task-wa-${d.id}`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                      href={waUrl(d.receiver_phone, `Halo${d.receiver_name_hint ? ` ${d.receiver_name_hint}` : ""}, saya ${"sopir"} Kain Nusantara membawa kiriman ${d.number} (${(d.shipment_nos || []).join(", ")}) untuk ${d.customer_name}. Perkiraan tiba sebentar lagi, mohon disiapkan penerimaannya. Terima kasih.`)}
                      className="secondary-button !py-1.5 !px-2.5 !text-[11px] whitespace-nowrap !border-[#1F7A45] !text-[#1F7A45]" title="Kirim WhatsApp ke penerima"><MessageCircle size={13} /> WA</a>
                  </>)}
                  {d.destination && (
                    <a data-testid={`driver-task-nav-${d.id}`} href={mapsUrl(d.destination)} target="_blank" rel="noopener noreferrer"
                      className="primary-button !py-1.5 !px-2.5 !text-[11px] whitespace-nowrap" title="Buka Google Maps ke alamat tujuan">
                      <Navigation size={13} /> Navigasi
                    </a>
                  )}
                  <div className="flex flex-col justify-center gap-0.5">
                    <button type="button" data-testid={`driver-task-up-${d.id}`} className="icon-button !p-2 sm:!p-1 min-h-[40px] min-w-[40px] sm:min-h-0 sm:min-w-0" disabled={busy || i === 0} onClick={() => move(i, -1)} title="Naikkan urutan" aria-label="Naikkan urutan"><ArrowUp size={15} /></button>
                    <button type="button" data-testid={`driver-task-down-${d.id}`} className="icon-button !p-2 sm:!p-1 min-h-[40px] min-w-[40px] sm:min-h-0 sm:min-w-0" disabled={busy || i === tasks.length - 1} onClick={() => move(i, 1)} title="Turunkan urutan" aria-label="Turunkan urutan"><ArrowDown size={15} /></button>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
