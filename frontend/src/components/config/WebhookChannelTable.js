import React from "react";
import { Ban, KeyRound, MessageCircle, ShieldAlert, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { formatDateTimeWIB } from "@/utils/formatters";
import { WEBHOOK_SEC } from "@/constants/testIds";

const SOURCE_LABEL = {
  db: "Tersimpan di sistem (terenkripsi)",
  env: "Dari variabel lingkungan server (ENV)",
  none: "Belum diisi",
};

/** Lencana aman / belum aman — satu-satunya penanda status kanal. */
export function SecurityBadge({ secure, channel }) {
  return secure ? (
    <span data-testid={WEBHOOK_SEC.badge} data-channel={channel} data-secure="true"
      className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
      <ShieldCheck className="h-3.5 w-3.5" /> Aman
    </span>
  ) : (
    <span data-testid={WEBHOOK_SEC.badge} data-channel={channel} data-secure="false"
      className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-900">
      <ShieldAlert className="h-3.5 w-3.5" /> Belum aman
    </span>
  );
}

/** Rahasia boleh dicabut dari sini hanya bila memang tersimpan di sistem (nilai ENV dicabut di server). */
export function revocable(c) {
  return {
    secret: c.secret_source === "db",
    verify: c.verify_token_configured != null && c.verify_token_source === "db",
  };
}

function SourceCell({ c }) {
  return (
    <div data-testid={WEBHOOK_SEC.source} data-source={c.secret_source} className="space-y-0.5 text-xs">
      <p>{SOURCE_LABEL[c.secret_source] || SOURCE_LABEL.none}</p>
      {c.verify_token_configured != null ? (
        <p className="text-muted-foreground">
          Verify token: {c.verify_token_configured
            ? (c.verify_token_source === "env" ? "dari ENV" : "tersimpan") : "belum diisi"}
        </p>
      ) : null}
    </div>
  );
}

function RejectedCell({ c }) {
  const n = c.rejected_total || 0;
  return (
    <div data-testid={WEBHOOK_SEC.rejected} data-total={n} className="space-y-0.5 text-xs">
      <p className={n ? "font-semibold text-rose-700" : ""}>
        <Ban className="mr-1 inline h-3 w-3" />{n} ditolak
      </p>
      {c.last_rejected_at ? <p className="text-muted-foreground">Terakhir {formatDateTimeWIB(c.last_rejected_at)}</p> : null}
      {c.last_ok_at ? <p className="text-muted-foreground">Terakhir sah {formatDateTimeWIB(c.last_ok_at)}</p> : null}
    </div>
  );
}

function ActionsCell({ c, canManage, onSet, onClear, onOpenWa }) {
  if (!canManage) return <span className="text-xs text-muted-foreground">Hanya baca</span>;
  if (c.managed_via === "wa_config") {
    return (
      <Button size="sm" variant="outline" data-testid={WEBHOOK_SEC.waLink} onClick={onOpenWa}>
        <MessageCircle className="mr-1 h-3.5 w-3.5" /> Atur di Integrasi WhatsApp
      </Button>
    );
  }
  const rv = revocable(c);
  const nothingToClear = !rv.secret && !rv.verify;
  return (
    <div className="flex flex-wrap gap-1.5">
      <Button size="sm" data-testid={WEBHOOK_SEC.setBtn} onClick={() => onSet(c)}>
        <KeyRound className="mr-1 h-3.5 w-3.5" /> {c.secret_configured ? "Ganti" : "Isi"}
      </Button>
      <Button size="sm" variant="outline" className="text-rose-700" data-testid={WEBHOOK_SEC.clearBtn}
        disabled={nothingToClear} onClick={() => onClear(c)}
        title={nothingToClear
          ? (c.secret_configured ? "Rahasia ini berasal dari ENV server; cabut dengan menghapus variabelnya di server." : "Belum ada rahasia yang tersimpan.")
          : "Cabut rahasia tersimpan"}>
        Cabut
      </Button>
    </div>
  );
}

/** Tabel kanal webhook bertanda tangan: status, sumber rahasia, statistik penolakan, aksi. */
export default function WebhookChannelTable({ channels, canManage, onSet, onClear, onOpenWa }) {
  return (
    <Table data-testid={WEBHOOK_SEC.table}>
      <TableHeader>
        <TableRow>
          <TableHead>Kanal</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Sumber rahasia</TableHead>
          <TableHead>Penolakan</TableHead>
          <TableHead className="text-right">Aksi</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {channels.map((c) => (
          <React.Fragment key={c.channel}>
            <TableRow data-testid={WEBHOOK_SEC.row} data-channel={c.channel} data-secure={String(!!c.secure)}
              className={c.secure ? "" : "border-b-0"}>
              <TableCell className="align-top">
                <p className="font-medium">{c.label}</p>
                <p className="font-mono text-[11px] text-muted-foreground">{c.path}</p>
                <p className="mt-0.5 max-w-xs text-[11px] text-muted-foreground">{c.method}</p>
              </TableCell>
              <TableCell className="align-top"><SecurityBadge secure={c.secure} channel={c.channel} /></TableCell>
              <TableCell className="align-top"><SourceCell c={c} /></TableCell>
              <TableCell className="align-top"><RejectedCell c={c} /></TableCell>
              <TableCell className="text-right align-top">
                <div className="flex justify-end">
                  <ActionsCell c={c} canManage={canManage} onSet={onSet} onClear={onClear} onOpenWa={onOpenWa} />
                </div>
              </TableCell>
            </TableRow>
            {c.secure ? null : (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={5} className="pt-0">
                  <p data-testid={WEBHOOK_SEC.warning} data-channel={c.channel}
                    className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                    Rahasia belum dikonfigurasi — endpoint <code>{c.path}</code> menerima permintaan dari SIAPA PUN
                    (hanya layak untuk mode simulasi/uji). Lead palsu bisa masuk dan mengotori CPL/ROAS.
                  </p>
                </TableCell>
              </TableRow>
            )}
          </React.Fragment>
        ))}
      </TableBody>
    </Table>
  );
}
