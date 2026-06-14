import { useEffect, useState } from "react";
import { API } from "../api.js";
import { fmtDelay } from "../util.js";

export default function StopsPanel({ city, date, onSelect, selStop }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    let cancel = false;
    API.stopDelays(city, date).then((d) => !cancel && setData(d)).catch(() => !cancel && setData(null));
    return () => { cancel = true; };
  }, [city, date]);

  if (!data) return <div className="empty">Loading stop delays…</div>;
  if (!data.delays?.length) return <div className="empty">No delay data for this date yet.</div>;

  return (
    <>
      <div className="section-label">Most delayed stops</div>
      {data.top_5_stops.map((s) => <StopRow key={s.stop_id} s={s} onSelect={onSelect} selected={selStop === s.stop_id} bad />)}
      <div className="section-label">Most ahead-of-schedule</div>
      {data.bottom_5_stops.map((s) => <StopRow key={s.stop_id} s={s} onSelect={onSelect} selected={selStop === s.stop_id} />)}
    </>
  );
}

function StopRow({ s, onSelect, selected, bad }) {
  return (
    <div className={`row ${selected ? "selected" : ""}`} style={{ cursor: "pointer" }}
      onClick={() => s.stop_lon != null && onSelect(s)}>
      <div className="meta">
        <div className="t">{s.stop_name || s.stop_id}</div>
        <div className="s">{s.total_trips} trips</div>
      </div>
      <span className="val" style={{ color: bad ? "var(--bad)" : "var(--good)" }}>{fmtDelay(s.mean_delay)}</span>
    </div>
  );
}
