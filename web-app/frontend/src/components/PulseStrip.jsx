import { forwardRef } from "react";
import { fmtDelay } from "../util.js";

const PulseStrip = forwardRef(function PulseStrip({ pulse }, ref) {
  if (!pulse) return null;
  const ot = pulse.on_time;

  return (
    <div ref={ref} className="pulse-strip glass">
      <Stat v={pulse.active_vehicles ?? "—"} l="Active vehicles" cls="accent" />
      <Stat v={pulse.avg_speed_mph != null ? `${pulse.avg_speed_mph}` : "—"} l="Avg mph" />
      <Stat v={`${pulse.moving ?? "—"}/${pulse.stopped ?? "—"}`} l="Moving / stopped" cls="good" />
      <Stat
        v={pulse.bunched_pairs ?? "—"} l="Bunched pairs"
        cls={pulse.bunched_pairs > 0 ? "bad" : "good"}
      />
      {ot && (
        <Stat
          v={fmtDelay(ot.mean_delay)}
          l={`Avg delay · ${ot.date}`}
          cls={Math.abs(ot.mean_delay) < 60 ? "good" : ot.mean_delay > 0 ? "bad" : "warn"}
        />
      )}
    </div>
  );
});

export default PulseStrip;

function Stat({ v, l, cls = "" }) {
  return (
    <div className="stat">
      <div className={`v ${cls}`}>{v}</div>
      <div className="l">{l}</div>
    </div>
  );
}
