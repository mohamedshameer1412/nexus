"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Brain } from "lucide-react";
import { api } from "@/lib/api";
import { getSelfCheck, keys } from "@/lib/queries";
import { SelfCheck as SelfCheckSchema } from "@/lib/schemas";
import { cn, friendlyError } from "@/lib/utils";
import { Alert, Badge, Button, Card, Skeleton } from "@/components/ui/primitives";

const VERDICT = {
  overconfident: { label: "Surer than your answers", tone: "mid" },
  underconfident: { label: "Better than you think", tone: "strong" },
  aligned: { label: "Feeling matches results", tone: "strong" },
  not_enough_answers: { label: "Needs 3+ answers", tone: "muted" },
  not_rated: { label: "Not rated", tone: "muted" },
};
const pc = (x) => `${Math.round(x * 100)}%`;

/** Rate how sure you feel about each topic (1 to 5) and see it beside what your answers show. */
export function SelfCheck({ id }) {
  const qc = useQueryClient();
  const { data, error, isPending } = useQuery({ queryKey: keys.selfCheck(id), queryFn: () => getSelfCheck(id) });
  const [draft, setDraft] = useState({});
  useEffect(() => { setDraft({}); }, [data]);
  const save = useMutation({
    mutationFn: async () => SelfCheckSchema.parse(await api(`/subjects/${id}/self-check`, { method: "PUT", json: { ratings: draft } })),
    onSuccess: (r) => { qc.setQueryData(keys.selfCheck(id), r); toast.success("Saved"); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  if (isPending) return <Skeleton className="h-32" />;
  if (error || data.topics.length === 0) return null;
  const labels = data.labels;
  const changed = Object.keys(draft).length > 0;
  return (
    <section aria-labelledby="self-h">
      <h2 id="self-h" className="mb-1 flex items-center gap-2 font-display text-lg font-semibold"><Brain className="h-5 w-5 text-brand" aria-hidden="true" />How sure do you feel?</h2>
      <p className="mb-3 text-sm text-muted">Rate each topic from 1 (lost) to 5 (very sure), then compare it with what your answers show. Feeling sure and being right are different things.</p>
      <Alert tone="info" className="mb-3" aria-live="polite">{data.message}</Alert>
      <ul className="grid gap-3 md:grid-cols-2">
        {data.topics.map((t) => {
          const rating = draft[t.topic_id] ?? t.rating;
          const v = VERDICT[t.verdict] ?? VERDICT.not_rated;
          return (
            <li key={t.topic_id}>
              <Card className="h-full p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="break-anywhere font-semibold">{t.name}</p>
                  <Badge tone={v.tone} className="ml-auto">{v.label}</Badge>
                </div>
                <div role="group" aria-label={`How sure are you about ${t.name}`} className="mt-2 flex flex-wrap gap-2">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n} type="button" aria-pressed={rating === n} title={labels[String(n)]}
                      onClick={() => setDraft((d) => ({ ...d, [t.topic_id]: n }))}
                      className={cn("inline-flex h-9 min-w-9 items-center justify-center rounded-lg border px-2.5 text-sm font-semibold transition-colors", rating === n ? "border-brand-deep bg-brand-deep text-white" : "border-border bg-surface hover:border-brand/40 hover:bg-brand-wash")}
                    >
                      {n}<span className="sr-only"> {labels[String(n)]}</span>
                    </button>
                  ))}
                  <span className="self-center text-xs text-muted">{rating ? labels[String(rating)] : "not rated"}</span>
                </div>
                {t.rating !== null && t.confidence !== null && (
                  <div className="mt-3 space-y-1.5 text-[12px] text-muted">
                    {[["Felt", t.perceived, "bg-brand/40"], ["Measured", t.confidence, "bg-brand"]].map(([k, v, c]) => (
                      <div key={k} className="flex items-center gap-2"><span className="w-16">{k}</span><span className="h-2 flex-1 rounded-full bg-brand-soft/60"><span className={cn("block h-full rounded-full", c)} style={{ width: `${Math.round(v * 100)}%` }} /></span><b className="tabular w-10 text-right text-foreground">{pc(v)}</b></div>
                    ))}
                    <p>{t.answered} answer{t.answered === 1 ? "" : "s"} behind the measured value.</p>
                  </div>
                )}
              </Card>
            </li>
          );
        })}
      </ul>
      <div className="mt-3"><Button onClick={() => save.mutate()} disabled={!changed} loading={save.isPending}>Save my ratings</Button></div>
    </section>
  );
}
