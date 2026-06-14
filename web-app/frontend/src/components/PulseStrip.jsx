import { fmtDelay } from "../util.js";

// Live "command center" stat cards. All but on-time come straight from Redis.
export default function PulseStrip({ pulse }) {
  if (!pulse) return null;
  const ot = pulse.on_time;

  return (
    <div className="pulse-strip glass">
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
}

function Stat({ v, l, cls = "" }) {
  return (
    <div className="stat">
      <div className={`v ${cls}`}>{v}</div>
      <div className="l">{l}</div>
    </div>
  );
}
