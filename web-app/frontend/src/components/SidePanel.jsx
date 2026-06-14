import LivePanel from "../panels/LivePanel.jsx";
import StopsPanel from "../panels/StopsPanel.jsx";
import RoutesPanel from "../panels/RoutesPanel.jsx";
import TrendsPanel from "../panels/TrendsPanel.jsx";
import HourlyPanel from "../panels/HourlyPanel.jsx";

const HEAD = {
  live: ["Network Pulse", "Live fleet derived from Redis — speed and bunching computed on the fly."],
  stops: ["Stop Delays", "Mean arrival delay per stop over the selected 7-day window."],
  routes: ["Route Delays", "Best and worst performing routes over the selected window."],
  trends: ["Reliability Trends", "Full history of on-time performance — improving or worsening."],
  hourly: ["The Late Clock", "When is transit late? Hour-of-day profile from the last 30 days."],
};

export default function SidePanel({
  open, setOpen, view, city, date, agency, snapshot, colorBy, setColorBy, onFocus,
  onSelectStop, selStop, onSelectRoute, selRouteId, onSelectLiveRoute, selLiveRoute,
}) {
  const [title, sub] = HEAD[view] || ["", ""];

  return (
    <>
      <button className={`icon-btn panel-toggle ${open ? "open" : ""}`} onClick={() => setOpen(!open)}
        title="Toggle panel">
        {open ? "›" : "‹"}
      </button>

      <aside className={`panel glass ${open ? "" : "closed"}`}>
        <div className="panel-head">
          <h2>{title}</h2>
          <p>{sub}</p>
        </div>
        <div className="panel-body">
          {view === "live" && <LivePanel snapshot={snapshot} colorBy={colorBy} setColorBy={setColorBy} onFocus={onFocus} onSelectRoute={onSelectLiveRoute} selRoute={selLiveRoute} />}
          {view === "stops" && <StopsPanel city={city} date={date} onSelect={onSelectStop} selStop={selStop} />}
          {view === "routes" && <RoutesPanel city={city} date={date} onSelect={onSelectRoute} selRouteId={selRouteId} />}
          {view === "trends" && <TrendsPanel city={city} agency={agency} />}
          {view === "hourly" && <HourlyPanel city={city} />}
        </div>
      </aside>
    </>
  );
}
