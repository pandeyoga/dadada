/**
 * useLogisticsDeepLink — fokus untuk **Modul Logistik** (`kn-open-logistics`) dan
 * lompatan ke **Pesanan** (`kn-open-order`). Pola sama dengan `useCaseDeepLink`.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { LOGISTICS_EVENT, ORDER_EVENT } from "../features/logistics/logisticsDeepLink";

export default function useLogisticsDeepLink(onNavigate, onOpenOrder) {
  const [logisticsFocus, setLogisticsFocus] = useState(null);
  const navRef = useRef(onNavigate); navRef.current = onNavigate;
  const orderRef = useRef(onOpenOrder); orderRef.current = onOpenOrder;

  useEffect(() => {
    const onLogistics = (e) => {
      const d = (e && e.detail) || {};
      if (typeof navRef.current === "function") navRef.current();
      setLogisticsFocus({ deliveryId: d.deliveryId || "", createFromShipmentId: d.createFromShipmentId || "", search: d.search || "", nonce: Date.now() });
    };
    const onOrder = (e) => {
      const d = (e && e.detail) || {};
      if (d.orderId && typeof orderRef.current === "function") orderRef.current(d.orderId);
    };
    window.addEventListener(LOGISTICS_EVENT, onLogistics);
    window.addEventListener(ORDER_EVENT, onOrder);
    return () => { window.removeEventListener(LOGISTICS_EVENT, onLogistics); window.removeEventListener(ORDER_EVENT, onOrder); };
  }, []);

  const clearLogisticsFocus = useCallback(() => setLogisticsFocus(null), []);
  return [logisticsFocus, clearLogisticsFocus];
}
