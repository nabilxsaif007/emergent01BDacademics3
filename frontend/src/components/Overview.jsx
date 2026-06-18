import AgentCard from "./AgentCard.jsx";
import CostPanel from "./CostPanel.jsx";
import LiveFeed from "./LiveFeed.jsx";
import AlertsBanner from "./AlertsBanner.jsx";

export default function Overview({ agents, feed, metrics, onOpen, onDeploy, onStop, onNew }) {
  const running = agents.filter((a) => a.status === "running" || a.status === "queued").length;
  const done = agents.filter((a) => a.status === "completed").length;
  const failed = agents.filter((a) => a.status === "failed").length;

  return (
    <div className="overview">
      <header className="overview-head">
        <div>
          <h1>Fleet Overview</h1>
          <p className="muted">Every agent, live. Dispatch a task to any of them right here.</p>
        </div>
        <button className="btn primary" onClick={onNew}>+ New agent</button>
      </header>

      <AlertsBanner agents={agents} metrics={metrics} onOpenAgent={onOpen} />

      <div className="stat-strip">
        <Stat label="Agents" value={agents.length} />
        <Stat label="Working" value={running} tone="accent" />
        <Stat label="Completed" value={done} tone="green" />
        <Stat label="Failed" value={failed} tone="danger" />
      </div>

      <div className="ov-layout">
        <div className="ov-main">
          <CostPanel metrics={metrics} />

          {agents.length === 0 ? (
            <div className="empty">
              <h2>No agents deployed</h2>
              <p>Create your first agent to start dispatching tasks.</p>
              <button className="btn primary" onClick={onNew}>+ Deploy your first agent</button>
            </div>
          ) : (
            <div className="grid">
              {agents.map((a) => (
                <AgentCard
                  key={a.id}
                  agent={a}
                  onOpen={() => onOpen(a.id)}
                  onDeploy={(text) => onDeploy(a.id, text)}
                  onStop={() => onStop(a.id)}
                />
              ))}
            </div>
          )}
        </div>

        <aside className="ov-rail">
          <LiveFeed feed={feed} onOpenAgent={onOpen} />
        </aside>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="stat">
      <div className={`stat-value ${tone || ""}`}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
