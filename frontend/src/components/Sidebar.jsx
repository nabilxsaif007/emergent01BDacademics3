import StatusDot from "./StatusDot.jsx";

export default function Sidebar({ agents, connected, selectedId, onSelect, onNew }) {
  const running = agents.filter((a) => a.status === "running").length;

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="logo">◆</span>
        <div>
          <div className="brand-name">Control Panel</div>
          <div className={`conn ${connected ? "on" : "off"}`}>
            {connected ? "live" : "offline"}
          </div>
        </div>
      </div>

      <div className="sidebar-stats">
        <div><strong>{agents.length}</strong> agents</div>
        <div><strong>{running}</strong> running</div>
      </div>

      <button className="btn primary block" onClick={onNew}>+ New agent</button>

      <div className="agent-list">
        {agents.length === 0 && <div className="muted pad">No agents yet.</div>}
        {agents.map((a) => (
          <button
            key={a.id}
            className={`agent-row ${a.id === selectedId ? "active" : ""}`}
            onClick={() => onSelect(a.id)}
          >
            <StatusDot status={a.status} />
            <div className="agent-row-body">
              <div className="agent-row-name">{a.name}</div>
              <div className="agent-row-sub">{a.role} · {a.status}</div>
            </div>
            {a.status === "running" && (
              <div className="mini-bar"><span style={{ width: `${a.progress}%` }} /></div>
            )}
          </button>
        ))}
      </div>
    </aside>
  );
}
