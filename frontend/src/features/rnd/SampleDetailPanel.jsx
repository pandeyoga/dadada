/**
 * SampleDetailPanel — rincian **Permintaan Sample** bergaya studio (cermin panel Permintaan
 * Desain): kepala + stepper, kiri = brief · tab per jenis (Labdip / Handfeel / Proofing) ·
 * keputusan · bahan · riwayat; kanan = fakta + tindakan.
 *
 * Mekanisme server tidak berubah: kirim ke supplier → round ber-bukti → nilai → pilih
 * pemenang → sample jadi → kirim. Dirender di dalam `DetailModal framed` oleh pemanggil.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Ban, CalendarClock, CheckCircle2, GitBranch, History, PackageMinus, Send, Trophy } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import { RevisionBadge, sampleRevisionCount } from "../../components/RevisionProgress";
import { formatDateId } from "../../components/KNDatePicker";
import { formatCurrency, formatQty } from "../../utils/formatters";
import { askReason } from "../../services/confirmService";
import { notifySuccess } from "../../utils/feedback";
import { openTrace } from "../documents/trace/traceDeepLink";
import DecideModal from "./DecideModal";
import IssueMaterialModal from "./IssueMaterialModal";
import LabdipHistoryModal from "./LabdipHistoryModal";
import RoundActionModal from "./RoundActionModal";
import SampleFinishModal from "./SampleFinishModal";
import SampleMasterDataPanel from "./SampleMasterDataPanel";
import SampleSpecPanel from "./SampleSpecPanel";
import SampleSendModal from "./SampleSendModal";
import SampleTypeTabs from "./SampleTypeTabs";
import { TypeBadge } from "./SampleBoardCard";
import {
  assessRound, cancelSample, decideSample, deliverSample, finishSample, getSample,
  issueMaterial, openRound, patchSample, rndMeta, sendSample, submitRound, uploadRoundProof,
} from "./rndApi";
import { errMsg, SAMPLE_STATUS_META, SAMPLE_STEPS } from "./rndMeta";
import { deliverLabel, sampleTypesOf, typeLabel } from "./sampleTypeMeta";
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
  const cur = SAMPLE_STEPS.findIndex((s) => s.key === status);
  return (
    <ol className="flex flex-wrap items-center gap-1" data-testid="sample-stepper">
      {SAMPLE_STEPS.map((s, i) => {
        const state = status === "cancelled" ? "todo" : i < cur ? "done" : i === cur ? "cur" : "todo";
        const cls = { done: "bg-[#1A7A3A] text-white", cur: "bg-[#0058CC] text-white", todo: "bg-[#F2F2F5] text-[#8E8E93]" }[state];
        return (
          <li key={s.key} className="flex items-center gap-1" data-testid={`sample-step-${s.key}`}>
            <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[10.5px] font-semibold ${cls}`}>{i + 1}. {s.label}</span>
            {i < SAMPLE_STEPS.length - 1 && <span className="h-px w-3 bg-[#D9D9DE]" />}
          </li>
        );
      })}
      {status === "cancelled" && <li className="rounded-full bg-[#6B6B73] px-2.5 py-1 text-[10.5px] font-semibold text-white">Dibatalkan</li>}
    </ol>
  );
}

export default function SampleDetailPanel({ sampleId, currentUser, types: typesProp, onClose, onChanged, focusRoundId = "", initialType = "" }) {
  const [sample, setSample] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [policy, setPolicy] = useState({});
  const [reasons, setReasons] = useState([]);
  const [types, setTypes] = useState(typesProp || []);
  const [measurements, setMeasurements] = useState([]);
  const [deliverTargets, setDeliverTargets] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);

  const role = currentUser?.role;
  const canSubmit = roleIs(role, ["admin", "manager", "warehouse", "md"]);
  const canAssess = roleIs(role, ["admin", "manager", "md"]);
  const canDecide = roleIs(role, ["admin", "manager", "md"]);
  const canCancel = canDecide;
  const canEdit = roleIs(role, ["admin", "manager", "sales", "md"]);

  const load = useCallback(async () => {
    setLoading(true);
    try { setSample(await getSample(sampleId)); setErr(""); }
    catch (e) { setErr(errMsg(e, "Gagal memuat permintaan sample.")); }
    finally { setLoading(false); }
  }, [sampleId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    rndMeta().then((m) => {
      setPolicy(m?.policy || {}); setReasons(m?.reasons || []);
      setMeasurements(m?.measurements || []); setDeliverTargets(m?.deliver_targets || []);
      if ((m?.sample_types || []).length) setTypes(m.sample_types);
    }).catch(() => {});
  }, []);

  const act = async (fn, done) => {
    setBusy(true); setErr("");
    try {
      await fn(); await load(); onChanged?.(); setModal(null);
      if (done) notifySuccess("Berhasil", done);
    } catch (e) { setErr(errMsg(e, "Aksi gagal dijalankan.")); }
    finally { setBusy(false); }
  };
  const uploadProof = (round, file) => act(() => uploadRoundProof(sample.id, round.id, file), `Bukti "${file.name}" terunggah pada rnd ${round.round_no}.`);
  const batalkan = async () => {
    const alasan = await askReason({ title: "Batalkan permintaan sample", message: `Sebutkan alasan pembatalan ${sample.number}.`, confirmLabel: "Batalkan permintaan" });
    if (!alasan) return;
    await act(() => cancelSample(sample.id, alasan), "Permintaan sample dibatalkan.");
  };

  const meta = SAMPLE_STATUS_META[sample?.status] || SAMPLE_STATUS_META.draft;
  const decided = sample?.status === "decided";
  const cancelled = sample?.status === "cancelled";
  const active = !!sample && !decided && !cancelled;
  const canSend = !!sample && ["draft", "sent", "in_progress", "assessed"].includes(sample.status);
  const hasAcc = (sample?.rounds || []).some((r) => r.result === "acc");
  const issues = sample?.material_issues || [];
  const codes = useMemo(() => sampleTypesOf(sample), [sample]);

  if (!sample) {
    return (
      <div data-testid="sample-detail-panel" className="grid gap-2 p-2">
        {err ? <ErrorNotice message={err} onRetry={load} testId="sample-detail-error" />
          : [0, 1, 2].map((i) => <div key={i} className="h-9 animate-pulse rounded-md bg-[#F2F2F5]" />)}
      </div>
    );
  }

  return (
    <div data-testid="sample-detail-panel" className="grid gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="kicker">Permintaan Sample · R&amp;D</p>
          <p data-testid="sample-detail-number" className="text-[16px] font-bold text-[#1C1C1E]">{sample.number}</p>
          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-[#6B6B73]">
            <span className="flex flex-wrap gap-1" data-testid="sample-detail-types">
              {codes.map((c) => <TypeBadge key={c} code={c} types={types} size="sm" testId={`sample-detail-type-${c}`} />)}
            </span>
            <span className="truncate">· {sample.title}</span>
            {sample.spec_number && <span>· dari <b>{sample.spec_number}</b></span>}
          </p>
        </div>
        <span className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
          {sample.color_target?.color_id && (
            <button className="secondary-button !px-2 !py-1 text-[10.5px]" data-testid="sample-labdip-history-button" onClick={() => setHistoryOpen(true)}>
              <History size={12} /> Riwayat labdip
            </button>
          )}
          <button className="secondary-button !px-2 !py-1 text-[10.5px]" data-testid="sample-trace-button"
            onClick={() => { openTrace({ docType: "md_sample", docId: sample.id, number: sample.number }); onClose?.(); }}>
            <GitBranch size={12} /> Jejak dokumen
          </button>
          <span data-testid="sample-detail-status" className={`status-pill ${meta.cls}`}>{meta.label}</span>
          <RevisionBadge count={sampleRevisionCount(sample)} testId="sample-detail-revision" />
        </span>
      </div>
      <Stepper status={sample.status} />
      {err && <ErrorNotice message={err} onDismiss={() => setErr("")} testId="sample-detail-error" />}

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="grid gap-3">
          <div className="section-card">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Brief untuk supplier</p>
            <p data-testid="sample-detail-brief" className="mt-1 whitespace-pre-wrap text-[12.5px] leading-relaxed text-[#1C1C1E]">{sample.brief || "— tanpa brief —"}</p>
            <div className="mt-2 flex flex-wrap gap-1.5 text-[10.5px]">
              {sample.color_target?.name && (
                <span className="inline-flex items-center gap-1 rounded-full border border-[#EFF0F2] px-2 py-0.5" data-testid="sample-detail-color">
                  <span className="inline-block h-3 w-3 rounded-full border border-[#E5E5EA]" style={{ background: sample.color_target.hex || "#fff" }} />
                  {sample.color_target.code ? `${sample.color_target.code} · ` : ""}{sample.color_target.name}
                </span>
              )}
              {sample.design_code && <span className="rounded-full border border-[#EFF0F2] px-2 py-0.5" data-testid="sample-detail-design">Desain {sample.design_code} v{sample.design_version || 1}</span>}
              {sample.so_number && <span className="rounded-full border border-[#EFF0F2] px-2 py-0.5" data-testid="sample-detail-order">Pesanan {sample.so_number}</span>}
              {!!Number(sample.qty_requested) && <span className="rounded-full border border-[#EFF0F2] px-2 py-0.5">{formatQty(sample.qty_requested)} {sample.unit}</span>}
            </div>
          </div>

          <SampleSpecPanel sample={sample} canEdit={canEdit} onChanged={() => { load(); onChanged?.(); }} />

          <SampleTypeTabs sample={sample} types={types} measurements={measurements} busy={busy} loading={loading}
            highlightRoundId={focusRoundId} initialType={initialType} canSubmit={canSubmit} canAssess={canAssess}
            canAddType={canEdit && active}
            onAddType={(code) => act(() => patchSample(sample.id, { sample_types: [...codes, code] }), `${typeLabel(code, types)} ditambahkan ke permintaan.`)}
            onUpload={uploadProof}
            onSubmit={(r) => setModal({ kind: "submit", round: r })}
            onAssess={(r) => setModal({ kind: "assess", round: r })}
            onOpenRound={(p, tc) => setModal({ kind: "round", participant: p, typeCode: tc })} />

          {sample.decision?.supplier_id && (
            <div className="rounded-lg border border-[#CDE9D6] bg-[#F4FCF6] p-3" data-testid="sample-decision-box">
              <p className="flex items-center gap-1.5 text-[12px] font-bold text-[#1A7A3A]">
                <Trophy size={14} /> Pemenang: {sample.decision.supplier_name}{sample.decision.score != null ? ` · skor ${sample.decision.score}` : ""}
              </p>
              <p className="mt-1 text-[11.5px] text-[#3C3C43]">
                Alasan: <b>{sample.decision.reason_label || sample.decision.reason_code}</b> · harga kesepakatan <b>{formatCurrency(sample.decision.price || 0)}</b>
                {sample.decision.note ? ` — “${sample.decision.note}”` : ""}
              </p>
              {(sample.decision.supplier_color_name || sample.decision.supplier_color_code) && (
                <p className="mt-1 text-[11.5px] text-[#3C3C43]" data-testid="sample-decision-color">
                  Warna versi supplier: <b>{sample.decision.supplier_color_name || "—"}</b>{sample.decision.supplier_color_code ? ` (${sample.decision.supplier_color_code})` : ""} — tersimpan di Pustaka Warna.
                </p>
              )}
              <p className="mt-1 text-[11.5px]" data-testid="sample-decision-contract">
                {sample.decision.contract_number
                  ? <>Kontrak harga terbit: <b>{sample.decision.contract_number}</b>{sample.decision.supplier_item_id ? " · barang supplier terdaftar" : ""}.</>
                  : "Kontrak otomatis sedang dimatikan di Pusat Pengaturan; harga perlu dibuat manual."}
                {sample.decision.product_sku ? <> Produk <b className="font-mono">{sample.decision.product_sku}</b> lahir di master.</> : null}
              </p>
            </div>
          )}

          <SampleMasterDataPanel sample={sample} canDecide={canDecide} busy={busy} onAct={(fn, msg) => act(fn, msg)} />

          <div className="section-card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Bahan yang diambil dari gudang</p>
              {active && canSubmit && (
                <button className="secondary-button !px-2 !py-1 text-[10.5px]" disabled={busy} data-testid="sample-issue-button" onClick={() => setModal({ kind: "issue" })}>
                  <PackageMinus size={12} /> Ambil bahan
                </button>
              )}
            </div>
            {issues.length === 0 ? (
              <p className="mt-1.5 text-[11px] text-[#6B6B73]" data-testid="sample-no-material">
                Belum ada bahan diambil. Bila sample dibuat dari stok sendiri, ambil dari roll — stok gudang berkurang nyata dan nilainya dibebankan ke <b>Beban Sample &amp; Pengembangan</b>.
              </p>
            ) : (
              <div className="mt-1 divide-y divide-[#F4F5F7]">
                {issues.map((m) => (
                  <div key={m.id} data-testid={`sample-material-row-${m.id}`} className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-[11.5px]">
                    <span className="font-semibold">{m.roll_no} · {m.product_name || m.product_id}</span>
                    <span className="tabular-nums text-[#6B6B73]">{formatQty(m.qty)} {m.unit} · {formatCurrency(m.cost || 0)}{m.journal_number ? ` · jurnal ${m.journal_number}` : ""}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="section-card">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Riwayat</p>
            <div data-testid="sample-timeline" className="mt-1 grid gap-1">
              {(sample.timeline || []).slice().reverse().map((t, i) => (
                <div key={`${t.at}-${i}`} className="flex items-start gap-2 text-[11px]">
                  <CalendarClock size={12} className="mt-0.5 shrink-0 text-[#9A9BA3]" />
                  <span className="text-[#3C3C43]">
                    <strong>{t.label}</strong>{t.actor ? ` · ${t.actor}` : ""} · {String(t.at || "").slice(0, 16).replace("T", " ")}
                    {t.note ? <span className="text-[#6B6B73]"> — {t.note}</span> : null}
                  </span>
                </div>
              ))}
              {(sample.timeline || []).length === 0 && <p className="text-[11px] text-[#8E8E93]">Belum ada riwayat.</p>}
            </div>
          </div>
        </div>

        <div className="grid content-start gap-3">
          <div className="section-card">
            <Row label="Dibuat oleh" testId="sample-detail-creator">{sample.created_by || "—"}</Row>
            <Row label="Target selesai" testId="sample-detail-target">{sample.target_date ? formatDateId(sample.target_date) : "—"}</Row>
            <Row label="Supplier" testId="sample-detail-suppliers">{(sample.participants || []).length || 0}</Row>
            <Row label="Round" testId="sample-detail-rounds">{(sample.rounds || []).length} · {(sample.rounds || []).filter((r) => r.result === "acc").length} ACC</Row>
            <Row label="Biaya sample" testId="sample-detail-cost">{formatCurrency(sample.cost_total || 0)}</Row>
            <Row label="Sample jadi" testId="sample-detail-finished">
              <span className={sample.finished_at ? "text-[#1B7F4B]" : "text-[#8E8E93]"}>{sample.finished_at ? formatDateId(String(sample.finished_at).slice(0, 10)) : "Belum"}</span>
            </Row>
            <Row label="Dikirim" testId="sample-detail-delivered">
              <span className={sample.delivered_at ? "text-[#1B7F4B]" : "text-[#8E8E93]"}>
                {sample.delivered_at ? `${formatDateId(String(sample.delivered_at).slice(0, 10))} → ${deliverLabel(sample.delivered_to, deliverTargets)}${sample.delivered_to_name ? ` (${sample.delivered_to_name})` : ""}` : "Belum"}
              </span>
            </Row>
          </div>

          <div className="section-card grid gap-2">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Tindakan</p>
            {active && !hasAcc && (
              <p className="rounded-lg bg-[#F2F7FF] p-2.5 text-[11px] text-[#004099]" data-testid="sample-next-hint">
                {(sample.participants || []).length === 0
                  ? <>Langkah berikutnya: <b>kirim ke supplier</b> — round 1 dibuka untuk tiap supplier × jenis.</>
                  : <>Menunggu hasil round. Unggah bukti & <b>setor hasil</b> di tab jenisnya, lalu <b>nilai</b> (ACC / revisi / tolak).</>}
              </p>
            )}
            <div className="grid gap-1.5">
              {canSend && canSubmit && (
                <button className="secondary-button" disabled={busy} data-testid="sample-send-button" onClick={() => setModal({ kind: "send" })}>
                  <Send size={13} /> Kirim ke supplier
                </button>
              )}
              {!decided && !cancelled && canDecide && (
                <button className="primary-button" disabled={busy || !hasAcc} data-testid="sample-decide-button"
                  title={hasAcc ? "Pilih supplier pemenang" : "Belum ada round yang ACC — nilai dulu hasil sample-nya"}
                  onClick={() => setModal({ kind: "decide" })}>
                  <Trophy size={13} /> Pilih pemenang
                </button>
              )}
              {!cancelled && canSubmit && !sample.finished_at && (
                <button className="secondary-button" disabled={busy || !hasAcc} data-testid="sample-finish-button"
                  title={hasAcc ? "Tandai sample sudah jadi" : "Belum ada round yang ACC"} onClick={() => setModal({ kind: "finish" })}>
                  <CheckCircle2 size={13} /> Sample jadi
                </button>
              )}
              {!cancelled && canSubmit && sample.finished_at && !sample.delivered_at && (
                <button className="secondary-button" disabled={busy} data-testid="sample-deliver-button" onClick={() => setModal({ kind: "deliver" })}>
                  <Send size={13} /> Kirim sample
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {canCancel && active && (
                <button className="secondary-button" disabled={busy} data-testid="sample-cancel-button" onClick={batalkan}>
                  <Ban size={13} /> Batalkan
                </button>
              )}
              <button className="secondary-button" data-testid="sample-detail-close" onClick={onClose}>Tutup</button>
            </div>
          </div>
        </div>
      </div>

      {modal?.kind === "send" && (
        <SampleSendModal mode="send" sample={sample} policy={policy} types={types} busy={busy} onClose={() => setModal(null)}
          onConfirm={(body) => act(() => sendSample(sample.id, body), "Permintaan terkirim — round 1 dibuka untuk tiap supplier × jenis.")} />
      )}
      {historyOpen && (
        <LabdipHistoryModal colorId={sample.color_target?.color_id}
          label={`warna ${sample.color_target?.code || ""} · ${sample.color_target?.name || ""}`}
          entityId={sample.entity_id} onClose={() => setHistoryOpen(false)} />
      )}
      {modal?.kind === "round" && (
        <SampleSendModal mode="round" sample={sample} participant={modal.participant} typeCode={modal.typeCode} types={types}
          policy={policy} busy={busy} onClose={() => setModal(null)}
          onConfirm={(body) => act(() => openRound(sample.id, body), "Round berikutnya dibuka.")} />
      )}
      {modal?.kind === "submit" && (
        <RoundActionModal mode="submit" round={modal.round} types={types} measurements={measurements} busy={busy} onClose={() => setModal(null)}
          onConfirm={(body) => act(() => submitRound(sample.id, modal.round.id, body), "Hasil round tersimpan — menunggu penilaian.")} />
      )}
      {modal?.kind === "assess" && (
        <RoundActionModal mode="assess" round={modal.round} types={types} measurements={measurements} busy={busy} onClose={() => setModal(null)}
          onConfirm={(body) => act(() => assessRound(sample.id, modal.round.id, body), "Penilaian tersimpan — jejak QC sample tercatat.")} />
      )}
      {modal?.kind === "decide" && (
        <DecideModal sample={sample} reasons={reasons} busy={busy} onClose={() => setModal(null)}
          onConfirm={(body) => act(() => decideSample(sample.id, body), "Pemenang diputuskan — kontrak harga & barang supplier terbentuk.")} />
      )}
      {modal?.kind === "issue" && (
        <IssueMaterialModal busy={busy} onClose={() => setModal(null)}
          onConfirm={(body) => act(() => issueMaterial(sample.id, body), "Bahan diambil — stok gudang berkurang & biaya sample bertambah.")} />
      )}
      {modal?.kind === "finish" && (
        <SampleFinishModal mode="finish" sample={sample} busy={busy} onClose={() => setModal(null)}
          onConfirm={(body) => act(() => finishSample(sample.id, body), "Sample ditandai JADI — tanggalnya tercatat.")} />
      )}
      {modal?.kind === "deliver" && (
        <SampleFinishModal mode="deliver" sample={sample} targets={deliverTargets} busy={busy} onClose={() => setModal(null)}
          onConfirm={(body) => act(() => deliverSample(sample.id, body), "Pengiriman sample tercatat beserta tujuannya.")} />
      )}
    </div>
  );
}
