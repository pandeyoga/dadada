import React, { useCallback } from "react";
import { FrostCard } from "../../components/GlassCard";
import { getPlotMap } from "../../services/api/buyer";
import useLoad from "./useLoad";
import Page, { Loading } from "./Page";

const FILL = { tersedia: "#d8efe0", dipesan: "#f5d98a", terjual: "#9db3b3", "milik-anda": "#209f59" };
const LABEL = { tersedia: "Tersedia", dipesan: "Dipesan", terjual: "Terjual", "milik-anda": "Milik Anda" };
const W = 46, H = 28, GAP = 5, PAD = 28, COLS = 6, RH = H + GAP;

export default function PlotMap() {
  const fetcher = useCallback(() => getPlotMap(), []);
  const { data } = useLoad(fetcher);
  const plots = data ? data.plots : [];
  const width = PAD + COLS * (W + GAP);
  const BLOCKS = ["A", "B", "C", "D", "E"];
  const height = 8 + BLOCKS.length * (2 * RH + 18) + 26;
  const count = (s) => plots.filter((p) => p.status === s).length;
  return (
    <Page id="P3" title="Peta kavling">
      <p className="text-[14px] text-[color:var(--rdg-muted)]">Siteplan {data ? data.project : "Estora Residence"}. Rumah Anda di Blok {data ? data.unit : "C-12"}.</p>
      {!data && <Loading />}
      {data && (
        <FrostCard className="!p-3">
          <div>
            <svg viewBox={`0 0 ${width} ${height}`} className="block w-full" role="img" aria-label="Siteplan kavling Estora Residence">
              <rect x="0" y={height - 22} width={width} height="16" rx="8" fill="#c8d6d6" />
              <text x={width / 2} y={height - 10} textAnchor="middle" fontSize="10" fontWeight="700" fill="#35555a">Jalan utama · gerbang</text>
              {BLOCKS.map((b, r) => (
                <g key={b} transform={`translate(0 ${8 + r * (2 * RH + 18)})`}>
                  <text x="8" y={RH + 5} fontSize="13" fontWeight="800" fill="#00454d">{b}</text>
                  {plots.filter((p) => p.block === b).map((p) => {
                    const mine = p.status === "milik-anda";
                    return (
                      <g key={p.id} transform={`translate(${PAD + ((p.number - 1) % COLS) * (W + GAP)} ${p.number > COLS ? RH : 0})`}>
                        <title>{`${p.id} · ${LABEL[p.status]}`}</title>
                        <rect width={W} height={H} rx="6" fill={FILL[p.status]} stroke={mine ? "#00353b" : "none"} strokeWidth={mine ? 3 : 0} />
                        <text x={W / 2} y={H / 2 + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill={mine ? "#fff" : "#00353b"}>{p.number}</text>
                        {mine && <text x={W / 2} y={H + 11} textAnchor="middle" fontSize="9.5" fontWeight="800" fill="#006747">milik Anda</text>}
                      </g>
                    );
                  })}
                </g>
              ))}
            </svg>
          </div>
          <ul className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2" aria-label="Legenda">
            {Object.keys(FILL).map((s) => (
              <li key={s} className="flex items-center gap-2 text-[13px] font-semibold">
                <span className="h-4 w-4 flex-none rounded" style={{ background: FILL[s], border: s === "milik-anda" ? "2px solid #00353b" : "1px solid rgba(0,53,59,.15)" }} aria-hidden="true" />
                {LABEL[s]} ({count(s)})
              </li>
            ))}
          </ul>
        </FrostCard>
      )}
    </Page>
  );
}
