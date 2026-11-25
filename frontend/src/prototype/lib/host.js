// Penjaga host: prototipe hanya aktif di mesin lokal dan host demo/trial.
const LOCAL = ["localhost", "127.0.0.1", ""];

export function isPrototypeHost(hostname) {
  const h = String(hostname == null ? "" : hostname).toLowerCase();
  return LOCAL.includes(h) || /^(demo|trial)\./.test(h);
}
