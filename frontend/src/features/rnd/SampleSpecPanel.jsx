/**
 * SampleSpecPanel — blok SPESIFIKASI di rincian sample (1 sample = 1 spesifikasi).
 * Ada spesifikasi → ringkasan lengkap + ubah (MD, sebelum ACC). Belum ada (data lama) → peringatan + "Lengkapi spesifikasi".
 */
import { useEffect, useState } from "react";
import { AlertTriangle, ClipboardList, Pencil, Save } from "lucide-react";
import FormModal from "../../components/FormModal";
import KNSelect from "../../components/KNSelect";
import { formatCurrency } from "../../utils/formatters";
import axios, { API } from "../../services/apiClient";
import { listColors, listDesigns, patchSpec, sampleTypes as fetchTypes } from "./rndApi";
import { errMsg, SPEC_STATUS_META } from "./rndMeta";
import { Field, Footer } from "./RndField";
import SampleSpecFields, { EMPTY_SPEC, buildSpecPayload, specProblems } from "./SampleSpecFields";

export default function SampleSpecPanel({ sample, canEdit, onChanged }) {
  const spec = sample.spec || null;
  const [modal, setModal] = useState(""); // "complete" | "edit"
  const editable = canEdit && spec && ["draft", "review"].includes(spec.status);
  const t = spec?.target || {};
  const md = sample.master_data || {};

  return (
    <div className="section-card" data-testid="sample-spec-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]"><ClipboardList size={12} /> Spesifikasi produk target</p>
        {spec && (
          <span className="flex items-center gap-1.5">
            <span className="font-mono text-[11px] text-[#6B6B73]" data-testid="sample-spec-number">{spec.number}</span>
            <span className={`status-pill ${(SPEC_STATUS_META[spec.status] || {}).cls || "pill-muted"}`} data-testid="sample-spec-status">{(SPEC_STATUS_META[spec.status] || {}).label || spec.status}</span>
            {editable && <button className="secondary-button !px-2 !py-1 text-[10.5px]" data-testid="sample-spec-edit-button" onClick={() => setModal("edit")}><Pencil size={11} /> Ubah</button>}
          </span>
        )}
      </div>

      {!spec ? (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#F5C26B] bg-[#FFF8EE] px-3 py-2" data-testid="sample-spec-missing">
          <p className="flex items-center gap-1.5 text-[11.5px] text-[#8C4A00]"><AlertTriangle size={13} /> <b>Belum ada spesifikasi</b> — data lama. Tanpa spesifikasi, SKU produk tidak bisa lahir saat ACC.</p>
          {canEdit && <button className="primary-button !py-1.5 text-[11px]" data-testid="sample-spec-complete-button" onClick={() => setModal("complete")}>Lengkapi spesifikasi</button>}
        </div>
      ) : (
        <dl className="mt-2 grid gap-x-4 gap-y-1.5 text-[11.5px] sm:grid-cols-2 lg:grid-cols-3" data-testid="sample-spec-summary">
          <Row k="Induk produk">{md.template?.name || (spec.template_id ? spec.template_id : "— produk konsep mandiri")}</Row>
          <Row k="Kombinasi varian">{Object.keys(spec.variant_attrs || {}).length ? Object.entries(spec.variant_attrs).map(([a, v]) => `${a}: ${v}`).join(", ") : "—"}</Row>
          <Row k="Jenis kain">{t.fabric_type || "—"}</Row>
          <Row k="Gramasi">{t.gramasi ? `${t.gramasi} gsm` : "—"}</Row>
          <Row k="Lebar">{t.lebar ? `${t.lebar} cm` : "—"}</Row>
          <Row k="Satuan">{spec.base_unit || sample.unit || "—"}</Row>
          {(t.yarn_count || t.epi || t.ppi) && <Row k="Konstruksi">{[t.yarn_count && `${t.yarn_count}${t.yarn_count_system ? ` ${t.yarn_count_system}` : ""}`, t.epi && `EPI ${t.epi}`, t.ppi && `PPI ${t.ppi}`].filter(Boolean).join(" · ")}</Row>}
          <Row k="Warna target">{spec.color_target?.name ? `${spec.color_target.code} · ${spec.color_target.name}` : "—"}</Row>
          <Row k="Desain">{spec.design_code || sample.design_code ? `${spec.design_code || sample.design_code} v${spec.design_version || sample.design_version || 1}` : "—"}</Row>
          <Row k="Kain dasar">{spec.base_fabric_name || "—"}</Row>
          <Row k="SKU usulan">{spec.sku_hint || "otomatis saat ACC"}</Row>
          <Row k="Target harga">{Number(spec.target_price) > 0 ? formatCurrency(spec.target_price) : "—"}</Row>
          <Row k="Produk lahir">{spec.product_sku ? <b className="font-mono">{spec.product_sku}</b> : "belum (saat ACC pemenang)"}</Row>
          {spec.notes && <Row k="Catatan" wide>{spec.notes}</Row>}
        </dl>
      )}

      {modal === "complete" && <CompleteSpecModal sample={sample} onClose={() => setModal("")} onDone={() => { setModal(""); onChanged?.(); }} />}
      {modal === "edit" && <EditSpecModal spec={spec} onClose={() => setModal("")} onDone={() => { setModal(""); onChanged?.(); }} />}
    </div>
  );
}

