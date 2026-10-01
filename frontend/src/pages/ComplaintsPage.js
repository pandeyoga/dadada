import React, { useCallback, useEffect, useState } from "react";
import { Headset, Plus } from "lucide-react";

import KpiCard from "@/components/patterns/KpiCard";
import ComplaintsListTab from "@/components/complaints/ComplaintsListTab";
import ManualComplaintDialog from "@/components/complaints/ManualComplaintDialog";
import { Button } from "@/components/ui/button";
import { LoadingKpis, ErrorState } from "@/components/patterns/StateViews";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { CHUB, COMPLAINTS } from "@/constants/testIds";

/**
 * ComplaintsPage (`/complaints`) — Komplain & Layanan Pelanggan.
 *
 * Fase 40d: kartu angka di atas BUKAN hiasan lagi — masing-masing menaut ke daftar yang
 * sudah terfilter persis seperti cara angkanya dihitung (blueprint §7.3: “KPI tanpa
 * drill-down dianggap belum selesai”). Daftarnya sendiri kini tabel pro.
 */
export default function ComplaintsPage() {
  const { can } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [manualOpen, setManualOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadStats = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const res = await api.get("/complaints/stats");
      setStats(res.data.data);
    } catch (e) {
      // Ringkasan gagal dimuat TIDAK boleh disembunyikan: pemakai harus tahu angka di atas
      // tidak bisa dipercaya saat ini (daftar di bawah tetap punya penanganan galatnya
      // sendiri, jadi layar tidak perlu kosong seluruhnya).
      setError(e?.response?.data?.detail || "Gagal memuat ringkasan komplain.");
      setStats(null);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const KPIS = [
    { label: "Total komplain", value: stats?.total, tone: "primary", to: "/complaints" },
    { label: "Terbuka", value: stats?.open, tone: "amber", to: "/complaints?status=open" },
    { label: "Dikerjakan", value: stats?.in_progress, tone: "sky",
      to: "/complaints?status=in_progress" },
    { label: "Selesai", value: stats?.resolved, tone: "emerald",
      to: "/complaints?status=resolved" },
    { label: "Lewat SLA", value: stats?.breached, tone: "rose", to: "/complaints?sla=breached",
      hint: stats?.avg_resolution_hours
        ? `Rata-rata tuntas ${stats.avg_resolution_hours} jam` : undefined },
  ];

  return (
    <div data-testid={COMPLAINTS.page} className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Headset className="h-5 w-5 text-primary" />
          <div>
            <h1 className="page-title">
              Komplain &amp; Layanan Pelanggan
            </h1>
            <p className="page-desc">
              Klik angka untuk membuka daftar yang sudah terfilter. Komplain dari portal pembeli
              maupun yang dicatat manual (WA/telepon/datang langsung) ada di sini.
            </p>
          </div>
        </div>
        {can("complaints", "create") ? (
          <Button data-testid={CHUB.mcOpenBtn} onClick={() => setManualOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> Catat komplain manual
          </Button>
        ) : null}
      </div>
      <ManualComplaintDialog open={manualOpen} onOpenChange={setManualOpen}
        onDone={() => { setManualOpen(false); loadStats(); setRefreshKey((k) => k + 1); }} />

      {loading && !stats ? <LoadingKpis /> : null}
      {error ? <ErrorState message={error} onRetry={loadStats} /> : null}
      {stats ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {KPIS.map((k) => (
            <KpiCard key={k.label} label={k.label} value={k.value ?? 0} tone={k.tone}
              hint={k.hint} to={k.to} testId={COMPLAINTS.metric} drillLabel="Lihat daftar" />
          ))}
        </div>
      ) : null}

      <ComplaintsListTab key={refreshKey} onChanged={loadStats} />
    </div>
  );
}
