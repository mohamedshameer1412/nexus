"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet, GraduationCap, Layers, LayoutList, Table2, Wand2 } from "lucide-react";
import { api } from "@/lib/api";
import { check, McqStarted } from "@/lib/schemas";
import { getActiveJobs, getDocs, getMcq, getMcqJob, getSubject, getTopics, keys } from "@/lib/queries";
import { shortDate } from "@/lib/format";
import { friendlyError, plural } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { JobProgress } from "@/components/nexus/answer";
import { askToBeNotified } from "@/components/nexus/job-watcher";
import McqCard from "@/components/nexus/mcq-card";
import { Bars } from "@/components/nexus/charts";
import { EmptyState, ErrorState, RunTrace, SectionTitle } from "@/components/nexus/common";
import { DataTable } from "@/components/nexus/data-table";
import { Alert, Badge, Button, Card, Field, Segmented, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from "@/components/ui/primitives";

function Generator({ id, topics }) {
  const qc = useQueryClient();
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState("5");
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState("");
  const [startedAt, setStartedAt] = useState(() => new Date().toISOString());
  const start = useMutation({
    mutationFn: () => api(`/subjects/${id}/mcq/jobs`, { method: "POST", json: { topic_id: topic ? Number(topic) : null, count: Number(count) } }),
    onMutate: () => askToBeNotified(),
    onSuccess: (r) => { setStartedAt(new Date().toISOString()); setJobId(check(McqStarted, r).id); setError(""); qc.invalidateQueries({ queryKey: keys.activeJobs }); },
    onError: (e) => { setError(friendlyError(e)); if (e.code === "too_many_pending") qc.invalidateQueries({ queryKey: keys.activeJobs }); },
  });
  const active = useQuery({ queryKey: keys.activeJobs, queryFn: getActiveJobs, retry: false });
  useEffect(() => {
    const mine = active.data?.jobs.find((j) => String(j.subject_id) === String(id));
    if (mine && jobId === null) { setJobId(mine.id); if (mine.created_at) setStartedAt(mine.created_at); }
  }, [active.data, id, jobId]);
  const job = useQuery({
    queryKey: keys.mcqJob(id, jobId), queryFn: () => getMcqJob(id, jobId), enabled: jobId !== null,
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 2500 : false), refetchIntervalInBackground: true,
  });
  const status = job.data?.status;
  useEffect(() => {
    if (!status || status === "pending") return;
    for (const k of [keys.mcq(id), keys.quiz(id), keys.subjects, keys.subject(id)]) qc.invalidateQueries({ queryKey: k });
  }, [status, id, qc]);
  const running = start.isPending || status === "pending" || (jobId !== null && !job.data && !job.error);
  const d = job.data;
  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand text-white"><Wand2 className="h-5 w-5" /></span>
        <div>
          <h2 className="font-display text-lg font-semibold">Generate practice questions</h2>
          <p className="text-sm text-muted">Each question must quote your material word for word, and its answer is checked a second time. Only questions that pass are kept.</p>
        </div>
      </div>
      <form onSubmit={(e) => { e.preventDefault(); setJobId(null); start.mutate(); }} className="mt-4 grid gap-3 sm:grid-cols-[1fr_9rem_auto] sm:items-end">
        <Field label="Topic" htmlFor="topic">
          <Select value={topic || "all"} onValueChange={(v) => setTopic(v === "all" ? "" : v)}>
            <SelectTrigger id="topic"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="all">Whole subject</SelectItem>{topics.map((t) => <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
        <Field label="How many" htmlFor="count">
          <Select value={String(count)} onValueChange={setCount}>
            <SelectTrigger id="count"><SelectValue /></SelectTrigger>
            <SelectContent>{[3, 5, 8, 10].map((n) => <SelectItem key={n} value={String(n)}>{n} questions</SelectItem>)}</SelectContent>
          </Select>
        </Field>
        <Button type="submit" loading={running}><Wand2 className="h-4 w-4" />{running ? "Writing" : "Generate"}</Button>
      </form>
      {error && <Alert tone="danger" className="mt-3">{error}</Alert>}
      {running && jobId !== null && <div className="mt-4"><JobProgress createdAt={startedAt} what="Writing and checking questions…" /></div>}
      {d && status !== "pending" && (
        <Alert tone={d.produced > 0 ? "success" : "warning"} className="mt-4">
          {d.produced > 0 ? `Added ${plural(d.produced, "question")}${d.rejected ? `; ${plural(d.rejected, "draft")} did not pass the checks and ${d.rejected === 1 ? "was" : "were"} thrown away` : ""}.`
            : d.reason || "No question passed the checks, so none were added. Nothing was made up."}
        </Alert>
      )}
      {d && status !== "pending" && <RunTrace steps={d.steps} loop={d.loop} title="What happened in this run" />}
    </Card>
  );
}

export default function PracticePage() {
  const { id } = useParams();
  const { data: subject } = useQuery({ queryKey: keys.subject(id), queryFn: () => getSubject(id) });
  useTitle("Practice", subject?.name);
  const docs = useQuery({ queryKey: keys.docs(id), queryFn: () => getDocs(id) });
  const topics = useQuery({ queryKey: keys.topics(id), queryFn: () => getTopics(id) });
  const bank = useQuery({ queryKey: keys.mcq(id), queryFn: () => getMcq(id) });
  const [filter, setFilter] = useState("");
  const [view, setView] = useState("cards");
  const [limit, setLimit] = useState(10);
  const byTopic = useMemo(() => {
    const m = new Map();
    for (const q of bank.data ?? []) { const k = q.topic_path?.split(" › ").pop() || "Other"; m.set(k, (m.get(k) || 0) + 1); }
    return [...m.entries()].map(([label, n]) => ({ label, n })).sort((a, b) => b.n - a.n);
  }, [bank.data]);
  const columns = useMemo(() => [
    { accessorKey: "question", header: "Question", cell: ({ getValue }) => <span className="line-clamp-2 min-w-[18rem]">{getValue()}</span> },
    { id: "topic", accessorFn: (r) => r.topic_path?.split(" › ").pop() ?? "", header: "Topic", cell: ({ getValue }) => <Badge tone="neutral">{getValue()}</Badge> },
    { id: "options", accessorFn: (r) => r.options.join(" | "), header: "Options", cell: ({ row }) => <span className="line-clamp-1 text-muted">{row.original.options.join(" · ")}</span> },
    { accessorKey: "created_at", header: "Added", cell: ({ getValue }) => shortDate(getValue()) },
  ], []);

  if (docs.isPending || bank.isPending) return <Skeleton className="h-64" />;
  if (bank.error) return <ErrorState error={bank.error} onRetry={bank.refetch} />;
  if (!docs.data?.some((d) => d.chunks > 0)) {
    return <EmptyState title="Upload some material first" action={<Button asChild><Link href={`/subjects/${id}/materials`}>Go to Materials</Link></Button>}>Practice questions are written from what you upload to this subject.</EmptyState>;
  }
  const usable = (topics.data ?? []).filter((t) => t.passages > 0);
  const shown = filter ? bank.data.filter((q) => String(q.topic_id) === filter) : bank.data;
  return (
    <div className="space-y-6">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Generator id={id} topics={usable} />
        <Card className="flex flex-col p-5">
          <div className="flex items-center justify-between"><h2 className="font-display text-lg font-semibold">Question bank</h2><span className="tabular font-display text-2xl font-semibold text-brand-deep">{bank.data.length}</span></div>
          <div className="mt-2 flex-1">
            {byTopic.length ? <Bars data={byTopic.slice(0, 7)} layout="vertical" series={[{ key: "n", name: "Questions" }]} height={Math.max(120, Math.min(7, byTopic.length) * 28)} catWidth={120} /> : <p className="text-sm text-muted">No questions yet.</p>}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Button asChild variant="subtle" size="sm"><Link href={`/subjects/${id}/practice/flashcards`}><Layers className="h-4 w-4" />Flashcards</Link></Button>
            <Button asChild variant="subtle" size="sm"><Link href={`/subjects/${id}/quiz`}><GraduationCap className="h-4 w-4" />Take a quiz</Link></Button>
          </div>
        </Card>
      </div>

      <section aria-labelledby="bank-h">
        <SectionTitle id="bank-h" action={bank.data.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {view === "cards" && (
              <Select value={filter || "all"} onValueChange={(v) => { setFilter(v === "all" ? "" : v); setLimit(10); }}>
                <SelectTrigger className="h-9 w-52 text-sm" aria-label="Show topic"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="all">All topics</SelectItem>{usable.map((t) => <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>)}</SelectContent>
              </Select>
            )}
            <Button asChild size="sm" variant="secondary"><a href={`/api/v1/subjects/${id}/mcq.csv`} download className="no-underline"><FileSpreadsheet className="h-4 w-4" />CSV</a></Button>
            <Segmented label="View" value={view} onValueChange={setView} options={[{ value: "cards", label: "Practise", icon: LayoutList }, { value: "table", label: "Table", icon: Table2 }]} />
          </div>
        )}>Your questions</SectionTitle>
        {bank.data.length === 0 ? (
          <EmptyState icon={Wand2} title="No questions yet">Generate some above. Practice is never scored.</EmptyState>
        ) : view === "table" ? (
          <DataTable columns={columns} data={bank.data} filename="nexus-practice-questions" title="Practice questions" searchPlaceholder="Search questions"
            facets={[{ id: "topic", label: "Topics" }]} />
        ) : shown.length === 0 ? <p className="text-sm text-muted">No questions for that topic yet.</p> : (
          <>
            <ul className="space-y-4">{shown.slice(0, limit).map((q, i) => <li key={q.id}><McqCard subjectId={id} q={q} index={i + 1} /></li>)}</ul>
            {shown.length > limit && <div className="mt-4 text-center"><Button variant="secondary" onClick={() => setLimit((l) => l + 10)}>Show {Math.min(10, shown.length - limit)} more</Button></div>}
          </>
        )}
      </section>
    </div>
  );
}
