/**
 * sirenAlarm.js — sirine gate MERAH via Web Audio API (tanpa berkas suara).
 * Anti-spam: lonceng hanya membunyikan alarm yang BARU muncul setelah baseline
 * (reload halaman dengan alarm lama yang belum dibaca tidak langsung meraung).
 */
let ctx = null;
const seenAlarmIds = new Set();
let baselineDone = false;

export function isSirenMuted() {
  try { return localStorage.getItem("kn_siren_muted") === "1"; } catch { return false; }
}

export function setSirenMuted(muted) {
  try { localStorage.setItem("kn_siren_muted", muted ? "1" : "0"); } catch { /* ignore */ }
}

/** Dua-nada naik-turun ala sirine, ~0,6 dtk per siklus. Return false bila mute/gagal. */
export function playSiren(cycles = 3) {
  if (isSirenMuted()) return false;
  try {
    ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === "suspended") ctx.resume();
    const t0 = ctx.currentTime;
    const cycle = 0.6;
    const end = t0 + cycles * cycle;
    const gain = ctx.createGain();
    gain.connect(ctx.destination);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.linearRampToValueAtTime(0.25, t0 + 0.05);
    gain.gain.setValueAtTime(0.25, end - 0.08);
    gain.gain.linearRampToValueAtTime(0.0001, end);
    const osc = ctx.createOscillator();
    osc.type = "square";
    osc.connect(gain);
    for (let i = 0; i < cycles; i++) {
      const s = t0 + i * cycle;
      osc.frequency.setValueAtTime(650, s);
      osc.frequency.linearRampToValueAtTime(1150, s + cycle / 2);
      osc.frequency.linearRampToValueAtTime(650, s + cycle);
    }
    osc.start(t0);
    osc.stop(end + 0.05);
    return true;
  } catch { return false; }
}

/** Dipanggil tiap lonceng dimuat ulang — bunyikan hanya alarm gate BARU yang belum dibaca. */
export function sirenOnNewAlarms(items) {
  const alarms = (items || []).filter((n) => n.type === "rfid_gate_alarm" && !n.read);
  if (!baselineDone) {
    alarms.forEach((n) => seenAlarmIds.add(n.id));
    baselineDone = true;
    return;
  }
  const fresh = alarms.filter((n) => !seenAlarmIds.has(n.id));
  fresh.forEach((n) => seenAlarmIds.add(n.id));
  if (fresh.length) playSiren();
}
