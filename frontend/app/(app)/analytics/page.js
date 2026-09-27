"use client";
import { useState, useRef, useEffect } from "react";
import {
  BrainCircuit, Send, Lightbulb, BookOpen, CheckCircle,
  ChevronDown, ChevronRight, Cpu, FileText, MessageSquare,
  RefreshCw, Zap, ListChecks, FlaskConical, Minimize2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AI_TUTOR_HISTORY } from "@/lib/nexus-data";
import { useTitle } from "@/lib/use-title";

// ─── XAI Explainability Panel ─────────────────────────────────────────────────
function XAIPanel({ xai }) {
  const [open, setOpen] = useState(true);
  if (!xai) return null;
  return (
    <motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-3">
      <button onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-xl bg-[#EAF4FF] border border-[#C8DEFF] px-4 py-3 text-left">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-4.5 w-4.5 text-[#1464E8]" />
          <span className="text-[14px] font-bold text-[#0B2A5B]">Why this answer?</span>
        </div>
        {open ? <ChevronDown className="h-4 w-4 text-[#5A6E8C]" /> : <ChevronRight className="h-4 w-4 text-[#5A6E8C]" />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.25 }}
            className="flex flex-col gap-3 overflow-hidden">

            {/* Reason */}
            <div className="xai-card">
              <p className="mb-1 text-[11.5px] font-bold uppercase tracking-widest text-[#1464E8]">Reason</p>
              <p className="text-[13.5px] text-[#0B2A5B] leading-relaxed">{xai.reason}</p>
            </div>

            {/* Evidence */}
            <div className="rounded-xl border border-border bg-surface p-4">
              <p className="mb-2 text-[11.5px] font-bold uppercase tracking-widest text-muted">Evidence Used</p>
              <ul className="flex flex-col gap-2">
                {xai.evidence.map((e, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[#1464E8]" />
                    <span className="text-[13px] text-foreground">{e}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Competency + Confidence */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-border bg-surface p-3">
                <p className="mb-1 text-[11px] font-bold uppercase tracking-widest text-muted">Competency</p>
                <p className="text-[13px] font-semibold text-foreground">{xai.competency}</p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-3">
                <p className="mb-1 text-[11px] font-bold uppercase tracking-widest text-muted">Confidence</p>
                <div className="flex items-center gap-2">
                  <div className="domain-bar flex-1">
                    <div className="domain-bar-fill" style={{ width: `${xai.confidence * 100}%`, background: "#16A36A" }} />
                  </div>
                  <span className="tabular text-[13px] font-bold text-[#16A36A]">{Math.round(xai.confidence * 100)}%</span>
                </div>
              </div>
            </div>

            {/* Sources */}
            <div className="rounded-xl border border-border bg-surface p-4">
              <p className="mb-2 text-[11.5px] font-bold uppercase tracking-widest text-muted">Source Materials</p>
              <div className="flex flex-wrap gap-2">
                {xai.sources.map((s, i) => (
                  <span key={i} className="xai-source text-[12px] font-medium text-foreground">{s}</span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── Markdown-lite renderer ───────────────────────────────────────────────────
function MsgContent({ content }) {
  // Very simple: bold, newlines, headers
  const lines = content.split("\n");
  return (
    <div className="prose-nx">
      {lines.map((line, i) => {
        if (line.startsWith("**") && line.endsWith("**") && line.length > 4)
          return <h4 key={i} className="mt-3 mb-1 text-[14px] font-bold first:mt-0">{line.slice(2, -2)}</h4>;
        if (line.startsWith("- "))
          return <li key={i} className="ml-4 list-disc text-[14px]">{renderInline(line.slice(2))}</li>;
        if (line === "") return <br key={i} />;
        return <p key={i} className="text-[14px]">{renderInline(line)}</p>;
      })}
    </div>
  );
}

function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : p
  );
}

// ─── Message Bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg, onXai }) {
  const isUser = msg.role === "user";
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-xl font-bold text-[12px] text-white
        ${isUser ? "bg-[#0B2A5B]" : "bg-[#1464E8]"}`}>
        {isUser ? "AS" : <BrainCircuit className="h-4.5 w-4.5" />}
      </div>
      {/* Bubble */}
      <div className={`max-w-[82%] flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
        <div className={`rounded-2xl px-4 py-3 text-[14px] leading-relaxed
          ${isUser
            ? "bg-[#0B2A5B] text-white rounded-tr-sm"
            : "bg-surface border border-border text-foreground rounded-tl-sm shadow-card"
          }`}>
          {isUser ? <p>{msg.content}</p> : <MsgContent content={msg.content} />}
        </div>
        {/* XAI trigger */}
        {msg.xai && (
          <button onClick={() => onXai(msg.xai)}
            className="flex items-center gap-1.5 rounded-lg bg-[#EAF4FF] border border-[#C8DEFF] px-2.5 py-1 text-[11.5px] font-semibold text-[#1464E8] hover:bg-[#D3E9FF] transition-colors">
            <Lightbulb className="h-3.5 w-3.5" />Why this answer?
          </button>
        )}
      </div>
    </motion.div>
  );
}

// ─── Quick Actions ────────────────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { icon: RefreshCw,   label: "Explain Again" },
  { icon: ListChecks,  label: "Generate MCQs" },
  { icon: FlaskConical,label: "Give Example" },
  { icon: Zap,         label: "Practice Question" },
  { icon: Minimize2,   label: "Simplify" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function AITutorPage() {
  useTitle("AI Tutor · NEXUS");
  const [messages, setMessages] = useState(AI_TUTOR_HISTORY);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [activeXai, setActiveXai] = useState(AI_TUTOR_HISTORY.find((m) => m.xai)?.xai ?? null);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || sending) return;
    setInput("");
    setSending(true);
    setMessages((m) => [...m, { role: "user", content: q, ts: new Date().toISOString() }]);
    // Simulate AI response
    await new Promise((r) => setTimeout(r, 1200));
    setMessages((m) => [...m, {
      role: "assistant",
      content: `I'll generate a practice question on **Correlation vs Regression**:\n\n**Question**\nA study finds that studying time and exam scores have a correlation coefficient of **r = 0.85**. Which of the following is the most accurate interpretation?\n\n- A) Students who study more *cause* higher scores\n- B) There is a strong positive linear relationship between study time and scores\n- C) Studying time explains 85% of the variance in scores\n- D) Both A and C are correct\n\n**Correct Answer: B**\n\nCorrelation only measures association — it does not imply causation (A is wrong). R² = 0.72, not 0.85 (C is wrong).`,
      ts: new Date().toISOString(),
      xai: {
        reason: "Generated based on your current topic and gap in Statistical Analysis competency.",
        evidence: ["Fundamentals of Official Statistics — Chapter 4", "Your recent quiz (65% accuracy in quantitative stats)"],
        competency: "Statistics & Data Analysis",
        confidence: 0.91,
        sources: ["NSSTA Learning Material", "iGOT Statistics Foundation"],
      },
    }]);
    setSending(false);
  };

  return (
    <div className="flex h-[calc(100vh-80px)] flex-col gap-0 lg:flex-row lg:gap-5 pb-20 lg:pb-0">

      {/* ── LEFT: Chat ── */}
      <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-border bg-surface shadow-card overflow-hidden">

        {/* Header */}
        <div className="flex items-center gap-3 border-b border-border px-5 py-4"
          style={{ background: "linear-gradient(95deg,#0B2A5B,#1464E8)" }}>
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-white/15 backdrop-blur">
            <BrainCircuit className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-[15px] font-bold text-white">NEXUS AI Tutor</p>
            <p className="text-[11.5px] text-white/70">Contextual · Explainable · Evidence-backed</p>
          </div>
          <span className="ml-auto flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-semibold text-white">
            <span className="h-2 w-2 rounded-full bg-[#16A36A] animate-pulse" />Online
          </span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-5 flex flex-col gap-5 nx-scroll-light">
          {messages.map((m, i) => (
            <MessageBubble key={i} msg={m} onXai={(x) => setActiveXai(x)} />
          ))}
          {sending && (
            <div className="flex gap-3">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-[#1464E8] text-white">
                <BrainCircuit className="h-4.5 w-4.5" />
              </div>
              <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3 shadow-card">
                <span className="typing-dots"><i /><i /><i /></span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Quick actions */}
        <div className="overflow-x-auto px-4 py-2 border-t border-border flex gap-2 nx-scroll">
          {QUICK_ACTIONS.map(({ icon: Icon, label }) => (
            <button key={label} onClick={() => setInput(label)}
              className="shrink-0 flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-[12px] font-semibold text-foreground hover:bg-[#EAF4FF] hover:border-[#1464E8] hover:text-[#1464E8] transition-colors whitespace-nowrap">
              <Icon className="h-3.5 w-3.5" />{label}
            </button>
          ))}
        </div>

        {/* Composer */}
        <div className="border-t border-border px-4 py-3">
          <div className="flex items-end gap-2 rounded-xl border border-border bg-surface-2 px-3 py-2 focus-within:border-[#1464E8] focus-within:ring-4 focus-within:ring-[#1464E8]/10 transition-all">
            <textarea
              className="flex-1 resize-none bg-transparent text-[14px] text-foreground placeholder:text-muted/70 outline-none leading-relaxed min-h-[42px] max-h-[120px]"
              placeholder="Ask a question, request examples, or practice a concept…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={1}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            />
            <button
              onClick={send}
              disabled={!input.trim() || sending}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#1464E8] text-white disabled:opacity-40 hover:bg-[#0B2A5B] transition-colors"
              aria-label="Send">
              <Send className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-1.5 text-center text-[11px] text-muted">
            Answers are generated from your enrolled learning materials only · Official use only
          </p>
        </div>
      </div>

      {/* ── RIGHT: XAI Panel (desktop only) ── */}
      <div className="hidden w-[340px] shrink-0 flex-col gap-4 overflow-y-auto lg:flex nx-scroll-light">
        <div className="rounded-2xl border border-border bg-surface p-5 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-[#EAF4FF]">
              <Cpu className="h-4.5 w-4.5 text-[#1464E8]" />
            </span>
            <div>
              <p className="text-[14px] font-bold text-foreground">Explainability</p>
              <p className="text-[11.5px] text-muted">XAI — Why & How</p>
            </div>
          </div>
          {activeXai
            ? <XAIPanel xai={activeXai} />
            : (
              <div className="flex flex-col items-center gap-3 py-8 text-center">
                <div className="grid h-14 w-14 place-items-center rounded-2xl bg-[#EAF4FF]">
                  <Lightbulb className="h-7 w-7 text-[#1464E8]" />
                </div>
                <p className="text-[14px] font-semibold text-foreground">Tap "Why this answer?"</p>
                <p className="text-[12.5px] text-muted leading-relaxed max-w-[220px]">
                  After an AI response, click the blue button to see the evidence, competency affected, and confidence score.
                </p>
              </div>
            )
          }
        </div>

        {/* AI Tutor illustration */}
        <div className="rounded-2xl border border-border bg-surface overflow-hidden shadow-card">
          <div className="px-4 pt-4">
            <p className="text-[13px] font-bold text-foreground">How NEXUS AI Tutor Works</p>
            <p className="mt-1 text-[12px] text-muted leading-relaxed">
              The AI only answers from your enrolled learning materials. Every answer shows the sources it relied on.
            </p>
          </div>
          <img src="/ai-tutor.png" alt="AI Tutor illustration" className="mt-3 w-full object-contain max-h-48" />
        </div>
      </div>
    </div>
  );
}
