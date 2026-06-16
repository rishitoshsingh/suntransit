import LivePanel from "../panels/LivePanel.jsx";
import StopsPanel from "../panels/StopsPanel.jsx";
import RoutesPanel from "../panels/RoutesPanel.jsx";
import TrendsPanel from "../panels/TrendsPanel.jsx";
import HourlyPanel from "../panels/HourlyPanel.jsx";

const HEAD = {
  live: ["Network Pulse", "Live fleet derived from Redis — speed and bunching computed on the fly."],
  stops: ["Stops + Hex Heatmap", "Grey dots mark stop locations; hex colour shows rolling 30-day mean delay. Use the hour slider to filter by time of day."],
  routes: ["Route Delays", "Best and worst performing routes over the selected window."],
  analytics: ["Analytics Dashboard", "System reliability trends and hour-of-day lateness profile."],
};

export default function SidePanel({
  open, setOpen, view, city, date, agency, h3Res, snapshot, colorBy, setColorBy, onFocus,
  onSelectStop, selStop, onSelectRoute, selRouteId, onSelectLiveRoute, selLiveRoute,
}) {
  const [title, sub] = HEAD[view] || ["", ""];
  const isAnalytics = view === "analytics";

  return (
    <>
      {!isAnalytics && (
        <button className={`icon-btn panel-toggle ${open ? "open" : ""}`} onClick={() => setOpen(!open)}
          title="Toggle panel">
          {open ? "›" : "‹"}
        </button>
      )}

      <aside className={`panel glass ${open ? "" : "closed"} ${isAnalytics ? "analytics" : ""}`}>
        <div className="panel-head">
          <h2>{title}</h2>
          <p>{sub}</p>
        </div>
        <div className="panel-body">
          {view === "live" && <LivePanel snapshot={snapshot} colorBy={colorBy} setColorBy={setColorBy} onFocus={onFocus} onSelectRoute={onSelectLiveRoute} selRoute={selLiveRoute} />}
          {view === "stops" && <StopsPanel city={city} date={date} onSelect={onSelectStop} selStop={selStop} />}
          {view === "routes" && <RoutesPanel city={city} date={date} onSelect={onSelectRoute} selRouteId={selRouteId} />}
          {isAnalytics && (
            <div className="analytics-grid">
              <div className="analytics-col">
                <TrendsPanel city={city} agency={agency} />
              </div>
              <div className="analytics-col">
                <HourlyPanel city={city} />
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
