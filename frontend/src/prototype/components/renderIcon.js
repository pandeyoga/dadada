import React from "react";

/** Terima komponen ikon (mis. `Lock` dari lucide-react) atau elemen jadi. */
export default function renderIcon(icon, props) {
  if (!icon) return null;
  if (React.isValidElement(icon)) return icon;
  const Icon = icon;
  return <Icon aria-hidden="true" {...props} />;
}
