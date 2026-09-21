/**
 * RfidSecurityPanel (FASE R6) — Alarm/insiden gate MERAH (acknowledge → resolve),
 * laporan shrinkage, dan monitor heartbeat device.
 */
import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, HeartPulse, ShieldAlert } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { Pill, SectionCard, fmtTime, EmptyBox } from "./rfidShared";

const SEV = { high: ["red", "Tinggi"], medium: ["orange", "Sedang"] };
const HEALTH = { online: ["green", "Online"], stale: ["orange", "Stale (>5 mnt)"], offline: ["gray", "Offline"] };

export default function RfidSecurityPanel({ whId, selectedEntity }) {
  const [incidents, setIncidents] = useState([]);
  const [statusFilter, setStatusFilter] = useState("open");
  const [shrink, setShrink] = useState(null);
  const [health, setHealth] = useState(null);
  const [noteFor, setNoteFor] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const [i, s, h] = await Promise.all([
        axios.get(`${API}/rfid/incidents`, { params: { status: statusFilter || undefined, warehouse_id: whId || undefined } }),
        axios.get(`${API}/rfid/shrinkage-report`, { params: { days: 30 } }),
        axios.get(`${API}/rfid/device-health`),
      ]);
      setIncidents(i.data.incidents || []); setShrink(s.data); setHealth(h.data);
    } catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  useEffect(() => { load(); }, [whId, statusFilter, selectedEntity]); // eslint-disable-line

  const act = async (inc, action) => {
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/rfid/incidents/${inc.id}/${action}`, { note });
      setNoteFor(null); setNote(""); await load();
    } catch (e) { setError(e.response?.data?.detail || "Gagal"); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-3" data-testid="rfid-security-panel">
      {error && <p className="rounded bg-[#FBE9E7] px-3 py-2 text-[12px] font-semibold text-[#C0341D]">{error}</p>}

      {shrink && (
        <div className="grid grid-cols-3 gap-2" data-testid="rfid-shrinkage-stats">
          {[["Red reads (30 hari)", shrink.totals.red_reads, "#C0341D"],
            ["Insiden terbuka", shrink.totals.incidents_open, "#FF9500"],
            ["Roll gate exception", shrink.totals.gate_exception_rolls, "#6B219A"]].map(([l, v, c]) => (
            <div key={l} className="rounded-lg border border-[#EFF0F2] bg-white p-2.5">
              <p className="text-[10px] font-bold uppercase text-[#8E8E93]">{l}</p>
              <p className="text-[20px] font-black" style={{ color: c }}>{v}</p>
            </div>
          ))}
        </div>
      )}

      <SectionCard title="Alarm Insiden Gate" right={
        <div className="flex gap-1">
          {["open", "acknowledged", "resolved", ""].map((s) => (
            <button key={s || "all"} data-testid={`rfid-inc-filter-${s || "all"}`}
              onClick={() => setStatusFilter(s)}
              className={`rounded px-2 py-1 text-[10.5px] font-semibold ${statusFilter === s ? "bg-[#1C1C1E] text-white" : "bg-[#F5F5F7] text-[#6B6B73]"}`}>
              {{ open: "Terbuka", acknowledged: "Di-ack", resolved: "Selesai", "": "Semua" }[s]}
            </button>
          ))}
        </div>}>
        {incidents.length === 0 ? <EmptyBox icon={ShieldAlert} text="Tidak ada insiden." /> : (
          <div className="max-h-96 space-y-1.5 overflow-y-auto">
            {incidents.map((inc) => {
              const [color, sev] = SEV[inc.severity] || ["gray", inc.severity];
              return (
                <div key={inc.id} data-testid={`rfid-incident-${inc.id}`} className="rounded-lg border border-[#F0F0F2] p-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <AlertTriangle size={14} className="text-[#C0341D]" />
                    <span className="min-w-0 flex-1">
                      <span className="block text-[12px] font-bold">{inc.roll_no || inc.epc} <span className="font-normal text-[#6B6B73]">· {inc.product_name || "EPC asing"}</span>
                        {inc.hits > 1 && <span className="ml-1 rounded bg-[#FBE9E7] px-1 text-[10px] font-bold text-[#C0341D]">×{inc.hits}</span>}
                      </span>
                      <span className="block text-[11px] text-[#6B6B73]">{inc.reason}</span>
                      <span className="block text-[10px] text-[#9A9BA3]">{inc.device_name} · {fmtTime(inc.last_at)}{inc.ack_by ? ` · ack: ${inc.ack_by}` : ""}{inc.resolved_by ? ` · selesai: ${inc.resolved_by}` : ""}</span>
                    </span>
                    <Pill color={color}>{sev}</Pill>
                    <Pill color={inc.status === "open" ? "red" : inc.status === "acknowledged" ? "orange" : "green"}>
                      {{ open: "TERBUKA", acknowledged: "DI-ACK", resolved: "SELESAI" }[inc.status]}
                    </Pill>
                    {inc.status !== "resolved" && (
                      <button data-testid={`rfid-inc-act-${inc.id}`} disabled={busy}
                        onClick={() => { setNoteFor(noteFor === inc.id ? null : inc.id); setNote(""); }}
                        className="rounded-lg bg-[#1C1C1E] px-2.5 py-1 text-[10.5px] font-semibold text-white disabled:opacity-40">
                        Tindak
                      </button>
                    )}
                  </div>
                  {noteFor === inc.id && (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5" data-testid={`rfid-inc-actions-${inc.id}`}>
                      <input data-testid={`rfid-inc-note-${inc.id}`} className="field flex-1 py-1 text-[11px]"
                        placeholder="Catatan tindakan…" value={note} onChange={(e) => setNote(e.target.value)} />
                      {inc.status === "open" && (
                        <button data-testid={`rfid-inc-ack-${inc.id}`} disabled={busy} onClick={() => act(inc, "acknowledge")}
                          className="rounded bg-[#FF9500] px-2.5 py-1 text-[10.5px] font-semibold text-white disabled:opacity-40">Acknowledge</button>
                      )}
                      <button data-testid={`rfid-inc-resolve-${inc.id}`} disabled={busy} onClick={() => act(inc, "resolve")}
                        className="rounded bg-[#1B7F4B] px-2.5 py-1 text-[10.5px] font-semibold text-white disabled:opacity-40">
                        <CheckCircle2 size={11} className="mr-0.5 inline" /> Selesaikan</button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </SectionCard>

      <div className="grid gap-3 lg:grid-cols-2">
        <SectionCard title="Shrinkage per Gudang (30 hari)">
          {!shrink || shrink.per_warehouse.length === 0 ? <EmptyBox icon={ShieldAlert} text="Belum ada data." /> : (
            <table className="w-full text-[11.5px]" data-testid="rfid-shrinkage-table">
              <thead><tr className="border-b border-[#EFF0F2] text-left text-[10px] text-[#8E8E93]">
                <th className="py-1">Gudang</th><th className="text-right">Red</th>
                <th className="text-right">Terbuka</th><th className="text-right">Exception</th></tr></thead>
              <tbody>{shrink.per_warehouse.map((r) => (
                <tr key={r.warehouse_id || "-"} className="border-b border-[#F5F5F7]">
                  <td className="py-1.5 font-semibold">{r.warehouse_name}</td>
                  <td className="text-right text-[#C0341D] font-bold">{r.red_reads}</td>
                  <td className="text-right">{r.incidents_open}</td>
                  <td className="text-right">{r.gate_exception_rolls}</td>
                </tr>))}</tbody>
            </table>
          )}
        </SectionCard>

        <SectionCard title={`Kesehatan Device${health ? ` (${health.stale_count} stale)` : ""}`}>
          {!health ? null : (
            <div className="max-h-64 space-y-1 overflow-y-auto" data-testid="rfid-device-health">
              {health.devices.map((d) => {
                const [color, label] = HEALTH[d.effective_status] || ["gray", d.effective_status];
                return (
                  <div key={d.id} className="flex items-center gap-2 rounded bg-[#FAFAFB] px-2 py-1.5">
                    <HeartPulse size={13} className={d.effective_status === "online" ? "text-[#1B7F4B]" : "text-[#B23B14]"} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-[11.5px] font-semibold">{d.name} <span className="font-normal text-[#8E8E93]">· {d.code}</span></span>
                      <span className="block text-[10px] text-[#9A9BA3]">
                        heartbeat {d.heartbeat_age_sec == null ? "belum pernah" : d.heartbeat_age_sec < 60 ? `${d.heartbeat_age_sec}s lalu` : `${Math.floor(d.heartbeat_age_sec / 60)}m lalu`}
                      </span>
                    </span>
                    <Pill color={color}>{label}</Pill>
                  </div>
                );
              })}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
