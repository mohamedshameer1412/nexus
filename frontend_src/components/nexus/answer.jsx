"use client";
import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { pageLabel, plural } from "@/lib/utils";
import { Alert, Badge, Card } from "@/components/ui/primitives";
import { Markdown, RunTrace } from "@/components/nexus/common";

export const STATUS = {
  pending: { label: "Working on it", tone: "neutral" },
  answered: { label: "Answered from your materials", tone: "strong" },
  abstained: { label: "Not in your materials", tone: "mid" },
  extractive: { label: "Matching passages only", tone: "mid" },
  failed: { label: "Something went wrong", tone: "weak" },
};

export function StatusBadge({ status, kind }) {
  const s = kind === "conflict" && status === "answered" ? { label: "Your materials disagree", tone: "mid" } : STATUS[status] ?? { label: status, tone: "neutral" };
  return <Badge tone={s.tone} dot>{s.label}</Badge>;
}

/** Shown while a background job runs: says what is happening, counts up, and tells the student they can leave. */
export function JobProgress({ createdAt, what }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const secs = Math.max(0, Math.round((now - new Date(createdAt).getTime()) / 1000));
  return (
    <div role="status" aria-live="polite" className="overflow-hidden rounded-xl border border-brand/25 bg-brand-wash">
      <div className="h-1 w-full overflow-hidden bg-brand-soft"><div className="h-full w-1/3 bg-brand" style={{ animation: "nx-slide 1.4s linear infinite" }} /></div>
      <div className="p-4">
        <p className="flex items-center gap-2 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-brand" aria-hidden="true" />{what}</p>
        <p className="mt-1 text-sm text-muted"><span className="tabular">{secs} s</span> so far. A model on this computer can take a minute or two. You can leave this page; the result will be here when you come back.</p>
      </div>
      <style>{`@keyframes nx-slide { from { transform: translateX(-100%) } to { transform: translateX(300%) } }`}</style>
    </div>
  );
}

/** [1], [2]… numbers for every distinct (passage, quote), in order of first use. */
export function numberCitations(claims) {
  const list = [];
  const index = new Map();
  for (const c of claims) for (const x of c.citations) {
    const key = `${x.passage_id}|${x.quote}`;
    if (!index.has(key)) { list.push(x); index.set(key, list.length); }
  }
  return { list, numberOf: (x) => index.get(`${x.passage_id}|${x.quote}`) };
}

function goTo(n) {
  const el = document.getElementById(`source-${n}`);
  if (!el) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
  el.focus({ preventScroll: true });
  el.animate?.([{ boxShadow: "0 0 0 4px rgb(1 148 226 / .35)" }, { boxShadow: "0 0 0 0 rgb(1 148 226 / 0)" }], { duration: 1200 });
}

export function Where({ x }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-x-1.5">
      <b className="text-foreground">{x.document}</b>
      {x.heading_path && <span>· {x.heading_path}</span>}
      {x.page_start != null && <span>· {pageLabel(x.page_start, x.page_end)}</span>}
    </span>
  );
}

