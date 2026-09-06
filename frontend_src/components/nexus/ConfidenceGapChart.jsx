"use client";
/**
 * ConfidenceGapChart
 * Shows per-topic gap: how far self-rating diverges from actual performance.
 * Positive = overconfident (red), Negative = underconfident (blue)
 */
export default function ConfidenceGapChart({ gap = {} }) {
  const entries = Object.entries(gap).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 10);
  if (!entries.length)
    return <p className="empty-state">Set your self-reported mastery to see your confidence gap.</p>;

  return (
    <div className="gap-chart">
      {entries.map(([topicId, gapVal]) => (
        <div key={topicId} className="gap-row">
          <span className="gap-label">{topicId.replace(/_/g, " ")}</span>
          <div className="gap-bar-wrap">
            <div className="gap-bar-center" />
            <div
              className={`gap-bar ${gapVal >= 0 ? "gap--over" : "gap--under"}`}
              style={{
                width: `${Math.min(Math.abs(gapVal), 100) / 2}%`,
                [gapVal >= 0 ? "left" : "right"]: "50%",
              }}
            />
          </div>
          <span className={`gap-val ${gapVal >= 0 ? "over" : "under"}`}>
            {gapVal >= 0 ? "+" : ""}{gapVal.toFixed(1)}
          </span>
        </div>
      ))}
      <div className="gap-legend">
        <span className="legend-over">Overconfident (+)</span>
        <span className="legend-under">Underconfident (-)</span>
      </div>
    </div>
  );
}
