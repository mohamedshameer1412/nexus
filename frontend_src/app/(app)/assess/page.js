"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Timer } from "lucide-react";
import { Bar, Panel, Ring } from "@/components/nexus/kit";
import { Button, Label, RadioGroup, RadioGroupItem } from "@/components/ui/primitives";
import { DIAGNOSTIC } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";
import { cn } from "@/lib/utils";

const TOTAL = DIAGNOSTIC.questions.length;
const LETTERS = "ABCD";
const clock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

function Submitted({ answered, onRestart }) {
  return (
    <Panel className="mx-auto max-w-lg text-center">
      <CheckCircle2 className="mx-auto h-14 w-14 text-[#16A36A]" />
      <h1 className="mt-3 text-[22px] font-bold text-[#0B2A5B]">Assessment submitted</h1>
      <p className="mt-2 text-[14.5px] text-[#5A6E8C]">You answered {answered} of {TOTAL} questions on {DIAGNOSTIC.topic}. Your competency profile will update with the result.</p>
      <div className="mt-5 flex justify-center gap-3">
        <Button type="button" variant="secondary" size="lg" className="rounded-xl border-[#D6E4F5] text-[14px]" onClick={onRestart}>Review again</Button>
        <Button asChild size="lg" className="rounded-xl bg-[#0B2A5B] text-[14px] hover:bg-[#123A78]"><Link href="/competency">View competency profile</Link></Button>
      </div>
    </Panel>
  );
}

