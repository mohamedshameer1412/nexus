"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, FlaskConical, Gauge as GaugeIcon, Scale, Telescope, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { WhatIf } from "@/lib/schemas";
import { getOutlook, keys } from "@/lib/queries";
import { RISK } from "@/lib/format";
import { cn, friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { Bars, ChartCard, Gauge, TrendLine } from "@/components/nexus/charts";
import { EmptyState, ErrorState, SectionTitle, StatTile } from "@/components/nexus/common";
import { Alert, Badge, Button, Card, Checkbox, Field, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from "@/components/ui/primitives";

const pc = (x) => (x === null || x === undefined ? "–" : `${Math.round(x * 100)}%`);
const hrs = (m) => `${Math.round((m / 60) * 10) / 10} h`;
const HORIZON = [1, 2, 3, 4, 6, 8, 12];

/** Where your match to target lands after N weeks at the current pace (the same formula as the what-if, run for several horizons). */
function Projection({ id, data }) {
  const h = data.profile.hours_per_week;
  const q = useQuery({
    queryKey: ["projection", id, h],
    queryFn: async () => Promise.all(HORIZON.map(async (w) => {
      const r = WhatIf.parse(await api(`/subjects/${id}/whatif`, { method: "POST", json: { hours_per_week: h, weeks: w, focus: [] } }));
      return { label: `${w} wk`, weeks: w, after: r.scenario.readiness_after == null ? null : Math.round(r.scenario.readiness_after * 100), covered: r.scenario.covered, lagging: r.scenario.lagging };
    })),
    staleTime: 60_000,
  });
  const now = data.readiness == null ? null : Math.round(data.readiness * 100);
  const rows = q.data ? [{ label: "Now", weeks: 0, after: now }, ...q.data] : [];
  const reach = q.data?.find((r) => r.after != null && r.after >= 100);
  return (
    <ChartCard title="Projected match to target" description={`If you keep studying ${h} h a week and follow the roadmap order.`} icon={Telescope}>
      {q.isPending ? <Skeleton className="h-60" /> : q.error ? <Alert tone="danger">{friendlyError(q.error)}</Alert> : now == null ? (
        <p className="text-sm text-muted">Take a quiz first: a projection needs a starting point.</p>
      ) : (
        <>
          <TrendLine data={rows} x="label" series={[{ key: "after", name: "Match to target %", color: "#0194E2" }]} yDomain={[0, 100]} yFmt={(v) => `${v}%`} reference={{ y: 100, label: "all topics at target" }} height={240} />
          <p className="mt-2 text-sm">{reach ? <>At this pace every assessed topic reaches target in about <b>{reach.weeks} week{reach.weeks === 1 ? "" : "s"}</b>.</> : <>Even after 12 weeks some topics stay below target at {h} h a week. Try more hours in the what-if below.</>}</p>
          <p className="mt-1 text-xs text-muted">A formula, not a prediction of a grade: finishing a topic&apos;s planned steps is assumed to close 70% of its gap.</p>
        </>
      )}
    </ChartCard>
  );
}

function Compare({ label, sim, highlight }) {
  return (
    <Card className={cn("p-4", highlight && "border-brand shadow-[0_0_0_3px_rgb(1_148_226/.12)]")}>
      <p className="font-semibold">{label}</p>
      <p className="mt-0.5 text-xs text-muted">{sim.hours_per_week} h a week for {sim.weeks} {sim.weeks === 1 ? "week" : "weeks"} = {hrs(sim.budget_minutes)}</p>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
        {[["Match to target", pc(sim.readiness_after)], ["Topics planned", `${sim.covered}/${sim.lagging}`], ["Weeks to finish", sim.weeks_to_finish]].map(([k, v]) => (
          <div key={k} className="rounded-lg bg-surface-2 py-2"><dt className="text-[11.5px] text-muted">{k}</dt><dd className="tabular font-display text-xl font-semibold">{v}</dd></div>
        ))}
      </dl>
    </Card>
  );
}

function Simulator({ id, data }) {
  const [hours, setHours] = useState(String(data.profile.hours_per_week));
  const [weeks, setWeeks] = useState(String(Math.min(data.profile.weeks, 26)));
  const [focus, setFocus] = useState([]);
  const run = useMutation({
    mutationFn: async () => WhatIf.parse(await api(`/subjects/${id}/whatif`, { method: "POST", json: { hours_per_week: Number(hours), weeks: Number(weeks), focus } })),
    onError: (e) => toast.error(friendlyError(e)),
  });
  const lagging = data.topics.filter((t) => ["critical", "moderate", "minor"].includes(t.status));
  const toggle = (tid, on) => setFocus((f) => (on ? [...f, tid].slice(0, 10) : f.filter((x) => x !== tid)));
  const r = run.data;
  const rows = r ? r.scenario.topics.map((t) => { const b = r.baseline.topics.find((x) => x.topic_id === t.topic_id); return { label: t.name, now: t.now == null ? null : Math.round(t.now * 100), plan: b?.after == null ? null : Math.round(b.after * 100), whatif: t.after == null ? null : Math.round(t.after * 100) }; }).filter((x) => x.now != null) : [];
  return (
    <section aria-labelledby="sim-h">
      <SectionTitle id="sim-h"><span className="inline-flex items-center gap-2"><FlaskConical className="h-5 w-5 text-brand" />What if…?</span></SectionTitle>
      <p className="-mt-2 mb-3 text-sm text-muted">Try a different plan and compare it with your current one before you commit. Nothing here is saved.</p>
      <Card className="p-5">
        <form className="grid gap-3 sm:grid-cols-[10rem_10rem_auto] sm:items-end" onSubmit={(e) => { e.preventDefault(); run.mutate(); }}>
          <Field label="Hours per week" htmlFor="wi-hours">
            <Select value={hours} onValueChange={setHours}><SelectTrigger id="wi-hours"><SelectValue /></SelectTrigger>
              <SelectContent>{[...new Set([1, 2, 3, 5, 8, 12, 20, 30, Number(data.profile.hours_per_week)])].sort((a, b) => a - b).map((h) => <SelectItem key={h} value={String(h)}>{h} {h === 1 ? "hour" : "hours"}</SelectItem>)}</SelectContent></Select>
          </Field>
          <Field label="For how many weeks" htmlFor="wi-weeks">
            <Select value={weeks} onValueChange={setWeeks}><SelectTrigger id="wi-weeks"><SelectValue /></SelectTrigger>
              <SelectContent>{[...new Set([1, 2, 3, 4, 6, 8, 12, 16, 26, Math.min(data.profile.weeks, 26)])].sort((a, b) => a - b).map((w) => <SelectItem key={w} value={String(w)}>{w} {w === 1 ? "week" : "weeks"}</SelectItem>)}</SelectContent></Select>
          </Field>
          <Button type="submit" loading={run.isPending}>Compare plans</Button>
        </form>
        {lagging.length > 0 && (
          <fieldset className="mt-4">
            <legend className="text-[13px] font-semibold">Study these first (optional, up to 10)</legend>
            <ul className="mt-2 flex flex-wrap gap-2">
              {lagging.map((t) => (
                <li key={t.topic_id}>
                  <label className={cn("flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-sm", focus.includes(t.topic_id) ? "border-brand bg-brand-wash" : "border-border hover:bg-brand-wash/60")}>
                    <Checkbox checked={focus.includes(t.topic_id)} onCheckedChange={(c) => toggle(t.topic_id, !!c)} />{t.name}
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
        )}
      </Card>
      {r && (
        <div className="mt-4 space-y-4" aria-live="polite">
          <div className="grid gap-3 md:grid-cols-2"><Compare label="Your current plan" sim={r.baseline} /><Compare label="This what-if" sim={r.scenario} highlight /></div>
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
            <ChartCard title="Confidence per topic" description="Now, after the current plan, after this what-if.">
              <Bars data={rows} series={[{ key: "now", name: "Now", color: "#C7D6E4" }, { key: "plan", name: "Current plan", color: "#64748B" }, { key: "whatif", name: "What-if", color: "#0194E2" }]} domain={[0, 100]} yFmt={(v) => `${v}%`} tipFmt={(v) => `${v}%`} height={260} />
            </ChartCard>
            <Card className="p-5">
              <h3 className="font-display text-[16px] font-semibold">Why it changes</h3>
              <ul className="mt-2 space-y-2 text-sm">{r.why.map((w, i) => <li key={i} className="flex gap-2"><ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-brand" />{w}</li>)}</ul>
              <p className="mt-3 text-xs text-muted">{r.assumption}</p>
            </Card>
          </div>
        </div>
      )}
    </section>
  );
}

export default function OutlookPage() {
  const { id } = useParams();
  useTitle("Outlook");
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.outlook(id), queryFn: () => getOutlook(id) });
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-96" />;
  if (data.topics.length === 0) return <EmptyState title="Nothing to look ahead at yet" action={<Button asChild><Link href={`/subjects/${id}/materials`}>Add materials</Link></Button>}>The outlook is built from your topics and the answers you give.</EmptyState>;
  const s = data.risk.summary;
  const d = data.debt;
  const maxMin = Math.max(...d.topics.map((t) => t.own_minutes + t.interest_minutes), 1);
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-[15rem_minmax(0,1fr)]">
        <Card className="flex flex-col items-center justify-center p-4">
          <Gauge value={s.score} label="Risk of missing your target" suffix="" tone={s.level === "high" ? "weak" : s.level === "medium" ? "mid" : s.level === "low" ? "strong" : "muted"} />
          <Badge tone={RISK[s.level]?.tone} className="mt-2">{RISK[s.level]?.label} risk</Badge>
        </Card>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile label="Learning debt" value={`${d.total_hours} h`} sub="study time owed below target" icon={Scale} />
          <StatTile label="High-risk topics" value={s.high} sub={`${s.medium} medium`} tone={s.high ? "weak" : undefined} icon={GaugeIcon} delay={0.04} />
          <StatTile label="Match to target" value={pc(data.readiness)} sub={`target ${pc(data.target)} per topic`} icon={TrendingUp} delay={0.08} />
          <StatTile label="Not assessed" value={s.unassessed} sub="risk cannot be judged" delay={0.12} />
        </div>
      </div>
      {s.late && <Alert tone="warning" title="The plan does not fit your date">At {s.hours_per_week} hours a week it runs past your target date{s.hours_needed ? `. About ${s.hours_needed} hours a week would fit.` : "."}</Alert>}

      <div className="grid gap-5 xl:grid-cols-2">
        <Projection id={id} data={data} />
        <ChartCard title="Risk by topic" description="0 to 100. The reasons for each score are listed below." icon={GaugeIcon}>
          <Bars data={data.risk.topics.filter((t) => t.score != null).map((t) => ({ label: t.name, score: t.score, level: t.level }))} layout="vertical" series={[{ key: "score", name: "Risk" }]}
            domain={[0, 100]} height={Math.max(180, data.risk.topics.filter((t) => t.score != null).length * 28)} catWidth={130}
            colorBy={(r) => (r.level === "high" ? "#D9463B" : r.level === "medium" ? "#F2A516" : "#0E8A5F")} />
          <p className="mt-2 text-xs text-muted">{data.risk.method}</p>
        </ChartCard>
      </div>

      <section aria-labelledby="debt-h">
        <SectionTitle id="debt-h"><span className="inline-flex items-center gap-2"><Scale className="h-5 w-5 text-brand" />Learning debt</span></SectionTitle>
        {d.topics.length === 0 ? <Alert tone="success">No topic is below your target right now, so you owe no study time.</Alert> : (
          <Card className="p-5">
            <p className="mb-4 text-sm text-muted">{d.method}</p>
            <ul className="space-y-3">
              {d.topics.map((t) => (
                <li key={t.topic_id}>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-semibold">{t.name}</span>
                    {t.repay_first && <Badge tone="weak">Repay first</Badge>}
                    <span className="tabular ml-auto text-muted">{hrs(t.own_minutes)}{t.interest_minutes ? ` + ${hrs(t.interest_minutes)} interest` : ""}</span>
                  </div>
                  <div className="mt-1.5 flex h-3 overflow-hidden rounded-full bg-brand-soft/60" role="img" aria-label={`${hrs(t.own_minutes)} owed, ${hrs(t.interest_minutes)} interest`}>
                    <div className="h-full bg-brand" style={{ width: `${(t.own_minutes / maxMin) * 100}%` }} />
                    <div className="h-full bg-[#F2A516]" style={{ width: `${(t.interest_minutes / maxMin) * 100}%` }} />
                  </div>
                  {t.blocks.length > 0 && <p className="mt-1 text-[12.5px] text-muted">Holds up {t.blocks.join(", ")}</p>}
                </li>
              ))}
            </ul>
            <p className="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted">
              <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-brand" />own time</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-[#F2A516]" />interest from topics that build on it</span>
              <Link href={`/subjects/${id}/roadmap`} className="font-semibold">See the weekly plan</Link>
            </p>
          </Card>
        )}
      </section>

      <section aria-labelledby="risk-h">
        <SectionTitle id="risk-h">Why each topic is at risk</SectionTitle>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.risk.topics.map((t) => (
            <Card key={t.topic_id} className="p-4">
              <div className="flex items-center gap-2"><p className="truncate font-semibold">{t.name}</p><Badge tone={RISK[t.level]?.tone ?? "muted"} className="ml-auto">{t.score == null ? "Unknown" : `${t.score}`}</Badge></div>
              <ul className="mt-2 list-disc space-y-0.5 pl-5 text-[12.5px] text-muted">{t.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>
            </Card>
          ))}
        </div>
      </section>

      <Simulator id={id} data={data} />
    </div>
  );
}
