import { useCallback, useEffect, useRef, useState } from "react";

export default function HourSlider({ hour, onChange }) {
  const [local, setLocal] = useState(hour === null ? -1 : hour);
  const timer = useRef(null);

  useEffect(() => {
    setLocal(hour === null ? -1 : hour);
  }, [hour]);

  const handleChange = useCallback(
    (e) => {
      const v = parseInt(e.target.value, 10);
      setLocal(v);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => onChange(v === -1 ? null : v), 150);
    },
    [onChange],
  );

  return (
    <div className="hour-slider glass">
      <div className="hour-slider-head">
        <span>Hour</span>
        <span className="hour-slider-val">{local === -1 ? "All day" : fmtHour(local)}</span>
      </div>
      <input type="range" min={-1} max={23} step={1} value={local} onChange={handleChange} />
    </div>
  );
}

function fmtHour(h) {
  if (h === 0) return "12 am";
  if (h < 12) return `${h} am`;
  if (h === 12) return "12 pm";
  return `${h - 12} pm`;
}
