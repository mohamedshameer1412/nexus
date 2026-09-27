"use client";
import { useParams } from "next/navigation";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileSpreadsheet, FileText, Printer } from "lucide-react";
import { getReport, keys } from "@/lib/queries";
import { dateTime, masteryOf, TONE_HEX } from "@/lib/format";
import { useTitle } from "@/lib/use-title";
import { Bars, ChartCard, TrendLine } from "@/components/nexus/charts";
import { ErrorState, SectionTitle, StatTile } from "@/components/nexus/common";
import { CellBar, DataTable } from "@/components/nexus/data-table";
import { Badge, Button, Card, Skeleton } from "@/components/ui/primitives";

const pct = (x) => Math.round(x * 100);

export default function ReportPage() {
  const { id } = useParams();
  useTitle("Report");
  const { data: r, error, isPending, refetch } = useQuery({ queryKey: keys.report(id), queryFn: () => getReport(id) });
  const topicCols = useMemo(() => [
    { accessorKey: "name", header: "Topic", cell: ({ getValue }) => <span className="font-medium">{getValue()}</span> },
    { accessorKey: "answered", header: "Answered", meta: { align: "right" } },
    { accessorKey: "correct", header: "Correct", meta: { align: "right" } },
    { id: "confidence", accessorFn: (t) => (t.confidence == null ? null : pct(t.confidence)), header: "Confidence", meta: { label: "Confidence %" },
      cell: ({ row, getValue }) => <CellBar value={getValue()} tone={masteryOf(row.original.label).tone === "muted" ? "brand" : masteryOf(row.original.label).tone} /> },
    { accessorKey: "theta", header: "θ", meta: { align: "right" }, cell: ({ getValue }) => (getValue() == null ? "–" : getValue().toFixed(2)) },
    { id: "level", accessorFn: (t) => masteryOf(t.label).label, header: "Level", cell: ({ row }) => <Badge tone={masteryOf(row.original.label).tone}>{masteryOf(row.original.label).label}</Badge> },
    { accessorKey: "avg_seconds", header: "Avg s", meta: { align: "right" }, cell: ({ getValue }) => getValue() ?? "–" },
  ], []);
  const attemptCols = useMemo(() => [
    { accessorKey: "id", header: "Quiz", cell: ({ getValue }) => `#${getValue()}` },
    { accessorKey: "finished_at", header: "Finished", cell: ({ getValue }) => dateTime(getValue()) },
    { accessorKey: "mode", header: "Mode", cell: ({ getValue }) => <Badge tone={getValue() === "assessment" ? "brand" : "neutral"}>{getValue()}</Badge> },
    { accessorKey: "kind", header: "Kind" },
    { id: "score", accessorFn: (a) => (a.answered ? Math.round((100 * a.correct) / a.answered) : null), header: "Score %", meta: { align: "right" } },
    { accessorKey: "correct", header: "Correct", meta: { align: "right" } },
    { accessorKey: "answered", header: "Answered", meta: { align: "right" } },
    { accessorKey: "ended_reason", header: "Ended early", cell: ({ getValue }) => getValue() ?? "–" },
  ], []);
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-96" />;
  const o = r.overall;
  const trend = r.ability_trend.map((p) => ({ label: `#${p.attempt_id}`, confidence: pct(p.confidence), accuracy: pct(p.accuracy) }));
  const tried = r.topics.filter((t) => t.confidence != null);

  return (
    <article className="space-y-6">
      <Card className="flex flex-wrap items-center gap-4 p-5">
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-brand-deep">Learning report</p>
          <h2 className="break-anywhere font-display text-2xl font-semibold">{r.subject}</h2>
          <p className="text-sm text-muted">Generated {dateTime(r.generated_at)}</p>
        </div>
        <div className="no-print flex flex-wrap gap-2">
          <Button asChild><a href={`/api/v1/subjects/${id}/report.pdf`} download className="no-underline"><FileText className="h-4 w-4" />PDF report</a></Button>
          <Button asChild variant="secondary"><a href={`/api/v1/subjects/${id}/report.xlsx`} download className="no-underline"><FileSpreadsheet className="h-4 w-4" />Excel workbook</a></Button>
          <Button asChild variant="secondary"><a href={`/api/v1/subjects/${id}/report.csv`} download className="no-underline">CSV</a></Button>
          <Button variant="ghost" onClick={() => window.print()}><Printer className="h-4 w-4" />Print</Button>
        </div>
      </Card>

      {o ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile label="Overall confidence" value={`${pct(o.confidence)}%`} sub="chance you are above proficient" tone={o.confidence >= 0.7 ? "strong" : o.confidence >= 0.45 ? "mid" : "weak"} />
          <StatTile label="Ability θ" value={`${o.theta > 0 ? "+" : ""}${o.theta.toFixed(2)}`} sub={`± ${o.se.toFixed(2)}`} delay={0.04} />
          <StatTile label="Expected accuracy" value={`${pct(o.expected_accuracy)}%`} sub="on an average question" delay={0.08} />
          <StatTile label="Answers used" value={o.answered} sub={`${o.correct} correct · ${r.wrong_questions} still wrong`} delay={0.12} />
        </div>
      ) : <p className="rounded-xl bg-surface p-4 text-sm shadow-card">No quiz answers yet, so there are no scores. Take a diagnostic test first.</p>}

      <div className="grid gap-5 xl:grid-cols-2">
        <ChartCard title="Confidence by topic">
          <Bars data={tried.map((t) => ({ label: t.name, confidence: pct(t.confidence), tone: masteryOf(t.label).tone }))} layout="vertical" series={[{ key: "confidence", name: "Confidence" }]} domain={[0, 100]}
            yFmt={(v) => `${v}%`} tipFmt={(v) => `${v}%`} height={Math.max(160, tried.length * 28)} catWidth={130} colorBy={(row) => TONE_HEX[row.tone] ?? TONE_HEX.brand} reference={{ x: 70, label: "70%" }} />
        </ChartCard>
        <ChartCard title="Over time" description="Overall confidence after each quiz, and that quiz's accuracy.">
          <TrendLine data={trend} series={[{ key: "confidence", name: "Confidence %", color: "#0194E2" }, { key: "accuracy", name: "Accuracy %", color: "#0E9F8E" }]} yDomain={[0, 100]} yFmt={(v) => `${v}%`} height={Math.max(220, tried.length * 20)} />
        </ChartCard>
      </div>

      <Card className="print-break p-5">
        <SectionTitle>What to do next</SectionTitle>
        <ul className="list-disc space-y-1 pl-6 text-sm">{r.recommendations.map((t, i) => <li key={i}>{t}</li>)}</ul>
      </Card>

      <section className="print-break"><SectionTitle>Topics</SectionTitle><DataTable columns={topicCols} data={r.topics} filename="nexus-report-topics" title={`${r.subject}: topics`} searchPlaceholder="Search topics" pageSize={25} /></section>
      {r.attempts.length > 0 && <section className="print-break"><SectionTitle>Quizzes</SectionTitle><DataTable columns={attemptCols} data={r.attempts} filename="nexus-report-quizzes" title={`${r.subject}: quizzes`} searchPlaceholder="Search quizzes" /></section>}
      {r.backtracking.length > 0 && (
        <Card className="print-break p-5">
          <SectionTitle>Step-backs to foundations</SectionTitle>
          <p className="mb-3 text-sm text-muted">Questions asked from a foundation topic after a miss, and how they went.</p>
          <Bars data={r.backtracking.map((b) => ({ label: b.topic, correct: b.correct, wrong: b.asked - b.correct }))} layout="vertical" stacked series={[{ key: "correct", name: "Correct", color: TONE_HEX.strong }, { key: "wrong", name: "Wrong", color: TONE_HEX.weak }]} height={Math.max(140, 40 + r.backtracking.length * 34)} catWidth={130} />
        </Card>
      )}
      <p className="text-xs text-muted">{r.method}</p>
    </article>
  );
}
