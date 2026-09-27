"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { FileText, LayoutGrid, Layers, List, MessageCircleQuestion, Plus, Search, Tags } from "lucide-react";
import { getSubjects, keys } from "@/lib/queries";
import { shortDate } from "@/lib/format";
import { useTitle } from "@/lib/use-title";
import { EmptyState, ErrorState, PageHeader } from "@/components/nexus/common";
import { DataTable } from "@/components/nexus/data-table";
import { NewSubjectDialog, SubjectActions } from "@/components/nexus/subject-actions";
import { Badge, Button, Card, Input, Segmented, Skeleton } from "@/components/ui/primitives";

const LEVEL = { new: "New learner", intermediate: "Intermediate", professional: "Professional" };
const HUES = ["#0194E2", "#0E9F8E", "#7C5CFA", "#F2A516", "#E5484D", "#0369A8"];

function Monogram({ name, id }) {
  const letters = name.split(/\s+/).filter((w) => /[A-Za-z0-9]/.test(w[0])).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "S";
  const hue = HUES[id % HUES.length];
  return <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl font-display text-[15px] font-semibold text-white shadow-sm" style={{ background: `linear-gradient(135deg, ${hue}, ${hue}cc)` }} aria-hidden="true">{letters}</span>;
}

function SubjectsInner() {
  useTitle("Subjects");
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState("");
  const [view, setView] = useState("grid");
  const creating = params.get("new") === "1";
  const setCreating = (o) => router.replace(o ? "/subjects?new=1" : "/subjects", { scroll: false });
  const { data, isPending, error, refetch } = useQuery({ queryKey: keys.subjects, queryFn: getSubjects });
  const shown = useMemo(() => (data ?? []).filter((s) => `${s.name} ${s.description}`.toLowerCase().includes(q.trim().toLowerCase())), [data, q]);
  const columns = useMemo(() => [
    { accessorKey: "name", header: "Subject", cell: ({ row }) => <Link href={`/subjects/${row.original.id}/materials`} className="font-semibold">{row.original.name}</Link> },
    { accessorKey: "level", header: "Level", cell: ({ getValue }) => (getValue() ? <Badge tone="neutral">{LEVEL[getValue()]}</Badge> : <span className="text-muted">Not set</span>), meta: { export: (r) => LEVEL[r.level] ?? "" } },
    { id: "documents", accessorFn: (r) => r.counts.documents, header: "Materials", meta: { align: "right" } },
    { id: "topics", accessorFn: (r) => r.counts.topics, header: "Topics", meta: { align: "right" } },
    { id: "practice", accessorFn: (r) => r.counts.practice_questions, header: "Practice questions", meta: { align: "right" } },
    { id: "questions", accessorFn: (r) => r.counts.questions, header: "Questions asked", meta: { align: "right" } },
    { accessorKey: "created_at", header: "Created", cell: ({ getValue }) => shortDate(getValue()) },
    { id: "actions", header: "", enableSorting: false, enableHiding: false, meta: { export: false }, cell: ({ row }) => <SubjectActions subject={row.original} variant="ghost" /> },
  ], []);

  return (
    <div>
      <PageHeader title="Subjects" description="Each subject keeps its own materials, questions, quizzes and progress."
        actions={<NewSubjectDialog open={creating} onOpenChange={setCreating} />} />
      {error ? <ErrorState error={error} onRetry={refetch} /> : isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-44" />)}</div>
      ) : data.length === 0 ? (
        <EmptyState title="No subjects yet" action={<Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" />New subject</Button>}>
          Create your first subject, then upload the material you want to study.
        </EmptyState>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <div className="relative w-full max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter subjects" aria-label="Filter subjects" className="h-9 pl-9 text-sm" />
            </div>
            <Segmented className="ml-auto" label="View" value={view} onValueChange={setView} options={[{ value: "grid", label: "Cards", icon: LayoutGrid }, { value: "table", label: "Table", icon: List }]} />
          </div>
          {view === "table" ? (
            <DataTable columns={columns} data={shown} filename="nexus-subjects" title="Subjects" searchPlaceholder="Search subjects" onRowClick={(r) => router.push(`/subjects/${r.id}/materials`)} />
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {shown.map((s, i) => (
                <motion.li key={s.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 8) * 0.04 }}>
                  <Card interactive className="group relative flex h-full flex-col p-5">
                    <div className="flex items-start gap-3">
                      <Monogram name={s.name} id={s.id} />
                      <div className="min-w-0 flex-1">
                        <Link href={`/subjects/${s.id}/materials`} className="break-anywhere font-display text-[17px] font-semibold text-foreground no-underline after:absolute after:inset-0 after:rounded-xl group-hover:text-brand-deep">{s.name}</Link>
                        <p className="mt-0.5 text-[12.5px] text-muted">{s.level ? LEVEL[s.level] : "Level not set"} · created {shortDate(s.created_at)}</p>
                      </div>
                      <div className="relative z-10"><SubjectActions subject={s} variant="ghost" /></div>
                    </div>
                    <p className="break-anywhere mt-3 line-clamp-2 min-h-[2.6em] text-sm text-muted">{s.description || "No description."}</p>
                    <dl className="mt-4 grid grid-cols-4 gap-2 border-t border-border pt-3 text-center">
                      {[[FileText, "Files", s.counts.documents], [Tags, "Topics", s.counts.topics], [Layers, "Practice", s.counts.practice_questions], [MessageCircleQuestion, "Asked", s.counts.questions]].map(([Icon, k, v]) => (
                        <div key={k}><dt className="flex items-center justify-center gap-1 text-[11.5px] text-muted"><Icon className="h-3.5 w-3.5" aria-hidden="true" />{k}</dt><dd className="tabular font-display text-lg font-semibold">{v}</dd></div>
                      ))}
                    </dl>
                  </Card>
                </motion.li>
              ))}
              <li>
                <button type="button" onClick={() => setCreating(true)} className="flex h-full min-h-44 w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-brand/30 text-brand-deep transition-colors hover:border-brand hover:bg-brand-wash">
                  <Plus className="h-6 w-6" aria-hidden="true" /><span className="font-semibold">New subject</span>
                </button>
              </li>
            </ul>
          )}
        </>
      )}
    </div>
  );
}

export default function SubjectsPage() {
  return <Suspense><SubjectsInner /></Suspense>;
}
