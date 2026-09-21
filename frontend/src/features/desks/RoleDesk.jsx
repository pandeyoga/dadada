/**
 * RoleDesk — Sesi #087 · MEJA MD & MEJA ADMIN GUDANG (pola Meja Finance/Admin Sales).
 * Satu komponen untuk dua meja: konfigurasi per `desk` (judul, ikon, pemuat, teks lingkup).
 * Baris antrean melompat ke layar penanganannya lewat `onOpenDocument` (navigasi + auto-buka);
 * aksi `create_delivery` (Admin Gudang) membuka Logistik dengan SJ terpilih — jembatan WMS→Logistik.
 */
import { useCallback, useEffect, useState } from "react";
import { Inbox, Palette, RefreshCw, ShieldAlert, Warehouse, Layers, BellRing } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import { apiErrorText } from "../../utils/apiError";
import DeskQueueCard from "../sales_admin/DeskQueueCard";
import { mdDesk, warehouseAdminDesk, myDesk, rowLink } from "../sales_admin/workDeskApi";
import { openLogistics } from "../logistics/logisticsDeepLink";

const DESKS = {
  md: {
    icon: Palette, kicker: "MD / Merchandiser", title: "Meja MD", load: mdDesk, testPrefix: "md-desk",
    intro: <>Pengembangan produk dari satu meja: <b>permintaan desain</b> (setujui · tugaskan · putuskan), <b>sample &amp; labdip</b> per putaran, <b>PR bahan</b>, dan SPK inspeksi yang belum punya acuan sample.</>,
  },
  warehouse_admin: {
    icon: Warehouse, kicker: "Admin Gudang", title: "Meja Admin Gudang", load: warehouseAdminDesk, testPrefix: "wh-desk",
    intro: <>Memimpin operasi gudang: <b>SJ yang sudah diberangkatkan tetapi belum diangkut logistik</b>, tugas outbound, PO menunggu penerimaan, SPK belum ditugaskan, persetujuan opname/transfer, dan pengiriman gagal/belum ditutup.</>,
  },
  // U-2 (2026-09) — satu meja untuk 6 peran tersisa; judul diambil dari server sesuai peran.
  me: {
    icon: BellRing, kicker: "Kerja saya", title: "Meja Saya", load: myDesk, testPrefix: "my-desk",
    intro: <>Semua yang menunggu tindakan Anda hari ini: <b>Giliran saya</b> (dokumen yang baru berpindah tahap ke Anda) dan antrean khas peran Anda. Buka baris untuk melompat ke layar penanganannya.</>,
  },
};

export default function RoleDesk({ desk = "md", selectedEntity = "all", onOpenDocument }) {
  const cfg = DESKS[desk] || DESKS.md;
  const Icon = cfg.icon;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedEntity && selectedEntity !== "all") params.entity_id = selectedEntity;
      setData(await cfg.load(params)); setError("");
    } catch (e) { setError(apiErrorText(e, `Gagal memuat ${cfg.title}.`)); }
    finally { setLoading(false); }
  }, [selectedEntity, cfg]);

  useEffect(() => { load(); }, [load]);

  function handleAction(row, queue) {
    if (row.action_kind === "create_delivery") {
      // Jembatan Gudang → Logistik: buka Logistik dengan SJ ini terpilih untuk dibuat pengiriman.
      openLogistics({ createFromShipmentId: row.ref_id });
      onOpenDocument?.({ view: "logistics", nav_id: "logistics" });
      return;
    }
    if (row.ref_type === "logistics_delivery") {
      openLogistics({ deliveryId: row.ref_id });
      onOpenDocument?.({ view: "logistics", nav_id: "logistics" });
      return;
    }
    if (row.ref_type === "shipment") {
      openLogistics({ search: row.number || "" });
      onOpenDocument?.({ view: "logistics", nav_id: "logistics" });
      return;
    }
    if (queue?.id === "giliran_saya" && row.extra?.link) {
      onOpenDocument?.({ view: row.extra.link, nav_id: row.extra.link, focus_id: row.ref_id, focus_type: row.ref_type });
      return;
    }
    onOpenDocument?.(rowLink(row, queue?.id, desk));
  }

  const queues = Array.isArray(data?.queues) ? data.queues : [];
  const openItems = queues.reduce((s, q) => s + (q.count || 0), 0);
  const oldest = Math.max(0, ...queues.map((q) => q.oldest_age_days || 0));
  const p = cfg.testPrefix;

  return (
    <div data-testid={`${p}`} className="grid gap-4">
      <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")} testId={`${p}-error`} />
      <section className="section-card">
        <div className="section-head">
          <div className="flex min-w-0 items-center gap-2">
            <Icon size={15} className="text-[#0058CC]" />
            <span className="kicker">{cfg.kicker}</span>
            <h2 data-testid={`${p}-title`}>{data?.title || cfg.title}</h2>
          </div>
          <button data-testid={`${p}-refresh`} className="icon-button" onClick={load} aria-label="Muat ulang meja">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
        <p className="px-3 pt-2 text-[11.5px] leading-relaxed text-[#6B6B73]">{cfg.intro}</p>
        <section data-testid={`${p}-metrics`} className="grid gap-3 p-3 sm:grid-cols-3">
          <Metric icon={Inbox} label="Perlu Ditindak" value={openItems} tone="rgba(255,149,0,.16)" testId={`${p}-metric-open`} />
          <Metric icon={Layers} label="Antrean" value={queues.filter((q) => q.count > 0).length} tone="rgba(0,88,204,.14)" testId={`${p}-metric-queues`} />
          <Metric icon={ShieldAlert} label="Umur Tertua" value={oldest > 0 ? `${oldest} hari` : "hari ini"} tone="rgba(255,59,48,.14)" testId={`${p}-metric-oldest`} />
        </section>
        {(data?.not_my_desk || []).length > 0 && (
          <div data-testid={`${p}-not-mine`} className="mx-3 mb-3 rounded-lg border border-[#CBDFFF] bg-[#F2F7FF] px-3 py-2">
            <p className="text-[10.5px] font-bold uppercase tracking-wide text-[#0058CC]">Bukan wewenang meja ini</p>
            <p className="text-[11.5px] text-[#31465F]">{data.not_my_desk.join(" · ")}</p>
          </div>
        )}
      </section>

      {loading && !data ? (
        <div className="section-card py-14 text-center text-[12px] text-[#6B6B73]" data-testid={`${p}-loading`}>Menyusun antrean…</div>
      ) : queues.length === 0 ? (
        <div className="section-card py-14 text-center text-[12px] text-[#6B6B73]" data-testid={`${p}-empty`}>
          <Inbox size={26} className="mx-auto mb-2 text-[#D6D6DB]" /> Belum ada antrean untuk badan usaha yang sedang Anda lihat.
        </div>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {queues.map((q) => (
            <DeskQueueCard key={q.id} queue={q} loading={loading} testPrefix={p} onAction={handleAction} />
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({ icon: Icon, label, value, tone, testId }) {
  return (
    <div data-testid={testId} className="metric-card">
      <div className="metric-icon" style={{ background: tone }}><Icon size={16} className="text-[#1C1C1E]" /></div>
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{label}</p>
        <p className="text-[15px] font-bold tabular-nums">{value}</p>
      </div>
    </div>
  );
}
