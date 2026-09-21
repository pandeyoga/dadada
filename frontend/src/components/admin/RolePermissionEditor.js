import React, { useMemo } from "react";
import { GitBranch, Ban, RotateCcw, Layers, Building2 } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { WEIGHT_CLS, SOURCE_BADGE, sortActions } from "@/components/admin/permissionsMeta";
import { ADMIN } from "@/constants/testIds";

/**
 * Editor Hak Akses PER PERAN — alternatif ramah dari matriks besar.
 *
 * Alur: pilih SATU peran → atur izinnya per modul dengan sakelar (bukan membaca ratusan sel
 * sekaligus). Ditambah kartu "Akses bagian RAB" agar satu peran bisa dibatasi hanya melihat
 * sebagian bagian RAB (Umum saja, Fasum/Fasos saja, atau beberapa).
 *
 * Komponen ini PRESENTASIONAL: seluruh state & penyimpanan tetap dikelola AdminPermissions
 * (satu sumber kebenaran), jadi tombol Simpan/hitung perubahan tetap satu untuk kedua mode.
 */
export default function RolePermissionEditor({
  editable, server, roles, role, onRole,
  roleLabel, labelOf, actionLabel, actionHelp, actionWeight,
  effective, written, toggle, restoreDefault,
  rabMeta, rabAllowed, onRabToggle,
}) {
  const meta = useMemo(() => server?.resource_meta || {}, [server]);
  const order = useMemo(() => server?.group_order || [], [server]);

  // Aksi yang RELEVAN untuk satu resource = gabungan aksi yang muncul di bawaan, di matriks
  // tersimpan, dan grant kode — supaya kita tidak menyodorkan 14 sakelar untuk setiap modul.
  const resActions = useMemo(() => {
    const map = {};
    (server?.resources || []).forEach((res) => {
      const set = new Set();
      const def = server?.defaults?.[res] || {};
      const mat = server?.matrix?.[res] || {};
      Object.values(def).forEach((arr) => (arr || []).forEach((a) => set.add(a)));
      Object.values(mat).forEach((arr) => (arr || []).forEach((a) => set.add(a)));
      const g = (server?.code_grants?.[role] || {})[res] || [];
      g.forEach((a) => set.add(a));
      if (!set.size) (server?.actions || []).forEach((a) => set.add(a));
      map[res] = sortActions([...set]).sort((x, y) => actionWeight(x) - actionWeight(y));
    });
    return map;
  }, [server, role, actionWeight]);

  const grouped = useMemo(() => {
    const map = new Map();
    (server?.resources || []).forEach((r) => {
      const g = meta[r]?.group || "Lainnya";
      if (!map.has(g)) map.set(g, []);
      map.get(g).push(r);
    });
    return [...map.entries()].sort((a, b) => {
      const ia = order.indexOf(a[0]); const ib = order.indexOf(b[0]);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
  }, [server, meta, order]);

  if (!role) return null;
  const isCustom = server?.role_meta?.[role]?.custom;

  return (
    <div data-testid={ADMIN.roleEditor} className="space-y-4">
      {/* Pemilih peran */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border bg-card p-3 shadow-[var(--shadow-card)]">
        <Layers className="h-5 w-5 text-primary" />
        <div className="min-w-[220px]">
          <label className="mb-1 block text-[11px] font-medium text-muted-foreground">
            Pilih peran untuk dikonfigurasi
          </label>
          <Select value={role} onValueChange={onRole}>
            <SelectTrigger data-testid={ADMIN.roleEditorSelect} className="h-9 w-64">
              <SelectValue placeholder="Pilih peran…" />
            </SelectTrigger>
            <SelectContent>
              {roles.map((r) => (
                <SelectItem key={r} value={r}>
                  {roleLabel(r)}{server?.role_meta?.[r]?.custom ? " (kustom)" : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          Mengatur <b>{roleLabel(role)}</b>{isCustom ? " (peran kustom)" : ""}. Nyalakan/matikan
          aksi per modul. Perubahan baru berlaku setelah <b>Simpan</b>.
        </p>
      </div>

      {/* Akses bagian RAB */}
      {rabMeta?.length ? (
        <div data-testid={ADMIN.rabSectionsCard}
          className="rounded-xl border border-primary/30 bg-primary/[0.03] p-3 shadow-[var(--shadow-card)]">
          <div className="mb-2 flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary" />
            <p className="text-sm font-semibold">Akses bagian RAB / BoQ</p>
          </div>
          <p className="mb-2 text-[11px] text-muted-foreground">
            Batasi bagian RAB yang boleh dilihat peran ini. Semua aktif = melihat seluruh
            bagian (bawaan). Butuh izin melihat modul <b>BoQ & RAB</b> lebih dulu.
          </p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {rabMeta.map((s) => {
              const on = rabAllowed.includes(s.code);
              return (
                <button key={s.code} type="button" data-testid={ADMIN.rabSectionToggle}
                  data-section={s.code} data-on={on} disabled={!editable}
                  onClick={() => onRabToggle(role, s.code, !on)}
                  className={`rounded-lg border px-3 py-2 text-left transition ${on
                    ? "border-primary bg-primary/10"
                    : "border-slate-200 bg-card hover:border-slate-300"} ${!editable ? "opacity-60" : ""}`}>
                  <span className="flex items-center gap-2 text-xs font-medium">
                    <span className={`inline-block h-3.5 w-3.5 rounded-full border ${on
                      ? "border-primary bg-primary" : "border-slate-300 bg-transparent"}`} />
                    {s.label}
                  </span>
                  <span className="mt-0.5 block text-[10px] text-muted-foreground">{s.help}</span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* Modul per grup */}
      <div className="space-y-4">
        {grouped.map(([group, list]) => (
          <div key={group} data-testid={ADMIN.roleEditorGroup} data-group={group}
            className="rounded-xl border bg-card shadow-[var(--shadow-card)]">
            <div className="border-b bg-secondary/50 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
              {group} · {list.length} modul
            </div>
            <div className="divide-y">
              {list.map((res) => {
                const eff = effective(res, role);
                const w = written(res, role);
                const checkedList = w === null ? eff.perms : w;
                return (
                  <div key={res} data-testid={ADMIN.roleEditorResource} data-resource={res}
                    className="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-[180px]">
                      <p className="text-xs font-semibold">{labelOf(res)}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">{res}</p>
                      {eff.sources?.length ? (
                        <div className="mt-1 flex flex-wrap items-center gap-1">
                          {eff.sources.map((s) => (
                            <span key={s} data-testid={ADMIN.permsSource}
                              className={`inline-flex items-center gap-1 rounded border px-1 py-0.5 text-[9px] uppercase ${SOURCE_BADGE[s]?.cls || ""}`}>
                              {s === "inherited" ? <GitBranch className="h-2.5 w-2.5" /> : null}
                              {s === "revoked" ? <Ban className="h-2.5 w-2.5" /> : null}
                              {SOURCE_BADGE[s]?.text || s}
                              {s === "inherited" && eff.inheritedFrom
                                ? `: ${roleLabel(eff.inheritedFrom)}` : ""}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    <div className="flex flex-1 flex-wrap items-center justify-start gap-1.5 sm:justify-end">
                      {(resActions[res] || []).map((a) => {
                        const active = checkedList.includes(a);
                        const fromCode = ((server?.code_grants?.[role] || {})[res] || []).includes(a);
                        const blocked = (server?.denied_actions?.[role] || []).includes(a);
                        return (
                          <button key={a} type="button" data-testid={ADMIN.roleEditorAction}
                            data-action={a} data-active={active} data-resource={res}
                            disabled={!editable || blocked}
                            title={actionHelp(a)}
                            onClick={() => toggle(res, role, a)}
                            className={`rounded-full border px-2.5 py-1 text-[11px] transition ${active
                              ? `${WEIGHT_CLS[actionWeight(a)] || ""} font-medium ring-1 ring-inset ring-current/20`
                              : "border-dashed border-slate-300 bg-transparent text-muted-foreground hover:border-slate-400"}
                              ${blocked ? "cursor-not-allowed opacity-40" : ""}`}>
                            {actionLabel(a)}
                            {fromCode ? <span className="ml-1 text-[8px] uppercase text-sky-600">kode</span> : null}
                          </button>
                        );
                      })}
                      {editable ? (
                        <button type="button" data-testid={ADMIN.roleEditorRestore}
                          onClick={() => restoreDefault(res, role)}
                          title="Kembalikan modul ini ke izin bawaan"
                          className="ml-1 inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] text-primary hover:bg-primary/5">
                          <RotateCcw className="h-3 w-3" /> Bawaan
                        </button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
