"use client";
import { useEffect, useState } from "react";

const PRIORITY_COLOR = {
  CRITICAL: "#ef4444",
  HIGH:     "#f97316",
  MEDIUM:   "#eab308",
  LOW:      "#22c55e",
};

export default function StudyPlanPage() {
  const [plan, setPlan] = useState([]);
  const [totalMinutes, setTotalMinutes] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchPlan() {
      try {
        const res = await fetch("/api/nexus/planner/plan/", {
          headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to load plan");
        setPlan(data.plan || []);
        setTotalMinutes(data.total_minutes || 0);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchPlan();
  }, []);

  if (loading) return <div className="plan-loading">Building your study plan...</div>;
  if (error)   return <div className="plan-error">{error}</div>;

  const hours   = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  return (
    <div className="plan-page">
      <div className="plan-header">
        <h1>Your Prioritised Study Plan</h1>
        <p>
          Sorted by Learning Debt — highest-impact topics first.
          Total estimated time: <strong>{hours > 0 ? `${hours}h ` : ""}{minutes}m</strong>
        </p>
      </div>

      {plan.length === 0 ? (
        <div className="plan-empty">
          <p>No study plan yet. Complete a diagnostic quiz to generate your plan.</p>
          <a href="/quiz" className="btn-primary">Start Diagnostic Quiz</a>
        </div>
      ) : (
        <div className="plan-list">
          {plan.map((item, idx) => (
            <PlanItem key={item.topic_id} rank={idx + 1} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function PlanItem({ rank, item }) {
  const color = PRIORITY_COLOR[item.priority] || "#64748b";
  const masteryPct = item.current_mastery ?? 0;

  return (
    <div className="plan-item">
      <div className="plan-rank">{rank}</div>

      <div className="plan-body">
        <div className="plan-top">
          <h3 className="plan-topic">{item.topic_id.replace(/_/g, " ")}</h3>
          <span className="plan-priority" style={{ background: color }}>
            {item.priority}
          </span>
        </div>

        {/* Mastery progress bar */}
        <div className="plan-mastery-wrap">
          <div className="plan-mastery-bar">
            <div
              className="plan-mastery-fill"
              style={{ width: `${masteryPct}%`, background: color }}
            />
            <div className="plan-threshold" title="Required: 70%" />
          </div>
          <span className="plan-mastery-label">{masteryPct.toFixed(0)}% / 70% required</span>
        </div>

        <div className="plan-meta">
          <span>Gap: <strong>{item.debt.toFixed(0)} pts</strong></span>
          <span>Est. time: <strong>{item.estimated_minutes} min</strong></span>
          <a
            href={`/nexus/tutor?topic_id=${encodeURIComponent(item.topic_id)}`}
            className="plan-study-btn"
          >
            Study this →
          </a>
        </div>
      </div>
    </div>
  );
}
