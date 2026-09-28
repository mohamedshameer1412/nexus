"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, Layers, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import { getFlashcards, getMcqAnswer, getSubject, keys } from "@/lib/queries";
import { cn, friendlyError, plural } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { EmptyState, ErrorState } from "@/components/nexus/common";
import { Badge, Button, Card, Kbd, Progress, Skeleton } from "@/components/ui/primitives";

const GRADES = [
  ["again", "Again", "Back in 10 minutes", "border-weak/40 text-weak hover:bg-weak-bg"],
  ["hard", "Hard", "Got it with effort", "border-mid/40 text-mid hover:bg-mid-bg"],
  ["good", "Good", "I knew it", "border-brand/40 text-brand-deep hover:bg-brand-wash"],
  ["easy", "Easy", "Much later", "border-strong/40 text-strong hover:bg-strong-bg"],
];

export default function FlashcardsPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const { data: subject } = useQuery({ queryKey: keys.subject(id), queryFn: () => getSubject(id) });
  useTitle("Flashcards", subject?.name);
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.flashcards(id), queryFn: () => getFlashcards(id), staleTime: Infinity, refetchOnWindowFocus: false });
  const [index, setIndex] = useState(0);
  const [shown, setShown] = useState(false);
  const [tally, setTally] = useState({ again: 0, hard: 0, good: 0, easy: 0 });
  const card = data?.cards[index];
  const answer = useQuery({ queryKey: ["fc-answer", id, card?.item_id], queryFn: () => getMcqAnswer(id, card.item_id), enabled: shown && !!card, staleTime: Infinity });
  const rate = useMutation({
    mutationFn: (grade) => api(`/subjects/${id}/flashcards/${card.item_id}/review`, { method: "POST", json: { grade } }),
    onSuccess: (_, grade) => { setShown(false); setTally((t) => ({ ...t, [grade]: t[grade] + 1 })); setIndex((i) => i + 1); qc.invalidateQueries({ queryKey: keys.dashboard }); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const onKey = useCallback((e) => {
    if (!card || e.target.closest?.("input,textarea,select")) return;
    if (e.key === " " || e.key === "Enter") { e.preventDefault(); setShown(true); }
    if (shown && !rate.isPending && ["1", "2", "3", "4"].includes(e.key)) rate.mutate(GRADES[Number(e.key) - 1][0]);
  }, [card, shown, rate]);
  useEffect(() => { window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey); }, [onKey]);

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-80" />;
  const back = <Link href={`/subjects/${id}/practice`} className="mb-3 inline-flex items-center gap-1 text-sm font-semibold no-underline hover:underline"><ArrowLeft className="h-4 w-4" />Practice</Link>;
  const reviewed = Object.values(tally).reduce((a, b) => a + b, 0);
  if (data.total === 0) return <div>{back}<EmptyState icon={Layers} title="No cards yet" action={<Button asChild><Link href={`/subjects/${id}/practice`}>Generate practice questions</Link></Button>}>Every practice question becomes a flashcard.</EmptyState></div>;
  if (!card) {
    return (
      <div className="mx-auto max-w-2xl">{back}
        <Card className="p-8 text-center">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-strong-bg text-strong"><CheckCircle2 className="h-7 w-7" /></span>
          <h2 className="mt-4 font-display text-2xl font-semibold">{reviewed ? `${plural(reviewed, "card")} reviewed` : "Nothing is due right now"}</h2>
          {reviewed > 0 && (
            <div className="mx-auto mt-5 grid max-w-md grid-cols-4 gap-2">
              {GRADES.map(([g, label]) => <div key={g} className="rounded-lg bg-surface-2 py-2"><p className="text-[12px] text-muted">{label}</p><p className="tabular font-display text-xl font-semibold">{tally[g]}</p></div>)}
            </div>
          )}
          <p className="mx-auto mt-4 max-w-md text-sm text-muted">{data.next_due ? `The next card is due ${new Date(data.next_due).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" })}. ` : ""}Cards you know come back later and later; cards you miss come back soon.</p>
          <Button className="mt-5" variant="secondary" onClick={() => { refetch(); setIndex(0); setTally({ again: 0, hard: 0, good: 0, easy: 0 }); }}><RotateCcw className="h-4 w-4" />Check again</Button>
        </Card>
      </div>
    );
  }
  const a = answer.data;
  return (
    <div className="mx-auto max-w-2xl">
      {back}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-display text-xl font-semibold"><Layers className="h-5 w-5 text-brand" />Flashcards</h2>
        <div className="flex gap-1.5"><Badge tone="neutral">{data.due} due</Badge><Badge tone="outline">{data.new} new</Badge></div>
      </div>
      <div className="mt-3 flex items-center gap-3"><Progress value={Math.round((index / data.cards.length) * 100)} aria-label="Session progress" /><span className="tabular shrink-0 text-[13px] text-muted">{index + 1} / {data.cards.length}</span></div>

      <div className="mt-5 [perspective:1400px]">
        <AnimatePresence mode="wait">
          <motion.div key={card.item_id} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={{ duration: 0.22 }}>
            <motion.div animate={{ rotateY: shown ? 180 : 0 }} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }} className="relative min-h-[22rem] [transform-style:preserve-3d]">
              <Card className="absolute inset-0 flex flex-col p-6 [backface-visibility:hidden]">
                <div className="flex items-center justify-between gap-2"><Badge tone="neutral" className="max-w-[70%] truncate">{card.topic?.split(" › ").pop()}</Badge>{card.is_new && <Badge tone="brand">New</Badge>}</div>
                <p className="break-anywhere mt-5 font-display text-[21px] font-semibold leading-snug">{card.question}</p>
                <ol className="mt-5 grid gap-2 sm:grid-cols-2">
                  {card.options.map((o, i) => <li key={i} className="break-anywhere rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm"><b className="text-brand-deep">{String.fromCharCode(65 + i)}.</b> {o}</li>)}
                </ol>
                <p className="mt-auto pt-5 text-center text-[12.5px] text-muted">Recall the answer, then flip. <Kbd>Space</Kbd></p>
              </Card>
              <Card className="absolute inset-0 flex flex-col overflow-y-auto p-6 [backface-visibility:hidden] [transform:rotateY(180deg)]">
                {!a ? <Skeleton className="h-full" /> : (
                  <>
                    <p className="text-[13px] font-semibold text-muted">Answer</p>
                    <p className="mt-1 flex items-start gap-2 font-display text-[20px] font-semibold text-strong"><CheckCircle2 className="mt-1 h-5 w-5 shrink-0" />{String.fromCharCode(65 + a.answer_index)}. {a.answer}</p>
                    {a.explanation && <p className="break-anywhere mt-3 text-sm">{a.explanation}</p>}
                    <blockquote className="break-anywhere evidence mt-3 rounded-r-md px-3 py-2 text-sm leading-relaxed">{a.quote}</blockquote>
                    <p className="mt-1 text-[12px] text-muted">{a.document}{a.heading_path ? ` · ${a.heading_path.split(" › ").pop()}` : ""}</p>
                  </>
                )}
              </Card>
            </motion.div>
          </motion.div>
        </AnimatePresence>
      </div>

      {!shown ? (
        <Button size="lg" className="mt-5 w-full" onClick={() => setShown(true)}>Show answer</Button>
      ) : (
        <div className="mt-5">
          <p className="mb-2 text-sm font-semibold">How well did you know it?</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {GRADES.map(([g, label, hint, cls], i) => (
              <button key={g} type="button" disabled={rate.isPending || !a} onClick={() => rate.mutate(g)}
                className={cn("flex flex-col items-center rounded-xl border bg-surface px-3 py-2.5 transition-colors disabled:opacity-50", cls)}>
                <span className="font-semibold">{label} <Kbd className="ml-1">{i + 1}</Kbd></span><span className="text-[12px] text-muted">{hint}</span>
              </button>
            ))}
          </div>
          <p className="mt-3 text-center text-[12.5px] text-muted">Rate honestly: the schedule only works if it reflects what you really remembered.</p>
        </div>
      )}
    </div>
  );
}
