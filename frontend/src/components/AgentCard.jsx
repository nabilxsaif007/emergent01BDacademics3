import { useState } from "react";
import StatusDot from "./StatusDot.jsx";

const shortModel = (m) => (m || "").replace("claude-", "").replace(/-\d+$/, "");
const money = (n) => "$" + (n || 0).toFixed(n >= 1 ? 2 : 4);
const compact = (n) => (n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(n || 0));

// A live tile in the fleet grid: status, current task, last activity, usage,
// and an inline box to dispatch a task without leaving the overview.
export default function AgentCard({ agent, onOpen, onDeploy, onStop }) {
  const [text, setText] = useState("");
  const busy = agent.status === "running" || agent.status === "queued";
  const stalled = busy && Date.now() / 1000 - (agent.last_beat || 0) > 30;

  const dispatch = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    onDeploy(t);
    setText("");
  };

  return (
    <div className={`card ${busy ? "busy" : ""}`}>
      <div className="card-head" onClick={onOpen} role="button">
        <StatusDot status={agent.status} />
        <div className="card-id">
          <div className="card-name">{agent.name}</div>
          <div className="card-role">{agent.role}</div>
        </div>
        <span className={`pill ${agent.status}`}>{agent.status}</span>
      </div>

      {busy && (
        <div className="progress thin">
          <span style={{ width: `${agent.progress}%` }} />
        </div>
      )}

      <div className="card-task" onClick={onOpen} role="button">
        {agent.task ? (
          <>
            <div className="card-label">Task</div>
            <div className="card-task-text">{agent.task}</div>
          </>
        ) : (
          <div className="muted card-task-text">No task yet — give it one below.</div>
        )}
      </div>

      <div className="card-activity" onClick={onOpen} role="button">
        <span className={`dot-tick ${stalled ? "stalled" : ""}`} />
        {agent.last_activity || "idle"}
      </div>

      <div className="card-meta" onClick={onOpen} role="button">
        <span className="meta-model">{shortModel(agent.model)}</span>
        <span className="meta-sep">·</span>
        <span title="tokens">{compact((agent.tokens_in || 0) + (agent.tokens_out || 0))} tok</span>
        <span className="meta-sep">·</span>
        <span title="cost">{money(agent.cost_usd)}</span>
        {agent.tasks_done > 0 && (
          <span className="meta-tasks">{agent.tasks_done} done</span>
        )}
      </div>

      {busy ? (
        <button className="btn block" onClick={onStop}>Stop</button>
      ) : (
        <form className="card-dispatch" onSubmit={dispatch}>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Dispatch a task…"
          />
          <button className="btn primary" disabled={!text.trim()}>Go</button>
        </form>
      )}
    </div>
  );
}
