"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Bot, CheckCircle2, CornerDownLeft, Download, RotateCcw, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { getAgents, getResult, keys } from "@/lib/queries";
import { TONE_HEX } from "@/lib/format";
import { cn, plural } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { AgentPipeline, RootCauseChains } from "@/components/nexus/agents";
import { Bars, Gauge } from "@/components/nexus/charts";
import { ErrorState, SectionTitle } from "@/components/nexus/common";
import { Alert, Badge, Button, Card, CardBody, CardHeader, Segmented, Skeleton } from "@/components/ui/primitives";

const LEVEL = { new: "New learner", intermediate: "Intermediate", professional: "Professional" };
const pc = (x) => Math.round(x * 100);
const EVENT_LABELS = { tab_switch: "Tab switches", full_screen_exit: "Left full screen", copy_attempt: "Copy attempts blocked", paste_attempt: "Paste attempts blocked" };

function DiagnosisCard({ d, subjectId }) {
  const qc = useQueryClient();
  const accept = useMutation({
    mutationFn: () => api(`/subjects/${subjectId}/level`, { method: "PUT", json: { level: d.suggested } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.subject(subjectId) }); toast.success(`Your level is now ${LEVEL[d.suggested]}`); },
  });
  return (
    <Card className="border-brand/40 p-5">
      <h2 className="font-display text-lg font-semibold">Diagnostic conclusion</h2>
      {d.suggested ? <p className="mt-2 flex flex-wrap items-center gap-2 text-sm">Suggested level <Badge tone="brand">{LEVEL[d.suggested]}</Badge><span className="text-muted">overall confidence <b className="text-foreground">{pc(d.confidence)}%</b></span></p>
        : <p className="mt-2 text-sm text-muted">Too few answers to suggest a level.</p>}
      {d.note && <p className="mt-1 text-sm">{d.note}</p>}
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        {["easy", "medium", "hard"].map((k) => <div key={k} className="rounded-lg bg-surface-2 p-2.5"><p className="text-xs capitalize text-muted">{k}</p><p className="tabular font-display text-lg font-semibold">{d.by_difficulty[k].correct}/{d.by_difficulty[k].answered}</p></div>)}
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 text-sm">
        <div><h3 className="font-semibold text-strong">Looks strong</h3>{d.strongest.length === 0 ? <p className="text-muted">No topic stands out yet.</p> : <ul className="mt-1 space-y-1">{d.strongest.map((t) => <li key={t.topic_id}>{t.name} <span className="text-muted">({pc(t.confidence)}%)</span></li>)}</ul>}</div>
        <div><h3 className="font-semibold text-weak">Start here</h3>{d.weakest.length === 0 ? <p className="text-muted">Nothing to flag.</p> : <ul className="mt-1 space-y-1">{d.weakest.map((t) => <li key={t.topic_id}>{t.name} <span className="text-muted">({pc(t.confidence)}%)</span></li>)}</ul>}</div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {d.suggested && d.suggested !== d.claimed && <Button size="sm" onClick={() => accept.mutate()} loading={accept.isPending}>Use {LEVEL[d.suggested]} as my level</Button>}
        <Button asChild size="sm" variant="secondary"><Link href={`/subjects/${subjectId}/progress`}>Confidence by topic</Link></Button>
      </div>
    </Card>
  );
}

