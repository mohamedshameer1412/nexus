"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

export default function TutorSessionPage() {
  const params  = useSearchParams();
  const topicId = params.get("topic_id") || "";
  const [session, setSession]   = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");
  const [activeCard, setActiveCard] = useState(0);

  useEffect(() => {
    async function fetchSession() {
      setLoading(true);
      try {
        const url = topicId
          ? `/api/nexus/tutor/session/?topic_id=${encodeURIComponent(topicId)}`
          : "/api/nexus/tutor/session/";
        const res  = await fetch(url, {
          headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to load session");
        setSession(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchSession();
  }, [topicId]);

  if (loading) return <div className="tutor-loading">Loading content for "{topicId || "top priority topic"}"...</div>;
  if (error)   return <div className="tutor-error">{error}</div>;
  if (!session) return null;

  const { content_cards, twin_debt } = session;
  const topic = session.topic_id;

  return (
    <div className="tutor-page">
      <div className="tutor-header">
        <div>
          <h1>Tutor Session</h1>
          <p className="tutor-topic">
            Focus topic: <strong>{topic.replace(/_/g, " ")}</strong>
          </p>
        </div>
        <div className="tutor-debt-badge" title="Your current learning debt score">
          Debt: {twin_debt?.toFixed(1) ?? "--"}
        </div>
      </div>

      {/* Content cards carousel */}
      <div className="tutor-cards">
        <div className="card-nav">
          <button
            className="card-nav-btn"
            onClick={() => setActiveCard(i => Math.max(0, i - 1))}
            disabled={activeCard === 0}
          >
            ← Prev
          </button>
          <span className="card-counter">
            {activeCard + 1} / {content_cards.length}
          </span>
          <button
            className="card-nav-btn"
            onClick={() => setActiveCard(i => Math.min(content_cards.length - 1, i + 1))}
            disabled={activeCard === content_cards.length - 1}
          >
            Next →
          </button>
        </div>

        {content_cards[activeCard] && (
          <ContentCard card={content_cards[activeCard]} />
        )}
      </div>

      {/* Card thumbnails */}
      <div className="card-thumbs">
        {content_cards.map((card, idx) => (
          <button
            key={idx}
            className={`card-thumb ${idx === activeCard ? "card-thumb--active" : ""}`}
            onClick={() => setActiveCard(idx)}
          >
            {idx + 1}
          </button>
        ))}
      </div>

      <div className="tutor-actions">
        <a href="/nexus/plan" className="btn-secondary">Back to Study Plan</a>
        <a href={`/quiz?topic=${encodeURIComponent(topic)}`} className="btn-primary">
          Test yourself on this topic →
        </a>
      </div>
    </div>
  );
}

function ContentCard({ card }) {
  const relevancePct = Math.round(card.relevance * 100);
  return (
    <div className="content-card">
      <div className="content-card-header">
        <span className="card-topic-tag">{card.topic?.replace(/_/g, " ")}</span>
        <span
          className="card-relevance"
          title="How closely this content matches your focus topic"
        >
          {relevancePct}% match
        </span>
      </div>

      <div className="content-card-body">
        <p>{card.text}</p>
      </div>

      <div className="content-card-footer">
        <span className="card-source">Source: {card.source}</span>
      </div>
    </div>
  );
}
