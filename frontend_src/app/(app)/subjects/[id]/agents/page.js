"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, Bot, ChevronRight, Play } from "lucide-react";
import { api } from "@/lib/api";
import { getAgents, keys } from "@/lib/queries";
import { dateTime, relTime, signed, TONE_HEX } from "@/lib/format";
import { cn, friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { AgentPipeline, GraphLegend, PrereqGraph, RiskBadge, RootCauseChains } from "@/components/nexus/agents";
import { Bars, TrendLine } from "@/components/nexus/charts";
import { ErrorState, SectionTitle } from "@/components/nexus/common";
import { DataTable } from "@/components/nexus/data-table";
import { Alert, Badge, Button, Card, Skeleton } from "@/components/ui/primitives";

const LOOP = ["Observe", "Diagnose", "Predict", "Decide", "Intervene", "Verify", "Remember", "Replan"];
const TRIGGER = { quiz: "After a quiz", manual: "Run by you", first_look: "First look" };

function Detail({ step, subjectId }) {
  const d = step.details ?? {};
  if (step.status !== "done") return <p className="text-sm text-muted">{step.summary}</p>;
  switch (step.agent) {
    case "evaluator":
      return (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-2 text-center">
            {[["Answered", d.answered], ["Correct", d.correct], ["Accuracy", `${d.accuracy}%`]].map(([k, v]) => <div key={k} className="rounded-lg bg-surface-2 py-2"><p className="text-xs text-muted">{k}</p><p className="tabular font-display text-xl font-semibold">{v}</p></div>)}
          </div>
          <div><h4 className="mb-2 font-semibold">Misses traced to their root cause</h4><RootCauseChains misses={d.misses} subjectId={subjectId} limit={10} /></div>
          {d.root_causes?.length > 0 && (
            <div>
              <h4 className="mb-2 font-semibold">Root causes, ranked</h4>
              <Bars data={d.root_causes.map((r) => ({ label: r.topic, missed: r.missed }))} layout="vertical" series={[{ key: "missed", name: "Misses explained", color: TONE_HEX.weak }]} height={Math.max(100, d.root_causes.length * 34)} catWidth={130} />
            </div>
          )}
        </div>
      );
    case "analytics":
      return (
        <div className="space-y-4">
          {d.trend?.length > 1 && <TrendLine data={d.trend.map((t) => ({ label: `#${t.attempt_id}`, theta: t.theta, accuracy: Math.round(t.accuracy * 100) }))} series={[{ key: "theta", name: "Ability θ", color: "#0194E2" }]} yFmt={(v) => v.toFixed(1)} height={200} reference={{ y: 0, label: "proficient" }} />}
          {d.theta_delta != null && <p className="text-sm">Change since the previous quiz: <b className={d.theta_delta >= 0 ? "text-strong" : "text-weak"}>{signed(d.theta_delta)}</b> logits.</p>}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="mb-2 font-semibold">Concept drift</h4>
              {d.drift?.length ? <ul className="space-y-2">{d.drift.map((x) => <li key={x.topic_id} className="rounded-lg border border-border p-2.5 text-sm"><b>{x.topic}</b> <Badge tone="mid" className="ml-1">{x.state}</Badge><p className="mt-0.5 text-[12.5px] text-muted">{x.note}</p></li>)}</ul> : <p className="text-sm text-muted">No topic is drifting or fading.</p>}
              {d.growing?.length > 0 && <p className="mt-2 text-sm text-strong">Growing: {d.growing.join(", ")}</p>}
            </div>
            <div>
              <h4 className="mb-2 font-semibold">Confidence gap (felt vs measured)</h4>
              {d.confidence_gap?.length ? <ul className="space-y-2">{d.confidence_gap.map((x) => <li key={x.topic_id} className="flex items-center justify-between gap-2 rounded-lg border border-border p-2.5 text-sm"><span className="truncate font-medium">{x.topic}</span><span className="tabular text-[12.5px] text-muted">felt {Math.round(x.felt * 100)}% · measured {Math.round(x.measured * 100)}%</span></li>)}</ul> : <p className="text-sm text-muted">Your self-ratings match your results (or you have not rated topics yet on the Progress page).</p>}
            </div>
          </div>
        </div>
      );
    case "predictor":
      return (
        <div className="space-y-3">
          <Bars data={(d.topics ?? []).map((t) => ({ label: t.name, score: t.score, level: t.level }))} layout="vertical" series={[{ key: "score", name: "Risk" }]} domain={[0, 100]} height={Math.max(140, (d.topics?.length ?? 0) * 32)} catWidth={130}
            colorBy={(r) => (r.level === "high" ? TONE_HEX.weak : r.level === "medium" ? "#F2A516" : TONE_HEX.strong)} />
          <ul className="space-y-1.5 text-sm">{(d.topics ?? []).slice(0, 4).map((t) => <li key={t.topic_id}><b>{t.name}</b> <RiskBadge level={t.level} /> <span className="text-muted">{t.reasons.join("; ")}</span></li>)}</ul>
          <p className="text-xs text-muted">{d.method}</p>
        </div>
      );
    case "planner":
      return (
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h4 className="mb-2 font-semibold">Next best actions</h4>
            <ol className="space-y-2">{(d.actions ?? []).map((a, i) => (
              <li key={i} className="rounded-lg border border-border p-3 text-sm">
                <div className="flex items-center gap-2"><span className="grid h-6 w-6 place-items-center rounded-full bg-brand text-[12px] font-bold text-white">{i + 1}</span><Link href={a.href} className="flex-1 font-semibold">{a.title}</Link><Badge tone="outline">{a.minutes} min</Badge></div>
                <p className="mt-1 text-[12.5px] text-muted">{a.why.join("; ")}</p>
              </li>))}
            </ol>
          </div>
          <div>
            <h4 className="mb-2 font-semibold">Learning debt: {d.debt_hours} h</h4>
            <ul className="space-y-2">{(d.debt ?? []).map((t) => (
              <li key={t.topic_id} className="text-sm"><div className="flex justify-between gap-2"><span className="truncate font-medium">{t.name}</span><span className="tabular text-muted">{Math.round((t.own_minutes + t.interest_minutes) / 6) / 10} h</span></div>
                {t.blocks.length > 0 && <p className="text-[12px] text-muted">holds up {t.blocks.join(", ")}</p>}</li>))}
            </ul>
          </div>
        </div>
      );
    case "tutor":
      return (
        <div className="space-y-3">
          <p className="text-sm">Focus: <b>{d.focus?.topic}</b> · {d.label} · <Badge tone="neutral">{d.difficulty} difficulty</Badge></p>
          <p className="text-[13px] text-muted">{d.why}</p>
          {d.passages?.length > 0 && <div className="space-y-2">{d.passages.map((p, i) => <blockquote key={i} className="evidence rounded-r-md px-3 py-2 text-sm">{p}{p.length >= 280 ? "…" : ""}</blockquote>)}</div>}
          <Button asChild size="sm"><Link href={d.href}>Start this intervention<ArrowRight className="h-4 w-4" /></Link></Button>
        </div>
      );
    case "mentor":
      return (
        <ul className="space-y-2">{(d.goals ?? []).map((g) => (
          <li key={g.id} className="rounded-lg border border-border p-3 text-sm">
            <div className="flex items-center justify-between gap-2"><Link href={`/career/${g.id}`} className="font-semibold">{g.title}</Link><span className="tabular font-semibold text-brand-deep">{Math.round((g.readiness ?? 0) * 100)}%</span></div>
            <div className="mt-1.5 h-2 rounded-full bg-brand-soft/60"><div className="h-full rounded-full bg-brand" style={{ width: `${Math.round((g.readiness ?? 0) * 100)}%` }} /></div>
            <p className="mt-1 text-[12px] text-muted">{g.verified} of {g.total} skills verified by your answers</p>
          </li>))}
        </ul>
      );
    default:
      return <pre className="overflow-x-auto text-xs">{JSON.stringify(d, null, 2)}</pre>;
  }
}

export default function AgentsPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  useTitle("Agents");
  const [selected, setSelected] = useState("evaluator");
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.agents(id), queryFn: () => getAgents(id) });
  const run = useMutation({
    mutationFn: () => api(`/subjects/${id}/agents/run`, { method: "POST" }),
    onSuccess: (r) => { qc.setQueryData(keys.agents(id), r); toast.success("The agents ran", { description: `${r.run.steps.filter((s) => s.status === "done").length} of 6 had evidence to work with.` }); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const columns = useMemo(() => [
    { accessorKey: "id", header: "Run", cell: ({ getValue }) => <span className="tabular font-semibold">#{getValue()}</span> },
    { accessorKey: "created_at", header: "When", cell: ({ getValue }) => dateTime(getValue()) },
    { accessorKey: "trigger", header: "Trigger", cell: ({ getValue }) => <Badge tone="outline">{TRIGGER[getValue()] ?? getValue()}</Badge>, meta: { export: (r) => TRIGGER[r.trigger] ?? r.trigger } },
    { accessorKey: "attempt_id", header: "Quiz", cell: ({ getValue }) => (getValue() ? <Link href={`/subjects/${id}/quiz/${getValue()}/result`}>#{getValue()}</Link> : "–") },
    { accessorKey: "summary", header: "Summary", cell: ({ getValue }) => <span className="line-clamp-2 min-w-[20rem] text-[13px]">{getValue()}</span> },
    { accessorKey: "ms", header: "ms", meta: { align: "right" } },
  ], [id]);
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-96" />;
  const r = data.run;
  const step = r.steps.find((s) => s.agent === selected) ?? r.steps[0];
  const roots = (r.steps.find((s) => s.agent === "evaluator")?.details?.root_causes ?? []).map((x) => x.topic_id);

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-4 p-5">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-brand text-white shadow-[0_8px_20px_-8px_rgb(1_148_226/.9)]"><Bot className="h-6 w-6" /></span>
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-xl font-semibold">Agent console</h2>
            <p className="text-sm text-muted">Six agents run after every quiz. Each reads your answers, decides one thing, and records why. None of them calls a language model, so every conclusion is repeatable.</p>
          </div>
          <div className="text-right text-[12.5px] text-muted">
            <p>Last run {relTime(r.created_at)} · {TRIGGER[r.trigger] ?? r.trigger}</p>
            <p className="tabular">{r.ms} ms in total</p>
          </div>
          <Button onClick={() => run.mutate()} loading={run.isPending}><Play className="h-4 w-4" />Run the agents now</Button>
        </div>
        <ol className="flex flex-wrap items-center gap-1 border-t border-border bg-surface-2 px-5 py-3 text-[12.5px] font-semibold text-muted" aria-label="The learning loop">
          {LOOP.map((s, i) => <li key={s} className="inline-flex items-center gap-1"><span className="rounded-md bg-surface px-2 py-0.5 text-foreground ring-1 ring-border">{s}</span>{i < LOOP.length - 1 && <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />}</li>)}
        </ol>
      </Card>

      {r.steps.every((s) => s.status !== "done") && <Alert tone="info">The agents have nothing to work with yet. Upload material, generate practice questions and take a quiz.</Alert>}

      <AgentPipeline steps={r.steps} onSelect={setSelected} selected={selected} />

      <Card className="p-5">
        <SectionTitle>{step.name} agent <span className="ml-2 text-sm font-normal text-muted">{step.role}</span></SectionTitle>
        <p className="mb-4 rounded-lg bg-brand-wash px-3 py-2 text-sm">{step.summary}</p>
        <Detail step={step} subjectId={id} />
      </Card>

      <section>
        <SectionTitle>Prerequisite graph</SectionTitle>
        <Card className="p-4"><PrereqGraph graph={r.graph} highlight={roots} height={460} /><GraphLegend /><p className="mt-1 text-[12px] text-muted">Outlined in blue: the root causes the Evaluator found in the last quiz. Edit links on the Progress page.</p></Card>
      </section>

      {data.history.length > 0 && (
        <section>
          <SectionTitle>Run history</SectionTitle>
          <DataTable columns={columns} data={data.history} filename="nexus-agent-runs" title="Agent runs" searchPlaceholder="Search runs" pageSize={5} />
        </section>
      )}
    </div>
  );
}
