"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, ThumbsDown, ThumbsUp, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { getQuestion, keys } from "@/lib/queries";
import { friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { AnswerView, JobProgress, PassagesView, StatusBadge } from "@/components/nexus/answer";
import { ErrorState, RunTrace } from "@/components/nexus/common";
import { Button, ConfirmDialog, Skeleton } from "@/components/ui/primitives";

export default function QuestionPage() {
  const { id, qid } = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const { data: q, isPending, error, refetch } = useQuery({
    queryKey: keys.question(id, qid),
    queryFn: () => getQuestion(id, qid),
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 2500 : false), // poll until the job is done
  });
  useTitle(q?.question.slice(0, 50), "Ask");
  const feedback = useMutation({
    mutationFn: (value) => api(`/subjects/${id}/questions/${qid}/feedback`, { method: "POST", json: { value } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.question(id, qid) }); qc.invalidateQueries({ queryKey: keys.questions(id) }); toast.success("Thanks, noted"); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const remove = useMutation({
    mutationFn: () => api(`/subjects/${id}/questions/${qid}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.questions(id) }); qc.invalidateQueries({ queryKey: keys.subjects }); toast.success("Question deleted"); router.replace(`/subjects/${id}/ask`); },
    onError: (e) => { toast.error(friendlyError(e)); setOpen(false); },
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-40" />;
  return (
    <div>
      <Link href={`/subjects/${id}/ask`} className="mb-3 inline-flex items-center gap-1 text-sm font-semibold no-underline hover:underline">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Ask
      </Link>
      <h2 className="break-anywhere font-display text-2xl font-semibold">{q.question}</h2>
      <p className="mt-2"><StatusBadge status={q.status} kind={q.kind} /></p>

      <div className="mt-5">
        {q.status === "pending" ? (
          <JobProgress createdAt={q.created_at} what="Reading your materials and writing an answer…" />
        ) : q.status === "answered" ? (
          <AnswerView q={q} />
        ) : (
          <><PassagesView q={q} /><RunTrace steps={q.steps} loop={q.loop} title="What happened" /></>
        )}
      </div>

      {q.status !== "pending" && (
        <div className="mt-8 flex flex-wrap items-center gap-2 border-t border-border pt-4">
          {q.status === "answered" && (
            <>
              <Button variant="secondary" size="sm" onClick={() => feedback.mutate("helpful")} aria-pressed={q.feedback === "helpful"}><ThumbsUp className="h-4 w-4" aria-hidden="true" /> This helped</Button>
              <Button variant="secondary" size="sm" onClick={() => feedback.mutate("wrong")} aria-pressed={q.feedback === "wrong"}><ThumbsDown className="h-4 w-4" aria-hidden="true" /> This looks wrong</Button>
              {q.feedback && <span className="text-xs text-muted">You marked this “{q.feedback}”.</span>}
            </>
          )}
          <Button variant="danger-outline" size="sm" className="ml-auto" onClick={() => setOpen(true)}><Trash2 className="h-4 w-4" aria-hidden="true" />Delete</Button>
          <ConfirmDialog open={open} onOpenChange={setOpen} title="Delete this question?" description="The question and its answer are removed. Your materials are not touched." confirm="Delete" loading={remove.isPending} onConfirm={() => remove.mutate()} />
        </div>
      )}

    </div>
  );
}
