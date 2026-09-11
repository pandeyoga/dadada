import React, { useCallback, useEffect, useState } from "react";
import { History, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import DataTable from "@/components/patterns/DataTable";
import StatusPill from "@/components/patterns/StatusPill";
import PricingRuleDialog, { APPROVAL_MODE_LABEL, RULE_META } from "@/components/config/PricingRuleDialog";
import CouponRedemptionsDialog from "@/components/config/CouponRedemptionsDialog";
import api from "@/services/apiClient";
import { useReference } from "@/context/ReferenceContext";
import { useAuth } from "@/context/AuthContext";
import { formatDateWIB, formatIDR } from "@/utils/formatters";
import { PRICING } from "@/constants/testIds";

const valueText = (r) => (r.kind === "percent" ? `${r.value}%` : formatIDR(r.value))
  + (r.max_amount ? ` (maks ${formatIDR(r.max_amount)})` : "");

const periodText = (r) => (!r.valid_from && !r.valid_until ? "Tanpa batas"
  : `${r.valid_from ? formatDateWIB(r.valid_from) : "…"} – ${r.valid_until ? formatDateWIB(r.valid_until) : "…"}`);

/** Tabel generik satu jenis aturan harga (skema diskon / promo / kupon). */
export default function PricingRuleTable({ kind }) {
  const meta = RULE_META[kind];
  const { labelOf } = useReference();
  const { can } = useAuth();
  const mayUpdate = can("pricing", "update");
  const [toggling, setToggling] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState({ q: "", sort: "code", direction: "asc", skip: 0, limit: 50 });
  const [form, setForm] = useState(null);
  const [redeemFor, setRedeemFor] = useState(null);
  const [projectNames, setProjectNames] = useState({});

  useEffect(() => {
    api.get("/projects", { params: { limit: 100 } }).then((r) => setProjectNames(
      Object.fromEntries((r.data.data || []).map((p) => [p.id, p.name])))).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const res = await api.get(`/pricing/${meta.slug}`);
      setRows(res.data.data || []);
    } catch (e) {
      setError(e?.response?.data?.detail || `Gagal memuat ${meta.label.toLowerCase()}.`);
    } finally { setLoading(false); }
  }, [meta.slug, meta.label]);

  useEffect(() => { load(); }, [load]);

  const modeOf = (r) => r.approval_mode || (r.requires_approval ? "always" : "global");
  const toggleApproval = async (r, on) => {
    const mode = on ? "always" : "global";
    setToggling(r.id);
    try {
      const res = await api.put(`/pricing/${meta.slug}/${r.id}`, { approval_mode: mode, requires_approval: on });
      setRows((rs) => rs.map((x) => (x.id === r.id ? { ...x, ...res.data.data } : x)));
      toast.success(`${r.code}: ${on ? "selalu perlu persetujuan manajer" : "ikut ambang organisasi"}.`);
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal mengubah mode persetujuan."); } finally { setToggling(""); }
  };

  const filtered = rows.filter((r) => {
    const q = (query.q || "").toLowerCase();
    return !q || `${r.code} ${r.name}`.toLowerCase().includes(q);
  });

  const columns = [
    { key: "code", header: "Kode", sortable: true,
      render: (r) => <span className="font-mono text-xs">{r.code}</span> },
    { key: "name", header: meta.label, sortable: true,
      render: (r) => (
        <div>
          <div className="font-medium">{r.name}</div>
          {r.note ? <div className="text-xs text-muted-foreground">{r.note}</div> : null}
          {kind === "promo" && r.stackable === false ? (
            <div className="text-xs text-amber-700">Tidak bisa digabung kupon</div>
          ) : null}
        </div>
      ) },
    { key: "value", header: "Potongan", align: "right", sortable: true,
      render: (r) => <span className="tabular-nums">{valueText(r)}</span>,
      exportValue: (r) => r.value },
    { key: "kind", header: "Jenis", render: (r) => labelOf("discount_kind", r.kind) },
    { key: "target", header: "Sasaran", render: (r) => (
      <span className="text-xs" data-testid={`pricing-rule-target-${r.code}`}>
        {labelOf("discount_target", r.target || "price")}
        {r.target === "cost" && r.target_component ? ` · ${r.target_component}` : ""}
      </span>
    ), exportValue: (r) => (r.target === "cost" ? `cost:${r.target_component}` : (r.target || "price")) },
    { key: "valid_from", header: "Periode", sortable: true,
      render: (r) => (
        <div className="text-xs">
          <div>{periodText(r)}</div>
          {!r.in_window ? <div className="text-rose-700">Di luar periode</div> : null}
        </div>
      ), exportValue: (r) => periodText(r) },
    ...(kind === "coupon" ? [{
      key: "used_count", header: "Kuota", align: "right", sortable: true,
      render: (r) => (
        <div className="text-xs tabular-nums">
          <div>{r.used_count || 0}{r.quota_total ? ` / ${r.quota_total}` : " / ∞"} terpakai</div>
          <div className="text-muted-foreground">
            {r.quota_per_customer ? `${r.quota_per_customer}× per pembeli` : "tanpa batas per pembeli"}
          </div>
        </div>
      ), exportValue: (r) => r.used_count || 0,
    }] : []),
    { key: "scope", header: "Berlaku untuk",
      render: (r) => (
        <div className="max-w-[220px] text-xs text-muted-foreground">
          <div className="truncate" title={(r.applies_project_ids || []).map((id) => projectNames[id] || id).join(", ")}>
            {(r.applies_project_ids || []).length
              ? (r.applies_project_ids || []).map((id) => projectNames[id] || id).join(", ")
              : "Semua proyek"}
          </div>
          <div className="truncate">
            {(r.applies_unit_types || []).length ? `Tipe: ${(r.applies_unit_types || []).join(", ")}` : "Semua tipe unit"}
          </div>
        </div>
      ), exportValue: (r) => (r.applies_project_ids || []).map((id) => projectNames[id] || id).join("|") },
    { key: "approval_mode", header: "Approval manajer",
      render: (r) => {
        const mode = modeOf(r);
        return (
          <div className="flex flex-col gap-0.5">
            <Switch data-testid={`pricing-rule-approval-toggle-${r.code}`} checked={mode === "always"}
              disabled={!mayUpdate || toggling === r.id} aria-label={`Approval manajer ${r.code}`}
              onCheckedChange={(v) => toggleApproval(r, v)} />
            <span data-testid={`pricing-rule-approval-${r.code}`} data-mode={mode}
              className={`text-[11px] ${mode === "always" ? "text-amber-700" : mode === "never" ? "text-emerald-700" : "text-muted-foreground"}`}>
              {APPROVAL_MODE_LABEL[mode]}
            </span>
          </div>
        );
      }, exportValue: (r) => modeOf(r) },
    { key: "active", header: "Status",
      render: (r) => <StatusPill status={r.active ? "active" : "inactive"} label={r.active ? "Aktif" : "Nonaktif"} />,
      exportValue: (r) => (r.active ? "aktif" : "nonaktif") },
    { key: "actions", header: "Aksi", align: "right", sticky: true,
      render: (r) => (
        <div className="flex justify-end gap-1">
          {kind === "coupon" ? (
            <Button data-testid={PRICING.redemptionsBtn} size="sm" variant="ghost"
              aria-label={`Riwayat pemakaian ${r.code}`} onClick={() => setRedeemFor(r)}>
              <History className="h-3.5 w-3.5" />
            </Button>
          ) : null}
          <Button data-testid={PRICING.editBtn} size="sm" variant="ghost"
            aria-label={`Ubah ${r.code}`} onClick={() => setForm(r)}>
            <Pencil className="h-3.5 w-3.5" />
          </Button>
        </div>
      ), exportValue: () => "" },
  ];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">{meta.help}</p>
        <Button data-testid={PRICING.addBtn} size="sm" onClick={() => setForm({})}>
          <Plus className="mr-1.5 h-4 w-4" /> {meta.label} baru
        </Button>
      </div>
      <DataTable
        testId={PRICING.table}
        testIds={{ search: `${PRICING.table}-search`, row: PRICING.row,
          export: `${PRICING.table}-export`, columns: `${PRICING.table}-columns` }}
        columns={columns} rows={filtered} total={filtered.length} query={query}
        onQueryChange={(p) => setQuery((q) => ({ ...q, ...p }))}
        loading={loading} error={error} onRefresh={load}
        searchPlaceholder={`Cari ${meta.label.toLowerCase()}…`} exportName={meta.slug}
        emptyTitle={`Belum ada ${meta.label.toLowerCase()}`} />
      {form !== null ? (
        <PricingRuleDialog kind={kind} source={form} open onOpenChange={(o) => { if (!o) setForm(null); }}
          onSaved={() => { setForm(null); load(); }} />
      ) : null}
      {redeemFor ? (
        <CouponRedemptionsDialog coupon={redeemFor} open
          onOpenChange={(o) => { if (!o) setRedeemFor(null); }} />
      ) : null}
    </div>
  );
}
