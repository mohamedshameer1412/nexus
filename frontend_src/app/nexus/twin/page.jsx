"use client";
import { useEffect, useState } from "react";
import MasteryHeatmap from "@/components/nexus/MasteryHeatmap";
import DebtBarChart from "@/components/nexus/DebtBarChart";
import ConfidenceGapChart from "@/components/nexus/ConfidenceGapChart";
import AgentLogFeed from "@/components/nexus/AgentLogFeed";

export default function DigitalTwinDashboard() {
  const [twin, setTwin] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTwin() {
      try {
        const [twinRes, logsRes] = await Promise.all([
          fetch("/api/nexus/twin/",      { headers: authHeaders() }),
          fetch("/api/nexus/twin/logs/", { headers: authHeaders() }),
        ]);
        setTwin(await twinRes.json());
        setLogs(await logsRes.json());
      } catch (e) {
        console.error("Failed to load Digital Twin:", e);
      } finally {
        setLoading(false);
      }
    }
    fetchTwin();
  }, []);

  if (loading) return <TwinSkeleton />;
  if (!twin)   return <div className="twin-error">Could not load your Digital Twin.</div>;

  return (
    <div className="twin-dashboard">
      {/* ── Header ── */}
      <div className="twin-header">
        <div className="twin-id">
          <h1>Your Learner Digital Twin</h1>
          <p className="twin-sub">
            Every number here is verified — earned through your actual quiz performance,
            not what you told the system.
          </p>
        </div>
        <div className="twin-scores">
          <ScorePill label="Learning Debt"     value={twin.learning_debt_score}  color="red"    />
          <ScorePill label="Failure Risk"      value={twin.failure_risk_score}   color="orange" />
          <ScorePill label="Concept Drift"     value={twin.concept_drift_score}  color="purple" />
        </div>
      </div>

      {/* ── Mastery Heatmap ── */}
      <section className="twin-section">
        <h2>Verified Mastery by Topic</h2>
        <p className="section-sub">
          Green = you can demonstrate this. Red = unverified or below threshold.
        </p>
        <MasteryHeatmap mastery={twin.verified_mastery} />
      </section>

      {/* ── Learning Debt ── */}
      <section className="twin-section">
        <h2>Learning Debt Score: {twin.learning_debt_score.toFixed(1)} / 100</h2>
        <p className="section-sub">
          Higher debt = more concepts below required level, weighted by how many
          other topics depend on them (Propagation Factor).
        </p>
        <DebtBarChart mastery={twin.verified_mastery} />
      </section>

      {/* ── Confidence-Ability Gap ── */}
      <section className="twin-section">
        <h2>Confidence-Ability Gap</h2>
        <p className="section-sub">
          How far your <em>self-belief</em> diverges from your <em>actual performance</em>.
          Positive = overconfident. Negative = underconfident.
        </p>
        <ConfidenceGapChart gap={twin.confidence_gap} />
      </section>

      {/* ── Agent Decision Log ── */}
      <section className="twin-section">
        <h2>Recent Agent Decisions</h2>
        <p className="section-sub">Every action NEXUS took — and why.</p>
        <AgentLogFeed logs={logs} />
      </section>
    </div>
  );
}

function ScorePill({ label, value, color }) {
  return (
    <div className={`score-pill score-pill--${color}`}>
      <span className="pill-value">{typeof value === "number" ? value.toFixed(1) : "--"}</span>
      <span className="pill-label">{label}</span>
    </div>
  );
}

function TwinSkeleton() {
  return (
    <div className="twin-dashboard twin-skeleton">
      <div className="skeleton-header" />
      <div className="skeleton-section" />
      <div className="skeleton-section" />
    </div>
  );
}

function authHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}
