// Live panel: colour-by toggle, most-active routes, and active bunching alerts.
export default function LivePanel({ snapshot, colorBy, setColorBy, onFocus, onSelectRoute, selRoute }) {
  const pulse = snapshot?.pulse;
  const bunching = snapshot?.bunching || [];
  const vehicleById = Object.fromEntries((snapshot?.vehicles || []).map((v) => [v.vehicle_id, v]));

  return (
    <>
      <div className="section-label">Colour vehicles by</div>
      <div className="tabs" style={{ width: "100%" }}>
        <button className={`tab ${colorBy === "route" ? "active" : ""}`} style={{ flex: 1 }} onClick={() => setColorBy("route")}>Route</button>
        <button className={`tab ${colorBy === "speed" ? "active" : ""}`} style={{ flex: 1 }} onClick={() => setColorBy("speed")}>Speed</button>
      </div>

      <div className="section-label">Most vehicles in service</div>
      {pulse?.busiest_routes?.length ? (
        pulse.busiest_routes.map((r) => (
          <div className={`row ${selRoute === r.route_id ? "selected" : ""}`} key={r.route_id}
            style={{ cursor: "pointer" }} onClick={() => onSelectRoute?.(r.route_id)}>
            <span className="chip" style={{ background: r.route_color }}>{r.route_short_name || "?"}</span>
            <div className="meta"><div className="t">Route {r.route_short_name || r.route_id}</div></div>
            <span className="val">{r.count}</span>
          </div>
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
  );
}
