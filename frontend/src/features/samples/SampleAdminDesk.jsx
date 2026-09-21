/**
 * SampleAdminDesk — REVISI SAMPEL: MEJA ADMIN SAMPEL (POV tim sampel).
 * Antrean per tahap: ACC pembayaran (berbayar) → teruskan ke gudang → dipotong → dikirim/diambil → selesai.
 * Satu tindakan per baris; pantau membuka daftar Pesanan Sampel dengan baris terpilih.
 */
import { useCallback, useEffect, useState } from "react";
import { Scissors, RefreshCw, Inbox, Layers, ShieldAlert } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import { apiErrorText } from "../../utils/apiError";
import DeskQueueCard from "../sales_admin/DeskQueueCard";
import { sampleDesk, approveSamplePayment, confirmSampleOrder } from "./sampleApi";

export default function SampleAdminDesk({ currentUser, selectedEntity = "all", onOpenDocument }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyRef, setBusyRef] = useState("");
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedEntity && selectedEntity !== "all") params.entity_id = selectedEntity;
      setData(await sampleDesk(params)); setError("");
    } catch (e) { setError(apiErrorText(e, "Gagal memuat Meja Admin Sampel.")); }
    finally { setLoading(false); }
  }, [selectedEntity]);
  useEffect(() => { load(); }, [load]);

  const flash = (m) => { setToast(m); setTimeout(() => setToast(""), 5000); };

  async function handleAction(row) {
    if (row.action_kind === "approve_payment" || row.action_kind === "confirm") {
      setBusyRef(row.ref_id); setError("");
      try {
        if (row.action_kind === "approve_payment") { await approveSamplePayment(row.ref_id); flash(`${row.number}: pembayaran sampel disetujui — kini siap diteruskan ke gudang.`); }
        else { const r = await confirmSampleOrder(row.ref_id); flash(`${row.number} diteruskan ke gudang — ${r?.tasks_created ?? ""} tugas potong lahir.`); }
        await load();
      } catch (e) { setError(apiErrorText(e, "Aksi gagal.")); }
      finally { setBusyRef(""); }
      return;
    }
    onOpenDocument?.({ view: "sample-orders", nav_id: "sample-orders", focus_type: "sample_order", focus_id: row.ref_id, number: row.number });
  }

  const queues = Array.isArray(data?.queues) ? data.queues : [];
  const openItems = queues.filter((q) => ["bayar_sampel", "siap_gudang"].includes(q.id)).reduce((s, q) => s + (q.count || 0), 0);
  const oldest = Math.max(0, ...queues.map((q) => q.oldest_age_days || 0));

  return (
    <div data-testid="sample-desk" className="grid gap-4">
      <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")} testId="sample-desk-error" />
      {toast && <div data-testid="sample-desk-toast" className="rounded-md border border-[#A7D8B0] bg-[#EAF7EE] px-3 py-2 text-[12px] text-[#126E2C]">{toast}</div>}
      <section className="section-card">
        <div className="section-head">
          <div className="flex min-w-0 items-center gap-2">
            <Scissors size={15} className="text-[#9A5B00]" />
            <span className="kicker">Admin Sampel</span>
            <h2 data-testid="sample-desk-title">{data?.title || "Meja Admin Sampel"}</h2>
          </div>
          <button data-testid="sample-desk-refresh" className="icon-button" onClick={load} aria-label="Muat ulang meja"><RefreshCw size={14} className={loading ? "animate-spin" : ""} /></button>
        </div>
        <p className="px-3 pt-2 text-[11.5px] leading-relaxed text-[#6B6B73]">Pesanan sampel dari sales (SOS-): <b>sampel berbayar</b> disetujui pembayarannya dulu (Finance/Admin Sampel), <b>sampel gratis</b> langsung siap. Lalu <b>teruskan ke gudang</b> → gudang memotong dari roll (pindai RFID, catat panjang aktual) → dikirim / diambil pelanggan.</p>
        <section data-testid="sample-desk-metrics" className="grid gap-3 p-3 sm:grid-cols-3">
          <Metric icon={Inbox} label="Perlu Tindakan Saya" value={openItems} tone="rgba(255,149,0,.16)" testId="sample-desk-metric-open" />
          <Metric icon={Layers} label="Antrean Aktif" value={queues.filter((q) => q.count > 0).length} tone="rgba(154,91,0,.14)" testId="sample-desk-metric-queues" />
          <Metric icon={ShieldAlert} label="Umur Tertua" value={oldest > 0 ? `${oldest} hari` : "hari ini"} tone="rgba(255,59,48,.14)" testId="sample-desk-metric-oldest" />
        </section>
        {(data?.not_my_desk || []).length > 0 && (
          <div data-testid="sample-desk-not-mine" className="mx-3 mb-3 rounded-lg border border-[#F3D9A4] bg-[#FFF9EC] px-3 py-2">
            <p className="text-[10.5px] font-bold uppercase tracking-wide text-[#9A5B00]">Bukan wewenang meja ini</p>
            <p className="text-[11.5px] text-[#5C4A1E]">{data.not_my_desk.join(" · ")}</p>
          </div>
        )}
      </section>
      {loading && !data ? <div className="section-card py-14 text-center text-[12px] text-[#6B6B73]" data-testid="sample-desk-loading">Menyusun antrean…</div>
        : (
          <div className="grid gap-3 xl:grid-cols-2">
            {queues.map((q) => <DeskQueueCard key={q.id} queue={q} loading={loading} busyRef={busyRef} testPrefix="sample-desk" onAction={handleAction} />)}
          </div>
        )}
    </div>
  );
}

function Metric({ icon: Icon, label, value, tone, testId }) {
  return (
    <div data-testid={testId} className="metric-card">
      <div className="metric-icon" style={{ background: tone }}><Icon size={16} className="text-[#1C1C1E]" /></div>
      <div className="min-w-0"><p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{label}</p><p className="text-[15px] font-bold tabular-nums">{value}</p></div>
    </div>
  );
}
