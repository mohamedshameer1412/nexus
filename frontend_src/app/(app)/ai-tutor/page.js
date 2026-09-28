"use client";
import Link from "next/link";
import { Fragment, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ChartLine, ChevronDown, Paperclip, SendHorizontal } from "lucide-react";
import { Asset, Bar, UnderlineTabs } from "@/components/nexus/kit";
import { AI_TUTOR_HISTORY, COMPETENCY, TUTOR_REPLIES } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";
import { cn } from "@/lib/utils";

const QUICK = ["Explain Again", "Generate MCQs", "Give Example", "Practice Question"];
const HEAD_COLORS = ["text-[#1464E8]", "text-[#16A36A]"];

// **bold** and *italic* inside a line.
function Inline({ text }) {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) =>
    part.startsWith("**") ? <b key={i} className="font-semibold text-[#0B2A5B]">{part.slice(2, -2)}</b>
      : part.startsWith("*") && part.length > 2 ? <em key={i}>{part.slice(1, -1)}</em>
        : <Fragment key={i}>{part}</Fragment>);
}

/** The tutor's small markdown: a line that is only **bold** is a heading, "- " is a bullet. */
function Answer({ text }) {
  let heading = 0;
  const blocks = [];
  let bullets = [];
  const flush = () => { if (bullets.length) blocks.push(<ul key={`u${blocks.length}`} className="ml-5 list-disc space-y-1 marker:text-[#1464E8]">{bullets}</ul>); bullets = []; };
  text.split("\n").forEach((line, i) => {
    const t = line.trim();
    if (!t) return flush();
    if (/^\*\*[^*]+\*\*$/.test(t)) { flush(); blocks.push(<h3 key={i} className={cn("mt-2 text-[16px] font-bold first:mt-0", HEAD_COLORS[heading++ % 2])}>{t.slice(2, -2)}</h3>); return; }
    if (t.startsWith("- ")) { bullets.push(<li key={i}><Inline text={t.slice(2)} /></li>); return; }
    flush();
    blocks.push(<p key={i}><Inline text={t} /></p>);
  });
  flush();
  return <div className="space-y-1.5 text-[14px] leading-relaxed text-[#33476A]">{blocks}</div>;
}

