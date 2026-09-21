/**
 * DesignRequestDetailPanel — isi pop-up rincian **Permintaan Desain**.
 *
 * Tata letak dua kolom: kiri = brief, desain Studio yang tertaut (pintu kerja desainer),
 * riwayat; kanan = fakta + tindakan. Keputusan ACC/revisi untuk permintaan yang sudah
 * tertaut desain dilakukan DI HALAMAN DESAIN (dengan nilai 0–2) — status di sini mengikuti.
 */
import { useState } from "react";
import {
  Ban, CalendarClock, CheckCircle2, ClipboardList, ExternalLink, Play, RotateCcw, Save, User,
} from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import { designRequestRounds, RevisionBadge, RoundBoxes } from "../../components/RevisionProgress";
import KNSelect from "../../components/KNSelect";
import KNDatePicker, { formatDateId } from "../../components/KNDatePicker";
import { ColorChip } from "../../components/PantoneFinder";
import { askReason } from "../../services/confirmService";
import { notifySuccess } from "../../utils/feedback";
import { openRnd } from "../rnd/rndDeepLink";
import LinkedDesignsPanel from "./LinkedDesignsPanel";
import ReferenceGallery from "./ReferenceGallery";
import {
  apiText, approveDesignRequest, assignDesignRequest, cancelDesignRequest, deleteReference, DSR_STATUS_CLASS,
  DSR_STATUS_LABEL, DSR_STEPS, getDesignRequest, rejectDesignRequest, startDesignRequest,
  submitDesignRequest, updateDesignRequest, uploadReference,
} from "./designRequestsApi";
import { roleIs } from "../../config/roles";

function Row({ label, children, testId }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-[#F2F2F5] py-1.5 last:border-0">
      <span className="text-[11px] text-[#6B6B73]">{label}</span>
      <span data-testid={testId} className="text-right text-[11.5px] font-semibold text-[#1C1C1E]">{children}</span>
    </div>
  );
}

