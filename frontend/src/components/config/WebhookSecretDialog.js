import React, { useState } from "react";
import { toast } from "sonner";
import { Eye, EyeOff, Info } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import api from "@/services/apiClient";
import { isInternalPermissionMessage, readDetail } from "@/utils/panelLoad";
import { WEBHOOK_SEC } from "@/constants/testIds";

export const MIN_SECRET_LEN = 8;   // sama dengan backend (`webhook_security.MIN_SECRET_LEN`)

// Nama kolom rahasia di dashboard penyedia, supaya admin tahu nilai apa yang ditempel.
const SECRET_LABEL = {
  meta_lead: "App Secret aplikasi Meta (Settings › Basic)",
  google_lead: "Key webhook Lead Form Google Ads",
  tiktok_lead: "Rahasia webhook TikTok",
};

/** Kalimat galat yang terbaca: pesan server apa adanya, kecuali nama izin internal. */
export function webhookError(e, fallback) {
  if (e?.response?.status === 403) return "Peran Anda tidak boleh mengubah rahasia webhook (butuh izin kelola Pusat Konfigurasi).";
  const d = readDetail(e);
  return d && !isInternalPermissionMessage(d) ? d : fallback;
}

function EnvList({ names }) {
  return names.map((n, i) => (
    <React.Fragment key={n}>{i ? " atau " : ""}<code>{n}</code></React.Fragment>
  ));
}

function SecretField({ id, label, value, onChange, testId, placeholder, help }) {
  const [shown, setShown] = useState(false);
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input id={id} data-testid={testId} type={shown ? "text" : "password"} autoComplete="new-password"
          spellCheck={false} value={value} placeholder={placeholder} className="pr-10 font-mono"
          onChange={(e) => onChange(e.target.value)} />
        <button type="button" aria-label={shown ? "Sembunyikan isian" : "Tampilkan isian"}
          className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
          onClick={() => setShown((v) => !v)}>
          {shown ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {help ? <p className="text-[11px] text-muted-foreground">{help}</p> : null}
    </div>
  );
}

/**
 * Isi / ganti rahasia satu kanal. Nilai lama TIDAK PERNAH ditampilkan (server pun tak mengirimnya):
 * kolom selalu mulai kosong dan kolom kosong = tidak diubah. Komponen ini dipasang hanya selama dialog terbuka,
 * jadi nilai yang diketik hilang begitu dialog ditutup.
 */
export default function WebhookSecretDialog({ channel, onClose, onSaved }) {
  const [secret, setSecret] = useState("");
  const [verify, setVerify] = useState("");
  const [busy, setBusy] = useState(false);
  const hasVerify = channel.verify_token_configured != null;
  const secretOk = !secret.trim() || secret.trim().length >= MIN_SECRET_LEN;
  const verifyOk = !verify.trim() || verify.trim().length >= MIN_SECRET_LEN;
  const empty = !secret.trim() && !verify.trim();

  const submit = async () => {
    const body = {};
    if (secret.trim()) body.secret = secret.trim();
    if (hasVerify && verify.trim()) body.verify_token = verify.trim();
    setBusy(true);
    try {
      const r = await api.put(`/webhooks/secrets/${channel.channel}`, body);
      toast.success(`Rahasia ${channel.label} disimpan. Pasang nilai yang sama di dashboard penyedia.`);
      setSecret(""); setVerify("");
      onSaved(r.data?.data);
    } catch (e) {
      toast.error(webhookError(e, "Gagal menyimpan rahasia webhook."));
    } finally { setBusy(false); }
  };

  const envs = channel.env_secret || [];
  const envVerify = channel.env_verify || [];
  return (
    <Dialog open onOpenChange={(o) => { if (!o && !busy) onClose(); }}>
      <DialogContent data-testid={WEBHOOK_SEC.dialog} className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{channel.secret_configured ? "Ganti" : "Isi"} rahasia {channel.label}</DialogTitle>
          <DialogDescription>
            Begitu rahasia terisi, kanal ini WAJIB bertanda tangan: permintaan tanpa tanda tangan yang cocok ditolak.
            Nilai yang sudah tersimpan tidak pernah ditampilkan.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-3" autoComplete="off" onSubmit={(e) => { e.preventDefault(); if (!empty && secretOk && verifyOk && !busy) submit(); }}>
          <SecretField id="wh-secret" label={SECRET_LABEL[channel.channel] || "Rahasia"} value={secret} onChange={setSecret}
            testId={WEBHOOK_SEC.inputSecret}
            placeholder={channel.secret_configured ? "Kosongkan = tidak diubah" : `Minimal ${MIN_SECRET_LEN} karakter`}
            help={secret.trim() && !secretOk ? `Minimal ${MIN_SECRET_LEN} karakter.` : null} />
          {hasVerify ? (
            <SecretField id="wh-verify" label="Verify token (handshake)" value={verify} onChange={setVerify}
              testId={WEBHOOK_SEC.inputVerify}
              placeholder={channel.verify_token_configured ? "Kosongkan = tidak diubah" : `Minimal ${MIN_SECRET_LEN} karakter`}
              help={verify.trim() && !verifyOk ? `Minimal ${MIN_SECRET_LEN} karakter.` : null} />
          ) : null}
          <div data-testid={WEBHOOK_SEC.envHint} className="flex gap-2 rounded-md border bg-secondary/40 p-2.5 text-[11px] text-muted-foreground">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <p>
              Alternatif: set variabel lingkungan di server
              {envs.length ? <> <EnvList names={envs} /></> : null}
              {envVerify.length ? <> (verify token: <EnvList names={envVerify} />)</> : null}.
              Nilai yang disimpan di sini diutamakan di atas ENV; ENV dipakai bila nilai di sini dicabut.
            </p>
          </div>
          <p className="rounded-md border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">
            Pasang rahasia yang <b>sama persis</b> di dashboard penyedia. Kalau tidak, lead asli ikut ditolak dan
            tidak masuk antrean &ldquo;Gagal Masuk&rdquo;.
          </p>
          <DialogFooter>
            <Button type="button" variant="outline" data-testid={WEBHOOK_SEC.cancel} disabled={busy} onClick={onClose}>Batal</Button>
            <Button type="submit" data-testid={WEBHOOK_SEC.submit} disabled={busy || empty || !secretOk || !verifyOk}>
              {busy ? "Menyimpan…" : "Simpan rahasia"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
