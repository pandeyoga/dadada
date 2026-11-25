let seq = 0;

/** ID unik untuk entri baru (penghitung mencegah tabrakan pada milidetik yang sama). */
export function newId(prefix, t) {
  seq += 1;
  return `${prefix}-${t}-${seq}`;
}
