import { useState } from "react";
import StatusDot from "./StatusDot.jsx";

// A live tile in the fleet grid: status, current task, last activity, and an
// inline box to dispatch a task without leaving the overview.
export default function AgentCard({ agent, onOpen, onDeploy, onStop }) {
  const [text, setText] = useState("");
  const busy = agent.status === "running" || agent.status === "queued";

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
        <span className="dot-tick" />
        {agent.last_activity || "idle"}
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