export function AnswerView({ q }) {
  const claims = q.claims ?? [];
  const { list, numberOf } = numberCitations(claims);
  const conflict = q.kind === "conflict";
  return (
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_24rem] lg:items-start lg:gap-6">
      <div>
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">{conflict ? "Your materials disagree" : "Answer"}</h2>
          {conflict && <p className="mt-1 text-sm text-muted">Two passages say different things. Each side is shown with its own quote; Nexus does not pick a winner.</p>}
          <ol className="mt-3 space-y-3">
            {claims.map((c, i) => (
              <li key={i} className="break-anywhere flex gap-3 text-[15.5px] leading-relaxed">
                <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-soft text-[12px] font-bold text-brand-deep">{i + 1}</span>
                <span>{c.text}{c.citations.map((x) => {
                  const n = numberOf(x);
                  return <button key={n} type="button" onClick={() => goTo(n)} aria-label={`Show source ${n}`} className="ml-1 inline-flex h-5 min-w-5 items-center justify-center rounded bg-brand/10 px-1 align-super text-[11px] font-bold text-brand-deep hover:bg-brand hover:text-white">{n}</button>;
                })}</span>
              </li>
            ))}
          </ol>
          {q.dropped > 0 && <Alert tone="info" className="mt-4">{plural(q.dropped, "other statement")} the model wrote could not be verified against your materials and {q.dropped === 1 ? "was" : "were"} left out.</Alert>}
        </Card>

        {q.explanation && (
          <Card className="mt-4 p-5">
            <h2 className="font-display text-lg font-semibold">Explanation, step by step</h2>
            <Markdown text={q.explanation} className="mt-2" />
            <p className="mt-3 text-xs text-muted">The model&apos;s own reasoning. It passed simple checks (no invented numbers, follows the quotes) but is not verified word for word.</p>
          </Card>
        )}

        {q.verification?.length > 0 && (
          <Card className="mt-4 p-5">
            <h2 className="font-display text-lg font-semibold">Verification</h2>
            <ul className="mt-2 space-y-1.5">
              {q.verification.map((v) => <li key={v} className="flex gap-2 text-sm text-strong"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /><span>{v}</span></li>)}
            </ul>
          </Card>
        )}
        <RunTrace steps={q.steps} loop={q.loop} title="How this answer was produced" />
      </div>

      <section aria-labelledby="sources-h" className="mt-6 lg:sticky lg:top-20 lg:mt-0">
        <h2 id="sources-h" className="font-display text-lg font-semibold">Sources and evidence</h2>
        <p className="mt-1 text-xs text-muted">Nexus checked that these exact words exist in your material. Read the quote to judge whether the statement reads it correctly.</p>
        <ul className="nx-scroll-light mt-3 max-h-[calc(100dvh-10rem)] space-y-3 overflow-y-auto pr-1">
          {list.map((x, i) => (
            <li key={i}>
              <Card id={`source-${i + 1}`} tabIndex={-1} className="scroll-mt-24 p-4 focus:outline-none">
                <p className="break-anywhere text-xs text-muted"><Badge tone="brand" className="mr-1.5">{i + 1}</Badge><Where x={x} /></p>
                <blockquote className="break-anywhere evidence my-2 rounded-r-md px-3 py-2 text-sm leading-relaxed">{x.quote}</blockquote>
                <p className="flex items-center gap-1 text-xs font-semibold text-strong"><ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />Found word for word in your material</p>
              </Card>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

/** Not answered / no model / failed: the reason, and the student's own passages exactly as stored. */
export function PassagesView({ q }) {
  const sources = q.sources ?? [];
  return (
    <div>
      {q.reason && <Alert tone={q.status === "failed" ? "danger" : "warning"}>{q.reason}</Alert>}
      {sources.length > 0 && (
        <section aria-labelledby="closest-h" className="mt-6">
          <h2 id="closest-h" className="font-display text-lg font-semibold">{q.status === "extractive" ? "Passages that match" : "Closest passages"}</h2>
          <p className="mt-1 text-xs text-muted">Your own words from your materials, exactly as stored.</p>
          <ul className="mt-3 space-y-3">
            {sources.map((s, i) => (
              <li key={i}>
                <Card className="p-4">
                  <p className="break-anywhere text-xs text-muted"><Where x={s} />{s.matched.length > 0 && <Badge tone="neutral" className="ml-2">matched {s.matched.join(", ")}</Badge>}</p>
                  <p className="break-anywhere evidence mt-2 whitespace-pre-wrap rounded-r-md px-3 py-2 text-sm leading-relaxed">{s.text}</p>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      )}
      {q.status === "abstained" && <p className="mt-4 text-sm text-muted">Try different words, or upload material that covers this.</p>}
    </div>
  );
}
