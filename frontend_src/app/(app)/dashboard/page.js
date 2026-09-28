"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, BookOpen, CheckSquare, ChevronRight, Clock, ClipboardList, Timer } from "lucide-react";
import { Area, AreaChart, Bar as RBar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Asset, Panel, Ring, SourceBadge } from "@/components/nexus/kit";
import { COMPETENCY, DASHBOARD_RECOMMENDED, LEARNING, MONTHLY_ACTIVITY, OFFICER, PROGRESS_TREND } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";
import { cn } from "@/lib/utils";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good Morning" : h < 17 ? "Good Afternoon" : "Good Evening";
}

const STATS = [
  { value: LEARNING.ongoingCount, label: "Ongoing Courses", Icon: BookOpen, tone: "text-[#1464E8] bg-[#E6F0FF]", href: "/learn" },
  { value: LEARNING.pendingAssessments, label: "Pending Assessments", Icon: ClipboardList, tone: "text-[#E5484D] bg-[#FDECEC]", href: "/assess" },
  { value: LEARNING.completedCount, label: "Completed Courses", Icon: CheckSquare, tone: "text-[#16A36A] bg-[#E3F7EE]", href: "/profile" },
];

const ICON_TINT = { statistics: "bg-[#FDEDEE]", skills: "bg-[#E6F0FF]", progress: "bg-[#FFF3DC]" };

function StatCard({ value, label, Icon, tone, href, compact = false }) {
  return (
    <Link href={href} className={cn("flex items-center gap-3 rounded-2xl border border-[#E3ECF8] bg-white no-underline shadow-[0_2px_14px_rgb(20_100_232/.06)] transition-shadow hover:shadow-lift",
      compact ? "flex-col items-start gap-1.5 p-3" : "p-5")}>
      <span className={cn("grid shrink-0 place-items-center rounded-xl", tone, compact ? "h-8 w-8" : "h-12 w-12")}><Icon className={compact ? "h-4 w-4" : "h-6 w-6"} aria-hidden="true" /></span>
      <span className="min-w-0">
        <span className={cn("block font-extrabold leading-none text-[#0B2A5B]", compact ? "text-[20px]" : "text-[28px]")}>{value}</span>
        <span className={cn("mt-1 block leading-tight text-[#5A6E8C]", compact ? "text-[11px]" : "text-[13px]")}>{label}</span>
      </span>
    </Link>
  );
}

function RecommendCard({ r }) {
  return (
    <Link href={`/learn/${r.id}`} className="group relative flex min-w-[260px] snap-start flex-col rounded-2xl border border-[#E3ECF8] bg-white p-5 no-underline shadow-[0_2px_14px_rgb(20_100_232/.06)] transition-shadow hover:shadow-lift lg:min-w-0">
      <div className="flex items-start justify-between">
        <SourceBadge source={r.badge} />
        <ChevronRight className="h-4 w-4 text-[#E5484D] transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
      </div>
      <div className="mt-3 flex items-end justify-between gap-3">
        <div>
          <p className="text-[16px] font-bold leading-snug text-[#0B2A5B]">{r.title}</p>
          <p className="mt-2 flex items-center gap-1.5 text-[13px] text-[#5A6E8C]"><Clock className="h-3.5 w-3.5" aria-hidden="true" />{r.weeks} weeks</p>
        </div>
        <span className={cn("grid h-14 w-14 shrink-0 place-items-center rounded-2xl", ICON_TINT[r.icon])}><Asset name={`icon-${r.icon}`} className="h-10 w-10" /></span>
      </div>
    </Link>
  );
}

const tip = { contentStyle: { borderRadius: 10, border: "1px solid #E3ECF8", fontSize: 12 }, cursor: { fill: "#EAF4FF" } };

