import { SPEED_COLORS, delayColor } from "../map/basemaps.js";

// Context-sensitive map legend, bottom-left.
export default function Legend({ view, colorBy }) {
  if (view === "live") {
    const rows =
      colorBy === "speed"
        ? [
            ["Stopped", SPEED_COLORS.stopped],
            ["Slow (<12 mph)", SPEED_COLORS.slow],
            ["Moving", SPEED_COLORS.moving],
          ]
        : [["Coloured by route", "var(--accent)"]];
    return (
      <div className="legend glass">
        <h4>Live fleet</h4>
        {rows.map(([t, c]) => (
          <div className="lg-row" key={t}>
            <span className="sw" style={{ background: c }} /> {t}
          </div>
        ))}
        <div className="lg-row">
          <span className="sw" style={{ background: "transparent", border: "2px dashed #ff5d6c" }} /> Bunched
        </div>
      </div>
    );
  }

  if (view === "stops" || view === "routes") {
    return (
      <div className="legend glass">
        <h4>{view === "stops" ? "Stop delay" : "Route delay"}</h4>
        <div className="lg-row"><span className="sw" style={{ background: delayColor(0) }} /> Early</div>
        <div className="lg-row"><span className="sw" style={{ background: delayColor(0.5) }} /> On time</div>
        <div className="lg-row"><span className="sw" style={{ background: delayColor(1) }} /> Late</div>
      </div>
    );
  }

  return null;
}
