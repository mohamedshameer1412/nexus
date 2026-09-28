"use client";
import Link from "next/link";
import { useState } from "react";
import { CheckCircle2, Circle, ClipboardList } from "lucide-react";
import { Legend, PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from "recharts";
import { Bar, Panel, PanelTitle, Ring, UnderlineTabs } from "@/components/nexus/kit";
import { ASSESSMENTS, CAREER_PATH, COMPETENCY, ROLE_BENCHMARK } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";
import { cn } from "@/lib/utils";

const TABS = ["Overview", "Domain Skills", "Career Path", "Assessment History"];
const SHORT = { stats: "Statistics", digital: "Digital", policy: "Policy", comms: "Communication", mgmt: "Management", domain: "Domain" };

function DomainBars() {
  return (
    <ul className="space-y-4">
      {COMPETENCY.domains.map((d) => (
        <li key={d.id}>
          <div className="mb-1.5 flex justify-between text-[14px] text-[#33476A]"><span>{d.label}</span><b className="text-[#0B2A5B]">{d.score}%</b></div>
          <Bar value={d.score} />
        </li>
      ))}
    </ul>
  );
}

function Overview() {
  const radar = COMPETENCY.domains.map((d) => ({ axis: SHORT[d.id], score: d.score, target: d.target }));
  return (
    <div className="grid gap-5 lg:grid-cols-[1.45fr_1fr]">
      <Panel className="flex flex-col items-center lg:block">
        <PanelTitle className="hidden lg:block">Your Competency Score</PanelTitle>
        <div className="flex flex-col items-center gap-6 lg:flex-row">
          <Ring value={COMPETENCY.overallScore} size={150} stroke={18} />
          <div className="hidden lg:block">
            <p className="text-[40px] font-extrabold leading-none text-[#0B2A5B]">{COMPETENCY.overallScore}%</p>
            <p className="mt-2 max-w-[220px] text-[14px] text-[#5A6E8C]">You are doing well! Keep learning to reach the next level.</p>
          </div>
        </div>
      </Panel>
      <Panel className="order-3 lg:order-none">
        <PanelTitle>Role Benchmark</PanelTitle>
        <p className="mb-2 text-[13px] text-[#5A6E8C]">Your Score</p>
        <div className="flex items-center gap-4"><Bar value={ROLE_BENCHMARK.yours} height={10} /><b className="w-12 text-right text-[16px] text-[#0B2A5B]">{ROLE_BENCHMARK.yours}%</b></div>
        <p className="mb-2 mt-4 text-[13px] text-[#5A6E8C]">Role target · {CAREER_PATH.next}</p>
        <div className="flex items-center gap-4"><Bar value={ROLE_BENCHMARK.target} tone="green" height={10} /><b className="w-12 text-right text-[16px] text-[#0B2A5B]">{ROLE_BENCHMARK.target}%</b></div>
        <p className="mt-4 text-[14px] font-medium text-[#16A36A]">You are on track! Continue learning</p>
      </Panel>
      <Panel>
        <PanelTitle>Competency Across Domains</PanelTitle>
        <DomainBars />
      </Panel>
      <Panel className="order-4 lg:order-none">
        <PanelTitle>Skill Radar</PanelTitle>
        <div className="h-[300px]">
          <ResponsiveContainer>
            <RadarChart data={radar} outerRadius="70%">
              <PolarGrid stroke="#D6E4F5" />
              <PolarAngleAxis dataKey="axis" tick={{ fontSize: 12, fill: "#33476A" }} />
              <Radar name="Your Score" dataKey="score" stroke="#1464E8" strokeWidth={2} fill="#1464E8" fillOpacity={0.28} dot={{ r: 3, fill: "#1464E8" }} />
              <Radar name="Target" dataKey="target" stroke="#16A36A" strokeWidth={2} fill="none" />
              <Legend iconType="plainline" wrapperStyle={{ fontSize: 13 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}

function DomainSkills() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {COMPETENCY.domains.map((d) => {
        const gap = d.target - d.score;
        return (
          <Panel key={d.id}>
            <p className="text-[15px] font-bold text-[#0B2A5B]">{d.label}</p>
            <div className="mt-3 flex items-end justify-between"><span className="text-[28px] font-extrabold text-[#0B2A5B]">{d.score}%</span><span className="text-[13px] text-[#5A6E8C]">Target {d.target}%</span></div>
            <Bar value={d.score} className="mt-2" />
            <p className={cn("mt-3 text-[13px] font-semibold", gap > 10 ? "text-[#C27800]" : "text-[#16A36A]")}>{gap > 10 ? `${gap} points below target` : "Close to target"}</p>
          </Panel>
        );
      })}
    </div>
  );
}

function CareerTab() {
  return (
    <Panel>
      <PanelTitle action={<Link href="/career" className="text-[14px] font-semibold text-[#1464E8] no-underline">Open Career Path</Link>}>{CAREER_PATH.current} → {CAREER_PATH.next}</PanelTitle>
      <p className="text-[14px] text-[#5A6E8C]">Required competency {CAREER_PATH.requiredCompetency}% · you are at {CAREER_PATH.currentCompetency}%</p>
      <Bar value={(CAREER_PATH.currentCompetency / CAREER_PATH.requiredCompetency) * 100} className="my-4" />
      <ul className="space-y-3">
        {CAREER_PATH.milestones.map((m) => (
          <li key={m.label} className="flex items-center gap-3 text-[14px] text-[#33476A]">
            {m.done ? <CheckCircle2 className="h-5 w-5 text-[#16A36A]" /> : <Circle className="h-5 w-5 text-[#B7C6DC]" />}{m.label}
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function HistoryTab() {
  return (
    <Panel className="p-0">
      <ul className="divide-y divide-[#EEF3FA]">
        {ASSESSMENTS.map((a) => (
          <li key={a.id} className="flex items-center gap-4 px-5 py-4">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#E6F0FF] text-[#1464E8]"><ClipboardList className="h-5 w-5" /></span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[14px] font-semibold text-[#0B2A5B]">{a.title}</p>
              <p className="text-[12.5px] text-[#5A6E8C]">{a.domain} · {a.questions} questions · {a.duration}</p>
            </div>
            {a.status === "completed" ? <b className="text-[15px] text-[#0B2A5B]">{a.score}%</b>
              : <Link href="/assess" className="rounded-lg bg-[#0B2A5B] px-3 py-1.5 text-[13px] font-semibold text-white no-underline">Start</Link>}
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export default function CompetencyPage() {
  useTitle("Competency Profile · NEXUS");
  const [tab, setTab] = useState(TABS[0]);
  return (
    <div className="space-y-5">
      <h1 className="hidden text-[26px] font-bold text-[#0B2A5B] lg:block">Competency Profile</h1>
      <UnderlineTabs tabs={TABS} value={tab} onChange={setTab} />
      {tab === "Overview" && <Overview />}
      {tab === "Domain Skills" && <DomainSkills />}
      {tab === "Career Path" && <CareerTab />}
      {tab === "Assessment History" && <HistoryTab />}
    </div>
  );
}
