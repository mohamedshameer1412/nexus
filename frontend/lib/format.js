// Formatting shared by every screen: percentages, dates, and the words used for mastery states.

export const pct = (x, digits = 0) => (x == null || Number.isNaN(x) ? "–" : `${Number(x).toFixed(digits)}%`);   // x is already 0..100
export const pct01 = (x, digits = 0) => (x == null ? "–" : `${(x * 100).toFixed(digits)}%`);
export const ratio = (c, n) => (n ? Math.round((100 * c) / n) : null);
export const num = (x, digits = 0) => (x == null ? "–" : Number(x).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 }));
export const signed = (x, digits = 2) => (x == null ? "–" : `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(digits)}`);

export function shortDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}
export function dateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
export function relTime(iso) {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  if (s < 86400 * 7) return `${Math.round(s / 86400)} d ago`;
  return shortDate(iso);
}
export function bytes(n) {
  if (n == null) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1048576).toFixed(1)} MB`;
}

/** IRT labels from the backend → the words the student sees, and their colour tone. */
export const MASTERY = {
  confident: { label: "Strong", tone: "strong" },
  building: { label: "Getting there", tone: "mid" },
  shaky: { label: "Needs work", tone: "weak" },
  few: { label: "Too few answers", tone: "muted" },
  untried: { label: "Not tried", tone: "muted" },
};
export const masteryOf = (label) => MASTERY[label] ?? { label: label ?? "–", tone: "muted" };

/** Roadmap gap status → words and tone. */
export const GAP = {
  critical: { label: "Critical", tone: "weak" },
  moderate: { label: "Moderate", tone: "mid" },
  minor: { label: "Minor", tone: "neutral" },
  on_track: { label: "On track", tone: "strong" },
  unassessed: { label: "Not assessed", tone: "muted" },
};
export const gapOf = (s) => GAP[s] ?? { label: s, tone: "muted" };

export const RISK = { high: { label: "High", tone: "weak" }, medium: { label: "Medium", tone: "mid" }, low: { label: "Low", tone: "strong" }, unknown: { label: "Unknown", tone: "muted" } };

/** Colour for a 0..1 confidence against a target (default 0.7). */
export function confTone(c, target = 0.7) {
  if (c == null) return "muted";
  if (c >= target) return "strong";
  if (c >= target * 0.65) return "mid";
  return "weak";
}
export const TONE_HEX = { strong: "#0E8A5F", mid: "#D08700", weak: "#D9463B", muted: "#9AAABB", brand: "#0194E2", neutral: "#0194E2" };
export const CHART = ["#0194E2", "#0E9F8E", "#F2A516", "#7C5CFA", "#E5484D", "#64748B"];
