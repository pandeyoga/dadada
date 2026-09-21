/**
 * DesignScoreTrendChart — grafik **Tren Nilai Desain per Bulan** (Design Studio).
 *
 * Pendamping DesignerKpiTrendChart: titik = rata-rata nilai versi desain (0–2) yang
 * dinilai pada bulan itu (tanggal penilaian, fallback tanggal unggah versi).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Palette } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import KNSelect from "../../components/KNSelect";
import { errMsg } from "../rnd/rndMeta";
import { designerKpiTrend } from "./designerApi";

const PALETTE = ["#0058CC", "#1B7F4B", "#B8860B", "#C0392B",
  "#7E57C2", "#0097A7", "#EF6C00", "#5D4037"];

const MONTH_OPTIONS = [
  { value: "3", label: "3 bulan terakhir" },
  { value: "6", label: "6 bulan terakhir" },
  { value: "12", label: "12 bulan terakhir" },
];

const fmt = (v) => (v == null ? "—" : String(v).replace(".", ","));

export default function DesignScoreTrendChart({ params = {}, accMin = 1.5, testId = "design-score-trend" }) {
  const [months, setMonths] = useState("6");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await designerKpiTrend({ ...params, metric: "design_score", months: Number(months) });
      setData(res || null);
      setError("");
    } catch (e) {
      setError(errMsg(e, "Gagal memuat tren nilai desain."));
    } finally {
      setLoading(false);
    }
  }, [params, months]);

  useEffect(() => { load(); }, [load]);

  const series = data?.series || [];
  const labels = data?.month_labels || [];
  const rows = useMemo(() => {
    if (!data) return [];
    return (data.months || []).map((_, i) => {
      const row = { month: labels[i] };
      series.forEach((s) => { row[s.designer] = s.points?.[i]?.score ?? null; });
      return row;
    });
  }, [data, labels, series]);
  const hasData = series.some((s) => (s.points || []).some((p) => p.score !== null));

  return (
    <section className="section-card" data-testid={testId}>
      <div className="section-head">
        <div className="flex items-center gap-2">
          <Palette size={16} className="text-[#0058CC]" />
          <h2>Tren nilai desain per bulan</h2>
        </div>
        <KNSelect data-testid={`${testId}-months`} value={months}
          onValueChange={setMonths} options={MONTH_OPTIONS} className="field !w-[170px]" />
      </div>
      <div className="section-body">
        <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")}
          testId={`${testId}-error`} />
        <p className="mb-1 text-[11.5px] text-[#6B6B73]" data-testid={`${testId}-note`}>
          Rata-rata nilai versi desain (0–2) yang dinilai penilai pada bulan itu. Garis putus = ambang ACC ({fmt(accMin)}).
          {" "}Titik kosong = tidak ada versi yang dinilai.
        </p>

        {loading && !data ? (
          <p className="py-10 text-center text-[12px] text-[#6B6B73]"
            data-testid={`${testId}-loading`}>Memuat grafik tren…</p>
        ) : !hasData ? (
          <div className="py-10 text-center" data-testid={`${testId}-empty`}>
            <p className="text-[12px] font-semibold text-[#4A4B52]">Belum ada nilai desain</p>
            <p className="text-[11.5px] text-[#9A9BA3]">
              Versi desain yang sudah dinilai di Design Studio akan muncul sebagai titik bulanan di sini.
            </p>
          </div>
        ) : (
          <div style={{ width: "100%", height: 340 }} data-testid={`${testId}-chart`}>
            <ResponsiveContainer>
              <LineChart data={rows} margin={{ top: 8, right: 16, left: -8, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#6B6B73" }}
                  axisLine={{ stroke: "#E1E4EA" }} tickLine={false} />
                <YAxis domain={[0, 2]} ticks={[0, 0.5, 1, 1.5, 2]} tick={{ fontSize: 11, fill: "#6B6B73" }}
                  axisLine={false} tickLine={false} width={38} tickFormatter={fmt} />
                <ReferenceLine y={accMin} stroke="#1B7F4B" strokeDasharray="4 4"
                  label={{ value: "ACC", fontSize: 10, fill: "#1B7F4B", position: "right" }} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 10, border: "1px solid #E1E4EA" }}
                  formatter={(v, name) => [v == null ? "—" : `${fmt(v)}/2`, name]} />
                <Legend wrapperStyle={{ fontSize: 11.5, paddingTop: 6 }} iconType="plainline" />
                {series.map((s, idx) => (
                  <Line key={s.designer} type="monotone" dataKey={s.designer} name={s.designer}
                    stroke={PALETTE[idx % PALETTE.length]} strokeWidth={2.2}
                    dot={{ r: 2.5 }} activeDot={{ r: 5 }} connectNulls isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {hasData && (
          <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1" data-testid={`${testId}-avg-legend`}>
            {series.map((s, idx) => (
              <span key={s.designer} className="inline-flex items-center gap-1 text-[11px] text-[#4A4B52]">
                <span className="inline-block h-2 w-2 rounded-full"
                  style={{ background: PALETTE[idx % PALETTE.length] }} />
                {s.designer}
                <b className="tabular-nums">· rata-rata {fmt(s.avg)}/2 · {s.versions} versi</b>
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
