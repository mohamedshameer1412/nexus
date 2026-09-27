"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Lightbulb, Printer, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { getCareer, keys } from "@/lib/queries";
import { shortDate, TONE_HEX } from "@/lib/format";
import { friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { Donut, Gauge, TrendArea } from "@/components/nexus/charts";
import { ErrorState, SectionTitle, StatTile } from "@/components/nexus/common";
import { CellBar, DataTable } from "@/components/nexus/data-table";
import { Alert, Badge, Button, Card, CardBody, CardHeader, ConfirmDialog, Skeleton } from "@/components/ui/primitives";

const STATUS = {
  verified: { label: "Verified", tone: "strong", note: "Enough right answers on a matching topic." },
  developing: { label: "Developing", tone: "mid", note: "You have answers on it, but it is not solid yet." },
  not_tested: { label: "Not tested", tone: "neutral", note: "Your materials cover it, but you have not answered questions on it." },
  no_evidence: { label: "No evidence", tone: "weak", note: "Nothing in your materials and no answers yet." },
};
const pc = (x) => (x === null || x === undefined ? "–" : `${Math.round(x * 100)}%`);

export default function CareerDetail() {
  const { id } = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.career(id), queryFn: () => getCareer(id), refetchInterval: (q) => (q.state.data?.status === "pending" ? 3000 : false) });
  useTitle(data?.title ?? "Career goal");
  const remove = useMutation({
    mutationFn: () => api(`/career/${id}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.careers }); toast.success("Career goal deleted"); router.push("/career"); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const columns = useMemo(() => [
    { accessorKey: "skill", header: "Skill", cell: ({ row }) => <div className="min-w-[12rem]"><p className="font-semibold">{row.original.skill}</p><p className="line-clamp-1 text-[12px] text-muted">“{row.original.quote}”</p></div> },
    { accessorKey: "importance", header: "Importance", cell: ({ getValue }) => <Badge tone={getValue() === "required" ? "brand" : "outline"}>{getValue() === "required" ? "Required" : "Preferred"}</Badge> },
    { id: "status", accessorFn: (s) => STATUS[s.status]?.label ?? s.status, header: "Evidence", cell: ({ row }) => <Badge tone={STATUS[row.original.status]?.tone} dot>{STATUS[row.original.status]?.label}</Badge> },
    { id: "confidence", accessorFn: (s) => (s.confidence == null ? null : Math.round(s.confidence * 100)), header: "Confidence", meta: { label: "Confidence %" }, cell: ({ getValue, row }) => <CellBar value={getValue()} tone={STATUS[row.original.status]?.tone === "neutral" ? "brand" : STATUS[row.original.status]?.tone} /> },
    { id: "where", accessorFn: (s) => (s.topic ? `${s.topic} (${s.subject})` : s.subject ?? ""), header: "Matched to", cell: ({ row }) => {
      const s = row.original;
      return s.topic ? <Link href={`/subjects/${s.subject_id}/progress`}>{s.topic}<span className="text-muted"> · {s.subject}</span></Link> : s.subject ? <Link href={`/subjects/${s.subject_id}/materials`}>{s.subject}</Link> : <span className="text-muted">–</span>;
    } },
    { id: "answers", accessorFn: (s) => (s.answered ? `${s.correct}/${s.answered}` : ""), header: "Answers", meta: { align: "right" } },
  ], []);
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-96" />;
  const sc = data.score;
  const c = sc.counts ?? {};
  return (
    <div className="space-y-6">
      <Link href="/career" className="no-print inline-flex items-center gap-1 text-sm font-semibold no-underline hover:underline"><ArrowLeft className="h-4 w-4" />All career goals</Link>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="break-anywhere font-display text-[28px] font-semibold">{data.title}</h1><p className="text-sm text-muted">{data.from_model ? `Skills read by ${data.model}` : "Skills read by plain rules"} from your text · added {shortDate(data.created_at)}</p></div>
        <div className="no-print flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => window.print()}><Printer className="h-4 w-4" />Print</Button>
          <Button variant="danger-outline" size="sm" onClick={() => setConfirm(true)}><Trash2 className="h-4 w-4" />Delete</Button>
        </div>
      </div>
      {data.status === "pending" && <Alert tone="info"><span role="status" className="flex items-center gap-2"><span className="typing-dots"><i /><i /><i /></span>Reading the job description…</span></Alert>}
      {data.status === "failed" && <Alert tone="danger">No skills could be read from this text. Paste the requirements section, one skill per line or a comma-separated list, and try again.</Alert>}
      {data.status === "done" && (
        <>
          <div className="grid gap-4 md:grid-cols-[15rem_minmax(0,1fr)_minmax(0,1fr)]">
            <Card className="flex items-center justify-center p-4"><Gauge value={sc.readiness == null ? null : Math.round(sc.readiness * 100)} label="Readiness" /></Card>
            <div className="grid grid-cols-2 gap-3">
              <StatTile label="Verified skills" value={`${sc.verified}/${sc.total}`} sub="proven by your answers" tone="strong" />
              <StatTile label="Developing" value={c.developing ?? 0} sub="answers, not solid yet" tone="mid" />
              <StatTile label="Not tested" value={c.not_tested ?? 0} sub="covered, no answers" />
              <StatTile label="No evidence" value={c.no_evidence ?? 0} sub="not in your materials" tone={c.no_evidence ? "weak" : undefined} />
            </div>
            <Card><CardHeader title="Readiness over time" /><CardBody>
              {data.history.length < 2 ? <p className="text-sm text-muted">A record is kept each time your readiness changes. Take more quizzes to see it move.</p>
                : <TrendArea data={data.history.map((h) => ({ label: shortDate(h.at), readiness: Math.round((h.readiness ?? 0) * 100) }))} series={[{ key: "readiness", name: "Readiness", color: "#0194E2" }]} yDomain={[0, 100]} yFmt={(v) => `${v}%`} height={150} />}
            </CardBody></Card>
          </div>
          <section>
            <SectionTitle>Skills the job asks for</SectionTitle>
            <p className="-mt-2 mb-3 text-sm text-muted">Each skill quotes the description and is checked against the topics and answers in all your subjects. Required skills count double in readiness.</p>
            <DataTable columns={columns} data={data.skills} filename="nexus-career-skills" title={`${data.title}: skills`} searchPlaceholder="Search skills" pageSize={25}
              facets={[{ id: "status", label: "Evidence" }, { id: "importance", label: "Importance", options: [{ value: "required", label: "Required" }, { value: "preferred", label: "Preferred" }] }]} />
          </section>
          {data.next_steps.length > 0 && (
            <section>
              <SectionTitle><span className="inline-flex items-center gap-2"><Lightbulb className="h-5 w-5 text-[#D08700]" />What to do next</span></SectionTitle>
              <ol className="grid gap-3 md:grid-cols-2">
                {data.next_steps.map((n, i) => (
                  <li key={n.skill}><Card className="h-full p-4">
                    <div className="flex items-start gap-3"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brand text-[13px] font-bold text-white">{i + 1}</span>
                      <div><Link href={n.href} className="font-semibold">{n.title}</Link><p className="mt-1 text-sm text-muted">{n.suggestion}</p><Badge tone={STATUS[n.status]?.tone} className="mt-2">{STATUS[n.status]?.label}</Badge></div></div>
                  </Card></li>
                ))}
              </ol>
              <p className="mt-2 text-xs text-muted">Project ideas are suggestions, not matches with real openings.</p>
            </section>
          )}
        </>
      )}
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title="Delete this career goal?" description="The skills and readiness history are removed. Your subjects are not touched." confirm="Delete" loading={remove.isPending} onConfirm={() => remove.mutate()} />
    </div>
  );
}
