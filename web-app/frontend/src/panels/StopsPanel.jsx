import { useEffect, useState } from "react";
import { API } from "../api.js";
import { fmtDelay } from "../util.js";
import { delayColor } from "../map/basemaps.js";

const SCALE_MAX = 600;
const delayColorFixed = (s) => delayColor(Math.max(0, Math.min(1, 0.5 + s / (2 * SCALE_MAX))));

export default function StopsPanel({ city, date, onSelect, selStop }) {
  const [data, setData] = useState(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancel = false;
    setQuery("");
    API.stopDelays(city, date).then((d) => !cancel && setData(d)).catch(() => !cancel && setData(null));
    return () => { cancel = true; };
  }, [city, date]);

  if (!data) return <div className="empty">Loading stop delays…</div>;
  if (!data.delays?.length) return <div className="empty">No delay data for this date yet.</div>;

  const q = query.trim().toLowerCase();
  const searchResults = q
    ? data.delays
        .filter((s) => (s.stop_name || s.stop_id).toLowerCase().includes(q))
        .slice(0, 25)
    : null;

  return (
    <>
      <div className="search-box">
        <input
          type="text" placeholder="Search stops…"
          value={query} onChange={(e) => setQuery(e.target.value)}
        />
        {query && <button className="search-clear" onClick={() => setQuery("")}>×</button>}
      </div>

      {searchResults ? (
        searchResults.length ? (
          searchResults.map((s) => <StopRow key={s.stop_id} s={s} onSelect={onSelect} selected={selStop === s.stop_id} />)
        ) : (
          <div className="empty">No stops match "{query}"</div>
        )
      ) : (
        <>
          <div className="section-label">Most delayed stops</div>
          {data.top_5_stops.map((s) => <StopRow key={s.stop_id} s={s} onSelect={onSelect} selected={selStop === s.stop_id} />)}
          <div className="section-label">Most ahead-of-schedule</div>
          {data.bottom_5_stops.map((s) => <StopRow key={s.stop_id} s={s} onSelect={onSelect} selected={selStop === s.stop_id} />)}
        </>
      )}
    </>
  );
}

function StopRow({ s, onSelect, selected }) {
  return (
    <div className={`row ${selected ? "selected" : ""}`} style={{ cursor: "pointer" }}
      onClick={() => s.stop_lon != null && onSelect(s)}>
      <div className="meta">
        <div className="t">{s.stop_name || s.stop_id}</div>
        <div className="s">{s.total_trips} trips</div>
      </div>
      <span className="val" style={{ color: delayColorFixed(s.mean_delay) }}>{fmtDelay(s.mean_delay)}</span>
    </div>
  );
}
