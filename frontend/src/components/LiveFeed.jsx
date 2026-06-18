const ICON = { status: "●", tool: "⚙", message: "✉", error: "✕" };

function ago(ts) {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

export default function LiveFeed({ feed, onOpenAgent }) {
  return (
    <div className="live-feed">
      <div className="rail-head">
        <span className="rail-title">Live activity</span>
        <span className="feed-count">{feed.length}</span>
      </div>
      <div className="feed-body">
        {feed.length === 0 ? (
          <div className="muted feed-empty">Nothing yet — dispatch a task to wake the fleet.</div>
        ) : (
          feed.map((e) => (
            <div className={`feed-row ${e.level}`} key={e.id}>
              <span className={`feed-icon ${e.level}`}>{ICON[e.kind] || "●"}</span>
              <div className="feed-main">
                <div className="feed-line">
                  <button className="feed-agent" onClick={() => onOpenAgent(e.agent_id)}>
                    {e.agent_name}
                  </button>
                  <span className="feed-text">{e.text}</span>
                </div>
              </div>
              <span className="feed-ago">{ago(e.ts)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
