"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Briefcase, ChevronRight, ClipboardPaste, Target } from "lucide-react";
import { api } from "@/lib/api";
import { getCareers, keys } from "@/lib/queries";
import { shortDate } from "@/lib/format";
import { friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { EmptyState, ErrorState, PageHeader, SectionTitle } from "@/components/nexus/common";
import { Alert, Badge, Button, Card, Field, Input, Skeleton, Textarea } from "@/components/ui/primitives";

const STATE = { pending: { label: "Reading", tone: "mid" }, done: { label: "Ready", tone: "strong" }, failed: { label: "Could not read", tone: "weak" } };

export default function CareerPage() {
  useTitle("Career goals");
  const router = useRouter();
  const qc = useQueryClient();
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.careers, queryFn: getCareers });
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [problem, setProblem] = useState("");
  const create = useMutation({
    mutationFn: () => api("/career", { method: "POST", json: { title, text } }),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: keys.careers }); router.push(`/career/${r.id}`); },
    onError: (e) => setProblem(friendlyError(e)),
  });
  return (
    <div>
      <PageHeader title="Career goals" description="Paste a job description. Nexus lists the skills it asks for and checks each one against your own materials and quiz answers." />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card className="p-5">
          <h2 className="flex items-center gap-2 font-display text-lg font-semibold"><ClipboardPaste className="h-5 w-5 text-brand" />Skill-gap analysis for a job</h2>
          <form className="mt-4 space-y-4" onSubmit={(e) => { e.preventDefault(); setProblem(""); create.mutate(); }}>
            <Field label="Job title" htmlFor="cg-title"><Input id="cg-title" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Junior Data Analyst" /></Field>
            <Field label="Job description" htmlFor="cg-text" hint={`${text.trim().length} characters (at least 40). Only this text is sent to a model, and only if you allowed cloud models. Your materials never are.`}>
              <Textarea id="cg-text" value={text} onChange={(e) => setText(e.target.value)} rows={11} maxLength={16000} placeholder="Paste the requirements and responsibilities here" />
            </Field>
            {problem && <Alert tone="danger">{problem}</Alert>}
            <Button type="submit" loading={create.isPending} disabled={title.trim().length < 2 || text.trim().length < 40}><Target className="h-4 w-4" />Analyse my readiness</Button>
          </form>
        </Card>
        <section aria-labelledby="cg-list-h">
          <SectionTitle id="cg-list-h">Your goals</SectionTitle>
          {error ? <ErrorState error={error} onRetry={refetch} /> : isPending ? <Skeleton className="h-24" /> : data.length === 0 ? (
            <EmptyState icon={Briefcase} title="No career goals yet">Add a job description to see which of its skills your study already proves.</EmptyState>
          ) : (
            <ul className="space-y-3">
              {data.map((g) => (
                <li key={g.id}>
                  <Link href={`/career/${g.id}`} className="block text-inherit no-underline">
                    <Card interactive className="flex items-center gap-3 p-4">
                      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand-deep"><Briefcase className="h-5 w-5" /></span>
                      <div className="min-w-0 flex-1"><p className="break-anywhere font-semibold">{g.title}</p><p className="text-[12.5px] text-muted">{g.skills} skill{g.skills === 1 ? "" : "s"} · added {shortDate(g.created_at)}</p></div>
                      <Badge tone={(STATE[g.status] ?? STATE.done).tone} dot>{(STATE[g.status] ?? STATE.done).label}</Badge>
                      <ChevronRight className="h-4 w-4 text-muted" />
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
