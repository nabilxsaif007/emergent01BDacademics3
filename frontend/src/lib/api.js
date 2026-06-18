// Thin REST client. Paths are proxied to the backend by Vite (see vite.config.js).

async function req(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.status === 204 ? null : res.json();
}

export const api = {
  listAgents: () => req("/api/agents"),
  createAgent: (name, role, model) =>
    req("/api/agents", { method: "POST", body: JSON.stringify({ name, role, model }) }),
  getAgent: (id) => req(`/api/agents/${id}`),
  deleteAgent: (id) => req(`/api/agents/${id}`, { method: "DELETE" }),
  chat: (id, content) =>
    req(`/api/agents/${id}/chat`, { method: "POST", body: JSON.stringify({ content }) }),
  stop: (id) => req(`/api/agents/${id}/stop`, { method: "POST" }),
};
