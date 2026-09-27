"use client";
import { WifiOff } from "lucide-react";
import { Button } from "@/components/ui/primitives";

/** Shown by the service worker when a page that was never opened before is requested without a connection. */
export default function OfflinePage() {
  return (
    <main id="main" className="mx-auto mt-24 max-w-md rounded-2xl border border-border bg-surface p-8 text-center shadow-card">
      <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-brand-soft text-brand-deep"><WifiOff className="h-6 w-6" aria-hidden="true" /></span>
      <h1 className="mt-4 font-display text-xl font-semibold">You are offline</h1>
      <p className="mt-2 text-sm text-muted">This page has not been saved on this device yet. Pages and materials you opened before still work. Asking, quizzes and saving need a connection.</p>
      <Button className="mt-5" onClick={() => window.location.reload()}>Try again</Button>
    </main>
  );
}
