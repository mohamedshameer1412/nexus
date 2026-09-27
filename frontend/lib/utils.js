import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...inputs) => twMerge(clsx(inputs));

export function pageLabel(start, end) {
  if (start == null) return "";
  return end == null || end === start ? `PDF p. ${start}` : `PDF pp. ${start}–${end}`;
}

export function friendlyError(error) {
  if (!error) return "";
  if (error.code === "network") return "Could not reach the server. Check your connection and try again.";
  return error.message || "Something went wrong. Please try again.";
}

/** Split text into pieces and mark the words that match a search term (same prefix rule as the backend). Pure data, no HTML. */
export function highlightParts(text, terms) {
  const keys = terms.map((t) => t.toLowerCase());
  const hit = (w) => {
    const l = w.toLowerCase();
    return keys.some((k) => l === k || (k.length >= 4 && l.startsWith(k.slice(0, Math.max(4, k.length - 2)))));
  };
  return text.split(/([\p{L}\p{N}]+)/u).map((part, i) => ({ key: i, text: part, mark: i % 2 === 1 && hit(part) }));
}

export const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
