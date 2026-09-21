/**
 * ProofImage — thumbnail bukti round yang dimuat lewat axios (membawa Authorization +
 * X-Entity-Id), lalu ditampilkan sebagai object URL. `<img src>` polos tidak membawa header
 * entitas, jadi bukti supplier di badan usaha non-utama akan 403.
 */
import { useEffect, useState } from "react";
import axios from "axios";
import { FileText, ImageOff, Loader2 } from "lucide-react";

const cache = new Map();

export function isImageProof(a) {
  const ct = String(a?.content_type || "").toLowerCase();
  if (ct.startsWith("image/")) return true;
  return /\.(png|jpe?g|webp|gif)$/i.test(String(a?.filename || ""));
}

export function useProofBlob(url, enabled = true) {
  const [state, setState] = useState(() => (cache.has(url) ? { src: cache.get(url), status: "ok" } : { src: "", status: "loading" }));
  useEffect(() => {
    if (!enabled || !url) return undefined;
    if (cache.has(url)) { setState({ src: cache.get(url), status: "ok" }); return undefined; }
    let alive = true;
    setState({ src: "", status: "loading" });
    axios.get(url, { responseType: "blob" })
      .then((r) => {
        const src = URL.createObjectURL(r.data);
        cache.set(url, src);
        if (alive) setState({ src, status: "ok" });
      })
      .catch(() => { if (alive) setState({ src: "", status: "error" }); });
    return () => { alive = false; };
  }, [url, enabled]);
  return state;
}

export default function ProofImage({ url, alt = "", attachment, className = "", imgClassName = "object-cover", testId }) {
  const image = isImageProof(attachment);
  const { src, status } = useProofBlob(url, image);
  if (!image) {
    return (
      <span className={`flex items-center justify-center bg-[#F2F2F5] text-[#8E8E93] ${className}`} data-testid={testId} title={attachment?.filename}>
        <FileText size={18} />
      </span>
    );
  }
  if (status === "loading") {
    return <span className={`flex items-center justify-center bg-[#F2F2F5] text-[#B5B5BC] ${className}`} data-testid={testId}><Loader2 size={14} className="animate-spin" /></span>;
  }
  if (status === "error") {
    return <span className={`flex items-center justify-center bg-[#FFF0F0] text-[#C4361D] ${className}`} data-testid={testId} title="Gagal memuat bukti"><ImageOff size={14} /></span>;
  }
  return <img src={src} alt={alt} className={`${className} ${imgClassName}`} data-testid={testId} loading="lazy" />;
}
