// Free CARTO vector basemaps — no API key. One per theme.
export const BASEMAPS = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};

// 5-stop diverging ramp: dark-yellow → yellow → green → red → dark-red
// 0.0 = very early (≤−10 min), 0.5 = on time, 1.0 = very late (≥+10 min)
export function delayColor(scaled /* 0..1, 0.5 = on time */) {
  const t = Math.max(0, Math.min(1, scaled));
  const stops = [
    [0.00, [180, 120,   0]],  // dark amber  ≤ −10 min
    [0.25, [250, 204,  21]],  // yellow        −5 min
    [0.50, [ 34, 197,  94]],  // green          on time
    [0.75, [239,  68,  68]],  // red           +5 min
    [1.00, [153,  27,  27]],  // dark red    ≥ +10 min
  ];
  let i = 0;
  while (i < stops.length - 2 && t > stops[i + 1][0]) i++;
  const [t0, c0] = stops[i], [t1, c1] = stops[i + 1];
  const k = (t - t0) / (t1 - t0);
  const lerp = (a, b) => Math.round(a + (b - a) * k);
  return `rgb(${lerp(c0[0], c1[0])},${lerp(c0[1], c1[1])},${lerp(c0[2], c1[2])})`;
}

export const SPEED_COLORS = {
  stopped: "#ff5d6c",
  slow: "#ffc24b",
  moving: "#2ee6a6",
  unknown: "#8794ad",
};

// H3 hexagon heatmap. Resolutions precomputed by the batch job; this mirrors the
// backend ZOOM_TO_RES (app/config.py) so the map requests the right grain by zoom.
export const H3_RESOLUTIONS = [7, 8, 9];
export function resForZoom(zoom) {
  if (zoom < 9.5) return 7; // city overview
  if (zoom < 12) return 8;  // neighborhood
  return 9;                 // street
}
