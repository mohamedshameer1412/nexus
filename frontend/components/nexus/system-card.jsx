"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { RefreshCw, ScanText, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { getSystem, keys } from "@/lib/queries";
import { friendlyError } from "@/lib/utils";
import { Badge, Button, Card, Progress, Skeleton } from "@/components/ui/primitives";

/** What this server can do: semantic search (embeddings) and OCR, with a way to embed what is missing. */
export function SystemCard() {
  const qc = useQueryClient();
  const { data, isPending } = useQuery({ queryKey: keys.system, queryFn: getSystem, refetchInterval: 15_000 });
  const reindex = useMutation({
    mutationFn: () => api("/system/reindex", { method: "POST" }),
    onSuccess: (r) => { toast[r.scheduled ? "success" : "info"](r.scheduled ? "Embedding started in the background" : "Semantic search is off on this server"); qc.invalidateQueries({ queryKey: keys.system }); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  if (isPending) return <Skeleton className="mt-6 h-40" />;
  const s = data.semantic, o = data.ocr;
  const pct = s.passages ? Math.round((100 * s.indexed) / s.passages) : 0;
  return (
    <Card className="mt-6 p-5">
      <h2 className="font-display text-lg font-semibold">Search and OCR</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-border p-4">
          <p className="flex items-center gap-2 font-semibold"><Sparkles className="h-4 w-4 text-brand" />Semantic search <Badge tone={s.enabled ? "strong" : "muted"} dot className="ml-auto">{s.enabled ? "On" : "Off"}</Badge></p>
          <p className="mt-1 text-[13px] text-muted">{s.enabled ? `Local embeddings (${s.model}) find passages that say the same thing in other words. Nothing leaves this server.` : `Keyword search only: ${s.reason}.`}</p>
          <div className="mt-3 flex items-center gap-2"><Progress value={pct} /><span className="tabular shrink-0 text-xs text-muted">{s.indexed}/{s.passages}</span></div>
          <Button variant="secondary" size="sm" className="mt-3" onClick={() => reindex.mutate()} loading={reindex.isPending} disabled={!s.enabled || s.indexed >= s.passages}><RefreshCw className="h-4 w-4" />Embed missing passages</Button>
        </div>
        <div className="rounded-xl border border-border p-4">
          <p className="flex items-center gap-2 font-semibold"><ScanText className="h-4 w-4 text-brand" />OCR for scans and photos <Badge tone={o.engine ? "strong" : "muted"} dot className="ml-auto">{o.engine ? o.label : "Off"}</Badge></p>
          <p className="mt-1 text-[13px] text-muted">{o.engine ? `Scanned PDF pages and photos of notes are read with ${o.label} (languages: ${o.languages.join(", ")}), up to ${o.max_pages} pages per file.` : `Scanned pages cannot be read: ${o.reason}.`}</p>
        </div>
      </div>
    </Card>
  );
}
