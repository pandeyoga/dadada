import React, { useCallback, useState } from "react";
import { FileText, Eye } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import ListRow from "../../../components/ListRow";
import StatusChip from "../../../components/StatusChip";
import Sheet from "../../../components/Sheet";
import DocIllustration from "./DocIllustration";
import { listHomeDocuments } from "../../../services/api/care";
import useLoad from "../../../lib/useLoad";

const fetchAll = () => listHomeDocuments();

/** W23: dokumen rumah dengan status dan pratinjau lokal. */
export default function HomeDocuments() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["care", "buyer", "bills"]);
  const [doc, setDoc] = useState(null);
  return (
    <Page id="W23" title="Dokumen rumah" back="/app/warga/layanan" nav="resident">
      {!data && <Loading error={error} />}
      {data && (
        <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
          {data.map((d) => (
            <ListRow key={d.id} icon={FileText} title={d.title} onClick={() => setDoc(d)}
              subtitle={<><span className="block">{d.note}</span><span className="mt-1.5 flex items-center gap-2"><StatusChip tone={d.tone} icon={null}>{d.status}</StatusChip><span className="inline-flex items-center gap-1 text-[12.5px] font-bold text-rdg-forest"><Eye size={14} aria-hidden="true" /> Lihat</span></span></>}
              right={<span />} />
          ))}
        </FrostCard>
      )}
      <Sheet open={Boolean(doc)} onClose={() => setDoc(null)} title={doc ? doc.title : "Dokumen"}>
        {doc && (
          <div className="space-y-3">
            <DocIllustration kind={doc.kind} title={doc.title} className="mx-auto h-64 w-auto" />
            <p className="text-center text-[13.5px] text-[color:var(--rdg-muted)]">Pratinjau contoh. Berkas asli diserahkan pengelola saat serah terima.</p>
            <button type="button" className="rdg-btn-ghost w-full" onClick={() => setDoc(null)}>Tutup</button>
          </div>
        )}
      </Sheet>
    </Page>
  );
}
