/**
 * ReferenceGallery — gambar referensi brief pada Permintaan Desain.
 * Dipakai di modal buat (pratinjau lokal sebelum permintaan punya nomor) dan di panel
 * rincian (unggah/hapus ke server). Referensi ikut OTOMATIS ke tab Referensi desain Studio.
 */
import { useEffect, useMemo } from "react";
import { Image as ImageIcon, Trash2, Upload } from "lucide-react";
import { referenceUrl } from "./designRequestsApi";

export default function ReferenceGallery({ requestId, files = [], localFiles = [], canEdit, onPick, onRemove, busy, testId = "dsr-references" }) {
  const previews = useMemo(() => localFiles.map((f) => ({ file: f, url: URL.createObjectURL(f) })), [localFiles]);
  useEffect(() => () => previews.forEach((p) => URL.revokeObjectURL(p.url)), [previews]);
  const total = files.length + localFiles.length;

  return (
    <div data-testid={testId}>
      <div className="mb-1.5 flex items-center justify-between">
        <p className="text-[10.5px] text-[#6B6B73]"><b>Gambar referensi</b> · inspirasi / acuan untuk desainer · {total} gambar</p>
        {canEdit && (
          <label className={`secondary-button cursor-pointer !py-1 text-[11px] ${busy ? "pointer-events-none opacity-60" : ""}`} data-testid={`${testId}-upload-label`}>
            <Upload size={12} /> Tambah gambar
            <input type="file" className="hidden" accept="image/*" multiple data-testid={`${testId}-upload`}
              onChange={(e) => { onPick?.(Array.from(e.target.files || [])); e.target.value = ""; }} />
          </label>
        )}
      </div>
      {total === 0 ? (
        <div className="flex h-16 flex-col items-center justify-center rounded-lg border border-dashed border-[#D9D9DE] text-[10.5px] text-[#9A9BA3]" data-testid={`${testId}-empty`}>
          <ImageIcon size={16} className="mb-0.5" /> belum ada gambar referensi
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-6">
          {files.map((f) => (
            <figure key={f.id} className="group relative aspect-square overflow-hidden rounded-lg border border-[#E5E5EA] bg-[#F5F5F7]" data-testid={`${testId}-item-${f.id}`}>
              <a href={referenceUrl(requestId, f.id)} target="_blank" rel="noreferrer">
                <img src={referenceUrl(requestId, f.id)} alt={f.filename} className="h-full w-full object-cover" loading="lazy" />
              </a>
              {canEdit && (
                <button type="button" className="absolute right-1 top-1 hidden rounded bg-white/90 p-1 text-red-500 shadow group-hover:block"
                  data-testid={`${testId}-delete-${f.id}`} title="Hapus" onClick={() => onRemove?.(f)}>
                  <Trash2 size={11} />
                </button>
              )}
            </figure>
          ))}
          {previews.map((p, i) => (
            <figure key={p.url} className="group relative aspect-square overflow-hidden rounded-lg border border-dashed border-[#C9B3DB] bg-[#FBF7FE]" data-testid={`${testId}-local-${i}`}>
              <img src={p.url} alt={p.file.name} className="h-full w-full object-cover" />
              <span className="absolute bottom-1 left-1 rounded bg-white/90 px-1 text-[8.5px] font-bold text-[#6B219A]">baru</span>
              {canEdit && (
                <button type="button" className="absolute right-1 top-1 hidden rounded bg-white/90 p-1 text-red-500 shadow group-hover:block"
                  data-testid={`${testId}-local-remove-${i}`} title="Buang" onClick={() => onRemove?.(null, i)}>
                  <Trash2 size={11} />
                </button>
              )}
            </figure>
          ))}
        </div>
      )}
    </div>
  );
}