export default function ResultPage() {
  const { id, aid } = useParams();
  useTitle("Quiz result");
  const [show, setShow] = useState("all");
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.result(id, aid), queryFn: () => getResult(id, aid) });
  const agents = useQuery({ queryKey: [...keys.agents(id), "attempt", aid], queryFn: () => getAgents(id, aid), enabled: !!data });
  const byTopic = useMemo(() => {
    const m = new Map();
    for (const x of data?.answers ?? []) { const k = x.topic?.split(" › ").pop() || "Other"; const v = m.get(k) ?? { label: k, correct: 0, wrong: 0 }; x.correct ? v.correct++ : v.wrong++; m.set(k, v); }
    return [...m.values()].sort((a, b) => (b.correct + b.wrong) - (a.correct + a.wrong));
  }, [data]);
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-96" />;
  const { attempt: a } = data;
  const total = a.correct + a.incorrect;
  const pct = total ? Math.round((100 * a.correct) / total) : 0;
  const events = Object.entries(data.focus_events).filter(([, n]) => n > 0);
  const answers = data.answers.filter((x) => show === "all" || (show === "wrong" ? !x.correct : x.backtrack));
  const run = agents.data?.run;
  const ev = run?.steps.find((s) => s.agent === "evaluator");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-semibold">Quiz #{a.id} result</h2>
          <p className="text-sm text-muted">{a.mode === "assessment" ? "Scored assessment" : "Practice quiz"}{a.kind !== "standard" ? `, ${a.kind}` : ""}. {plural(total, "answer")}{data.skipped ? `, ${data.skipped} skipped` : ""}.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="secondary" size="sm"><a href={`/api/v1/subjects/${id}/quiz/attempts/${aid}/report.pdf`} download className="no-underline"><Download className="h-4 w-4" />PDF</a></Button>
          <Button asChild size="sm"><Link href={`/subjects/${id}/quiz`}><RotateCcw className="h-4 w-4" />Another quiz</Link></Button>
        </div>
      </div>
      {data.ended_reason && <Alert tone="warning" title="This assessment ended early">{data.ended_reason}. Questions you had not answered were not counted.</Alert>}
      {data.diagnosis && <DiagnosisCard d={data.diagnosis} subjectId={id} />}

      <div className="grid gap-5 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <Card className="flex flex-col items-center justify-center p-5">
          <Gauge value={pct} label={`${a.correct} of ${total} correct`} size={200} />
          <div className="mt-4 grid w-full grid-cols-2 gap-2 text-center">
            <div className="rounded-lg bg-strong-bg p-2"><p className="text-xs text-strong">Correct</p><p className="tabular font-display text-xl font-semibold text-strong">{a.correct}</p></div>
            <div className="rounded-lg bg-weak-bg p-2"><p className="text-xs text-weak">Wrong</p><p className="tabular font-display text-xl font-semibold text-weak">{a.incorrect}</p></div>
          </div>
          {events.length > 0 && <div className="mt-3 flex flex-wrap justify-center gap-1.5">{events.map(([k, n]) => <Badge key={k} tone="mid">{EVENT_LABELS[k]}: {n}</Badge>)}</div>}
        </Card>
        <Card>
          <CardHeader title="By topic" description="Correct and wrong answers in this quiz." />
          <CardBody>
            <Bars data={byTopic} layout="vertical" stacked series={[{ key: "correct", name: "Correct", color: TONE_HEX.strong }, { key: "wrong", name: "Wrong", color: TONE_HEX.weak }]}
              height={Math.max(140, byTopic.length * 34)} catWidth={130} />
          </CardBody>
        </Card>
      </div>

      <Card className="p-5">
        <SectionTitle action={<Button asChild variant="ghost" size="sm"><Link href={`/subjects/${id}/agents`}><Bot className="h-4 w-4" />Agent console</Link></Button>}>What the agents concluded</SectionTitle>
        {agents.isPending ? <Skeleton className="h-40" /> : !run ? <p className="text-sm text-muted">The agents could not run for this quiz.</p> : (
          <div className="space-y-5">
            <AgentPipeline steps={run.steps} compact />
            <div>
              <h3 className="mb-2 font-semibold">Root causes of your misses</h3>
              <RootCauseChains misses={ev?.details?.misses} subjectId={id} />
            </div>
          </div>
        )}
      </Card>

      <section aria-labelledby="break-h">
        <SectionTitle id="break-h" action={<Segmented label="Show" value={show} onValueChange={setShow} options={[{ value: "all", label: "All" }, { value: "wrong", label: "Wrong" }, { value: "back", label: "Step-backs" }]} />}>Question by question</SectionTitle>
        <ol className="space-y-3">
          {answers.length === 0 && <li className="text-sm text-muted">Nothing to show for this filter.</li>}
          {answers.map((x, i) => (
            <li key={i}>
              <Card className={cn("border-l-4 p-4", x.correct ? "border-l-strong" : "border-l-weak")}>
                <div className="flex items-start gap-3">
                  {x.correct ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-strong" /> : <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-weak" />}
                  <div className="min-w-0 flex-1">
                    <p className="break-anywhere font-semibold">{x.question}</p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">{x.topic?.split(" › ").pop()}{x.backtrack && <Badge tone="neutral"><CornerDownLeft className="h-3 w-3" />step back to basics</Badge>}</p>
                    <p className={cn("break-anywhere mt-2 text-sm", x.correct ? "text-strong" : "text-weak")}>You chose <b>{String.fromCharCode(65 + x.chosen_index)}</b>: {x.options[x.chosen_index]}</p>
                    {!x.correct && <p className="break-anywhere mt-1 text-sm">Right answer <b>{String.fromCharCode(65 + x.answer_index)}</b>: {x.options[x.answer_index]}</p>}
                    {x.explanation && <p className="break-anywhere mt-2 rounded-md bg-surface-2 px-3 py-2 text-sm text-muted">{x.explanation}</p>}
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
