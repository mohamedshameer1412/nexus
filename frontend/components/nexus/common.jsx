"use client";
// Page-level building blocks shared by every screen.
import Link from "next/link";
import { motion } from "framer-motion";
import { AlertTriangle, CornerUpLeft, FileSearch, SearchX, ShieldCheck, Sparkles, Search, Bot, XCircle } from "lucide-react";
import { cn, highlightParts, pageLabel } from "@/lib/utils";
import { Badge, Button, Card, Skeleton } from "@/components/ui/primitives";

export function Logo({ className = "", mark = "tile" }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <span className={cn("grid place-items-center overflow-hidden", mark === "tile" ? "h-8 w-8 rounded-lg bg-white shadow-[0_2px_8px_rgb(0_0_0/.15)]" : "h-9 w-9")}>
        <img src="/logo-128.png" alt="" className="h-[26px] w-[26px] object-contain" width={26} height={26} />
      </span>
      <span className="font-display text-[19px] font-semibold tracking-tight">Nexus</span>
    </span>
  );
}

/** The top of a page: title, one line of context, actions on the right. */
export function PageHeader({ title, description, actions, children, className, back }) {
  return (
    <div className={cn("mb-6", className)}>
      {back}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="break-anywhere font-display text-[26px] font-semibold leading-tight text-foreground sm:text-[30px]">{title}</h1>
          {description && <p className="mt-1 max-w-2xl text-[15px] text-muted">{description}</p>}
        </div>
        {actions && <div className="no-print flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

export function SectionTitle({ children, action, className, id }) {
  return (
    <div className={cn("mb-3 flex flex-wrap items-center justify-between gap-3", className)}>
      <h2 id={id} className="font-display text-lg font-semibold">{children}</h2>
      {action}
    </div>
  );
}

export function EmptyState({ title, children, action, icon: Icon = FileSearch, className }) {
  return (
    <div className={cn("rounded-xl border border-dashed border-brand/30 bg-surface/70 px-6 py-12 text-center", className)}>
      <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-brand-soft text-brand-deep"><Icon className="h-6 w-6" aria-hidden="true" /></span>
      <h2 className="mt-4 font-display text-lg font-semibold">{title}</h2>
      {children && <p className="mx-auto mt-1 max-w-md text-sm text-muted">{children}</p>}
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  const gone = error?.status === 404;
  return (
    <div role="alert" className="rounded-xl border border-border bg-surface px-6 py-12 text-center shadow-card">
      <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-weak-bg text-weak">{gone ? <SearchX className="h-6 w-6" /> : <AlertTriangle className="h-6 w-6" />}</span>
      <h1 className="mt-4 font-display text-xl font-semibold">{gone ? "Not found" : "This page could not load"}</h1>
      <p className="mx-auto mt-1 max-w-md text-sm text-muted">{gone ? "That page does not exist, or it belongs to someone else." : error?.message || "Check your connection and try again."}</p>
      <div className="mt-5 flex justify-center gap-2">
        {!gone && onRetry && <Button onClick={() => onRetry()}>Try again</Button>}
        <Button asChild variant="secondary"><Link href="/subjects">Your subjects</Link></Button>
      </div>
    </div>
  );
}

export function LoadingPage({ rows = 3 }) {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-9 w-64" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className="h-40" />)}
    </div>
  );
}

/** A number with its label. `tone` colours the value; `trend` is a small signed change. */
export function StatTile({ label, value, sub, icon: Icon, tone, href, className, delay = 0 }) {
  const body = (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.38, delay, ease: "easeOut" }}
      className={cn(
        "group relative h-full overflow-hidden rounded-xl border border-border/70 bg-surface p-4 transition-[box-shadow,border-color] duration-300",
        "shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-glow)] hover:border-brand/30",
        href && "cursor-pointer",
        className
      )}>
      {/* Accent top stripe */}
      <span className="absolute inset-x-0 top-0 h-[3px] rounded-t-xl bg-gradient-to-r from-brand/50 via-brand to-brand-deep/60 opacity-0 transition-opacity duration-300 group-hover:opacity-100" aria-hidden="true" />
      <div className="flex items-start justify-between gap-2">
        <p className="text-[13px] font-medium text-muted">{label}</p>
        {Icon && <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand-soft to-brand-wash text-brand shadow-[inset_0_1px_0_rgb(255_255_255/.8)]"><Icon className="h-4 w-4" aria-hidden="true" /></span>}
      </div>
      <p className={cn("tabular mt-1 font-display text-[28px] font-semibold leading-none", tone === "strong" && "text-strong", tone === "weak" && "text-weak", tone === "mid" && "text-mid")}>{value}</p>
      {sub && <p className="mt-2 text-[12.5px] text-muted">{sub}</p>}
    </motion.div>
  );
  return href ? <Link href={href} className="block no-underline text-inherit">{body}</Link> : body;
}

/** Text with the matched words marked. Rendered as React nodes (never as HTML), so document text cannot inject anything. */
export function Highlighted({ text, terms }) {
  if (!terms?.length) return text;
  return highlightParts(text, terms).map((p) => (p.mark ? <mark key={p.key}>{p.text}</mark> : <span key={p.key}>{p.text}</span>));
}

export function SourceLine({ subjectId, documentId, document, heading, pageStart, pageEnd, extra }) {
  return (
    <p className="break-anywhere flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-muted">
      {documentId ? <Link href={`/subjects/${subjectId}/materials/${documentId}`} className="font-semibold">{document}</Link> : <span className="font-semibold text-foreground">{document}</span>}
      {heading && <span className="truncate">{heading}</span>}
      {pageStart != null && <Badge tone="outline">{pageLabel(pageStart, pageEnd)}</Badge>}
      {extra}
    </p>
  );
}

export function PassageCard({ subjectId, item, terms, weak }) {
  return (
    <Card className="p-4">
      <SourceLine subjectId={subjectId} documentId={item.document_id} document={item.document} heading={item.heading_path} pageStart={item.page_start} pageEnd={item.page_end}
        extra={<>{item.matched?.length > 0 && <Badge tone="neutral">matched {item.matched.join(", ")}</Badge>}{weak && <Badge tone="muted">weaker match</Badge>}</>} />
      <p className="break-anywhere evidence mt-2 whitespace-pre-wrap rounded-r-md px-3 py-2 text-sm leading-relaxed"><Highlighted text={item.text} terms={terms} /></p>
    </Card>
  );
}

// ------------------------------------------------------------------------------------------------ markdown (safe: React elements only)

function inline(text, keyBase) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g;
  let last = 0, i = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    const k = `${keyBase}-${i++}`;
    if (t.startsWith("**")) out.push(<strong key={k}>{t.slice(2, -2)}</strong>);
    else if (t.startsWith("`")) out.push(<code key={k}>{t.slice(1, -1)}</code>);
    else if (t.startsWith("[")) {
      const [, label, href] = t.match(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/);
      out.push(<a key={k} href={href} target="_blank" rel="noopener noreferrer">{label}</a>);
    } else out.push(<em key={k}>{t.slice(1, -1)}</em>);
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text, className }) {
  const lines = (text || "").replace(/\r/g, "").split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) { blocks.push({ t: "h", level: h[1].length, text: h[2] }); i++; continue; }
    if (line.startsWith("```")) {
      const code = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) code.push(lines[i++]);
      i++;
      blocks.push({ t: "code", text: code.join("\n") });
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) { const items = []; while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*]\s+/, "")); blocks.push({ t: "ul", items }); continue; }
    if (/^\s*\d+[.)]\s+/.test(line)) { const items = []; while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*\d+[.)]\s+/, "")); blocks.push({ t: "ol", items }); continue; }
    if (/^\s*(\[\d+\]\s*)?>/.test(line)) { const q = []; while (i < lines.length && /^\s*(\[\d+\]\s*)?>/.test(lines[i])) q.push(lines[i++].replace(/^\s*(\[\d+\]\s*)?>\s?/, "")); blocks.push({ t: "quote", text: q.join(" ") }); continue; }
    const p = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|\s*[-*]\s|\s*\d+[.)]\s|\s*>)/.test(lines[i])) p.push(lines[i++]);
    blocks.push({ t: "p", text: p.join(" ") });
  }
  return (
    <div className={cn("prose-nx break-anywhere", className)}>
      {blocks.map((b, n) => {
        const k = `b${n}`;
        if (b.t === "h") {
          /** @type {any} */
          const Tag = `h${Math.min(6, b.level + 1)}`;
          return <Tag key={k}>{inline(b.text, k)}</Tag>;
        }
        if (b.t === "ul") return <ul key={k}>{b.items.map((x, j) => <li key={j}>{inline(x, `${k}-${j}`)}</li>)}</ul>;
        if (b.t === "ol") return <ol key={k}>{b.items.map((x, j) => <li key={j}>{inline(x, `${k}-${j}`)}</li>)}</ol>;
        if (b.t === "quote") return <blockquote key={k}>{inline(b.text, k)}</blockquote>;
        if (b.t === "code") return <pre key={k} className="overflow-x-auto rounded-md bg-surface-2 p-3 text-xs">{b.text}</pre>;
        return <p key={k}>{inline(b.text, k)}</p>;
      })}
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ run trace

const ACTOR = { verifier: "Checker (code)", orchestrator: "Controller (code)", local: "Local model", cloud: "Cloud model", solver: "Independent reader" };
const SENT_BACK = new Set(["revision"]);
const REJECTED = new Set(["revision_stopped", "tier_failed", "model_error"]);

function TraceIcon({ kind, sentBack }) {
  const cls = "h-4 w-4 shrink-0";
  if (sentBack) return <CornerUpLeft className={cn(cls, "text-weak")} aria-hidden="true" />;
  if (kind === "verification" || kind === "solver") return <ShieldCheck className={cn(cls, "text-strong")} aria-hidden="true" />;
  if (kind === "retrieval" || kind === "topic" || kind === "request") return <Search className={cn(cls, "text-brand")} aria-hidden="true" />;
  if (kind === "draft") return <Bot className={cn(cls, "text-brand")} aria-hidden="true" />;
  if (REJECTED.has(kind)) return <XCircle className={cn(cls, "text-mid")} aria-hidden="true" />;
  return <Sparkles className={cn(cls, "text-brand")} aria-hidden="true" />;
}

/** The recorded steps of one run, in order. A "sent back" step means the checker rejected a draft and the model redid it. */
export function RunTrace({ steps, title = "How this was produced", loop }) {
  if (!steps || steps.length === 0) return null;
  const back = steps.filter((s) => SENT_BACK.has(s.kind)).length;
  return (
    <section aria-labelledby="trace-h" className="mt-8">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="trace-h" className="font-display text-lg font-semibold">{title}</h2>
        {back > 0 ? <Badge tone="weak"><CornerUpLeft className="h-3.5 w-3.5" aria-hidden="true" />Sent back {back} time{back === 1 ? "" : "s"}</Badge>
          : <Badge tone="strong">Passed the checks the first time</Badge>}
        {loop?.rejected > 0 && <Badge tone="mid">{loop.rejected} rejected by the checker</Badge>}
      </div>
      <p className="mt-1 text-[13px] text-muted">A model writes a draft, code checks it against your material, and anything that fails is sent back. Every step was recorded while it ran.</p>
      <ol className="relative mt-4 space-y-2 border-l-2 border-brand-soft pl-5">
        {steps.map((s, i) => {
          const sentBack = SENT_BACK.has(s.kind);
          return (
            <li key={i} className={cn("relative flex items-start gap-2.5 rounded-lg border bg-surface p-2.5 text-sm", sentBack ? "border-weak/30 bg-weak-bg" : "border-border")}>
              <span className="absolute -left-[27px] top-3.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-brand" aria-hidden="true" />
              <TraceIcon kind={s.kind} sentBack={sentBack} />
              <span className="break-anywhere flex-1">{sentBack && <b>Sent back: </b>}{s.text}</span>
              <span className="shrink-0 text-xs text-muted">{ACTOR[s.by] ?? s.by}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
