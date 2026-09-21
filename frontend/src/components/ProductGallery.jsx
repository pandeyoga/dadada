import { useEffect, useState } from "react";
import { ImageOff, Maximize2, X, ChevronLeft, ChevronRight } from "lucide-react";
import { BACKEND_URL } from "../services/apiClient";
import { onImageError, productImage } from "../utils/productImage";
import { useEscapeClose } from "../utils/escapeLayers";
import { overlayDismiss } from "../utils/overlayDismiss";

export const mediaUrl = url => String(url || "").startsWith("/api/") ? `${BACKEND_URL}${url}` : url;
export const ProductGallery = ({ product, testId = "product-gallery", compact = false, items, coverId }) => {
  const photos = items || (product?.media || []).filter(m => m.status === "approved" && !m.deleted);
  const [active, setActive] = useState(0); const [full, setFull] = useState(false);
  const idKey = photos.map(m => m.id).join("|");
  useEffect(() => { const idx = photos.findIndex(m => m.id === (coverId || product?.cover_media_id)); setActive(Math.max(0, idx)); setFull(false); }, [product?.id, idKey, coverId, product?.cover_media_id]); // eslint-disable-line
  const closeFull = () => setFull(false);
  useEscapeClose(full, closeFull);
  const photo = photos[active] || photos[0];
  const src = photo ? mediaUrl(photo.url) : productImage(product);
  const hasPhoto = !!photo || !!product?.image;
  const alt = `${product?.name || "Produk"} · ${photo?.kind === "mockup" ? "Ilustrasi mockup" : "Foto produk"}`;
  return <div data-testid={testId} className="min-w-0">
    <div className={`relative overflow-hidden rounded-lg border bg-[#F4F5F7] ${compact ? "aspect-[4/3]" : "aspect-square"}`}>
      {hasPhoto ? <img data-testid={`${testId}-image`} src={src} alt={alt} onError={onImageError} className="h-full w-full object-contain" /> : <div data-testid={`${testId}-empty`} className="flex h-full flex-col items-center justify-center gap-2 text-[#9A9BA3]"><ImageOff size={32} strokeWidth={1} /><span className="text-xs">Belum ada foto</span></div>}
      {photo?.kind === "mockup" && <span data-testid={`${testId}-mockup-label`} className="absolute bottom-2 left-2 rounded bg-white/95 px-2 py-1 text-xs">Ilustrasi mockup{photo.ai || photo.is_ai ? " AI" : ""}</span>}
      {hasPhoto && <button data-testid={`${testId}-zoom`} type="button" className="absolute right-2 top-2 rounded-md bg-white/95 p-2" title="Perbesar foto" onClick={() => setFull(true)}><Maximize2 size={15} /></button>}
    </div>
    {photos.length > 1 && <div className="mt-2 flex flex-wrap gap-2">{photos.map((p, i) => <button data-testid={`${testId}-thumb-${p.id}`} aria-label={`Foto ${i + 1}`} aria-pressed={active === i} type="button" key={p.id} onClick={() => setActive(i)} className={`h-12 w-12 overflow-hidden rounded border-2 ${active === i ? "border-[#0058CC]" : "border-transparent"}`}><img src={mediaUrl(p.url)} alt={`Foto ${i + 1}`} onError={onImageError} className="h-full w-full bg-gray-50 object-contain" /></button>)}</div>}
    {full && <div data-testid={`${testId}-lightbox`} role="dialog" aria-modal="true" aria-label="Foto produk ukuran penuh" className="fixed inset-0 z-[260] flex items-center justify-center bg-black/90 p-5" {...overlayDismiss(closeFull)}>
      <button type="button" data-testid={`${testId}-zoom-close`} aria-label="Tutup foto" className="absolute right-5 top-5 rounded bg-white p-2" onClick={closeFull}><X /></button>
      <img src={src} alt={alt} className="max-h-[85vh] max-w-[90vw] object-contain" onClick={e => e.stopPropagation()} />
      {photos.length > 1 && <div className="absolute bottom-5 flex gap-4 text-white" onClick={e => e.stopPropagation()}><button data-testid={`${testId}-prev`} aria-label="Foto sebelumnya" onClick={() => setActive((active + photos.length - 1) % photos.length)}><ChevronLeft /></button><span data-testid={`${testId}-counter`}>{active + 1} / {photos.length}</span><button data-testid={`${testId}-next`} aria-label="Foto berikutnya" onClick={() => setActive((active + 1) % photos.length)}><ChevronRight /></button></div>}
    </div>}
  </div>;
};