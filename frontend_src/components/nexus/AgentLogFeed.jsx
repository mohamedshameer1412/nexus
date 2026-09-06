"use client";
const AGENT_COLORS = {
  analytics:  "#6366f1",
  evaluator:  "#ef4444",
  planner:    "#10b981",
  tutor:      "#3b82f6",
  content:    "#f59e0b",
  mentor:     "#8b5cf6",
};

export default function AgentLogFeed({ logs = [] }) {
  if (!logs.length)
    return <p className="empty-state">No agent decisions yet. Complete a quiz session to see agent activity.</p>;

  return (
    <div className="agent-log-feed">
      {logs.map((log) => (
        <div key={log.id} className="log-entry">
          <div
            className="log-agent-badge"
            style={{ background: AGENT_COLORS[log.agent_name] || "#64748b" }}
          >
            {log.agent_name}
          </div>
          <div className="log-body">
            <p className="log-decision">{log.decision}</p>
            <span className="log-time">
              {new Date(log.timestamp).toLocaleString("en-IN")}
            </span>
          </div>
          {log.verified !== null && (
            <div className={`log-verified ${log.verified ? "verified--yes" : "verified--no"}`}>
              {log.verified ? "✓ Worked" : "✗ Needs review"}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
