"use client";
import { useEffect } from "react";
import { Button } from "@/components/ui/primitives";

/** Shown instead of Next's bare "Application error". A page left open across an update fails to load its scripts: reloading fixes it. */
export default function AppError({ error, reset }) {
  const stale = /ChunkLoadError|Loading chunk|dynamically imported module|Failed to fetch/i.test(`${error?.name} ${error?.message}`);
  useEffect(() => {
    if (!stale) return;
    try { if (sessionStorage.getItem("nexus.reloaded") !== "1") { sessionStorage.setItem("nexus.reloaded", "1"); window.location.reload(); } } catch {}
  }, [stale]);
  return (
    <div role="alert" className="mx-auto mt-16 max-w-md rounded-2xl border border-border bg-surface p-8 text-center shadow-card">
      <h1 className="font-display text-xl font-semibold">{stale ? "Nexus was updated" : "This page hit an error"}</h1>
      <p className="mt-2 text-sm text-muted">{stale ? "This page was opened before an update. Reload to continue." : "Your data is safe. Try again, or reload the page."}</p>
      {error?.digest && <p className="mt-1 text-xs text-muted">Reference: {error.digest}</p>}
      <div className="mt-5 flex justify-center gap-2">
        <Button onClick={() => window.location.reload()}>Reload</Button>
        {!stale && <Button variant="secondary" onClick={reset}>Try again</Button>}
      </div>
    </div>
  );
}
