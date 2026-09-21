/**
 * CycleCountPanel — stock opname kilat via sweep RFID handheld (report-only,
 * SSOT aman: tidak mengubah kuantitas). Expected = semua tag aktif di gudang.
 */
import { useEffect, useState } from "react";
import { ClipboardCheck, Zap, PlayCircle } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { SectionCard, EmptyBox, Pill, fmtTime } from "./rfidShared";

export default function CycleCountPanel({ whId, selectedEntity }) {
  const [session, setSession] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [epcInput, setEpcInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadHistory = async () => {
    try {
      const r = await axios.get(`${API}/rfid/cycle-counts`, { params: { warehouse_id: whId || undefined } });
      setHistory(r.data.counts || []);
    } catch { /* noop */ }
  };
  useEffect(() => { loadHistory(); setSession(null); setResult(null); }, [whId, selectedEntity]); // eslint-disable-line

  const run = async (fn) => {
    setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(e.response?.data?.detail || "Gagal"); } finally { setBusy(false); }
  };
  const start = () => run(async () => {
    const r = await axios.post(`${API}/rfid/cycle-count/start`, { warehouse_id: whId });
    setSession(r.data); setResult(null);
  });
  const scan = (epcs) => run(async () => {
    const r = await axios.post(`${API}/rfid/verify-sessions/${session.id}/scan`, { epcs });
    setSession(r.data); setEpcInput("");
  });
  const complete = () => run(async () => {
    const r = await axios.post(`${API}/rfid/cycle-count/${session.id}/complete`);
    setResult(r.data); setSession(null); await loadHistory();
  });

  return (
    <div className="space-y-3" data-testid="cycle-count-panel">
      {error && <p data-testid="cc-error" className="rounded bg-[#FBE9E7] px-3 py-2 text-[12px] font-semibold text-[#C0341D]">{error}</p>}

      <SectionCard title="Stock Opname Kilat (Sweep RFID)" right={
        !session && (
          <button data-testid="cc-start" disabled={busy || !whId} onClick={start}
            className="flex items-center gap-1 rounded-lg bg-[#0058CC] px-3 py-1.5 text-[12px] font-semibold text-white disabled:opacity-40">
            <PlayCircle size={13} /> Mulai Stock Opname
          </button>
        )}>
        {!whId && <p className="text-[12px] text-[#8E8E93]">Pilih gudang dulu di atas.</p>}
        {session && (
          <div className="space-y-2" data-testid="cc-session">
            <p className="text-[12px] font-semibold" data-testid="cc-progress">
              Terbaca {session.matched_count ?? (session.scanned_epcs || []).length}/{session.expected_count ?? session.expected?.length} tag
            </p>
            <textarea data-testid="cc-input" className="field h-16 w-full font-mono text-[11px]"
              placeholder="Tempel EPC hasil sweep handheld (Chainway)…" value={epcInput}
              onChange={(e) => setEpcInput(e.target.value)} />
            <div className="flex flex-wrap gap-1.5">
              <button data-testid="cc-scan" disabled={busy || !epcInput.trim()}
                onClick={() => scan(epcInput.split(/[\s,;]+/).filter(Boolean))}
                className="rounded-lg bg-[#0058CC] px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40">Kirim Scan</button>
              <button data-testid="cc-simulate" disabled={busy}
                onClick={() => scan((session.expected || []).map((e) => e.epc))}
                className="flex items-center gap-1 rounded-lg border border-[#0058CC] px-3 py-1.5 text-[11px] font-semibold text-[#0058CC] disabled:opacity-40">
                <Zap size={12} /> Simulasi Scan Semua</button>
              <button data-testid="cc-complete" disabled={busy} onClick={complete}
                className="ml-auto rounded-lg bg-[#1B7F4B] px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40">
                Rekonsiliasi & Selesai</button>
            </div>
          </div>
        )}
        {result && (
          <div className="rounded-lg bg-[#F7FAFF] p-3" data-testid="cc-result">
            <p className="text-[13px] font-black">{result.cc_number} — akurasi {result.accuracy_pct}%</p>
            <p className="text-[11.5px] text-[#6B6B73]">Ditemukan {result.found_count}/{result.expected_count} · hilang {result.missing_count} · asing/salah lokasi {result.extra_count}</p>
            {result.missing_items?.length > 0 && (
              <div className="mt-1.5 rounded bg-[#FBE9E7] p-2 text-[11px]" data-testid="cc-missing">
                <p className="font-bold text-[#C0341D]">Tidak terbaca (cek fisik!):</p>
                {result.missing_items.slice(0, 10).map((m) => <p key={m.epc}>· {m.roll_no} — {m.product_name} <span className="font-mono text-[9.5px]">{m.epc}</span></p>)}
                {result.missing_items.length > 10 && <p>+{result.missing_items.length - 10} lagi…</p>}
              </div>
            )}
            {result.extra_items?.length > 0 && (
              <div className="mt-1.5 rounded bg-[#FFF4E5] p-2 text-[11px]" data-testid="cc-extra">
                <p className="font-bold text-[#8C4A00]">Terbaca tapi bukan milik gudang ini:</p>
                {result.extra_items.slice(0, 10).map((m) => <p key={m.epc}>· {m.roll_no || m.epc} — {m.note}</p>)}
              </div>
            )}
            <p className="mt-1.5 text-[10.5px] text-[#8E8E93]">Laporan saja — stok TIDAK diubah otomatis (Roll-as-SSOT). Tindak lanjuti selisih via inspeksi/insiden.</p>
          </div>
        )}
      </SectionCard>

      <SectionCard title={`Riwayat Cycle Count (${history.length})`}>
        {history.length === 0 ? <EmptyBox icon={ClipboardCheck} text="Belum ada cycle count." /> : (
          <div className="space-y-1" data-testid="cc-history">
            {history.map((c) => (
              <div key={c.id} className="flex items-center gap-2 rounded bg-[#FAFAFB] px-2 py-1.5 text-[11.5px]">
                <span className="font-bold">{c.cc_number}</span>
                <span className="text-[#6B6B73]">{c.warehouse_name} · {fmtTime(c.created_at)} · {c.created_by}</span>
                <span className="ml-auto" />
                <Pill color={c.accuracy_pct >= 100 ? "green" : c.accuracy_pct >= 95 ? "orange" : "red"}>
                  {c.accuracy_pct}% · hilang {c.missing_count}</Pill>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
