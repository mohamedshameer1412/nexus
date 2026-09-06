"use client";
/**
 * MasteryHeatmap
 * Renders each topic as a colored cell.
 * Green >= 70%, Yellow 40-69%, Red < 40%
 */
export default function MasteryHeatmap({ mastery = {} }) {
  const topics = Object.entries(mastery);
  if (!topics.length) return <p className="empty-state">No mastery data yet. Complete a quiz to see your scores.</p>;

  return (
    <div className="heatmap-grid">
      {topics.map(([topicId, pct]) => (
        <div
          key={topicId}
          className={`heatmap-cell ${masteryClass(pct)}`}
          title={`${topicId}: ${pct}%`}
        >
          <span className="cell-topic">{topicId.replace(/_/g, " ")}</span>
          <span className="cell-pct">{pct.toFixed(0)}%</span>
        </div>
      ))}
    </div>
  );
}

function masteryClass(pct) {
  if (pct >= 70) return "mastery--high";
  if (pct >= 40) return "mastery--mid";
  return "mastery--low";
}
