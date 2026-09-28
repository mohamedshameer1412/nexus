"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileImage, FileText, FileType2, Globe, MoreHorizontal, ScanText, Search, Trash2, Eye } from "lucide-react";
import { api } from "@/lib/api";
import { getDocs, getSearch, getSubject, getTopics, keys } from "@/lib/queries";
import { bytes, shortDate } from "@/lib/format";
import { useTitle } from "@/lib/use-title";
import { friendlyError, plural } from "@/lib/utils";
import { EmptyState, ErrorState, PassageCard, SectionTitle } from "@/components/nexus/common";
import { DataTable } from "@/components/nexus/data-table";
import { Capabilities, UploadPanel } from "@/components/nexus/upload";
import {
  Alert, Badge, Button, Card, ConfirmDialog, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger, Input, Skeleton, Tooltip,
} from "@/components/ui/primitives";

const KIND = { pdf: [FileText, "PDF"], docx: [FileType2, "Word"], txt: [FileText, "Text"], url: [Globe, "Web page"], image: [FileImage, "Image"] };
const ROLE = { notes: "Notes", syllabus: "Syllabus", pyq: "Past papers" };

function DocActions({ id, d }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);
  const refresh = () => [keys.docs(id), keys.topics(id), keys.subject(id), keys.subjects, keys.dashboard].forEach((k) => qc.invalidateQueries({ queryKey: k }));
  const role = useMutation({
    mutationFn: (r) => api(`/subjects/${id}/materials/${d.id}/role`, { method: "PATCH", json: { role: r } }),
    onSuccess: () => { refresh(); toast.success("Updated"); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const remove = useMutation({
    mutationFn: () => api(`/subjects/${id}/materials/${d.id}`, { method: "DELETE" }),
    onSuccess: () => { refresh(); toast.success(`Removed “${d.title}”`); setConfirm(false); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild><Button variant="ghost" size="icon-sm" aria-label={`Actions for ${d.title}`} onClick={(e) => e.stopPropagation()}><MoreHorizontal className="h-4 w-4" /></Button></DropdownMenuTrigger>
        <DropdownMenuContent onClick={(e) => e.stopPropagation()}>
          <DropdownMenuItem onSelect={() => router.push(`/subjects/${id}/materials/${d.id}`)}><Eye />Open</DropdownMenuItem>
          {d.role !== "pyq" && <>
            <DropdownMenuSeparator /><DropdownMenuLabel>Mark as</DropdownMenuLabel>
            {["notes", "syllabus"].map((r) => <DropdownMenuItem key={r} disabled={d.role === r} onSelect={() => role.mutate(r)}>{ROLE[r]}</DropdownMenuItem>)}
          </>}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setConfirm(true)} className="text-weak data-[highlighted]:bg-weak-bg data-[highlighted]:text-weak"><Trash2 />Remove</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={`Remove “${d.title}”?`} confirm="Remove" loading={remove.isPending} onConfirm={() => remove.mutate()}
        description="Its passages disappear from search, answers and quizzes. Practice questions written from it keep their quotes. This cannot be undone." />
    </>
  );
}

function Documents({ id }) {
  const router = useRouter();
  const { data, isPending, error, refetch } = useQuery({ queryKey: keys.docs(id), queryFn: () => getDocs(id) });
  const columns = useMemo(() => [
    { accessorKey: "title", header: "Title", cell: ({ row }) => {
      const d = row.original; const [Icon] = KIND[d.kind] ?? [FileText];
      return (
        <div className="flex min-w-[14rem] items-center gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-brand-wash text-brand"><Icon className="h-[18px] w-[18px]" /></span>
          <div className="min-w-0"><Link href={`/subjects/${id}/materials/${d.id}`} className="block truncate font-semibold text-foreground no-underline hover:text-brand-deep" onClick={(e) => e.stopPropagation()}>{d.title}</Link>
            <p className="truncate text-[12px] text-muted">{d.source}</p></div>
        </div>
      );
    } },
    { accessorKey: "kind", header: "Type", cell: ({ getValue }) => <Badge tone="outline">{KIND[getValue()]?.[1] ?? getValue()}</Badge>, meta: { export: (r) => KIND[r.kind]?.[1] ?? r.kind } },
    { accessorKey: "role", header: "Role", cell: ({ getValue }) => <Badge tone={getValue() === "notes" ? "neutral" : "mid"}>{ROLE[getValue()] ?? "Notes"}</Badge>, meta: { export: (r) => ROLE[r.role] } },
    { accessorKey: "pages", header: "Pages", meta: { align: "right" }, cell: ({ getValue }) => getValue() ?? "–" },
    { accessorKey: "chunks", header: "Passages", meta: { align: "right" } },
    { accessorKey: "ocr_pages", header: "OCR", cell: ({ getValue }) => (getValue() ? <Tooltip content="Pages read from images with OCR"><Badge tone="mid"><ScanText className="h-3 w-3" />{getValue()}</Badge></Tooltip> : <span className="text-muted">–</span>) },
    { accessorKey: "status", header: "Status", cell: ({ row }) => {
      const d = row.original;
      return d.status === "parsed" ? <Badge tone="strong" dot>Ready</Badge> : <Tooltip content={d.warnings[0]}><Badge tone="weak" dot>{d.status === "empty" ? "No text" : "Failed"}</Badge></Tooltip>;
    } },
    { accessorKey: "bytes", header: "Size", meta: { align: "right", export: (r) => r.bytes }, cell: ({ getValue }) => bytes(getValue()) },
    { accessorKey: "created_at", header: "Added", cell: ({ getValue }) => shortDate(getValue()) },
    { id: "actions", header: "", enableSorting: false, enableHiding: false, meta: { export: false }, cell: ({ row }) => <DocActions id={id} d={row.original} /> },
  ], [id]);
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-48" />;
  if (data.length === 0) return <EmptyState title="No materials yet">Upload a PDF, a Word document, a text file or a photo of your notes to start.</EmptyState>;
  const warned = data.filter((d) => d.warnings.length);
  return (
    <>
      <DataTable columns={columns} data={data} filename="nexus-materials" title="Materials" searchPlaceholder="Search materials" pageSize={10}
        facets={[{ id: "kind", label: "Types", options: Object.entries(KIND).map(([v, [, l]]) => ({ value: v, label: l })) }, { id: "role", label: "Roles", options: Object.entries(ROLE).map(([v, l]) => ({ value: v, label: l })) }]}
        onRowClick={(d) => router.push(`/subjects/${id}/materials/${d.id}`)} />
      {warned.length > 0 && (
        <details className="mt-3 rounded-xl border border-mid/25 bg-mid-bg/50 px-4 py-2 text-sm">
          <summary className="cursor-pointer font-semibold text-[#7A4A00]">{plural(warned.length, "file")} with notes about how they were read</summary>
          <ul className="mt-2 space-y-1.5 pb-2">{warned.flatMap((d) => d.warnings.map((w, i) => <li key={`${d.id}-${i}`}><b>{d.title}:</b> {w}</li>))}</ul>
        </details>
      )}
    </>
  );
}

function Topics({ id }) {
  const { data } = useQuery({ queryKey: keys.topics(id), queryFn: () => getTopics(id) });
  if (!data?.length) return null;
  const max = Math.max(...data.map((t) => t.passages), 1);
  return (
    <Card className="p-5">
      <SectionTitle>Topics found <span className="ml-1 text-sm font-normal text-muted">{data.length}</span></SectionTitle>
      <ul className="grid gap-x-6 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
        {data.map((t) => (
          <li key={t.id} className="min-w-0">
            <div className="flex items-baseline justify-between gap-2 text-sm"><span className="truncate" title={t.path}>{t.name}</span><span className="tabular shrink-0 text-[12px] text-muted">{t.passages}</span></div>
            <div className="mt-1 h-1 rounded-full bg-brand-soft/70"><div className="h-full rounded-full bg-brand/70" style={{ width: `${(100 * t.passages) / max}%` }} /></div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function SearchBox({ id }) {
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const { data, isFetching, error } = useQuery({ queryKey: keys.search(id, q), queryFn: () => getSearch(id, q), enabled: q.length > 0 });
  const strong = data?.results.filter((r) => r.relevant) ?? [];
  const weak = data?.results.filter((r) => !r.relevant).slice(0, 3) ?? [];
  return (
    <section aria-labelledby="search-h">
      <SectionTitle id="search-h">Search this subject</SectionTitle>
      <form role="search" onSubmit={(e) => { e.preventDefault(); setQ(text.trim().slice(0, 200)); }} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
          <Input aria-label="Search your materials" placeholder="e.g. binary tree traversal" value={text} maxLength={200} onChange={(e) => setText(e.target.value)} className="pl-9" />
        </div>
        <Button type="submit">Search</Button>
      </form>
      <div className="mt-3 space-y-3" aria-live="polite">
        {error && <Alert tone="danger">{error.message}</Alert>}
        {q && isFetching && <Skeleton className="h-20" />}
        {data && !isFetching && data.results.length === 0 && <p className="text-sm text-muted">No passage in this subject matches. Try other words, or upload material that covers it.</p>}
        {data && !isFetching && strong.map((r) => <PassageCard key={r.passage_id} subjectId={id} item={r} terms={data.terms} />)}
        {data && !isFetching && strong.length === 0 && weak.length > 0 && <p className="text-sm text-muted">No passage matches most of your words. These contain only some of them:</p>}
        {data && !isFetching && weak.map((r) => <PassageCard key={r.passage_id} subjectId={id} item={r} terms={data.terms} weak />)}
      </div>
    </section>
  );
}

export default function MaterialsPage() {
  const { id } = useParams();
  const { data: subject } = useQuery({ queryKey: keys.subject(id), queryFn: () => getSubject(id) });
  useTitle("Materials", subject?.name);
  return (
    <div className="space-y-6">
      <UploadPanel subjectId={id} />
      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 className="font-display text-lg font-semibold">Your files</h2><Capabilities /></div>
        <Documents id={id} />
      </div>
      <Topics id={id} />
      <SearchBox id={id} />
    </div>
  );
}
