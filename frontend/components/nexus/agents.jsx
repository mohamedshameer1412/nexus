"use client";
// The six-agent pipeline, root-cause chains and the prerequisite graph.
import Link from "next/link";
import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Activity, ArrowRight, BookOpenCheck, Briefcase, CalendarClock, ChevronRight, ScanSearch, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { TONE_HEX } from "@/lib/format";
import { Badge } from "@/components/ui/primitives";

export const AGENT_ICON = { evaluator: ScanSearch, analytics: Activity, predictor: TrendingDown, planner: CalendarClock, tutor: BookOpenCheck, mentor: Briefcase };

/** Six agents in the order they run. `compact` shows summaries only (quiz result); otherwise each step can be expanded. */
export function AgentPipeline({ steps, compact, onSelect, selected }) {
  return (
    <ol className={cn("grid gap-3", compact ? "sm:grid-cols-2 xl:grid-cols-3" : "md:grid-cols-2 xl:grid-cols-3")}>
      {steps.map((s, i) => {
        const Icon = AGENT_ICON[s.agent] ?? Activity;
        const idle = s.status !== "done";
        const active = selected === s.agent;
        return (
          <motion.li key={s.agent} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 * i, duration: 0.35, ease: "easeOut" }}>
            <button type="button" disabled={!onSelect} onClick={() => onSelect?.(s.agent)} aria-pressed={onSelect ? active : undefined}
              className={cn("relative flex h-full w-full flex-col rounded-xl border bg-surface p-4 text-left shadow-card transition-all enabled:hover:shadow-lift",
                active ? "border-brand shadow-[0_0_0_3px_rgb(1_148_226/.15)]" : "border-border/80")}>
              <div className="flex items-center gap-3">
                <span className={cn("relative grid h-10 w-10 shrink-0 place-items-center rounded-xl", idle ? "bg-surface-2 text-muted" : "bg-brand text-white")}>
                  <Icon className="h-5 w-5" aria-hidden="true" />
                  {!idle && <motion.span className="absolute -right-1 -top-1 h-3 w-3 rounded-full border-2 border-surface bg-strong" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.12 * i + 0.3 }} />}
                </span>
                <div className="min-w-0">
                  <p className="flex items-center gap-2 font-display text-[16px] font-semibold">{s.name}<span className="tabular text-[11px] font-normal text-muted">{i + 1}/6</span></p>
                  <p className="truncate text-[12.5px] text-muted">{s.role}</p>
                </div>
                {onSelect && <ChevronRight className={cn("ml-auto h-4 w-4 shrink-0 text-muted transition-transform", active && "rotate-90 text-brand")} />}
              </div>
              <p className={cn("mt-3 text-[13.5px] leading-relaxed", idle ? "text-muted" : "text-foreground")}>{s.summary}</p>
              <p className="tabular mt-auto pt-3 text-[11.5px] text-muted">{idle ? "Waiting for evidence" : `Done in ${s.ms} ms`}</p>
            </button>
          </motion.li>
        );
      })}
    </ol>
  );
}

