import React from "react";
import { Lock, LockOpen } from "lucide-react";
import StatusChip from "../../../components/StatusChip";
import ListRow from "../../../components/ListRow";
import { doorLogText, jam } from "./ui";

/** Daftar riwayat pintu (entri sudah diurutkan terbaru dulu). */
export default function DoorLog({ entries }) {
  if (!entries.length) return <p className="py-3 text-[14px] text-[color:var(--rdg-muted)]">Belum ada aktivitas.</p>;
  return (
    <ul className="divide-y divide-[color:var(--rdg-line)]">
      {entries.map((e) => (
        <li key={e.id}>
          <ListRow
            icon={e.state === "unlocked" ? LockOpen : Lock}
            title={doorLogText(e)}
            subtitle={jam(e.at)}
            right={<StatusChip tone={e.state === "unlocked" ? "warn" : "ok"} icon={null}>{e.state === "unlocked" ? "Terbuka" : "Terkunci"}</StatusChip>}
          />
        </li>
      ))}
    </ul>
  );
}
