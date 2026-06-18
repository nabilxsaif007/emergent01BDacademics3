import { useEffect, useState } from "react";
import { useAgents } from "./lib/useAgents.js";
import Sidebar from "./components/Sidebar.jsx";
import AgentPanel from "./components/AgentPanel.jsx";
import CreateAgentModal from "./components/CreateAgentModal.jsx";

export default function App() {
  const store = useAgents();
  const [selectedId, setSelectedId] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const selected = store.agents.find((a) => a.id === selectedId) || null;

  // Load logs/chat the first time an agent is opened.
  useEffect(() => {
    if (selectedId && !store.detail[selectedId]) store.loadDetail(selectedId);
  }, [selectedId, store]);

  // Auto-select the first agent once we have any.
  useEffect(() => {
    if (!selectedId && store.agents.length) setSelectedId(store.agents[0].id);
  }, [store.agents, selectedId]);

  return (
    <div className="app">
      <Sidebar
        agents={store.agents}
        connected={store.connected}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onNew={() => setShowCreate(true)}
      />
      <main className="main">
        {selected ? (
          <AgentPanel
            agent={selected}
            detail={store.detail[selected.id]}
            onChat={(text) => store.sendChat(selected.id, text)}
            onStop={() => store.stopAgent(selected.id)}
            onDelete={async () => {
              await store.deleteAgent(selected.id);
              setSelectedId(null);
            }}
          />
        ) : (
          <div className="empty">
            <h2>No agent selected</h2>
            <p>Create an agent to deploy it, then chat to put it to work.</p>
            <button className="btn primary" onClick={() => setShowCreate(true)}>
              + Deploy your first agent
            </button>
          </div>
        )}
      </main>

      {showCreate && (
        <CreateAgentModal
          onClose={() => setShowCreate(false)}
          onCreate={async (name, role) => {
            const a = await store.createAgent(name, role);
            setShowCreate(false);
            setSelectedId(a.id);
          }}
        />
      )}
    </div>
  );
}
