import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const src = "/tmp/kn-audit/frontend/src/utils/variants.js";
const tempModule = "/tmp/kn-audit-variants-real.mjs";
const out = "/app/test_reports/isolated_variants_result.json";

const source = readFileSync(src, "utf8");
writeFileSync(tempModule, source, "utf8");

const mod = await import(pathToFileURL(tempModule).href);

const variants = [
  {
    id: "v1",
    sku: "SKU-MER-A-115-COT",
    color_code: "MER",
    color_name: "Merah",
    color_hex: "#FF0000",
    color: "Merah",
    grade: "A",
    available_qty: 10,
    variant_attrs: { color: "Merah", grade: "A", lebar: "1.15", material: "Cotton" },
  },
  {
    id: "v2",
    sku: "SKU-MER-A-150-POLY",
    color_code: "MER",
    color_name: "Merah",
    color_hex: "#FF0000",
    color: "Merah",
    grade: "A",
    available_qty: 8,
    variant_attrs: { color: "Merah", grade: "A", lebar: "1.50", material: "Poly" },
  },
  {
    id: "v3",
    sku: "SKU-BIR-B-115-COT",
    color_code: "BIR",
    color_name: "Biru",
    color_hex: "#0000FF",
    color: "Biru",
    grade: "B",
    available_qty: 5,
    variant_attrs: { color: "Biru", grade: "B", lebar: "1.15", material: "Cotton" },
  },
];

const axis = mod.deriveAxisOptions(variants);
const resolved = mod.resolveVariant(variants, "MER", "A");
const unresolvedDimensions = variants
  .filter((v) => (v.color_code || v.color) === "MER" && v.grade === "A")
  .map((v) => ({ id: v.id, sku: v.sku, lebar: v.variant_attrs?.lebar, material: v.variant_attrs?.material }));

const result = {
  source: src,
  probe_type: "isolated-real-frontend-utils",
  axis_options: {
    colors: axis.colors,
    grades: axis.grades,
    hasColor: axis.hasColor,
    hasGrade: axis.hasGrade,
    hasWidthAxis: Object.prototype.hasOwnProperty.call(axis, "widths"),
    hasMaterialAxis: Object.prototype.hasOwnProperty.call(axis, "materials"),
  },
  resolve_variant_probe: {
    requested: { colorKey: "MER", gradeKey: "A" },
    resolved: { id: resolved?.id || null, sku: resolved?.sku || null },
    ambiguous_candidates_same_color_grade: unresolvedDimensions,
    finding: "resolveVariant cannot disambiguate width/material when color+grade duplicates exist",
  },
};

writeFileSync(out, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
