"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, SearchX } from "lucide-react";
import { getSearchAll, keys } from "@/lib/queries";
import { pageLabel, plural } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { EmptyState, ErrorState, Highlighted, PageHeader } from "@/components/nexus/common";
import { Badge, Button, Card, Input, Segmented, Skeleton } from "@/components/ui/primitives";

function Results() {
  const router = useRouter();
  const q = (useSearchParams().get("q") ?? "").trim();
  const [text, setText] = useState(q);
  const [subject, setSubject] = useState("all");
  useTitle(q ? `Search: ${q}` : "Search");
  const { data, error, isFetching, refetch } = useQuery({ queryKey: keys.searchAll(q), queryFn: () => getSearchAll(q), enabled: q.length > 0 });
  const subjects = useMemo(() => [...new Map((data?.results ?? []).map((r) => [String(r.subject_id), r.subject])).entries()], [data]);
  const shown = (data?.results ?? []).filter((r) => subject === "all" || String(r.subject_id) === subject);
  return (
    <div>
      <PageHeader title="Search materials" description="Every subject of yours is searched; each result links to the exact passage." />
      <form role="search" className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setSubject("all"); router.push(`/search?q=${encodeURIComponent(text.trim())}`); }}>
        <div className="relative flex-1"><Search className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" /><Input value={text} onChange={(e) => setText(e.target.value)} aria-label="Words to look for" placeholder="e.g. enqueue operation" maxLength={200} className="h-12 pl-11 text-base" autoFocus /></div>
        <Button type="submit" size="lg" className="h-12">Search</Button>
      </form>
      <div className="mt-6" aria-live="polite">
        {!q ? <p className="text-sm text-muted">Type the words you remember.</p>
          : error ? <ErrorState error={error} onRetry={refetch} />
          : isFetching && !data ? <Skeleton className="h-40" />
          : data && data.results.length === 0 ? <EmptyState icon={SearchX} title="Nothing found">None of your materials contain those words together. Try fewer or different words.</EmptyState>
          : data && (
            <>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-muted">{plural(data.results.length, "passage")} in {plural(subjects.length, "subject")}</p>
                {subjects.length > 1 && <Segmented label="Subject" value={subject} onValueChange={setSubject} options={[{ value: "all", label: "All" }, ...subjects.map(([v, l]) => ({ value: v, label: l }))]} />}
              </div>
              <ul className="space-y-3">
                {shown.map((r) => (
                  <li key={`${r.subject_id}-${r.passage_id}`}>
                    <Card className="p-4">
                      <p className="break-anywhere flex flex-wrap items-center gap-2 text-[12.5px] text-muted">
                        <Badge tone="brand">{r.subject}</Badge><b className="text-foreground">{r.document}</b>{r.heading_path && <span>{r.heading_path.split(" › ").pop()}</span>}{r.page_start != null && <Badge tone="outline">{pageLabel(r.page_start, r.page_end)}</Badge>}
                      </p>
                      <p className="break-anywhere evidence mt-2 whitespace-pre-wrap rounded-r-md px-3 py-2 text-sm leading-relaxed"><Highlighted text={r.text} terms={data.terms} /></p>
                      <Link className="mt-2 inline-block text-sm font-semibold" href={`/subjects/${r.subject_id}/materials/${r.document_id}#c${r.passage_id}`}>Open in the document</Link>
                    </Card>
                  </li>
                ))}
              </ul>
            </>
          )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return <Suspense fallback={<Skeleton className="h-32" />}><Results /></Suspense>;
}
