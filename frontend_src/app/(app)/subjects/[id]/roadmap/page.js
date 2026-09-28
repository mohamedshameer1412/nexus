"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, BookOpen, CalendarCheck, CheckCircle2, Flag, Layers, Lightbulb, NotebookPen, Printer, RotateCcw, Sparkles, Target, TrendingDown, TrendingUp, GraduationCap } from "lucide-react";
import { api } from "@/lib/api";
import { getRoadmap, keys } from "@/lib/queries";
import { gapOf, TONE_HEX } from "@/lib/format";
import { cn, friendlyError, plural } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { Bars, ChartCard, Gauge } from "@/components/nexus/charts";
import { EmptyState, ErrorState, SectionTitle, StatTile } from "@/components/nexus/common";
import { Alert, Badge, Button, Card, Checkbox, Field, Input, Progress, Segmented, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from "@/components/ui/primitives";

const STEP = { read: ["Read", BookOpen], notes: ["Note", NotebookPen], flashcards: ["Flashcards", Layers], quiz: ["Quiz", GraduationCap], revision: ["Revision", RotateCcw] };
const pc = (x) => Math.round(x * 100);
const hours = (m) => `${Math.round((m / 60) * 10) / 10} h`;
const ORDER = ["critical", "moderate", "unassessed", "minor", "on_track"];

function Profile({ id, data }) {
  const qc = useQueryClient();
  const [goal, setGoal] = useState(data.profile.goal);
  const [hoursPerWeek, setHours] = useState(String(data.profile.hours_per_week));
  const [date, setDate] = useState(data.profile.target_date_source === "plan" ? (data.profile.target_date ?? "") : "");
  const [exam, setExam] = useState(data.profile.exam_date ?? "");
  const [problem, setProblem] = useState("");
  const save = useMutation({
    mutationFn: () => api(`/subjects/${id}/roadmap/profile`, { method: "PUT", json: { goal, hours_per_week: Number(hoursPerWeek), target_date: date || null, exam_date: exam } }),
    onSuccess: (r) => { qc.setQueryData(keys.roadmap(id), r); setProblem(""); toast.success("Roadmap updated"); },
    onError: (e) => setProblem(friendlyError(e)),
  });
  const today = new Date().toISOString().slice(0, 10);
  const hoursOptions = [...new Set([1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 30, Number(data.profile.hours_per_week)])].sort((a, b) => a - b);
  return (
    <Card className="no-print p-5">
      <h2 className="font-display text-lg font-semibold">Study profile</h2>
      <p className="mt-0.5 text-sm text-muted">The plan fits the time you have. Your level ({data.level ?? "not chosen"}) sets a target of <b className="text-foreground">{pc(data.target)}%</b> confidence in every topic.</p>
      <form className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_9rem_10rem_10rem_auto] xl:items-end" onSubmit={(e) => { e.preventDefault(); setProblem(""); save.mutate(); }}>
        <Field label="Goal" htmlFor="goal"><Input id="goal" value={goal} maxLength={300} onChange={(e) => setGoal(e.target.value)} placeholder="e.g. score 80% in the end-semester exam" /></Field>
        <Field label="Hours per week" htmlFor="hpw">
          <Select value={hoursPerWeek} onValueChange={setHours}><SelectTrigger id="hpw"><SelectValue /></SelectTrigger>
            <SelectContent>{hoursOptions.map((h) => <SelectItem key={h} value={String(h)}>{h} {h === 1 ? "hour" : "hours"}</SelectItem>)}</SelectContent></Select>
        </Field>
        <Field label="Exam date" htmlFor="exam-date"><Input id="exam-date" type="date" min={today} value={exam} onChange={(e) => setExam(e.target.value)} /></Field>
        <Field label="Finish by" htmlFor="target-date"><Input id="target-date" type="date" min={today} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <Button type="submit" loading={save.isPending}>Update plan</Button>
      </form>
      {problem && <Alert tone="danger" className="mt-3">{problem}</Alert>}
    </Card>
  );
}

