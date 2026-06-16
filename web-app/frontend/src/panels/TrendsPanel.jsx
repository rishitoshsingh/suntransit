import { useEffect, useState } from "react";
import {
  ComposedChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid,
} from "recharts";
import { API } from "../api.js";
import { fmtDelayShort } from "../util.js";

export default function TrendsPanel({ city, agency }) {
  const [agencyTrend, setAgencyTrend] = useState(null);
  const [routes, setRoutes] = useState([]);

  useEffect(() => {
    let cancel = false;
    API.agencyTrend(city).then((d) => !cancel && setAgencyTrend(d)).catch(() => {});
    API.routeTrends(city).then((d) => !cancel && setRoutes(d || [])).catch(() => {});
    return () => { cancel = true; };
  }, [city]);

  const series = (agencyTrend?.series || []).map((d) => {
    const mean = d.mean_delay != null ? +(d.mean_delay / 60).toFixed(2) : null;
    const std = d.std_delay != null ? +(d.std_delay / 60).toFixed(2) : 0;
    return {
      date: d.date.slice(5),
      mean,
      hi: mean != null ? +(mean + std).toFixed(2) : null,
      lo: mean != null ? +(mean - std).toFixed(2) : null,
    };
  });

  return (
    <>
      <div className="chart-card">
        <h3>System on-time trend {agencyTrend && <TrendBadge badge={agencyTrend.badge} />}</h3>
        <div className="sub">Daily mean delay (minutes), ± std dev band</div>
        <div className="chart-legend">
          <span><span className="cleg-line" />Mean delay</span>
          <span><span className="cleg-dashed" />±1 std dev</span>
        </div>
        {series.length ? (
          <ResponsiveContainer width="100%" height={170}>
            <ComposedChart data={series} margin={{ top: 6, right: 6, left: -22, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--text-dim)" }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: "var(--text-dim)" }} width={42} />
              <ReferenceLine y={0} stroke="var(--text-dim)" strokeDasharray="3 3" />
              <Tooltip content={<TrendTip />} />
              <Line dataKey="hi" stroke="var(--accent)" strokeWidth={1} strokeOpacity={0.4} strokeDasharray="4 3" dot={false} connectNulls legendType="none" />
              <Line dataKey="lo" stroke="var(--accent)" strokeWidth={1} strokeOpacity={0.4} strokeDasharray="4 3" dot={false} connectNulls legendType="none" />
              <Line dataKey="mean" stroke="var(--accent)" strokeWidth={2.5} dot={false} connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty">Not enough history yet.</div>
        )}
      </div>

      <div className="section-label">Routes — worst first</div>
      {routes.length ? (
        routes.slice(0, 25).map((r) => (
          <div className="row" key={r.route_id}>
            <span className="chip" style={{ background: r.route_color }}>{r.route_short_name || "?"}</span>
            <div className="meta">
              <Spark values={r.spark} color={r.route_color} />
            </div>
            <span className="val">{fmtDelayShort(r.recent_mean)}</span>
            <TrendBadge badge={r.badge} />
          </div>
        ))
      ) : (
        <div className="empty">No route history yet.</div>
      )}
    </>
  );
}

function TrendBadge({ badge }) {
  const label = { improving: "▼ improving", worsening: "▲ worsening", flat: "— steady" }[badge] || "";
  return <span className={`badge ${badge}`}>{label}</span>;
}

function TrendTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const m = payload.find((p) => p.dataKey === "mean")?.value;
  return (
    <div className="glass" style={{ padding: "6px 10px", fontSize: 12 }}>
      <b>{label}</b> · {m != null ? `${m}m` : "—"}
    </div>
  );
}

function Spark({ values, color }) {
  const v = values.filter((x) => x != null);
  if (v.length < 2) return <div className="s">—</div>;
  const min = Math.min(...v), max = Math.max(...v), span = max - min || 1;
  const w = 150, h = 26;
  const pts = values
    .map((y, i) => (y == null ? null : `${(i / (values.length - 1)) * w},${h - ((y - min) / span) * h}`))
    .filter(Boolean)
    .join(" ");
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}
