/**
 * LoadingCheckPanel (FASE R4) — Final Loading Check: sweep handheld vs manifest SO
 * sebelum barang naik mobil. Hasil tidak bersih = dispatch DIBLOKIR backend.
 */
import { useEffect, useState } from "react";
import { ScanLine, Zap, CheckCircle, AlertTriangle } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { apiErrorText } from "../../utils/apiError";

export const LoadingCheckPanel = ({ orderId, soNumber }) => {
  const [session, setSession] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [epcInput, setEpcInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadStatus = async () => {
    try {
      const r = await axios.get(`${API}/outbound/so/${orderId}/loading-check`);
      setSession(r.data.open_session);
      setLastResult(r.data.last_result);
    } catch { /* noop */ }
  };
  useEffect(() => { if (orderId) loadStatus(); }, [orderId]); // eslint-disable-line

  const run = async (fn) => {
    setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(apiErrorText(e, "Gagal")); } finally { setBusy(false); }
  };
  const start = () => run(async () => {
    const r = await axios.post(`${API}/outbound/so/${orderId}/loading-check/start`);
    setSession(r.data);
  });
  const scan = (epcs) => run(async () => {
    const r = await axios.post(`${API}/outbound/loading-check/${session.id}/scan`, { epcs });
    setSession(r.data); setEpcInput("");
  });
  const complete = () => run(async () => {
    await axios.post(`${API}/outbound/loading-check/${session.id}/complete`);
    setSession(null); setLastResult(null); await loadStatus();
  });

  if (!orderId) return null;
  return (
    <div data-testid="loading-check-panel" className="rounded-lg border border-[#D9D2F0] bg-[#F7F5FF] p-2.5 space-y-2">
      <p className="flex items-center gap-1.5 text-[11.5px] font-bold text-[#4B3B9E]">
        <ScanLine size={13} /> Pemeriksaan Muat Akhir (handheld vs SO {soNumber || ""})
      </p>
      {error && <p data-testid="lc-error" className="rounded bg-[#FBE9E7] px-2 py-1 text-[11px] font-semibold text-[#C0341D]">{error}</p>}

      {lastResult && !session && (
        <div data-testid="lc-last-result" className={`flex items-center gap-1.5 rounded px-2 py-1.5 text-[11px] font-semibold ${
          lastResult.result === "clean" ? "bg-[#E6F6EC] text-[#1B7F4B]" : "bg-[#FBE9E7] text-[#C0341D]"}`}>
          {lastResult.result === "clean" ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
          {lastResult.result === "clean"
            ? `BERSIH — ${lastResult.matched}/${lastResult.expected} cocok. Dispatch dibuka.`
            : `ADA SELISIH (missing ${lastResult.missing?.length || 0}, extra ${lastResult.extra?.length || 0}) — dispatch DIBLOKIR, ulangi check.`}
        </div>
      )}

      {!session ? (
        <button data-testid="lc-start" disabled={busy} onClick={start}
          className="rounded-lg bg-[#4B3B9E] px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40">
          {lastResult ? "Ulangi Loading Check" : "Mulai Loading Check"}
        </button>
      ) : (
        <div className="space-y-1.5">
          <p className="text-[11px] text-[#6B6B73]" data-testid="lc-progress">
            Cocok {session.matched_count ?? 0}/{session.expected_count ?? session.expected?.length} EPC
            {session.untagged_count > 0 && <span className="text-[#B23B14]"> · {session.untagged_count} roll tanpa tag tidak ikut check</span>}
            {session.not_committed_count > 0 && <span className="block font-semibold text-[#B23B14]" data-testid="lc-not-committed-warn">⚠ {session.not_committed_count} roll masih reserved (belum commit) — check bisa bersih tapi dispatch akan tertahan sampai roll di-commit</span>}
          </p>
          <textarea data-testid="lc-input" className="h-12 w-full rounded border border-[#D9D2F0] px-2 py-1 font-mono text-[10.5px]"
            placeholder="Tempel EPC hasil sweep handheld…" value={epcInput} onChange={(e) => setEpcInput(e.target.value)} />
          <div className="flex flex-wrap gap-1.5">
            <button data-testid="lc-scan" disabled={busy || !epcInput.trim()}
              onClick={() => scan(epcInput.split(/[\s,;]+/).filter(Boolean))}
              className="rounded bg-[#4B3B9E] px-2.5 py-1 text-[10.5px] font-semibold text-white disabled:opacity-40">Kirim Scan</button>
            <button data-testid="lc-simulate" disabled={busy}
              onClick={() => scan((session.expected || []).map((e) => e.epc))}
              className="flex items-center gap-1 rounded border border-[#4B3B9E] px-2.5 py-1 text-[10.5px] font-semibold text-[#4B3B9E] disabled:opacity-40">
              <Zap size={11} /> Simulasi Semua</button>
            <button data-testid="lc-complete" disabled={busy} onClick={complete}
              className="ml-auto rounded bg-[#1B7F4B] px-2.5 py-1 text-[10.5px] font-semibold text-white disabled:opacity-40">Selesaikan</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoadingCheckPanel;
