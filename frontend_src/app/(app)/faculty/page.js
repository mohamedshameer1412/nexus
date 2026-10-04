"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Calculator, Check, ClipboardCheck, Gavel, LineChart, Pencil, Quote, X } from "lucide-react";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { cn, friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { EmptyState, ErrorState, PageHeader } from "@/components/nexus/common";
import {
  Alert, Badge, Button, Card, Dialog, DialogContent, Field, Input, Segmented, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger, Textarea,
} from "@/components/ui/primitives";

const L = (i) => String.fromCharCode(65 + i);
const pct = (x) => (x == null ? "–" : `${Math.round(x * 100)}%`);
const KIND = { worked_example: "Worked example", flashcards: "Flashcards", revision: "Revision quiz", practice: "Practice set" };

function useAct(onDone) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ path, method = "POST", json }) => api(path, { method, json }),
    onSuccess: (_, v) => { qc.invalidateQueries({ queryKey: ["faculty"] }); onDone?.(v); },
    onError: (e) => toast.error(friendlyError(e)),
  });
}

// ------------------------------------------------------------------------------------------------ review queue

function EditDialog({ item, open, onOpenChange }) {
  const [q, setQ] = useState(item.question);
  const [opts, setOpts] = useState(item.options);
  const [ans, setAns] = useState(String(item.answer_index));
  const [why, setWhy] = useState(item.explanation || "");
  const act = useAct(() => { onOpenChange(false); toast.success("Corrected and approved"); });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent wide title="Edit and approve" description="Fix the wording, the options or the key. Saving approves the question for officers.">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); act.mutate({ path: `/faculty/review/${item.id}`, method: "PUT", json: { question: q, options: opts, answer_index: Number(ans), explanation: why } }); }}>
          <Field label="Question" htmlFor="ed-q"><Textarea id="ed-q" rows={2} value={q} onChange={(e) => setQ(e.target.value)} required /></Field>
          <div className="grid gap-2 sm:grid-cols-2">
            {opts.map((o, i) => (
              <Field key={i} label={`Option ${L(i)}`} htmlFor={`ed-o${i}`}>
                <Input id={`ed-o${i}`} value={o} onChange={(e) => setOpts(opts.map((x, j) => (j === i ? e.target.value : x)))} required />
              </Field>
            ))}
          </div>
          <div><p className="mb-1.5 text-[13px] font-semibold">Correct option</p>
            <Segmented label="Correct option" value={ans} onValueChange={setAns} options={[0, 1, 2, 3].map((i) => ({ value: String(i), label: L(i) }))} /></div>
          <Field label="Explanation" htmlFor="ed-w"><Textarea id="ed-w" rows={2} value={why} onChange={(e) => setWhy(e.target.value)} /></Field>
          <Button type="submit" loading={act.isPending}>Save and approve</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RejectDialog({ item, open, onOpenChange }) {
  const [note, setNote] = useState("");
  const act = useAct(() => { onOpenChange(false); toast.success("Rejected; officers will not see it"); });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title="Reject this question" description="It stays out of the question bank. The reason is kept with it.">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); act.mutate({ path: `/faculty/review/${item.id}/reject`, json: { note } }); }}>
          <Field label="Reason" htmlFor="rj" hint="For example: two options are defensible, or the quote does not support the key.">
            <Textarea id="rj" rows={3} value={note} onChange={(e) => setNote(e.target.value)} required minLength={5} maxLength={500} />
          </Field>
          <Button type="submit" variant="danger" loading={act.isPending} disabled={note.trim().length < 5}>Reject</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ReviewItem({ item, readOnly }) {
  const [edit, setEdit] = useState(false);
  const [reject, setReject] = useState(false);
  const approve = useAct(() => toast.success("Approved for officers"));
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        <Badge tone="neutral">{item.subject}</Badge>{item.topic_path && <span>{item.topic_path.split(" › ").pop()}</span>}
        <span>· {item.difficulty}</span>{item.model && <span>· drafted by {item.model}</span>}
        {item.solver === "agreed" && <Badge tone="strong">Independent reader agreed</Badge>}
        {item.key_check && <Badge tone="brand"><Calculator className="h-3 w-3" />{item.key_check}</Badge>}
        {readOnly && <Badge tone={item.review === "approved" ? "strong" : "weak"}>{item.review}</Badge>}
      </div>
      <p className="break-anywhere mt-2 font-display text-[17px] font-semibold">{item.question}</p>
      <ol className="mt-3 grid gap-1.5 sm:grid-cols-2">
        {item.options.map((o, i) => (
          <li key={i} className={cn("break-anywhere rounded-lg border px-3 py-2 text-sm", i === item.answer_index ? "border-strong bg-strong-bg font-semibold text-strong" : "border-border")}>
            <b>{L(i)}.</b> {o}
          </li>
        ))}
      </ol>
      {item.quote && <p className="break-anywhere mt-3 flex gap-2 rounded-lg bg-surface-2 px-3 py-2 text-sm text-muted"><Quote className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>“{item.quote}”{item.doc_title && <> — {item.doc_title}{item.page_start ? `, p. ${item.page_start}` : ""}</>}</span></p>}
      {item.explanation && <p className="break-anywhere mt-2 text-sm">{item.explanation}</p>}
      {item.review_note && <p className="mt-2 text-sm text-muted">Note: {item.review_note}</p>}
      {!readOnly && (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button size="sm" onClick={() => approve.mutate({ path: `/faculty/review/${item.id}/approve`, json: {} })} loading={approve.isPending}><Check className="h-4 w-4" />Approve</Button>
          <Button size="sm" variant="secondary" onClick={() => setEdit(true)}><Pencil className="h-4 w-4" />Edit</Button>
          <Button size="sm" variant="ghost" onClick={() => setReject(true)}><X className="h-4 w-4" />Reject</Button>
        </div>
      )}
      {edit && <EditDialog item={item} open={edit} onOpenChange={setEdit} />}
      {reject && <RejectDialog item={item} open={reject} onOpenChange={setReject} />}
    </Card>
  );
}

