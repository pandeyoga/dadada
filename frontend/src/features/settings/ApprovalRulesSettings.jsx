/**
 * Approval Rules Settings — matriks ambang persetujuan per jenis dokumen.
 * Skema TUNGGAL = skema mesin: {doc_type, entity_id, min_amount, max_amount,
 * required_role, sort, active, is_percent}.
 */
import { useState, useEffect } from "react";
import axios, { API } from "../../services/apiClient";
import {
  AlertCircle, CheckCircle2, Edit2, Loader2, Plus, Settings, Trash2, X
} from "lucide-react";
import ApprovalRuleForm from "./ApprovalRuleForm";
import FormModal from "../../components/FormModal";
import { docTypeLabel, fmtRange, roleLabel } from "./approvalRulesConstants";
import { askConfirm } from "@/services/confirmService";
import { useEntityScope } from "../../context/EntityScopeContext";

const EMPTY_FORM = {
  doc_type: "sales_order",
  min_amount: "",
  max_amount: "",
  required_role: "manager",
  sort: 1,
  active: true,
  description: "",
  entity_id: "all",
};

export default function ApprovalRulesSettings({ currentUser }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);

  const token = localStorage.getItem("kn_token");
  const isAdmin = currentUser?.role === "admin";
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const { entities } = useEntityScope();
  const entityName = (id) => {
    const e = entities.find((x) => x.id === id);
    return e ? (e.code ? `${e.name} (${e.code})` : e.name) : id;
  };

  useEffect(() => {
    loadRules();
  }, []); // eslint-disable-line

  async function loadRules() {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/approval-rules`, auth);
      setRules(res.data || []);
      setError(null);
    } catch (e) {
      setError("Gagal memuat rules: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setFormData(EMPTY_FORM);
    setEditingRule(null);
    setShowCreateForm(false);
  }

  function handleEdit(rule) {
    setFormData({
      doc_type: rule.doc_type || "sales_order",
      min_amount: rule.min_amount ?? "",
      max_amount: rule.max_amount ?? "",
      required_role: rule.required_role || "",
      sort: rule.sort ?? 1,
      active: rule.active !== false,
      description: rule.description || "",
      entity_id: rule.entity_id || "all",
    });
    setEditingRule(rule);
    setShowCreateForm(true);
  }

  function buildPayload() {
    const min = parseFloat(formData.min_amount);
    return {
      doc_type: formData.doc_type,
      min_amount: Number.isNaN(min) ? 0 : min,
      max_amount: formData.max_amount === "" || formData.max_amount === null
        ? null : parseFloat(formData.max_amount),
      required_role: formData.required_role || "",
      sort: parseInt(formData.sort) || 1,
      active: !!formData.active,
      description: formData.description || "",
      entity_id: formData.entity_id || "all",
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const payload = buildPayload();
    if (payload.max_amount !== null && payload.max_amount <= payload.min_amount) {
      return setError("Nilai maksimal harus lebih besar dari nilai minimal");
    }
    try {
      if (editingRule) {
        await axios.patch(`${API}/approval-rules/${editingRule.id}`, payload, auth);
        setNotice("Aturan berhasil diupdate!");
      } else {
        await axios.post(`${API}/approval-rules`, payload, auth);
        setNotice("Aturan berhasil dibuat!");
      }
      resetForm();
      loadRules();
    } catch (e) {
      setError("Gagal menyimpan: " + (e.response?.data?.detail || e.message));
    }
  }

  async function handleDelete(rule) {
    const ok = await askConfirm({
      title: `Nonaktifkan aturan ${docTypeLabel(rule.doc_type)} (${fmtRange(rule)})?`,
      message: "Mesin approval berhenti membaca aturan ini; dokumen pada rentang tsb tidak lagi otomatis meminta persetujuan.",
      confirmLabel: "Nonaktifkan Aturan",
      danger: true,
      testId: "approval-rule-delete-confirm",
    });
    if (!ok) return;
    try {
      await axios.delete(`${API}/approval-rules/${rule.id}`, auth);
      setNotice("Aturan dinonaktifkan.");
      loadRules();
    } catch (e) {
      setError("Gagal menghapus: " + (e.response?.data?.detail || e.message));
    }
  }

  async function toggleActive(rule) {
    try {
      await axios.patch(`${API}/approval-rules/${rule.id}`,
        { active: rule.active === false }, auth);
      loadRules();
    } catch (e) {
      setError("Gagal toggle status: " + (e.response?.data?.detail || e.message));
    }
  }

  if (!isAdmin) {
    return (
      <div className="view-container">
        <div className="notice-bar danger">
          <AlertCircle size={14} /> Hanya admin yang dapat mengelola aturan persetujuan.
        </div>
      </div>
    );
  }

  return (
    <div data-testid="approval-rules-settings" className="view-container">
      {notice && (
        <div className="notice-bar success">
          <CheckCircle2 size={14} /> {notice}
          <button onClick={() => setNotice(null)}><X size={12} /></button>
        </div>
      )}

      {error && (
        <div className="notice-bar danger">
          <AlertCircle size={14} /> {error}
          <button onClick={() => setError(null)}><X size={12} /></button>
        </div>
      )}

      <div className="view-header">
        <div>
          <h1 className="view-title">
            <Settings size={20} /> Aturan Persetujuan
          </h1>
          <p className="view-subtitle">
            Rentang nilai dokumen &amp; peran yang berwenang memutuskan — dibaca langsung oleh mesin approval
          </p>
        </div>
        {!showCreateForm && (
          <button
            data-testid="create-rule-btn"
            className="primary-button"
            onClick={() => setShowCreateForm(true)}
          >
            <Plus size={14} /> Buat Aturan Baru
          </button>
        )}
      </div>

      <FormModal
        open={showCreateForm}
        onClose={resetForm}
        title={editingRule ? "Ubah Aturan Persetujuan" : "Aturan Persetujuan Baru"}
        subtitle="Rentang nilai dokumen & peran yang berwenang memutuskan"
        icon={Settings}
        size="lg"
        testId="rule-form-modal"
      >
        <ApprovalRuleForm
          variant="modal"
          formData={formData}
          setFormData={setFormData}
          onSubmit={handleSubmit}
          onCancel={resetForm}
          editingRule={editingRule}
        />
      </FormModal>

      {loading ? (
        <div className="loading-state">
          <Loader2 size={24} className="spin" />
          <p>Memuat aturan persetujuan…</p>
        </div>
      ) : rules.length === 0 ? (
        <div className="empty-state">
          <Settings size={32} style={{ opacity: 0.3 }} />
          <p>Belum ada aturan persetujuan.</p>
          {!showCreateForm && (
            <button className="primary-button" onClick={() => setShowCreateForm(true)}>
              <Plus size={14} /> Buat Aturan Pertama
            </button>
          )}
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Jenis Dokumen</th>
                <th>Cakupan</th>
                <th>Rentang Nilai</th>
                <th>Peran Penyetuju</th>
                <th className="text-center">Urutan</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map(rule => (
                <tr key={rule.id} data-testid={`rule-row-${rule.id}`}>
                  <td>
                    <span className="feature-badge badge-blue">
                      {docTypeLabel(rule.doc_type)}
                    </span>
                    {rule.description && (
                      <div className="text-xs text-muted">{rule.description}</div>
                    )}
                  </td>
                  <td className="text-sm">
                    {(!rule.entity_id || rule.entity_id === "all") ? "Semua entitas" : entityName(rule.entity_id)}
                  </td>
                  <td className="font-mono text-sm tabular-nums whitespace-nowrap">
                    {fmtRange(rule)}
                  </td>
                  <td>
                    {rule.required_role ? (
                      <span className="feature-badge badge-purple">{roleLabel(rule.required_role)}</span>
                    ) : (
                      <span className="text-xs text-muted">Tanpa persetujuan (otomatis)</span>
                    )}
                  </td>
                  <td className="text-center tabular-nums">{rule.sort}</td>
                  <td>
                    <button
                      data-testid={`toggle-rule-${rule.id}`}
                      className={`status-pill ${rule.active !== false ? "pill-success" : "pill-muted"}`}
                      onClick={() => toggleActive(rule)}
                    >
                      {rule.active !== false ? "Aktif" : "Nonaktif"}
                    </button>
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button
                        data-testid={`edit-rule-${rule.id}`}
                        className="icon-button"
                        onClick={() => handleEdit(rule)}
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        data-testid={`delete-rule-${rule.id}`}
                        className="icon-button danger"
                        onClick={() => handleDelete(rule)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
