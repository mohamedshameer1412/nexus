"use client";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, Brain, Fingerprint, GraduationCap, History, ListChecks, Repeat, TrendingDown, TrendingUp, WandSparkles } from "lucide-react";
import { api } from "@/lib/api";
import { getExamples, getTwin, keys } from "@/lib/queries";
import { cn, friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { AbilityIntervals, Bars, ChartCard, RadarProfile } from "@/components/nexus/charts";
import { EmptyState, ErrorState, SectionTitle, StatTile } from "@/components/nexus/common";
import { Alert, Badge, Button, Card, Skeleton } from "@/components/ui/primitives";

const pc = (x) => (x === null || x === undefined ? "–" : `${Math.round(x * 100)}%`);
const KIND = { worked_example: "Worked example", flashcards: "Flashcards", revision: "Revision quiz", practice: "Practice", ask: "Ask the tutor" };
const STATUS = {
  critical: { label: "Far below target", tone: "weak", bar: "bg-weak" },
  moderate: { label: "Below target", tone: "mid", bar: "bg-mid" },
  minor: { label: "Close to target", tone: "neutral", bar: "bg-brand" },
  on_track: { label: "On track", tone: "strong", bar: "bg-strong" },
  unassessed: { label: "Not assessed yet", tone: "muted", bar: "bg-muted" },
};
const FEELING = { overconfident: ["Surer than your answers", "mid"], underconfident: ["Better than you think", "strong"], aligned: ["Feeling matches results", "strong"] };
const OUTCOME = { improved: ["Improved", "strong"], no_change: ["No change", "mid"], worse: ["Got worse", "weak"] };
const DIFF = { easy: "Start with easier questions", medium: "Mixed questions fit you", hard: "Try harder questions" };

/** A worked example for one topic, written from that topic's own passages. */
function WorkedExample({ id, topic, name, openNow }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: keys.examples(id, topic), queryFn: () => getExamples(id, topic),
    refetchInterval: (s) => (s.state.data?.[0]?.status === "pending" ? 3000 : false),
  });
  const make = useMutation({
    mutationFn: () => api(`/subjects/${id}/examples`, { method: "POST", json: { topic_id: topic } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.examples(id, topic) }); qc.invalidateQueries({ queryKey: keys.twin(id) }); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const latest = q.data?.[0];
  const pending = latest?.status === "pending" || make.isPending;
  return (
    <details className="mt-3 rounded-lg border border-border bg-surface-2/60 p-3" open={openNow || undefined}>
      <summary className="cursor-pointer text-sm font-semibold text-brand-deep"><WandSparkles className="mr-1 inline h-4 w-4" aria-hidden="true" /> Worked example for {name}</summary>
      <div className="mt-3 space-y-3" aria-live="polite">
        {pending && <p role="status" className="flex items-center gap-2 text-sm text-muted"><span className="typing-dots" aria-hidden="true"><i /><i /><i /></span> Writing an example from your material…</p>}
        {!pending && latest?.status === "failed" && <Alert tone="danger">The example could not be written. Try again.</Alert>}
        {!pending && latest?.status === "done" && latest.example && (
          <div>
            <p className="break-anywhere font-semibold">{latest.example.problem}</p>
            <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm">
              {latest.example.steps.map((s, i) => (
                <li key={i} className="break-anywhere">{s.text}<br /><span className="evidence mt-1 block rounded-r px-2 py-1 text-xs text-muted">“{s.quote}”</span></li>
              ))}
            </ol>
            {latest.example.answer && <p className="break-anywhere mt-2 text-sm"><b>Result:</b> {latest.example.answer}</p>}
            {latest.example.check && <p className="break-anywhere mt-2 text-sm"><b>Now you try:</b> {latest.example.check}</p>}
            <p className="mt-2 text-xs text-muted">{latest.example.from_model ? `Written by ${latest.model} from this topic's passages only; every step quotes them.` : "No model answered, so these are the topic's own key passages to work through."}</p>
          </div>
        )}
        <Button size="sm" variant="subtle" disabled={pending} onClick={() => make.mutate()}>{latest ? "Write another example" : "Write a worked example"}</Button>
      </div>
    </details>
  );
}

function Planner({ id, data }) {
  if (data.next.length === 0) return <Alert tone="success">Nothing is below your target right now. Keep it that way with a short quiz each week.</Alert>;
  return (
    <ol className="space-y-3">
      {data.next.map((n, i) => (
        <li key={n.topic_id}>
          <Card className="p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-brand text-sm font-bold text-white" aria-hidden="true">{i + 1}</span>
              <p className="break-anywhere font-semibold">{n.title}</p>
              <Badge tone="outline" className="ml-auto">{n.minutes} min</Badge>
              {!n.fits_this_week && <Badge tone="mid">Not this week</Badge>}
            </div>
            <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-muted">{n.why.map((w, k) => <li key={k} className="break-anywhere">{w}</li>)}</ul>
            <p className="mt-2 text-xs text-muted">Level: {DIFF[n.difficulty]}. {n.difficulty_why}</p>
            <div className="mt-3">
              {n.kind === "worked_example" ? <Button size="sm" asChild><a href={`#topic-${n.topic_id}`}>Open the worked example <ArrowRight className="h-4 w-4" aria-hidden="true" /></a></Button>
                : <Button size="sm" asChild><Link href={n.href}>Go <ArrowRight className="h-4 w-4" aria-hidden="true" /></Link></Button>}
            </div>
          </Card>
        </li>
      ))}
    </ol>
  );
}

function TopicCard({ id, t, openExample }) {
  const st = STATUS[t.status];
  const f = FEELING[t.feeling];
  const loop = t.loop;
  return (
    <li id={`topic-${t.topic_id}`} className="scroll-mt-20">
      <Card className="h-full p-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-anywhere font-semibold">{t.subtopic ? `${t.unit} › ${t.subtopic}` : t.name}</p>
          {t.trend === "improving" && <span className="inline-flex items-center gap-1 text-xs text-strong"><TrendingUp className="h-4 w-4" aria-hidden="true" /> improving</span>}
          {t.trend === "slipping" && <span className="inline-flex items-center gap-1 text-xs text-weak"><TrendingDown className="h-4 w-4" aria-hidden="true" /> slipping</span>}
          <Badge tone={st.tone} className="ml-auto">{st.label}</Badge>
        </div>
        <div className="mt-3 h-2 rounded-full bg-brand-soft/60" role="img" aria-label={t.confidence === null ? "Not assessed" : `Confidence ${pc(t.confidence)}`}>
          {t.confidence !== null && <div className={cn("h-full rounded-full", st.bar)} style={{ width: `${Math.round(t.confidence * 100)}%` }} />}
        </div>
        <p className="mt-2 text-sm text-muted">
          {t.confidence === null ? "No answers yet." : <>Confidence <b>{pc(t.confidence)}</b> · ability {t.theta > 0 ? "+" : ""}{t.theta} (± {t.se}) · {t.answered} answer{t.answered === 1 ? "" : "s"}</>}
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {f && <Badge tone={f[1]}>{f[0]}</Badge>}
          {t.exam_count > 0 && <Badge tone="mid">Asked {t.exam_count}× in past papers</Badge>}
          {t.blocked_by.length > 0 && <Badge tone="mid">Builds on {t.blocked_by.join(", ")}</Badge>}
          {t.answered >= 3 && <Badge tone="outline">{DIFF[t.difficulty]}</Badge>}
        </div>
        {t.drift_note && <p className="mt-2 text-xs text-muted">{t.drift_note}</p>}
        {loop.tries > 0 && (
          <p className="mt-2 text-xs">
            <Repeat className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" />
            {loop.state === "improved"
              ? <>Last action (<b>{KIND[loop.last_kind]}</b>) was followed by an improvement of {Math.round(loop.change * 100)} points.</>
              : <>Last action (<b>{KIND[loop.last_kind]}</b>) did not raise this topic ({OUTCOME[loop.last_outcome]?.[0].toLowerCase()}), so the planner is changing the approach.</>}
          </p>
        )}
        {(t.gap || t.status === "unassessed") && <WorkedExample id={id} topic={t.topic_id} name={t.name} openNow={openExample === t.topic_id} />}
      </Card>
    </li>
  );
}

function Inner() {
  const { id } = useParams();
  const params = useSearchParams();
  useTitle("My twin");
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.twin(id), queryFn: () => getTwin(id) });
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-64" />;
  if (data.topics.length === 0) {
    return <EmptyState title="Your twin starts with your materials" action={<Button asChild><Link href={`/subjects/${id}/materials`}>Add materials</Link></Button>}>Upload a syllabus or notes, then answer a few questions, and this page becomes a picture of what you know.</EmptyState>;
  }
  const p = data.profile;
  const open = Number(params.get("topic")) || null;
  const units = [...new Set(data.topics.map((t) => t.unit))];
  const radar = data.units.filter((u) => u.confidence != null).map((u) => ({ name: u.unit.length > 18 ? `${u.unit.slice(0, 17)}…` : u.unit, value: Math.round(u.confidence * 100) }));
  const radarTopics = radar.length >= 3 ? radar : data.topics.filter((t) => t.confidence != null).slice(0, 10).map((t) => ({ name: t.name.length > 16 ? `${t.name.slice(0, 15)}…` : t.name, value: Math.round(t.confidence * 100) }));
  const LEVELS = { new: "New learner", intermediate: "Intermediate", professional: "Professional" };
  return (
    <div className="space-y-6">
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-4 bg-gradient-to-r from-brand to-[#0B7FC4] px-5 py-4 text-white">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-white/15 ring-1 ring-white/30"><Fingerprint className="h-6 w-6" /></span>
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-xl font-semibold">Learner twin</h2>
            <p className="text-sm text-white/85">One picture of you in {data.subject}, built only from what you have done.</p>
          </div>
        </div>
        <dl className="grid grid-cols-2 gap-4 px-5 py-4 text-sm sm:grid-cols-4">
          <div><dt className="text-xs text-muted">Level</dt><dd className="font-semibold">{p.level ? LEVELS[p.level] : "Not chosen"}</dd></div>
          <div><dt className="text-xs text-muted">Studying</dt><dd className="font-semibold">{p.department || "–"}{p.semester ? `, semester ${p.semester}` : ""}</dd></div>
          <div><dt className="text-xs text-muted">Time</dt><dd className="font-semibold">{p.hours_per_week} h a week</dd></div>
          <div><dt className="text-xs text-muted">Exam or deadline</dt><dd className="font-semibold">{p.exam_date ?? p.target_date ?? "–"}</dd></div>
          {p.goal && <div className="col-span-2 sm:col-span-4"><dt className="text-xs text-muted">Goal</dt><dd className="break-anywhere font-semibold">{p.goal}</dd></div>}
        </dl>
      </Card>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Match to target" value={pc(data.readiness)} sub={`target ${pc(data.target)} per topic`} />
        <StatTile label="Overall ability θ" value={data.overall ? `${data.overall.theta > 0 ? "+" : ""}${data.overall.theta.toFixed(2)}` : "–"} sub={data.overall ? `± ${data.overall.se.toFixed(2)}, ${data.overall.answered} answers` : "no answers yet"} delay={0.04} />
        <StatTile label="Strong topics" value={data.strengths.length} sub={data.strengths.slice(0, 2).join(", ") || "none yet"} tone="strong" delay={0.08} />
        <StatTile label="Needs work" value={data.weaknesses.length} sub={data.weaknesses.slice(0, 2).join(", ") || "none"} tone={data.weaknesses.length ? "weak" : undefined} delay={0.12} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <ChartCard title="Mastery profile" description={radar.length >= 3 ? "Average confidence per unit." : "Confidence per topic."} icon={Brain}><RadarProfile data={radarTopics} height={300} /></ChartCard>
        <ChartCard title="Ability with uncertainty" description="The twin's estimate for each topic, and how sure it is."><AbilityIntervals items={data.topics.map((t) => ({ ...t }))} target={data.target} /></ChartCard>
      </div>

      <section aria-labelledby="plan-h">
        <SectionTitle id="plan-h"><span className="inline-flex items-center gap-2"><ListChecks className="h-5 w-5 text-brand" />Next best actions</span></SectionTitle>
        <p className="-mt-2 mb-3 max-w-3xl text-sm text-muted">Ranked by distance below target, how often past papers ask about a topic, slipping trends and your deadline. If a topic builds on a weak one, the planner aims at the cause; if an action did not help last time, it tries another.</p>
        <Planner id={id} data={data} />
      </section>

      <section aria-labelledby="topics-h">
        <SectionTitle id="topics-h">Topic by topic</SectionTitle>
        {units.map((u) => (
          <div key={u} className="mb-5">
            {units.length > 1 && <h3 className="mb-2 font-semibold text-muted">{u}</h3>}
            <ul className="grid gap-3 lg:grid-cols-2">{data.topics.filter((t) => t.unit === u).map((t) => <TopicCard key={t.topic_id} id={id} t={t} openExample={open} />)}</ul>
          </div>
        ))}
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">How you go wrong</h2>
          <p className="mt-0.5 text-sm text-muted">{data.patterns.method}</p>
          {data.patterns.patterns.length === 0 ? <p className="mt-3 text-sm text-muted">No repeated pattern yet ({data.patterns.answers} answers so far).</p> : (
            <ul className="mt-3 space-y-2">{data.patterns.patterns.map((pt, i) => <li key={i} className="rounded-lg border border-border p-3"><p className="font-semibold">{pt.title}{pt.topic ? ` · ${pt.topic}` : ""}</p><p className="mt-0.5 text-sm text-muted">{pt.detail}</p></li>)}</ul>
          )}
        </Card>
        <Card className="p-5">
          <h2 className="flex items-center gap-2 font-display text-lg font-semibold"><History className="h-5 w-5 text-brand" />What has worked for you</h2>
          {data.memory.length === 0 ? (
            <p className="mt-2 text-sm text-muted">Nexus notes each study action on a weak topic, then checks after three or more new answers whether the topic improved. Nothing has been checked yet.</p>
          ) : (
            <Bars data={data.memory.map((m) => ({ label: m.label, change: Math.round(m.mean_change * 100), tried: m.tried }))} layout="vertical" series={[{ key: "change", name: "Average change (points)" }]}
              height={Math.max(120, data.memory.length * 38)} catWidth={130} colorBy={(r) => (r.change > 0 ? "#0E8A5F" : "#D9463B")} />
          )}
          {data.history.length > 0 && (
            <ul className="mt-3 divide-y divide-border text-sm">
              {data.history.map((h) => (
                <li key={h.id} className="flex flex-wrap items-center gap-2 py-2">
                  <span className="break-anywhere flex-1">{KIND[h.kind]} · <b>{h.topic}</b></span>
                  {h.outcome ? <Badge tone={OUTCOME[h.outcome][1]}>{OUTCOME[h.outcome][0]}</Badge> : <Badge tone="outline">{h.status === "pending" ? "Writing…" : "Waiting for 3 new answers"}</Badge>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="no-print flex flex-wrap gap-2">
        <Button asChild><Link href={`/subjects/${id}/quiz`}><GraduationCap className="h-4 w-4" />Take a quiz</Link></Button>
        <Button asChild variant="secondary"><Link href={`/subjects/${id}/agents`}>See what the agents decided</Link></Button>
      </div>
    </div>
  );
}

export default function TwinPage() {
  return <Suspense fallback={<Skeleton className="h-64" />}><Inner /></Suspense>;
}
