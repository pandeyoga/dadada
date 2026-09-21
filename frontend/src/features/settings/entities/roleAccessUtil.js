/** Util izin peran di sisi klien — cermin `access_modules.py` (level_of / apply_levels). */

export const fullActions = (module, resource) => module.actions?.[resource] || [];

export function levelOf(perms, module) {
  const acts = new Set();
  module.resources.forEach((r) => (perms[r] || []).forEach((a) => acts.add(a)));
  if (!acts.size) return { level: "none", partial: false };
  if ([...acts].every((a) => a === "view")) return { level: "view", partial: false };
  const full = module.resources.every((r) => {
    const have = new Set(perms[r] || []);
    return fullActions(module, r).every((a) => have.has(a));
  });
  return { level: "manage", partial: !full };
}

export function applyLevel(perms, module, level) {
  const out = { ...perms };
  module.resources.forEach((r) => {
    const full = fullActions(module, r);
    if (level === "none") delete out[r];
    else if (level === "view") { if (full.includes("view")) out[r] = ["view"]; else delete out[r]; }
    else out[r] = [...full];
  });
  return out;
}

export function toggleAction(perms, module, resource, action) {
  const full = fullActions(module, resource);
  const have = new Set(perms[resource] || []);
  if (have.has(action)) {
    have.delete(action);
    if (action === "view") have.clear();           // tanpa Lihat, aksi lain tidak berarti
  } else {
    have.add(action);
    if (full.includes("view")) have.add("view");   // aksi apa pun menyiratkan Lihat
  }
  const out = { ...perms };
  const list = full.filter((a) => have.has(a));
  if (list.length) out[resource] = list; else delete out[resource];
  return out;
}

export function setResource(perms, module, resource, all) {
  const out = { ...perms };
  if (all) out[resource] = [...fullActions(module, resource)]; else delete out[resource];
  return out;
}

export const sameActions = (a = [], b = []) => [...a].sort().join(",") === [...b].sort().join(",");

export const moduleActionsChanged = (perms, original, module) =>
  module.resources.some((r) => !sameActions(perms[r], original[r]));
