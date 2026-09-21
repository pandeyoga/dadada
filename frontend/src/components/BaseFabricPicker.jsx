import { useEffect, useState } from "react";
import { Ban, Check, Layers3, Search } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { catalogApi, catalogError } from "../features/catalog/catalogApi";

const TYPES = [["", "Semua"], ["woven", "Woven"], ["knit", "Knit"]];

/** Pemilih "kain dasar" dari master data induk produk — klik → popup cari/filter. */
export default function BaseFabricPicker({ value, valueName, onChange, excludeId = "", disabled = false, testId = "base-fabric" }) {
  const [open, setOpen] = useState(false);
  return <>
    <button type="button" data-testid={`${testId}-trigger`} disabled={disabled}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}
      className="field flex w-full items-center justify-between gap-2 text-left disabled:opacity-60">
      <span data-testid={`${testId}-value`} className={`truncate ${value ? "font-semibold text-[#1C1C1E]" : "text-[#8E8E93]"}`}>
        {value ? (valueName || value) : "— Tidak ada —"}
      </span>
      <Layers3 size={14} className="shrink-0 text-[#6B6B73]" />
    </button>
    {open && <BaseFabricDialog value={value} excludeId={excludeId} testId={testId} onClose={() => setOpen(false)}
      onPick={(tpl) => { onChange(tpl); setOpen(false); }} />}
  </>;
}

function BaseFabricDialog({ value, excludeId, testId, onClose, onPick }) {
  const [q, setQ] = useState(""); const [type, setType] = useState("");
  const [rows, setRows] = useState(null); const [error, setError] = useState("");
  useEffect(() => {
    let live = true; setError("");
    const t = setTimeout(() => catalogApi.list({ search: q, limit: 80, paginate: true })
      .then((d) => { if (live) setRows(d.items || []); })
      .catch((e) => { if (live) setError(catalogError(e)); }), 250);
    return () => { live = false; clearTimeout(t); };
  }, [q]);
  const list = (rows || []).filter((t) => t.id !== excludeId && (!type || t.fabric_type === type));
  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent data-testid={`${testId}-dialog`} closeTestId={`${testId}-close`} overlayClassName="!z-[240]"
        className="!z-[245] flex max-h-[85vh] w-[calc(100%-24px)] max-w-2xl flex-col overflow-hidden bg-white p-0">
        <div className="border-b border-[#EFF0F2] px-4 py-3">
          <DialogTitle className="text-[14px] font-bold">Pilih kain dasar dari master data</DialogTitle>
          <DialogDescription className="text-[11px] text-[#6B6B73]">Kain polos/woven dari master data yang menjadi sumber bahan (mis. untuk labdip & printing).</DialogDescription>
        </div>
        <div className="space-y-2 border-b border-[#EFF0F2] px-4 py-3">
          <div className="flex items-center gap-2 rounded-lg bg-[#F2F3F5] px-3 py-2">
            <Search size={14} className="text-[#8E8E93]" />
            <input autoFocus data-testid={`${testId}-search`} value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Cari nama induk, kategori, atau prefix SKU…" className="w-full bg-transparent text-[13px] outline-none" />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {TYPES.map(([v, l]) => <button type="button" key={v} data-testid={`${testId}-type-${v || "all"}`} onClick={() => setType(v)}
              className={`rounded-full border px-3 py-1 text-[11.5px] font-semibold ${type === v ? "border-[#0058CC] bg-[#0058CC] text-white" : "border-[#E5E5EA] bg-white text-[#3A3A3C]"}`}>{l}</button>)}
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {error && <p data-testid={`${testId}-error`} role="alert" className="m-2 rounded bg-red-50 p-2 text-xs text-red-700">{error}</p>}
          <button type="button" data-testid={`${testId}-none`} onClick={() => onPick(null)}
            className={`mb-1 flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-[12.5px] ${!value ? "border-[#0058CC] bg-[#EAF2FF]" : "border-[#EFF0F2] hover:bg-[#FAFBFC]"}`}>
            <Ban size={14} className="text-[#8E8E93]" /><span className="font-semibold">— Tidak ada —</span>
            <span className="text-[11px] text-[#8E8E93]">Produk tidak bersumber dari kain master data lain</span>
          </button>
          {rows === null && !error && <p className="p-3 text-xs text-[#8E8E93]" data-testid={`${testId}-loading`}>Memuat master data…</p>}
          {rows !== null && !list.length && <p className="p-3 text-xs text-[#8E8E93]" data-testid={`${testId}-empty`}>Tidak ada induk master data yang cocok.</p>}
          {list.map((t) => <button type="button" key={t.id} data-testid={`${testId}-option-${t.id}`} onClick={() => onPick(t)}
            className={`mb-1 flex w-full items-start justify-between gap-3 rounded-lg border px-3 py-2 text-left ${value === t.id ? "border-[#0058CC] bg-[#EAF2FF]" : "border-[#EFF0F2] hover:bg-[#FAFBFC]"}`}>
            <span className="min-w-0">
              <span className="block truncate text-[12.5px] font-semibold">{t.name}</span>
              <span className="block text-[11px] text-[#6B6B73]">{t.category} · {t.fabric_type || "—"} · {t.motif || "—"} · {t.stage || "—"}</span>
              <span className="block text-[10.5px] text-[#8E8E93]">{t.gramasi ? `${t.gramasi} gsm` : "— gsm"} · {t.lebar ? `lebar ${t.lebar} m` : "lebar —"} · {t.variant_count || 0} SKU</span>
            </span>
            <span className="flex shrink-0 items-center gap-1 font-mono text-[10.5px] text-[#6B6B73]">{t.sku_prefix}{value === t.id && <Check size={13} className="text-[#0058CC]" />}</span>
          </button>)}
        </div>
      </DialogContent>
    </Dialog>
  );
}
