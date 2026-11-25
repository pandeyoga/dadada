import { useEffect, useState } from "react";
import { AUTO_LOCK_MS, doorStatus, lockDoor, unlockDoor } from "../../../services/api/security";
import { useNow, useProto } from "../../../services/useStore";

/** Status pintu langsung: hitung mundur kunci otomatis dan aksi buka/kunci. */
export default function useDoor() {
  const door = useProto((s) => s.security.door);
  const t = useNow(1000);
  const status = doorStatus({ security: { door } }, t);
  const left = AUTO_LOCK_MS - (t - Date.parse(door.changedAt));
  const remaining = status === "unlocked" ? Math.min(AUTO_LOCK_MS / 1000, Math.max(0, Math.ceil(left / 1000))) : 0;
  const [error, setError] = useState("");

  // Saat batas 30 detik lewat, tulis catatan "Otomatis terkunci" (idempoten).
  useEffect(() => {
    if (status === "locked" && door.state === "unlocked") lockDoor().catch(() => {});
  }, [status, door.state]);

  const run = async (fn) => {
    setError("");
    try { await fn(); } catch (e) { setError((e && e.message) || "Gagal"); }
  };
  return { status, remaining, error, unlock: () => run(() => unlockDoor("aplikasi")), lock: () => run(lockDoor) };
}
