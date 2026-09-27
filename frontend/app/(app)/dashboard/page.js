"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Award, BarChart2, BookOpen, BrainCircuit, Briefcase, ChevronRight,
  Clock, FileText, GraduationCap, LayoutDashboard, MessageSquare,
  Play, Route, Settings, Shield, Target, TrendingUp, Users, Zap,
} from "lucide-react";
import { motion } from "framer-motion";
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from "recharts";
import { OFFICER, COMPETENCY, LEARNING, COURSES, RECOMMENDATIONS, MONTHLY_ACTIVITY, ASSESSMENTS, CAREER_PATH } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";

// ─── helpers ─────────────────────────────────────────────────────────────────
function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good Morning" : h < 17 ? "Good Afternoon" : "Good Evening";
}

function ScoreRing({ score, size = 96 }) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="comp-ring -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EAF4FF" strokeWidth={8} />
      <motion.circle
        cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke="#1464E8" strokeWidth={8} strokeLinecap="round"
        strokeDasharray={`${dash} ${circ}`}
        initial={{ strokeDasharray: `0 ${circ}` }}
        animate={{ strokeDasharray: `${dash} ${circ}` }}
        transition={{ duration: 1.2, ease: "easeOut", delay: 0.3 }}
      />
    </svg>
  );
}

const BADGE_STYLE = {
  igot: "bg-[#1464E8] text-white",
  tpac: "bg-[#16A36A] text-white",
  nssta: "bg-[#7C5CFA] text-white",
  assessment: "bg-[#F2A900] text-[#3D2800]",
};

