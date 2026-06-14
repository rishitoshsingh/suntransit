import { Fragment, useEffect, useMemo, useState } from "react";
import { API } from "../api.js";
import { fmtDelay } from "../util.js";

const BANDS = [
  { key: "early", label: "Early" },
  { key: "ontime", label: "On time" },
  { key: "late", label: "Late" },
];

const bandOf = (d) => (d <= -60 ? "early" : d >= 60 ? "late" : "ontime");

export default function RoutesPanel({ city, date, onSelect, selRouteId }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    let cancel = false;
    API.routeDelays(city, date).then((d) => !cancel && setData(d)).catch(() => !cancel && setData(null));
    return () => { cancel = true; };
  }, [city, date]);

  // Group into Early / On time / Late, each sorted most-early -> most-late so the
  // whole list reads as one gradient from the top down.
  const grouped = useMemo(() => {
    const g = { early: [], ontime: [], late: [] };
    (data?.routes || [])
      .filter((r) => r.mean_delay != null)
      .slice()
      .sort((a, b) => a.mean_delay - b.mean_delay)
      .forEach((r) => g[bandOf(r.mean_delay)].push(r));
    return g;
  }, [data]);

  if (!data) return <div className="empty">Loading route delays…</div>;
  const total = grouped.early.length + grouped.ontime.length + grouped.late.length;
  if (!total) return <div className="empty">No delay data for this date yet.</div>;

  return (
    <>
      {BANDS.map(({ key, label }) => (
        <Fragment key={key}>
          <div className="section-label">{label} <span className="sub">· {grouped[key].length}</span></div>
          {grouped[key].length
            ? grouped[key].map((r) => (
                <RouteRow key={r.route_id} r={r} onSelect={onSelect} selected={selRouteId === r.route_id} />
              ))
            : <div className="sub" style={{ padding: "2px 0 4px" }}>none</div>}
        </Fragment>
      ))}
    </>
  );
}

function RouteRow({ r, onSelect, selected }) {
  const d = r.mean_delay;
  const color = Math.abs(d) < 60 ? "var(--text-faint)" : d < 0 ? "var(--good)" : "var(--bad)";
  return (
    <div className={`row ${selected ? "selected" : ""}`} style={{ cursor: "pointer" }} onClick={() => onSelect?.(r)}>
      <span className="chip" style={{ background: r.route_color }}>{r.route_short_name || "?"}</span>
      <div className="meta">
        <div className="t">Route {r.route_short_name || r.route_id}</div>
        <div className="s">{r.total_trips} trips</div>
      </div>
      <span className="val" style={{ color }}>{fmtDelay(d)}</span>
    </div>
  );
}