export default function DashboardPage() {
  useTitle("Dashboard · NEXUS");
  const [hello, setHello] = useState("Good Morning");
  useEffect(() => setHello(greeting()), []);

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <motion.header initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-[22px] font-bold leading-tight text-[#0B2A5B] lg:text-[26px]">
          {hello},<br className="lg:hidden" /> <span className="text-[26px] lg:text-[26px]">{OFFICER.name}</span> <span aria-hidden="true">👋</span>
        </h1>
        <p className="mt-1 text-[14px] text-[#33476A]">{OFFICER.designation}</p>
        <p className="hidden text-[14px] text-[#33476A] lg:block">{OFFICER.department}</p>
      </motion.header>

      {/* Score + stats */}
      <div className="grid gap-4 lg:grid-cols-[1.35fr_1fr_1fr_1fr]">
        <Link href="/competency" className="flex items-center gap-5 rounded-2xl border border-[#E3ECF8] bg-white p-5 no-underline shadow-[0_2px_14px_rgb(20_100_232/.06)] hover:shadow-lift">
          <Ring value={COMPETENCY.overallScore} size={96} stroke={13} label={false} className="hidden lg:block" />
          <Ring value={COMPETENCY.overallScore} size={128} stroke={16} className="lg:hidden" />
          <span>
            <span className="block text-[34px] font-extrabold leading-none text-[#0B2A5B] lg:text-[28px]">{COMPETENCY.overallScore}%</span>
            <span className="mt-1 hidden text-[13px] leading-tight text-[#5A6E8C] lg:block">Competency<br />Score</span>
          </span>
        </Link>
        <div className="grid grid-cols-3 gap-3 lg:hidden">{STATS.map((s) => <StatCard key={s.label} {...s} compact />)}</div>
        {STATS.map((s) => <div key={s.label} className="hidden lg:block"><StatCard {...s} /></div>)}
      </div>

      {/* Banner */}
      <div className="relative hidden h-[124px] overflow-hidden rounded-2xl bg-gradient-to-r from-[#DCEBFF] via-[#E8F2FF] to-[#D3E5FF] px-7 lg:flex lg:items-center">
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 900 124" preserveAspectRatio="none" aria-hidden="true">
          <path d="M420 124 C 560 40, 700 110, 900 30 L900 124 Z" fill="#C3DAFB" opacity=".55" />
        </svg>
        <div className="relative">
          <p className="text-[22px] font-bold text-[#0B2A5B]">Keep Learning, Keep Growing</p>
          <p className="mt-1 text-[15px] text-[#33476A]">Smarter Skills | Stronger India</p>
        </div>
        <Asset name="learning-progress" className="absolute bottom-0 right-10 h-[118px] w-auto" />
      </div>

      {/* Recommended */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[18px] font-bold text-[#0B2A5B]">Recommended for You</h2>
          <Link href="/learn" className="flex items-center gap-1 text-[14px] font-semibold text-[#1464E8] no-underline">View All <ArrowRight className="h-4 w-4" /></Link>
        </div>
        <div className="nx-noscroll -mx-4 flex snap-x gap-4 overflow-x-auto px-4 pb-1 lg:mx-0 lg:grid lg:grid-cols-3 lg:overflow-visible lg:px-0">
          {DASHBOARD_RECOMMENDED.map((r) => <RecommendCard key={r.id} r={r} />)}
        </div>
      </section>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr_0.8fr]">
        <Panel>
          <h2 className="mb-3 text-[16px] font-bold text-[#0B2A5B]">Monthly Learning Activity</h2>
          <div className="h-[170px]">
            <ResponsiveContainer>
              <BarChart data={MONTHLY_ACTIVITY} margin={{ left: -24, right: 4, top: 6 }}>
                <defs><linearGradient id="nx-bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#1464E8" /><stop offset="100%" stopColor="#8DB9FF" /></linearGradient></defs>
                <CartesianGrid vertical={false} stroke="#EEF3FA" />
                <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#5A6E8C" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#8193B0" }} />
                <Tooltip {...tip} formatter={(v) => [`${v} h`, "Learning"]} />
                <RBar dataKey="hours" fill="url(#nx-bar)" radius={[6, 6, 0, 0]} barSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel>
          <h2 className="mb-3 text-[16px] font-bold text-[#0B2A5B]">Learning Progress</h2>
          <div className="h-[170px]">
            <ResponsiveContainer>
              <AreaChart data={PROGRESS_TREND} margin={{ left: -24, right: 8, top: 6 }}>
                <defs><linearGradient id="nx-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#1464E8" stopOpacity={0.28} /><stop offset="100%" stopColor="#1464E8" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid vertical={false} stroke="#EEF3FA" />
                <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#5A6E8C" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#8193B0" }} />
                <Tooltip {...tip} formatter={(v) => [`${v}%`, "Competency"]} />
                <Area dataKey="value" stroke="#1464E8" strokeWidth={2.5} fill="url(#nx-area)" dot={{ r: 3.5, fill: "#1464E8" }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-1">
          <div className="flex items-center gap-3 rounded-2xl border border-[#D5F0E3] bg-[#EEFAF4] p-5">
            <BookOpen className="h-8 w-8 shrink-0 text-[#16A36A]" aria-hidden="true" />
            <p className="text-[14px] leading-tight text-[#33476A]"><b className="text-[18px] text-[#0B2A5B]">{LEARNING.completedCount}</b> Courses<br />Completed</p>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-[#E3ECF8] bg-white p-5">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#1464E8] text-white"><Timer className="h-5 w-5" aria-hidden="true" /></span>
            <p className="text-[14px] leading-tight text-[#33476A]"><b className="text-[18px] text-[#0B2A5B]">{LEARNING.totalHours}</b> Hours<br />Learned</p>
          </div>
        </div>
      </div>
    </div>
  );
}
