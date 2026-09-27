"use client";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileText, History, NotebookPen, Search, Send } from "lucide-react";
import { api } from "@/lib/api";
import { getDocs, getQuestions, getSubject, getTopics, keys } from "@/lib/queries";
import { friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { Bubble, ChatTurn } from "@/components/nexus/chat";
import { DocPane, DocSheet, useIsDesktop } from "@/components/nexus/doc-viewer";
import { EmptyState, ErrorState } from "@/components/nexus/common";
import { StatusBadge } from "@/components/nexus/answer";
import { relTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Alert, Button, ConfirmDialog, Input, Skeleton } from "@/components/ui/primitives";

const MAX = 500;
const SHOWN = 20;

function Composer({ id, text, setText, onSent }) {
  const qc = useQueryClient();
  const ref = useRef(null);
  const [error, setError] = useState("");
  const ask = useMutation({
    mutationFn: (question) => api(`/subjects/${id}/questions`, { method: "POST", json: { question } }),
    onSuccess: async () => {
      setText("");
      await Promise.all([qc.invalidateQueries({ queryKey: keys.questions(id) }), qc.invalidateQueries({ queryKey: keys.subjects })]);
      onSent();
    },
    onError: (e) => setError(friendlyError(e)),
  });
  useEffect(() => {
    const el = ref.current;
    if (el) { el.style.height = "auto"; el.style.height = `${Math.min(el.scrollHeight, 160)}px`; } // grows with the text, like a chat box
  }, [text]);
  const send = () => {
    const t = text.trim();
    setError("");
    if (t.length < 3) return setError("Type your question first.");
    ask.mutate(t);
  };
  return (
    <form onSubmit={(e) => { e.preventDefault(); send(); }} className="space-y-1">
      {error && <Alert tone="danger">{error}</Alert>}
      <div className="flex items-end gap-2">
        <label htmlFor="question" className="sr-only">Your question</label>
        <textarea
          id="question" ref={ref} rows={1} value={text} maxLength={MAX} disabled={ask.isPending}
          placeholder="Ask about your materials…" aria-describedby="q-help"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }}
          className="min-h-[48px] flex-1 resize-none overflow-hidden rounded-2xl border border-border bg-surface px-4 py-3 text-[15px] shadow-card focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15"
        />
        <Button type="submit" size="icon" aria-label="Ask" loading={ask.isPending} className="h-12 w-12 rounded-full">{!ask.isPending && <Send className="h-4 w-4" aria-hidden="true" />}</Button>
      </div>
      <p id="q-help" className="px-1 text-xs text-muted">Enter to send, Shift+Enter for a new line. <span className="tabular">{text.length}/{MAX}</span>. Answers use only this subject&apos;s materials, with the exact words they rest on.</p>
    </form>
  );
}

