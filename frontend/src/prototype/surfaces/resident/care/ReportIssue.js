import React, { useCallback, useState } from "react";
import { Plus, Star } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import Sheet from "../../../components/Sheet";
import EmptyState from "../../../components/EmptyState";
import { Msg } from "../security/ui";
import ReportForm from "./ReportForm";
import TicketCard from "./TicketCard";
import { listTickets, confirmTicket } from "../../../services/api/care";
import useLoad from "../../../lib/useLoad";

const fetchTickets = () => listTickets().then((l) => l.filter((t) => t.kind !== "tanya"));

function RatingForm({ ticket, onDone }) {
  const [rating, setRating] = useState(0);
  const [problem, setProblem] = useState("");
  const submit = async () => {
    setProblem("");
    try { await confirmTicket(ticket.id, rating); onDone(); } catch (err) { setProblem(err.message); }
  };
  return (
    <div className="space-y-3">
      <p className="text-[14px] text-[color:var(--rdg-muted)]">{`Apakah perbaikan "${ticket.category}" sudah beres? Beri nilai untuk teknisi.`}</p>
      <div className="flex justify-center gap-1" role="group" aria-label="Nilai">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" aria-label={`${n} bintang`} aria-pressed={rating === n} onClick={() => setRating(n)} className="grid h-12 w-12 place-items-center rounded-xl">
            <Star size={30} aria-hidden="true" className={n <= rating ? "fill-[#f2b705] text-[#b9741a]" : "text-[color:var(--rdg-muted)]"} />
          </button>
        ))}
      </div>
      <Msg error={problem} />
      <button type="button" className="rdg-btn-primary w-full" onClick={submit}>Kirim nilai</button>
    </div>
  );
}

/** W21: lapor kerusakan → linimasa tiket → konfirmasi + nilai. */
export default function ReportIssue() {
  const fetcher = useCallback(fetchTickets, []);
  const { data, error } = useLoad(fetcher, ["care"]);
  const [form, setForm] = useState(false);
  const [rate, setRate] = useState(null);
  return (
    <Page id="W21" title="Lapor kerusakan" back="/app/warga/layanan" nav="resident">
      <button type="button" className="rdg-btn-primary w-full" aria-label="Lapor kerusakan baru" onClick={() => setForm(true)}><Plus size={18} aria-hidden="true" /> Lapor kerusakan baru</button>
      {!data && <Loading error={error} />}
      {data && data.length === 0 && <EmptyState title="Belum ada laporan" body="Laporan kerusakan Anda akan muncul di sini beserta perkembangannya." />}
      {data && data.map((t) => <TicketCard key={t.id} ticket={t} onConfirm={setRate} />)}
      <Sheet open={form} onClose={() => setForm(false)} title="Lapor kerusakan">
        <ReportForm onDone={() => setForm(false)} />
      </Sheet>
      <Sheet open={Boolean(rate)} onClose={() => setRate(null)} title="Konfirmasi dan beri nilai">
        {rate && <RatingForm ticket={rate} onDone={() => setRate(null)} />}
      </Sheet>
    </Page>
  );
}
