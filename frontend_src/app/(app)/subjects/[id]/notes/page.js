"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Download, Eye, MessageCircleQuestion, NotebookPen, Pencil, Plus, Printer, Save, Search, Sparkles, Trash2, Wand2 } from "lucide-react";
import { api } from "@/lib/api";
import { getNote, getNotes, getSubject, keys } from "@/lib/queries";
import { cn, friendlyError, plural } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { EmptyState, ErrorState, Markdown } from "@/components/nexus/common";
import { Alert, Badge, Button, Card, ConfirmDialog, Input, Label, Segmented, Skeleton, Textarea } from "@/components/ui/primitives";

const when = (iso) => new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

function Editor({ subjectId, noteId, onSaved, onDeleted, onClose }) {
  const qc = useQueryClient();
  const existing = useQuery({ queryKey: keys.note(subjectId, noteId), queryFn: () => getNote(subjectId, noteId), enabled: noteId !== "new" });
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [preview, setPreview] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [problem, setProblem] = useState("");
  const [del, setDel] = useState(false);
  useEffect(() => { if (existing.data) { setTitle(existing.data.title); setBody(existing.data.body); setDirty(false); setPreview(existing.data.source !== "own"); } }, [existing.data]);
  useEffect(() => { if (noteId === "new") { setTitle(""); setBody(""); setDirty(false); setPreview(false); } }, [noteId]);
  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (e) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const save = useMutation({
    mutationFn: () => (noteId === "new"
      ? api(`/subjects/${subjectId}/notes`, { method: "POST", json: { title, body } })
      : api(`/subjects/${subjectId}/notes/${noteId}`, { method: "PUT", json: { title, body } })),
    onSuccess: (n) => { setDirty(false); setProblem(""); qc.invalidateQueries({ queryKey: keys.notes(subjectId) }); qc.setQueryData(keys.note(subjectId, n.id), n); toast.success("Note saved"); onSaved(n.id); },
    onError: (e) => setProblem(friendlyError(e)),
  });
  const remove = useMutation({
    mutationFn: () => api(`/subjects/${subjectId}/notes/${noteId}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: keys.notes(subjectId) }); toast.success("Note deleted"); setDel(false); onDeleted(); },
    onError: (e) => { toast.error(friendlyError(e)); setDel(false); },
  });
  const download = () => {
    const url = URL.createObjectURL(new Blob([`# ${title}\n\n${body}`], { type: "text/markdown;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(title || "note").replace(/[^\w -]+/g, "").trim().slice(0, 60) || "note"}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (noteId !== "new" && existing.isPending) return <Skeleton className="h-64" />;
  if (existing.error) return <ErrorState error={existing.error} onRetry={existing.refetch} />;
  return (
    <div>
      <button type="button" onClick={onClose} className="mb-2 inline-flex min-h-11 items-center gap-1 text-sm lg:hidden"><ArrowLeft className="h-4 w-4" aria-hidden="true" /> All notes</button>
      <form onSubmit={(e) => { e.preventDefault(); save.mutate(); }} className="space-y-3">
        <div><Label htmlFor="note-title">Title</Label><Input id="note-title" value={title} maxLength={200} onChange={(e) => { setTitle(e.target.value); setDirty(true); }} placeholder="e.g. Stacks and queues" /></div>
        <div className="flex items-center justify-between">
          <Label htmlFor="note-body">Note</Label>
          <Button type="button" variant="ghost" size="sm" onClick={() => setPreview((v) => !v)} aria-pressed={preview}>{preview ? <><Pencil className="h-4 w-4" aria-hidden="true" /> Edit</> : <><Eye className="h-4 w-4" aria-hidden="true" /> Preview</>}</Button>
        </div>
        {preview ? (
          <div className="min-h-64 rounded-xl border border-border bg-surface p-5"><Markdown text={body} />{!body.trim() && <p className="text-sm text-muted">Nothing to preview yet.</p>}</div>
        ) : (
          <Textarea id="note-body" value={body} onChange={(e) => { setBody(e.target.value); setDirty(true); }} maxLength={50000} className="min-h-[24rem] font-mono text-[13.5px] leading-relaxed" placeholder={"Write in plain text. You can use:\n# Heading\n- a list\n**bold**, *italic*, `code`\n> a quote"} />
        )}
        {problem && <Alert tone="danger">{problem}</Alert>}
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" loading={save.isPending} disabled={!dirty && noteId !== "new"}><Save className="h-4 w-4" aria-hidden="true" />Save note</Button>
          {dirty && <span className="text-xs text-muted" role="status">Unsaved changes</span>}
          {noteId !== "new" && (
            <>
              <Button type="button" variant="secondary" size="sm" onClick={download}><Download className="h-4 w-4" aria-hidden="true" /> Download</Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => { setPreview(true); setTimeout(() => window.print(), 100); }}><Printer className="h-4 w-4" aria-hidden="true" /> Print</Button>
              <Button type="button" variant="danger-outline" size="sm" className="ml-auto" onClick={() => setDel(true)}><Trash2 className="h-4 w-4" aria-hidden="true" />Delete</Button>
              <ConfirmDialog open={del} onOpenChange={setDel} title="Delete this note?" description="It is removed for good. Your materials are not touched." confirm="Delete" loading={remove.isPending} onConfirm={() => remove.mutate()} />
            </>
          )}
        </div>
      </form>
    </div>
  );
}

const KINDS = [{ value: "all", label: "All" }, { value: "smart", label: "Smart" }, { value: "own", label: "Mine" }, { value: "chat", label: "Chat" }];
const SOURCE = { smart: ["Smart note", "brand"], chat: ["From chat", "neutral"], own: ["Mine", "outline"] };

export default function NotesPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const { data: subject } = useQuery({ queryKey: keys.subject(id), queryFn: () => getSubject(id) });
  useTitle("Notes", subject?.name);
  const { data, error, isPending, refetch } = useQuery({ queryKey: keys.notes(id), queryFn: () => getNotes(id) });
  const [selected, setSelected] = useState(null); // note id, "new", or null
  const [filter, setFilter] = useState("");
  const [kind, setKind] = useState("all");
  const smart = useMutation({
    mutationFn: () => api(`/subjects/${id}/notes/smart`, { method: "POST", json: {} }),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: keys.notes(id) }); toast.success(`${plural(r.notes.length, "smart note")} ready`, { description: "One per topic, every point copied from your material." }); setKind("smart"); if (r.notes[0]) setSelected(r.notes[0].id); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-64" />;
  const q = filter.trim().toLowerCase();
  const shown = data.notes.filter((n) => (kind === "all" || n.source === kind) && (!q || `${n.title} ${n.snippet}`.toLowerCase().includes(q)));
  const count = (k) => data.notes.filter((n) => k === "all" || n.source === k).length;

  return (
    <div className="space-y-5">
      <Card className="flex flex-wrap items-center gap-4 p-5">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-brand text-white"><Sparkles className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-lg font-semibold">Smart notes from your material</h2>
          <p className="text-sm text-muted">One study sheet per topic: key points, definitions, key terms and a self-check, each point copied word for word with its page.</p>
        </div>
        <Button onClick={() => smart.mutate()} loading={smart.isPending}><Wand2 className="h-4 w-4" />{count("smart") ? "Refresh smart notes" : "Generate smart notes"}</Button>
      </Card>
      <div className="lg:grid lg:grid-cols-[20rem_minmax(0,1fr)] lg:gap-6">
        <section aria-labelledby="notes-h" className={cn(selected !== null && "hidden lg:block")}>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 id="notes-h" className="flex items-center gap-2 font-display text-lg font-semibold"><NotebookPen className="h-5 w-5 text-brand" />Notes <span className="tabular text-sm font-normal text-muted">{data.notes.length}</span></h2>
            <Button size="sm" variant="secondary" onClick={() => setSelected("new")}><Plus className="h-4 w-4" />New</Button>
          </div>
          <Segmented className="mb-3" label="Show" value={kind} onValueChange={setKind} options={KINDS.map((k) => ({ ...k, label: `${k.label} ${count(k.value)}` }))} />
          {data.notes.length > 0 && (
            <div className="relative mb-3">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
              <Input aria-label="Search your notes" placeholder="Search notes" value={filter} onChange={(e) => setFilter(e.target.value)} className="h-9 pl-9 text-sm" />
            </div>
          )}
          {data.notes.length === 0 ? (
            <EmptyState title="No notes yet" action={<Button onClick={() => setSelected("new")}>Write a note</Button>}>Generate smart notes above, write your own, or save answers from the Ask chat.</EmptyState>
          ) : shown.length === 0 ? <p className="text-sm text-muted">No note matches.</p> : (
            <ul className="nx-scroll-light max-h-[70vh] space-y-2 overflow-y-auto pr-1">
              {shown.map((n) => (
                <li key={n.id}>
                  <button type="button" onClick={() => setSelected(n.id)} aria-current={selected === n.id ? "true" : undefined}
                    className={cn("w-full rounded-xl border p-3 text-left transition-colors", selected === n.id ? "border-brand bg-brand-wash shadow-[0_0_0_3px_rgb(1_148_226/.12)]" : "border-border bg-surface hover:bg-brand-wash/60")}>
                    <span className="flex items-start gap-2"><span className="break-anywhere flex-1 font-semibold">{n.title.replace(/^Smart notes: /, "")}</span><Badge tone={SOURCE[n.source]?.[1] ?? "outline"}>{SOURCE[n.source]?.[0] ?? n.source}</Badge></span>
                    <span className="break-anywhere mt-1 line-clamp-2 block text-xs text-muted">{n.snippet.replace(/[#*_>]/g, "") || "Empty note"}</span>
                    <span className="mt-1 block text-[11.5px] text-muted">{when(n.updated_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section aria-label="Note" className={cn(selected === null && "hidden lg:block")}>
          {selected === null ? (
            <Card className="hidden p-8 text-center text-sm text-muted lg:block">
              <NotebookPen className="mx-auto h-8 w-8 text-brand" />
              <p className="mt-3">Pick a note to read or edit it, or start a new one. To turn a chat answer into a note, use the note button under it in <Link href={`/subjects/${id}/ask`}><MessageCircleQuestion className="inline h-4 w-4" /> Ask</Link>.</p>
            </Card>
          ) : (
            <Card className="p-5"><Editor key={String(selected)} subjectId={id} noteId={selected} onSaved={(nid) => setSelected(nid)} onDeleted={() => setSelected(null)} onClose={() => setSelected(null)} /></Card>
          )}
        </section>
      </div>
    </div>
  );
}
