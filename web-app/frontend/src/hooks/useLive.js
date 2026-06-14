import { useEffect, useRef, useState } from "react";
import { openLiveSocket } from "../api.js";

// Opens a live WebSocket for `city` while `active`. Exposes the latest snapshot
// and connection status. Reconnects automatically if the socket drops.
export function useLive(city, active) {
  const [snapshot, setSnapshot] = useState(null);
  const [status, setStatus] = useState("idle");
  const wsRef = useRef(null);
  const retryRef = useRef(null);

  useEffect(() => {
    if (!active || !city) {
      wsRef.current?.close();
      setStatus("idle");
      return;
    }

    let closed = false;
    const connect = () => {
      const ws = openLiveSocket(city, setSnapshot, (s) => {
        setStatus(s);
        if ((s === "closed" || s === "error") && !closed) {
          clearTimeout(retryRef.current);
          retryRef.current = setTimeout(connect, 3000); // auto-reconnect
        }
      });
      wsRef.current = ws;
    };
    connect();

    return () => {
      closed = true;
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [city, active]);

  return { snapshot, status };
}
