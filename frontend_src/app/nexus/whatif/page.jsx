"use client";
import { useState } from "react";

export default function WhatIfPage() {
  const [topicA, setTopicA] = useState("");
  const [topicB, setTopicB] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function simulate() {
    if (!topicA.trim() || !topicB.trim()) {
      setError("Enter both topics"); return;
    }
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await fetch("/api/nexus/planner/whatif/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({ topic_a: topicA, topic_b: topicB }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="whatif-page">
      <div className="whatif-header">
        <h1>What-If Learning Simulator</h1>
        <p>
          Compare two study options. NEXUS evaluates both against your Digital Twin
          and tells you which gives higher expected improvement — and why.
        </p>
      </div>

      <div className="whatif-inputs">
        <div className="topic-input">
          <label>Topic A</label>
          <input value={topicA} onChange={e => setTopicA(e.target.value)} placeholder="e.g. recursion" />
        </div>
        <div className="vs-label">VS</div>
        <div className="topic-input">
          <label>Topic B</label>
          <input value={topicB} onChange={e => setTopicB(e.target.value)} placeholder="e.g. graph_traversal" />
        </div>
      </div>

      {error && <p className="whatif-error">{error}</p>}

      <button className="btn-simulate" onClick={simulate} disabled={loading}>
        {loading ? "Simulating..." : "Compare"}
      </button>

      {result && <WhatIfResult result={result} />}
    </div>
  );
}

function WhatIfResult({ result }) {
  const { topic_a, topic_b, recommendation, recommended_topic, reason } = result;
  return (
    <div className="whatif-result">
      <div className="result-recommendation">
        <span className="rec-label">NEXUS recommends:</span>
        <span className="rec-topic">{recommended_topic}</span>
      </div>
      <p className="rec-reason">{reason}</p>

      <div className="comparison-grid">
        <TopicCard data={topic_a} isWinner={recommendation === "A"} />
        <TopicCard data={topic_b} isWinner={recommendation === "B"} />
      </div>
    </div>
  );
}

function TopicCard({ data, isWinner }) {
  return (
    <div className={`topic-card ${isWinner ? "topic-card--winner" : ""}`}>
      {isWinner && <div className="winner-badge">Recommended</div>}
      <h3>{data.id}</h3>
      <div className="metric"><span>Current Mastery</span><strong>{data.mastery.toFixed(1)}%</strong></div>
      <div className="metric"><span>Gap from required</span><strong>{data.gap.toFixed(1)} pts</strong></div>
      <div className="metric"><span>Value Score</span><strong>{data.value_score.toFixed(1)}</strong></div>
    </div>
  );
}
