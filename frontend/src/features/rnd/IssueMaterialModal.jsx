/** IssueMaterialModal — ambil bahan dari ROLL untuk sample; stok gudang benar-benar berkurang (mutasi `sample_issue`). */
import { useEffect, useState } from "react";
import { PackageMinus } from "lucide-react";
import FormModal from "../../components/FormModal";
import KNSelect from "../../components/KNSelect";
import { formatCurrency, formatQty } from "../../utils/formatters";
import { listRolls } from "./rndApi";
import { errMsg } from "./rndMeta";
import { Field, Footer, Hint } from "./RndField";

export default function IssueMaterialModal({ onClose, onConfirm, busy }) {
  const [rolls, setRolls] = useState([]);
  const [rollId, setRollId] = useState("");
  const [qty, setQty] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => {
    listRolls({ status: "available", limit: 300 })
      .then((r) => { const list = Array.isArray(r) ? r : r?.items || []; setRolls(list.filter((x) => Number(x.length_remaining || 0) > 0)); })
      .catch((e) => setErr(errMsg(e, "Gagal memuat daftar roll.")));
  }, []);
  const roll = rolls.find((r) => r.id === rollId);

  return (
    <FormModal open onClose={onClose} size="md" testId="issue-material-modal" icon={PackageMinus} error={err}
      title="Ambil Bahan untuk Sample" subtitle="Dari roll gudang — stok gudang & stok sample selalu satu angka"
      footer={<Footer onClose={onClose} busy={busy} disabled={!rollId || !qty} icon={PackageMinus} testId="issue-confirm" confirmLabel="Ambil bahan"
        onConfirm={() => onConfirm({ roll_id: rollId, qty, note })} />}>
      <div className="grid gap-3">
        <Hint tone="warn">
          Pengambilan ini <b>mengurangi stok gudang</b> (mutasi <b>Ambil Bahan Sample (R&amp;D)</b>); biayanya masuk biaya sample dan dibebankan di buku besar (<b>Dr 6-7000 Beban Sample &amp; Pengembangan / Cr 1-1300 Persediaan</b>).
        </Hint>
        <Field label="Roll sumber bahan *">
          <KNSelect data-testid="issue-roll" className="field" value={rollId} searchable
            options={rolls.map((r) => ({ value: r.id, label: `${r.roll_no} · ${r.product_name || r.product_id} · sisa ${formatQty(r.length_remaining)} ${r.unit || "meter"}` }))}
            onValueChange={setRollId} />
        </Field>
        <div className="grid gap-2.5 sm:grid-cols-2">
          <Field label="Jumlah diambil *">
            <input className="field" type="number" min="0" step="any" data-testid="issue-qty" value={qty} onChange={(e) => setQty(e.target.value)} placeholder="3" />
          </Field>
          <Field label="Catatan">
            <input className="field" data-testid="issue-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="mis. swatch labdip" />
          </Field>
        </div>
        {roll && qty && (
          <Hint tone="ok" testId="issue-impact">
            Sisa roll {roll.roll_no}: <b>{formatQty(roll.length_remaining)}</b> → <b>{formatQty(Math.max(Number(roll.length_remaining) - Number(qty || 0), 0))}</b> {roll.unit || "meter"}
            {roll.unit_cost ? ` · perkiraan biaya ${formatCurrency(Number(roll.unit_cost) * Number(qty || 0))}` : ""}
          </Hint>
        )}
      </div>
    </FormModal>
  );
}