function Stepper({ status }) {
  const idx = status === "revision" ? 2 : DSR_STEPS.findIndex((s) => s.key === status);
  const cur = status === "draft" ? -1 : idx;
  return (
    <ol className="flex flex-wrap items-center gap-1" data-testid="dsr-stepper">
      {DSR_STEPS.map((s, i) => {
        const state = status === "cancelled" ? "todo" : status === "revision" && i === 2 ? "warn" : i < cur ? "done" : i === cur ? "cur" : "todo";
        const cls = { done: "bg-[#1A7A3A] text-white", cur: "bg-[#6B219A] text-white", warn: "bg-[#C62828] text-white", todo: "bg-[#F2F2F5] text-[#8E8E93]" }[state];
        return (
          <li key={s.key} className="flex items-center gap-1" data-testid={`dsr-step-${s.key}`}>
            <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[10.5px] font-semibold ${cls}`}>
              {i + 1}. {state === "warn" ? "Revisi" : s.label}
            </span>
            {i < DSR_STEPS.length - 1 && <span className="h-px w-3 bg-[#D9D9DE]" />}
          </li>
        );
      })}
      {status === "cancelled" && <li className="rounded-full bg-[#6B6B73] px-2.5 py-1 text-[10.5px] font-semibold text-white">Dibatalkan</li>}
    </ol>
  );
}

export default function DesignRequestDetailPanel({ doc, meta, onChanged, onClose }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [assignee, setAssignee] = useState(doc.assigned_to || "");
  const [due, setDue] = useState(doc.due_date || "");
  const [cat, setCat] = useState(doc.category_code || "");
  const [dcat, setDcat] = useState(doc.design_category_code || "");

  const role = meta?.role || "";
  const canDecide = roleIs(role, ["admin", "manager"]);
  const canAssign = canDecide;
  const canWork = roleIs(role, ["admin", "manager", "designer"]);
  const canRefs = roleIs(role, ["admin", "manager", "sales_admin", "md"]) && !["approved", "cancelled"].includes(doc.status);
  const rounds = designRequestRounds(doc);
  const designs = doc.designs || [];
  const hasCats = !!doc.category_code && !!doc.design_category_code;
  const active = !["approved", "cancelled"].includes(doc.status);
  const patternOpts = (meta?.categories?.pattern || []).map((c) => ({ value: c.code, label: `${c.code} — ${c.name}` }));
  const designOpts = (meta?.categories?.design || []).map((c) => ({ value: c.code, label: `${c.code} — ${c.name}` }));

  async function run(fn, pesan) {
    setBusy(true); setErr("");
    try {
      await fn();
      notifySuccess("Berhasil", pesan);
      onChanged?.(await getDesignRequest(doc.id));
    } catch (e) {
      setErr(apiText(e, "Aksi gagal."));
    } finally { setBusy(false); }
  }

  async function mintaRevisi() {
    const alasan = await askReason({ title: "Minta revisi", message: `Apa yang harus diubah pada ${doc.number}? Alasan ini dibaca desainer.`, confirmLabel: "Kirim permintaan revisi" });
    if (!alasan) return;
    await run(() => rejectDesignRequest(doc.id, alasan), "Permintaan revisi terkirim.");
  }
  async function batalkan() {
    const alasan = await askReason({ title: "Batalkan permintaan desain", message: `Sebutkan alasan pembatalan ${doc.number}.`, confirmLabel: "Batalkan permintaan" });
    if (!alasan) return;
    await run(() => cancelDesignRequest(doc.id, alasan), "Permintaan dibatalkan.");
  }

  return (
    <div data-testid="dsr-detail-panel" className="grid gap-3">
      {/* ── Kepala ── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="kicker">Permintaan Desain</p>
          <p data-testid="dsr-detail-number" className="text-[16px] font-bold text-[#1C1C1E]">{doc.number}</p>
          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-[#6B6B73]">
            {hasCats ? (
              <>
                <span className="rounded-full bg-[#F1E9F7] px-2 py-0.5 text-[10.5px] font-semibold text-[#6B219A]" data-testid="dsr-detail-category">{doc.category_name || doc.category_code}</span>
                <span className="rounded-full bg-[#EEF4FF] px-2 py-0.5 text-[10.5px] font-semibold text-[#0058CC]" data-testid="dsr-detail-dcategory">{doc.design_category_name || doc.design_category_code}</span>
              </>
            ) : <span className="rounded-full bg-[#FDF3F2] px-2 py-0.5 text-[10.5px] font-semibold text-[#A8221A]">kategori belum diisi</span>}
            <span>· {doc.source_label}</span>
            {doc.so_number && <span>· pesanan <b>{doc.so_number}</b></span>}
            {doc.customer_name && <span>· {doc.customer_name}</span>}
          </p>
        </div>
        <span className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
          <span data-testid="dsr-detail-status" className={`status-pill ${DSR_STATUS_CLASS[doc.status] || "pill-muted"}`}>
            {DSR_STATUS_LABEL[doc.status] || doc.status}
          </span>
          <RevisionBadge count={doc.revision_count} testId="dsr-detail-revision" />
        </span>
      </div>
      <Stepper status={doc.status} />

      {err && <ErrorNotice message={err} onDismiss={() => setErr("")} testId="dsr-detail-error" />}
      {doc.status === "revision" && doc.reject_reason && (
        <div className="rounded-lg bg-[#FDF3F2] px-3 py-2 text-[11.5px] text-[#C62828]" data-testid="dsr-detail-revision-note">
          <b>Catatan revisi:</b> {doc.reject_reason}
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_300px]">
        {/* ── Kiri ── */}
        <div className="grid gap-3">
          <div className="section-card">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Brief</p>
            <p data-testid="dsr-detail-brief" className="mt-1 whitespace-pre-wrap text-[12.5px] leading-relaxed text-[#1C1C1E]">{doc.brief}</p>
            {(doc.color_targets || []).length > 0 && (
              <div data-testid="dsr-detail-colors" className="mt-2 flex flex-wrap gap-1.5">
                {doc.color_targets.map((c) => (
                  <span key={c.code} className="inline-flex items-center gap-1 rounded-full border border-[#EFF0F2] px-2 py-0.5 text-[10.5px]">
                    <ColorChip hex={c.hex} size={12} /> {c.code} · {c.name}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-3 border-t border-[#F2F2F5] pt-2.5">
              <ReferenceGallery requestId={doc.id} files={doc.references || []} canEdit={canRefs} busy={busy}
                onPick={(list) => run(async () => { for (const f of list) await uploadReference(doc.id, f); },
                  `${list.length} gambar referensi ditambahkan${(doc.designs || []).length ? " — ikut ke desain tertaut." : "."}`)}
                onRemove={(f) => run(() => deleteReference(doc.id, f.id), "Gambar referensi dihapus.")} />
            </div>
          </div>

          <LinkedDesignsPanel doc={doc} canWork={canWork}
            onChanged={async (fresh, gotoDesignId) => {
              notifySuccess("Berhasil", gotoDesignId ? "Desain dibuat — membuka Design Studio." : "Desain ditautkan.");
              onChanged?.(fresh || await getDesignRequest(doc.id));
              if (gotoDesignId) openRnd({ view: "rnd-designs", designId: gotoDesignId });
            }}
            onError={(e) => setErr(apiText(e, "Aksi gagal."))} />

          <div className="section-card">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Riwayat</p>
            <div data-testid="dsr-detail-history" className="mt-1 grid gap-1">
              {(doc.history || []).slice().reverse().map((h, i) => (
                <div key={`${h.at}-${i}`} className="flex items-start gap-2 text-[11px]">
                  <CalendarClock size={12} className="mt-0.5 shrink-0 text-[#9A9BA3]" />
                  <span className="text-[#3C3C43]">
                    <strong>{h.label}</strong> · {h.actor} · {(h.at || "").slice(0, 16).replace("T", " ")}
                    {h.note ? <span className="text-[#6B6B73]"> — {h.note}</span> : null}
                  </span>
                </div>
              ))}
              {(doc.history || []).length === 0 && <p className="text-[11px] text-[#8E8E93]">Belum ada riwayat.</p>}
            </div>
          </div>
        </div>

        {/* ── Kanan ── */}
        <div className="grid content-start gap-3">
          <div className="section-card">
            <Row label="Diminta oleh" testId="dsr-detail-requester">{doc.requested_by || "—"}</Row>
            <Row label="Desainer" testId="dsr-detail-assignee">{doc.assigned_name || "Belum ditugaskan"}</Row>
            <Row label="Tenggat" testId="dsr-detail-due">
              <span className={doc.is_overdue ? "text-[#A8221A]" : ""}>{doc.due_date ? formatDateId(doc.due_date) : "—"}{doc.is_overdue ? " · lewat" : ""}</span>
            </Row>
            <Row label="Desain tertaut" testId="dsr-detail-versions">{designs.length || doc.versions || 0}</Row>
            <Row label="Putaran revisi" testId="dsr-detail-revisions">{doc.revision_count || 0}</Row>
            {rounds.length > 0 && (
              <div className="pt-1.5">
                <p className="mb-1 text-[10.5px] font-bold uppercase text-[#8E8E93]">Progres ronde</p>
                <RoundBoxes items={rounds} testPrefix="dsr-round" testId="dsr-rounds-progress" />
              </div>
            )}
            {doc.cancelled_reason && <Row label="Alasan pembatalan" testId="dsr-detail-cancel-reason">{doc.cancelled_reason}</Row>}
          </div>

          <div className="section-card grid gap-2">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Tindakan</p>

            {canDecide && doc.status === "delivered" && (
              doc.studio_linked ? (
                <div className="rounded-lg bg-[#F2F7FF] p-2.5 text-[11px] text-[#004099]" data-testid="dsr-decide-in-studio">
                  Desain sudah diajukan desainer. Beri <b>nilai (0–2)</b> lalu <b>ACC</b> atau <b>minta revisi</b> di halaman desain — status permintaan mengikuti otomatis.
                  <button type="button" data-testid="dsr-open-studio-button" className="primary-button mt-2 w-full"
                    onClick={() => openRnd({ view: "rnd-designs", designId: (designs.filter((x) => x.studio).pop() || designs[designs.length - 1]).id })}>
                    <ExternalLink size={13} /> Nilai & putuskan di Design Studio
                  </button>
                </div>
              ) : (
                <div className="grid gap-1.5">
                  <button data-testid="dsr-approve-button" className="primary-button" disabled={busy}
                    onClick={() => run(() => approveDesignRequest(doc.id, ""), "Desain disetujui.")}>
                    <CheckCircle2 size={13} /> Setujui (ACC)
                  </button>
                  <button data-testid="dsr-reject-button" className="secondary-button" disabled={busy} onClick={mintaRevisi}>
                    <RotateCcw size={13} /> Minta revisi
                  </button>
                </div>
              )
            )}

            {canAssign && active && (
              <div className="grid gap-1.5 rounded-lg bg-[#FAFBFC] p-2" data-testid="dsr-assign-box">
                <label className="block">
                  <span className="field-label">Tugaskan ke desainer</span>
                  <KNSelect data-testid="dsr-assign-select" value={assignee} onValueChange={setAssignee}
                    options={(meta?.designers || []).map((d) => ({ value: d.id, label: d.has_account ? d.name : `${d.name} (belum punya akun)` }))}
                    className="field" placeholder="Pilih desainer" searchable />
                </label>
                <label className="block">
                  <span className="field-label">Tenggat</span>
                  <KNDatePicker data-testid="dsr-assign-due" value={due} onChange={setDue} placeholder="Pilih tenggat" />
                </label>
                <button data-testid="dsr-assign-button" className="primary-button" disabled={busy || !assignee}
                  onClick={() => run(() => assignDesignRequest(doc.id, assignee, due), "Permintaan ditugaskan.")}>
                  <User size={13} /> {doc.assigned_to ? "Ubah penugasan" : "Tugaskan"}
                </button>
              </div>
            )}

            {canAssign && active && !hasCats && (
              <div className="grid gap-1.5 rounded-lg border border-[#F3D9D6] bg-[#FDF8F7] p-2" data-testid="dsr-category-box">
                <p className="text-[10.5px] text-[#A8221A]">Lengkapi kategori agar desainer bisa membuat desain dengan kode otomatis.</p>
                <KNSelect data-testid="dsr-edit-category" value={cat} onValueChange={setCat} options={patternOpts} className="field" placeholder="Kategori Pattern" searchable />
                <KNSelect data-testid="dsr-edit-dcategory" value={dcat} onValueChange={setDcat} options={designOpts} className="field" placeholder="Kategori Design" />
                <button data-testid="dsr-save-category" className="secondary-button" disabled={busy || !cat || !dcat}
                  onClick={() => run(() => updateDesignRequest(doc.id, { category_code: cat, design_category_code: dcat }), "Kategori disimpan.")}>
                  <Save size={13} /> Simpan kategori
                </button>
              </div>
            )}

            <div className="flex flex-wrap gap-1.5">
              {doc.status === "draft" && (
                <button data-testid="dsr-submit-button" className="secondary-button" disabled={busy}
                  onClick={() => run(() => submitDesignRequest(doc.id), "Permintaan diajukan.")}>
                  <ClipboardList size={13} /> Ajukan
                </button>
              )}
              {canWork && ["assigned", "revision"].includes(doc.status) && designs.length > 0 && (
                <button data-testid="dsr-start-button" className="secondary-button" disabled={busy}
                  onClick={() => run(() => startDesignRequest(doc.id), "Ditandai sedang dikerjakan.")}>
                  <Play size={13} /> Tandai dikerjakan
                </button>
              )}
              {canDecide && active && (
                <button data-testid="dsr-cancel-button" className="secondary-button" disabled={busy} onClick={batalkan}>
                  <Ban size={13} /> Batalkan
                </button>
              )}
              <button data-testid="dsr-detail-close" className="secondary-button" onClick={onClose}>Tutup</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
