"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Bookmark, BookmarkCheck, CheckCircle2, Download, ExternalLink, FileSearch, NotebookPen, ThumbsDown, ThumbsUp, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { getQuestion, keys } from "@/lib/queries";
import { cn, friendlyError, plural } from "@/lib/utils";
import { StatusBadge, Where, numberCitations } from "@/components/nexus/answer";
import { Markdown } from "@/components/nexus/common";

export function UserBubble({ children }) {
  return (
    <div className="flex justify-end">
      <p className="break-anywhere max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand-deep px-4 py-2.5 text-[15px] text-white shadow-[0_6px_16px_-8px_rgb(3_105_168/.7)] sm:max-w-[70%]">{children}</p>
    </div>
  );
}

function Avatar() {
  return (
    <span aria-hidden="true" className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white shadow-card ring-1 ring-border">
      <img src="/logo-128.png" alt="" className="h-5 w-5" />
    </span>
  );
}

export function Bubble({ children, label }) {
  return (
    <div className="flex items-start gap-2">
      <Avatar />
      <div className="min-w-0 max-w-[94%] rounded-2xl rounded-tl-md border border-border/80 bg-surface px-4 py-3 text-[15px] leading-relaxed shadow-card sm:max-w-[82%]">
        <span className="sr-only">{label ?? "Nexus said:"}</span>
        {children}
      </div>
    </div>
  );
}

export function Typing({ what = "Reading your materials", createdAt }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const secs = createdAt ? Math.max(0, Math.round((now - new Date(createdAt).getTime()) / 1000)) : null;
  return (
    <Bubble>
      <p role="status" className="flex items-center gap-2 text-sm text-muted">
        <span className="typing-dots" aria-hidden="true"><i /><i /><i /></span>
        {what}…{secs !== null && ` ${secs} s`}
      </p>
    </Bubble>
  );
}

function ViewButton({ onView, x, label = "View in the document" }) {
  if (!onView || !x.document_id) return null;
  return (
    <button type="button" onClick={() => onView({ docId: x.document_id, page: x.page_start, quote: x.quote, passageId: x.passage_id })} className="mt-1 inline-flex h-8 items-center gap-1 text-xs font-semibold text-link hover:underline">
      <FileSearch className="h-4 w-4" aria-hidden="true" /> {label}
    </button>
  );
}

function Evidence({ qid, list, open, setOpen, onView }) {
  return (
    <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)} className="mt-3 rounded-lg border border-border bg-surface-2">
      <summary className="flex h-10 cursor-pointer items-center px-3 text-sm font-semibold text-brand-deep">Evidence · {plural(list.length, "source")}</summary>
      <ul className="space-y-2 px-3 pb-3">
        {list.map((x, i) => (
          <li key={i}>
            <div id={`src-${qid}-${i + 1}`} tabIndex={-1} className="scroll-mt-24 rounded-md border border-border bg-surface p-3 focus:outline-none focus:ring-4 focus:ring-brand/20">
              <p className="break-anywhere text-xs text-muted"><b>[{i + 1}]</b> <Where x={x} /></p>
              <blockquote className="break-anywhere evidence my-2 rounded-r-md px-3 py-2 text-sm">{x.quote}</blockquote>
              <p className="flex items-center gap-1 text-xs font-semibold text-strong"><CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" /> These exact words were found in your material.</p>
              <ViewButton onView={onView} x={x} />
            </div>
          </li>
        ))}
      </ul>
    </details>
  );
}

