import { useState } from "react";
import { Link2 } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import axios, { API } from "../../services/apiClient";
import { catalogError } from "./catalogApi";
export const DesignMediaImport = ({ product, onImport, busy }) => {
  const [open, setOpen] = useState(false); const [designs, setDesigns] = useState([]); const [designId, setDesignId] = useState(product.design_id || ""); const [fileId, setFileId] = useState(""); const [error, setError] = useState("");
  const design = designs.find(d => d.id === designId);
  const load = async () => { setOpen(!open); if (open) return; try { const r = await axios.get(`${API}/design-gallery`); setDesigns((r.data || []).filter(d => d.status === "approved")); setError(""); } catch (e) { setError(catalogError(e)); } };
  return <div className="border-t pt-4"><button data-testid="media-design-toggle" className="secondary-button" onClick={load}><Link2 size={14} />Ambil dari desain R&D</button>
    {open && <div className="mt-3 space-y-3">{error && <p data-testid="media-design-error" role="alert" className="text-sm text-red-700">{error}</p>}
      <KNSelect data-testid="media-design-select" className="field" placeholder="Pilih desain yang disetujui" value={designId} onValueChange={v => { setDesignId(v); setFileId(""); }} options={designs.map(d => ({ value: d.id, label: `${d.code || d.title} · v${d.version || 1}` }))} />
      <KNSelect data-testid="media-design-file" className="field" placeholder="Pilih berkas desain" value={fileId} onValueChange={setFileId} options={(design?.files || []).filter(f => !f.ai?.demo && f.content_type?.startsWith("image/")).map(f => ({ value: f.id, label: f.filename }))} />
      <button data-testid="media-design-import" className="primary-button" disabled={busy || !design || !fileId} onClick={() => onImport({ design_id: designId, file_id: fileId, version: design.version || 1 })}>Tambahkan ke galeri varian</button>
    </div>}
  </div>;
};