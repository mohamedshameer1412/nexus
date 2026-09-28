"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Download, FileText, ScanText, ShieldAlert, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { getDoc, keys } from "@/lib/queries";
import { friendlyError, pageLabel, plural } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { ErrorState } from "@/components/nexus/common";
import { Alert, Badge, Button, Card, ConfirmDialog, Input, Segmented, Skeleton } from "@/components/ui/primitives";

const TINTS = ["#0194E2", "#0E9F8E", "#7C5CFA", "#F2A516", "#E5484D", "#0369A8", "#14B8A6", "#8B5CF6"];

/** Consecutive passages that share a section become one topic block, so topic boundaries are visible. */
function sections(passages) {
  const out = [];
  for (const p of passages) {
    const key = p.heading_path || "Untitled section";
    const last = out[out.length - 1];
    if (last && last.key === key) last.items.push(p);
    else out.push({ key, idx: out.length, name: key.split(" › ").pop(), trail: key.split(" › ").slice(0, -1).join(" › "), items: [p] });
  }
  return out;
}

export default function DocumentPage() {
  const { id, docId } = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const [view, setView] = useState("text");
  const [filter, setFilter] = useState("");
  const { data, isPending, error, refetch } = useQuery({ queryKey: keys.doc(id, docId), queryFn: () => getDoc(id, docId) });
  const remove = useMutation({
    mutationFn: () => api(`/subjects/${id}/materials/${docId}`, { method: "DELETE" }),
    onSuccess: () => {
      for (const k of [keys.docs(id), keys.topics(id), keys.subject(id), keys.subjects]) qc.invalidateQueries({ queryKey: k });
      toast.success("Material removed");
      router.replace(`/subjects/${id}/materials`);
    },
    onError: (e) => { toast.error(friendlyError(e)); setConfirm(false); },
  });
  const groups = useMemo(() => sections(data?.passages ?? []), [data]);
  useTitle(data?.document.title, "Materials");
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <div className="space-y-3"><Skeleton className="h-10 w-72" /><Skeleton className="h-64" /></div>;
  const { document: d, passages } = data;
  const fileUrl = `/api/v1/subjects/${id}/materials/${docId}/file`;
  const hasOriginal = ["pdf", "image", "txt", "docx"].includes(d.kind);
  const f = filter.trim().toLowerCase();
  const shown = f ? groups.map((g) => ({ ...g, items: g.items.filter((p) => p.text.toLowerCase().includes(f)) })).filter((g) => g.items.length) : groups;

  return (
    <div>
      <Link href={`/subjects/${id}/materials`} className="mb-3 inline-flex items-center gap-1 text-sm font-semibold no-underline hover:underline"><ArrowLeft className="h-4 w-4" />All materials</Link>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="break-anywhere font-display text-2xl font-semibold">{d.title}</h2>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge tone="outline">{d.kind.toUpperCase()}</Badge>
            {d.pages ? <Badge tone="neutral">{plural(d.pages, "page")}</Badge> : null}
            <Badge tone="neutral">{plural(d.chunks, "passage")}</Badge>
            <Badge tone="neutral">{plural(groups.length, "section")}</Badge>
            {d.ocr_pages > 0 && <Badge tone="mid"><ScanText className="h-3 w-3" />{plural(d.ocr_pages, "page")} read with OCR</Badge>}
            <Badge tone={d.status === "parsed" ? "strong" : "weak"} dot>{d.status === "parsed" ? "Ready" : d.status}</Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {hasOriginal && <Button asChild variant="secondary" size="sm"><a href={fileUrl} download className="no-underline"><Download className="h-4 w-4" />Original</a></Button>}
          <Button variant="danger-outline" size="sm" onClick={() => setConfirm(true)}><Trash2 className="h-4 w-4" />Remove</Button>
        </div>
      </div>
      {d.kind === "url" && <p className="break-anywhere mt-2 text-sm">Web page: <a href={d.source} target="_blank" rel="noopener noreferrer">{d.source}</a> (as it was when you added it)</p>}
      <div className="mt-3 space-y-2">{d.warnings.map((w) => <Alert key={w} tone="warning">{w}</Alert>)}</div>

      {(d.kind === "pdf" || d.kind === "image") && (
        <Segmented className="mt-5" label="View" value={view} onValueChange={setView}
          options={[{ value: "text", label: "Extracted text", icon: FileText }, { value: "original", label: d.kind === "pdf" ? "Original PDF" : "Original image" }]} />
      )}

      {view === "original" && d.kind === "pdf" && <Card className="mt-4 overflow-hidden"><iframe src={fileUrl} title={`${d.title} (PDF)`} className="h-[78vh] w-full border-0" /></Card>}
      {view === "original" && d.kind === "image" && <Card className="mt-4 p-4"><img src={fileUrl} alt={d.title} className="mx-auto max-h-[78vh] w-auto rounded-lg" /></Card>}

      {view === "text" && (
        <div className="mt-5 lg:grid lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-6">
          <aside className="mb-4 lg:sticky lg:top-28 lg:mb-0 lg:self-start">
            <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Find in this document" aria-label="Find in this document" className="h-9 text-sm" />
            <nav aria-label="Sections" className="nx-scroll-light mt-3 max-h-[60vh] overflow-y-auto">
              <p className="mb-1.5 text-[12px] font-semibold text-muted">Sections</p>
              <ol className="space-y-0.5">
                {groups.map((g, i) => (
                  <li key={g.key + i}>
                    <a href={`#sec-${i}`} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] text-foreground no-underline hover:bg-brand-wash">
                      <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: TINTS[i % TINTS.length] }} aria-hidden="true" />
                      <span className="truncate">{g.name}</span><span className="tabular ml-auto text-[11.5px] text-muted">{g.items.length}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
          </aside>
          <div className="space-y-5">
            {passages.length === 0 && <p className="text-sm text-muted">Nothing could be extracted from this file.</p>}
            {f && shown.length === 0 && <p className="text-sm text-muted">No passage contains “{filter}”.</p>}
            {shown.map((g) => {
              const tint = TINTS[g.idx % TINTS.length];
              return (
                <section key={g.idx} id={`sec-${g.idx}`} className="scroll-mt-32 overflow-hidden rounded-xl border border-border bg-surface shadow-card">
                  <header className="flex items-center gap-3 border-b border-border px-4 py-3" style={{ background: `${tint}12`, borderLeft: `4px solid ${tint}` }}>
                    <div className="min-w-0">
                      <h3 className="truncate font-display text-[16px] font-semibold">{g.name}</h3>
                      {g.trail && <p className="truncate text-[12px] text-muted">{g.trail}</p>}
                    </div>
                    <Badge tone="outline" className="ml-auto">{plural(g.items.length, "passage")}</Badge>
                  </header>
                  <div className="divide-y divide-border/70">
                    {g.items.map((p) => (
                      <article key={p.id} id={`c${p.id}`} className="px-4 py-3">
                        <p className="mb-1 flex flex-wrap items-center gap-2 text-[11.5px] text-muted"><span className="tabular">#{p.ordinal + 1}</span>{p.page_start != null && <span>{pageLabel(p.page_start, p.page_end)}</span>}</p>
                        {p.quarantined && <Alert tone="warning" icon={ShieldAlert} className="mb-2">Not used for answers: it reads like instructions to an AI ({p.flag_reason}).</Alert>}
                        <p className="break-anywhere whitespace-pre-wrap text-[14.5px] leading-relaxed">{p.text}</p>
                      </article>
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      )}
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title="Remove this material?" confirm="Remove" loading={remove.isPending} onConfirm={() => remove.mutate()}
        description="Its passages disappear from search, questions and quizzes. This cannot be undone." />
    </div>
  );
}
