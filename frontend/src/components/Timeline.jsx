// Execution timeline: the tool calls an agent made, with durations — a
// lightweight take on the "execution graph" view from the observability tools.

export default function Timeline({ logs }) {
  const steps = (logs || []).filter((l) => l.level === "tool");

  if (steps.length === 0) {
    return <div className="muted timeline-empty">No tool calls yet.</div>;
  }

  const maxDur = Math.max(...steps.map((s) => s.dur_ms || 0), 1);

  return (
    <div className="timeline">
      {steps.map((s, i) => {
        const name = s.tool || (s.text || "").split("(")[0];
        const arg = (s.text || "").slice((name || "").length).replace(/^\(|\)$/g, "");
        const dur = s.dur_ms || 0;
        return (
          <div className="tl-row" key={s.id || i}>
            <div className="tl-rail">
              <span className="tl-dot" />
              {i < steps.length - 1 && <span className="tl-line" />}
            </div>
            <div className="tl-body">
              <div className="tl-head">
                <span className="tl-name">{name}</span>
                {dur > 0 && <span className="tl-dur">{dur} ms</span>}
              </div>
              {arg && <div className="tl-arg">{arg}</div>}
              <div className="tl-bar">
                <span style={{ width: `${Math.max(6, (dur / maxDur) * 100)}%` }} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
