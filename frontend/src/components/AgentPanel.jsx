import StatusDot from "./StatusDot.jsx";
import LogStream from "./LogStream.jsx";
import Chat from "./Chat.jsx";

export default function AgentPanel({ agent, detail, onBack, onChat, onStop, onDelete }) {
  const busy = agent.status === "running" || agent.status === "queued";

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
          <h3 className="col-title">Activity</h3>
          <LogStream logs={detail?.logs || []} />
        </section>
      </div>
    </div>
  );
}
