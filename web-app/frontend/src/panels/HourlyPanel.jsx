import { useEffect, useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";
import { API } from "../api.js";
import { delayColor } from "../map/basemaps.js";
import { fmtDelay } from "../util.js";

const fmtHour = (h) => `${((h + 11) % 12) + 1}${h < 12 ? "a" : "p"}`;

export default function HourlyPanel({ city }) {
  const [agency, setAgency] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [routeId, setRouteId] = useState("");

  useEffect(() => {
    let cancel = false;
    setRouteId("");
    API.agencyHourly(city).then((d) => !cancel && setAgency(d)).catch(() => !cancel && setAgency({ available: false }));
    API.routeHourly(city).then((d) => !cancel && setRoutes(d?.routes || [])).catch(() => {});
    return () => { cancel = true; };
  }, [city]);

  const selected = useMemo(() => routes.find((r) => r.route_id === routeId), [routes, routeId]);
  const hours = selected ? selected.hours : agency?.hours;

  if (agency && agency.available === false) {
    return (
      <div className="empty">
        Hourly profile not built yet.<br />
        Run <code>hourly_profile_job.sh</code> to populate the late-clock tables.
      </div>
    );
  }
  if (!hours) return <div className="empty">Loading hourly profile…</div>;

  // normalise to a 0..23 dense array
  const byHour = Object.fromEntries(hours.map((h) => [h.hour, h]));
  const maxAbs = Math.max(60, ...hours.map((h) => Math.abs(h.mean_delay || 0)));
  const dense = Array.from({ length: 24 }, (_, h) => {
    const d = byHour[h];
    const delay = d?.mean_delay ?? null;
    return {
      hour: h, label: fmtHour(h), delay,
      min: delay != null ? +(delay / 60).toFixed(2) : null,
      color: delay != null ? delayColor(0.5 + delay / (2 * maxAbs)) : "var(--border)",
      trips: d?.total_trips ?? 0,
    };
  });

  const worst = [...dense].filter((d) => d.delay != null).sort((a, b) => b.delay - a.delay)[0];

  return (
    <>
      <div className="control" style={{ marginBottom: 12 }}>
        <select className="select" style={{ width: "100%" }} value={routeId} onChange={(e) => setRouteId(e.target.value)}>
          <option value="">Whole network</option>
          {routes.map((r) => (
            <option key={r.route_id} value={r.route_id}>Route {r.route_short_name || r.route_id}</option>
          ))}
        </select>
      </div>

      {worst && (
        <div className="row" style={{ marginBottom: 6 }}>
          <div className="meta">
            <div className="t">Peak lateness at {fmtHour(worst.hour)}</div>
            <div className="s">{selected ? `Route ${selected.route_short_name || selected.route_id}` : "Network-wide"}</div>
          </div>
          <span className="val" style={{ color: "var(--bad)" }}>{fmtDelay(worst.delay)}</span>
        </div>
      )}

      <div className="section-label">Delay by hour of day</div>
      <div className="hourbar">
        {dense.map((d) => (
          <div key={d.hour} className="cell" style={{ background: d.color }} title={`${d.label}: ${fmtDelay(d.delay)}`} />
        ))}
      </div>
      <div className="hourbar-axis">
        {dense.map((d) => (
          <span key={d.hour} style={{ textAlign: "center" }}>{d.hour % 6 === 0 ? d.label : ""}</span>
        ))}
      </div>

      <div className="chart-card" style={{ marginTop: 16 }}>
        <div className="sub">Mean delay (minutes) — green early, red late</div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={dense} margin={{ top: 6, right: 6, left: -24, bottom: 0 }}>
            <XAxis dataKey="label" tick={{ fontSize: 9, fill: "var(--text-faint)" }} interval={2} />
            <YAxis tick={{ fontSize: 10, fill: "var(--text-faint)" }} width={42} />
            <ReferenceLine y={0} stroke="var(--text-faint)" />
            <Tooltip content={<HourTip />} />
            <Bar dataKey="min" radius={[3, 3, 0, 0]}>
              {dense.map((d) => <Cell key={d.hour} fill={d.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}

function HourTip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="glass" style={{ padding: "7px 11px", fontSize: 12 }}>
      <b>{d.label}</b><br />{fmtDelay(d.delay)} · {d.trips} trips
    </div>
  );
}
