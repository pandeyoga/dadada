// PdfTemplateDesigner — Fase 3: Advanced PDF Configuration UI.
// Editor template per doc_type + branding per entitas + pratinjau HTML live (debounced)
// + unduh PDF. Konsumsi endpoint /api/pdf/* (lihat routers/pdf.py).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios, { API } from "../../services/apiClient";
import KNSelect from "../../components/KNSelect";
import PdfEditorTabs from "./PdfEditorTabs";
import { DEFAULT_CODE } from "./pdfConstants";
import { askConfirm } from "../../services/confirmService";
import {
  FileText, Download, Save, RotateCcw, Loader2, RefreshCw, FileWarning, Layers,
} from "lucide-react";

export default function PdfTemplateDesigner({ currentUser, selectedEntity, entities = [] }) {
  const [docTypes, setDocTypes] = useState([]);       // dari /pdf/templates (berlapis: __default__ + jenis)
  const [docType, setDocType] = useState(DEFAULT_CODE);
  const [config, setConfig] = useState(null);
  const [defaults, setDefaults] = useState(null);
  const [meta, setMeta] = useState(null);             // {customized, version, updated_at, updated_by, override_keys}
  const [defaultEffective, setDefaultEffective] = useState(null);
  const [placeholders, setPlaceholders] = useState([]);
  const [newImages, setNewImages] = useState({});     // {header_image_b64|footer_image_b64|stamp_b64: dataURL|""}
  const isDefault = docType === DEFAULT_CODE;
  // Pratinjau __default__ memakai dokumen nyata jenis pertama yang punya data.
  const previewDocType = isDefault ? (docTypes.find((d) => d.doc_type !== DEFAULT_CODE)?.doc_type || "invoice") : docType;
  const [entityId, setEntityId] = useState("");
  const [branding, setBranding] = useState(null);
  const [newLogo, setNewLogo] = useState(null);       // data-URL logo baru (belum disimpan)
  const [sample, setSample] = useState(null);         // {source_id, number, entity_id, label}
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewNonce, setPreviewNonce] = useState(0);
  const [savingTpl, setSavingTpl] = useState(false);
  const [savingBrand, setSavingBrand] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [brandingMsg, setBrandingMsg] = useState("");
  const [brandingErr, setBrandingErr] = useState("");
  const flash = useRef(null);

  const docTypeOptions = useMemo(
    () => docTypes.map((d) => ({ value: d.doc_type,
      label: `${d.label}${d.customized ? " · disetel" : ""}`,
      group: d.doc_type === DEFAULT_CODE ? "Bawaan" : (d.module || "Lainnya") })), [docTypes]);
  const entityOptions = useMemo(
    () => entities.map((e) => ({ value: e.id, label: e.legal_name || e.short_name || e.id })), [entities]);

  const flashMsg = useCallback((text) => {
    setMsg(text); setErr("");
    if (flash.current) clearTimeout(flash.current);
    flash.current = setTimeout(() => setMsg(""), 3500);
  }, []);

  // init entity dari konteks aktif
  useEffect(() => {
    if (!entities.length || entityId) return;
    const initial = (selectedEntity && selectedEntity !== "all" && entities.some((e) => e.id === selectedEntity))
      ? selectedEntity : entities[0].id;
    setEntityId(initial);
  }, [entities, selectedEntity, entityId]);

  // muat daftar jenis dokumen berlapis (+ status disetel/versi)
  const loadTargets = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/pdf/templates`);
      setDocTypes(r.data.data || []); setPlaceholders(r.data.placeholders || []);
    } catch (e) { setErr(e.response?.data?.detail || "Gagal memuat daftar dokumen."); }
  }, []);
  useEffect(() => { loadTargets(); }, [loadTargets]);

  // muat template cfg saat docType berubah
  useEffect(() => {
    if (!docType) return;
    (async () => {
      try {
        const r = await axios.get(`${API}/pdf/templates/${docType}`);
        setConfig(r.data.config); setDefaults(r.data.defaults); setMeta(r.data.meta || null);
        setDefaultEffective(r.data.default_effective || null);
        if (r.data.placeholders) setPlaceholders(r.data.placeholders);
      } catch (e) { setErr(e.response?.data?.detail || "Gagal memuat template."); }
    })();
  }, [docType]);

  // muat branding saat entitas berubah
  useEffect(() => {
    if (!entityId) return;
    setNewLogo(null); setNewImages({}); setBrandingMsg(""); setBrandingErr("");
    (async () => {
      try {
        const r = await axios.get(`${API}/pdf/branding/${entityId}`);
        setBranding(r.data);
      } catch (e) { setBranding(null); }
    })();
  }, [entityId]);

  // muat sample doc saat docType/entitas berubah
  useEffect(() => {
    if (!previewDocType) return;
    (async () => {
      try {
        const r = await axios.get(`${API}/pdf/sample/${previewDocType}`, { params: { entity_id: entityId || undefined } });
        setSample(r.data);
      } catch (e) { setSample(null); }
    })();
  }, [previewDocType, entityId]);

  // pratinjau debounced (config/docType/entity/sample/nonce)
  const cfgKey = config ? JSON.stringify(config) : "";
  useEffect(() => {
    if (!docType || !config) return undefined;
    if (!sample || !sample.source_id) { setPreviewHtml(""); setPreviewError(""); return undefined; }
    setPreviewLoading(true); setPreviewError("");
    const t = setTimeout(async () => {
      try {
        const r = await axios.post(`${API}/pdf/preview`, {
          doc_type: previewDocType, source_id: sample.source_id,
          entity_id: entityId || sample.entity_id, config,
        }, { headers: { Accept: "text/html" } });
        setPreviewHtml(typeof r.data === "string" ? r.data : String(r.data || ""));
      } catch (e) {
        setPreviewError(e.response?.data?.detail || "Gagal memuat pratinjau.");
        setPreviewHtml("");
      } finally { setPreviewLoading(false); }
    }, 550);
    return () => clearTimeout(t);
  }, [cfgKey, previewDocType, entityId, sample?.source_id, previewNonce]); // eslint-disable-line

  const patch = useCallback((k, v) => setConfig((c) => ({ ...(c || {}), [k]: v })), []);
  const patchBranding = useCallback((k, v) => setBranding((b) => ({ ...(b || {}), [k]: v })), []);

  const onLogoFile = useCallback((file) => {
    if (file.size > 1024 * 1024) { setBrandingErr("Ukuran logo maksimal 1 MB."); return; }
    const reader = new FileReader();
    reader.onload = () => { setNewLogo(reader.result); setBrandingErr(""); };
    reader.readAsDataURL(file);
  }, []);
  const onRemoveLogo = useCallback(() => {
    setNewLogo("");                                   // "" = minta hapus saat simpan
    setBranding((b) => ({ ...(b || {}), logo_src: "" }));
  }, []);
  // Gambar kop / footer / cap — null = hapus, dataURL = ganti (disimpan bersama branding)
  const onImageFile = useCallback((key, file) => {
    if (file === null) { setNewImages((m) => ({ ...m, [key]: "" })); return; }
    if (file.size > 1024 * 1024) { setBrandingErr("Ukuran gambar maksimal 1 MB."); return; }
    const reader = new FileReader();
    reader.onload = () => { setNewImages((m) => ({ ...m, [key]: reader.result })); setBrandingErr(""); };
    reader.readAsDataURL(file);
  }, []);

  async function saveTemplate() {
    if (!docType || !config) return;
    setSavingTpl(true); setErr("");
    try {
      const r = await axios.put(`${API}/pdf/templates/${docType}`, { config });
      setConfig(r.data.config); setMeta(r.data.meta || null);
      flashMsg(isDefault ? "Bawaan seluruh dokumen tersimpan — semua jenis yang tidak menimpanya ikut berubah." : "Template tersimpan (hanya perbedaan dari bawaan yang disimpan).");
      loadTargets();
    } catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan template."); }
    finally { setSavingTpl(false); }
  }

  async function saveBranding() {
    if (!entityId) return;
    setSavingBrand(true); setBrandingErr(""); setBrandingMsg("");
    try {
      const payload = {
        company_name: branding?.company_name || "",
        tagline: branding?.tagline || "",
        address: branding?.address || "",
        phone: branding?.phone || "",
        email: branding?.email || "",
        website: branding?.website || "",
        npwp: branding?.npwp || "",
      };
      if (newLogo !== null) payload.logo_b64 = newLogo; // data-url atau "" (hapus)
      Object.entries(newImages).forEach(([k, v]) => { payload[k] = v; });
      const r = await axios.put(`${API}/pdf/branding/${entityId}`, payload);
      setBranding(r.data); setNewLogo(null); setNewImages({});
      setBrandingMsg("Branding tersimpan.");
      setPreviewNonce((n) => n + 1);                  // segarkan pratinjau (branding server-side)
    } catch (e) { setBrandingErr(e.response?.data?.detail || "Gagal menyimpan branding."); }
    finally { setSavingBrand(false); }
  }

  async function resetDefaults() {
    // Pola sipro: reset = BUANG override di server; dokumen yang sudah terbit tidak berubah.
    const ok = await askConfirm({
      title: isDefault ? "Kembalikan bawaan seluruh dokumen ke setelan pabrik?" : `Buang setelan khusus "${docTypes.find((d) => d.doc_type === docType)?.label || docType}"?`,
      description: isDefault ? "Semua jenis dokumen yang tidak menimpanya akan kembali ke gaya pabrik. Dokumen yang sudah terbit tidak berubah."
        : "Jenis dokumen ini akan kembali mengikuti bawaan seluruh dokumen. Dokumen yang sudah terbit tidak berubah.",
      confirmLabel: "Kembalikan", danger: true });
    if (!ok) return;
    try {
      const r = await axios.delete(`${API}/pdf/templates/${docType}`);
      setConfig(r.data.config); setMeta(r.data.meta || null);
      flashMsg("Dikembalikan ke bawaan."); loadTargets();
    } catch (e) { setErr(e.response?.data?.detail || "Gagal mengembalikan ke bawaan."); }
  }

  async function downloadPdf() {
    if (!sample?.source_id) return;
    setDownloading(true); setErr("");
    try {
      const r = await axios.get(`${API}/pdf/render/${previewDocType}/${sample.source_id}`, {
        params: { format: "pdf", entity_id: entityId || sample.entity_id, download: true },
        responseType: "blob",
      });
      const blobUrl = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = blobUrl; a.download = `${previewDocType}-${sample.number || sample.source_id}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(blobUrl);
      flashMsg("PDF diunduh.");
    } catch (e) { setErr("Gagal mengunduh PDF."); }
    finally { setDownloading(false); }
  }

  const hasSample = !!(sample && sample.source_id);

  return (
    <div className="grid gap-4" data-testid="pdf-template-designer">
      {/* Toolbar */}
      <section className="section-card">
        <div className="section-body flex flex-wrap items-end gap-3">
          <div className="grid gap-1">
            <label className="kicker flex items-center gap-1"><FileText size={12} /> Jenis Dokumen</label>
            <KNSelect value={docType} onValueChange={setDocType} options={docTypeOptions}
              className="field !w-[240px]" searchable placeholder="Pilih dokumen…" data-testid="pdf-doctype-select" />
          </div>
          <div className="grid gap-1">
            <label className="kicker">Entitas (PT)</label>
            <KNSelect value={entityId} onValueChange={setEntityId} options={entityOptions}
              className="field !w-[220px]" placeholder="Pilih entitas…" data-testid="pdf-entity-select" />
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <button className="btn-secondary flex items-center gap-1.5" onClick={resetDefaults} data-testid="pdf-reset-default" disabled={!meta?.customized}
              title={meta?.customized ? "Buang setelan & kembali ke bawaan" : "Belum ada setelan khusus"}>
              <RotateCcw size={14} /> {isDefault ? "Setelan Pabrik" : "Ikuti Bawaan"}
            </button>
            <button className="btn-secondary flex items-center gap-1.5" onClick={downloadPdf}
              disabled={downloading || !hasSample} data-testid="pdf-download">
              {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} Unduh PDF
            </button>
            <button className="btn-primary flex items-center gap-1.5" onClick={saveTemplate}
              disabled={savingTpl || !config} data-testid="pdf-save-template">
              {savingTpl ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Simpan Template
            </button>
          </div>
        </div>
        <div className="px-4 pb-3 flex flex-wrap items-center gap-2 text-[11.5px]" data-testid="pdf-layer-info">
          <Layers size={13} className="text-[#0058CC]" />
          {isDefault ? (
            <span className="text-[#3C3C43]">Gaya & kop di sini dipakai <b>SEMUA</b> dokumen. Pilih jenis dokumen untuk menimpanya (mis. kolom tanda tangan Surat Jalan berbeda dari Faktur).</span>
          ) : (
            <span className="text-[#3C3C43]">Hanya <b>perbedaan</b> dari bawaan yang disimpan untuk jenis ini{meta?.override_keys?.length ? <>: <span className="font-mono text-[10.5px]">{meta.override_keys.join(", ")}</span></> : " — saat ini mengikuti bawaan sepenuhnya"}.</span>
          )}
          {meta?.customized && <span className="ml-auto rounded-full bg-[#EAF2FF] px-2 py-0.5 text-[10.5px] font-semibold text-[#0058CC]" data-testid="pdf-meta-version">v{meta.version} · {String(meta.updated_at || "").slice(0, 16).replace("T", " ")} · {meta.updated_by}</span>}
        </div>
        {(msg || err) && (
          <div className="px-4 pb-3">
            {msg && <div className="notice-bar success !py-1.5" data-testid="pdf-msg"><span className="text-[11.5px]">{msg}</span></div>}
            {err && <div className="notice-bar danger !py-1.5" data-testid="pdf-err"><span className="text-[11.5px]">{err}</span></div>}
          </div>
        )}
      </section>

      {/* Editor + Preview */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,440px)_minmax(0,1fr)] items-start">
        {config ? (
          <PdfEditorTabs
            config={config} patch={patch}
            branding={branding} patchBranding={patchBranding}
            onLogoFile={onLogoFile} onRemoveLogo={onRemoveLogo} onSaveBranding={saveBranding}
            savingBrand={savingBrand} brandingMsg={brandingMsg} brandingErr={brandingErr}
            newLogoPreview={newLogo}
            onImageFile={onImageFile} newImages={newImages} placeholders={placeholders}
            defaultEffective={defaultEffective} isDefault={isDefault}
          />
        ) : (
          <section className="section-card"><div className="section-body text-[12px] text-[#9A9BA3] py-6">Memuat konfigurasi…</div></section>
        )}

        {/* Preview pane */}
        <section className="section-card" data-testid="pdf-preview-pane">
          <div className="section-head flex items-center justify-between">
            <h2 className="text-[13px] font-bold flex items-center gap-2">
              Pratinjau{isDefault && <span className="text-[10.5px] font-normal text-[#9A9BA3]">(contoh: {docTypes.find((d) => d.doc_type === previewDocType)?.label || previewDocType})</span>}
              {sample?.number && <span className="rounded-full bg-[#EAF2FF] px-2 py-0.5 text-[10.5px] font-semibold text-[#0058CC]">{sample.number}</span>}
              {previewLoading && <Loader2 size={13} className="animate-spin text-[#0058CC]" />}
            </h2>
            <button className="btn-secondary flex items-center gap-1.5 !py-1" onClick={() => setPreviewNonce((n) => n + 1)}
              disabled={!hasSample} data-testid="pdf-preview-refresh">
              <RefreshCw size={13} /> Segarkan
            </button>
          </div>
          <div className="section-body">
            {!hasSample ? (
              <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[#D6D7DC] bg-[#FAFBFC] py-16 text-center">
                <FileWarning size={26} className="text-[#C4C5CC]" />
                <p className="text-[12.5px] font-semibold text-[#6B6B73]">Belum ada data {sample?.label || "dokumen"} untuk entitas ini</p>
                <p className="text-[11.5px] text-[#9A9BA3] max-w-[320px]">Buat dokumen dulu, atau pilih entitas/jenis dokumen lain untuk melihat pratinjau.</p>
              </div>
            ) : previewError ? (
              <div className="notice-bar danger" data-testid="pdf-preview-error"><span className="text-[12px]">{previewError}</span></div>
            ) : (
              <iframe
                title="Pratinjau PDF"
                srcDoc={previewHtml}
                data-testid="pdf-preview-frame"
                sandbox="allow-same-origin"
                className="w-full rounded-lg border border-[#E5E6EB] bg-white"
                style={{ height: "78vh" }}
              />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
