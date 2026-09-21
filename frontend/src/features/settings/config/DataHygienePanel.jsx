/**
 * DataHygienePanel — Kebersihan Data (K-1/K-2 otomatis, 2026-09).
 * Sistem merapikan EYD nama & nomor telepon pada data lama saat boot; layar ini menampilkan
 * riwayat per-record (sebelum → sesudah), pratinjau yang masih akan berubah, dan tombol
 * kembalikan per-record (record yang dikembalikan dikunci dari perapian berikutnya).
 */
import { useCallback, useEffect, useState } from "react";
import { Sparkles, Loader2, RefreshCw, Undo2, LockOpen, ShieldCheck, Play } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import ErrorNotice from "../../../components/ErrorNotice";
import KNSelect from "../../../components/KNSelect";
import { notifySuccess } from "../../../utils/feedback";
import { askConfirm } from "../../../services/confirmService";
import { errMsg } from "./configApi";

const FIELD_LABEL = { name: "Nama", pic_name: "Nama PIC", phone: "Telepon/WA", full_name: "Nama lengkap", addresses: "Alamat (penerima/telepon)", contacts: "Kontak (nama/telepon)" };
const fmt = (v) => (v == null || v === "" ? "—" : String(v));
const SUB_LABEL = { recipient_name: "penerima", phone: "telepon", name: "nama" };

/** Untuk field array (alamat/kontak): rincikan hanya sub-field yang berubah per baris. */
function arrayDiff(before, after) {
  const out = [];
  (after || []).forEach((it, i) => {
    const b = (before || [])[i] || {};
    Object.keys(it || {}).forEach((k) => { if (it[k] !== b[k]) out.push({ row: i + 1, key: k, before: b[k], after: it[k] }); });
  });
  return out;
}

function ChangeList({ changes, testId }) {
  return (
    <ul className="cfg-hint-sm" data-testid={testId} style={{ margin: 0, paddingLeft: 14 }}>
      {changes.map((c, i) => Array.isArray(c.after) ? (
        <li key={i}>
          <b>{FIELD_LABEL[c.field] || c.field}:</b>
          <ul style={{ margin: 0, paddingLeft: 12 }}>
            {arrayDiff(c.before, c.after).map((d, j) => (
              <li key={j}>#{d.row} {SUB_LABEL[d.key] || d.key}: <span style={{ textDecoration: "line-through", opacity: 0.6 }}>{fmt(d.before)}</span> → <span style={{ color: "#126E2C", fontWeight: 600 }}>{fmt(d.after)}</span></li>
            ))}
          </ul>
        </li>
      ) : (
        <li key={i}>
          <b>{FIELD_LABEL[c.field] || c.field}:</b>{" "}
          <span style={{ textDecoration: "line-through", opacity: 0.6 }}>{fmt(c.before)}</span> → <span style={{ color: "#126E2C", fontWeight: 600 }}>{fmt(c.after)}</span>
        </li>
      ))}
    </ul>
  );
}

