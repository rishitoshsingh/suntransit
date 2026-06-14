// All backend calls live here. URLs are same-origin (Vite proxies in dev,
// FastAPI serves the built app in prod).

async function get(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

export const API = {
  cities: () => get("/api/cities"),
  health: () => get("/api/health"),
  oldestDate: (agency) => get(`/api/oldest_date/${agency}`),

  stopDelays: (city, date) => get(`/api/stop_delays/${city}/${date}`),
  routeDelays: (city, date) => get(`/api/route_delays/${city}/${date}`),
  routePath: (city, routeId) => get(`/api/route_path/${city}/${encodeURIComponent(routeId)}`),
  agencyDelays: (agency, date) => get(`/api/agency_delays/${agency}/${date}`),

  agencyTrend: (city) => get(`/api/trends/agency/${city}`),
  routeTrends: (city) => get(`/api/trends/routes/${city}`),

  agencyHourly: (city) => get(`/api/hourly/agency/${city}`),
  routeHourly: (city) => get(`/api/hourly/routes/${city}`),

  positions: (city) => get(`/api/positions/${city}`),
};

// Live WebSocket. Returns an object with .close(); pushes snapshots to onSnapshot.
export function openLiveSocket(city, onSnapshot, onStatus) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/live/${city}`);
  ws.onopen = () => onStatus?.("live");
  ws.onclose = () => onStatus?.("closed");
  ws.onerror = () => onStatus?.("error");
  ws.onmessage = (e) => {
    try {
      onSnapshot(JSON.parse(e.data));
    } catch {
      /* ignore malformed frame */
    }
  };
  return ws;
}
