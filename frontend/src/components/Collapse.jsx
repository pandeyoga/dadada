/**
 * Collapse — buka/tutup beranimasi (grid-template-rows 0fr→1fr).
 * Dulu kartu meja kerja hanya "menghilangkan" isinya tanpa transisi sehingga
 * terasa statis; pembungkus ini membuat kartunya benar-benar mengecil/membesar.
 */
export default function Collapse({ open, children }) {
  return (
    <div
      aria-hidden={!open}
      className={`grid transition-[grid-template-rows] duration-300 ease-in-out ${
        open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}
    >
      <div className={`min-h-0 overflow-hidden transition-opacity duration-200 ${
        open ? "opacity-100" : "opacity-0"}`}>
        {children}
      </div>
    </div>
  );
}