function Coach({ id, data }) {
  const qc = useQueryClient();
  const c = data.coach;
  const ask = useMutation({
    mutationFn: () => api(`/subjects/${id}/roadmap/coach`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.roadmap(id) }),
    onError: (e) => toast.error(friendlyError(e)),
  });
  return (
    <Card className="relative overflow-hidden p-5">
      <div className="absolute inset-y-0 left-0 w-1 bg-brand" aria-hidden="true" />
      <h2 className="flex items-center gap-2 font-display text-lg font-semibold"><Sparkles className="h-5 w-5 text-brand" />Coach</h2>
      {c.status === "pending" ? <p role="status" className="mt-2 flex items-center gap-2 text-sm text-muted"><span className="typing-dots"><i /><i /><i /></span>The coach is writing your plan…</p> : (
        <>
          <p className="break-anywhere mt-2 text-[15px] leading-relaxed">{c.text}</p>
          <p className="mt-2 text-xs text-muted">{c.from_model ? `Written by ${c.model} from your topic names and scores.` : "Worked out from your numbers by plain rules."}{c.stale && " Your progress has changed since this was written."}{c.status === "failed" && " The last attempt did not finish."}</p>
        </>
      )}
      <div className="no-print mt-3 flex flex-wrap items-center gap-2">
        <Button variant="subtle" size="sm" onClick={() => ask.mutate()} disabled={c.status === "pending"} loading={ask.isPending}>{c.from_model ? "Ask again" : "Ask the coach to write it"}</Button>
        <span className="text-xs text-muted">Only topic names and scores are sent, never your materials.</span>
      </div>
    </Card>
  );
}

function Heatmap({ data }) {
  const cols = Object.keys(data.source_labels);
  const cell = (s) => (s.answered ? `${Math.round((100 * s.correct) / s.answered)}%` : "–");
  const bg = (s) => {
    if (!s.answered) return "transparent";
    const r = s.correct / s.answered;
    return r >= 0.7 ? `rgb(14 138 95 / ${0.12 + 0.3 * r})` : r >= 0.4 ? `rgb(242 165 22 / ${0.18 + 0.25 * r})` : `rgb(201 55 44 / ${0.18 + 0.3 * (1 - r)})`;
  };
  return (
    <div className="nx-scroll-light overflow-x-auto">
      <table className="w-full min-w-[34rem] border-separate border-spacing-1 text-sm">
        <caption className="sr-only">Accuracy per topic and kind of test</caption>
        <thead><tr><th scope="col" className="px-2 py-1 text-left text-[12.5px] font-semibold text-muted">Topic</th>{cols.map((k) => <th key={k} scope="col" className="px-2 py-1 text-center text-[12.5px] font-semibold text-muted">{data.source_labels[k]}</th>)}</tr></thead>
        <tbody>
          {data.gaps.map((g) => (
            <tr key={g.topic_id}>
              <th scope="row" className="max-w-[14rem] truncate px-2 py-1.5 text-left font-medium">{g.name}</th>
              {cols.map((k) => <td key={k} className="tabular rounded-md px-2 py-1.5 text-center" style={{ background: bg(g.sources[k]) }} title={g.sources[k].answered ? `${g.sources[k].correct} of ${g.sources[k].answered}` : "no answers"}>{cell(g.sources[k])}</td>)}
            </tr>
          ))}
          <tr className="font-semibold"><th scope="row" className="px-2 py-1.5 text-left">All topics</th>{cols.map((k) => <td key={k} className="tabular rounded-md bg-surface-2 px-2 py-1.5 text-center">{cell(data.source_totals[k])}</td>)}</tr>
        </tbody>
      </table>
    </div>
  );
}

