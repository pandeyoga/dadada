import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Building2, Camera, CheckCircle2, ChevronDown, ChevronUp, ExternalLink, Flag, Headset, KeyRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import StatusPill from "@/components/patterns/StatusPill";
import EmptyState from "@/components/patterns/EmptyState";
import MoneyText from "@/components/patterns/MoneyText";
import { LoadingCards, ErrorState } from "@/components/patterns/StateViews";
import ManualComplaintDialog from "@/components/complaints/ManualComplaintDialog";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { formatDateTimeWIB, formatDateWIB } from "@/utils/formatters";
import { photoSrc } from "@/utils/photoSrc";
import { CHUB } from "@/constants/testIds";

/**
 * CustomerUnitsTab — unit milik pelanggan + KONSTRUKSI nyata: progres per tahapan,
 * milestone (hold point / gerbang serah terima), bukti foto terakhir, status serah terima,
 * dan tautan ke modul Pembangunan. Dirangkai server (`/customers/{id}/units-construction`).
 */
export function CustomerUnitsTab({ customerId }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const res = await api.get(`/customers/${customerId}/units-construction`);
      setRows(res.data.data || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Gagal memuat unit & konstruksi.");
    } finally { setLoading(false); }
  }, [customerId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <LoadingCards count={1} />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!rows.length) {
    return (
      <div data-testid={CHUB.ucEmpty}>
        <EmptyState icon={Building2} title="Belum ada unit tertaut"
          description="Unit menempel pada pelanggan setelah reservasi/booking dikonversi menjadi pembeli." />
      </div>
    );
  }
  return (
    <div data-testid={CHUB.ucTab} className="space-y-4">
      {rows.map((r) => <UnitCard key={r.unit.id} row={r} />)}
    </div>
  );
}

const STAGE_TONE = {
  done: "text-emerald-700", submitted: "text-sky-700", in_progress: "text-amber-700",
  ready: "text-slate-700", rework: "text-rose-700", blocked: "text-muted-foreground",
};
const STAGE_LABEL = {
  done: "selesai", submitted: "menunggu verifikasi", in_progress: "dikerjakan",
  ready: "siap mulai", rework: "perbaikan", blocked: "menunggu tahap sebelumnya",
};

