import React from "react";

export default function Screen({ id, children }) {
  return <div data-screen={id} className="min-h-screen">{children}</div>;
}
