// Imperative MapLibre layer manager. React drives it via effects; all the
// add-source / add-layer / set-data plumbing lives here so the components stay clean.
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { BASEMAPS, delayColor, SPEED_COLORS } from "./basemaps.js";

const EMPTY = { type: "FeatureCollection", features: [] };

// Source ids -> the layers that render them. Layers are added once and toggled per view.
const SOURCES = ["routes", "stops", "trails", "bunching", "vehicles"];
// Selection-highlight sources (a clicked stop / a clicked route shape).
const SEL_SOURCES = ["sel-stop", "sel-route"];

export class MapController {
  constructor(container, theme, onVehicleClick) {
    this.theme = theme;
    this.onVehicleClick = onVehicleClick;
    this._data = {
      routes: EMPTY, stops: EMPTY, trails: EMPTY, bunching: EMPTY, vehicles: EMPTY,
      "sel-stop": EMPTY, "sel-route": EMPTY,
    };
    this._selRoute = null; // live: route_id whose vehicles are highlighted
    this._view = "live";

    this.map = new maplibregl.Map({
      container,
      style: BASEMAPS[theme],
      center: [-112.074, 33.4484],
      zoom: 10.5,
      attributionControl: { compact: true },
    });
    this.map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    this.map.on("load", () => this._ensureLayers());
  }

  // (Re)create all sources + layers. Called on first load and after a style swap.
  _ensureLayers() {
    const m = this.map;
    for (const id of [...SOURCES, ...SEL_SOURCES]) {
      if (!m.getSource(id)) m.addSource(id, { type: "geojson", data: this._data[id] });
      else m.getSource(id).setData(this._data[id]);
    }

    this._add("routes-line", "line", "routes", {
      "line-color": ["get", "color"], "line-width": ["interpolate", ["linear"], ["zoom"], 9, 2, 14, 5],
      "line-opacity": 0.85,
    }, { "line-cap": "round", "line-join": "round" });

    this._add("stops-circle", "circle", "stops", {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 3, 15, 9],
      "circle-color": ["get", "color"], "circle-opacity": 0.85,
      "circle-stroke-width": 0.5, "circle-stroke-color": "rgba(0,0,0,0.3)",
    });

    this._add("trails-line", "line", "trails", {
      "line-color": ["get", "color"], "line-width": 3, "line-opacity": 0.45,
    }, { "line-cap": "round", "line-join": "round" });

    this._add("bunching-line", "line", "bunching", {
      "line-color": "#ff5d6c", "line-width": 2, "line-dasharray": [1, 1], "line-opacity": 0.9,
    });

