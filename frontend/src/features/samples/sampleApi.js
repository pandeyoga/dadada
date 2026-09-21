import axios, { API } from "../../services/apiClient";

export const listSampleOrders = (params = {}) => axios.get(`${API}/sample-orders`, { params }).then((r) => r.data);
export const sampleStats = (params = {}) => axios.get(`${API}/sample-orders/stats/summary`, { params }).then((r) => r.data);
export const sampleDesk = (params = {}) => axios.get(`${API}/sample-orders/desk`, { params }).then((r) => r.data);
export const approveSamplePayment = (id, note = "") => axios.post(`${API}/sample-orders/${id}/approve-payment`, { note }).then((r) => r.data);
export const confirmSampleOrder = (id) => axios.post(`${API}/sample-orders/${id}/confirm`).then((r) => r.data);
export const cancelSampleOrder = (id, note = "") => axios.post(`${API}/sample-orders/${id}/cancel`, { note }).then((r) => r.data);
