"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Check, Flame, Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardBody, CardHeader } from "@/components/ui/primitives";

/** Study streak (days in a row with any study) and a daily goal ring. The goal is a personal setting kept in this browser. */
export function StreakCard({ streak }) {
  const [goal, setGoal] = useState(streak.goal);
  useEffect(() => { try { const g = Number(localStorage.getItem("nexus.goal")); if (g) setGoal(Math.min(100, Math.max(1, g))); } catch {} }, []);
  const change = (d) => setGoal((g) => { const n = Math.min(100, Math.max(1, g + d)); try { localStorage.setItem("nexus.goal", String(n)); } catch {} return n; });
  const pct = Math.min(100, Math.round((streak.today / goal) * 100));
  const done = streak.today >= goal;
  const r = 42, c = 2 * Math.PI * r;
  return (
    <Card className="h-full">
      <CardHeader title="Streak and daily goal" description="Quiz answers and flashcards today (UTC)." />
      <CardBody>
        <div className="flex items-center gap-5">
          <div className="relative h-28 w-28 shrink-0" role="img" aria-label={`${streak.today} of ${goal} answered today`}>
            <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden="true">
              <circle cx="50" cy="50" r={r} fill="none" strokeWidth="10" stroke="rgb(217 238 251)" />
              <motion.circle cx="50" cy="50" r={r} fill="none" strokeWidth="10" strokeLinecap="round" stroke={done ? "#0E8A5F" : "#0194E2"} strokeDasharray={c}
                initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - pct / 100) }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }} />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center"><span className="tabular font-display text-2xl font-semibold">{streak.today}</span><span className="text-xs text-muted">of {goal}</span></div>
          </div>
          <div className="min-w-0 text-sm">
            <p className="flex items-center gap-1.5 font-display text-xl font-semibold"><Flame className={cn("h-5 w-5", streak.days > 0 ? "text-[#F2A516]" : "text-muted")} aria-hidden="true" />{streak.days} {streak.days === 1 ? "day" : "days"}</p>
            <p className="text-muted">{done ? "Goal reached today." : streak.days > 0 ? "in a row. Answer today to keep it going." : "Answer a question today to start a streak."}</p>
            <div className="mt-3 flex items-center gap-1.5">
              <span className="text-xs text-muted">Daily goal</span>
              <button type="button" onClick={() => change(-5)} aria-label="Lower the daily goal" className="grid h-8 w-8 place-items-center rounded-md border border-border hover:bg-brand-wash"><Minus className="h-4 w-4" /></button>
              <b className="tabular min-w-7 text-center">{goal}</b>
              <button type="button" onClick={() => change(5)} aria-label="Raise the daily goal" className="grid h-8 w-8 place-items-center rounded-md border border-border hover:bg-brand-wash"><Plus className="h-4 w-4" /></button>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

/** First-run guide as a numbered path (the steps really are a sequence). Disappears once every step is done. */
export function Onboarding({ totals, firstSubjectId }) {
  const base = firstSubjectId ? `/subjects/${firstSubjectId}` : "/subjects";
  const steps = [
    { done: totals.subjects > 0, label: "Create a subject", href: "/subjects?new=1" },
    { done: totals.materials > 0, label: "Upload notes, a PDF or a photo", href: `${base}/materials` },
    { done: totals.questions > 0, label: "Ask a question and check its sources", href: `${base}/ask` },
    { done: totals.practice_questions > 0, label: "Generate practice questions", href: `${base}/practice` },
    { done: totals.quizzes > 0, label: "Take a diagnostic quiz", href: `${base}/quiz` },
  ];
  const doneCount = steps.filter((s) => s.done).length;
  if (doneCount === steps.length) return null;
  const next = steps.findIndex((s) => !s.done);
  return (
    <Card className="mb-6 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 px-5 pt-4">
        <h2 className="font-display text-[17px] font-semibold">Set up your study space</h2>
        <span className="tabular text-sm text-muted">{doneCount} of {steps.length} done</span>
      </div>
      <ol className="grid gap-2 p-4 sm:grid-cols-5">
        {steps.map((s, i) => (
          <li key={s.label}>
            <Link href={s.href} className={cn("flex h-full items-start gap-3 rounded-lg border p-3 text-sm no-underline transition-colors",
              s.done ? "border-strong/20 bg-strong-bg/60 text-muted" : i === next ? "border-brand bg-brand-wash text-foreground shadow-[0_0_0_3px_rgb(1_148_226/.12)]" : "border-border text-foreground hover:bg-brand-wash")}>
              <span className={cn("grid h-6 w-6 shrink-0 place-items-center rounded-full text-[12px] font-bold", s.done ? "bg-strong text-white" : i === next ? "bg-brand text-white" : "bg-brand-soft text-brand-deep")}>
                {s.done ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : i + 1}
              </span>
              <span className={cn("font-medium", s.done && "line-through")}>{s.label}</span>
            </Link>
          </li>
        ))}
      </ol>
    </Card>
  );
}
