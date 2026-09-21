/** TagInput — tag tersimpan: ketik sedikit → saran muncul, Enter/koma menambah. */
import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { studioTags } from "../rndApi";

export default function TagInput({ value = [], onChange, testId = "design-tags" }) {
  const [text, setText] = useState("");
  const [sugg, setSugg] = useState([]);
  const [open, setOpen] = useState(false);
  const timer = useRef(null);

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      try {
        const rows = await studioTags(text.trim());
        setSugg(rows.filter((r) => !value.some((v) => v.toLowerCase() === r.name.toLowerCase())));
      } catch { setSugg([]); }
    }, 180);
    return () => clearTimeout(timer.current);
  }, [text, value]);

  const add = (t) => {
    const s = String(t || "").trim().replace(/,$/, "");
    if (!s || value.some((v) => v.toLowerCase() === s.toLowerCase())) { setText(""); return; }
    onChange([...value, s]);
    setText("");
  };

  return (
    <div className="relative" data-testid={testId}>
      <div className="field flex min-h-[36px] flex-wrap items-center gap-1 !py-1">
        {value.map((t) => (
          <span key={t} className="inline-flex items-center gap-1 rounded-full bg-[#F1E9F7] px-2 py-0.5 text-[11px] font-medium text-[#6B219A]"
            data-testid={`${testId}-chip-${t}`}>
            {t}
            <button type="button" onClick={() => onChange(value.filter((v) => v !== t))}
              className="text-[#6B219A]/70 hover:text-[#6B219A]" aria-label={`hapus ${t}`}><X size={10} /></button>
          </span>
        ))}
        <input value={text} data-testid={`${testId}-input`}
          className="min-w-[120px] flex-1 border-0 bg-transparent text-[12px] outline-none"
          placeholder={value.length ? "" : "ketik tag, Enter untuk tambah…"}
          onChange={(e) => { setText(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(text); }
            if (e.key === "Backspace" && !text && value.length) onChange(value.slice(0, -1));
          }} />
      </div>
      {open && sugg.length > 0 && (
        <div className="absolute z-30 mt-1 max-h-44 w-full overflow-auto rounded-lg border border-[#E5E5EA] bg-white p-1 shadow-lg"
          data-testid={`${testId}-suggestions`}>
          {sugg.map((s) => (
            <button key={s.name} type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => add(s.name)}
              data-testid={`${testId}-suggestion-${s.name}`}
              className="flex w-full items-center justify-between rounded px-2 py-1 text-left text-[11.5px] hover:bg-[#F5F5F7]">
              <span>{s.name}</span>
              <span className="text-[10px] text-[#9A9BA3]">{s.uses ? `${s.uses}×` : ""}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