function Row({ k, children, wide }) {
  return (
    <div className={`flex items-start justify-between gap-2 border-b border-[#F2F2F5] py-1 ${wide ? "sm:col-span-2 lg:col-span-3" : ""}`}>
      <dt className="shrink-0 text-[#6B6B73]">{k}</dt><dd className="text-right font-semibold text-[#1C1C1E]">{children}</dd>
    </div>
  );
}

function CompleteSpecModal({ sample, onClose, onDone }) {
  const [types, setTypes] = useState([]);
  const [colors, setColors] = useState([]);
  const [designs, setDesigns] = useState([]);
  const [catalog, setCatalog] = useState({});
  const [sp, setSp] = useState(EMPTY_SPEC);
  const [f, setF] = useState({ title: sample.title || "", unit: sample.unit || "meter", line_code: sample.line_code || "",
    color_id: sample.color_target?.color_id || "", design_id: sample.design_id || "", so_id: sample.so_id || "" });
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const sampleTypes = sample.sample_types || [];
  useEffect(() => {
    fetchTypes({}).then((r) => setTypes(Array.isArray(r) ? r : [])).catch(() => {});
    listColors().then((c) => setColors(Array.isArray(c) ? c : c?.items || [])).catch(() => {});
    listDesigns().then((d) => setDesigns(Array.isArray(d) ? d : d?.items || [])).catch(() => {});
  }, []);
  const problems = specProblems({ sp, catalog, f, sampleTypes, types });
  const save = async () => {
    setBusy(true); setErr("");
    try {
      await axios.post(`${API}/rnd/samples/${sample.id}/spec`, buildSpecPayload({ sp, catalog, f, sampleTypes }));
      onDone();
    } catch (e) { setErr(errMsg(e, "Gagal menyimpan spesifikasi.")); setBusy(false); }
  };
  return (
    <FormModal open onClose={onClose} size="lg" testId="sample-spec-complete-modal" icon={ClipboardList} error={err}
      title={`Lengkapi spesifikasi · ${sample.number}`} subtitle="Spesifikasi produk target untuk permintaan ini — wajib agar SKU bisa lahir saat ACC"
      footer={<Footer onClose={onClose} onConfirm={save} busy={busy} disabled={problems.length > 0} icon={Save} testId="sample-spec-complete-save" confirmLabel="Simpan spesifikasi" />}>
      <div className="grid gap-3">
        <SampleSpecFields sp={sp} setSp={setSp} catalog={catalog} setCatalog={setCatalog} f={f} set={set}
          sampleTypes={sampleTypes} types={types} colors={colors} designs={designs} testPrefix="complete-spec" />
        {problems.length > 0 && <p className="text-[11px] text-[#A8221A]" data-testid="complete-spec-problems">Belum lengkap: <b>{problems.join(", ")}</b>.</p>}
      </div>
    </FormModal>
  );
}

function EditSpecModal({ spec, onClose, onDone }) {
  const t = spec.target || {};
  const [v, setV] = useState({ fabric_type: t.fabric_type || "woven", gramasi: t.gramasi ?? "", lebar: t.lebar ?? "",
    sku_hint: spec.sku_hint || "", target_price: spec.target_price || "", notes: spec.notes || "" });
  const s = (k, val) => setV((p) => ({ ...p, [k]: val }));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const save = async () => {
    setBusy(true); setErr("");
    try {
      await patchSpec(spec.id, { target: { ...t, fabric_type: v.fabric_type, gramasi: v.gramasi === "" ? null : v.gramasi, lebar: v.lebar === "" ? null : v.lebar },
        sku_hint: v.sku_hint, target_price: v.target_price || 0, notes: v.notes });
      onDone();
    } catch (e) { setErr(errMsg(e, "Gagal mengubah spesifikasi.")); setBusy(false); }
  };
  return (
    <FormModal open onClose={onClose} size="md" testId="sample-spec-edit-modal" icon={Pencil} error={err}
      title={`Ubah spesifikasi · ${spec.number}`} subtitle="Boleh diubah selama spesifikasi belum di-ACC"
      footer={<Footer onClose={onClose} onConfirm={save} busy={busy} icon={Save} testId="sample-spec-edit-save" confirmLabel="Simpan perubahan" />}>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <Field label="Jenis kain *"><KNSelect data-testid="spec-edit-fabric" className="field" value={v.fabric_type} options={[{ value: "woven", label: "Woven (tenun)" }, { value: "knit", label: "Knit (rajut)" }]} onValueChange={(x) => s("fabric_type", x)} /></Field>
        <Field label="Gramasi (gsm)"><input className="field" type="number" data-testid="spec-edit-gramasi" value={v.gramasi} onChange={(e) => s("gramasi", e.target.value)} /></Field>
        <Field label="Lebar (cm)"><input className="field" type="number" data-testid="spec-edit-lebar" value={v.lebar} onChange={(e) => s("lebar", e.target.value)} /></Field>
        <Field label="SKU usulan"><input className="field" data-testid="spec-edit-sku" value={v.sku_hint} onChange={(e) => s("sku_hint", e.target.value.toUpperCase())} /></Field>
        <Field label="Target harga (Rp)"><input className="field" type="number" data-testid="spec-edit-price" value={v.target_price} onChange={(e) => s("target_price", e.target.value)} /></Field>
        <Field label="Catatan"><input className="field" data-testid="spec-edit-notes" value={v.notes} onChange={(e) => s("notes", e.target.value)} /></Field>
      </div>
    </FormModal>
  );
}
