"use client";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

const AGENTS = [
  { id: "analytics",  label: "Analytics Agent",  desc: "Updating your Digital Twin with session results" },
  { id: "evaluator",  label: "Evaluator Agent",  desc: "Finding root causes of concept failures" },
  { id: "planner",    label: "Planner Agent",    desc: "Rebuilding your prioritized study plan" },
  { id: "tutor",      label: "Tutor Agent",      desc: "Preparing next session content" },
];

export default function AnalyzingPage() {
  const params = useSearchParams();
  const sessionId = params.get("session_id");
  const taskIds   = JSON.parse(params.get("task_ids") || "{}");

  const [agentStatus, setAgentStatus] = useState(
    Object.fromEntries(AGENTS.map(a => [a.id, "waiting"]))
  );
  const [pipelineDone, setPipelineDone] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!sessionId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/nexus/agents/${sessionId}/`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ task_ids: taskIds }));
    };

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);

      if (msg.type === "pipeline_start") {
        setAgentStatus(prev => {
          const next = { ...prev };
          msg.agents.forEach(a => { next[a] = "running"; });
          return next;
        });
      }

      if (msg.type === "agent_complete" || msg.type === "agent_timeout") {
        setAgentStatus(prev => ({
          ...prev,
          [msg.agent]: msg.status,
        }));
      }

      if (msg.type === "pipeline_complete") {
        setPipelineDone(true);
        ws.close();
      }
    };

    return () => ws.close();
  }, [sessionId]);

  return (
    <div className="analyze-page">
      <div className="analyze-header">
        <h1>NEXUS is analyzing your session</h1>
        <p>6 agents are working in parallel. Each will complete in under 4 seconds.</p>
      </div>

      <div className="agent-grid">
        {AGENTS.map(agent => (
          <AgentCard
            key={agent.id}
            agent={agent}
            status={agentStatus[agent.id] || "waiting"}
          />
        ))}
      </div>

      {pipelineDone && (
        <div className="analyze-complete">
          <h2>✓ Analysis complete</h2>
          <p>Your Digital Twin has been updated.</p>
          <a href="/nexus/twin" className="btn-primary">View Digital Twin</a>
          <a href="/nexus/plan" className="btn-secondary">See Study Plan</a>
        </div>
      )}
    </div>
  );
}

function AgentCard({ agent, status }) {
  const icons = { waiting: "⏳", running: "⚙️", done: "✅", failed: "❌", timeout: "⏱️" };
  const classes = { waiting: "card--waiting", running: "card--running", done: "card--done", failed: "card--failed", timeout: "card--timeout" };

  return (
    <div className={`agent-card ${classes[status] || ""}`}>
      <div className="agent-icon">{icons[status]}</div>
      <div className="agent-info">
        <h3>{agent.label}</h3>
        <p>{agent.desc}</p>
      </div>
      {status === "running" && <div className="agent-spinner" />}
    </div>
  );
}
