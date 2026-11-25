import React from "react";
import { Link } from "react-router-dom";
import Screen from "../../components/Screen";
import MobileShell from "../../components/MobileShell";
import screens from "../../screens.json";

// Sementara: daftar tautan semua layar. Diganti di task berikutnya.
export default function Launcher() {
  return (
    <MobileShell>
      <Screen id="U1">
        <div className="p-5">
          <h1 className="text-xl font-bold text-rdg-ink">Rumah Dalam Genggaman</h1>
          <p className="text-sm text-rdg-teal mb-4">Data contoh</p>
          <ul className="space-y-1">
            {screens.filter((s) => s.id !== "U1").map((s) => (
              <li key={s.id}>
                <Link className="text-sm text-rdg-ink underline" to={s.path}>{s.id} · {s.title}</Link>
              </li>
            ))}
          </ul>
        </div>
      </Screen>
    </MobileShell>
  );
}
