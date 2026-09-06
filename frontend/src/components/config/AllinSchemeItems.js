import React from "react";
import { Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RupiahInput } from "@/components/ui/rupiah-input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const TREATMENTS = { developer_borne: "Developer (all-in)", customer_pass_through: "Pembeli (titipan)" };

export const AllinSchemeItems = ({ items, components, onChange }) => {
  const patch = (i, change) => onChange(items.map((item, j) => i === j ? { ...item, ...change } : item));
  return <div className="min-w-0 space-y-3" data-testid="allin-items-editor">
    {items.map((it, i) => <div key={i} data-testid={`allin-item-${i}`} className="grid min-w-0 grid-cols-1 gap-3 border-b pb-3 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
      <div className="min-w-0 space-y-1">
        <Label htmlFor={`allin-component-${i}`}>Komponen {i + 1}</Label>
        <Select value={it.component_code} onValueChange={v => patch(i, { component_code: v })}>
          <SelectTrigger id={`allin-component-${i}`} data-testid={`allin-component-${i}`}><SelectValue placeholder="Pilih komponen" /></SelectTrigger>
          <SelectContent>{components.filter(c => !c.is_legacy).map(c => <SelectItem key={c.code} value={c.code} data-testid={`allin-component-option-${i}-${c.code}`} disabled={items.some((x, j) => j !== i && x.component_code === c.code)}>{c.name}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="min-w-0 space-y-1">
        <Label htmlFor={`allin-treatment-${i}`}>Ditanggung oleh</Label>
        <Select value={it.treatment} onValueChange={v => patch(i, { treatment: v })}>
          <SelectTrigger id={`allin-treatment-${i}`} data-testid={`allin-treatment-${i}`}><SelectValue /></SelectTrigger>
          <SelectContent>{Object.entries(TREATMENTS).map(([k, v]) => <SelectItem key={k} value={k} data-testid={`allin-treatment-option-${i}-${k}`}>{v}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="min-w-0 space-y-1">
        <Label htmlFor={`allin-amount-${i}`}>Nominal pengganti (opsional)</Label>
        <RupiahInput id={`allin-amount-${i}`} data-testid={`allin-amount-${i}`} placeholder="Sesuai rumus" value={it.override_amount ?? ""} onChange={e => patch(i, { override_amount: e.target.value })} />
      </div>
      <div className="flex items-end justify-end">
        <Button type="button" variant="ghost" size="icon" data-testid={`allin-remove-${i}`} aria-label={`Hapus komponen ${i + 1}`} title={`Hapus komponen ${i + 1}`} onClick={() => onChange(items.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></Button>
      </div>
    </div>)}
    <Button type="button" size="sm" variant="secondary" data-testid="allin-add-component" onClick={() => onChange([...items, { component_code: "", treatment: "customer_pass_through", override_amount: "" }])}><Plus className="mr-1 h-4 w-4" />Komponen</Button>
  </div>;
};