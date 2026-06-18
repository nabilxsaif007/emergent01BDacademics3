import { useEffect, useRef, useState } from "react";

export default function Chat({ messages, disabled, onSend }) {
  const [text, setText] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const submit = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
  };

  return (
    <div className="chat">
      <div className="chat-log">
        {messages.length === 0 && (
          <div className="muted pad">Send a prompt to put this agent to work.</div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.role}`}>
            <div className="bubble-role">{m.role}</div>
            <div className="bubble-text">{m.content}</div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form className="chat-input" onSubmit={submit}>
        <textarea
          rows={2}
          placeholder={disabled ? "Agent is working…" : "Prompt or paste code… (Enter to send)"}
          value={text}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }}
        />
        <button className="btn primary" disabled={disabled || !text.trim()}>Send</button>
      </form>
    </div>
  );
}
