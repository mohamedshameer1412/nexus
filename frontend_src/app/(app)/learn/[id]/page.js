"use client";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Award, BarChart3, CalendarDays, CheckCircle2, ChevronLeft, Clock3, MonitorPlay, PlayCircle, Star } from "lucide-react";
import { Asset, Panel, SourceBadge, StatusPill, UnderlineTabs } from "@/components/nexus/kit";
import { Button } from "@/components/ui/primitives";
import { COURSE_DETAILS, LEARNING_PATH } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";

const TABS = ["About", "Modules", "Reviews", "Certificates"];

function Chip({ Icon, children }) {
  return <span className="inline-flex h-7 items-center gap-1.5 rounded-lg border border-[#E3ECF8] bg-white px-2.5 text-[12.5px] font-medium text-[#33476A]"><Icon className="h-3.5 w-3.5 text-[#1464E8]" aria-hidden="true" />{children}</span>;
}

export default function CourseDetailsPage() {
  const { id } = useParams();
  const course = COURSE_DETAILS[id];
  const status = LEARNING_PATH.find((s) => s.id === id)?.status ?? "not-started";
  const [enrolled, setEnrolled] = useState(status !== "not-started");
  const [tab, setTab] = useState("About");
  useTitle(`${course?.title ?? "Course"} · NEXUS`);
  if (!course) notFound();

  const enroll = () => {
    if (enrolled) return toast.info("Opening your next module", { description: course.modules.find((m) => m.status !== "completed")?.title ?? "All modules are complete." });
    setEnrolled(true);
    toast.success(`Enrolled in ${course.title}`, { description: "It has been added to your learning path." });
  };

  return (
    <div className="space-y-5">
      <Button asChild variant="secondary" size="sm" className="hidden rounded-full text-[13.5px] text-[#1464E8] shadow-[0_2px_10px_rgb(20_100_232/.08)] lg:inline-flex">
        <Link href="/learn"><ChevronLeft className="h-4 w-4" />Back to Courses</Link>
      </Button>

      <div className="grid items-center gap-5 lg:grid-cols-[230px_1fr_200px]">
        <div className="relative hidden h-[150px] overflow-hidden rounded-2xl bg-gradient-to-br from-[#2F6FE0] via-[#3E86F5] to-[#8CC0FF] lg:block">
          <Asset name="officers-group" className="absolute bottom-0 left-1/2 h-[120px] w-auto -translate-x-1/2" />
        </div>
        <div>
          <h1 className="text-[26px] font-bold leading-tight text-[#0B2A5B] lg:text-[24px]">{course.title}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <SourceBadge source={course.badge} />
            <span className="hidden lg:contents"><Chip Icon={BarChart3}>{course.level}</Chip></span>
            <Chip Icon={CalendarDays}>{course.weeks} weeks</Chip>
            <span className="hidden lg:contents"><Chip Icon={MonitorPlay}>{course.pace}</Chip></span>
          </div>
          <Button type="button" size="lg" onClick={enroll}
            className="mt-4 w-full rounded-xl bg-[#0B2A5B] text-[15px] shadow-[0_6px_18px_rgb(11_42_91/.25)] hover:bg-[#123A78] lg:max-w-[420px]">
            {enrolled ? <><PlayCircle className="h-4 w-4" />Continue Learning</> : "Enroll Now"}
          </Button>
        </div>
        <div className="hidden h-[150px] place-items-center rounded-2xl bg-gradient-to-b from-[#EEF5FF] to-[#DCEAFE] lg:grid">
          <Asset name="competency-growth" className="h-[120px] w-auto" />
        </div>
      </div>

      <UnderlineTabs tabs={TABS} value={tab} onChange={setTab} />

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <div>
          {tab === "About" && (
            <>
              <h2 className="text-[17px] font-bold text-[#0B2A5B]">About this course</h2>
              <p className="mt-2 text-[14.5px] text-[#5A6E8C]">{course.about}</p>
              <h2 className="mt-6 text-[17px] font-bold text-[#0B2A5B]">Key Learnings</h2>
              <ul className="mt-3 space-y-3">
                {course.learnings.map((l) => <li key={l} className="flex items-center gap-3 text-[15px] text-[#33476A]"><CheckCircle2 className="h-5 w-5 shrink-0 fill-[#16A36A] text-white" aria-hidden="true" />{l}</li>)}
              </ul>
            </>
          )}
          {tab === "Modules" && (
            <ul className="space-y-3">
              {course.modules.map((m) => (
                <li key={m.title} className="flex items-center gap-4 rounded-xl border border-[#E3ECF8] bg-white p-4">
                  <div className="min-w-0 flex-1"><p className="text-[14.5px] font-semibold text-[#0B2A5B]">{m.title}</p><p className="text-[13px] text-[#5A6E8C]">{m.hours} hours</p></div>
                  <StatusPill status={m.status} icon />
                </li>
              ))}
            </ul>
          )}
          {tab === "Reviews" && (course.reviews.length ? (
            <ul className="space-y-3">
              {course.reviews.map((r) => (
                <li key={r.name} className="rounded-xl border border-[#E3ECF8] bg-white p-4">
                  <div className="flex items-center justify-between"><p className="text-[14px] font-semibold text-[#0B2A5B]">{r.name} <span className="font-normal text-[#5A6E8C]">· {r.role}</span></p>
                    <span className="flex" aria-label={`${r.rating} of 5`}>{[1, 2, 3, 4, 5].map((i) => <Star key={i} className={`h-4 w-4 ${i <= r.rating ? "fill-[#F2A900] text-[#F2A900]" : "text-[#D6E1EF]"}`} />)}</span></div>
                  <p className="mt-2 text-[14px] text-[#33476A]">{r.text}</p>
                </li>
              ))}
            </ul>
          ) : <p className="text-[14px] text-[#5A6E8C]">No reviews yet.</p>)}
          {tab === "Certificates" && (
            <div className="flex items-start gap-3 rounded-xl border border-[#E3ECF8] bg-white p-4">
              <Award className="h-6 w-6 shrink-0 text-[#F2A900]" /><p className="text-[14px] text-[#33476A]">{course.certificate}</p>
            </div>
          )}
        </div>

        <Panel className="hidden lg:block">
          <h2 className="mb-3 text-[16px] font-bold text-[#0B2A5B]">Course Preview</h2>
          <ul className="space-y-2.5">
            {course.modules.map((m, i) => (
              <li key={m.title} className="flex items-center gap-3 rounded-xl bg-[#F3F7FD] px-3 py-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white text-[#1464E8] shadow-sm"><PlayCircle className="h-4 w-4" /></span>
                <span className="text-[12px] font-semibold text-[#8193B0]">{i + 1}</span>
                <span className="min-w-0"><span className="block text-[13.5px] font-semibold text-[#0B2A5B]">{m.title}</span><span className="flex items-center gap-1 text-[12px] text-[#5A6E8C]"><Clock3 className="h-3 w-3" />{m.hours} hours</span></span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
