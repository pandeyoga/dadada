import React from "react";
import Screen from "../components/Screen";
import MobileShell from "../components/MobileShell";

export default function Placeholder({ id, title }) {
  return (
    <MobileShell>
      <Screen id={id}>
        <div className="p-5">
          <p className="text-xs font-semibold text-rdg-teal">{id}</p>
          <h1 className="text-xl font-bold text-rdg-ink">{title}</h1>
        </div>
      </Screen>
    </MobileShell>
  );
}
