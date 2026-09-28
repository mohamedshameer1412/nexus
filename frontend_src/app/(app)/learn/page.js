"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, CheckSquare, Clock3, Square } from "lucide-react";
import { Asset, Bar, Panel, StatusPill } from "@/components/nexus/kit";
import { Button } from "@/components/ui/primitives";
import { COURSE_DETAILS, CURRENT_LEARNING, LEARNING_PATH, SOURCES } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";
import { cn } from "@/lib/utils";

const DOT = { completed: "bg-[#16A36A]", "in-progress": "bg-[#1464E8]", "not-started": "bg-[#AFC0D6]" };
const LINE = { completed: "bg-[#16A36A]", "in-progress": "bg-[#1464E8]", "not-started": "bg-[#D6E1EF]" };
const TAG = {
  completed: ["Completed", "text-[#16A36A] bg-[#E3F7EE]"],
  "in-progress": ["In Progress", "text-[#1464E8] bg-[#E6F0FF]"],
  "not-started": ["Not Started", "text-[#5A6E8C] bg-[#EEF2F7]"],
};

function Step({ step, i, last }) {
  return (
    <motion.li initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }} className="relative flex gap-4 pb-5">
      {!last && <span className={cn("absolute left-[19px] top-10 h-[calc(100%-24px)] w-[3px] rounded-full", LINE[step.status])} aria-hidden="true" />}
      <span className={cn("relative z-10 mt-5 grid h-10 w-10 shrink-0 place-items-center rounded-full text-[15px] font-bold text-white shadow-[0_0_0_5px_#F3F7FD]", DOT[step.status])}>{i + 1}</span>
      <Link href={`/learn/${step.id}`} className="flex flex-1 gap-4 rounded-2xl border border-[#E3ECF8] bg-white p-4 no-underline shadow-[0_2px_14px_rgb(20_100_232/.06)] transition-shadow hover:shadow-lift">
        <span className={cn("grid h-14 w-14 shrink-0 place-items-center rounded-xl", step.status === "completed" ? "bg-[#E3F7EE]" : "bg-[#E6F0FF]")}><Asset name={`icon-${step.icon}`} className="h-10 w-10" /></span>
        <span className="min-w-0">
          <span className="block text-[15px] font-bold leading-snug text-[#0B2A5B]">{step.title}</span>
          <span className="mt-1 block text-[13px] text-[#5A6E8C]">{SOURCES[step.badge]} • {step.weeks} weeks</span>
          <span className="mt-2 block"><StatusPill status={step.status} /></span>
        </span>
      </Link>
    </motion.li>
  );
}

export default function LearningPathPage() {
  useTitle("My Learning Path · NEXUS");
  const current = COURSE_DETAILS[CURRENT_LEARNING.courseId];
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.05fr]">
      <section>
        <header className="mb-5 hidden lg:block">
          <h1 className="text-[26px] font-bold text-[#0B2A5B]">My Learning Path</h1>
          <p className="mt-1 text-[14px] text-[#5A6E8C]">A personalized journey for your growth.</p>
        </header>
        <ol>{LEARNING_PATH.map((s, i) => <Step key={s.id} step={s} i={i} last={i === LEARNING_PATH.length - 1} />)}</ol>
      </section>

      <aside className="space-y-4 lg:pt-2">
        <Panel>
          <p className="text-[14px] font-semibold text-[#33476A]">Current Learning</p>
          <p className="mt-1 text-[17px] font-bold text-[#0B2A5B]">{current.title}</p>
        </Panel>
        <Panel>
          <p className="text-[40px] font-extrabold leading-none text-[#0B2A5B]">{CURRENT_LEARNING.progress}%</p>
          <Bar value={CURRENT_LEARNING.progress} height={12} className="mt-4" />
          <div className="mt-3 flex justify-between text-[13px] text-[#5A6E8C]">
            <span>Week {CURRENT_LEARNING.week} of {CURRENT_LEARNING.weeks}</span><span>{CURRENT_LEARNING.modulesLeft} modules left</span>
          </div>
          <Button asChild size="lg" className="mt-5 w-full rounded-xl bg-[#0B2A5B] text-[15px] shadow-[0_6px_18px_rgb(11_42_91/.25)] hover:bg-[#123A78]">
            <Link href={`/learn/${CURRENT_LEARNING.courseId}`}>Continue Learning <ArrowRight className="h-4 w-4" /></Link>
          </Button>
        </Panel>
        <Panel>
          <h2 className="mb-3 text-[16px] font-bold text-[#0B2A5B]">Learning Resources</h2>
          <ul className="space-y-2.5">
            {current.modules.map((m) => {
              const [label, cls] = TAG[m.status];
              const Icon = m.status === "completed" ? CheckSquare : Square;
              return (
                <li key={m.title} className="flex items-center gap-3 rounded-xl border border-[#E3ECF8] px-3 py-2.5">
                  <Icon className={cn("h-4 w-4 shrink-0", m.status === "completed" ? "text-[#16A36A]" : "text-[#1464E8]")} aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate text-[13px] text-[#33476A]">{m.title}</span>
                  <span className="hidden items-center gap-1 text-[12px] text-[#8193B0] sm:flex"><Clock3 className="h-3.5 w-3.5" />{m.hours}h</span>
                  <span className={cn("shrink-0 rounded-md px-2 py-1 text-[11.5px] font-semibold", cls)}>{label}</span>
                </li>
              );
            })}
          </ul>
        </Panel>
      </aside>
    </div>
  );
}
