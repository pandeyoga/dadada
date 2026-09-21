/** marketingShared — konstanta & helper modul Sosial Media & Konten. */
import axios, { API } from "../../services/apiClient";

export const PLATFORM_STYLE = {
  instagram: { label: "Instagram", bg: "#FCE7F3", fg: "#9D174D" },
  tiktok: { label: "TikTok", bg: "#E5E7EB", fg: "#111827" },
  facebook: { label: "Facebook", bg: "#DBEAFE", fg: "#1D4ED8" },
  whatsapp: { label: "WA Status", bg: "#DCFCE7", fg: "#166534" },
  shopee: { label: "Shopee", bg: "#FFEDD5", fg: "#C2410C" },
  youtube: { label: "YouTube", bg: "#FEE2E2", fg: "#B91C1C" },
};
export const STATUS_STYLE = {
  idea: { label: "Ide", cls: "bg-[#F2F2F7] text-[#6B6B73] border-[#E5E5EA]" },
  draft: { label: "Draft", cls: "bg-[#EEF2FF] text-[#3730A3] border-[#C7D2FE]" },
  review: { label: "Review", cls: "bg-[#FFF4E5] text-[#B45309] border-[#FCE1B6]" },
  approved: { label: "Disetujui", cls: "bg-[#E0F2FE] text-[#0369A1] border-[#BAE6FD]" },
  scheduled: { label: "Terjadwal", cls: "bg-[#EDE9FE] text-[#6D28D9] border-[#DDD6FE]" },
  published: { label: "Tayang", cls: "bg-[#E9F7EF] text-[#1B7F4B] border-[#CDE9D6]" },
  cancelled: { label: "Batal", cls: "bg-[#FDECEC] text-[#C0392B] border-[#F5C6C6]" },
};
export const NEXT_ACTIONS = {
  idea: [{ to: "draft", label: "Jadikan draft" }],
  draft: [{ to: "review", label: "Ajukan review", primary: true }],
  review: [{ to: "approved", label: "Setujui", primary: true, approver: true }, { to: "draft", label: "Kembalikan", reason: true }],
  approved: [{ to: "scheduled", label: "Jadwalkan", primary: true }, { to: "draft", label: "Kembalikan", reason: true }],
  scheduled: [{ to: "published", label: "Tandai tayang", primary: true, url: true }, { to: "approved", label: "Batal jadwal", reason: true }],
  published: [],
  cancelled: [{ to: "idea", label: "Hidupkan lagi" }],
};
export const METRIC_LABEL = { likes: "Suka", comments: "Komentar", shares: "Bagikan", saves: "Simpan", reach: "Jangkauan", impressions: "Tayangan", clicks: "Klik", followers_gained: "Pengikut baru", sales_leads: "Prospek" };

export const fmtN = (n) => new Intl.NumberFormat("id-ID").format(Math.round(n || 0));
export const monthKey = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
export const MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
export const monthLabel = (m) => `${MONTHS_ID[Number(m.slice(5, 7)) - 1]} ${m.slice(0, 4)}`;
export const fmtWhen = (s) => (s ? `${s.slice(8, 10)}/${s.slice(5, 7)} ${s.slice(11, 16) || ""}` : "—");

export function PlatformChip({ code, small }) {
  const p = PLATFORM_STYLE[code] || { label: code, bg: "#F2F2F7", fg: "#333" };
  return <span className={`inline-block rounded-full font-bold ${small ? "px-1.5 py-px text-[9px]" : "px-2 py-0.5 text-[10px]"}`} style={{ background: p.bg, color: p.fg }} data-testid={`mkt-platform-chip-${code}`}>{p.label}</span>;
}
export function StatusPill({ status, testId }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.idea;
  return <span className={`inline-block rounded-full border px-2 py-px text-[10px] font-bold ${s.cls}`} data-testid={testId}>{s.label}</span>;
}

export const mktApi = {
  meta: () => axios.get(`${API}/marketing/meta`).then((r) => r.data),
  posts: (params) => axios.get(`${API}/marketing/posts`, { params }).then((r) => r.data),
  post: (id) => axios.get(`${API}/marketing/posts/${id}`).then((r) => r.data),
  createPost: (b) => axios.post(`${API}/marketing/posts`, b).then((r) => r.data),
  updatePost: (id, b) => axios.patch(`${API}/marketing/posts/${id}`, b).then((r) => r.data),
  transition: (id, b) => axios.post(`${API}/marketing/posts/${id}/transition`, b).then((r) => r.data),
  metrics: (id, b) => axios.post(`${API}/marketing/posts/${id}/metrics`, b).then((r) => r.data),
  deletePost: (id) => axios.delete(`${API}/marketing/posts/${id}`).then((r) => r.data),
  upload: (id, file, caption = "") => { const fd = new FormData(); fd.append("file", file); fd.append("caption", caption); return axios.post(`${API}/marketing/posts/${id}/attachments`, fd).then((r) => r.data); },
  removeAttachment: (id, fid) => axios.delete(`${API}/marketing/posts/${id}/attachments/${fid}`).then((r) => r.data),
  attachmentUrl: (id, fid) => `${API}/marketing/posts/${id}/attachments/${fid}`,
  campaigns: (params) => axios.get(`${API}/marketing/campaigns`, { params }).then((r) => r.data),
  createCampaign: (b) => axios.post(`${API}/marketing/campaigns`, b).then((r) => r.data),
  updateCampaign: (id, b) => axios.patch(`${API}/marketing/campaigns/${id}`, b).then((r) => r.data),
  assets: (q) => axios.get(`${API}/marketing/assets`, { params: { q } }).then((r) => r.data),
  analytics: (params) => axios.get(`${API}/marketing/analytics`, { params }).then((r) => r.data),
};
