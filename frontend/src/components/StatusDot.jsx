const COLORS = {
  idle: "#7a869a",
  queued: "#d9a441",
  running: "#3ea6ff",
  completed: "#3fb950",
  failed: "#f85149",
  stopped: "#7a869a",
};

export default function StatusDot({ status }) {
  return (
    <span
      className={`status-dot ${status === "running" ? "pulse" : ""}`}
      style={{ background: COLORS[status] || "#7a869a" }}
      title={status}
    />
  );
}
