// Form buat/edit Approval Rule — skema MESIN: doc_type + rentang nilai + peran.
import { CheckCircle2, X } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import { useEntityScope } from "../../context/EntityScopeContext";
import { DOC_TYPES, ROLES } from "./approvalRulesConstants";

export default function ApprovalRuleForm({ formData, setFormData, onSubmit, onCancel,
                                          editingRule, variant = "card" }) {
  const isModal = variant === "modal";
  const isPct = formData.doc_type === "discount";
  const { entities } = useEntityScope();
  const entityOptions = [
    { value: "all", label: "Semua entitas (warisan grup)" },
    ...entities.map((e) => ({ value: e.id, label: e.code ? `${e.name} (${e.code})` : e.name })),
  ];
  return (
    <div className={isModal ? "" : "form-card"} data-testid="rule-form">
      {!isModal && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">
            {editingRule ? "Ubah Aturan" : "Buat Aturan Baru"}
          </h3>
          <button className="icon-button" onClick={onCancel}>
            <X size={14} />
          </button>
        </div>
      )}

      <form onSubmit={onSubmit} className="grid gap-3">
        <div className="form-row-2col">
          <div className="form-group">
            <label className="form-label">Jenis Dokumen <span className="req">*</span></label>
            <KNSelect
              data-testid="rule-doc-type"
              className="form-select"
              value={formData.doc_type}
              onValueChange={v => setFormData({ ...formData, doc_type: v })}
              options={DOC_TYPES.map(t => ({ value: t.value, label: t.label }))}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Peran Penyetuju <span className="req">*</span></label>
            <KNSelect
              data-testid="rule-required-role"
              className="form-select"
              value={formData.required_role}
              onValueChange={v => setFormData({ ...formData, required_role: v })}
              options={ROLES.map(r => ({ value: r.value, label: r.label }))}
            />
            <p className="form-help text-xs">Kosong = dokumen pada rentang ini lolos tanpa persetujuan.</p>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Cakupan Entitas</label>
          <KNSelect
            data-testid="rule-entity-id"
            className="form-select"
            value={formData.entity_id || "all"}
            onValueChange={v => setFormData({ ...formData, entity_id: v })}
            options={entityOptions}
          />
          <p className="form-help text-xs">Aturan ber-entitas dinilai lebih dulu; "Semua entitas" jadi cadangan bila tidak ada.</p>
        </div>

        <div className="form-row-3col">
          <div className="form-group">
            <label className="form-label">Nilai Minimal ({isPct ? "%" : "Rp"}) <span className="req">*</span></label>
            <input
              data-testid="rule-min-amount"
              className="form-input"
              type="number" min="0" step="0.01"
              value={formData.min_amount}
              onChange={e => setFormData({ ...formData, min_amount: e.target.value })}
              placeholder="0"
              required
            />
            <p className="form-help text-xs">Batas bawah rentang (inklusif).</p>
          </div>

          <div className="form-group">
            <label className="form-label">Nilai Maksimal ({isPct ? "%" : "Rp"})</label>
            <input
              data-testid="rule-max-amount"
              className="form-input"
              type="number" min="0" step="0.01"
              value={formData.max_amount}
              onChange={e => setFormData({ ...formData, max_amount: e.target.value })}
              placeholder="Kosongkan = tanpa batas"
            />
            <p className="form-help text-xs">Batas atas (eksklusif); kosong = tanpa batas atas.</p>
          </div>

          <div className="form-group">
            <label className="form-label">Urutan Evaluasi</label>
            <input
              data-testid="rule-sort"
              className="form-input"
              type="number" min="1"
              value={formData.sort}
              onChange={e => setFormData({ ...formData, sort: parseInt(e.target.value) || 1 })}
            />
            <p className="form-help text-xs">Kecil = dinilai lebih dulu.</p>
          </div>
        </div>

        <div className="form-row-2col">
          <div className="form-group">
            <label className="form-label">Keterangan</label>
            <input
              data-testid="rule-description"
              className="form-input"
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              placeholder="Keterangan aturan…"
            />
          </div>

          <div className="form-group">
            <label className="form-check-label sm:mt-6">
              <input
                type="checkbox"
                data-testid="rule-active"
                checked={formData.active}
                onChange={e => setFormData({ ...formData, active: e.target.checked })}
              />
              {" "}Aktif
            </label>
          </div>
        </div>

        <div className="form-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>
            Batal
          </button>
          <button type="submit" data-testid="save-rule-btn" className="primary-button">
            <CheckCircle2 size={14} /> {editingRule ? "Simpan Perubahan" : "Buat Aturan"}
          </button>
        </div>
      </form>
    </div>
  );
}
