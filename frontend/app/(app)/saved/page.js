"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Bookmark, BookmarkX } from "lucide-react";
import { api } from "@/lib/api";
import { getSaved, keys } from "@/lib/queries";
import { dateTime } from "@/lib/format";
import { friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { STATUS, StatusBadge } from "@/components/nexus/answer";
import { EmptyState, ErrorState, PageHeader } from "@/components/nexus/common";
import { DataTable } from "@/components/nexus/data-table";
import { Badge, Button, Skeleton } from "@/components/ui/primitives";

export default function SavedPage() {
  useTitle("Saved answers");
  const router = useRouter();
  const qc = useQueryClient();
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.saved, queryFn: getSaved });
  const unsave = useMutation({
    mutationFn: (r) => api(`/subjects/${r.subject_id}/questions/${r.id}/saved`, { method: "PUT", json: { saved: false } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.saved }); toast.success("Removed from saved"); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const columns = useMemo(() => [
    { accessorKey: "question", header: "Question", cell: ({ row }) => <Link href={`/subjects/${row.original.subject_id}/ask/${row.original.id}`} className="font-semibold" onClick={(e) => e.stopPropagation()}>{row.original.question}</Link> },
    { accessorKey: "subject", header: "Subject", cell: ({ getValue }) => <Badge tone="neutral">{getValue()}</Badge> },
    { id: "status", accessorFn: (r) => STATUS[r.status]?.label ?? r.status, header: "Outcome", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
    { accessorKey: "created_at", header: "Asked", cell: ({ getValue }) => dateTime(getValue()) },
    { id: "x", header: "", enableSorting: false, enableHiding: false, meta: { export: false }, cell: ({ row }) => <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); unsave.mutate(row.original); }} aria-label={`Remove from saved: ${row.original.question}`}><BookmarkX className="h-4 w-4" />Remove</Button> },
  ], [unsave]);
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-40" />;
  return (
    <div>
      <PageHeader title="Saved answers" description="Answers you bookmarked in the Ask chat, from every subject." />
      {data.saved.length === 0 ? <EmptyState icon={Bookmark} title="Nothing saved yet">Use the bookmark button under an answer in the Ask chat to keep it here.</EmptyState>
        : <DataTable columns={columns} data={data.saved} filename="nexus-saved-answers" title="Saved answers" searchPlaceholder="Search saved answers" facets={[{ id: "subject", label: "Subjects" }]}
            onRowClick={(r) => router.push(`/subjects/${r.subject_id}/ask/${r.id}`)} />}
    </div>
  );
}