export default function AskPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const { data: subject } = useQuery({ queryKey: keys.subject(id), queryFn: () => getSubject(id) });
  useTitle("Ask", subject?.name);
  const docs = useQuery({ queryKey: keys.docs(id), queryFn: () => getDocs(id) });
  const topics = useQuery({ queryKey: keys.topics(id), queryFn: () => getTopics(id) });
  const history = useQuery({ queryKey: keys.questions(id), queryFn: () => getQuestions(id) });
  const [all, setAll] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [draft, setDraft] = useState("");
  const [viewer, setViewer] = useState(null);
  const [find, setFind] = useState(""); // { docId, page, quote, passageId } | { docId: null } when opened from the toolbar
  const desktop = useIsDesktop();
  const prefill = useSearchParams().get("q");
  useEffect(() => { if (prefill) setDraft(prefill.slice(0, MAX)); }, [prefill]);
  const endRef = useRef(null);
  const hasMaterial = docs.data?.some((d) => d.chunks > 0);

  const items = history.data ? [...history.data].sort((a, b) => a.id - b.id) : [];
  const visible = all ? items : items.slice(-SHOWN);
  const lastId = items.at(-1)?.id;
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    endRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "end" });
  }, [lastId]);

  const remove = useMutation({
    mutationFn: (item) => api(`/subjects/${id}/questions/${item.id}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.questions(id) }); qc.invalidateQueries({ queryKey: keys.subjects }); toast.success("Question deleted"); setToDelete(null); },
    onError: (e) => { toast.error(friendlyError(e)); setToDelete(null); },
  });

  const notes = useMutation({
    mutationFn: () => api(`/subjects/${id}/notes/from-answers`, { method: "POST", json: { doubt_ids: visible.filter((x) => x.status === "answered" || x.status === "extractive").map((x) => x.id) } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.notes(id) }); toast.success("Saved as a note from this chat"); },
    onError: (e) => toast.error(friendlyError(e)),
  });

  if (docs.isPending || history.isPending) return <Skeleton className="h-64" />;
  if (history.error) return <ErrorState error={history.error} onRetry={history.refetch} />;
  if (!hasMaterial) {
    return (
      <EmptyState title="Upload some material first" action={<Button asChild><Link href={`/subjects/${id}/materials`}>Go to Materials</Link></Button>}>
        Answers are written only from what you upload to this subject.
      </EmptyState>
    );
  }

  const split = !!viewer && desktop;
  const hist = [...items].reverse().filter((x) => x.question.toLowerCase().includes(find.trim().toLowerCase()));
  const pane = <DocPane subjectId={id} target={viewer} onClose={() => setViewer(null)} />;
  return (
    <div className={cn("lg:grid lg:gap-6", split ? "lg:grid-cols-[minmax(0,1fr)_30rem]" : "xl:grid-cols-[16rem_minmax(0,1fr)]")}>
    {!split && (
      <aside aria-label="Question history" className="hidden xl:block">
        <div className="sticky top-32 rounded-xl border border-border/80 bg-surface p-3 shadow-card">
          <p className="mb-2 flex items-center gap-1.5 px-1 text-[13px] font-semibold"><History className="h-4 w-4 text-brand" />History <span className="tabular ml-auto font-normal text-muted">{items.length}</span></p>
          <div className="relative mb-2"><Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" /><Input value={find} onChange={(e) => setFind(e.target.value)} placeholder="Find a question" aria-label="Find a question" className="h-8 pl-8 text-[13px]" /></div>
          <ul className="nx-scroll-light max-h-[60vh] space-y-0.5 overflow-y-auto">
            {hist.length === 0 && <li className="px-2 py-3 text-[13px] text-muted">No questions yet.</li>}
            {hist.map((x) => (
              <li key={x.id}>
                <Link href={`/subjects/${id}/ask/${x.id}`} className="block rounded-md px-2 py-1.5 text-foreground no-underline hover:bg-brand-wash">
                  <span className="line-clamp-2 text-[13px] leading-snug">{x.question}</span>
                  <span className="mt-0.5 flex items-center gap-1.5 text-[11.5px] text-muted"><span className={cn("h-1.5 w-1.5 rounded-full", x.status === "answered" ? "bg-strong" : x.status === "pending" ? "bg-brand" : x.status === "failed" ? "bg-weak" : "bg-mid")} />{relTime(x.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    )}
    <div className="flex min-h-[calc(100dvh-16rem)] min-w-0 flex-col">
      <h2 className="sr-only">Chat with your materials</h2>
      <div className="mb-3 flex flex-wrap justify-end gap-2">
        <Button variant="secondary" size="sm" onClick={() => setViewer((v) => (v ? null : { docId: null }))} aria-pressed={!!viewer}><FileText className="h-4 w-4" aria-hidden="true" /> {viewer ? "Hide my documents" : "Show my documents"}</Button>
        <Button variant="secondary" size="sm" onClick={() => notes.mutate()} loading={notes.isPending} disabled={!visible.some((x) => x.status === "answered" || x.status === "extractive")}><NotebookPen className="h-4 w-4" aria-hidden="true" /> Notes from this chat</Button>
      </div>
      <div role="log" aria-label="Conversation" aria-live="polite" className="flex-1 pb-4">
        {items.length > visible.length && (
          <div className="mb-4 text-center"><Button variant="secondary" size="sm" onClick={() => setAll(true)}>Show {items.length - visible.length} earlier</Button></div>
        )}
        <ul className="space-y-6">
          <li>
            <Bubble label="Nexus said:">
              <p>Ask me anything about <b className="break-anywhere">{subject?.name ?? "this subject"}</b>. I answer only from your uploaded materials, show the exact words I used, and say so when they do not cover your question.</p>
              {items.length === 0 && (topics.data?.length ?? 0) > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {topics.data.slice(0, 2).map((t) => (
                    <button key={`sum-${t.id}`} type="button" className="h-9 rounded-full border border-brand/25 bg-brand-wash px-3 text-[13px] font-semibold text-brand-deep hover:border-brand hover:bg-brand-soft"
                      onClick={() => { setDraft(`Summarise the main points of "${t.name}" using only my materials.`); document.getElementById("question")?.focus(); }}>
                      Summarise {t.name}
                    </button>
                  ))}
                  {topics.data.slice(0, 3).map((t) => (
                    <button key={t.id} type="button" className="h-9 rounded-full border border-brand/25 bg-brand-wash px-3 text-[13px] font-semibold text-brand-deep hover:border-brand hover:bg-brand-soft"
                      onClick={() => { setDraft(`What is ${t.name}?`); document.getElementById("question")?.focus(); }}>
                      What is {t.name}?
                    </button>
                  ))}
                </div>
              )}
            </Bubble>
          </li>
          {visible.map((item) => <ChatTurn key={item.id} subjectId={id} item={item} onDelete={setToDelete} onView={setViewer} />)}
        </ul>
        <div ref={endRef} />
      </div>

      <div className="sticky bottom-[4.25rem] z-20 -mx-1 bg-gradient-to-t from-background via-background to-background/0 px-1 pb-3 pt-6 sm:bottom-0">
        <Composer id={id} text={draft} setText={setDraft} onSent={() => endRef.current?.scrollIntoView({ block: "end" })} />
      </div>

      <ConfirmDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)} title="Delete this question?" description="The question and its answer are removed. Your materials are not touched."
        confirm="Delete" loading={remove.isPending} onConfirm={() => remove.mutate(toDelete)} />
    </div>
    {split && <aside aria-label="Your document" className="sticky top-32 h-[calc(100dvh-10rem)] overflow-hidden rounded-xl border border-border bg-surface shadow-card">{pane}</aside>}
    {viewer && !desktop && <DocSheet open onOpenChange={(o) => !o && setViewer(null)}>{pane}</DocSheet>}
    </div>
  );
}
