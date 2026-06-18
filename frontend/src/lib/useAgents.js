import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";

// Central store: keeps the agent list in sync via WebSocket, and lazily loads
// per-agent logs + chat history. Returns everything App needs.
export function useAgents() {
  const [agents, setAgents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [detail, setDetail] = useState({}); // id -> { logs: [], messages: [] }
  const wsRef = useRef(null);

  const upsertAgent = useCallback((agent) => {
    setAgents((prev) => {
      const i = prev.findIndex((a) => a.id === agent.id);
      if (i === -1) return [...prev, agent];
      const next = [...prev];
      next[i] = agent;
      return next;
    });
  }, []);

  // --- WebSocket live feed ---
  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      switch (msg.type) {
        case "snapshot":
          setAgents(msg.agents);
          break;
        case "agent_created":
        case "agent_updated":
          upsertAgent(msg.agent);
          break;
        case "agent_deleted":
          setAgents((prev) => prev.filter((a) => a.id !== msg.agent_id));
          break;
        case "log":
          setDetail((prev) => {
            const d = prev[msg.agent_id];
            if (!d) return prev; // not loaded yet; will fetch on open
            return { ...prev, [msg.agent_id]: { ...d, logs: [...d.logs, msg.line] } };
          });
          break;
        case "message":
          setDetail((prev) => {
            const d = prev[msg.agent_id];
            if (!d) return prev;
            return { ...prev, [msg.agent_id]: { ...d, messages: [...d.messages, msg.message] } };
          });
          break;
        default:
          break;
      }
    };
    return () => ws.close();
  }, [upsertAgent]);

  const loadDetail = useCallback(async (id) => {
    const data = await api.getAgent(id);
    setDetail((prev) => ({ ...prev, [id]: { logs: data.logs, messages: data.messages } }));
  }, []);

  const createAgent = useCallback((name, role) => api.createAgent(name, role), []);
  const deleteAgent = useCallback((id) => api.deleteAgent(id), []);
  const sendChat = useCallback((id, content) => api.chat(id, content), []);
  const stopAgent = useCallback((id) => api.stop(id), []);

  return {
    agents,
    connected,
    detail,
    loadDetail,
    createAgent,
    deleteAgent,
    sendChat,
    stopAgent,
  };
}
