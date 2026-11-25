import React, { useCallback } from "react";
import { FileText, Receipt, FileSignature } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import ListRow from "../../components/ListRow";
import StatusChip from "../../components/StatusChip";
import { listDocuments } from "../../services/api/buyer";
import { rupiah, tanggal } from "../../lib/format";
import useLoad from "./useLoad";
import Page, { Loading } from "./Page";

const tone = (s) => (s === "terverifikasi" ? "ok" : s === "diperiksa" ? "warn" : "neutral");
const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);

function Group({ title, children }) {
  return (
    <section>
      <h2 className="mb-2 text-[17px] font-extrabold">{title}</h2>
      <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">{children}</FrostCard>
    </section>
  );
}

export default function Documents() {
  const fetcher = useCallback(() => listDocuments(), []);
  const { data } = useLoad(fetcher);
  return (
    <Page id="P8" title="Dokumen">
      {!data && <Loading />}
      {data && (
        <>
          <Group title="Perjanjian">
            {data.contracts.map((c) => (
              <ListRow key={c.id} icon={FileSignature} title={c.title} right={<StatusChip tone="neutral">{cap(c.status)}</StatusChip>} />
            ))}
            {data.files.filter((f) => f.id === "doc-5").map((f) => (
              <ListRow key={f.id} icon={FileText} title={f.title} subtitle={tanggal(f.at)} right={<StatusChip tone={tone(f.status)}>{cap(f.status)}</StatusChip>} />
            ))}
          </Group>
          <Group title="Berkas KPR">
            {data.files.filter((f) => f.id !== "doc-5").map((f) => (
              <ListRow key={f.id} icon={FileText} title={f.title} subtitle={tanggal(f.at)} right={<StatusChip tone={tone(f.status)}>{cap(f.status)}</StatusChip>} />
            ))}
          </Group>
          <Group title="Kuitansi">
            {data.receipts.length === 0 && <p className="p-4 text-[14px] text-[color:var(--rdg-muted)]">Belum ada kuitansi.</p>}
            {data.receipts.map((r) => (
              <ListRow key={r.id} icon={Receipt} title={r.title} subtitle={`${r.id.toUpperCase()} · ${tanggal(r.paidAt)}`} right={<span className="text-[14px] font-bold">{rupiah(r.amount)}</span>} />
            ))}
          </Group>
        </>
      )}
    </Page>
  );
}
