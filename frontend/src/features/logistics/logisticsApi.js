// FB-02 — API modul Logistik (pengiriman, dasbor, riwayat, armada, serah terima pickup).
import axios, { API } from "../../services/apiClient";

const L = `${API}/logistics`;
export const logisticsMeta = () => axios.get(`${L}/meta`).then((r) => r.data);
export const logisticsSummary = (params) => axios.get(`${L}/summary`, { params }).then((r) => r.data);
export const logisticsDashboard = (params) => axios.get(`${L}/dashboard`, { params }).then((r) => r.data);
export const logisticsHistory = (params) => axios.get(`${L}/history`, { params }).then((r) => r.data);
export const listDeliveries = (params) => axios.get(`${L}/deliveries`, { params }).then((r) => r.data);
export const getDelivery = (id) => axios.get(`${L}/deliveries/${id}`).then((r) => r.data);
export const unassignedShipments = (params) => axios.get(`${L}/shipments/unassigned`, { params }).then((r) => r.data);
export const createDelivery = (payload) => axios.post(`${L}/deliveries`, payload).then((r) => r.data);
export const updateDelivery = (id, payload) => axios.patch(`${L}/deliveries/${id}`, payload).then((r) => r.data);
export const addPosition = (id, payload) => axios.post(`${L}/deliveries/${id}/positions`, payload).then((r) => r.data);
export const transitionDelivery = (id, payload) => axios.post(`${L}/deliveries/${id}/transition`, payload).then((r) => r.data);
export const pickupHandover = (id, payload) => axios.post(`${L}/deliveries/${id}/pickup-handover`, payload).then((r) => r.data);
export const deletePhoto = (id, photoId) => axios.delete(`${L}/deliveries/${id}/photos/${photoId}`).then((r) => r.data);
export const deletePosition = (id, posId) => axios.delete(`${L}/deliveries/${id}/positions/${posId}`).then((r) => r.data);   // L-2
export const listDrivers = (params) => axios.get(`${L}/drivers`, { params }).then((r) => r.data);
export const setMyRoute = (ids) => axios.post(`${L}/my-route`, { ids }).then((r) => r.data);
export const fleetAvailability = (params) => axios.get(`${L}/fleet/availability`, { params }).then((r) => r.data);
export const listVehicles = (params) => axios.get(`${L}/fleet/vehicles`, { params }).then((r) => r.data);
export const createVehicle = (payload) => axios.post(`${L}/fleet/vehicles`, payload).then((r) => r.data);
export const updateVehicle = (id, payload) => axios.patch(`${L}/fleet/vehicles/${id}`, payload).then((r) => r.data);
export const setVehicleStatus = (id, payload) => axios.post(`${L}/fleet/vehicles/${id}/status`, payload).then((r) => r.data);
export function uploadPhoto(id, file, kind, note = "") {
  const fd = new FormData();
  fd.append("file", file); fd.append("kind", kind); fd.append("note", note);
  return axios.post(`${L}/deliveries/${id}/photos`, fd, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
}
export const photoUrl = (id, photoId) => `${L}/deliveries/${id}/photos/${photoId}`;

export const STATUS_PILL = {
  prepared: "pill-muted", loaded: "pill-info", in_transit: "pill-warning",
  delivered: "pill-success", completed: "pill-success", failed: "pill-danger",
};
export const STATUS_LABEL = {
  prepared: "Disiapkan", loaded: "Dimuat", in_transit: "Dalam perjalanan",
  delivered: "Terkirim", completed: "Selesai", failed: "Gagal kirim",
};
export const PICKUP_STATUS_LABEL = { prepared: "Menunggu diambil", delivered: "Diserahkan", completed: "Selesai" };
export const statusLabelOf = (d) => (d?.mode === "self_pickup" ? (PICKUP_STATUS_LABEL[d.status] || STATUS_LABEL[d.status]) : STATUS_LABEL[d?.status]) || d?.status;
export const MODE_LABEL = { expedition: "Ekspedisi", own_fleet: "Armada sendiri", self_pickup: "Diambil pelanggan" };
export const MODE_PILL = { expedition: "pill-info", own_fleet: "pill-warning", self_pickup: "pill-purple" };
export const STEPS = ["prepared", "loaded", "in_transit", "delivered", "completed"];
export const PICKUP_STEPS = ["prepared", "delivered", "completed"];
export const VEHICLE_STATUS_PILL = { available: "pill-success", on_trip: "pill-warning", maintenance: "pill-danger" };
// Ringkasan pengangkut per moda untuk tabel/kartu.
export const carrierText = (d) => {
  if (d.mode === "self_pickup") return d.pod?.receiver_name ? `Diambil: ${d.pod.receiver_name}` : `Ambil sendiri${d.pickup_date ? ` · tgl ${d.pickup_date}` : ""}`;
  if (d.mode === "expedition") return `${d.courier_name || "—"} · ${d.tracking_no || "resi belum ada"}`;
  return `${d.vehicle_plate || "—"} · ${d.driver_name || "—"}`;
};
// Google Maps directions ke alamat tujuan (di ponsel otomatis membuka aplikasi Maps).
export const mapsUrl = (address) => `https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=${encodeURIComponent(address)}`;
// Telepon & WhatsApp sekali sentuh. Nomor lokal 08xx → 628xx untuk wa.me.
export const telUrl = (phone) => `tel:${String(phone).replace(/[^\d+]/g, "")}`;
export const waUrl = (phone, text = "") => {
  let p = String(phone).replace(/\D/g, "");
  if (p.startsWith("0")) p = `62${p.slice(1)}`;
  return `https://wa.me/${p}${text ? `?text=${encodeURIComponent(text)}` : ""}`;
};

// L-1 — "hari ini" operasional = tanggal WIB (Asia/Jakarta), bukan UTC.
export const todayWib = () => new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Jakarta" });
