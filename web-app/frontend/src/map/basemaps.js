// Free CARTO vector basemaps — no API key. One per theme.
export const BASEMAPS = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};

// Diverging colour for delay: negative (early) = green, ~0 = neutral, positive (late) = red.
export function delayColor(scaled /* 0..1, .5 = on time */) {
  const t = Math.max(0, Math.min(1, scaled));
  const green = [46, 230, 166], grey = [120, 134, 160], red = [255, 93, 108];
  const lerp = (a, b, k) => Math.round(a + (b - a) * k);
  const mix = (a, b, k) => `rgb(${lerp(a[0], b[0], k)},${lerp(a[1], b[1], k)},${lerp(a[2], b[2], k)})`;
  return t < 0.5 ? mix(green, grey, t / 0.5) : mix(grey, red, (t - 0.5) / 0.5);
}

export const SPEED_COLORS = {
  stopped: "#ff5d6c",
  slow: "#ffc24b",
  moving: "#2ee6a6",
  unknown: "#8794ad",
};