function UnitCard({ row }) {
  const { unit, schedule, items, items_done, items_total, milestones, photos, handover, contract, links } = row;
  const [showAll, setShowAll] = useState(false);
  const progress = schedule ? Number(schedule.progress || 0) : Number(unit.construction_progress || 0);
  const current = items.find((i) => ["in_progress", "submitted", "rework", "ready"].includes(i.status));
  const visible = showAll ? items : items.filter((i) => i.status !== "blocked").slice(-6);

  return (
    <div data-testid={CHUB.ucUnitCard} data-unit={unit.code}
      className="space-y-4 rounded-xl border bg-card p-4 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
            <Link data-testid={CHUB.ucOpenUnit} className="text-primary hover:underline" to={links.unit}>{unit.code}</Link>
            <span className="text-muted-foreground">· {unit.type}</span>
            <StatusPill status={unit.status} group="unit_status" />
            {contract ? <StatusPill status={contract.legal_stage} group="contract_legal_stage" /> : null}
          </p>
          <p className="text-xs text-muted-foreground">
            {unit.project_name || "-"} · blok {unit.block || "-"}
            {unit.land_area ? ` · LT ${unit.land_area} m²` : ""}{unit.building_area ? ` · LB ${unit.building_area} m²` : ""}
          </p>
        </div>
        <div className="flex items-center gap-4 text-right">
          <div><p className="text-xs text-muted-foreground">Harga</p><MoneyText value={unit.price} className="text-sm" /></div>
          <Link data-testid={CHUB.ucOpenBuild} to={links.build}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
            Modul Pembangunan <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      </div>

      {/* progres */}
      <div data-testid={CHUB.ucProgress} className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium">
            Progres pembangunan {progress}%{unit.construction_label ? ` · ${unit.construction_label}` : ""}
          </span>
          <span className="text-muted-foreground">
            {schedule ? `rencana ${Math.round(schedule.planned_progress || 0)}% · deviasi ${schedule.deviation > 0 ? "+" : ""}${Math.round(schedule.deviation || 0)}% · ${items_done}/${items_total} tahap`
              : "belum ada jadwal pembangunan sistem"}
          </span>
        </div>
        <Progress value={progress} className="h-2" />
        {current ? (
          <p className="text-xs text-muted-foreground">
            Tahap berjalan: <b className="text-foreground">{current.name}</b> · {STAGE_LABEL[current.status]}
            {current.planned_finish ? ` · target ${formatDateWIB(current.planned_finish)}` : ""}
            {current.late_days ? <span className="text-rose-700"> · terlambat {current.late_days} hari</span> : null}
          </p>
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {/* tahapan */}
        <section className="space-y-1.5">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Tahapan pekerjaan</h4>
            {items.length > 6 ? (
              <Button data-testid={CHUB.ucToggleStages} size="sm" variant="ghost" className="h-7 text-xs"
                onClick={() => setShowAll((v) => !v)}>
                {showAll ? <><ChevronUp className="mr-1 h-3.5 w-3.5" /> Ringkas</> : <><ChevronDown className="mr-1 h-3.5 w-3.5" /> Semua ({items.length})</>}
              </Button>
            ) : null}
          </div>
          {items.length ? (
            <ul className="divide-y rounded-lg border">
              {visible.map((it) => (
                <li key={it.id} data-testid={CHUB.ucStageRow} data-status={it.status}
                  className="flex items-center justify-between gap-2 px-3 py-1.5 text-[13px]">
                  <div className="min-w-0">
                    <p className="truncate">
                      <span className="font-mono text-[11px] text-muted-foreground">{it.step_code}</span> {it.name}
                      {it.hold_point ? <Flag className="ml-1 inline h-3 w-3 text-amber-600" /> : null}
                      {it.handover_gate ? <KeyRound className="ml-1 inline h-3 w-3 text-sky-600" /> : null}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      M{it.week} · target {it.planned_finish ? formatDateWIB(it.planned_finish) : "-"}
                      {it.completed_at ? ` · selesai ${formatDateWIB(it.completed_at)}` : ""}
                      {it.evidence_count ? ` · ${it.evidence_count} foto` : ""}
                    </p>
                  </div>
                  <span className={`shrink-0 text-xs font-medium ${STAGE_TONE[it.status] || ""}`}>{STAGE_LABEL[it.status] || it.status}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
              Unit ini belum punya jadwal pembangunan. Bangkitkan dari template di Modul Pembangunan
              agar tahapan, bukti foto, dan pengingat bisa dipantau di sini.
            </p>
          )}
        </section>

        <div className="space-y-4">
          {/* milestone */}
          <section className="space-y-1.5">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Milestone</h4>
            {milestones.length ? (
              <ul className="space-y-1">
                {milestones.map((m) => (
                  <li key={m.code} data-testid={CHUB.ucMilestoneRow} className="flex items-center gap-2 text-xs">
                    {m.status === "done" ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                      : <Flag className="h-3.5 w-3.5 text-muted-foreground" />}
                    <span className="truncate">{m.name}</span>
                    <span className="ml-auto shrink-0 text-muted-foreground">
                      {m.status === "done" && m.completed_at ? formatDateWIB(m.completed_at)
                        : (m.planned_finish ? `target ${formatDateWIB(m.planned_finish)}` : "")}
                    </span>
                  </li>
                ))}
              </ul>
            ) : <p className="text-xs text-muted-foreground">Belum ada milestone (hold point / gerbang serah terima) pada jadwal.</p>}
          </section>

          {/* foto */}
          <section className="space-y-1.5">
            <h4 className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Camera className="h-3.5 w-3.5" /> Bukti foto terakhir
            </h4>
            {photos.length ? (
              <div className="grid grid-cols-4 gap-1.5">
                {photos.map((p) => (
                  <a key={p.file_id} data-testid={CHUB.ucPhoto} href={photoSrc(p)} target="_blank" rel="noreferrer"
                    title={`${p.step} · ${p.uploaded_at ? formatDateTimeWIB(p.uploaded_at) : ""}`}
                    className="block aspect-square overflow-hidden rounded-md border bg-secondary">
                    <img src={photoSrc(p, { variant: "thumb" })} alt={p.step}
                      className="h-full w-full object-cover" loading="lazy" />
                  </a>
                ))}
              </div>
            ) : <p className="text-xs text-muted-foreground">Belum ada foto bukti pekerjaan.</p>}
          </section>

          {/* serah terima */}
          <section data-testid={CHUB.ucHandover} className="rounded-lg border bg-background p-2.5">
            <p className="flex items-center gap-1.5 text-xs font-semibold"><KeyRound className="h-3.5 w-3.5" /> Serah terima (BAST)</p>
            {handover ? (
              <p className="mt-1 text-xs text-muted-foreground">
                <StatusPill status={handover.state} label={handover.state_label || handover.state} />
                {" "}<span className="font-mono">{handover.number}</span>
                {handover.handed_over_at ? ` · ${formatDateWIB(handover.handed_over_at)}` : ""}
                {handover.received_by ? ` · diterima ${handover.received_by}` : ""}
                {handover.keys_handed != null ? ` · kunci ${handover.keys_handed}` : ""}
              </p>
            ) : (
              <p className="mt-1 text-xs text-muted-foreground">
                Belum serah terima{unit.construction_status === "ready_handover" ? " — unit sudah SIAP diserahkan" : ""}.
              </p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

/** CustomerComplaintsTab — komplain pelanggan (portal & manual) + tombol catat manual. */
export function CustomerComplaintsTab({ customer, complaints = [], onChanged }) {
  const { can } = useAuth();
  const [open, setOpen] = useState(false);
  const action = can("complaints", "create") ? (
    <Button data-testid={CHUB.mcOpenBtn} size="sm" onClick={() => setOpen(true)}>
      <Headset className="mr-1.5 h-4 w-4" /> Catat komplain
    </Button>
  ) : null;
  const dialog = (
    <ManualComplaintDialog open={open} onOpenChange={setOpen} customer={customer}
      onDone={() => { setOpen(false); onChanged?.(); }} />
  );
  if (!complaints.length) {
    return (
      <div className="space-y-3">
        <div className="flex justify-end">{action}</div>
        <EmptyState icon={Headset} title="Tidak ada komplain"
          description="Komplain dari portal pembeli maupun yang dicatat manual oleh tim (WA/telepon/datang langsung) tampil di sini beserta status SLA-nya." />
        {dialog}
      </div>
    );
  }
  return (
    <div className="space-y-2">
      <div className="flex justify-end">{action}</div>
      {complaints.map((c) => (
        <div key={c.id} data-testid="customer-complaint-row" data-complaint={c.id}
          aria-label={`Komplain ${c.subject}`} className="rounded-lg border bg-card p-3 shadow-[var(--shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium">{c.subject}</p>
            <div className="flex items-center gap-2">
              {c.source === "manual" ? <StatusPill status="info" label={`manual · ${c.channel || "-"}`} /> : <StatusPill status="info" label="portal" />}
              {c.sla_breached ? <StatusPill status="overdue" label="SLA terlewat" /> : null}
              <StatusPill status={c.status} group="complaint_status" />
            </div>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {c.unit_code || "-"} · dibuat {formatDateTimeWIB(c.created_at)}
            {c.assigned_to ? ` · PIC ${c.assigned_to}` : ""}
          </p>
        </div>
      ))}
      {dialog}
    </div>
  );
}
