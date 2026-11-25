import React from "react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import ScreenHeader from "../../components/ScreenHeader";

export { default as Loading } from "../../components/Loading";

/** Kerangka layar mitra: header terang + menu bawah "partner". `nav={null}` untuk pendaftaran. */
export default function PartnerPage({ id, title, back = "/app/mitra", nav = "partner", children }) {
  return (
    <MobileShell nav={nav}>
      <Screen id={id}>
        <ScreenHeader title={title} back={back} variant="light" />
        <div className="space-y-4 px-5 pb-6 pt-2">{children}</div>
      </Screen>
    </MobileShell>
  );
}