export default function AssessmentPage() {
  useTitle("Diagnostic Assessment · NEXUS");
  const [current, setCurrent] = useState(DIAGNOSTIC.start);
  const [answers, setAnswers] = useState(DIAGNOSTIC.preAnswered);
  const [seconds, setSeconds] = useState(DIAGNOSTIC.secondsLeft);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (done) return;
    const t = setInterval(() => setSeconds((s) => {
      if (s <= 1) { setDone(true); return 0; }
      return s - 1;
    }), 1000);
    return () => clearInterval(t);
  }, [done]);

  const answered = Object.keys(answers).length;
  const pct = Math.round((answered / TOTAL) * 100);
  const q = DIAGNOSTIC.questions[current];
  const last = current === TOTAL - 1;

  if (done) return <Submitted answered={answered} onRestart={() => { setDone(false); setSeconds(DIAGNOSTIC.secondsLeft); setCurrent(0); }} />;

  return (
    <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
      <Panel className="border-0 bg-transparent p-0 shadow-none lg:border lg:bg-white lg:p-7 lg:shadow-[0_2px_14px_rgb(20_100_232/.06)]">
        <h1 className="hidden text-[20px] font-bold text-[#0B2A5B] lg:block">Diagnostic Assessment</h1>
        <div className="flex items-center justify-between lg:mt-5">
          <p className="text-[14px] text-[#33476A]">Question {current + 1} of {TOTAL}</p>
          <span className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[14px] font-bold tabular-nums", seconds < 60 ? "bg-[#FDECEC] text-[#D64545]" : "bg-[#E3F7EE] text-[#16A36A]")}
            role="timer" aria-label={`Time left ${clock(seconds)}`}>
            <Timer className="h-4 w-4" aria-hidden="true" />{clock(seconds)}
          </span>
        </div>
        <Bar value={((current + 1) / TOTAL) * 100} height={7} className="mt-3" />

        <fieldset className="mt-6">
          <legend className="text-[17px] font-bold leading-snug text-[#0B2A5B] lg:text-[16px]">{q.q}</legend>
          <RadioGroup value={String(answers[current] ?? "")} onValueChange={(v) => setAnswers((a) => ({ ...a, [current]: Number(v) }))} className="mt-5 gap-3">
            {q.options.map((o, i) => {
              const on = answers[current] === i;
              const id = `q${current}-${i}`;
              return (
                <Label key={o} htmlFor={id} className={cn("mb-0 flex cursor-pointer items-center gap-4 rounded-xl border px-4 py-3.5 text-[15px] font-normal transition-colors",
                  on ? "border-[#BFD6FA] bg-[#E6F0FF] text-[#0B2A5B]" : "border-[#E3ECF8] bg-white text-[#33476A] hover:border-[#BFD6FA]")}>
                  <RadioGroupItem id={id} value={String(i)} className="h-6 w-6 shrink-0 border-[#C3D2E6] data-[state=checked]:border-[#1464E8] data-[state=checked]:bg-[#1464E8] data-[state=checked]:text-white" />
                  <span>{LETTERS[i]}. {o}</span>
                </Label>
              );
            })}
          </RadioGroup>
        </fieldset>

        <div className="mt-8 grid grid-cols-2 gap-4">
          <Button type="button" variant="secondary" disabled={current === 0} onClick={() => setCurrent((c) => c - 1)}
            className="h-14 rounded-xl border-[#D6E4F5] text-[16px]">
            <ArrowLeft className="h-5 w-5" />Previous
          </Button>
          <Button type="button" onClick={() => (last ? setDone(true) : setCurrent((c) => c + 1))}
            className="h-14 rounded-xl bg-[#0B2A5B] text-[16px] shadow-[0_6px_18px_rgb(11_42_91/.25)] hover:bg-[#123A78]">
            {last ? "Submit" : "Next"}<ArrowRight className="h-5 w-5" />
          </Button>
        </div>
      </Panel>

      <div className="hidden space-y-5 lg:block">
        <Panel>
          <h2 className="text-[16px] font-bold text-[#0B2A5B]">Assessment Progress</h2>
          <div className="mt-4 flex items-center gap-6">
            <Ring value={pct} size={130} stroke={14} label={false} />
            <div>
              <p className="text-[36px] font-extrabold leading-none text-[#0B2A5B]">{pct}%</p>
              <p className="mt-3 flex items-center gap-2 text-[12.5px] text-[#5A6E8C]"><span className="h-1.5 w-3 rounded-full bg-[#1464E8]" />{answered} Answered</p>
              <p className="mt-1 flex items-center gap-2 text-[12.5px] text-[#5A6E8C]"><span className="h-1.5 w-3 rounded-full bg-[#DCE9FB]" />{TOTAL - answered} Remaining</p>
            </div>
          </div>
        </Panel>
        <Panel>
          <h2 className="text-[16px] font-bold text-[#0B2A5B]">Topic: {DIAGNOSTIC.topic}</h2>
          <div className="mt-4 grid grid-cols-5 gap-3">
            {DIAGNOSTIC.questions.map((_, i) => {
              const state = i === current ? "current" : answers[i] !== undefined ? "answered" : "open";
              return (
                <button key={i} type="button" onClick={() => setCurrent(i)} aria-label={`Question ${i + 1}, ${state === "open" ? "not answered" : state}`} aria-current={i === current ? "step" : undefined}
                  className={cn("grid h-11 w-11 place-items-center rounded-full text-[14px] font-semibold transition-transform hover:scale-105",
                    state === "current" && "bg-[#1464E8] text-white shadow-[0_4px_12px_rgb(20_100_232/.35)]",
                    state === "answered" && "bg-[#E3F7EE] text-[#16A36A]",
                    state === "open" && "bg-[#EEF3FA] text-[#5A6E8C]")}>
                  {i + 1}
                </button>
              );
            })}
          </div>
          <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-[12.5px] text-[#5A6E8C]">
            <span className="flex items-center gap-2"><span className="h-3.5 w-3.5 rounded bg-[#16A36A]" />Answered</span>
            <span className="flex items-center gap-2"><span className="h-3.5 w-3.5 rounded bg-[#1464E8]" />Current</span>
            <span className="flex items-center gap-2"><span className="h-3.5 w-3.5 rounded bg-[#D6E1EF]" />Not Answered</span>
          </div>
        </Panel>
      </div>
    </div>
  );
}