function ReviewTab() {
  const [status, setStatus] = useState("pending");
  const { data, error, isPending, refetch } = useQuery({ queryKey: ["faculty", "review", status], queryFn: () => api(`/faculty/review?status=${status}`) });
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">Questions drafted by the model from uploaded material. Each passed the automatic checks (exact quote, independent reader, SymPy for computed keys); officers see it only after you approve it.</p>
        <Segmented label="Show" value={status} onValueChange={setStatus} options={[
          { value: "pending", label: `Pending${data ? ` (${data.counts.pending})` : ""}` }, { value: "approved", label: "Approved" }, { value: "rejected", label: "Rejected" }]} />
      </div>
      {isPending ? <Skeleton className="h-64" /> : data.items.length === 0
        ? <EmptyState icon={ClipboardCheck} title={status === "pending" ? "Nothing waiting for review" : `No ${status} questions`}>New drafts appear here as soon as they pass the checks.</EmptyState>
        : data.items.map((it) => <ReviewItem key={it.id} item={it} readOnly={status !== "pending"} />)}
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ contests

function ContestCard({ c }) {
  const [resolution, setResolution] = useState("");
  const act = useAct((v) => toast.success(v.json.decision === "upheld" ? "Upheld: the answer is now marked correct" : "Rejected: the mark stands"));
  const decide = (decision) => act.mutate({ path: `/faculty/contests/${c.id}/resolve`, json: { decision, resolution } });
  return (
    <Card className="p-5">
      <p className="flex flex-wrap items-center gap-2 text-xs text-muted"><Badge tone="neutral">{c.subject}</Badge><span>{c.topic_path?.split(" › ").pop()}</span><span>· {dateTime(c.created_at)}</span>
        {c.status !== "open" && <Badge tone={c.status === "upheld" ? "strong" : "muted"}>{c.status}</Badge>}</p>
      <p className="break-anywhere mt-2 font-semibold">{c.question}</p>
      <ol className="mt-2 grid gap-1.5 sm:grid-cols-2">
        {c.options.map((o, i) => (
          <li key={i} className={cn("break-anywhere rounded-lg border px-3 py-1.5 text-sm", i === c.answer_index ? "border-strong bg-strong-bg text-strong" : i === c.chosen_index ? "border-weak bg-weak-bg text-weak" : "border-border")}>
            <b>{L(i)}.</b> {o}{i === c.answer_index && " (key)"}{i === c.chosen_index && " (officer)"}
          </li>
        ))}
      </ol>
      {c.quote && <p className="break-anywhere mt-2 rounded-lg bg-surface-2 px-3 py-2 text-sm text-muted">“{c.quote}”</p>}
      <Alert tone="info" className="mt-3" title="The officer's reason">{c.reason}</Alert>
      {c.status === "open" ? (
        <div className="mt-4 space-y-3">
          <Field label="Your decision, as the officer will read it" htmlFor={`res-${c.id}`}>
            <Textarea id={`res-${c.id}`} rows={2} value={resolution} onChange={(e) => setResolution(e.target.value)} maxLength={1000} />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={resolution.trim().length < 5} loading={act.isPending} onClick={() => decide("upheld")}>Uphold: re-mark correct and withdraw the question</Button>
            <Button size="sm" variant="secondary" disabled={resolution.trim().length < 5} loading={act.isPending} onClick={() => decide("rejected")}>Reject: the mark stands</Button>
          </div>
        </div>
      ) : <p className="mt-3 text-sm"><b>Decision:</b> {c.resolution}</p>}
    </Card>
  );
}

function ContestsTab() {
  const [status, setStatus] = useState("open");
  const { data, error, isPending, refetch } = useQuery({ queryKey: ["faculty", "contests", status], queryFn: () => api(`/faculty/contests?status=${status}`) });
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">Officers contest answers they believe were marked wrongly. Upholding re-marks the answer, recomputes the score and mastery, and withdraws the question.</p>
        <Segmented label="Show" value={status} onValueChange={setStatus} options={[{ value: "open", label: "Open" }, { value: "upheld", label: "Upheld" }, { value: "rejected", label: "Rejected" }]} />
      </div>
      {isPending ? <Skeleton className="h-64" /> : data.contests.length === 0
        ? <EmptyState icon={Gavel} title={`No ${status} contests`}>When an officer contests a score it appears here.</EmptyState>
        : data.contests.map((c) => <ContestCard key={c.id} c={c} />)}
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ insights

function Stat({ label, value, hint }) {
  return <Card className="p-4"><p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p><p className="tabular mt-1 font-display text-2xl font-semibold">{value}</p>{hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}</Card>;
}

function InsightsTab() {
  const { data, error, isPending, refetch } = useQuery({ queryKey: ["faculty", "insights"], queryFn: () => api("/faculty/insights") });
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-64" />;
  const b = data.question_bank;
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted">For NSSTA: which interventions close which gaps, measured by each officer&apos;s verified re-test. Aggregated across officers; nobody is named.</p>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Officers" value={data.officers} />
        <Stat label="Approved questions" value={b.approved} hint={`${b.pending} pending, ${b.rejected} rejected`} />
        <Stat label="Keys checked by SymPy" value={data.sympy_checked} />
        <Stat label="Contests" value={data.contests.open + data.contests.upheld + data.contests.rejected} hint={`${data.contests.open} open, ${data.contests.upheld} upheld`} />
      </div>
      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[520px] text-sm">
          <caption className="px-5 pt-4 text-left font-display text-lg font-semibold">What closes gaps</caption>
          <thead><tr className="text-left text-xs uppercase tracking-wide text-muted"><th className="px-5 py-2">Intervention</th><th className="px-3 py-2 text-right">Tried</th><th className="px-3 py-2 text-right">Re-tested</th><th className="px-3 py-2 text-right">Closed the gap</th><th className="px-5 py-2 text-right">Avg. gain</th></tr></thead>
          <tbody>
            {data.interventions.length === 0 && <tr><td colSpan={5} className="px-5 py-6 text-center text-muted">No interventions yet.</td></tr>}
            {data.interventions.map((k) => (
              <tr key={k.kind} className="border-t border-border">
                <td className="px-5 py-2.5 font-semibold">{KIND[k.kind] ?? k.kind}</td><td className="tabular px-3 text-right">{k.tried}</td><td className="tabular px-3 text-right">{k.verified}</td>
                <td className="tabular px-3 text-right">{k.improved} <span className="text-muted">({pct(k.closes_rate)})</span></td><td className="tabular px-5 text-right">{k.avg_gain == null ? "–" : `${k.avg_gain > 0 ? "+" : ""}${Math.round(k.avg_gain * 100)} pts`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[520px] text-sm">
          <caption className="px-5 pt-4 text-left font-display text-lg font-semibold">By topic</caption>
          <thead><tr className="text-left text-xs uppercase tracking-wide text-muted"><th className="px-5 py-2">Topic</th><th className="px-3 py-2 text-right">Tried</th><th className="px-3 py-2 text-right">Closed</th><th className="px-5 py-2">Works best</th></tr></thead>
          <tbody>
            {data.topics.length === 0 && <tr><td colSpan={4} className="px-5 py-6 text-center text-muted">No data yet.</td></tr>}
            {data.topics.map((t) => (
              <tr key={t.topic} className="border-t border-border"><td className="px-5 py-2.5 font-semibold">{t.topic}</td><td className="tabular px-3 text-right">{t.tried}</td>
                <td className="tabular px-3 text-right">{t.improved}/{t.verified}</td><td className="px-5">{t.works_best ? KIND[t.works_best] ?? t.works_best : "–"}</td></tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

export default function FacultyPage() {
  useTitle("Faculty");
  return (
    <div>
      <PageHeader title="Faculty workspace" description="Review AI-drafted questions before officers see them, resolve contested scores, and see which programmes close which gaps." />
      <Tabs defaultValue="review">
        <TabsList className="mb-5">
          <TabsTrigger value="review"><ClipboardCheck className="h-4 w-4" />Review queue</TabsTrigger>
          <TabsTrigger value="contests"><Gavel className="h-4 w-4" />Contests</TabsTrigger>
          <TabsTrigger value="insights"><LineChart className="h-4 w-4" />NSSTA insights</TabsTrigger>
        </TabsList>
        <TabsContent value="review"><ReviewTab /></TabsContent>
        <TabsContent value="contests"><ContestsTab /></TabsContent>
        <TabsContent value="insights"><InsightsTab /></TabsContent>
      </Tabs>
    </div>
  );
}
