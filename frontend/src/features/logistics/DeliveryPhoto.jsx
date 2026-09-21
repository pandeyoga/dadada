import { useEffect, useState } from "react";
import { ImageOff } from "lucide-react";
import axios from "../../services/apiClient";

// Foto pengiriman via blob-fetch ber-Authorization → objectURL.
export default function DeliveryPhoto({ url, alt, fit = "cover" }) {
  const [src, setSrc] = useState("");
  const [fail, setFail] = useState(false);
  useEffect(() => {
    let active = true; let created = "";
    axios.get(url, { responseType: "blob" })
      .then((r) => { if (active) { created = URL.createObjectURL(r.data); setSrc(created); } })
      .catch(() => active && setFail(true));
    return () => { active = false; if (created) URL.revokeObjectURL(created); };
  }, [url]);
  if (fail) return <div className="h-full w-full flex items-center justify-center text-[#C7C9CF]"><ImageOff size={20} /></div>;
  if (!src) return <div className="h-full w-full animate-pulse bg-[#E9EBEF]" />;
  return <img src={src} alt={alt} className={`h-full w-full object-${fit}`} />;
}
