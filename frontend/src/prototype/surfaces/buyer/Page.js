import React from "react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import ScreenHeader from "../../components/ScreenHeader";

/** Kerangka layar pembeli tingkat L: header terang + menu bawah. */
export default function Page({ id, title, back = "/app/pembeli", nav = "buyer", right, children }) {
  return (
    <MobileShell nav={nav}>
      <Screen id={id}>
        <ScreenHeader title={title} back={back} right={right} variant="light" />
        <div className="space-y-4 px-5 pb-6 pt-2">{children}</div>
      </Screen>
    </MobileShell>
  );
}

export { default as Loading } from "../../components/Loading";
