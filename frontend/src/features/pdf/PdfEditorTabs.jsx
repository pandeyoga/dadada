// PdfEditorTabs — panel editor (6 tab) untuk konfigurasi template PDF + branding entitas.
// Semua kontrol memakai kelas/komponen existing (field/form-input/btn-*, KNSelect, Switch).
import { useRef } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import KNSelect from "../../components/KNSelect";
import {
  PAPER_SIZES, ORIENTATIONS, FONT_FAMILIES, FONT_SIZES, COLOR_PRESETS, EDITOR_TABS,
  HEADER_MODES, FOOTER_MODES, TABLE_GRIDS, SECTION_LABELS,
} from "./pdfConstants";
import PdfScriptTab from "./PdfScriptTab";
import { Plus, Trash2, Upload, ImageOff, Save, Loader2, Info } from "lucide-react";

function Toggle({ label, checked, onChange, testId, hint }) {
  return (
    <label className="flex items-center justify-between gap-3 rounded-lg border border-[#EDEEF1] px-3 py-2">
      <span className="text-[12.5px] font-medium">{label}{hint && <span className="block text-[10.5px] font-normal text-[#9A9BA3]">{hint}</span>}</span>
      <Switch checked={!!checked} onCheckedChange={onChange} data-testid={testId} />
    </label>
  );
}

function ImageUpload({ label, hint, src, onFile, onRemove, testId }) {
  const ref = useRef(null);
  return (
    <Row label={label} hint={hint}>
      <div className="flex items-center gap-3">
        <div className="flex h-16 min-w-[64px] max-w-[220px] items-center justify-center overflow-hidden rounded-md border border-[#E5E6EB] bg-[#F7F8FA] px-1">
          {src ? <img src={src} alt={label} className="max-h-full max-w-full object-contain" /> : <ImageOff size={20} className="text-[#C4C5CC]" />}
        </div>
        <div className="flex flex-col gap-1">
          <input ref={ref} type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} data-testid={`${testId}-input`} />
          <button type="button" className="btn-secondary flex items-center gap-1.5" onClick={() => ref.current?.click()} data-testid={`${testId}-upload`}><Upload size={13} /> Unggah</button>
          {src && <button type="button" className="text-[11px] text-[#C0392B] hover:underline" onClick={onRemove} data-testid={`${testId}-remove`}>Hapus</button>}
        </div>
      </div>
    </Row>
  );
}

function Row({ label, hint, children }) {
  return (
    <div className="grid gap-1">
      <label className="text-[11px] font-bold uppercase tracking-[0.03em] text-[#6B6B73]">{label}</label>
      {children}
      {hint && <p className="text-[10.5px] text-[#9A9BA3] leading-snug">{hint}</p>}
    </div>
  );
}

function ColorField({ value, onChange, testId }) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="color" value={value || "#0058CC"} onChange={(e) => onChange(e.target.value)}
        className="h-9 w-12 cursor-pointer rounded-md border border-[#D6D7DC] bg-white p-0.5"
        data-testid={testId}
        aria-label="Pilih warna"
      />
      <input
        type="text" value={value || ""} onChange={(e) => onChange(e.target.value)}
        className="form-input !w-[110px] font-mono text-[12px]"
        data-testid={testId ? `${testId}-hex` : undefined}
      />
      <div className="flex items-center gap-1">
        {COLOR_PRESETS.map((c) => (
          <button key={c} type="button" onClick={() => onChange(c)} title={c}
            className="h-5 w-5 rounded-full border border-black/10 transition-transform hover:scale-110"
            style={{ background: c }} />
        ))}
      </div>
    </div>
  );
}

