/**
 * DesignRequestCreateModal — **Buat Permintaan Desain** (pop-up, 3 bagian).
 *
 * Sinkron dengan Design Studio: yang diminta dinyatakan dengan **Kategori Pattern** +
 * **Kategori Design** (master yang SAMA dengan form "Desain Baru"), sehingga saat desainer
 * menekan "Buat desain dari permintaan" kode desain terbentuk otomatis tanpa input ulang.
 */
import { useMemo, useState } from "react";
import { CalendarClock, ClipboardList, Palette, UserRound } from "lucide-react";
import FormModal from "../../components/FormModal";
import KNSelect from "../../components/KNSelect";
import KNDatePicker from "../../components/KNDatePicker";
import PantoneFinder, { ColorChip } from "../../components/PantoneFinder";
import ReferenceGallery from "./ReferenceGallery";
import { apiText, createDesignRequest, uploadReference } from "./designRequestsApi";

const EMPTY = {
  source: "internal", so_id: "", category_code: "", design_category_code: "", brief: "",
  due_date: "", assigned_to: "", line_code: "",
};

function Section({ icon: Icon, step, title, hint, children, testId }) {
  return (
    <section data-testid={testId} className="rounded-xl border border-[#EFF0F2] bg-[#FAFBFC] p-3">
      <div className="mb-2.5 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#6B219A] text-[10.5px] font-bold text-white">{step}</span>
        <Icon size={13} className="text-[#6B219A]" />
        <div>
          <p className="text-[12px] font-bold text-[#1C1C1E]">{title}</p>
          {hint && <p className="text-[10.5px] text-[#8E8E93]">{hint}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

export default function DesignRequestCreateModal({ open, onClose, onCreated, meta, orders = [] }) {
  const [form, setForm] = useState(EMPTY);
  const [colors, setColors] = useState([]);
  const [refs, setRefs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (patch) => setForm((f) => ({ ...f, ...patch }));

  const designerOptions = [{ value: "", label: "— Belum ditugaskan (atasan menugaskan nanti) —" }].concat(
    (meta?.designers || []).map((d) => ({ value: d.id, label: d.has_account ? d.name : `${d.name} (belum punya akun)` })));
  const sourceOptions = (meta?.sources || []).map((s) => ({ value: s.id, label: s.label }));
  const orderOptions = [{ value: "", label: "— Pilih pesanan —" }].concat(
    orders.map((o) => ({ value: o.id, label: `${o.number || o.order_number || o.id} · ${o.customer_name || ""}` })));
  const patternOpts = useMemo(() => (meta?.categories?.pattern || []).map((c) => ({ value: c.code, label: `${c.code} — ${c.name}` })), [meta]);
  const designOpts = useMemo(() => (meta?.categories?.design || []).map((c) => ({ value: c.code, label: `${c.code} — ${c.name}` })), [meta]);

  const briefOk = (form.brief || "").trim().length >= 5;
  const catsOk = !!form.category_code && !!form.design_category_code;
  const soOk = form.source !== "so" || !!form.so_id;

  async function simpan() {
    setBusy(true); setErr("");
    try {
      const doc = await createDesignRequest({ ...form, target_type: "pattern", color_targets: colors, submit_now: true });
      let gagal = 0;
      for (const f of refs) {
        try { await uploadReference(doc.id, f); } catch { gagal += 1; }
      }
      if (gagal) setErr(`${gagal} gambar referensi gagal diunggah — tambahkan lagi dari rincian ${doc.number}.`);
      onCreated?.(doc);
      setForm(EMPTY); setColors([]); setRefs([]);
    } catch (e) {
      setErr(apiText(e, "Gagal membuat permintaan desain."));
    } finally { setBusy(false); }
  }

  return (
    <FormModal
      open={open} onClose={onClose}
      title="Permintaan Desain Baru"
      subtitle="Tentukan kategori seperti di Design Studio, tulis brief, lalu (opsional) tugaskan"
      icon={Palette} size="lg" testId="dsr-create-modal"
      onSubmit={simpan} submitLabel={form.assigned_to ? "Ajukan & Tugaskan" : "Ajukan Permintaan"} busy={busy} error={err}
      submitDisabled={!briefOk || !catsOk || !soOk}
      submitTestId="dsr-create-submit"
    >
      <div className="grid gap-3">
        <Section step={1} icon={ClipboardList} title="Untuk siapa & dari mana" testId="dsr-section-source">
          <div className="grid gap-2.5 sm:grid-cols-2">
            <label className="block">
              <span className="field-label">Sumber permintaan</span>
              <KNSelect data-testid="dsr-source-select" value={form.source}
                onValueChange={(v) => set({ source: v, so_id: v === "so" ? form.so_id : "" })}
                options={sourceOptions} className="field" placeholder="Pilih sumber" />
            </label>
            {form.source === "so" ? (
              <label className="block">
                <span className="field-label">Pesanan pelanggan *</span>
                <KNSelect data-testid="dsr-so-select" value={form.so_id}
                  onValueChange={(v) => set({ so_id: v })} options={orderOptions}
                  className="field" placeholder="Pilih pesanan" searchable />
              </label>
            ) : (
              <p className="self-end pb-2 text-[10.5px] text-[#8E8E93]">
                Pilih “Dari pesanan pelanggan” untuk menautkan permintaan ke SO — pelanggan & nomor pesanan ikut otomatis.
              </p>
            )}
          </div>
        </Section>

        <Section step={2} icon={Palette} title="Apa yang harus dibuat"
          hint="Kategori sama dengan Design Studio — kode desain (mis. SRI-SLR-AO-001) terbentuk otomatis saat desainer mulai." testId="dsr-section-what">
          <div className="grid gap-2.5 sm:grid-cols-2">
            <label className="block">
              <span className="field-label">Kategori Pattern *</span>
              <KNSelect data-testid="dsr-category-select" value={form.category_code}
                onValueChange={(v) => set({ category_code: v })} options={patternOpts}
                className="field" placeholder="salur / batik / bunga / polkadot…" searchable />
            </label>
            <label className="block">
              <span className="field-label">Kategori Design *</span>
              <KNSelect data-testid="dsr-dcategory-select" value={form.design_category_code}
                onValueChange={(v) => set({ design_category_code: v })} options={designOpts}
                className="field" placeholder="allover / pinggiran" />
            </label>
            <label className="block sm:col-span-2">
              <span className="field-label">Brief (apa yang harus dibuat) *</span>
              <textarea data-testid="dsr-brief-input" className="field" rows={3}
                placeholder="mis. Motif batik pesisir untuk katalog lebaran — 3 alternatif warna, repeat ±32 cm."
                value={form.brief} onChange={(e) => set({ brief: e.target.value })} />
              <span className={`mt-0.5 block text-right text-[10px] ${briefOk ? "text-[#8E8E93]" : "text-[#A8221A]"}`}>
                {briefOk ? `${form.brief.trim().length} karakter` : "minimal satu kalimat (≥ 5 karakter)"}
              </span>
            </label>
            <div className="sm:col-span-2">
              <span className="field-label">Warna target (opsional)</span>
              <PantoneFinder triggerTestId="dsr-color-picker" label="Tambah warna dari Pustaka Warna…"
                onSelect={(c) => setColors((prev) => (prev.some((p) => p.code === c.code) ? prev
                  : prev.concat([{ color_id: c.id || "", code: c.code || "", name: c.name || "", hex: c.hex || "" }])))} />
              {colors.length > 0 && (
                <div data-testid="dsr-color-chips" className="mt-1.5 flex flex-wrap gap-1.5">
                  {colors.map((c) => (
                    <span key={c.code} className="inline-flex items-center gap-1 rounded-full border border-[#EFF0F2] bg-white px-2 py-0.5 text-[10.5px]">
                      <ColorChip hex={c.hex} size={12} /> {c.code} · {c.name}
                      <button type="button" className="text-[#9A9BA3]" data-testid={`dsr-color-remove-${c.code}`}
                        onClick={() => setColors((prev) => prev.filter((p) => p.code !== c.code))}>×</button>
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="sm:col-span-2">
              <ReferenceGallery testId="dsr-create-refs" localFiles={refs} canEdit
                onPick={(list) => setRefs((p) => p.concat(list.filter((f) => f.type.startsWith("image/"))))}
                onRemove={(_, i) => setRefs((p) => p.filter((__, j) => j !== i))} />
              <p className="mt-1 text-[10px] text-[#8E8E93]">Gambar ikut otomatis ke tab <b>Referensi</b> pada desain yang dibuat desainer dari permintaan ini.</p>
            </div>
          </div>
        </Section>

        <Section step={3} icon={UserRound} title="Siapa & kapan" hint="Boleh dikosongkan — atasan bisa menugaskan dari papan." testId="dsr-section-who">
          <div className="grid gap-2.5 sm:grid-cols-2">
            <label className="block">
              <span className="field-label">Ditugaskan ke</span>
              <KNSelect data-testid="dsr-assignee-select" value={form.assigned_to}
                onValueChange={(v) => set({ assigned_to: v })} options={designerOptions}
                className="field" placeholder="Belum ditugaskan" searchable />
            </label>
            <label className="block">
              <span className="field-label"><CalendarClock size={10} className="inline" /> Tenggat</span>
              <KNDatePicker data-testid="dsr-due-input" value={form.due_date} onChange={(v) => set({ due_date: v })} placeholder="Pilih tenggat" />
            </label>
          </div>
        </Section>
      </div>
    </FormModal>
  );
}
