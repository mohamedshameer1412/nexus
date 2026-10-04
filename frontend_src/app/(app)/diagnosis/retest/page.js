"use client";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, RotateCcw, TrendingUp } from "lucide-react";
import { Panel } from "@/components/nexus/kit";
import { RETEST as R } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";
import { cn } from "@/lib/utils";

function Bar({ value, target, tone }) {
  return (
    <div className="relative h-3 w-full rounded-full bg-[#E4EEFB]">
      <motion.div className={cn("h-full rounded-full", tone === "after" ? "bg-gradient-to-r from-[#34C38F] to-[#16A36A]" : "bg-[#F08A8D]")}
        initial={{ width: 0 }} animate={{ width: `${value}%` }} transition={{ duration: 0.9, ease: "easeOut" }} />
      {target && <span className="absolute -top-1 h-5 w-0.5 rounded bg-[#0B2A5B]" style={{ left: `${target}%` }} aria-hidden="true" />}
    </div>
  );
}

/** Closing the loop: the same skill re-tested after the refresher, what it changed downstream, and the replan. */
export default function RetestPage() {
  useTitle("Re-test Result · NEXUS");
  const gain = R.after.score - R.before.score;
  return (
    <div className="mx-auto max-w-xl space-y-3 lg:space-y-4">
      <h1 className="hidden text-[26px] font-bold text-[#0B2A5B] lg:block">Re-test Result</h1>

      <Panel className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[12.5px] text-[#5A6E8C]">Re-test · {R.date}</p>
            <p className="text-[17px] font-bold text-[#0B2A5B]">{R.topic}</p>
          </div>
          <span className="flex items-center gap-1 rounded-lg bg-[#E3F7EE] px-2.5 py-1 text-[12.5px] font-bold text-[#16A36A]"><CheckCircle2 className="h-4 w-4" />Gap closed</span>
        </div>
        <div className="mt-3 space-y-2.5">
          <div>
            <div className="mb-1 flex justify-between text-[13px]"><span className="text-[#5A6E8C]">Before · {R.before.date}</span><b className="text-[#C0282D]">{R.before.score}%</b></div>
            <Bar value={R.before.score} target={R.target} />
          </div>
          <div>
            <div className="mb-1 flex justify-between text-[13px]"><span className="text-[#5A6E8C]">After · {R.after.date}</span><b className="text-[#16A36A]">{R.after.score}%</b></div>
            <Bar value={R.after.score} target={R.target} tone="after" />
          </div>
        </div>
        <p className="mt-3 flex items-center justify-between text-[12.5px] text-[#5A6E8C]">
          <span>Marker = {R.target}% role target</span>
          <span className="flex items-center gap-1 text-[15px] font-extrabold text-[#16A36A]"><TrendingUp className="h-4 w-4" />+{gain} pts</span>
        </p>
      </Panel>

      <Panel className="p-4">
        <h2 className="mb-2 text-[16px] font-bold text-[#0B2A5B]">Effect on dependent topics</h2>
        <ul className="divide-y divide-[#EEF3FA]">
          {R.downstream.map((d) => (
            <li key={d.topic} className="flex items-center gap-2 py-2 text-[14px]">
              <span className="flex-1 text-[#33476A]">{d.topic}</span>
              <span className="text-[#8193B0]">{d.before}%</span><ArrowRight className="h-3.5 w-3.5 text-[#8193B0]" />
              <b className={d.after >= R.target ? "text-[#16A36A]" : "text-[#C27800]"}>{d.after}%</b>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel className="p-4">
        <h2 className="text-[16px] font-bold text-[#0B2A5B]">Competency updated</h2>
        <div className="mt-2 grid grid-cols-2 gap-3 text-center">
          <div className="rounded-xl bg-[#F3F7FD] px-2 py-2.5">
            <p className="text-[12px] text-[#5A6E8C]">{R.competency.domain}</p>
            <p className="mt-1 text-[17px] font-extrabold text-[#0B2A5B]">{R.competency.before}% → <span className="text-[#16A36A]">{R.competency.after}%</span></p>
          </div>
          <div className="rounded-xl bg-[#F3F7FD] px-2 py-2.5">
            <p className="text-[12px] text-[#5A6E8C]">Overall competency</p>
            <p className="mt-1 text-[17px] font-extrabold text-[#0B2A5B]">{R.competency.overallBefore}% → <span className="text-[#16A36A]">{R.competency.overallAfter}%</span></p>
          </div>
        </div>
      </Panel>

      <Panel className="p-4">
        <ol className="flex items-center justify-between" aria-label="Learning loop">
          {R.loop.map((s, i) => (
            <li key={s} className="flex flex-col items-center gap-1 text-[11px] font-semibold text-[#33476A]">
              <span className={cn("grid h-7 w-7 place-items-center rounded-full text-white", i < R.loop.length - 1 ? "bg-[#16A36A]" : "bg-[#1464E8]")}>
                {i < R.loop.length - 1 ? <CheckCircle2 className="h-4 w-4" /> : <RotateCcw className="h-4 w-4" />}
              </span>{s}
            </li>
          ))}
        </ol>
        <div className="mt-3 rounded-xl border border-[#BFD6FA] bg-[#E6F0FF] px-4 py-2.5">
          <p className="text-[12px] font-semibold text-[#1464E8]">Replanned: next step</p>
          <p className="text-[14.5px] font-bold text-[#0B2A5B]">{R.next.title}</p>
          <p className="text-[12.5px] text-[#33476A]">{R.next.detail} · re-test {R.next.retest}</p>
        </div>
      </Panel>
    </div>
  );
}
