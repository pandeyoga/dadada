/** PostDetailModal — rincian konten: status & aksi alur, lampiran, performa, riwayat. */
import { useEffect, useState } from "react";
import { FileText, Image as ImageIcon, Loader2, Megaphone, Pencil, Trash2, Upload, X } from "lucide-react";
import FormModal from "../../components/FormModal";
import { askReason, askConfirm } from "@/services/confirmService";
import { useProofBlob } from "../rnd/ProofImage";
import PostFormModal from "./PostFormModal";
import { mktApi, NEXT_ACTIONS, PlatformChip, StatusPill, METRIC_LABEL, fmtN, fmtWhen } from "./marketingShared";

export default function PostDetailModal({ postId, meta, campaigns, currentUser, onClose, onChanged }) {
  const [post, setPost] = useState(null);
  const [edit, setEdit] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [url, setUrl] = useState("");
  const [metrics, setMetrics] = useState({});
  const role = currentUser?.role;
  const canEdit = ["admin", "manager", "designer", "sales", "sales_admin"].includes(role);
  const isApprover = ["admin", "manager"].includes(role);

  const refresh = async () => { const p = await mktApi.post(postId); setPost(p); setUrl(p.published_url || ""); setMetrics(p.metrics || {}); };
  useEffect(() => { refresh().catch(() => setErr("Konten tidak ditemukan.")); }, [postId]); // eslint-disable-line

  const act = async (a) => {
    setErr("");
    let note = "";
    if (a.reason) { note = await askReason({ title: `${a.label} · alasan?`, testId: "mkt-reason" }); if (!note) return; }
    setBusy(true);
    try { setPost(await mktApi.transition(post.id, { to: a.to, note, published_url: a.url ? url : "" })); onChanged?.(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal mengubah status."); } finally { setBusy(false); }
  };
  const saveMetrics = async () => {
    setBusy(true); setErr("");
    try { setPost(await mktApi.metrics(post.id, { metrics })); onChanged?.(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan performa."); } finally { setBusy(false); }
  };
  const upload = async (files) => {
    setBusy(true); setErr("");
    try { let latest = post; for (const f of files) latest = (await mktApi.upload(post.id, f)).post; setPost(latest); }
    catch (e) { setErr(e.response?.data?.detail || "Unggah gagal."); } finally { setBusy(false); }
  };
  const remove = async () => {
    const ok = await askConfirm({ title: `Hapus konten "${post.title}"?`, danger: true, testId: "mkt-delete-confirm" });
    if (!ok) return;
    try { await mktApi.deletePost(post.id); onChanged?.(); onClose(); } catch (e) { setErr(e.response?.data?.detail || "Gagal menghapus."); }
  };

  if (!post) return <FormModal open title="Memuat…" onClose={onClose} testId="mkt-post-detail-loading"><p className="text-[12px]">{err || "…"}</p></FormModal>;
  const actions = (NEXT_ACTIONS[post.status] || []).filter((a) => !a.approver || isApprover);
  const camp = campaigns?.find((c) => c.id === post.campaign_id);

  return (
    <>
      <FormModal open title={post.title} subtitle={`${post.content_type} · ${post.pic_name ? `PIC ${post.pic_name}` : "tanpa PIC"} · dibuat ${post.created_by}`} icon={Megaphone} size="lg" onClose={onClose} testId="mkt-post-detail"
        footer={<div className="flex w-full flex-wrap items-center gap-2">
          {canEdit && post.status !== "published" && <button type="button" className="secondary-button !py-1 text-[11px]" onClick={() => setEdit(true)} data-testid="mkt-edit-post"><Pencil size={12} /> Ubah</button>}
          {isApprover && post.status !== "published" && <button type="button" className="secondary-button !py-1 text-[11px] !text-[#C0392B]" onClick={remove} data-testid="mkt-delete-post"><Trash2 size={12} /> Hapus</button>}
          <span className="flex-1" />
          {canEdit && actions.map((a) => <button key={a.to} type="button" disabled={busy} onClick={() => act(a)} data-testid={`mkt-action-${a.to}`} className={`${a.primary ? "primary-button" : "secondary-button"} !py-1 text-[11px]`}>{busy ? <Loader2 size={12} className="spin" /> : null} {a.label}</button>)}
          <button type="button" className="secondary-button !py-1 text-[11px]" onClick={onClose} data-testid="mkt-detail-close">Tutup</button>
        </div>}>
        <div className="grid gap-3 text-[12px]">
          <div className="flex flex-wrap items-center gap-1.5">
            <StatusPill status={post.status} testId="mkt-detail-status" />
            {(post.platforms || []).map((c) => <PlatformChip key={c} code={c} />)}
            {(post.accounts || []).map((a) => <span key={a.id} className="rounded-full bg-[#F2F2F7] px-2 py-px text-[10px] font-bold text-[#3C3C43]" data-testid={`mkt-detail-account-${a.id}`}>@{a.handle}</span>)}
            {post.entity_name && <span className="rounded-full bg-[#E0F2FE] px-2 py-px text-[10px] font-bold text-[#0369A1]" data-testid="mkt-detail-entity">{post.entity_name}</span>}
            <span className="text-[11px] text-[#6B6B73]">· tayang {post.publish_at ? `${fmtWhen(post.publish_at)} WIB` : "belum dijadwalkan"}</span>
            {camp && <span className="rounded-full px-2 py-px text-[10px] font-bold text-white" style={{ background: camp.color || "#0058CC" }}>{camp.name}</span>}
          </div>
          {err && <p className="text-[11px] text-[#C0392B]" data-testid="mkt-detail-error">{err}</p>}
          {post.status === "scheduled" && canEdit && (
            <label className="text-[10.5px] font-semibold text-[#6B6B73]">Tautan post (tempel setelah diposting)<input className="field mt-0.5 w-full" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.instagram.com/p/…" data-testid="mkt-published-url" /></label>
          )}
          {post.published_url && <a href={post.published_url} target="_blank" rel="noreferrer" className="text-[11px] text-[#0058CC] underline" data-testid="mkt-published-link">{post.published_url}</a>}

          <section className="rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Caption</p>
            <p className="whitespace-pre-wrap" data-testid="mkt-detail-caption">{post.caption || <span className="text-[#9A9BA3]">belum ada caption</span>}</p>
            {post.hashtags?.length > 0 && <p className="mt-1 text-[11px] text-[#0058CC]">{post.hashtags.map((h) => `#${h}`).join(" ")}</p>}
            {post.cta && <p className="mt-1 text-[11px]"><b>CTA:</b> {post.cta}</p>}
            {post.assets?.length > 0 && <p className="mt-1 text-[11px] text-[#6B6B73]"><b>Bahan:</b> {post.assets.map((a) => a.label).join(" · ")}</p>}
            {post.notes && <p className="mt-1 text-[11px] text-[#6B6B73]"><b>Catatan:</b> {post.notes}</p>}
          </section>

          <section>
            <div className="mb-1 flex items-center justify-between"><p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Materi visual · {post.attachments?.length || 0}</p>
              {canEdit && <label className="secondary-button cursor-pointer !py-0.5 text-[10.5px]" data-testid="mkt-upload-label"><Upload size={11} /> Unggah gambar/video<input type="file" multiple accept="image/*,video/*,.pdf" className="hidden" data-testid="mkt-upload" onChange={(e) => { const fs = Array.from(e.target.files || []); if (fs.length) upload(fs); e.target.value = ""; }} /></label>}
            </div>
            <div className="flex flex-wrap gap-1.5" data-testid="mkt-attachments">
              {(post.attachments || []).map((f) => <Thumb key={f.id} meta={f} url={mktApi.attachmentUrl(post.id, f.id)} onRemove={canEdit && post.status !== "published" ? async () => setPost(await mktApi.removeAttachment(post.id, f.id)) : null} />)}
              {!post.attachments?.length && <p className="text-[11px] text-[#9A9BA3]">belum ada materi</p>}
            </div>
          </section>

          {post.status === "published" && (
            <section className="rounded-lg border border-[#CDE9D6] bg-[#F4FBF6] p-2.5" data-testid="mkt-metrics">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-[#1B7F4B]">Performa (isi manual dari insight platform)</p>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                {Object.entries(METRIC_LABEL).map(([k, l]) => (
                  <label key={k} className="text-[10px] font-semibold text-[#6B6B73]">{l}<input type="number" min="0" className="field mt-0.5 w-full !py-0.5" value={metrics[k] ?? ""} disabled={!canEdit} onChange={(e) => setMetrics((m) => ({ ...m, [k]: e.target.value }))} data-testid={`mkt-metric-${k}`} /></label>
                ))}
              </div>
              <div className="mt-2 flex items-center gap-2">
                {canEdit && <button type="button" className="primary-button !py-1 text-[11px]" disabled={busy} onClick={saveMetrics} data-testid="mkt-save-metrics">Simpan performa</button>}
                {post.metrics?.recorded_at && <span className="text-[10.5px] text-[#6B6B73]">terakhir dicatat {fmtWhen(post.metrics.recorded_at)} · engagement {fmtN((post.metrics.likes || 0) + (post.metrics.comments || 0) + (post.metrics.shares || 0) + (post.metrics.saves || 0))}</span>}
              </div>
            </section>
          )}

          <section>
            <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Riwayat</p>
            <ol className="grid gap-0.5 text-[11px]" data-testid="mkt-history">
              {[...(post.history || [])].reverse().map((h, i) => <li key={i} className="flex gap-2"><span className="w-28 font-mono text-[#8E8E93]">{fmtWhen(h.at)}</span><StatusPill status={h.status} /><span>{h.by}{h.note ? ` — ${h.note}` : ""}</span></li>)}
            </ol>
          </section>
        </div>
      </FormModal>
      {edit && <PostFormModal meta={meta} campaigns={campaigns} post={post} onClose={() => setEdit(false)} onSaved={(p) => { setPost(p); setEdit(false); onChanged?.(); }} />}
    </>
  );
}

function Thumb({ meta, url, onRemove }) {
  const isImg = meta.content_type?.startsWith("image/");
  const { src, status } = useProofBlob(url, isImg);
  return (
    <div className="relative h-20 w-20 overflow-hidden rounded-md border border-[#E5E5EA] bg-[#F5F5F7]" data-testid={`mkt-attachment-${meta.id}`} title={meta.filename}>
      <a href={url} target="_blank" rel="noreferrer" className="flex h-full w-full items-center justify-center">
        {isImg ? (status === "ok" && src ? <img src={src} alt={meta.filename} className="h-full w-full object-cover" /> : <ImageIcon size={16} className="text-[#B5B5BC]" />) : <FileText size={16} className="text-[#6B6B73]" />}
      </a>
      {onRemove && <button type="button" onClick={onRemove} className="absolute right-0.5 top-0.5 rounded-full bg-white/90 p-0.5 shadow" data-testid={`mkt-attachment-remove-${meta.id}`}><X size={10} /></button>}
    </div>
  );
}
