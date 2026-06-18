import { useEffect, useRef } from "react";

function fmt(ts) {
  return new Date(ts * 1000).toLocaleTimeString();
}

export default function LogStream({ logs }) {
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="logs">
      {logs.length === 0 && <div className="muted pad">No activity yet.</div>}
      {logs.map((l) => (
        <div key={l.id} className={`log-line ${l.level}`}>
          <span className="log-ts">{fmt(l.ts)}</span>
          <span className="log-badge">{l.level}</span>
          <span className="log-text">{l.text}</span>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
