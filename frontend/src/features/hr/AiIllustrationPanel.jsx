import { useEffect, useState } from "react";
import axios, { API } from "../../services/apiClient";
import { Wand2, X, FlaskConical, MessageSquare, Send, Maximize2, PowerOff, Trash2 } from "lucide-react";
import { askConfirm } from "../../services/confirmService";
import KNSelect from "../../components/KNSelect";
import GalleryImage from "./GalleryImage";

// FB-01 — Ilustrasi AI (Gemini Nano Banana Pro). Hasil = ARAHAN atasan (bukan artwork /
// versi baru): desainer me-rework/revisi berdasarkan ilustrasi ini.
const MODES = [
  { value: "mockup", label: "Mockup produk (artwork → kain/produk)" },
  { value: "modify", label: "Modifikasi artwork sesuai arahan" },
];

export const fileUrl = (galleryId, fileId) => `${API}/design-gallery/${galleryId}/files/${fileId}`;

export default function AiIllustrationPanel({ g, canManage, canComment = canManage, currentUser, onChanged }) {
  const artworks = (g.files || []).filter((f) => (f.kind || "artwork") !== "ai_illustration");
  const illus = (g.files || []).filter((f) => f.kind === "ai_illustration");
  const [status, setStatus] = useState(null);
  const [mode, setMode] = useState("mockup");
  const [source, setSource] = useState(artworks[0]?.id || "");
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    axios.get(`${API}/design-gallery-ai/status`).then((r) => setStatus(r.data)).catch(() => setStatus(null));
  }, []);
  useEffect(() => { if (!source && artworks[0]) setSource(artworks[0].id); }, [artworks.length]); // eslint-disable-line

  async function generate() {
    if (prompt.trim().length < 3) { setErr("Tulis arahan minimal 3 karakter."); return; }
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await axios.post(`${API}/design-gallery/${g.id}/ai-illustrate`, {
        mode, prompt: prompt.trim(), source_file_id: source || null,
      });
      setMsg("Ilustrasi AI selesai.");
      setPrompt(""); setPreview(r.data?.id || null);
      await onChanged();
    } catch (e) { setErr(e.response?.data?.detail || "Gagal membuat ilustrasi AI."); }
    finally { setBusy(false); }
  }
  async function remove(fid) {
    const f = illus.find((x) => x.id === fid);
    const n = (f?.comments || []).length;
    // G-1 — konfirmasi + peringatan jumlah komentar yang ikut hilang.
    const ok = await askConfirm({ title: "Hapus ilustrasi AI ini?", danger: true, confirmLabel: "Hapus",
      description: n ? `${n} komentar "Diskusi arahan" pada ilustrasi ini akan ikut terhapus dan tidak bisa dikembalikan.` : "Ilustrasi akan dihapus permanen." });
    if (!ok) return;
    setErr(""); setMsg("");
    try { await axios.delete(`${API}/design-gallery/${g.id}/files/${fid}`); if (preview === fid) setPreview(null); setMsg("Ilustrasi dihapus."); await onChanged(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal menghapus ilustrasi."); }
  }

  const sourceOpts = artworks.map((f, i) => ({ value: f.id, label: `Artwork ${i + 1} — ${f.filename}` }));
  const shown = illus.find((f) => f.id === preview);

  return (
    <div className="mt-3 rounded-lg border border-[#E6DDF7] bg-[#FAF7FF] p-2.5" data-testid="gallery-ai-illustration-block">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="flex items-center gap-1.5 text-[12px] font-semibold text-[#5B2EA6]"><Wand2 size={14} /> Ilustrasi AI — arahan (Gemini Nano Banana Pro)</span>
        {status && (
          /* G-2 — NONAKTIF punya badge sendiri (abu), tidak lagi bertentangan dengan catatan "dinonaktifkan" */
          <span data-testid="gallery-ai-status" className={`px-1.5 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 ${status.enabled === false ? "bg-[#EDEEF1] text-[#6B6B73]" : status.demo ? "bg-[#FFF3D6] text-[#8C4A00]" : status.verified ? "bg-[#E7F5EC] text-[#1F7A45]" : "bg-[#FFF3D6] text-[#8C4A00]"}`}>
            {status.enabled === false ? <><PowerOff size={10} /> NONAKTIF</> : status.demo ? <><FlaskConical size={10} /> MODE DEMO</> : status.verified ? `LIVE · ${status.model}` : `KEY BELUM DIUJI · ${status.model}`}
          </span>
        )}
      </div>
      <p className="text-[10.5px] text-[#6B6B73] mt-1">
        Hasil AI adalah <b>ilustrasi arahan</b> — bukan artwork & bukan versi baru. Desainer me-rework artwork berdasarkan ilustrasi ini.
      </p>
      {err && <div className="notice-bar danger !my-2 !py-1.5" data-testid="gallery-ai-illus-error"><span className="text-[11.5px]">{err}</span></div>}
      {msg && <div className="notice-bar success !my-2 !py-1.5" data-testid="gallery-ai-illus-msg"><span className="text-[11.5px]">{msg}</span></div>}

      {canManage && status?.enabled === true && (
        <div className="grid gap-2 mt-2">
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Mode</label>
              <KNSelect data-testid="gallery-ai-mode" value={mode} onValueChange={setMode} options={MODES} className="field" /></div>
            <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Artwork acuan</label>
              {sourceOpts.length ? <KNSelect data-testid="gallery-ai-source" value={source} onValueChange={setSource} options={sourceOpts} className="field" />
                : <p className="text-[11px] text-[#B7791F]">Belum ada artwork — mockup tetap bisa dibuat dari arahan teks.</p>}</div>
          </div>
          <textarea data-testid="gallery-ai-prompt" className="form-input" rows="2" value={prompt} onChange={(e) => setPrompt(e.target.value)}
            placeholder={mode === "mockup" ? "mis. Terapkan motif ini pada kemeja lengan panjang, latar studio putih" : "mis. Ganti warna dasar jadi navy, perbesar skala motif 20%"} />
          <div className="flex items-center gap-2">
            <button data-testid="gallery-ai-generate-button" className="primary-button !py-1.5" onClick={generate} disabled={busy}>
              <Wand2 size={13} /> {busy ? "Membuat ilustrasi…" : "Buat Ilustrasi"}
            </button>
            {status?.demo && <span className="text-[10.5px] text-[#8C4A00]">Isi API key Gemini di Pengaturan → Integrasi AI untuk hasil sungguhan.</span>}
          </div>
        </div>
      )}
      {status && status.enabled === false && <p className="text-[11px] text-[#B7791F] mt-1.5" data-testid="gallery-ai-illus-disabled">{status.disabled_reason || "Ilustrasi AI dinonaktifkan admin."}</p>}

      <div className="grid gap-1.5 mt-3">
        <label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Ilustrasi arahan ({illus.length})</label>
        {illus.length === 0 && <p className="text-[10.5px] text-[#9A9BA3]" data-testid="gallery-ai-illus-empty">Belum ada ilustrasi AI.</p>}
        <div className="flex flex-wrap gap-2">
          {illus.map((f) => (
            <div key={f.id} className="relative w-[120px]" data-testid={`gallery-ai-illus-${f.id}`}>
              <button type="button" className="block w-full aspect-[4/3] rounded-md overflow-hidden bg-[#F2F3F5] border-2 border-[#C9B8EE]" onClick={() => setPreview(f.id)} title={f.ai?.prompt}>
                <GalleryImage galleryId={g.id} fileId={f.id} alt={f.ai?.prompt || f.filename} />
              </button>
              <span className="absolute top-1 left-1 px-1 py-0.5 rounded bg-[#5B2EA6] text-white text-[9px] font-bold">{f.ai?.demo ? "AI · DEMO" : "AI"} · {f.ai?.mode}</span>
              {(f.comments || []).length > 0 && <span data-testid={`gallery-ai-illus-comments-${f.id}`} className="absolute bottom-6 right-1 px-1 py-0.5 rounded bg-white/90 border border-[#C9B8EE] text-[#5B2EA6] text-[9px] font-bold flex items-center gap-0.5" title={`${f.comments.length} komentar`}><MessageSquare size={9} /> {f.comments.length}</span>}
              <span className="block text-[9.5px] text-[#6B6B73] truncate mt-0.5" title={f.ai?.prompt}>{f.ai?.prompt}</span>
              {canManage && <button data-testid={`gallery-ai-illus-del-${f.id}-button`} className="absolute -top-1.5 -right-1.5 bg-white rounded-full shadow p-0.5 text-[#C0341D]" onClick={() => remove(f.id)}><X size={12} /></button>}
            </div>
          ))}
        </div>
      </div>

      {shown && (
        <div className="mt-3 rounded-md border border-[#C9B8EE] bg-white p-2" data-testid="gallery-ai-illus-preview">
          <div className="flex items-start justify-between gap-2">
            <p className="text-[11px] text-[#3A3B42]"><b>{shown.ai?.mode === "mockup" ? "Mockup" : "Modifikasi"}</b> · oleh {shown.ai?.by} · {shown.ai?.model}<br />{shown.ai?.prompt}</p>
            <div className="flex items-center gap-1 shrink-0">
              <a data-testid="gallery-ai-illus-open-full" className="secondary-button !py-1 !px-2 !text-[11px]" href={fileUrl(g.id, shown.id)} target="_blank" rel="noopener noreferrer" title="Buka ukuran penuh di tab baru"><Maximize2 size={12} /> Ukuran penuh</a>
              <button className="icon-button" onClick={() => setPreview(null)}><X size={14} /></button>
            </div>
          </div>
          <div className="mt-1.5 max-h-[480px] rounded overflow-hidden bg-[#F2F3F5]"><GalleryImage galleryId={g.id} fileId={shown.id} alt={shown.ai?.prompt} fit="contain" /></div>
          <IllustrationComments g={g} file={shown} canComment={canComment} currentUser={currentUser} onChanged={onChanged} />
        </div>
      )}
    </div>
  );
}

// Komentar arahan ↔ balasan desainer, berurutan waktu, tersimpan pada berkas ilustrasi.
function IllustrationComments({ g, file, canComment, currentUser, onChanged }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const comments = file.comments || [];
  const canDelete = (c) => currentUser && (c.user_id === currentUser.id || currentUser.role === "admin");
  async function removeComment(c) {   // G-6 — hapus komentar sendiri
    if (!(await askConfirm({ title: "Hapus komentar ini?", description: c.text.slice(0, 120), confirmLabel: "Hapus", danger: true }))) return;
    setErr("");
    try { await axios.delete(`${API}/design-gallery/${g.id}/files/${file.id}/comments/${c.id}`); await onChanged(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal menghapus komentar."); }
  }
  async function send() {
    if (!text.trim()) return;
    setBusy(true); setErr("");
    try {
      await axios.post(`${API}/design-gallery/${g.id}/files/${file.id}/comments`, { text: text.trim() });
      setText(""); await onChanged();
    } catch (e) { setErr(e.response?.data?.detail || "Gagal mengirim komentar."); }
    finally { setBusy(false); }
  }
  return (
    <div className="mt-2 border-t border-[#EEE9F8] pt-2" data-testid="gallery-ai-comments">
      <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase text-[#6B6B73]"><MessageSquare size={12} /> Diskusi arahan ({comments.length})</p>
      <div className="mt-1.5 grid gap-1.5 max-h-[200px] overflow-auto">
        {comments.length === 0 && <p className="text-[10.5px] text-[#9A9BA3]" data-testid="gallery-ai-comments-empty">Belum ada komentar. Desainer dapat membalas arahan di sini.</p>}
        {comments.map((c) => (
          <div key={c.id} data-testid={`gallery-ai-comment-${c.id}`} className={`rounded-md px-2.5 py-1.5 text-[11.5px] ${c.role === "designer" ? "bg-[#F1F5FF] border border-[#D6E2FF]" : "bg-[#FAF7FF] border border-[#E6DDF7]"}`}>
            <p className="text-[10px] text-[#6B6B73] flex items-center gap-1"><b>{c.by}</b> · {c.role === "designer" ? "Desainer" : "Atasan"} · {String(c.at).slice(0, 16).replace("T", " ")}
              {canDelete(c) && <button type="button" data-testid={`gallery-ai-comment-del-${c.id}`} className="ml-auto icon-button !p-0.5 text-[#C0341D]" title="Hapus komentar saya" onClick={() => removeComment(c)}><Trash2 size={11} /></button>}</p>
            <p className="text-[#3A3B42] whitespace-pre-wrap">{c.text}</p>
          </div>
        ))}
      </div>
      {err && <p className="text-[11px] text-[#C0341D] mt-1" data-testid="gallery-ai-comment-error">{err}</p>}
      {canComment && (
        <div className="flex gap-2 mt-2">
          <input data-testid="gallery-ai-comment-input" className="form-input flex-1" placeholder="Tulis catatan / balasan…" value={text}
            onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") send(); }} />
          <button data-testid="gallery-ai-comment-send" className="secondary-button" disabled={busy || !text.trim()} onClick={send}><Send size={13} /> Kirim</button>
        </div>
      )}
    </div>
  );
}
