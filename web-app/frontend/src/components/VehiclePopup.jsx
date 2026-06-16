import { useEffect } from "react";
import maplibregl from "maplibre-gl";

// Renders a MapLibre popup for a clicked vehicle. Pure imperative bridge.
export default function VehiclePopup({ map, popup, onClose, cityTimezone }) {
  useEffect(() => {
    if (!map || !popup) return;
    const p = popup.props;
    const speed = p.speed_mph != null && p.speed_mph !== "null" ? `${p.speed_mph} mph` : "—";
    const bunched = p.bunched === true || p.bunched === "true";

    const el = new maplibregl.Popup({ closeButton: true, offset: 14, maxWidth: "260px" })
      .setLngLat(popup.lngLat)
      .setHTML(`
        <div class="vp">
          <div class="vp-head">
            <span class="chip" style="background:${p.route_color}">${p.route_short_name || "?"}</span>
            <strong>${p.trip_headsign || "Unknown route"}</strong>
          </div>
          <div class="vp-rows">
            <div>Vehicle <b>${p.vehicle_id}</b></div>
            <div>Speed <b>${speed}</b>${bunched ? ' · <b style="color:#ff5d6c">bunched</b>' : ""}</div>
            <div>Last seen <b>${p.last_timestamp ? new Date(p.last_timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", timeZone: cityTimezone, timeZoneName: "short" }) : "—"}</b></div>
          </div>
        </div>
      `)
      .addTo(map);

    el.on("close", onClose);
    return () => el.remove();
  }, [map, popup, onClose]);

  return null;
}