export default function PdfEditorTabs({
  config, patch, branding, patchBranding,
  onLogoFile, onRemoveLogo, onSaveBranding, savingBrand, brandingMsg, brandingErr, newLogoPreview,
  onImageFile, newImages = {}, placeholders = [], defaultEffective = null, isDefault = false,
}) {
  const fileRef = useRef(null);
  const cf = config || {};
  const patchNested = (group, k, v) => patch(group, { ...(cf[group] || {}), [k]: v });
  const tb = cf.table || {};
  const sec = cf.sections || {};
  // Penanda "berbeda dari bawaan" per kunci (pola override sipro) — hanya di jenis dokumen.
  const differs = (k) => !isDefault && defaultEffective && JSON.stringify(cf[k]) !== JSON.stringify(defaultEffective[k]);
  const Diff = ({ k }) => differs(k) ? <span className="ml-1 rounded bg-[#FFF3D6] px-1 text-[9px] font-bold text-[#8C4A00]" title="Menimpa bawaan seluruh dokumen">menimpa</span> : null;
  const img = (key) => (newImages[key] !== undefined ? newImages[key] : branding?.[`${key.replace("_b64", "")}_src`] || "");

  // ── custom fields helpers ───────────────────────────────
  const customFields = cf.custom_fields || [];
  const setCustom = (arr) => patch("custom_fields", arr);
  const addCustom = () => setCustom([...customFields, { label: "", value: "" }]);
  const updCustom = (i, k, v) => setCustom(customFields.map((r, idx) => (idx === i ? { ...r, [k]: v } : r)));
  const delCustom = (i) => setCustom(customFields.filter((_, idx) => idx !== i));

  // ── signature slots helpers ─────────────────────────────
  const sigs = cf.signature_slots || [];
  const setSigs = (arr) => patch("signature_slots", arr);
  const addSig = () => setSigs([...sigs, { label: "", role: "", name: "", show_stamp: false }]);
  const updSig = (i, k, v) => setSigs(sigs.map((r, idx) => (idx === i ? { ...r, [k]: v } : r)));
  const delSig = (i) => setSigs(sigs.filter((_, idx) => idx !== i));

  // ── hidden fields (comma separated) ─────────────────────
  const hiddenStr = (cf.hidden_fields || []).join(", ");
  const setHidden = (str) => patch("hidden_fields", str.split(",").map((s) => s.trim()).filter(Boolean));

  const logoSrc = newLogoPreview || branding?.logo_src || "";

  return (
    <section className="section-card" data-testid="pdf-editor">
      <Tabs defaultValue="layout" className="w-full">
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1.5 bg-transparent p-2 border-b border-[#EDEEF1]">
          {EDITOR_TABS.map((t) => (
            <TabsTrigger key={t.id} value={t.id} data-testid={`pdf-tab-${t.id}`}
              className="rounded-full border border-[#E5E5EA] bg-[#F5F5F7] px-3.5 py-1.5 text-[12.5px] font-medium text-[#6B6B73] shadow-none data-[state=active]:border-[#007AFF] data-[state=active]:bg-[#007AFF] data-[state=active]:text-white data-[state=active]:shadow-none">
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <div className="section-body grid gap-3">
          {/* ── NASKAH (placeholder) ───────────────────────── */}
          <TabsContent value="naskah" className="mt-0">
            <PdfScriptTab config={cf} patch={patch} placeholders={placeholders} />
          </TabsContent>

          {/* ── LAYOUT ─────────────────────────────────────── */}
          <TabsContent value="layout" className="grid gap-3 mt-0">
            <Row label={<>Mode kop surat<Diff k="header_mode" /></>} hint="'Tanpa kop' untuk kertas berkop cetakan sendiri.">
              <KNSelect value={cf.header_mode || "system"} onValueChange={(v) => patch("header_mode", v)} options={HEADER_MODES} className="field" data-testid="pdf-header-mode" />
            </Row>
            <Row label={<>Mode footer<Diff k="footer_mode" /></>}>
              <KNSelect value={cf.footer_mode || "text"} onValueChange={(v) => patch("footer_mode", v)} options={FOOTER_MODES} className="field" data-testid="pdf-footer-mode" />
            </Row>
            <Row label={<>Bagian dokumen<Diff k="sections" /></>} hint="Sembunyikan bagian — angka tetap milik mesin, hanya tidak dicetak.">
              <div className="grid gap-1.5">
                {SECTION_LABELS.map(([k, lbl]) => (
                  <Toggle key={k} label={lbl} checked={sec[k] !== false} onChange={(v) => patchNested("sections", k, v)} testId={`pdf-section-${k}`} />
                ))}
              </div>
            </Row>
            <Row label="Ukuran Kertas">
              <KNSelect value={cf.paper_size || "A4"} onValueChange={(v) => patch("paper_size", v)}
                options={PAPER_SIZES} className="field" data-testid="pdf-paper-size" />
            </Row>
            <Row label="Orientasi">
              <KNSelect value={cf.orientation || "portrait"} onValueChange={(v) => patch("orientation", v)}
                options={ORIENTATIONS} className="field" data-testid="pdf-orientation" />
            </Row>
            <Row label="Margin (mm)" hint="Atas · Kanan · Bawah · Kiri">
              <div className="grid grid-cols-4 gap-2">
                {["margin_top", "margin_right", "margin_bottom", "margin_left"].map((k) => (
                  <input key={k} type="number" min="0" max="60" className="form-input text-center"
                    value={cf[k] ?? 0} onChange={(e) => patch(k, Number(e.target.value))}
                    data-testid={`pdf-${k}`} />
                ))}
              </div>
            </Row>
            <Row label="Judul Dokumen (override)" hint="Kosongkan untuk memakai judul bawaan dokumen.">
              <input type="text" className="form-input" value={cf.title_override || ""}
                onChange={(e) => patch("title_override", e.target.value)}
                placeholder="mis. SURAT PESANAN" data-testid="pdf-title-override" />
            </Row>
            <label className="flex items-center justify-between gap-3 rounded-lg border border-[#EDEEF1] px-3 py-2">
              <span className="text-[12.5px] font-medium">Tampilkan logo perusahaan</span>
              <Switch checked={!!cf.show_logo} onCheckedChange={(v) => patch("show_logo", v)} data-testid="pdf-show-logo" />
            </label>
            <label className="flex items-center justify-between gap-3 rounded-lg border border-[#EDEEF1] px-3 py-2">
              <span className="text-[12.5px] font-medium">Tampilkan “terbilang” (nominal huruf)</span>
              <Switch checked={!!cf.show_terbilang} onCheckedChange={(v) => patch("show_terbilang", v)} data-testid="pdf-show-terbilang" />
            </label>
          </TabsContent>

          {/* ── KOP SURAT (branding per entitas) ───────────── */}
          <TabsContent value="kop" className="grid gap-3 mt-0">
            <div className="flex items-start gap-2 rounded-lg bg-[#EFF4FF] px-3 py-2 text-[11.5px] text-[#0058CC]">
              <Info size={14} className="mt-0.5 shrink-0" />
              <span>Kop surat disimpan per <b>entitas (PT)</b>. Simpan branding untuk melihat perubahan di pratinjau.</span>
            </div>
            <Row label="Nama Perusahaan">
              <input type="text" className="form-input" value={branding?.company_name || ""}
                onChange={(e) => patchBranding("company_name", e.target.value)} data-testid="pdf-brand-name" />
            </Row>
            <Row label="Alamat">
              <textarea className="form-input min-h-[60px]" value={branding?.address || ""}
                onChange={(e) => patchBranding("address", e.target.value)} data-testid="pdf-brand-address" />
            </Row>
            <Row label="Tagline (opsional)">
              <input type="text" className="form-input" value={branding?.tagline || ""} onChange={(e) => patchBranding("tagline", e.target.value)} data-testid="pdf-brand-tagline" placeholder="mis. Tekstil Nusantara Berkualitas" />
            </Row>
            <div className="grid grid-cols-2 gap-2">
              <Row label="Telepon">
                <input type="text" className="form-input" value={branding?.phone || ""}
                  onChange={(e) => patchBranding("phone", e.target.value)} data-testid="pdf-brand-phone" />
              </Row>
              <Row label="NPWP">
                <input type="text" className="form-input" value={branding?.npwp || ""}
                  onChange={(e) => patchBranding("npwp", e.target.value)} data-testid="pdf-brand-npwp" />
              </Row>
              <Row label="Email">
                <input type="text" className="form-input" value={branding?.email || ""} onChange={(e) => patchBranding("email", e.target.value)} data-testid="pdf-brand-email" />
              </Row>
              <Row label="Website">
                <input type="text" className="form-input" value={branding?.website || ""} onChange={(e) => patchBranding("website", e.target.value)} data-testid="pdf-brand-website" />
              </Row>
            </div>
            <ImageUpload label="Gambar kop (mode 'Gambar kop')" hint="PNG/JPG lebar penuh, ≤ 1 MB. Dipakai bila Layout → Mode kop = Gambar." src={img("header_image_b64")} onFile={(f) => onImageFile("header_image_b64", f)} onRemove={() => onImageFile("header_image_b64", null)} testId="pdf-brand-header-image" />
            <ImageUpload label="Gambar footer (mode 'Gambar footer')" hint="Strip bawah halaman, ≤ 1 MB." src={img("footer_image_b64")} onFile={(f) => onImageFile("footer_image_b64", f)} onRemove={() => onImageFile("footer_image_b64", null)} testId="pdf-brand-footer-image" />
            <ImageUpload label="Cap perusahaan (stempel)" hint="PNG transparan; muncul di slot tanda tangan yang mencentang 'Cap'." src={img("stamp_b64")} onFile={(f) => onImageFile("stamp_b64", f)} onRemove={() => onImageFile("stamp_b64", null)} testId="pdf-brand-stamp" />
            <Row label="Logo" hint="PNG/JPG, disarankan < 200 KB. Disimpan sebagai base64.">
              <div className="flex items-center gap-3">
                <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-md border border-[#E5E6EB] bg-[#F7F8FA]">
                  {logoSrc ? <img src={logoSrc} alt="logo" className="max-h-full max-w-full object-contain" /> : <ImageOff size={20} className="text-[#C4C5CC]" />}
                </div>
                <div className="flex flex-col gap-1">
                  <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
                    onChange={(e) => e.target.files?.[0] && onLogoFile(e.target.files[0])} data-testid="pdf-brand-logo-input" />
                  <button type="button" className="btn-secondary flex items-center gap-1.5"
                    onClick={() => fileRef.current?.click()} data-testid="pdf-brand-logo-upload">
                    <Upload size={13} /> Unggah Logo
                  </button>
                  {logoSrc && <button type="button" className="text-[11px] text-[#C0392B] hover:underline" onClick={onRemoveLogo} data-testid="pdf-brand-logo-remove">Hapus logo</button>}
                </div>
              </div>
            </Row>
            <div className="flex items-center gap-2 pt-1">
              <button className="btn-primary flex items-center gap-1.5" onClick={onSaveBranding} disabled={savingBrand} data-testid="pdf-brand-save">
                {savingBrand ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Simpan Branding
              </button>
              {brandingMsg && <span className="text-[11.5px] font-semibold text-[#1F7A45]">{brandingMsg}</span>}
              {brandingErr && <span className="text-[11.5px] font-semibold text-[#C0392B]">{brandingErr}</span>}
            </div>
          </TabsContent>

          {/* ── FONT & WARNA ───────────────────────────────── */}
          <TabsContent value="typografi" className="grid gap-3 mt-0">
            <Row label="Font">
              <KNSelect value={cf.font_family || "'DejaVu Sans'"} onValueChange={(v) => patch("font_family", v)}
                options={FONT_FAMILIES} className="field" data-testid="pdf-font-family" />
            </Row>
            <Row label="Ukuran Font Dasar">
              <KNSelect value={String(cf.font_size || 10)} onValueChange={(v) => patch("font_size", Number(v))}
                options={FONT_SIZES} className="field !w-[140px]" data-testid="pdf-font-size" />
            </Row>
            <Row label="Warna Utama" hint="Judul, garis kop & header tabel.">
              <ColorField value={cf.color_primary} onChange={(v) => patch("color_primary", v)} testId="pdf-color-primary" />
            </Row>
            <Row label="Warna Aksen" hint="Teks isi & label.">
              <ColorField value={cf.color_accent} onChange={(v) => patch("color_accent", v)} testId="pdf-color-accent" />
            </Row>
          </TabsContent>

          {/* ── TABEL (gaya tabel rincian) ─────────────────── */}
          <TabsContent value="tabel" className="grid gap-3 mt-0">
            <Row label={<>Garis tabel<Diff k="table" /></>} hint="Transparan cocok untuk kertas berkop dengan garis cetakan sendiri.">
              <KNSelect value={tb.grid || "full"} onValueChange={(v) => patchNested("table", "grid", v)} options={TABLE_GRIDS} className="field" data-testid="pdf-table-grid" />
            </Row>
            <Toggle label="Cetak nama kolom (kepala tabel)" checked={tb.show_header !== false} onChange={(v) => patchNested("table", "show_header", v)} testId="pdf-table-show-header" />
            <Toggle label="Kepala tabel berwarna aksen" checked={tb.header_fill !== false} onChange={(v) => patchNested("table", "header_fill", v)} testId="pdf-table-header-fill" />
            <Toggle label="Baris belang (zebra)" checked={!!tb.zebra} onChange={(v) => patchNested("table", "zebra", v)} testId="pdf-table-zebra" />
            <Toggle label="Sorot baris total" checked={tb.total_highlight !== false} onChange={(v) => patchNested("table", "total_highlight", v)} testId="pdf-table-total-highlight" />
            <div className="grid grid-cols-2 gap-2">
              <Row label="Ukuran huruf tabel (pt)">
                <input type="number" min="6" max="14" step="0.5" className="form-input" value={tb.font_size ?? 9} onChange={(e) => patchNested("table", "font_size", Number(e.target.value))} data-testid="pdf-table-font-size" />
              </Row>
              <Row label="Warna garis">
                <ColorField value={tb.grid_color || "#bbbbbb"} onChange={(v) => patchNested("table", "grid_color", v)} testId="pdf-table-grid-color" />
              </Row>
            </div>
          </TabsContent>

          {/* ── FIELD (custom + hidden) ────────────────────── */}
          <TabsContent value="field" className="grid gap-3 mt-0">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-[0.03em] text-[#6B6B73]">Field Tambahan</span>
              <button type="button" className="btn-secondary flex items-center gap-1" onClick={addCustom} data-testid="pdf-custom-add"><Plus size={13} /> Tambah</button>
            </div>
            {customFields.length === 0 && <p className="text-[11.5px] text-[#9A9BA3]">Belum ada field tambahan. Field ini muncul di bagian meta dokumen.</p>}
            <div className="grid gap-2">
              {customFields.map((r, i) => (
                <div key={i} className="flex items-center gap-2" data-testid={`pdf-custom-row-${i}`}>
                  <input className="form-input flex-1" placeholder="Label" value={r.label} onChange={(e) => updCustom(i, "label", e.target.value)} />
                  <input className="form-input flex-1" placeholder="Nilai" value={r.value} onChange={(e) => updCustom(i, "value", e.target.value)} />
                  <button type="button" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-[#EDEEF1] text-[#C0392B] transition-colors hover:bg-[#FDECEA]" onClick={() => delCustom(i)} data-testid={`pdf-custom-del-${i}`} aria-label="Hapus"><Trash2 size={15} /></button>
                </div>
              ))}
            </div>
            <Row label="Sembunyikan Field (meta)" hint="Daftar label meta yang disembunyikan, pisahkan dengan koma. mis: Termin, Referensi">
              <input className="form-input" value={hiddenStr} onChange={(e) => setHidden(e.target.value)} data-testid="pdf-hidden-fields" />
            </Row>
          </TabsContent>

          {/* ── TANDA TANGAN (slots) ───────────────────────── */}
          <TabsContent value="ttd" className="grid gap-3 mt-0">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-[0.03em] text-[#6B6B73]">Slot Tanda Tangan</span>
              <button type="button" className="btn-secondary flex items-center gap-1" onClick={addSig} data-testid="pdf-sig-add"><Plus size={13} /> Tambah Slot</button>
            </div>
            {sigs.length === 0 && <p className="text-[11.5px] text-[#9A9BA3]">Kosong = pakai slot tanda tangan bawaan dokumen. Tambahkan untuk override.</p>}
            <div className="grid gap-2">
              {sigs.map((r, i) => (
                <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto_auto] items-center gap-2" data-testid={`pdf-sig-row-${i}`}>
                  <input className="form-input" placeholder="Label (mis. Hormat kami)" value={r.label} onChange={(e) => updSig(i, "label", e.target.value)} />
                  <input className="form-input" placeholder="Peran (mis. finance)" value={r.role} onChange={(e) => updSig(i, "role", e.target.value)} />
                  <input className="form-input" placeholder="Nama" value={r.name} onChange={(e) => updSig(i, "name", e.target.value)} />
                  <label className="flex items-center gap-1 text-[10.5px] whitespace-nowrap" title="Tempel cap perusahaan di slot ini"><input type="checkbox" checked={!!r.show_stamp} onChange={(e) => updSig(i, "show_stamp", e.target.checked)} data-testid={`pdf-sig-stamp-${i}`} /> Cap</label>
                  <button type="button" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-[#EDEEF1] text-[#C0392B] transition-colors hover:bg-[#FDECEA]" onClick={() => delSig(i)} data-testid={`pdf-sig-del-${i}`} aria-label="Hapus"><Trash2 size={15} /></button>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* ── FOOTER / WATERMARK ─────────────────────────── */}
          <TabsContent value="footer" className="grid gap-3 mt-0">
            <Toggle label="Nomor halaman (Hal. 1 / 2)" checked={cf.show_page_numbers !== false} onChange={(v) => patch("show_page_numbers", v)} testId="pdf-show-page-numbers" />
            <Toggle label="Tempat & tanggal sebelum tanda tangan" hint="mis. 'Bandung, 03 Sep 2026'" checked={!!cf.show_place_date} onChange={(v) => patch("show_place_date", v)} testId="pdf-show-place-date" />
            {cf.show_place_date && <Row label="Tempat"><input className="form-input" value={cf.place || ""} onChange={(e) => patch("place", e.target.value)} placeholder="Bandung" data-testid="pdf-place" /></Row>}
            <Toggle label="Catatan meterai di slot tanda tangan pertama" checked={!!cf.show_materai} onChange={(v) => patch("show_materai", v)} testId="pdf-show-materai" />
            {cf.show_materai && <Row label="Teks meterai"><input className="form-input" value={cf.materai_note || ""} onChange={(e) => patch("materai_note", e.target.value)} data-testid="pdf-materai-note" /></Row>}
            <Toggle label="Catatan 'dihasilkan oleh sistem' di kaki dokumen" checked={!!cf.show_generated_note} onChange={(v) => patch("show_generated_note", v)} testId="pdf-show-generated-note" />
            <Row label="Teks Footer" hint="Muncul di bagian bawah setiap halaman.">
              <input className="form-input" value={cf.footer_text || ""} onChange={(e) => patch("footer_text", e.target.value)}
                placeholder="mis. Dokumen ini sah tanpa tanda tangan basah." data-testid="pdf-footer-text" />
            </Row>
            <Row label="Watermark" hint="Teks miring transparan di tengah halaman. Kosongkan untuk menonaktifkan.">
              <input className="form-input" value={cf.watermark_text || ""} onChange={(e) => patch("watermark_text", e.target.value)}
                placeholder="mis. SALINAN / LUNAS" data-testid="pdf-watermark-text" />
            </Row>
            {cf.watermark_text && <Row label={`Ketebalan watermark (${cf.watermark_opacity ?? 6}%)`}>
              <input type="range" min="1" max="40" value={cf.watermark_opacity ?? 6} onChange={(e) => patch("watermark_opacity", Number(e.target.value))} data-testid="pdf-watermark-opacity" className="w-full" />
            </Row>}
          </TabsContent>
        </div>
      </Tabs>
    </section>
  );
}
