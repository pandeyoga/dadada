/** DesignImage — gambar berkas desain dimuat lewat axios (membawa sesi/Authorization), bukan <img src> polos yang 401. */
import { ImageOff, Loader2 } from "lucide-react";
import { useProofBlob } from "../ProofImage";

export default function DesignImage({ src, alt = "", className = "", loading, "data-testid": testId }) {
  const { src: blob, status } = useProofBlob(src, !!src);
  if (status === "loading") return <span className={`flex items-center justify-center bg-[#F5F5F7] text-[#B5B5BC] ${className}`} data-testid={testId}><Loader2 size={14} className="animate-spin" /></span>;
  if (status === "error" || !blob) return <span className={`flex items-center justify-center bg-[#F5F5F7] text-[#B5B5BC] ${className}`} title="Gagal memuat gambar" data-testid={testId}><ImageOff size={14} /></span>;
  return <img src={blob} alt={alt} className={className} loading={loading} data-testid={testId} />;
}
