"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowDown, CalendarClock, PlayCircle, Search, Target } from "lucide-react";
import { Panel, SourceBadge } from "@/components/nexus/kit";
import { Button } from "@/components/ui/primitives";
import { DIAGNOSIS as D } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";
import { cn } from "@/lib/utils";

function Link_({ step, i }) {
  const root = step.root;
  return (
    <motion.li initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + i * 0.15 }}>
      {i > 0 && (
        <div className="flex items-center gap-2 py-1.5 pl-5 text-[12px] font-medium text-[#8193B0]">
          <ArrowDown className="h-4 w-4" aria-hidden="true" />depends on
        </div>
      )}
      <div className={cn("flex items-center gap-3 rounded-xl border px-4 py-3",
        root ? "border-[#F5B5B5] bg-[#FDECEC]" : "border-[#E3ECF8] bg-white")}>
        <span className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-full text-[13px] font-extrabold",
          root ? "bg-[#E5484D] text-white" : "bg-[#EEF3FA] text-[#0B2A5B]")}>{step.score}%</span>
        <span className="min-w-0 flex-1">
          <span className="block text-[15px] font-bold text-[#0B2A5B]">{step.topic}</span>
          <span className={cn("block text-[12.5px]", root ? "font-semibold text-[#C0282D]" : "text-[#5A6E8C]")}>{root ? "Root cause" : step.note}</span>
        </span>
      </div>
    </motion.li>
  );
}

/** Root-cause diagnosis: where the errors showed, the prerequisite that explains them, why to fix it first, and what happens next. */
export default function DiagnosisPage() {
  useTitle("Root-cause Diagnosis · NEXUS");
  const a = D.assessment;
  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="hidden text-[26px] font-bold text-[#0B2A5B] lg:block">Root-cause Diagnosis</h1>

      <Panel className="flex items-center gap-3 p-4">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#FFF3DC] text-[#C27800]"><Search className="h-5 w-5" aria-hidden="true" /></span>
        <div className="min-w-0 flex-1">
          <p className="text-[12.5px] text-[#5A6E8C]">Assessment · {a.date}</p>
          <p className="text-[15px] font-bold text-[#0B2A5B]">{a.title}: {a.correct} of {a.total} correct</p>
        </div>
      </Panel>

      <Panel className="p-4">
        <h2 className="mb-3 text-[16px] font-bold text-[#0B2A5B]">Why the errors happened</h2>
        <ol>{D.chain.map((s, i) => <Link_ key={s.topic} step={s} i={i} />)}</ol>
        <ul className="mt-3 space-y-1.5 rounded-xl bg-[#F3F7FD] px-4 py-3 text-[13px] text-[#33476A]">
          <li className="font-semibold text-[#0B2A5B]">Evidence</li>
          {D.evidence.map((e) => <li key={e} className="flex gap-2"><span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#1464E8]" />{e}</li>)}
        </ul>
      </Panel>

      <Panel className="p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[16px] font-bold text-[#0B2A5B]">Fix this first</h2>
          <span className="rounded-lg bg-[#0B2A5B] px-2.5 py-1 text-[12px] font-bold text-white">Priority {D.priority.score}</span>
        </div>
        <dl className="mt-3 divide-y divide-[#EEF3FA] text-[13.5px]">
          {D.priority.factors.map((f) => (
            <div key={f.label} className="flex justify-between gap-3 py-2"><dt className="text-[#5A6E8C]">{f.label}</dt><dd className="text-right font-semibold text-[#0B2A5B]">{f.value}</dd></div>
          ))}
        </dl>
        <p className="mt-2 flex items-start gap-2 rounded-xl bg-[#FFF6E5] px-3 py-2.5 text-[13px] text-[#7A4A00]">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Self-rated <b>{D.confidenceGap.rated}</b>, tested <b>{D.confidenceGap.tested}%</b>: a confidence gap.</span>
        </p>
      </Panel>

      <Panel className="p-4">
        <div className="flex items-start gap-3">
          <Target className="mt-0.5 h-5 w-5 shrink-0 text-[#16A36A]" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="text-[15px] font-bold leading-snug text-[#0B2A5B]">{D.action.title}</p>
            <p className="mt-1 flex items-center gap-2 text-[12.5px] text-[#5A6E8C]"><SourceBadge source={D.action.source} />{D.action.minutes} min refresher</p>
          </div>
        </div>
        <Button asChild size="lg" className="mt-3 w-full rounded-xl bg-[#0B2A5B] hover:bg-[#123A78]">
          <Link href="/diagnosis/retest"><PlayCircle className="h-4 w-4" />Start refresher</Link>
        </Button>
        <p className="mt-2 flex items-center justify-center gap-1.5 text-[12.5px] text-[#5A6E8C]"><CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />Re-test scheduled for {D.action.retest}</p>
      </Panel>
    </div>
  );
}
