import { useEffect, useState } from "react";
import { API } from "../api.js";
import { agencyLabel, defaultMaxDate, daysAgo } from "../util.js";

const TABS = [
  { id: "live", label: "Live" },
  { id: "stops", label: "Stops" },
  { id: "routes", label: "Routes" },
  { id: "trends", label: "Trends" },
  { id: "hourly", label: "Late Clock" },
];

export default function TopBar({
  cities, city, setCity, view, setView, date, setDate, agency, theme, setTheme, liveStatus,
}) {
  const [bounds, setBounds] = useState({ min: daysAgo(365), max: defaultMaxDate() });

  // Date range follows the selected agency's available history.
  useEffect(() => {
    if (!agency) return;
    API.oldestDate(agency)
      .then(({ oldest_date }) =>
        setBounds({ min: oldest_date || daysAgo(365), max: defaultMaxDate() })
      )
      .catch(() => {});
  }, [agency]);

  const showDate = view === "stops" || view === "routes";

  return (
    <div className="topbar glass">
      <div className="brand">
        <span className="dot" />
        SunTransit
        <small>· transit intelligence</small>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={`tab ${view === t.id ? "active" : ""}`} onClick={() => setView(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="spacer" />

      {liveStatus && (
        <div className={`live-pill ${liveStatus === "live" ? "" : "closed"}`}>
          <span className="pulse" />
          {liveStatus === "live" ? "LIVE" : "reconnecting…"}
        </div>
      )}

      {showDate && (
        <input
          type="date" className="datepick" value={date}
          min={bounds.min} max={bounds.max}
          onChange={(e) => setDate(e.target.value)}
        />
      )}

      <div className="control">
        <select className="select" value={city} onChange={(e) => setCity(e.target.value)} title={agencyLabel(agency)}>
          {Object.keys(cities).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <button className="icon-btn" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} title="Toggle theme">
        {theme === "dark" ? "☀" : "☾"}
      </button>
    </div>
  );
}
