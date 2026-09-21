/**
 * WmsHealthDashboard — KESEHATAN GUDANG dalam satu layar ringkas:
 * insiden terbuka, red reads hari ini, antrean putaway, PA aktif, gate exception,
 * roll tanpa tag, akurasi cycle count terakhir, device stale. Read-only.
 */
import { useEffect, useState } from "react";
import { Activity, AlertTriangle, ClipboardCheck, PackageSearch, RefreshCw, Printer } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import PrinterStatusWidget from "../../components/PrinterStatusWidget";

const nf = new Intl.NumberFormat("id-ID");

const TOTAL_CARDS = [
  ["open_incidents", "Insiden Terbuka", "#C0341D"],
  ["red_reads_today", "Red Reads Hari Ini", "#B23B14"],
  ["putaway_ready", "Antrean Simpan ke Rak", "#0058CC"],
  ["gate_exceptions", "Gate Exception", "#6B219A"],
  ["untagged", "Roll Tanpa Tag", "#FF9500"],
  ["devices_stale", "Device Stale", "#8C4A00"],
];

export default function WmsHealthDashboard({ selectedEntity }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = () => {
    axios.get(`${API}/wms/health-dashboard`)
      .then((r) => { setData(r.data); setError(""); })
      .catch((e) => setError(e.response?.data?.detail || e.message));
  };
  useEffect(() => { load(); }, [selectedEntity]); // eslint-disable-line

  const accColor = (p) => (p == null ? "#8E8E93" : p >= 100 ? "#1B7F4B" : p >= 95 ? "#FF9500" : "#C0341D");

  return (
    <div className="space-y-3" data-testid="wms-health-dashboard">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-1.5 text-[13px] font-bold">
          <Activity size={15} className="text-[#0058CC]" /> Kesehatan Gudang (semua lokasi)
        </p>
        <button data-testid="wms-health-refresh" onClick={load}
          className="flex items-center gap-1 rounded-lg border border-[#EFF0F2] bg-white px-2.5 py-1 text-[11px] font-semibold hover:bg-[#F5F5F7]">
          <RefreshCw size={12} /> Segarkan
        </button>
      </div>
      {error && <p className="rounded bg-[#FBE9E7] px-3 py-2 text-[12px] font-semibold text-[#C0341D]">{error}</p>}

      <section className="rounded-xl border border-[#EFF0F2] bg-[#FAFAFB] p-3" data-testid="wms-health-printers">
        <p className="mb-2 flex items-center gap-1.5 text-[12px] font-bold"><Printer size={13} className="text-[#0058CC]" /> Printer Label & Antrean</p>
        <PrinterStatusWidget />
      </section>

      {data && (
        <>
          <div className="grid grid-cols-3 gap-2 lg:grid-cols-6" data-testid="wms-health-totals">
            {TOTAL_CARDS.map(([k, label, color]) => (
              <div key={k} className="rounded-lg border border-[#EFF0F2] bg-white p-2.5">
                <p className="text-[9.5px] font-bold uppercase tracking-wide text-[#8E8E93]">{label}</p>
                <p className="text-[20px] font-black" style={{ color: data.totals[k] ? color : "#C7C7CC" }}>
                  {nf.format(data.totals[k])}
                </p>
              </div>
            ))}
          </div>

          <div className="overflow-x-auto rounded-xl border border-[#EFF0F2] bg-white">
            <table className="w-full text-[12px]" data-testid="wms-health-table">
              <thead>
                <tr className="border-b border-[#EFF0F2] text-left text-[10px] uppercase tracking-wide text-[#8E8E93]">
                  <th className="px-3 py-2">Gudang</th>
                  <th className="px-2 py-2 text-right" title="Insiden alarm gate belum ditindak">Insiden</th>
                  <th className="px-2 py-2 text-right" title="Pembacaan gate MERAH hari ini">Red Hari Ini</th>
                  <th className="px-2 py-2 text-right" title="Roll terverifikasi menunggu Perintah Simpan ke Rak">Antrean Simpan ke Rak</th>
                  <th className="px-2 py-2 text-right" title="PA terbuka / dalam perjalanan ke gudang ini">PA Aktif</th>
                  <th className="px-2 py-2 text-right" title="Roll exception di gate-in">Exception</th>
                  <th className="px-2 py-2 text-right" title="Roll fisik tanpa tag RFID">Tanpa Tag</th>
                  <th className="px-2 py-2 text-right" title="Akurasi stock opname RFID terakhir">Opname Terakhir</th>
                  <th className="px-2 py-2 text-right" title="Device online tapi heartbeat >5 menit">Device</th>
                </tr>
              </thead>
              <tbody>
                {data.warehouses.map((w) => (
                  <tr key={w.warehouse_id} className="border-b border-[#F5F5F7] hover:bg-[#FAFBFC]"
                    data-testid={`wms-health-row-${w.warehouse_id}`}>
                    <td className="px-3 py-2">
                      <span className="font-semibold">{w.warehouse_name}</span>
                      {w.roles?.length > 0 && (
                        <span className="ml-1.5 text-[9.5px] font-bold uppercase text-[#8E8E93]">
                          {w.roles.join(" · ")}
                        </span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-right">
                      {w.open_incidents > 0
                        ? <span className="inline-flex items-center gap-0.5 font-black text-[#C0341D]"><AlertTriangle size={11} />{w.open_incidents}</span>
                        : <span className="text-[#C7C7CC]">0</span>}
                    </td>
                    <td className="px-2 py-2 text-right font-semibold" style={{ color: w.red_reads_today ? "#B23B14" : "#C7C7CC" }}>{w.red_reads_today}</td>
                    <td className="px-2 py-2 text-right font-semibold" style={{ color: w.putaway_ready ? "#0058CC" : "#C7C7CC" }}>{w.putaway_ready}</td>
                    <td className="px-2 py-2 text-right" style={{ color: w.pa_open ? "#FF9500" : "#C7C7CC" }}>{w.pa_open}</td>
                    <td className="px-2 py-2 text-right font-semibold" style={{ color: w.gate_exceptions ? "#6B219A" : "#C7C7CC" }}>{w.gate_exceptions}</td>
                    <td className="px-2 py-2 text-right" style={{ color: w.untagged ? "#FF9500" : "#C7C7CC" }}>{w.untagged}</td>
                    <td className="px-2 py-2 text-right">
                      {w.last_cc ? (
                        <span className="font-bold" style={{ color: accColor(w.last_cc.accuracy_pct) }}>
                          {w.last_cc.accuracy_pct}%
                          <span className="ml-1 font-normal text-[10px] text-[#9A9BA3]">{w.last_cc.cc_number}</span>
                        </span>
                      ) : <span className="text-[#C7C7CC]">—</span>}
                    </td>
                    <td className="px-2 py-2 text-right">
                      {w.devices_total === 0 ? <span className="text-[#C7C7CC]">—</span> : (
                        <span className={w.devices_stale ? "font-bold text-[#8C4A00]" : "text-[#1B7F4B]"}>
                          {w.devices_total - w.devices_stale}/{w.devices_total} hidup
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="flex items-center gap-1 text-[10.5px] text-[#8E8E93]">
            <ClipboardCheck size={11} /> Insiden ditindak di Gate Monitor → Alarm & Keamanan · antrean putaway di Lokasi & Penempatan → Putaway Order · opname di Lokasi RFID → Cycle Count
          </p>
        </>
      )}
      {!data && !error && <div className="h-40 animate-pulse rounded-xl bg-[#F5F5F7]" data-testid="wms-health-loading"><PackageSearch className="hidden" /></div>}
    </div>
  );
}
