import { useEffect, useState } from "react";
import { ImageOff } from "lucide-react";
import { fetchGalleryImageUrl } from "./galleryUtils";

// Gambar galeri via blob-fetch ber-Authorization → objectURL (revoke saat unmount).
export default function GalleryImage({ galleryId, fileId, alt, fit = "cover" }) {
  const [url, setUrl] = useState("");
  const [fail, setFail] = useState(false);
  useEffect(() => {
    let active = true; let created = "";
    fetchGalleryImageUrl(galleryId, fileId).then((u) => { if (active) { created = u; setUrl(u); } }).catch(() => active && setFail(true));
    return () => { active = false; if (created) URL.revokeObjectURL(created); };
  }, [galleryId, fileId]);
  if (fail) return <div className="h-full w-full flex items-center justify-center text-[#C7C9CF]"><ImageOff size={24} /></div>;
  if (!url) return <div className="h-full w-full animate-pulse bg-[#E9EBEF]" />;
  return <img src={url} alt={alt} className={`h-full w-full object-${fit}`} />;
}