function AnswerBody({ q, onView }) {
  const claims = q.claims ?? [];
  const { list, numberOf } = numberCitations(claims);
  const [open, setOpen] = useState(false);
  const show = (n) => {
    setOpen(true);
    setTimeout(() => {
      const el = document.getElementById(`src-${q.id}-${n}`);
      if (!el) return;
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
      el.focus({ preventScroll: true });
    }, 30);
  };
  return (
    <div>
      {q.kind === "conflict" && <p className="mb-2 text-sm text-muted">Your materials disagree. Each side shows its own quote; Nexus does not pick a winner.</p>}
      <div className="space-y-2">
        {claims.map((c, i) => (
          <p key={i} className="break-anywhere">
            {c.text}
            {c.citations.map((x) => {
              const n = numberOf(x);
              return (
                <button key={n} type="button" onClick={() => show(n)} aria-label={`Show source ${n}`} className="ml-1 inline-flex h-5 min-w-5 items-center justify-center rounded bg-brand/10 px-1 align-super text-[11px] font-bold text-brand-deep hover:bg-brand hover:text-white">
                  {n}
                </button>
              );
            })}
          </p>
        ))}
      </div>
      {q.dropped > 0 && <p className="mt-2 text-xs text-muted">{plural(q.dropped, "other statement")} could not be verified against your materials and {q.dropped === 1 ? "was" : "were"} left out.</p>}
      {list.length > 0 && <Evidence qid={q.id} list={list} open={open} setOpen={setOpen} onView={onView} />}
      {q.explanation && (
        <details className="mt-2 rounded-lg border border-border bg-surface-2">
          <summary className="flex h-10 cursor-pointer items-center px-3 text-sm font-semibold text-brand-deep">Explanation, step by step</summary>
          <div className="px-3 pb-3">
            <Markdown text={q.explanation} className="text-sm" />
            <p className="mt-2 text-xs text-muted">The model&apos;s own reasoning. It passed simple checks but is not verified word for word.</p>
          </div>
        </details>
      )}
    </div>
  );
}

function PassagesBody({ q, onView }) {
  const sources = q.sources ?? [];
  return (
    <div>
      {q.reason && <p className="break-anywhere text-sm">{q.reason}</p>}
      {sources.length > 0 && (
        <details className="mt-3 rounded-lg border border-border bg-surface-2" open={q.status === "extractive"}>
          <summary className="flex h-10 cursor-pointer items-center px-3 text-sm font-semibold text-brand-deep">{q.status === "extractive" ? "Passages that match" : "Closest passages"} · {sources.length}</summary>
          <ul className="space-y-2 px-3 pb-3">
            {sources.map((s, i) => (
              <li key={i} className="rounded-md border border-border bg-surface p-3">
                <p className="break-anywhere text-xs text-muted"><Where x={s} />{s.matched.length > 0 && <> · matched: {s.matched.join(", ")}</>}</p>
                <p className="break-anywhere mt-1 whitespace-pre-wrap text-sm">{s.text}</p>
                <ViewButton onView={onView} x={{ ...s, quote: s.text.slice(0, 80) }} />
              </li>
            ))}
          </ul>
        </details>
      )}
      {q.status === "abstained" && <p className="mt-2 text-xs text-muted">Try different words, or upload material that covers this.</p>}
    </div>
  );
}

/** The answer as a Markdown file: the question, each statement with its [n] markers, and the exact quotes with where they are from. */
function answerMarkdown(q) {
  const { list, numberOf } = numberCitations(q.claims ?? []);
  const lines = [`# ${q.question}`, ""];
  if (q.status === "answered") {
    for (const c of q.claims) lines.push(`${c.text} ${c.citations.map((x) => `[${numberOf(x)}]`).join("")}`.trim(), "");
    lines.push("## Sources", "");
    list.forEach((x, i) => lines.push(`[${i + 1}] > ${x.quote}`, `    ${x.document}${x.heading_path ? ` · section: ${x.heading_path}` : ""}${x.page_start != null ? ` · page ${x.page_start}` : ""}`, ""));
  } else {
    lines.push(q.reason || "Not answered from your materials.", "");
    (q.sources ?? []).forEach((s) => lines.push(`> ${s.text}`, `    ${s.document}${s.heading_path ? ` · section: ${s.heading_path}` : ""}`, ""));
  }
  lines.push("_Exported from Nexus. The quotes were checked against the uploaded material._");
  return lines.join("\n");
}

