"use client";
import Link from "next/link";
import { Shield, Target, Play, Clock, CheckCircle2, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import { useTitle } from "@/lib/use-title";
import { ASSESSMENTS } from "@/lib/nexus-data";

export default function AssessPage() {
  useTitle("Assessments · NEXUS");

  const pending = ASSESSMENTS.filter((a) => a.status === "pending");
  const completed = ASSESSMENTS.filter((a) => a.status === "completed");

  return (
    <div className="pb-24 lg:pb-8">
      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="mb-6">
        <h1 className="text-[22px] font-black leading-tight text-foreground lg:text-[26px]">
          Competency Assessments
        </h1>
        <p className="mt-1 text-[13.5px] text-muted max-w-2xl">
          Take AI-powered diagnostic tests to identify your skill gaps. Assessments adapt to your responses in real time to accurately estimate your competency level.
        </p>
      </motion.div>

      {/* ── Pending Assessments ── */}
      <section className="mb-8">
        <h2 className="mb-4 text-[16px] font-bold text-foreground flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-[#F2A900]" />
          Action Required
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {pending.map((a, i) => (
            <motion.div key={a.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: i * 0.1 }}>
              <div className="flex flex-col gap-3 rounded-xl bg-surface p-5 shadow-card border border-border">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#FEF3C7]">
                      <Shield className="h-5 w-5 text-[#F2A900]" />
                    </span>
                    <div>
                      <h3 className="text-[15px] font-semibold text-foreground">{a.title}</h3>
                      <p className="text-[12.5px] text-muted mt-0.5">{a.domain}</p>
                    </div>
                  </div>
                  <span className="inline-flex items-center rounded-full bg-[#FEF3C7] px-2 py-0.5 text-[10.5px] font-bold text-[#F2A900]">
                    DUE {a.dueDate.toUpperCase()}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between border-t border-border pt-4">
                  <div className="flex items-center gap-4 text-[12.5px] text-muted">
                    <span className="flex items-center gap-1.5"><Clock className="h-4 w-4" /> {a.duration}</span>
                    <span className="flex items-center gap-1.5"><Target className="h-4 w-4" /> {a.questions} Qs</span>
                  </div>
                  <button className="flex items-center gap-1.5 rounded-lg bg-[#1464E8] px-4 py-2 text-[13px] font-semibold text-white hover:bg-[#0B2A5B] transition-colors shadow-sm">
                    <Play className="h-4 w-4" fill="currentColor" /> Start
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Completed Assessments ── */}
      <section>
        <h2 className="mb-4 text-[16px] font-bold text-foreground flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-[#16A36A]" />
          Completed
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {completed.map((a, i) => (
            <motion.div key={a.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 + (i * 0.1) }}>
              <div className="flex items-center justify-between gap-3 rounded-xl bg-surface-2 p-4 shadow-sm border border-border">
                <div>
                  <h3 className="text-[14px] font-semibold text-foreground">{a.title}</h3>
                  <p className="text-[12px] text-muted mt-0.5">Completed {a.dueDate}</p>
                </div>
                <div className="text-right">
                  <p className="text-[18px] font-black text-[#16A36A]">{a.score}%</p>
                  <p className="text-[11px] font-medium text-muted uppercase tracking-wider">Score</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
