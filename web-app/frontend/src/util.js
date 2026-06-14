// Small shared helpers (dates, formatting).

export function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().split("T")[0];
}

// Data lands a day late, so the newest selectable date is yesterday (or 2 days
// ago before 3am while the batch job runs).
export function defaultMaxDate() {
  return daysAgo(new Date().getHours() >= 3 ? 1 : 2);
}

export function agencyLabel(agency = "") {
  return agency.replace(/([a-z])([A-Z])/g, "$1 $2");
}

// Delay in seconds -> "+2m 30s late" / "1m 10s early" / "on time".
export function fmtDelay(sec) {
  if (sec == null) return "—";
  const late = sec >= 0;
  const a = Math.abs(Math.round(sec));
  if (a < 30) return "on time";
  const m = Math.floor(a / 60);
  const s = a % 60;
  const t = m ? `${m}m ${s}s` : `${s}s`;
  return `${t} ${late ? "late" : "early"}`;
}

export function fmtDelayShort(sec) {
  if (sec == null) return "—";
  const m = sec / 60;
  return `${m >= 0 ? "+" : ""}${m.toFixed(1)}m`;
}
