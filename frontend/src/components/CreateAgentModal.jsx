import { useState } from "react";

const ROLES = ["general", "coder", "researcher", "writer", "ops"];
const MODELS = [
  ["claude-opus-4-8", "Opus 4.8 — most capable"],
  ["claude-sonnet-4-6", "Sonnet 4.6 — balanced"],
  ["claude-haiku-4-5", "Haiku 4.5 — fast & cheap"],
];

export default function CreateAgentModal({ onClose, onCreate }) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("general");
  const [model, setModel] = useState("claude-sonnet-4-6");

  const submit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    onCreate(name.trim(), role, model);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Deploy a new agent</h2>
        <form onSubmit={submit}>
          <label>
            Name
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Bugfixer"
            />
          </label>
          <label>
            Role
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </label>
          <label>
            Model
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              {MODELS.map(([id, label]) => (
                <option key={id} value={id}>{label}</option>
              ))}
            </select>
          </label>
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn primary" disabled={!name.trim()}>
              Deploy
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
