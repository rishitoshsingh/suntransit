import { useMemo, useState } from "react";

// Live panel: colour-by toggle, route search, most-active routes, and bunching alerts.
export default function LivePanel({ snapshot, colorBy, setColorBy, onFocus, onSelectRoute, selRoute }) {
  const [query, setQuery] = useState("");

  const pulse = snapshot?.pulse;
  const bunching = snapshot?.bunching || [];
  const vehicleById = Object.fromEntries((snapshot?.vehicles || []).map((v) => [v.vehicle_id, v]));

  // All unique active routes derived from the live snapshot.
  const allRoutes = useMemo(() => {
    const seen = new Map();
    for (const v of snapshot?.vehicles || []) {
      if (!seen.has(v.route_id)) seen.set(v.route_id, v);
    }
    return [...seen.values()].sort((a, b) =>
      (a.route_short_name || a.route_id).localeCompare(b.route_short_name || b.route_id, undefined, { numeric: true })
    );
  }, [snapshot?.vehicles]);

  const q = query.trim().toLowerCase();
  const filtered = q
    ? allRoutes.filter((v) =>
        (v.route_short_name || "").toLowerCase().includes(q) ||
        String(v.route_id).toLowerCase().includes(q)
      )
    : null;

  return (
    <>
      <div className="section-label">Colour vehicles by</div>
      <div className="tabs" style={{ width: "100%" }}>
        <button className={`tab ${colorBy === "route" ? "active" : ""}`} style={{ flex: 1 }} onClick={() => setColorBy("route")}>Route</button>
        <button className={`tab ${colorBy === "speed" ? "active" : ""}`} style={{ flex: 1 }} onClick={() => setColorBy("speed")}>Speed</button>
      </div>

      <div className="section-label">Route search</div>
      <div className="search-box">
        <input
          type="text" placeholder="Route number or name…"
          value={query} onChange={(e) => setQuery(e.target.value)}
        />
        {query && <button className="search-clear" onClick={() => setQuery("")}>×</button>}
      </div>

      {filtered ? (
        filtered.length ? filtered.map((v) => (
          <RouteRow key={v.route_id} routeId={v.route_id} shortName={v.route_short_name} color={v.route_color}
            selected={selRoute === v.route_id} onSelect={onSelectRoute} />
        )) : <div className="empty">No routes match "{query}"</div>
      ) : (
        <>
          <div className="section-label">Most vehicles in service</div>
          {pulse?.busiest_routes?.length ? (
            pulse.busiest_routes.map((r) => (
              <RouteRow key={r.route_id} routeId={r.route_id} shortName={r.route_short_name} color={r.route_color}
                count={r.count} selected={selRoute === r.route_id} onSelect={onSelectRoute} />
            ))
          ) : (
            <div className="empty">Waiting for live data…</div>
          )}

          <div className="section-label">
            Bunching alerts {bunching.length > 0 && <span className="badge worsening">{bunching.length}</span>}
          </div>
          {bunching.length ? (
            bunching.slice(0, 12).map((b, i) => {
              const v = vehicleById[b.a];
              return (
                <div className="row" key={i} style={{ cursor: "pointer" }}
                  onClick={() => v && onFocus(v.lon, v.lat)}>
                  <span className="chip" style={{ background: v?.route_color || "#888" }}>{b.route_short_name || "?"}</span>
                  <div className="meta">
                    <div className="t">Buses {b.a} + {b.b}</div>
                    <div className="s">{b.distance_m} m apart</div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="empty">No bunching detected — fleet is well spaced. 🎉</div>
          )}
        </>
      )}
    </>
  );
}

function RouteRow({ routeId, shortName, color, count, selected, onSelect }) {
  return (
    <div className={`row ${selected ? "selected" : ""}`} style={{ cursor: "pointer" }}
      onClick={() => onSelect?.(routeId)}>
      <span className="chip" style={{ background: color }}>{shortName || "?"}</span>
      <div className="meta"><div className="t">Route {shortName || routeId}</div></div>
      {count != null && <span className="val">{count}</span>}
    </div>
  );
}
