import React, { useState } from "react";
import CameraView from "../../components/CameraView";
import { useProto } from "../../services/useStore";
import Page from "../buyer/Page";
import SosBanner from "./SosBanner";

export default function GuardCctv() {
  const list = useProto((s) => s.security.cameras.areaList);
  const [focus, setFocus] = useState(null);
  return (
    <Page id="S4" title="CCTV kawasan" back="/app/satpam" nav="satpam">
      <SosBanner />
      <div className="grid grid-cols-2 gap-2.5">
        {list.map((label, i) => {
          const id = `area-${i + 1}`;
          const big = focus === id;
          return (
            <button
              key={id} type="button" aria-pressed={big} aria-label={`${big ? "Perkecil" : "Perbesar"} kamera ${label}`}
              onClick={() => setFocus(big ? null : id)}
              className={`block overflow-hidden rounded-2xl text-left shadow-[var(--rdg-shadow-card)] ${big ? "col-span-2" : ""}`}
            >
              <CameraView cameraId={id} label={label} />
            </button>
          );
        })}
      </div>
    </Page>
  );
}
