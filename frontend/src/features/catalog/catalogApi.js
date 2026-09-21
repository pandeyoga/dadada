import axios, { API } from "../../services/apiClient";
export const catalogApi = {
  meta: () => axios.get(`${API}/product-catalog/meta`).then(r => r.data),
  list: params => axios.get(`${API}/product-templates`, { params }).then(r => r.data),
  detail: id => axios.get(`${API}/product-templates/${id}`).then(r => r.data),
  summary: id => axios.get(`${API}/product-templates/${id}/summary`).then(r => r.data),
  save: (id, data) => (id ? axios.patch(`${API}/product-templates/${id}`, data) : axios.post(`${API}/product-templates`, data)).then(r => r.data),
  generate: (id, data) => axios.post(`${API}/product-templates/${id}/generate-variants`, data).then(r => r.data),
  archive: id => axios.delete(`${API}/product-templates/${id}`).then(r => r.data),
  product: (id, data) => (id ? axios.patch(`${API}/products/${id}`, { data }) : axios.post(`${API}/products`, data)).then(r => r.data),
  media: id => axios.get(`${API}/products/${id}/media`).then(r => r.data),
  upload: (id, file, kind) => { const fd = new FormData(); fd.append("file", file); fd.append("kind", kind); return axios.post(`${API}/products/${id}/media`, fd).then(r => r.data); },
  mediaPatch: (id, mid, data) => axios.patch(`${API}/products/${id}/media/${mid}`, data).then(r => r.data),
  mediaDelete: (id, mid) => axios.delete(`${API}/products/${id}/media/${mid}`).then(r => r.data),
  mockup: (id, data) => axios.post(`${API}/products/${id}/media/generate-mockup`, data, { timeout: 90000 }).then(r => r.data),
  designMedia: (id, data) => axios.post(`${API}/products/${id}/media/from-design`, data).then(r => r.data),
};
export function catalogError(e) {
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(x => `${(x.loc || []).slice(1).join(".")}: ${x.msg}`).join("; ");
  return detail?.message || e?.message || "Perubahan tidak tersimpan. Coba kembali.";
}
export function catalogChanged() { window.dispatchEvent(new Event("kn-catalog-changed")); }