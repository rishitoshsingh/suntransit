import { useEffect, useRef, useState } from "react";
import { API } from "./api.js";
import { MapController } from "./map/mapController.js";
import { delayColor } from "./map/basemaps.js"; // used by colorRoutes below
import { useLive } from "./hooks/useLive.js";
import { defaultMaxDate } from "./util.js";
import TopBar from "./components/TopBar.jsx";
import PulseStrip from "./components/PulseStrip.jsx";
import SidePanel from "./components/SidePanel.jsx";
import Legend from "./components/Legend.jsx";
import VehiclePopup from "./components/VehiclePopup.jsx";
import HourSlider from "./components/HourSlider.jsx";
import AboutModal from "./components/AboutModal.jsx";

export default function App() {
  const mapRef = useRef(null);
  const mapEl = useRef(null);

  const [theme, setTheme] = useState("light");
  const [cities, setCities] = useState({});
  const [city, setCity] = useState("Phoenix");
  const [view, setView] = useState("live");
  const [h3Res, setH3Res] = useState(8);    // driven by zoom in the stops view
  const [h3Hour, setH3Hour] = useState(null); // null = all day, 0-23 = specific hour
  const [date, setDate] = useState(defaultMaxDate());
  const [panelOpen, setPanelOpen] = useState(true);
  const [colorBy, setColorBy] = useState("route"); // route | speed
  const [popup, setPopup] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selStop, setSelStop] = useState(null);      // stops view: clicked stop_id
  const [selRouteId, setSelRouteId] = useState(null); // routes view: clicked route_id
  const [selLiveRoute, setSelLiveRoute] = useState(null); // live view: highlighted route_id
  const [showAbout, setShowAbout] = useState(false);

  const agency = cities[city]?.agency;
  const { snapshot, status } = useLive(city, view === "live");

  // ---- one-time: load cities + create map ----
  useEffect(() => {
    API.cities().then(setCities).catch(() => {});
    const mc = new MapController(
      mapEl.current, theme,
      (props, lngLat) => setPopup({ props, lngLat }),
      (res) => setH3Res(res), // h3 view: zoom changed the resolution
    );
    mapRef.current = mc;
    return () => mc.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- theme ----
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    mapRef.current?.setTheme(theme);
  }, [theme]);

  // ---- recenter when city changes ----
  useEffect(() => {
    const c = cities[city]?.coordinates;
    if (c && mapRef.current) mapRef.current.flyTo([c[1], c[0]], 10.5);
    setPopup(null);
  }, [city, cities]);

  // ---- view visibility ----
  useEffect(() => {
    mapRef.current?.applyView(view);
    setPopup(null);
    if (view === "analytics") setPanelOpen(true);
  }, [view]);

  // ---- clear any selection/highlight when the dataset context changes ----
  useEffect(() => {
    setSelStop(null); setSelRouteId(null); setSelLiveRoute(null);
    mapRef.current?.highlightStop(null);
    mapRef.current?.clearRoute();
    mapRef.current?.clearLiveRoute();
    mapRef.current?.setVehicleHighlight(null);
  }, [view, city, date]);

  // ---- selection handlers (passed to the panels) ----
  const selectStop = (s) => {
    setSelStop(s.stop_id);
    mapRef.current?.highlightStop(s);
    if (s.stop_lon != null) mapRef.current?.flyTo([s.stop_lon, s.stop_lat], 14);
  };

  const selectRoute = async (r) => {
    const next = selRouteId === r.route_id ? null : r.route_id;
    setSelRouteId(next);
    if (!next) { mapRef.current?.clearRoute(); return; }
    const d = await API.routePath(city, r.route_id).catch(() => null);
    if (d?.route_path?.length) mapRef.current?.showRoute(d.route_path, r.route_color || d.route_color);
  };

  const selectLiveRoute = async (routeId) => {
    const next = selLiveRoute === routeId ? null : routeId;
    setSelLiveRoute(next);
    mapRef.current?.setVehicleHighlight(next);
    if (!next) { mapRef.current?.clearLiveRoute(); return; }
    const d = await API.routePath(city, next).catch(() => null);
    if (d?.route_path?.length) {
      const routeColor = snapshot?.vehicles?.find((v) => v.route_id === next)?.route_color || "#ffffff";
      mapRef.current?.setLiveRoute(d.route_path, routeColor);
    }
  };

  // ---- push live snapshot to the map ----
  useEffect(() => {
    if (view === "live" && snapshot) mapRef.current?.setLive(snapshot, colorBy);
  }, [snapshot, colorBy, view]);

  // ---- stop positions + route data (re-fetched on city/date change) ----
  useEffect(() => {
    if (!agency) return;
    let cancelled = false;

    async function load() {
      if (view === "stops") {
        setLoading(true);
        const d = await API.stopDelays(city, date).catch(() => null);
        if (!cancelled && d) mapRef.current?.setStops(d.delays);
        if (!cancelled) setLoading(false);
      } else if (view === "routes") {
        setLoading(true);
        const d = await API.routeDelays(city, date).catch(() => null);
        if (!cancelled && d) {
          const all = [...(d.top_5_routes || []), ...(d.bottom_5_routes || [])];
          mapRef.current?.setRoutes(colorRoutes(all));
        }
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [view, city, date, agency]);

  // ---- H3 hex heatmap (re-fetched on zoom/hour change, independent of stop data) ----
  useEffect(() => {
    if (view !== "stops" || !agency) return;
    let cancelled = false;
    API.h3Delays(city, h3Res, h3Hour).catch(() => null).then((d) => {
      if (!cancelled && d) mapRef.current?.setH3(d.cells);
    });
    return () => { cancelled = true; };
  }, [view, city, h3Res, h3Hour, agency]);

  return (
    <div className="app">
      <div id="map" ref={mapEl} />

      <TopBar
        cities={cities} city={city} setCity={setCity}
        view={view} setView={setView}
        date={date} setDate={setDate} agency={agency}
        theme={theme} setTheme={setTheme}
        liveStatus={view === "live" ? status : null}
        onAbout={() => setShowAbout(true)}
      />

      <Legend view={view} colorBy={colorBy} />

      {view === "live" && <PulseStrip pulse={snapshot?.pulse} agency={agency} />}

      <SidePanel
        open={panelOpen} setOpen={setPanelOpen}
        view={view} city={city} date={date} agency={agency} h3Res={h3Res}
        snapshot={snapshot} colorBy={colorBy} setColorBy={setColorBy}
        onFocus={(lng, lat) => mapRef.current?.flyTo([lng, lat], 14)}
        onSelectStop={selectStop} selStop={selStop}
        onSelectRoute={selectRoute} selRouteId={selRouteId}
        onSelectLiveRoute={selectLiveRoute} selLiveRoute={selLiveRoute}
      />

      {view === "stops" && <HourSlider hour={h3Hour} onChange={setH3Hour} />}

      {loading && <div className="loading"><div className="spinner" /></div>}

      {popup && (
        <VehiclePopup map={mapRef.current?.map} popup={popup} onClose={() => setPopup(null)}
          cityTimezone={cities[city]?.timezone} />
      )}

      {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}
    </div>
  );
}

// Colour each route line by its delay relative to the set (diverging scale).
function colorRoutes(routes) {
  const vals = routes.map((r) => r.mean_delay).filter((v) => v != null);
  const maxAbs = Math.max(1, ...vals.map(Math.abs));
  return routes.map((r) => {
    const scaled = Math.max(0, Math.min(1, 0.5 + (r.mean_delay ?? 0) / (2 * maxAbs)));
    return { ...r, _color: delayColor(scaled), _scaled: scaled };
  });
}
