"use client";
import Link from "next/link";
import { Award, ChevronRight, CircleHelp, History, LogOut, Settings, Target, UserRound } from "lucide-react";
import { useLogout } from "@/components/nexus/shell";
import { Bar, Initials, Panel, PanelTitle } from "@/components/nexus/kit";
import { Button } from "@/components/ui/primitives";
import { COMPETENCY, OFFICER, PROFILE } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";
import { cn } from "@/lib/utils";

const ICONS = { profile: UserRound, certificates: Award, history: History, career: Target, settings: Settings, help: CircleHelp, logout: LogOut };
const TONES = { blue: "bg-[#1464E8] text-white", red: "bg-[#E5484D] text-white" };

function MenuRow({ item, onLogout }) {
  const Icon = ICONS[item.key];
  const body = (
    <>
      <span className={cn("grid h-9 w-9 shrink-0 place-items-center rounded-lg", TONES[item.tone] ?? "bg-[#5E7392] text-white")}><Icon className="h-[18px] w-[18px]" aria-hidden="true" /></span>
      <span className="flex-1 text-[15px] font-medium text-[#33476A]">{item.label}</span>
      <ChevronRight className="h-4 w-4 text-[#8193B0]" aria-hidden="true" />
    </>
  );
  const cls = "flex w-full items-center gap-4 border-b border-[#EEF3FA] px-1 py-3.5 text-left no-underline last:border-0 hover:bg-[#F7FAFE]";
  return (
    <li className={cn(item.mobileOnly && "lg:hidden")}>
      {item.key === "logout" ? <button type="button" onClick={onLogout} className={cls}>{body}</button> : <Link href={item.href} className={cls}>{body}</Link>}
    </li>
  );
}

export default function ProfilePage() {
  useTitle("Profile · NEXUS");
  const logout = useLogout();
  return (
    <div className="space-y-5">
      <div className="hidden items-center justify-between lg:flex">
        <h1 className="text-[26px] font-bold text-[#0B2A5B]">Profile</h1>
        <Button asChild variant="secondary" className="rounded-xl border-[#9CC0F7] text-[14px] text-[#1464E8] hover:bg-[#E6F0FF]"><Link href="/account">Edit Profile</Link></Button>
      </div>
      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <section>
          <div className="flex flex-col items-center text-center">
            <Initials name={OFFICER.name} className="h-24 w-24 text-[30px]" />
            <h2 className="mt-3 text-[20px] font-bold text-[#0B2A5B]">{OFFICER.name}</h2>
            <p className="mt-1 text-[14px] text-[#5A6E8C]">{OFFICER.designation}</p>
            <p className="max-w-[260px] text-[14px] text-[#5A6E8C]">{OFFICER.department}</p>
          </div>
          <ul className="mt-6 rounded-2xl bg-white px-3 shadow-[0_2px_14px_rgb(20_100_232/.06)] lg:bg-transparent lg:px-0 lg:shadow-none">
            {PROFILE.menu.map((m) => <MenuRow key={m.key} item={m} onLogout={logout} />)}
          </ul>
        </section>
        <div className="space-y-5">
          <Panel>
            <PanelTitle>My Competency Summary</PanelTitle>
            <ul className="space-y-4">
              {COMPETENCY.domains.map((d) => (
                <li key={d.id}>
                  <div className="mb-1.5 flex justify-between text-[14px] text-[#33476A]"><span>{d.label}</span><b className="text-[#0B2A5B]">{d.score}%</b></div>
                  <Bar value={d.score} />
                </li>
              ))}
            </ul>
          </Panel>
          <Panel>
            <PanelTitle>Career Aspirations</PanelTitle>
            <p className="text-[14.5px] text-[#5A6E8C]">{PROFILE.aspiration}</p>
          </Panel>
        </div>
      </div>
    </div>
  );
}
