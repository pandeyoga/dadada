/** LifecycleActions — tombol aksi sesuai status & peran (desainer vs penilai) + dialog catatan/nilai/ACC/hold.
 *  Nilai HANYA diberikan sekali, di dialog ACC (keputusan pemilik 2026-09). */
import { useState } from "react";
import { overlayDismiss } from "@/utils/overlayDismiss";   // INV-UI-01
import { Archive, CheckCircle2, Eye, GitBranch, PackageCheck, PauseCircle, PlayCircle, Rocket, RotateCcw, Send, Undo2 } from "lucide-react";
import { designLifecycle, designNewVersion, holdDesign, releaseDesignHold } from "../rndApi";
import { errMsg, roundLabel } from "../rndMeta";
import ScoreInput from "./ScoreInput";
import ProductPicker from "./ProductPicker";

const ACTIONS = {
  submit: { label: "Ajukan untuk review", icon: Send, side: "designer", cls: "primary-button" },
  start_review: { label: "Mulai review", icon: Eye, side: "assessor", cls: "primary-button" },
  approve: { label: "Setujui (ACC) + nilai akhir", icon: CheckCircle2, side: "assessor", cls: "primary-button", needScore: true },
  request_revision: { label: "Minta revisi", icon: RotateCcw, side: "assessor", cls: "secondary-button", needNote: true },
  submit_final: { label: "Serahkan berkas final", icon: PackageCheck, side: "designer", cls: "primary-button" },
  return_final: { label: "Kembalikan berkas final", icon: RotateCcw, side: "assessor", cls: "secondary-button", needNote: true },
  activate: { label: "Aktifkan untuk produksi", icon: Rocket, side: "assessor", cls: "primary-button" },
  archive: { label: "Arsipkan", icon: Archive, side: "assessor", cls: "secondary-button", needNote: true },
  reopen: { label: "Buka kembali", icon: Undo2, side: "assessor", cls: "secondary-button" },
  new_version: { label: "Buat versi baru", icon: GitBranch, side: "designer", cls: "secondary-button", needNote: true },
  hold: { label: "Tahan desain", icon: PauseCircle, side: "holder", cls: "secondary-button !border-[#F2B48A] !text-[#B24A00]", needNote: true },
  release_hold: { label: "Lepas penahanan", icon: PlayCircle, side: "holder", cls: "primary-button !bg-[#B24A00]" },
};

const BY_STATUS = {
  draft: ["submit", "archive"],
  revision: ["submit", "archive"],
  pending_approval: ["start_review", "approve", "request_revision", "archive"],
  in_review: ["approve", "request_revision", "archive"],
  approved: ["submit_final", "hold", "archive"],
  final_submitted: ["activate", "return_final", "hold", "archive"],
  active: ["new_version", "hold", "archive"],
  archived: ["reopen"], retired: ["reopen"],
};

