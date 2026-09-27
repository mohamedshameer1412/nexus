"use client";
import Link from "next/link";
import { BookOpen, Clock, Play, TrendingUp, Search, Filter } from "lucide-react";
import { motion } from "framer-motion";
import { useTitle } from "@/lib/use-title";
import { COURSES } from "@/lib/nexus-data";

export default function LearnPage() {
  useTitle("Learning · NEXUS");

  const ongoing = COURSES.filter((c) => c.status === "ongoing");
  const completed = COURSES.filter((c) => c.status === "completed");

  const BADGE_STYLE = {
    igot: "bg-[#1464E8] text-white",
    tpac: "bg-[#16A36A] text-white",
    nssta: "bg-[#7C5CFA] text-white",
  };

  const CourseBadge = ({ badge }) => {
    const label = { igot: "iGOT", tpac: "TPAC", nssta: "NSSTA" }[badge] ?? badge;
    return (
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${BADGE_STYLE[badge] ?? "bg-border text-foreground"}`}>
        {label}
      </span>
    );
  };

  return (
    <div className="pb-24 lg:pb-8">
      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] font-black leading-tight text-foreground lg:text-[26px]">
            Learning Center
          </h1>
          <p className="mt-1 text-[13.5px] text-muted max-w-xl">
            Access your iGOT Karmayogi courses, TPAC recommendations, and track your capacity building progress.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
            <input 
              type="text" 
              placeholder="Search courses..." 
              className="h-10 w-full sm:w-64 rounded-lg border border-border bg-surface pl-9 pr-4 text-[13px] outline-none focus:border-[#1464E8] focus:ring-1 focus:ring-[#1464E8] transition-all"
            />
          </div>
          <button className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface hover:bg-surface-2 transition-colors">
            <Filter className="h-4 w-4 text-foreground" />
          </button>
        </div>
      </motion.div>

      {/* ── Ongoing Courses ── */}
      <section className="mb-8">
        <h2 className="mb-4 text-[16px] font-bold text-foreground flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-[#1464E8]" />
          In Progress
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {ongoing.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: i * 0.1 }}>
              <div className="flex flex-col gap-3 rounded-xl bg-surface p-5 shadow-card border border-border h-full">
                <div className="min-w-0 flex-1">
                  <CourseBadge badge={c.badge} />
                  <h3 className="mt-2 text-[15px] font-semibold leading-snug text-foreground">{c.title}</h3>
                  <div className="mt-1.5 flex items-center gap-2 text-[12.5px] text-muted">
                    <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {c.duration}</span>
                    <span className="text-border">·</span>
                    <span className="truncate">{c.domain}</span>
                  </div>
                </div>
                <div className="mt-2">
                  <div className="mb-1.5 flex items-center justify-between text-[12px]">
                    <span className="text-muted">Progress</span>
                    <span className="font-bold text-[#1464E8]">{c.progress}%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-[#EAF4FF]">
                    <div className="h-full rounded-full bg-[#1464E8] transition-all duration-1000" style={{ width: `${c.progress}%` }} />
                  </div>
                </div>
                <button className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-[#1464E8] px-4 py-2.5 text-[13px] font-semibold text-white hover:bg-[#0B2A5B] transition-colors shadow-sm">
                  <Play className="h-4 w-4" fill="currentColor" /> Continue Learning
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Completed Courses ── */}
      <section>
        <h2 className="mb-4 text-[16px] font-bold text-foreground flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-[#16A36A]" />
          Completed
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {completed.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 + (i * 0.1) }}>
              <div className="flex flex-col justify-between gap-3 rounded-xl bg-surface-2 p-5 shadow-sm border border-border h-full">
                <div>
                  <CourseBadge badge={c.badge} />
                  <h3 className="mt-2 text-[14.5px] font-semibold leading-snug text-foreground text-opacity-80">{c.title}</h3>
                  <div className="mt-1.5 flex items-center gap-2 text-[12px] text-muted">
                    <span>{c.domain}</span>
                  </div>
                </div>
                <button className="mt-2 flex items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-[12.5px] font-semibold text-foreground hover:bg-surface-2 transition-colors">
                  Review Material
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
