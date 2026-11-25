/** Keamanan rumah: fungsi murni dan layanan. Task 7 menambah fungsi lain di sini. */

export const AUTO_LOCK_MS = 30000;

/** Status pintu: terbuka hanya bila dibuka dan belum lewat 30 detik (kunci otomatis). */
export function doorStatus(state, now) {
  const door = state.security.door;
  if (door.state !== "unlocked") return "locked";
  return now - Date.parse(door.changedAt) < AUTO_LOCK_MS ? "unlocked" : "locked";
}
