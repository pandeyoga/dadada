/* Penamaan berkas tangkapan layar (CommonJS: dipakai skrip Node dan tes Jest). */
const FOLDERS = {
  U: "01-demo", P: "02-pembeli", T: "03-serah-terima", W: "04-warga", S: "05-satpam", K: "06-pengelola", M: "07-mitra",
};
const ROLES = {
  U: "Demo", P: "Pembeli", T: "Serah terima", W: "Warga", S: "Satpam", K: "Pengelola", M: "Mitra",
};

function slugify(title, max = 40) {
  const s = String(title)
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/&/g, " dan ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (s.length <= max) return s;
  const cut = s.slice(0, max + 1);
  const i = cut.lastIndexOf("-");
  return (i > 0 ? cut.slice(0, i) : s.slice(0, max)).replace(/-+$/, "");
}

function id2(id) {
  const m = /^([A-Z])(\d+)$/.exec(id);
  if (!m) throw new Error(`ID layar tidak valid: ${id}`);
  return `${m[1]}${m[2].padStart(2, "0")}`;
}

function folderFor(id) {
  const f = FOLDERS[id[0]];
  if (!f) throw new Error(`Awalan ID tidak dikenal: ${id}`);
  return f;
}

const roleFor = (id) => ROLES[id[0]];
const screenFileName = (entry) => `${id2(entry.id)}-${slugify(entry.title)}`;

module.exports = { slugify, id2, folderFor, roleFor, screenFileName, FOLDERS, ROLES };