export default function LifecycleActions({ design, canAssess, canEdit, canHold = false, minAcc = 1.5, onDone, onError }) {
  const [dlg, setDlg] = useState(null);
  const [note, setNote] = useState("");
  const [score, setScore] = useState(null);
  const [products, setProducts] = useState([]);
  const [busy, setBusy] = useState(false);
  const status = design.status || "draft";
  const fin = design.final || {};

  const base = design.on_hold ? ["release_hold", "archive"] : (BY_STATUS[status] || []);
  const visible = base.filter((a) => {
    const m = ACTIONS[a];
    if (m.side === "holder") return canHold;
    return m.side === "assessor" ? canAssess : canEdit;
  });

  const open = (a) => {
    setDlg({ action: a }); setNote(""); setScore(null);
    setProducts(design.recommended_products || []);
  };

  const run = async () => {
    const a = dlg.action;
    const m = ACTIONS[a];
    if (m.needNote && !note.trim()) { onError?.("Catatan wajib diisi."); return; }
    if (m.needScore && score === null) { onError?.("Beri nilai akhir (0–2) — nilai hanya diberikan saat ACC."); return; }
    setBusy(true);
    try {
      if (a === "new_version") await designNewVersion(design.id, { note });
      else if (a === "hold") await holdDesign(design.id, note);
      else if (a === "release_hold") await releaseDesignHold(design.id, note);
      else {
        const body = { note, score: m.needScore ? score : undefined };
        if (a === "approve") { body.recommended_product_ids = products.map((p) => p.id); }
        await designLifecycle(design.id, a.replace(/_/g, "-"), body);
      }
      setDlg(null);
      onDone?.(`${m.label} berhasil.`);
    } catch (e) { onError?.(errMsg(e, "Aksi gagal.")); } finally { setBusy(false); }
  };

  if (!visible.length) return null;
  const A = dlg ? ACTIONS[dlg.action] : null;
  return (
    <div className="flex flex-wrap gap-1.5" data-testid="design-lifecycle-actions">
      {visible.map((a) => {
        const m = ACTIONS[a]; const Icon = m.icon;
        return (
          <button key={a} className={`${m.cls} !py-1.5 text-[11.5px]`} onClick={() => open(a)} data-testid={`design-action-${a}`}>
            <Icon size={13} /> {m.label}
          </button>
        );
      })}
      {dlg && (
        <div className="fixed inset-0 z-[190] flex items-center justify-center bg-black/50 p-4" {...overlayDismiss(() => setDlg(null))} data-testid="design-action-dialog">
          <div className="max-h-[90vh] w-full max-w-[560px] space-y-3 overflow-y-auto rounded-xl bg-white p-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-[14px] font-bold">{A.label} — {design.code} · {roundLabel(design.version)}</h3>
            <DialogHint action={dlg.action} design={design} fin={fin} />
            {dlg.action === "approve" && (
              <div>
                <p className="mb-1 text-[10.5px] font-semibold text-[#6B6B73]">Peruntukan produk (ditentukan penilai)</p>
                <ProductPicker value={products} onChange={setProducts} testId="design-approve-products" />
              </div>
            )}
            {A.needScore && (
              <div>
                <p className="mb-1 text-[10.5px] font-semibold text-[#6B6B73]">Nilai akhir desain * (sekali, saat ACC — menjadi nilai KPI desainer)</p>
                <ScoreInput value={score} onChange={setScore} minAcc={minAcc} testId="design-action-score" />
              </div>
            )}
            <div>
              <p className="mb-1 text-[10.5px] font-semibold text-[#6B6B73]">
                {dlg.action === "new_version" ? "Apa yang berubah pada versi ini? *"
                  : dlg.action === "request_revision" ? "Catatan revisi untuk desainer *"
                    : dlg.action === "return_final" ? "Apa yang kurang pada berkas final? *"
                      : dlg.action === "archive" ? "Alasan pengarsipan *"
                        : dlg.action === "hold" ? "Alasan hold * (terlihat oleh R&D saat proofing ditolak)" : "Catatan (opsional)"}
              </p>
              <textarea className="field" rows={3} value={note} onChange={(e) => setNote(e.target.value)} data-testid="design-action-note"
                placeholder={dlg.action === "request_revision" ? "mis. warna latar terlalu gelap, repeat belum rapi"
                  : dlg.action === "hold" ? "mis. menunggu keputusan MD / bahan belum tersedia" : ""} />
            </div>
            <div className="flex justify-end gap-2">
              <button className="secondary-button" onClick={() => setDlg(null)}>Batal</button>
              <button className="primary-button" onClick={run} disabled={busy} data-testid="design-action-confirm">
                {busy ? "Memproses…" : A.label}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DialogHint({ action, design, fin }) {
  const box = (cls, children, testId) => <p className={`rounded-lg px-3 py-2 text-[11.5px] ${cls}`} data-testid={testId}>{children}</p>;
  if (action === "submit") return box("bg-[#F2F7FF] text-[#004099]", <>
    <b>{roundLabel(design.version)}</b> ({design.rounds?.find((r) => r.version === design.version)?.file_count ?? 0} berkas) akan masuk antrean penilai. Pastikan semua berkas ronde ini sudah diunggah.</>);
  if (action === "request_revision") return box("bg-[#FDF3F2] text-[#C62828]", <>
    Ronde <b>{roundLabel(design.version + 1)}</b> dibuka otomatis. <b>Tidak ada nilai</b> pada revisi — nilai diberikan sekali saat ACC.</>);
  if (action === "submit_final") return box(fin.complete ? "bg-[#EAF7EF] text-[#1A7A3A]" : "bg-[#FDF3F2] text-[#C62828]", <>
    Mockup {fin.mockup_files}/1 · File desain asli {fin.source_files ?? 0}/1.{fin.complete ? " Lengkap — siap diserahkan." : " Belum lengkap — unggah dulu di tab Final."}</>, "design-submit-final-check");
  if (action === "new_version") return box("bg-[#F2F7FF] text-[#004099]", <>
    v{design.version} → <b>v{design.version + 1}</b>. Status kembali <b>Draf</b>; unggah berkas baru lalu ajukan lagi.</>);
  if (action === "hold") return box("bg-[#FFF1E6] text-[#B24A00]", <>
    Selama <b>DITAHAN</b>, desain ini <b>tidak bisa dipakai permintaan proofing R&D</b> dan tidak bisa diaktifkan untuk produksi. Label DITAHAN tampil di daftar & bisa disaring.</>, "design-hold-hint");
  if (action === "release_hold") return box("bg-[#EAF7EF] text-[#1A7A3A]", <>
    Ditahan sejak <b>{design.hold?.at ? new Date(design.hold.at).toLocaleString("id-ID") : "—"}</b> oleh <b>{design.hold?.by}</b>: “{design.hold?.reason}”. Setelah dilepas, desain kembali bisa masuk proofing.</>, "design-release-hold-hint");
  return null;
}