export default function DataHygienePanel({ isAdmin = false }) {
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [preview, setPreview] = useState(null);
  const [coll, setColl] = useState("");
  const [busy, setBusy] = useState(false);
  const [acting, setActing] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setBusy(true); setErr("");
    try {
      const [s, l] = await Promise.all([
        axios.get(`${API}/data-hygiene/summary`),
        axios.get(`${API}/data-hygiene/log`, { params: { collection: coll || undefined, limit: 200 } }),
      ]);
      setSummary(s.data); setRows(l.data.items || []);
    } catch (e) { setErr(errMsg(e, "Gagal memuat kebersihan data.")); }
    finally { setBusy(false); }
  }, [coll]);

  useEffect(() => { load(); }, [load]);

  const loadPreview = async () => {
    setActing("preview"); setErr("");
    try { const { data } = await axios.get(`${API}/data-hygiene/preview`, { params: { collection: coll || undefined } }); setPreview(data); }
    catch (e) { setErr(errMsg(e, "Gagal memuat pratinjau.")); }
    finally { setActing(""); }
  };

  const runNow = async () => {
    const ok = await askConfirm({ title: "Rapikan data sekarang?", message: "Semua record yang belum dikunci akan dirapikan (EYD nama & nomor telepon). Setiap perubahan dicatat dan bisa dikembalikan per-record.", confirmLabel: "Rapikan", testId: "hygiene-run-confirm" });
    if (!ok) return;
    setActing("run"); setErr("");
    try { const { data } = await axios.post(`${API}/data-hygiene/run`, null, { params: { collection: coll || undefined } }); notifySuccess("Perapian selesai", `${data.changed} record dirapikan.`); setPreview(null); load(); }
    catch (e) { setErr(errMsg(e, "Gagal menjalankan perapian.")); }
    finally { setActing(""); }
  };

  const revert = async (r) => {
    const ok = await askConfirm({ title: `Kembalikan "${r.doc_label}"?`, message: "Nilai sebelum perapian dipulihkan dan record ini dikunci agar tidak dirapikan lagi.", confirmLabel: "Kembalikan", testId: "hygiene-revert-confirm" });
    if (!ok) return;
    setActing(r.id); setErr("");
    try { await axios.post(`${API}/data-hygiene/log/${r.id}/revert`); notifySuccess("Dikembalikan", `${r.doc_label} dipulihkan & dikunci.`); load(); }
    catch (e) { setErr(errMsg(e, "Gagal mengembalikan.")); }
    finally { setActing(""); }
  };

  const unlock = async (r) => {
    setActing(`unlock-${r.id}`); setErr("");
    try { await axios.post(`${API}/data-hygiene/${r.collection}/${r.doc_id}/unlock`); notifySuccess("Kunci dibuka", `${r.doc_label} akan ikut perapian berikutnya.`); load(); }
    catch (e) { setErr(errMsg(e, "Gagal membuka kunci.")); }
    finally { setActing(""); }
  };

  const labels = summary?.labels || {};
  const collOptions = [{ value: "", label: "Semua koleksi" }, ...Object.keys(summary?.rules || {}).map((k) => ({ value: k, label: labels[k] || k }))];
  const lockedTotal = Object.values(summary?.locked || {}).reduce((a, b) => a + b, 0);

  return (
    <section className="cfg-health" data-testid="data-hygiene-panel">
      <ErrorNotice message={err} onRetry={load} />
      <div className="cfg-health-verdict good" data-testid="data-hygiene-verdict">
        {summary ? <Sparkles size={20} /> : <ShieldCheck size={20} />}
        <div>
          <h3 data-testid="data-hygiene-headline">
            {summary ? `${summary.active} record dirapikan otomatis · ${summary.reverted} dikembalikan · ${lockedTotal} dikunci` : "Memuat…"}
          </h3>
          <p>
            Sistem merapikan penulisan (EYD: PT/CV kapital, nama orang Kapital Tiap Kata, gelar S.E./M.M.) dan
            menormalkan nomor telepon/WhatsApp ke format 62xxxxxxxxxx pada data lama saat aplikasi mulai, serta pada
            setiap penulisan baru (satu pintu). Setiap perubahan dicatat di sini dan bisa dikembalikan per-record.
            {summary?.last_run ? ` Terakhir: ${new Date(summary.last_run.at).toLocaleString("id-ID")} (${summary.last_run.trigger}, ${summary.last_run.changed} record).` : ""}
          </p>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button className="btn-secondary btn-sm" onClick={load} disabled={busy} data-testid="data-hygiene-refresh">
            {busy ? <Loader2 size={13} className="spin" /> : <RefreshCw size={13} />} Muat ulang
          </button>
          <button className="btn-secondary btn-sm" onClick={loadPreview} disabled={acting === "preview"} data-testid="data-hygiene-preview">
            {acting === "preview" ? <Loader2 size={13} className="spin" /> : <Sparkles size={13} />} Pratinjau yang akan berubah
          </button>
          {isAdmin && (
            <button className="btn-secondary btn-sm" onClick={runNow} disabled={acting === "run"} data-testid="data-hygiene-run">
              {acting === "run" ? <Loader2 size={13} className="spin" /> : <Play size={13} />} Rapikan sekarang
            </button>
          )}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "10px 0" }}>
        <span className="cfg-hint-sm">Koleksi</span>
        <div style={{ minWidth: 220 }}>
          <KNSelect data-testid="data-hygiene-collection" value={coll} onValueChange={(v) => { setColl(v); setPreview(null); }} options={collOptions} className="field" />
        </div>
        {summary && Object.entries(summary.per_collection || {}).map(([k, n]) => (
          <span key={k} className="badge-orange" data-testid={`data-hygiene-count-${k}`}>{labels[k] || k}: {n}</span>
        ))}
      </div>

      {preview && (
        <div className="cfg-health-verdict" data-testid="data-hygiene-preview-box" style={{ marginBottom: 10 }}>
          <div style={{ flex: 1 }}>
            <h3 data-testid="data-hygiene-preview-count">{preview.length ? `${preview.length} record masih akan berubah` : "Tidak ada lagi yang perlu dirapikan"}</h3>
            {preview.slice(0, 20).map((p) => (
              <div key={`${p.collection}/${p.doc_id}`} style={{ marginTop: 6 }}>
                <b>{labels[p.collection] || p.collection}</b> · {p.doc_label}
                <ChangeList changes={p.changes} />
              </div>
            ))}
          </div>
        </div>
      )}

      {rows.length ? (
        <table className="data-table cfg-health-table" data-testid="data-hygiene-table">
          <thead>
            <tr><th>Record</th><th>Perubahan</th><th>Kapan</th><th>Status</th><th> </th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-testid={`data-hygiene-row-${r.id}`}>
                <td><b>{labels[r.collection] || r.collection}</b><br /><span>{r.doc_label}</span><br /><code className="cfg-key">{r.doc_id}</code></td>
                <td><ChangeList changes={r.changes} testId={`data-hygiene-changes-${r.id}`} /></td>
                <td>{new Date(r.applied_at).toLocaleString("id-ID")}<br /><span className="cfg-hint-sm">{r.trigger} · {r.actor}</span></td>
                <td>
                  {r.reverted
                    ? <span className="badge-orange" data-testid={`data-hygiene-status-${r.id}`}>Dikembalikan · dikunci</span>
                    : <span className="badge-green" data-testid={`data-hygiene-status-${r.id}`}>Diterapkan</span>}
                </td>
                <td>
                  {isAdmin && !r.reverted && (
                    <button className="btn-secondary btn-sm" onClick={() => revert(r)} disabled={acting === r.id} data-testid={`data-hygiene-revert-${r.id}`}>
                      {acting === r.id ? <Loader2 size={13} className="spin" /> : <Undo2 size={13} />} Kembalikan
                    </button>
                  )}
                  {isAdmin && r.reverted && (
                    <button className="btn-secondary btn-sm" onClick={() => unlock(r)} disabled={acting === `unlock-${r.id}`} data-testid={`data-hygiene-unlock-${r.id}`}>
                      {acting === `unlock-${r.id}` ? <Loader2 size={13} className="spin" /> : <LockOpen size={13} />} Buka kunci
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (!busy && <p className="cfg-hint-sm" data-testid="data-hygiene-empty">Belum ada catatan perapian{coll ? " untuk koleksi ini" : ""}.</p>)}
    </section>
  );
}
