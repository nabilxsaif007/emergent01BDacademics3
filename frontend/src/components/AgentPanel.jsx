import { useState } from "react";
import StatusDot from "./StatusDot.jsx";
import LogStream from "./LogStream.jsx";
import Chat from "./Chat.jsx";
import Timeline from "./Timeline.jsx";

const shortModel = (m) => (m || "").replace("claude-", "").replace(/-\d+$/, "");
const money = (n) => "$" + (n || 0).toFixed(n >= 1 ? 2 : 4);
const compact = (n) => (n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(n || 0));

export default function AgentPanel({ agent, detail, onBack, onChat, onStop, onDelete }) {
  const busy = agent.status === "running" || agent.status === "queued";
  const [tab, setTab] = useState("activity"); // "activity" | "timeline"

  return (
    <div className="panel">
      <header className="panel-head">
        <div className="panel-title">
          <button className="btn back" onClick={onBack} title="Back to fleet">←</button>
          <StatusDot status={agent.status} />
          <div>
            <h2>{agent.name}</h2>
            <div className="muted">{agent.role} · {agent.status}</div>
          </div>
        </div>
        <div className="panel-actions">
          {busy && (
            <button className="btn" onClick={onStop}>Stop</button>
          )}
          <button className="btn danger" onClick={onDelete}>Delete</button>
        </div>
      </header>

      <div className="panel-metrics">
        <Metric label="Model" value={shortModel(agent.model)} />
        <Metric label="Tokens" value={compact((agent.tokens_in || 0) + (agent.tokens_out || 0))} />
        <Metric label="Cost" value={money(agent.cost_usd)} />
        <Metric label="Tasks done" value={agent.tasks_done || 0} />
      </div>

      {busy && (
        <div className="progress">
          <span style={{ width: `${agent.progress}%` }} />
        </div>
      )}

      <div className="panel-body">
        <section className="col chat-col">
          <h3 className="col-title">Chat</h3>
          <Chat
            messages={detail?.messages || []}
            disabled={busy}
            onSend={onChat}
          />
        </section>
        <section className="col log-col">
          <div className="col-tabs">
            <button className={tab === "activity" ? "active" : ""} onClick={() => setTab("activity")}>
              Activity
            </button>
            <button className={tab === "timeline" ? "active" : ""} onClick={() => setTab("timeline")}>
              Timeline
            </button>
          </div>
          {tab === "activity"
            ? <LogStream logs={detail?.logs || []} />
            : <Timeline logs={detail?.logs || []} />}
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