function Explain({ xai }) {
  const [tab, setTab] = useState("Explanation");
  const domain = COMPETENCY.domains.find((d) => d.label === xai.competency);
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-[#E3ECF8] bg-white p-4">
        <UnderlineTabs tabs={["Explanation", "Sources", "Competency"]} value={tab} onChange={setTab} />
        <div className="pt-3 text-[14px] leading-relaxed text-[#5A6E8C]">
          {tab === "Explanation" && <p>{xai.reason}</p>}
          {tab === "Sources" && <ul className="list-disc space-y-1 pl-5">{xai.sources.map((s) => <li key={s}>{s}</li>)}</ul>}
          {tab === "Competency" && domain && (
            <div>
              <p><b className="text-[#0B2A5B]">{domain.label}</b>: {domain.score}% now, target {domain.target}%.</p>
              <Bar value={domain.score} className="mt-2" />
              <Link href="/competency" className="mt-2 inline-block text-[13px] font-semibold text-[#1464E8] no-underline">Open competency profile</Link>
            </div>
          )}
        </div>
      </div>
      <div>
        <h3 className="text-[15px] font-bold text-[#0B2A5B]">Evidence Used</h3>
        <ol className="mt-2 list-decimal space-y-1 rounded-xl border border-[#E3ECF8] bg-white py-3 pl-9 pr-3 text-[13.5px] text-[#33476A]">
          {xai.evidence.map((e) => <li key={e}>{e}</li>)}
        </ol>
      </div>
      <div>
        <h3 className="text-[15px] font-bold text-[#0B2A5B]">Related Competency</h3>
        <p className="mt-2 flex items-center gap-3 text-[14px] text-[#33476A]">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-[#16A36A] text-white"><ChartLine className="h-4 w-4" aria-hidden="true" /></span>{xai.competency}
        </p>
      </div>
      <div>
        <h3 className="text-[15px] font-bold text-[#0B2A5B]">Confidence <span className="font-medium text-[#5A6E8C]">{xai.confidence.toFixed(2)}</span></h3>
        <Bar value={xai.confidence * 100} tone="green" height={10} className="mt-2" />
      </div>
    </div>
  );
}

function Message({ m, active, onPick }) {
  const [open, setOpen] = useState(false);
  if (m.role === "user") {
    return (
      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <p className="max-w-[88%] rounded-2xl bg-[#E3EEFF] px-5 py-3.5 text-[14.5px] font-medium leading-relaxed text-[#1450B8] lg:max-w-[70%]">{m.content}</p>
      </motion.div>
    );
  }
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <Asset name="icon-ai" className="mt-1 hidden h-11 w-11 shrink-0 lg:block" />
      <div className="min-w-0 flex-1 lg:max-w-[85%]">
        <button type="button" onClick={() => onPick(m.xai)}
          className={cn("w-full rounded-2xl border bg-[#F4F8FF] px-5 py-4 text-left transition-colors lg:bg-white", active ? "border-[#9CC0F7] lg:shadow-[0_0_0_3px_rgb(20_100_232/.08)]" : "border-[#E3ECF8] hover:border-[#BFD6FA]")}
          aria-label="Show why this answer">
          <Answer text={m.content} />
        </button>
        {m.xai && (
          <div className="lg:hidden">
            <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="mt-2 flex items-center gap-1 text-[13px] font-semibold text-[#1464E8]">
              Why this answer? <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
            </button>
            {open && <div className="mt-3"><Explain xai={m.xai} /></div>}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default function AITutorPage() {
  useTitle("AI Tutor · NEXUS");
  const [messages, setMessages] = useState(AI_TUTOR_HISTORY.slice(0, 2));
  const [xai, setXai] = useState(AI_TUTOR_HISTORY[1].xai);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const end = useRef(null);
  const first = useRef(true);

  useEffect(() => {
    if (first.current) { first.current = false; return; }
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, thinking]);

  const send = async (text) => {
    const q = text.trim();
    if (!q || thinking) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: q }]);
    setThinking(true);
    await new Promise((r) => setTimeout(r, 900));
    const reply = {
      role: "assistant",
      content: TUTOR_REPLIES[q] ?? `**Noted**\n- I have saved *${q}* for your next study session.\n- Use a quick action below, or ask in a subject's Ask tab for an answer cited from your own material.`,
      xai: { ...AI_TUTOR_HISTORY[1].xai, reason: `Built for your question on correlation and regression, using your Statistics & Data Analysis path and recent assessment results.` },
    };
    setMessages((m) => [...m, reply]);
    setXai(reply.xai);
    setThinking(false);
  };

  return (
    <div className="grid gap-6 lg:h-[calc(100dvh-96px)] lg:grid-cols-[1fr_360px]">
      <section className="flex min-h-0 flex-col">
        <header className="mb-5 hidden lg:block">
          <h1 className="text-[26px] font-bold text-[#0B2A5B]">NEXUS AI Tutor</h1>
          <p className="mt-1 text-[15px] text-[#33476A]">Your personal learning assistant</p>
        </header>
        <div className="nx-scroll-light min-h-0 flex-1 space-y-5 overflow-y-auto pb-4 lg:pr-2" aria-live="polite">
          {messages.map((m, i) => <Message key={i} m={m} active={m.xai === xai} onPick={(x) => x && setXai(x)} />)}
          {thinking && <div className="flex gap-3"><Asset name="icon-ai" className="hidden h-11 w-11 lg:block" /><div className="rounded-2xl border border-[#E3ECF8] bg-white px-5 py-4"><span className="typing-dots"><i /><i /><i /></span></div></div>}
          <div ref={end} />
        </div>
        <div className="sticky bottom-[72px] -mx-4 bg-[#F3F7FD]/95 px-4 pb-2 pt-3 backdrop-blur lg:static lg:mx-0 lg:bg-transparent lg:px-0 lg:pb-0">
          <div className="nx-noscroll flex gap-3 overflow-x-auto pb-3">
            {QUICK.map((a) => (
              <button key={a} type="button" onClick={() => send(a)} disabled={thinking}
                className="shrink-0 rounded-xl border border-[#9CC0F7] bg-white px-4 py-2.5 text-[13.5px] font-semibold text-[#1450B8] transition-colors hover:bg-[#E6F0FF] disabled:opacity-60">{a}</button>
            ))}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex h-14 items-center gap-2 rounded-2xl border border-[#E3ECF8] bg-white pl-5 pr-2 shadow-[0_2px_14px_rgb(20_100_232/.06)]">
            <label htmlFor="tutor-input" className="sr-only">Message the tutor</label>
            <input id="tutor-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your message..." maxLength={500}
              className="h-full min-w-0 flex-1 bg-transparent text-[15px] text-[#0B2A5B] outline-none placeholder:text-[#8193B0]" />
            <Paperclip className="h-5 w-5 text-[#8193B0] lg:hidden" aria-hidden="true" />
            <button type="submit" disabled={!input.trim() || thinking} aria-label="Send"
              className="grid h-10 w-10 place-items-center rounded-full bg-[#1464E8] text-white transition-opacity disabled:opacity-40 lg:bg-transparent lg:text-[#1464E8]">
              <SendHorizontal className="h-5 w-5" />
            </button>
          </form>
        </div>
      </section>

      <aside className="nx-scroll-light hidden overflow-y-auto rounded-2xl border border-[#E3ECF8] bg-[#F8FBFF] p-5 lg:block">
        <h2 className="mb-4 text-[20px] font-bold text-[#0B2A5B]">Why this answer?</h2>
        {xai ? <Explain key={messages.indexOf(messages.find((m) => m.xai === xai))} xai={xai} /> : <p className="text-[14px] text-[#5A6E8C]">Pick an answer to see its evidence.</p>}
      </aside>
    </div>
  );
}
