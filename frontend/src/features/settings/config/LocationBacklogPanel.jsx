/** Alamat belum terverifikasi — lengkapi satu per satu dari layar Kebersihan Data (2026-09). */
import { useCallback, useEffect, useState } from "react";
import { MapPin, Loader2, RefreshCw, Save, X } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import ErrorNotice from "../../../components/ErrorNotice";
import KNSelect from "../../../components/KNSelect";
import LocationFields, { locationIncomplete, locationSummary } from "../../../components/LocationFields";
import { notifySuccess } from "../../../utils/feedback";
import { errMsg } from "./configApi";

const STATUS_LABEL = { partial: "Sebagian", unverified: "Belum terverifikasi" };

export default function LocationBacklogPanel({ canEdit = true }) {
  const [data, setData] = useState(null);
  const [coll, setColl] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null);   // row key
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setBusy(true); setErr("");
    try { const { data: d } = await axios.get(`${API}/data-hygiene/unverified-locations`, { params: { collection: coll || undefined } }); setData(d); }
    catch (e) { setErr(errMsg(e, "Gagal memuat alamat belum terverifikasi.")); }
    finally { setBusy(false); }
  }, [coll]);
  useEffect(() => { load(); }, [load]);

  const startEdit = (r) => { setEditing(`${r.collection}/${r.doc_id}`); setDraft({ ...r, country_code: r.country_code || "ID" }); setErr(""); };
  const save = async (r) => {
    const miss = locationIncomplete(draft);
    if (miss) { setErr(`Alamat: ${miss}`); return; }
    setSaving(true); setErr("");
    try {
      await axios.post(`${API}/data-hygiene/location/${r.collection}/${r.doc_id}`, draft);
      notifySuccess("Alamat dilengkapi", `${r.doc_label}: ${locationSummary(draft)}`);
      setEditing(null); load();
    } catch (e) { setErr(errMsg(e, "Gagal menyimpan alamat.")); }
    finally { setSaving(false); }
  };

  const labels = data?.labels || {};
  const options = [{ value: "", label: "Semua" }, ...Object.entries(labels).map(([k, v]) => ({ value: k, label: `${v} (${data?.counts?.[k] ?? 0})` }))];

  return (
    <section className="cfg-health" data-testid="location-backlog-panel" style={{ marginTop: 18 }}>
      <ErrorNotice message={err} onRetry={() => setErr("")} />
      <div className="cfg-health-verdict" data-testid="location-backlog-verdict">
        <MapPin size={20} />
        <div>
          <h3 data-testid="location-backlog-headline">{data ? `${data.total} alamat belum terverifikasi` : "Memuat…"}</h3>
          <p>Data lama yang belum punya provinsi, kota/kabupaten, dan kode pos yang sah menurut registry Kemendagri 2025.
            Lengkapi satu per satu — pilih dari daftar atau ketik kode pos untuk isi otomatis. Alamat utama pelanggan ikut dilengkapi.</p>
        </div>
        <button className="btn-secondary btn-sm" onClick={load} disabled={busy} data-testid="location-backlog-refresh">
          {busy ? <Loader2 size={13} className="spin" /> : <RefreshCw size={13} />} Muat ulang
        </button>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "10px 0" }}>
        <span className="cfg-hint-sm">Jenis data</span>
        <div style={{ minWidth: 240 }}><KNSelect data-testid="location-backlog-collection" value={coll} onValueChange={setColl} options={options} className="field" /></div>
      </div>
      {data && data.items.length === 0 ? <p className="cfg-hint-sm" data-testid="location-backlog-empty">Semua alamat sudah terverifikasi.</p> : null}
      {data?.items?.length ? (
        <table className="data-table cfg-health-table" data-testid="location-backlog-table">
          <thead><tr><th>Record</th><th>Alamat tersimpan</th><th>Status</th><th> </th></tr></thead>
          <tbody>
            {data.items.map((r) => {
              const key = `${r.collection}/${r.doc_id}`;
              const isEdit = editing === key;
              return (
                <tr key={key} data-testid={`location-backlog-row-${r.doc_id}`}>
                  <td><b>{r.label}</b><br />{r.doc_label}<br /><code className="cfg-key">{r.doc_id}</code></td>
                  <td style={{ minWidth: 320 }}>
                    {isEdit ? (
                      <div style={{ maxWidth: 560 }}>
                        <LocationFields testId={`locfix-${r.doc_id}`} compact value={draft} onChange={(p) => setDraft((d) => ({ ...d, ...p }))} />
                      </div>
                    ) : (
                      <span data-testid={`location-backlog-current-${r.doc_id}`}>{[r.address, r.city, r.province, r.postal_code].filter(Boolean).join(", ") || "—"}</span>
                    )}
                  </td>
                  <td><span className="badge-orange" data-testid={`location-backlog-status-${r.doc_id}`}>{STATUS_LABEL[r.status] || r.status}</span></td>
                  <td>
                    {canEdit && !isEdit && <button className="btn-secondary btn-sm" onClick={() => startEdit(r)} data-testid={`location-backlog-edit-${r.doc_id}`}><MapPin size={13} /> Lengkapi</button>}
                    {isEdit && (
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn-primary btn-sm" onClick={() => save(r)} disabled={saving} data-testid={`location-backlog-save-${r.doc_id}`}>
                          {saving ? <Loader2 size={13} className="spin" /> : <Save size={13} />} Simpan
                        </button>
                        <button className="btn-secondary btn-sm" onClick={() => setEditing(null)} data-testid={`location-backlog-cancel-${r.doc_id}`}><X size={13} /></button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