function downloadText(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** One exchange: the student's question, then Nexus's reply (typing, answer with evidence, or an honest "not answered"). */
export function ChatTurn({ subjectId, item, onDelete, onView }) {
  const qc = useQueryClient();
  const { data: q, error } = useQuery({
    queryKey: keys.question(subjectId, item.id),
    queryFn: () => getQuestion(subjectId, item.id),
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 2500 : false),
  });
  const feedback = useMutation({
    mutationFn: (value) => api(`/subjects/${subjectId}/questions/${item.id}/feedback`, { method: "POST", json: { value } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.question(subjectId, item.id) }); toast.success("Thanks, noted"); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const toNote = useMutation({
    mutationFn: () => api(`/subjects/${subjectId}/notes/from-answers`, { method: "POST", json: { doubt_ids: [item.id] } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.notes(subjectId) }); toast.success("Saved to your notes, with its sources"); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const bookmark = useMutation({
    mutationFn: (saved) => api(`/subjects/${subjectId}/questions/${item.id}/saved`, { method: "PUT", json: { saved } }),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: keys.question(subjectId, item.id) }); qc.invalidateQueries({ queryKey: keys.saved }); toast.success(r.saved ? "Saved" : "Removed from saved"); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  return (
    <li className="space-y-3">
      <UserBubble>{item.question}</UserBubble>
      {error ? (
        <Bubble><p className="text-sm text-weak">{friendlyError(error)}</p></Bubble>
      ) : !q || q.status === "pending" ? (
        <Typing createdAt={item.created_at} />
      ) : (
        <Bubble>
          {q.status === "answered" ? <AnswerBody q={q} onView={onView} /> : <PassagesBody q={q} onView={onView} />}
          <div className="mt-3 flex flex-wrap items-center gap-0.5 border-t border-border pt-2">
            <StatusBadge status={q.status} kind={q.kind} />
            {q.status === "answered" && (
              <>
                <button type="button" onClick={() => feedback.mutate("helpful")} aria-pressed={q.feedback === "helpful"} aria-label="This helped" className={cn("inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-brand-wash hover:text-brand-deep", q.feedback === "helpful" && "bg-brand-soft text-brand-deep")}><ThumbsUp className="h-4 w-4" aria-hidden="true" /></button>
                <button type="button" onClick={() => feedback.mutate("wrong")} aria-pressed={q.feedback === "wrong"} aria-label="This looks wrong" className={cn("inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-brand-wash hover:text-brand-deep", q.feedback === "wrong" && "bg-brand-soft text-brand-deep")}><ThumbsDown className="h-4 w-4" aria-hidden="true" /></button>
              </>
            )}
            <span className="ml-auto flex items-center">
              <button type="button" onClick={() => bookmark.mutate(!q.saved)} aria-pressed={!!q.saved} aria-label={q.saved ? "Remove from saved answers" : "Save this answer"} className={cn("inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-brand-wash hover:text-brand-deep", q.saved && "bg-brand-soft text-brand-deep")}>{q.saved ? <BookmarkCheck className="h-4 w-4" aria-hidden="true" /> : <Bookmark className="h-4 w-4" aria-hidden="true" />}</button>
              {(q.status === "answered" || q.status === "extractive") && (
                <button type="button" onClick={() => toNote.mutate()} disabled={toNote.isPending} aria-label="Save this answer to my notes" className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-brand-wash hover:text-brand-deep disabled:opacity-60"><NotebookPen className="h-4 w-4" aria-hidden="true" /></button>
              )}
              <button type="button" onClick={() => downloadText(`nexus-answer-${item.id}.md`, answerMarkdown(q))} aria-label="Download this answer with its sources" className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-brand-wash hover:text-brand-deep"><Download className="h-4 w-4" aria-hidden="true" /></button>
              <Link href={`/subjects/${subjectId}/ask/${item.id}`} aria-label="Open full view" className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-brand-wash hover:text-brand-deep"><ExternalLink className="h-4 w-4" aria-hidden="true" /></Link>
              <button type="button" onClick={() => onDelete(item)} aria-label="Delete this question" className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-brand-wash hover:text-brand-deep"><Trash2 className="h-4 w-4" aria-hidden="true" /></button>
            </span>
          </div>
        </Bubble>
      )}
    </li>
  );
}
