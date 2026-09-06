"use client";
/**
 * DebtBarChart
 * Horizontal bar per topic — bar length = gap from 70% threshold.
 * Topics with no gap are hidden.
 */
export default function DebtBarChart({ mastery = {} }) {
  const REQUIRED = 70;
  const debtTopics = Object.entries(mastery)
    .map(([id, pct]) => ({ id, pct, debt: Math.max(0, REQUIRED - pct) }))
    .filter(t => t.debt > 0)
    .sort((a, b) => b.debt - a.debt)
    .slice(0, 10); // top 10 worst

  if (!debtTopics.length)
    return <p className="empty-state">No learning debt detected. All topics above threshold.</p>;

  return (
    <div className="debt-chart">
      {debtTopics.map(({ id, pct, debt }) => (
        <div key={id} className="debt-row">
          <span className="debt-label">{id.replace(/_/g, " ")}</span>
          <div className="debt-bar-wrap">
            <div
              className="debt-bar"
              style={{ width: `${(debt / REQUIRED) * 100}%` }}
            />
          </div>
          <span className="debt-val">{debt.toFixed(0)} pts below</span>
        </div>
      ))}
    </div>
  );
}
