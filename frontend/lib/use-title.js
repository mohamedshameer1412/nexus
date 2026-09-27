"use client";
import { useEffect } from "react";

/** Sets a distinct page title on client-rendered screens (WCAG 2.4.2). Pass the parts, most specific first. */
export function useTitle(...parts) {
  const title = parts.filter(Boolean).join(" · ");
  useEffect(() => {
    document.title = title ? `${title} · Nexus` : "Nexus";
  }, [title]);
}
