"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, FileBarChart, Info, Link2, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { getProgress, getSubject, keys } from "@/lib/queries";
import { masteryOf, shortDate, signed, TONE_HEX } from "@/lib/format";
import { cn, friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { GraphLegend, PrereqGraph } from "@/components/nexus/agents";
import { AbilityIntervals, ChartCard, Gauge, TrendLine } from "@/components/nexus/charts";
import { EmptyState, ErrorState, SectionTitle, StatTile } from "@/components/nexus/common";
import { SelfCheck } from "@/components/nexus/self-check";
import { Alert, Badge, Button, Card, Field, Segmented, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from "@/components/ui/primitives";

const pct = (x) => Math.round(x * 100);
const GROUPS = [
  { value: "all", label: "All" }, { value: "confident", label: "Strong" }, { value: "building", label: "Getting there" }, { value: "shaky", label: "Needs work" }, { value: "other", label: "Not enough data" },
];

export default function ProgressPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const { data: subject } = useQuery({ queryKey: keys.subject(id), queryFn: () => getSubject(id) });
  useTitle("Progress", subject?.name);
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.progress(id), queryFn: () => getProgress(id) });
  const [group, setGroup] = useState("all");
  const [topic, setTopic] = useState("");
  const [prereq, setPrereq] = useState("");
  const [problem, setProblem] = useState("");
  const done = () => { qc.invalidateQueries({ queryKey: keys.progress(id) }); qc.invalidateQueries({ queryKey: keys.agents(id) }); };
  const add = useMutation({
    mutationFn: () => api(`/subjects/${id}/prerequisites`, { method: "POST", json: { topic_id: Number(topic), prereq_id: Number(prereq) } }),
    onSuccess: () => { setTopic(""); setPrereq(""); setProblem(""); toast.success("Link added"); done(); },
    onError: (e) => setProblem(friendlyError(e)),
  });
  const remove = useMutation({
    mutationFn: (p) => api(`/subjects/${id}/prerequisites/${p.topic_id}/${p.prereq_id}`, { method: "DELETE" }),
    onSuccess: () => { toast.success("Link removed"); done(); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const graph = useMemo(() => ({
    nodes: (data?.topics ?? []).map((t) => ({ id: t.topic_id, name: t.name, confidence: t.confidence, state: t.confidence == null ? "unknown" : t.confidence >= 0.7 ? "solid" : "weak" })),
    edges: (data?.prerequisites ?? []).map((p) => ({ from: p.prereq_id, to: p.topic_id })),
  }), [data]);

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-96" />;
  if (data.topics.length === 0) {
    return <EmptyState title="No topics yet" action={<Button asChild><Link href={`/subjects/${id}/materials`}>Go to Materials</Link></Button>}>Progress is tracked per topic, and topics come from the material you upload.</EmptyState>;
  }
  const o = data.overall;
  const trend = data.ability_trend.map((p) => ({ label: `#${p.attempt_id} ${shortDate(p.at ? new Date(p.at * 1000).toISOString() : null)}`, confidence: pct(p.confidence), accuracy: pct(p.accuracy), answered: p.answered }));
  const counts = data.topics.reduce((acc, t) => { const k = ["confident", "building", "shaky"].includes(t.label) ? t.label : "other"; acc[k] = (acc[k] || 0) + 1; return acc; }, {});
  const shown = data.topics.filter((t) => group === "all" || (group === "other" ? !["confident", "building", "shaky"].includes(t.label) : t.label === group));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-muted">Mastery for every topic, from a Bayesian IRT model fitted only to your answers. Each estimate carries its uncertainty and narrows as you answer more.</p>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="secondary" size="sm"><Link href={`/subjects/${id}/roadmap`}>Roadmap</Link></Button>
          <Button asChild size="sm"><Link href={`/subjects/${id}/report`}><FileBarChart className="h-4 w-4" />Report</Link></Button>
        </div>
      </div>
      {!o && <Alert tone="info">Nothing measured yet. <Link href={`/subjects/${id}/quiz`}>Take a diagnostic test</Link> (two questions per topic) to get your first scores.</Alert>}

      {o && (
        <div className="grid gap-4 md:grid-cols-[16rem_minmax(0,1fr)]">
          <Card className="flex flex-col items-center justify-center p-4"><Gauge value={pct(o.confidence)} label="Overall confidence" /></Card>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Ability θ" value={signed(o.theta)} sub={`± ${o.se.toFixed(2)} (0 is average)`} />
            <StatTile label="Expected accuracy" value={`${pct(o.expected_accuracy)}%`} sub="on an average question" delay={0.04} />
            <StatTile label="Answers used" value={o.answered} sub={`${o.correct} correct`} delay={0.08} />
            <StatTile label="Topics strong" value={`${counts.confident ?? 0}/${data.topics.length}`} sub={`${counts.shaky ?? 0} need work`} tone={counts.shaky ? "mid" : "strong"} delay={0.12} />
          </div>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <ChartCard title="Ability by topic" description="Dot: your estimated ability. Bar: its uncertainty. Right of the dashed line means above proficient.">
          <AbilityIntervals items={data.topics.map((t) => ({ ...t }))} />
        </ChartCard>
        <ChartCard title="Confidence over time" description="Overall confidence after each quiz, with that quiz's accuracy.">
          <TrendLine data={trend} series={[{ key: "confidence", name: "Confidence %", color: "#0194E2" }, { key: "accuracy", name: "Quiz accuracy %", color: "#0E9F8E" }]}
            bars={[{ key: "answered", name: "Answers", color: "#64748B" }]} yDomain={[0, 100]} yFmt={(v) => `${v}%`} reference={{ y: 70, label: "target" }} height={300} />
        </ChartCard>
      </div>

      <section aria-labelledby="topics-h">
        <SectionTitle id="topics-h" action={<Segmented label="Filter topics" value={group} onValueChange={setGroup} options={GROUPS.map((g) => ({ ...g, label: `${g.label}${g.value === "all" ? "" : ` ${counts[g.value] ?? 0}`}` }))} />}>Topic mastery</SectionTitle>
        <Card className="divide-y divide-border">
          {shown.length === 0 && <p className="p-4 text-sm text-muted">No topics in this group.</p>}
          {shown.map((t) => {
            const m = masteryOf(t.label);
            const color = TONE_HEX[m.tone] ?? TONE_HEX.muted;
            return (
              <div key={t.topic_id} className="grid items-center gap-x-4 gap-y-1 px-4 py-3 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_auto]">
                <p className="truncate font-medium" title={t.path}>{t.name}</p>
                <div className="relative h-2.5 rounded-full bg-brand-soft/60">
                  <div className="absolute inset-y-0 left-0 rounded-full transition-[width] duration-700" style={{ width: `${t.confidence == null ? 0 : Math.max(2, pct(t.confidence))}%`, background: color }} />
                  <div className="absolute inset-y-[-3px] border-l-2 border-dashed border-brand-ink/40" style={{ left: "70%" }} aria-hidden="true" />
                </div>
                <div className="flex items-center gap-2 text-[13px]">
                  <span className="tabular w-10 text-right font-semibold" style={{ color }}>{t.confidence == null ? "–" : `${pct(t.confidence)}%`}</span>
                  <Badge tone={m.tone} className="w-[7.5rem] justify-center">{m.label}</Badge>
                </div>
                <p className="text-[12px] text-muted sm:col-span-3">
                  {t.confidence == null ? "No answers yet." : <>θ {signed(t.theta)} ± {t.se?.toFixed(2)} · {t.correct} of {t.answered} correct{t.recent_accuracy != null ? ` · last five ${pct(t.recent_accuracy)}%` : ""}{t.avg_seconds ? ` · about ${Math.round(t.avg_seconds)} s each` : ""}</>}
                </p>
              </div>
            );
          })}
        </Card>
      </section>

      <section aria-labelledby="pre-h">
        <SectionTitle id="pre-h">What builds on what</SectionTitle>
        <p className="mb-3 max-w-3xl text-sm text-muted">When you miss a quiz question, Nexus steps back to the topic it builds on, and the Evaluator agent traces misses along these links to their root cause. Without a link it uses the topic just before in your material.</p>
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <Card className="p-4"><PrereqGraph graph={graph} height={420} /><GraphLegend /></Card>
          <Card className="p-4">
            <form onSubmit={(e) => { e.preventDefault(); setProblem(""); add.mutate(); }} className="space-y-3">
              <Field label="This topic" htmlFor="pre-topic">
                <Select value={topic} onValueChange={setTopic}><SelectTrigger id="pre-topic"><SelectValue placeholder="Choose a topic" /></SelectTrigger>
                  <SelectContent>{data.topics.map((t) => <SelectItem key={t.topic_id} value={String(t.topic_id)}>{t.name}</SelectItem>)}</SelectContent></Select>
              </Field>
              <Field label="builds on" htmlFor="pre-req">
                <Select value={prereq} onValueChange={setPrereq}><SelectTrigger id="pre-req"><SelectValue placeholder="Choose its foundation" /></SelectTrigger>
                  <SelectContent>{data.topics.map((t) => <SelectItem key={t.topic_id} value={String(t.topic_id)}>{t.name}</SelectItem>)}</SelectContent></Select>
              </Field>
              <Button type="submit" disabled={!topic || !prereq} loading={add.isPending}><Link2 className="h-4 w-4" />Add link</Button>
              {problem && <Alert tone="danger">{problem}</Alert>}
            </form>
            {data.prerequisites.length > 0 && (
              <ul className="nx-scroll-light mt-4 max-h-64 space-y-1.5 overflow-y-auto border-t border-border pt-3">
                {data.prerequisites.map((p) => (
                  <li key={`${p.topic_id}-${p.prereq_id}`} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-brand-wash">
                    <span className="break-anywhere flex-1"><b>{p.prereq}</b> <ArrowRight className="inline h-3.5 w-3.5 text-muted" /> <b>{p.topic}</b></span>
                    <Button variant="ghost" size="icon-sm" aria-label={`Remove: ${p.topic} builds on ${p.prereq}`} onClick={() => remove.mutate(p)}><Trash2 className="h-4 w-4" /></Button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </section>

      <SelfCheck id={id} />

      <details className="rounded-xl border border-border bg-surface p-4 text-sm shadow-card">
        <summary className="flex cursor-pointer items-center gap-2 font-semibold"><Info className="h-4 w-4 text-brand" />How is mastery calculated?</summary>
        <p className="mt-2 text-muted">
          Item response theory (IRT), 3-parameter logistic with discrimination 1 and guessing 0.25 (four options). Your ability θ on each topic is the posterior mean over a grid with a Normal(0, 1.2) prior, so a topic with two answers stays near average with a wide uncertainty instead of a made-up certainty.
          Confidence is the probability that your true ability is above the proficient line (θ &gt; 0). Strong means at least 80%, Getting there at least 55%, Needs work below that, all with at least three answers.
          A question&apos;s difficulty starts from how it was written (easy, medium, hard) and is adjusted only from your <i>other</i> answers to it.
        </p>
      </details>
    </div>
  );
}
