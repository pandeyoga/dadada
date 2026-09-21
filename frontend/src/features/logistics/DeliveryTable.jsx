import { useMemo, useState } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown, Camera, MapPin, ExternalLink, ChevronRight, AlertTriangle } from "lucide-react";
import { STATUS_PILL, MODE_PILL, todayWib, carrierText } from "./logisticsApi";
import { formatDateId } from "../../components/KNDatePicker";
import { openOrderJourney } from "./logisticsDeepLink";

// Tabel pengiriman: kolom bisa diurutkan, baris → detail (klik / Enter), tautan ke Pesanan,
// ETA terlambat disorot. Di layar sempit (ponsel sopir) berubah menjadi kartu.
const COLS = [
  { key: "number", label: "Nomor" },
  { key: "order_number", label: "Pesanan / Pelanggan" },
  { key: "shipment", label: "Surat Jalan", sortable: false },
  { key: "mode_label", label: "Moda" },
  { key: "carrier", label: "Resi / Kendaraan", sortable: false },
  { key: "eta", label: "ETA" },
  { key: "position", label: "Posisi terakhir", sortable: false },
  { key: "photos", label: "Foto", sortable: false },
  { key: "status", label: "Status" },
];
const ORDER = ["prepared", "loaded", "in_transit", "delivered", "completed", "failed"];
const ACTIVE = ["prepared", "loaded", "in_transit"];

export default function DeliveryTable({ rows, onOpen, canOpenOrder }) {
  const [sort, setSort] = useState({ key: "number", dir: "desc" });
  const today = todayWib();
  const sorted = useMemo(() => {
    const val = (d) => sort.key === "status" ? ORDER.indexOf(d.status) : sort.key === "eta" ? (d.eta || "9999") : String(d[sort.key] ?? "");
    return [...rows].sort((a, b) => { const x = val(a), y = val(b); return (x > y ? 1 : x < y ? -1 : 0) * (sort.dir === "asc" ? 1 : -1); });
  }, [rows, sort]);
  const toggle = (key) => setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));
  const isLate = (d) => d.eta && d.eta < today && ACTIVE.includes(d.status);
  const carrier = carrierText;
  const openOrder = (e, d) => { e.stopPropagation(); openOrderJourney(d.order_id); };

  return (
    <>
      <div className="section-card !p-0 overflow-x-auto hidden sm:block">
        <table className="data-table w-full" data-testid="logistics-table">
          <thead><tr>
            {COLS.map((c) => (
              <th key={c.key}>
                {c.sortable === false ? c.label : (
                  <button type="button" data-testid={`logistics-sort-${c.key}`} onClick={() => toggle(c.key)} aria-sort={sort.key === c.key ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                    className={`inline-flex items-center gap-1 hover:text-[#0058CC] ${sort.key === c.key ? "text-[#0058CC]" : ""}`}>
                    {c.label}{sort.key === c.key ? (sort.dir === "asc" ? <ArrowUp size={11} /> : <ArrowDown size={11} />) : <ArrowUpDown size={11} className="opacity-40" />}
                  </button>
                )}
              </th>
            ))}
            <th className="w-8" />
          </tr></thead>
          <tbody>
            {sorted.map((d) => (
              <tr key={d.id} data-testid={`logistics-row-${d.id}`} tabIndex={0} role="button" aria-label={`Buka detail ${d.number}`}
                className="cursor-pointer hover:bg-[#F0F5FF] focus:bg-[#F0F5FF] focus:outline-none transition-colors"
                onClick={() => onOpen(d.id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(d.id); } }}>
                <td className="font-mono text-[11.5px] font-bold text-[#0058CC]">{d.number}</td>
                <td>
                  <div className="flex items-center gap-1 text-[12px] font-semibold">
                    {canOpenOrder ? (
                      <button type="button" data-testid={`logistics-open-order-${d.id}`} className="inline-flex items-center gap-1 hover:underline text-[#0058CC]" title="Buka pesanan & Perjalanan Pesanan" onClick={(e) => openOrder(e, d)}>{d.order_number} <ExternalLink size={10} /></button>
                    ) : d.order_number}
                  </div>
                  <div className="text-[10.5px] text-[#6B6B73]">{d.customer_name}</div>
                </td>
                <td className="text-[11px]">{(d.shipment_nos || []).join(", ")}</td>
                <td className="text-[11.5px]"><span className={`status-pill ${MODE_PILL[d.mode] || "pill-muted"}`}>{d.mode_label}</span></td>
                <td className="text-[11.5px]">{carrier(d)}</td>
                <td className={`text-[11.5px] tabular-nums ${isLate(d) ? "text-[#C0341D] font-bold" : ""}`} data-testid={`logistics-eta-${d.id}`}>
                  {d.eta ? formatDateId(d.eta, "dd MMM yyyy") : "—"}{isLate(d) && <span className="ml-1 inline-flex items-center gap-0.5 text-[9.5px]" title="Melewati ETA"><AlertTriangle size={10} /> terlambat</span>}
                </td>
                <td className="text-[11px] text-[#6B6B73]">{d.last_position ? <span className="flex items-center gap-1"><MapPin size={11} />{d.last_position.location}</span> : "—"}</td>
                <td className="text-[11px]"><span className="flex items-center gap-1"><Camera size={11} /> {d.photo_counts?.load || 0} muat · {d.photo_counts?.pod || 0} POD</span></td>
                <td><span className={`status-pill ${STATUS_PILL[d.status]}`} data-testid={`logistics-status-${d.id}`}>{d.status_label}</span></td>
                <td className="text-[#9A9BA3]"><ChevronRight size={14} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-3 py-2 text-[10.5px] text-[#9A9BA3] border-t border-[#F0F1F3]" data-testid="logistics-table-footer">{sorted.length} pengiriman · klik baris untuk detail, klik nomor pesanan untuk Perjalanan Pesanan</div>
      </div>

      {/* Kartu untuk layar sempit */}
      <div className="grid gap-2 sm:hidden" data-testid="logistics-cards">
        {sorted.map((d) => (
          <button key={d.id} type="button" data-testid={`logistics-card-${d.id}`} onClick={() => onOpen(d.id)} className="section-card !p-3 text-left hover:bg-[#F0F5FF]">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[11.5px] font-bold text-[#0058CC]">{d.number}</span>
              <span className={`status-pill ${STATUS_PILL[d.status]}`}>{d.status_label}</span>
            </div>
            <div className="text-[12px] font-semibold mt-1">{d.order_number} · {d.customer_name}</div>
            <div className="text-[11px] text-[#6B6B73] mt-0.5">{d.mode_label} · {carrier(d)}</div>
            <div className="flex items-center gap-3 text-[10.5px] text-[#6B6B73] mt-1 flex-wrap">
              <span className={isLate(d) ? "text-[#C0341D] font-bold" : ""}>ETA {d.eta || "—"}</span>
              {d.last_position && <span className="flex items-center gap-1"><MapPin size={10} />{d.last_position.location}</span>}
              <span className="flex items-center gap-1"><Camera size={10} /> {d.photo_counts?.load || 0}/{d.photo_counts?.pod || 0}</span>
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