/** Each miss traced back through the prerequisite graph: foundation → … → the topic that was missed. */
export function RootCauseChains({ misses, subjectId, limit = 6 }) {
  if (!misses?.length) return <p className="text-sm text-muted">No misses to trace in the last quiz.</p>;
  return (
    <ul className="space-y-2.5">
      {misses.slice(0, limit).map((m) => (
        <li key={m.topic_id} className="rounded-lg border border-border bg-surface-2/60 p-3">
          <div className="flex flex-wrap items-center gap-1.5 text-[13px]">
            {m.chain.map((c, i) => (
              <span key={i} className="inline-flex items-center gap-1.5">
                <span className={cn("rounded-md px-2 py-0.5 font-semibold", i === 0 && m.depth > 0 ? "bg-weak-bg text-weak" : i === m.chain.length - 1 ? "bg-brand-soft text-brand-deep" : "bg-surface text-foreground ring-1 ring-border")}>{c}</span>
                {i < m.chain.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-muted" aria-hidden="true" />}
              </span>
            ))}
          </div>
          <p className="mt-1.5 text-[12.5px] text-muted">
            {m.missed} miss{m.missed === 1 ? "" : "es"} in {m.topic}. {m.depth > 0 ? <>Root cause: <b className="text-foreground">{m.root}</b>, {m.depth} step{m.depth === 1 ? "" : "s"} back.</> : "The gap is in the topic itself."}
            {subjectId && m.root_id && <> <Link href={`/subjects/${subjectId}/twin?topic=${m.root_id}`} className="font-semibold">Work on {m.root}</Link></>}
          </p>
        </li>
      ))}
    </ul>
  );
}

/** The prerequisite graph as layered columns (foundations left), coloured by the student's confidence. */
export function PrereqGraph({ graph, highlight = [], height }) {
  const layout = useMemo(() => {
    const nodes = graph?.nodes ?? [];
    const edges = (graph?.edges ?? []).filter((e) => nodes.some((n) => n.id === e.from) && nodes.some((n) => n.id === e.to));
    const parents = new Map(nodes.map((n) => [n.id, []]));
    edges.forEach((e) => parents.get(e.to)?.push(e.from));
    const depth = new Map();
    const visit = (id, seen = new Set()) => {
      if (depth.has(id)) return depth.get(id);
      if (seen.has(id)) return 0;
      seen.add(id);
      const d = Math.max(-1, ...(parents.get(id) ?? []).map((p) => visit(p, seen))) + 1;
      depth.set(id, d);
      return d;
    };
    nodes.forEach((n) => visit(n.id));
    const cols = [];
    nodes.forEach((n) => { const d = depth.get(n.id) ?? 0; (cols[d] ||= []).push(n); });
    const W = 168, H = 52, GX = 44, GY = 14;
    const maxRows = Math.max(1, ...cols.map((c) => c?.length ?? 0));
    const pos = new Map();
    cols.forEach((c, x) => c?.forEach((n, y) => pos.set(n.id, { x: 20 + x * (W + GX), y: 20 + y * (H + GY) + ((maxRows - c.length) * (H + GY)) / 2 })));
    return { nodes, edges, pos, W, H, width: 40 + cols.length * (W + GX) - GX, height: 40 + maxRows * (H + GY) - GY };
  }, [graph]);
  const [hover, setHover] = useState(null);
  if (!layout.nodes.length) return <p className="text-sm text-muted">No topics yet.</p>;
  const { pos, W, H } = layout;
  const related = (id) => hover != null && (id === hover || layout.edges.some((e) => (e.from === hover && e.to === id) || (e.to === hover && e.from === id)));
  return (
    <div className="nx-scroll-light overflow-x-auto rounded-lg border border-border bg-surface-2/50" style={height ? { maxHeight: height } : undefined}>
      <svg width={layout.width} height={layout.height} role="img" aria-label="Prerequisite graph: foundations on the left, the topics that build on them to the right">
        <defs>
          <marker id="nx-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#8AA4BD" /></marker>
        </defs>
        {layout.edges.map((e, i) => {
          const a = pos.get(e.from), b = pos.get(e.to);
          if (!a || !b) return null;
          const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2, mx = (x1 + x2) / 2;
          const on = hover != null && (e.from === hover || e.to === hover);
          return <path key={i} d={`M${x1} ${y1} C${mx} ${y1}, ${mx} ${y2}, ${x2 - 2} ${y2}`} fill="none" stroke={on ? "#0194E2" : "#B7C9DA"} strokeWidth={on ? 2.2 : 1.4} markerEnd="url(#nx-arrow)" />;
        })}
        {layout.nodes.map((n) => {
          const p = pos.get(n.id);
          const tone = n.state === "solid" ? "strong" : n.state === "weak" ? "weak" : "muted";
          const hl = highlight.includes(n.id);
          const dim = hover != null && !related(n.id);
          return (
            <g key={n.id} transform={`translate(${p.x} ${p.y})`} onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} opacity={dim ? 0.35 : 1} style={{ transition: "opacity .15s" }}>
              <title>{`${n.name}: ${n.confidence == null ? "not assessed" : `${Math.round(n.confidence * 100)}% confidence`}`}</title>
              <rect width={W} height={H} rx={10} fill="#fff" stroke={hl ? "#0194E2" : "#D5E8F5"} strokeWidth={hl ? 2.5 : 1} />
              <rect width={5} height={H} rx={2} fill={TONE_HEX[tone]} />
              <text x={14} y={22} style={{ fontSize: 12.5, fontWeight: 600, fill: "#0B2239" }}>{n.name.length > 21 ? `${n.name.slice(0, 20)}…` : n.name}</text>
              <text x={14} y={40} style={{ fontSize: 11.5, fill: "#52667D" }}>{n.confidence == null ? "not assessed" : `${Math.round(n.confidence * 100)}% confidence`}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function GraphLegend() {
  return (
    <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-muted">
      {[["strong", "At or above target"], ["weak", "Below target"], ["muted", "Not assessed"]].map(([t, l]) => (
        <span key={t} className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: TONE_HEX[t] }} />{l}</span>
      ))}
      <span>Arrows point from a foundation to the topic that builds on it.</span>
    </p>
  );
}

export function RiskBadge({ level }) {
  const t = { high: "weak", medium: "mid", low: "strong" }[level] ?? "muted";
  return <Badge tone={t} dot className="capitalize">{level}</Badge>;
}
