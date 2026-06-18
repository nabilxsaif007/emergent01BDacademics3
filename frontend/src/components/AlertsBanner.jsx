// Derives at-a-glance warnings from current state — the "alerts banner" pattern
// common to the monitoring dashboards. Pure function of agents + metrics.

const HIGH_SPEND = 5; // USD/day before we flag it

export default function AlertsBanner({ agents, metrics, onOpenAgent }) {
  const alerts = [];

  const failed = agents.filter((a) => a.status === "failed");
  if (failed.length) {
    alerts.push({
      tone: "danger",
      text: `${failed.length} agent${failed.length > 1 ? "s" : ""} failed`,
      agentId: failed[0].id,
    });
  }

  const offline = agents.filter(
    (a) => (a.status === "running" || a.status === "queued") &&
      Date.now() / 1000 - (a.last_beat || 0) > 30
  );
  if (offline.length) {
    alerts.push({
      tone: "warn",
      text: `${offline.length} agent${offline.length > 1 ? "s" : ""} stalled (no heartbeat)`,
      agentId: offline[0].id,
    });
  }

  const todayCost = metrics?.today?.cost || 0;
  if (todayCost > HIGH_SPEND) {
    alerts.push({ tone: "warn", text: `High spend today — $${todayCost.toFixed(2)}` });
  }

  if (alerts.length === 0) return null;

  return (
    <div className="alerts">
      {alerts.map((a, i) => (
        <button
          key={i}
          className={`alert ${a.tone}`}
          onClick={() => a.agentId && onOpenAgent(a.agentId)}
        >
          <span className="alert-icon">{a.tone === "danger" ? "✕" : "⚠"}</span>
          {a.text}
        </button>
      ))}
    </div>
  );
}