export default function RoadmapPage() {
  const { id } = useParams();
  useTitle("Roadmap");
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.roadmap(id), queryFn: () => getRoadmap(id), refetchInterval: (q) => (q.state.data?.coach.status === "pending" ? 3000 : false) });
  const [done, setDone] = useState({});
  const [gapFilter, setGapFilter] = useState("below");
  const storeKey = `nexus.roadmap.${id}`;
  useEffect(() => { try { setDone(JSON.parse(localStorage.getItem(storeKey) || "{}")); } catch {} }, [storeKey]);
  const toggle = (key, on) => setDone((d) => { const n = { ...d, [key]: on }; try { localStorage.setItem(storeKey, JSON.stringify(n)); } catch {} return n; });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-96" />;
  if (data.gaps.length === 0) return <EmptyState title="Nothing to plan yet" action={<Button asChild><Link href={`/subjects/${id}/materials`}>Add materials</Link></Button>}>A roadmap is built from the topics Nexus finds in your material.</EmptyState>;
  const s = data.roadmap.summary;
  const lagging = data.gaps.filter((g) => g.status === "critical" || g.status === "moderate");
  const ranked = [...data.gaps].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || (b.gap ?? 0) - (a.gap ?? 0));
  const shownGaps = gapFilter === "below" ? ranked.filter((g) => !["on_track", "unassessed"].includes(g.status)) : ranked;
  const allSteps = data.roadmap.weeks.flatMap((w) => w.steps.map((st, i) => `${w.week}-${i}-${st.topic_id}-${st.type}`));
  const doneCount = allSteps.filter((k) => done[k]).length;
  const chart = ranked.filter((g) => g.confidence != null).map((g) => ({ label: g.name, confidence: pc(g.confidence), status: g.status }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-muted">A weekly plan built from your mastery gaps: foundations first, the biggest gaps early, sized to your hours.</p>
        <Button variant="secondary" size="sm" className="no-print" onClick={() => window.print()}><Printer className="h-4 w-4" />Print</Button>
      </div>
      <Profile key={JSON.stringify(data.profile)} id={id} data={data} />

      <div className="grid gap-4 md:grid-cols-[15rem_minmax(0,1fr)]">
        <Card className="flex items-center justify-center p-4"><Gauge value={data.readiness == null ? null : pc(data.readiness)} label="Match to your target" /></Card>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile label="Topics below target" value={lagging.length} sub={`${data.counts.critical} critical`} tone={lagging.length ? "weak" : "strong"} icon={Target} />
          <StatTile label="Not assessed" value={data.counts.unassessed} sub="no answers yet" delay={0.04} />
          <StatTile label="Plan length" value={s.weeks ? plural(s.weeks, "week") : "–"} sub={`${hours(s.total_minutes)} at ${s.hours_per_week} h/week`} icon={CalendarCheck} delay={0.08} />
          <StatTile label="Steps done" value={`${doneCount}/${allSteps.length}`} sub="ticked on this device" icon={CheckCircle2} delay={0.12} />
        </div>
      </div>

      {s.target_date && (
        <Alert tone={s.on_track ? "success" : "warning"} icon={CalendarCheck} title={s.on_track ? "On track" : "Tight schedule"}>
          {s.weeks_available === 0 ? "The target date has passed." : s.on_track ? `The plan needs ${plural(s.weeks, "week")} and you have ${plural(s.weeks_available, "week")} until ${s.target_date}.` : `The plan needs ${plural(s.weeks, "week")} but you have ${plural(s.weeks_available, "week")} until ${s.target_date}. About ${s.hours_needed} hours a week would fit.`}
        </Alert>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <Coach id={id} data={data} />
        <ChartCard title="Confidence against target" description={`Dashed line: your ${pc(data.target)}% target.`}>
          <Bars data={chart} layout="vertical" series={[{ key: "confidence", name: "Confidence" }]} domain={[0, 100]} yFmt={(v) => `${v}%`} tipFmt={(v) => `${v}%`}
            reference={{ x: pc(data.target), label: "target" }} height={Math.max(160, chart.length * 28)} catWidth={130}
            colorBy={(r) => TONE_HEX[gapOf(r.status).tone] ?? TONE_HEX.brand} />
        </ChartCard>
      </div>

      <section aria-labelledby="road-h">
        <SectionTitle id="road-h" action={<div className="flex w-48 items-center gap-2"><Progress value={allSteps.length ? (100 * doneCount) / allSteps.length : 0} /><span className="tabular text-xs text-muted">{allSteps.length ? Math.round((100 * doneCount) / allSteps.length) : 0}%</span></div>}>Week by week</SectionTitle>
        {s.weeks > s.shown_weeks && <Alert tone="info" className="mb-3">Showing the first {s.shown_weeks} of {s.weeks} weeks. The next weeks appear as you progress.</Alert>}
        <ol className="relative space-y-4 border-l-2 border-brand-soft pl-6 sm:ml-3">
          {data.roadmap.weeks.map((w) => {
            const keysW = w.steps.map((st, i) => `${w.week}-${i}-${st.topic_id}-${st.type}`);
            const complete = keysW.length > 0 && keysW.every((k) => done[k]);
            return (
              <li key={w.week} className="print-break relative">
                <span className={cn("absolute -left-[37px] top-4 grid h-7 w-7 place-items-center rounded-full border-2 border-background text-[12px] font-bold", complete ? "bg-strong text-white" : "bg-brand text-white")}>{complete ? <CheckCircle2 className="h-4 w-4" /> : w.week}</span>
                <Card className="p-5">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h3 className="font-display text-[17px] font-semibold">Week {w.week}</h3>
                    <span className="tabular text-xs text-muted">about {hours(w.minutes)}</span>
                  </div>
                  <p className="break-anywhere mt-1 text-sm">{w.goal}</p>
                  {w.focus?.length > 0 && <div className="mt-2 flex flex-wrap gap-1.5">{w.focus.map((f) => <Badge key={f} tone="neutral">{f}</Badge>)}</div>}
                  <ul className="mt-3 divide-y divide-border/70 rounded-lg border border-border">
                    {w.steps.map((step, i) => {
                      const key = keysW[i];
                      const [label, Icon] = STEP[step.type] ?? [step.type, BookOpen];
                      return (
                        <li key={key} className="flex items-center gap-3 px-3 py-2">
                          <Checkbox checked={!!done[key]} onCheckedChange={(c) => toggle(key, !!c)} aria-label={`Done: ${step.title}`} />
                          <Icon className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
                          <Link href={step.href} className={cn("break-anywhere flex-1 text-sm text-foreground no-underline hover:text-brand-deep", done[key] && "text-muted line-through")}><b className="font-semibold">{label}</b> · {step.title.replace(/^(Read: |Quiz yourself on |Flashcards for )/, "")}</Link>
                          <span className="tabular shrink-0 text-xs text-muted">{step.minutes} min</span>
                        </li>
                      );
                    })}
                  </ul>
                  <div className="mt-3 grid gap-2 text-[13px] sm:grid-cols-2">
                    <p className="flex gap-2"><Flag className="mt-0.5 h-4 w-4 shrink-0 text-brand" /><span><b>Milestone:</b> {w.milestone}</span></p>
                    {w.idea && <p className="flex gap-2"><Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-[#D08700]" /><span><b>Mini-project:</b> {w.idea}</span></p>}
                  </div>
                </Card>
              </li>
            );
          })}
        </ol>
      </section>

      <section aria-labelledby="gaps-h">
        <SectionTitle id="gaps-h" action={<Segmented label="Show" value={gapFilter} onValueChange={setGapFilter} options={[{ value: "below", label: "Below target" }, { value: "all", label: "All topics" }]} />}>Skill gaps</SectionTitle>
        <div className="grid gap-3 md:grid-cols-2">
          {shownGaps.length === 0 && <p className="text-sm text-muted">Every assessed topic is at or above target.</p>}
          {shownGaps.map((g) => {
            const st = gapOf(g.status);
            return (
              <Card key={g.topic_id} className="print-break p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="break-anywhere font-semibold">{g.name}</p>
                  {g.trend === "improving" && <span className="inline-flex items-center gap-1 text-xs text-strong"><TrendingUp className="h-3.5 w-3.5" />improving</span>}
                  {g.trend === "slipping" && <span className="inline-flex items-center gap-1 text-xs text-weak"><TrendingDown className="h-3.5 w-3.5" />slipping</span>}
                  <Badge tone={st.tone} className="ml-auto">{st.label}</Badge>
                </div>
                <div className="relative mt-3 h-2.5 rounded-full bg-brand-soft/60" role="img" aria-label={g.confidence === null ? `Not assessed. Target ${pc(g.target)}%.` : `Confidence ${pc(g.confidence)}%, target ${pc(g.target)}%.`}>
                  {g.confidence !== null && <div className="h-full rounded-full" style={{ width: `${Math.max(2, pc(g.confidence))}%`, background: TONE_HEX[st.tone] ?? TONE_HEX.brand }} />}
                  <div className="absolute -top-1 h-[18px] w-0.5 rounded bg-brand-ink" style={{ left: `${pc(g.target)}%` }} aria-hidden="true" />
                </div>
                <p className="mt-2 text-[13px] text-muted">{g.confidence === null ? "No answers yet." : <>Confidence <b className="text-foreground">{pc(g.confidence)}%</b> of {pc(g.target)}%{g.gap ? <>, gap <b className="text-foreground">{Math.round(g.gap * 100)} points</b></> : null}</>}</p>
                {g.blocked_by.length > 0 && <Alert tone="warning" icon={AlertTriangle} className="mt-2">Likely cause: <b>{g.blocked_by.map((b) => b.name).join(", ")}</b> {g.blocked_by.length === 1 ? "is" : "are"} not solid yet. The plan puts {g.blocked_by.length === 1 ? "it" : "them"} first.</Alert>}
                {g.reasons.length > 0 && <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs text-muted">{g.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
              </Card>
            );
          })}
        </div>
      </section>

      <ChartCard title="Evidence by kind of test" description="Share of answers right (or recalled, for flashcards), per topic and source. A dash means no answers of that kind.">
        <Heatmap data={data} />
      </ChartCard>
    </div>
  );
}