function CourseBadge({ badge }) {
  const label = { igot: "iGOT", tpac: "TPAC", nssta: "NSSTA", assessment: "Assessment" }[badge] ?? badge;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${BADGE_STYLE[badge] ?? "bg-border text-foreground"}`}>
      {label}
    </span>
  );
}

function DomainBar({ domain, delay = 0 }) {
  const color = domain.score >= 70 ? "#16A36A" : domain.score >= 55 ? "#F2A900" : "#D64545";
  return (
    <div className="flex items-center gap-3">
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-[13px] font-medium text-foreground">{domain.label}</span>
          <span className="tabular text-[13px] font-bold" style={{ color }}>{domain.score}%</span>
        </div>
        <div className="domain-bar">
          <motion.div
            className="domain-bar-fill" style={{ background: color }}
            initial={{ width: 0 }} animate={{ width: `${domain.score}%` }}
            transition={{ duration: 0.9, ease: "easeOut", delay }}
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sub = "", tone, href = null, delay = 0 }) {
  const toneClasses = {
    blue:  { bg: "bg-[#EAF4FF]", icon: "text-[#1464E8]" },
    green: { bg: "bg-[#D1FAE5]", icon: "text-[#16A36A]" },
    amber: { bg: "bg-[#FEF3C7]", icon: "text-[#F2A900]" },
    navy:  { bg: "bg-[#EAF4FF]", icon: "text-[#0B2A5B]" },
  };
  const t = toneClasses[tone] ?? toneClasses.blue;
  const inner = (
    <div className="flex items-start justify-between">
      <div>
        <p className="text-[12.5px] font-semibold text-muted">{label}</p>
        <p className="tabular mt-1 text-[26px] font-black leading-none text-foreground">{value}</p>
        {sub && <p className="mt-1 text-[11.5px] text-muted">{sub}</p>}
      </div>
      <span className={`grid h-10 w-10 place-items-center rounded-xl ${t.bg}`}>
        <Icon className={`h-5 w-5 ${t.icon}`} />
      </span>
    </div>
  );

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay }}>
      {href ? (
        <Link href={href} className="block rounded-xl border border-border bg-surface p-4 shadow-card transition-shadow hover:shadow-lift cursor-pointer">
          {inner}
        </Link>
      ) : (
        <div className="block rounded-xl border border-border bg-surface p-4 shadow-card transition-shadow">
          {inner}
        </div>
      )}
    </motion.div>
  );
}

function CourseCard({ course, delay = 0 }) {
  const ongoing = course.status === "ongoing";
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay }}>
      <div className="rounded-xl border border-border bg-surface p-4 shadow-card flex flex-col gap-3 h-full">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <CourseBadge badge={course.badge} />
            <p className="mt-1.5 text-[14px] font-semibold leading-snug text-foreground line-clamp-2">{course.title}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[12px] text-muted">
          <Clock className="h-3.5 w-3.5" />
          <span>{course.duration}</span>
          <span className="text-border">·</span>
          <span className="truncate">{course.domain}</span>
        </div>
        {ongoing && (
          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[11.5px] text-muted">Progress</span>
              <span className="tabular text-[11.5px] font-bold text-[#1464E8]">{course.progress}%</span>
            </div>
            <div className="domain-bar">
              <motion.div className="domain-bar-fill"
                initial={{ width: 0 }} animate={{ width: `${course.progress}%` }}
                transition={{ duration: 0.8, ease: "easeOut", delay: delay + 0.2 }}
              />
            </div>
          </div>
        )}
        <button className="mt-auto flex items-center gap-1.5 rounded-lg bg-[#1464E8] px-3 py-2 text-[12.5px] font-semibold text-white hover:bg-[#0B2A5B] transition-colors">
          {ongoing ? <Play className="h-3.5 w-3.5" /> : <TrendingUp className="h-3.5 w-3.5" />}
          {ongoing ? "Continue" : "Review"}
        </button>
      </div>
    </motion.div>
  );
}

function RecommendCard({ rec, delay = 0 }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay }}>
      <div className="rounded-xl border border-border bg-surface p-4 shadow-card flex flex-col gap-2.5">
        <div className="flex items-start justify-between gap-2">
          <CourseBadge badge={rec.badge} />
          <span className="flex items-center gap-1 text-[11px] font-semibold text-[#16A36A]">
            <Zap className="h-3 w-3" />{Math.round(rec.confidence * 100)}% match
          </span>
        </div>
        <p className="text-[14px] font-semibold leading-snug text-foreground">{rec.title}</p>
        <p className="text-[11.5px] text-muted leading-snug">{rec.gap}</p>
        <div className="flex items-center gap-2 text-[11.5px] text-muted">
          <Clock className="h-3.5 w-3.5" />{rec.duration}
          <span className="text-border">·</span>
          {rec.domain}
        </div>
        <button className="mt-1 flex items-center justify-center gap-1.5 rounded-lg border border-[#1464E8] px-3 py-1.5 text-[12.5px] font-semibold text-[#1464E8] hover:bg-[#EAF4FF] transition-colors">
          {rec.type === "assessment" ? "Take Assessment" : "Enrol Now"} <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </motion.div>
  );
}

// ─── Custom Chart Tooltip ─────────────────────────────────────────────────────
function ChartTip({ active = false, payload = [], label = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-[12.5px] shadow-pop">
      <p className="font-semibold text-foreground mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: <b>{p.value}{p.unit ?? ""}</b></p>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function NexusDashboardPage() {
  useTitle("Dashboard · NEXUS");
  const ongoing = COURSES.filter((c) => c.status === "ongoing");

  return (
    <div className="pb-24 lg:pb-8">

      {/* ── Greeting header ── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
        className="mb-6 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] font-black leading-tight text-foreground lg:text-[26px]">
            {greeting()}, <span className="text-[#1464E8]">{OFFICER.name}</span> 👋
          </h1>
          <p className="mt-0.5 text-[13.5px] text-muted">{OFFICER.designation} · {OFFICER.ministry}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/career"
            className="hidden sm:flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-[13px] font-semibold text-foreground shadow-card hover:shadow-lift transition-shadow">
            <Route className="h-4 w-4 text-[#1464E8]" />Career Path
          </Link>
          <Link href="/assess"
            className="flex items-center gap-1.5 rounded-lg bg-[#1464E8] px-3 py-2 text-[13px] font-semibold text-white hover:bg-[#0B2A5B] transition-colors shadow-card">
            <Target className="h-4 w-4" />Take Assessment
          </Link>
        </div>
      </motion.div>

      {/* ── Row 1: Competency ring + quick stats ── */}
      <div className="mb-5 grid gap-4 lg:grid-cols-[220px_1fr]">

        {/* Competency score card */}
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.45 }}
          className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-surface p-6 shadow-card text-center">
          <p className="text-[12.5px] font-bold uppercase tracking-widest text-muted">Competency Score</p>
          <div className="relative">
            <ScoreRing score={COMPETENCY.overallScore} size={110} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="tabular text-[28px] font-black leading-none text-foreground">{COMPETENCY.overallScore}%</span>
              <span className="text-[11px] font-semibold text-muted">{COMPETENCY.level}</span>
            </div>
          </div>
          <p className="text-[11.5px] text-muted">Last assessed {COMPETENCY.lastAssessed}</p>
        </motion.div>

        {/* Quick stat tiles */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <StatCard icon={BookOpen}       label="Ongoing Courses"     value={LEARNING.ongoingCount}       tone="blue"  delay={0.05} />
          <StatCard icon={FileText}       label="Pending Assessments" value={LEARNING.pendingAssessments} tone="amber" delay={0.1}  />
          <StatCard icon={GraduationCap}  label="Completed Courses"   value={LEARNING.completedCount}     tone="green" delay={0.15} />
          <StatCard icon={Clock}          label="Learning Hours"       value={`${LEARNING.totalHours}h`}  sub="total all time" tone="navy"  delay={0.2}  />
          <StatCard icon={TrendingUp}     label="This Month"           value={`${LEARNING.thisMonthHours}h`} sub="learning activity" tone="blue" delay={0.25} />
          <StatCard icon={Zap}            label="Day Streak"           value={`${LEARNING.streak}d`}      sub="keep it going!" tone="green" delay={0.3}  />
        </div>
      </div>

      {/* ── Row 2: Continue Learning (ongoing courses) ── */}
      <section className="mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[16px] font-bold text-foreground">Continue Learning</h2>
          <Link href="/learn" className="flex items-center gap-1 text-[13px] font-semibold text-[#1464E8] hover:underline">
            View all <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {ongoing.map((c, i) => <CourseCard key={c.id} course={c} delay={i * 0.08} />)}
        </div>
      </section>

      {/* ── Row 3: Recommended + Competency Overview ── */}
      <div className="mb-6 grid gap-5 xl:grid-cols-[1fr_320px]">

        {/* Recommended for You */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[16px] font-bold text-foreground">Recommended For You</h2>
            <span className="flex items-center gap-1 text-[12px] text-muted"><BrainCircuit className="h-4 w-4 text-[#1464E8]" />AI-powered</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {RECOMMENDATIONS.map((r, i) => <RecommendCard key={r.id} rec={r} delay={i * 0.08} />)}
          </div>
        </section>

        {/* Competency Overview */}
        <section>
          <h2 className="mb-3 text-[16px] font-bold text-foreground">Competency Overview</h2>
          <div className="rounded-xl border border-border bg-surface p-5 shadow-card flex flex-col gap-4">
            {COMPETENCY.domains.map((d, i) => (
              <DomainBar key={d.id} domain={d} delay={0.08 * i} />
            ))}
          </div>
        </section>
      </div>

      {/* ── Row 4: Analytics charts ── */}
      <div className="mb-6 grid gap-5 lg:grid-cols-2">

        {/* Monthly Learning Activity */}
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <h2 className="mb-1 text-[15px] font-bold text-foreground">Monthly Learning Activity</h2>
          <p className="mb-4 text-[12.5px] text-muted">Hours logged per month, last 6 months</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={MONTHLY_ACTIVITY} barSize={32}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} unit="h" />
              <Tooltip content={<ChartTip />} />
              <Bar dataKey="hours" name="Hours" fill="#1464E8" radius={[6, 6, 0, 0]} unit="h" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Competency progress over months */}
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <h2 className="mb-1 text-[15px] font-bold text-foreground">Learning Progress</h2>
          <p className="mb-4 text-[12.5px] text-muted">Courses completed per month</p>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={MONTHLY_ACTIVITY}>
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1464E8" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#1464E8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip content={<ChartTip />} />
              <Area dataKey="courses" name="Courses" stroke="#1464E8" strokeWidth={2}
                fill="url(#areaGrad)" dot={{ r: 4, fill: "#1464E8" }} type="monotone" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Row 5: Pending Assessments + Career Milestones ── */}
      <div className="grid gap-5 lg:grid-cols-2">

        {/* Pending Assessments */}
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-foreground">Pending Assessments</h2>
            <Link href="/assess" className="text-[13px] font-semibold text-[#1464E8] hover:underline">View all</Link>
          </div>
          <div className="flex flex-col gap-3">
            {ASSESSMENTS.filter((a) => a.status === "pending").map((a) => (
              <div key={a.id} className="flex items-center gap-3 rounded-xl bg-surface-2 border border-border px-4 py-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#FEF3C7]">
                  <Shield className="h-4.5 w-4.5 text-[#F2A900]" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[13.5px] font-semibold text-foreground truncate">{a.title}</p>
                  <p className="text-[12px] text-muted">{a.questions} questions · {a.duration} · Due {a.dueDate}</p>
                </div>
                <button className="shrink-0 rounded-lg bg-[#1464E8] px-3 py-1.5 text-[12px] font-semibold text-white hover:bg-[#0B2A5B] transition-colors">
                  Start
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Career Milestones */}
        <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
          <div className="mb-1 flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-foreground">Career Path</h2>
            <Link href="/career" className="text-[13px] font-semibold text-[#1464E8] hover:underline">Details</Link>
          </div>
          <p className="mb-4 text-[12.5px] text-muted">
            <span className="font-semibold text-foreground">{CAREER_PATH.current}</span>
            {" → "}<span className="font-semibold text-[#1464E8]">{CAREER_PATH.next}</span>
          </p>
          <div className="mb-4">
            <div className="mb-1 flex items-center justify-between text-[12.5px]">
              <span className="text-muted">Competency progress to promotion</span>
              <span className="font-bold text-[#1464E8]">{CAREER_PATH.currentCompetency}% / {CAREER_PATH.requiredCompetency}%</span>
            </div>
            <div className="domain-bar">
              <motion.div className="domain-bar-fill"
                initial={{ width: 0 }} animate={{ width: `${(CAREER_PATH.currentCompetency / CAREER_PATH.requiredCompetency) * 100}%` }}
                transition={{ duration: 1, ease: "easeOut", delay: 0.5 }}
              />
            </div>
          </div>
          <ul className="flex flex-col gap-2">
            {CAREER_PATH.milestones.map((m, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <span className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full text-white text-[11px] font-bold
                  ${m.done ? "bg-[#16A36A]" : "bg-[#D6E4F5] text-[#5A6E8C]"}`}>
                  {m.done ? "✓" : i + 1}
                </span>
                <span className={`text-[13px] ${m.done ? "text-muted line-through" : "text-foreground"}`}>{m.label}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

    </div>
  );
}