    this._add("vehicles-circle", "circle", "vehicles", {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 3.5, 14, 7],
      "circle-color": ["get", "color"],
      "circle-stroke-width": ["case", ["get", "bunched"], 2.5, 1],
      "circle-stroke-color": ["case", ["get", "bunched"], "#ff5d6c", "rgba(255,255,255,0.6)"],
    });

    // selection highlights, drawn on top of everything
    this._add("sel-route-line", "line", "sel-route", {
      "line-color": ["get", "color"],
      "line-width": ["interpolate", ["linear"], ["zoom"], 9, 5, 14, 9],
      "line-opacity": 1,
    }, { "line-cap": "round", "line-join": "round" });

    this._add("sel-stop-ring", "circle", "sel-stop", {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 9, 15, 18],
      "circle-color": "rgba(0,0,0,0)",
      "circle-stroke-width": 3,
      "circle-stroke-color": "#ffffff",
    });

    // click + hover on vehicles
    if (!this._wired) {
      this.map.on("click", "vehicles-circle", (e) => this.onVehicleClick?.(e.features[0].properties, e.lngLat));
      this.map.on("mouseenter", "vehicles-circle", () => (this.map.getCanvas().style.cursor = "pointer"));
      this.map.on("mouseleave", "vehicles-circle", () => (this.map.getCanvas().style.cursor = ""));
      this._wired = true;
    }
    this.applyView(this._view);
  }

  _add(id, type, source, paint, layout = {}) {
    if (this.map.getLayer(id)) return;
    this.map.addLayer({ id, type, source, paint, layout });
  }

  _set(id, data) {
    this._data[id] = data;
    const s = this.map.getSource(id);
    if (s) s.setData(data);
  }

  // ---- view visibility ----
  applyView(view) {
    this._view = view;
    const vis = {
      "routes-line": view === "routes",
      "stops-circle": view === "stops",
      "trails-line": view === "live",
      "bunching-line": view === "live",
      "vehicles-circle": view === "live",
      "sel-route-line": view === "routes",
      "sel-stop-ring": view === "stops",
    };
    for (const [id, on] of Object.entries(vis)) {
      if (this.map.getLayer(id)) this.map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    }
    this._applyVehicleHighlight(); // re-assert after (re)building layers
  }

  // ---- data setters ----
  setLive(snapshot, colorBy) {
    const bunched = new Set(snapshot.bunching.flatMap((p) => [p.a, p.b]));
    const vehicles = {
      type: "FeatureCollection",
      features: snapshot.vehicles.map((v) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [v.lon, v.lat] },
        properties: {
          ...v,
          bunched: bunched.has(v.vehicle_id),
          color: colorBy === "speed" ? SPEED_COLORS[v.speed_class] : v.route_color,
        },
      })),
    };
    const trails = {
      type: "FeatureCollection",
      features: snapshot.vehicles
        .filter((v) => v.trail && v.trail.length > 1)
        .map((v) => ({
          type: "Feature",
          geometry: { type: "LineString", coordinates: v.trail.map((p) => [p[1], p[0]]) },
          properties: {
            route_id: v.route_id,
            color: colorBy === "speed" ? SPEED_COLORS[v.speed_class] : v.route_color,
          },
        })),
    };
    const bunching = {
      type: "FeatureCollection",
      features: snapshot.bunching.map((p) => ({
        type: "Feature", geometry: { type: "LineString", coordinates: p.line }, properties: {},
      })),
    };
    this._set("vehicles", vehicles);
    this._set("trails", trails);
    this._set("bunching", bunching);
  }

  setStops(delays) {
    this._set("stops", {
      type: "FeatureCollection",
      features: delays
        .filter((d) => d.stop_lon != null && d.stop_lat != null)
        .map((d) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [d.stop_lon, d.stop_lat] },
          properties: { ...d, color: delayColor(d.scaled_delay) },
        })),
    });
  }

  setRoutes(routes) {
    this._set("routes", {
      type: "FeatureCollection",
      features: routes
        .filter((r) => r.route_path && r.route_path.length > 1)
        .map((r) => ({
          type: "Feature",
          geometry: { type: "LineString", coordinates: r.route_path.map((p) => [p[1], p[0]]) },
          properties: { color: r._color },
        })),
    });
  }

  flyTo(center, zoom = 12) {
    this.map.flyTo({ center, zoom, duration: 800 });
  }

  // ---- selection highlights ----

  // Ring a single clicked stop (stops view). Pass null to clear.
  highlightStop(stop) {
    this._set("sel-stop", stop && stop.stop_lon != null ? {
      type: "FeatureCollection",
      features: [{
        type: "Feature",
        geometry: { type: "Point", coordinates: [stop.stop_lon, stop.stop_lat] },
        properties: {},
      }],
    } : EMPTY);
  }

  // Draw a clicked route's shape (routes view) and fit the map to it.
  // path is the GTFS shape as [[lat, lon], ...]; pass null/empty to clear.
  showRoute(path, color = "#ffffff") {
    if (!path || path.length < 2) { this._set("sel-route", EMPTY); return; }
    const line = path.map((p) => [p[1], p[0]]);
    this._set("sel-route", {
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: { type: "LineString", coordinates: line }, properties: { color } }],
    });
    const bounds = line.reduce((b, c) => b.extend(c), new maplibregl.LngLatBounds(line[0], line[0]));
    this.map.fitBounds(bounds, { padding: 80, duration: 800, maxZoom: 14 });
  }

  clearRoute() { this._set("sel-route", EMPTY); }

  // Highlight live vehicles on one route, dim the rest (live view). Pass null to clear.
  setVehicleHighlight(routeId) {
    this._selRoute = routeId || null;
    this._applyVehicleHighlight();
  }

  _applyVehicleHighlight() {
    const m = this.map;
    const rid = this._selRoute;
    if (m.getLayer("vehicles-circle")) {
      const isSel = ["==", ["get", "route_id"], rid];
      m.setPaintProperty("vehicles-circle", "circle-opacity", rid ? ["case", isSel, 1, 0.12] : 1);
      m.setPaintProperty("vehicles-circle", "circle-radius", rid
        ? ["interpolate", ["linear"], ["zoom"], 9, ["case", isSel, 6, 3], 14, ["case", isSel, 10, 5]]
        : ["interpolate", ["linear"], ["zoom"], 9, 3.5, 14, 7]);
      m.setPaintProperty("vehicles-circle", "circle-stroke-color", rid
        ? ["case", isSel, "#ffffff", "rgba(255,255,255,0.4)"]
        : ["case", ["get", "bunched"], "#ff5d6c", "rgba(255,255,255,0.6)"]);
    }
    if (m.getLayer("trails-line")) {
      m.setPaintProperty("trails-line", "line-opacity",
        rid ? ["case", ["==", ["get", "route_id"], rid], 0.7, 0.05] : 0.45);
    }
  }

  setTheme(theme) {
    this.theme = theme;
    this.map.setStyle(BASEMAPS[theme]);
    this.map.once("styledata", () => this._ensureLayers());
  }

  resize() { this.map.resize(); }
  destroy() { this.map.remove(); }
}
