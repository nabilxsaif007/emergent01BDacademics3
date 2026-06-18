import { useEffect, useState } from "react";
import { useAgents } from "./lib/useAgents.js";
import Sidebar from "./components/Sidebar.jsx";
import Overview from "./components/Overview.jsx";
import AgentPanel from "./components/AgentPanel.jsx";
import CreateAgentModal from "./components/CreateAgentModal.jsx";

export default function App() {
  const store = useAgents();
  const [view, setView] = useState("overview"); // "overview" | "detail"
  const [selectedId, setSelectedId] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const selected = store.agents.find((a) => a.id === selectedId) || null;

  const openAgent = (id) => {
    setSelectedId(id);
    setView("detail");
  };
  const goOverview = () => {
    setView("overview");
    setSelectedId(null);
  };

  // Load logs/chat the first time an agent's detail is opened.
  useEffect(() => {
    if (view === "detail" && selectedId && !store.detail[selectedId]) {
      store.loadDetail(selectedId);
    }
  }, [view, selectedId, store]);

  return (
    <div className="app">
      <Sidebar
        agents={store.agents}
        connected={store.connected}
        view={view}
        selectedId={selectedId}
        onOverview={goOverview}
        onSelect={openAgent}
        onNew={() => setShowCreate(true)}
      />

      <main className="main">
        {view === "overview" || !selected ? (
          <Overview
            agents={store.agents}
            onOpen={openAgent}
            onDeploy={(id, text) => store.sendChat(id, text)}
            onStop={(id) => store.stopAgent(id)}
            onNew={() => setShowCreate(true)}
          />
        ) : (
          <AgentPanel
            agent={selected}
            detail={store.detail[selected.id]}
            onBack={goOverview}
            onChat={(text) => store.sendChat(selected.id, text)}
            onStop={() => store.stopAgent(selected.id)}
            onDelete={async () => {
              await store.deleteAgent(selected.id);
              goOverview();
            }}
          />
        )}
      </main>

      {showCreate && (
        <CreateAgentModal
          onClose={() => setShowCreate(false)}
          onCreate={async (name, role) => {
            const a = await store.createAgent(name, role);
            setShowCreate(false);
            openAgent(a.id);
          }}
        />
      )}
    </div>
  );
}
