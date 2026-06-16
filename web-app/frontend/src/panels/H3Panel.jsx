import { useEffect, useState } from "react";
import { API } from "../api.js";
import { fmtDelay } from "../util.js";

// What each resolution roughly covers (mirrors basemaps.resForZoom).
const RES_LABEL = { 7: "city", 8: "neighborhood", 9: "street" };

export default function H3Panel({ city, res, onFocus }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    let cancel = false;
    setData(null);
    API.h3Delays(city, res).then((d) => !cancel && setData(d)).catch(() => !cancel && setData(null));
    return () => { cancel = true; };
  }, [city, res]);

  if (!data) return <div className="empty">Loading hex grid…</div>;
  const cells = (data.cells || []).filter((c) => c.mean_delay != null);
  if (!cells.length) return <div className="empty">No H3 delay data yet.</div>;

  const sorted = [...cells].sort((a, b) => b.mean_delay - a.mean_delay);
  const top = sorted.slice(0, 5);
  const bottom = sorted.slice(-5).reverse();

  return (
    <>
      <div className="section-label">
        Resolution {res} · {RES_LABEL[res] || ""} · {cells.length} hexes
      </div>
      <div className="section-label">Most delayed areas</div>
      {top.map((c) => <CellRow key={c.h3_index} c={c} onFocus={onFocus} bad />)}
      <div className="section-label">Most ahead-of-schedule</div>
      {bottom.map((c) => <CellRow key={c.h3_index} c={c} onFocus={onFocus} />)}
    </>
  );
}

function CellRow({ c, onFocus, bad }) {
  return (
    <div className="row" style={{ cursor: "pointer" }}
      onClick={() => c.center && onFocus?.(c.center[0], c.center[1])}>
      <div className="meta">
        <div className="t" style={{ fontFamily: "monospace" }}>{c.h3_index}</div>
        <div className="s">{c.total_trips} trips</div>
      </div>
      <span className="val" style={{ color: bad ? "var(--bad)" : "var(--good)" }}>{fmtDelay(c.mean_delay)}</span>
    </div>
  );
}
