"use client";
import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, FileImage, FileText, Globe, Loader2, ScanText, Sparkles, UploadCloud, XCircle } from "lucide-react";
import { api, uploadFile } from "@/lib/api";
import { check, Upload } from "@/lib/schemas";
import { getSystem, keys } from "@/lib/queries";
import { cn, friendlyError, plural } from "@/lib/utils";
import { Alert, Badge, Button, Field, Input, Progress, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/primitives";

const MAX_MB = 50;
const IMAGE = /\.(png|jpe?g|webp|gif|bmp|tiff?)$/i;

function refresh(qc, id) {
  return Promise.all([keys.docs(id), keys.topics(id), keys.subject(id), keys.subjects, keys.dashboard].map((k) => qc.invalidateQueries({ queryKey: k })));
}

/** What this server can read right now (OCR engine, semantic search), so the student knows before uploading a scan. */
export function Capabilities() {
  const { data } = useQuery({ queryKey: keys.system, queryFn: getSystem, staleTime: 60_000 });
  if (!data) return null;
  const ocr = data.ocr?.engine;
  const sem = data.semantic;
  return (
    <div className="flex flex-wrap items-center gap-2 text-[12.5px] text-muted">
      <Badge tone={ocr ? "strong" : "muted"} dot><ScanText className="h-3.5 w-3.5" />{ocr ? `OCR on (${data.ocr.label}, ${data.ocr.languages.join(", ")})` : "OCR off"}</Badge>
      <Badge tone={sem?.enabled ? "strong" : "muted"} dot><Sparkles className="h-3.5 w-3.5" />{sem?.enabled ? `Semantic search on · ${sem.indexed} of ${sem.passages} passages embedded` : "Keyword search only"}</Badge>
    </div>
  );
}

/** Files: PDF, Word, text, or a photo/scan (read with OCR). Several at once, each with its own progress and result. */
export function UploadPanel({ subjectId }) {
  const qc = useQueryClient();
  const input = useRef(null);
  const [drag, setDrag] = useState(false);
  const [role, setRole] = useState("notes");
  const [queue, setQueue] = useState([]); // [{key, name, pct, state, note}]
  const [url, setUrl] = useState("");
  const [fetching, setFetching] = useState(false);
  const [urlError, setUrlError] = useState("");
  const { data: sys } = useQuery({ queryKey: keys.system, queryFn: getSystem, staleTime: 60_000 });
  const ocr = !!sys?.ocr?.engine;

  const patch = (key, p) => setQueue((q) => q.map((x) => (x.key === key ? { ...x, ...p } : x)));
  async function send(files) {
    const items = [...files].map((f, i) => ({ key: `${Date.now()}-${i}-${f.name}`, file: f, name: f.name, pct: 0, state: "waiting", note: "" }));
    setQueue((q) => [...items.map(({ file, ...x }) => x), ...q].slice(0, 12));
    for (const it of items) {
      const f = it.file;
      if (f.size > MAX_MB * 1048576) { patch(it.key, { state: "error", note: `Larger than ${MAX_MB} MB` }); continue; }
      if (IMAGE.test(f.name) && !ocr) { patch(it.key, { state: "error", note: "Photos need OCR, which is off on this server" }); continue; }
      patch(it.key, { state: "uploading" });
      try {
        const r = check(Upload, await uploadFile(`/subjects/${subjectId}/materials`, f, (pct) => patch(it.key, { pct, state: pct >= 100 ? "reading" : "uploading" }), { role }));
        const d = r.document;
        patch(it.key, { state: r.duplicate ? "duplicate" : d.status === "parsed" ? "done" : "warn", pct: 100,
          note: r.duplicate ? "Already in this subject" : d.status === "parsed" ? `${plural(d.chunks, "passage")}${d.ocr_pages ? `, ${plural(d.ocr_pages, "page")} read with OCR` : ""}` : d.warnings[0] || d.status });
        if (!r.duplicate) toast.success(`Added “${d.title}”`, { description: `${plural(d.chunks, "passage")} ready to search and quiz.` });
        await refresh(qc, subjectId);
        qc.invalidateQueries({ queryKey: keys.system });
      } catch (e) {
        patch(it.key, { state: "error", note: friendlyError(e) });
      }
    }
    if (input.current) input.current.value = "";
  }

  async function addPage(e) {
    e.preventDefault();
    setUrlError("");
    if (!url.trim()) return setUrlError("Paste a web address first.");
    setFetching(true);
    try {
      const r = check(Upload, await api(`/subjects/${subjectId}/materials/url`, { method: "POST", json: { url: url.trim(), role } }));
      toast[r.duplicate ? "info" : "success"](r.duplicate ? "That page is already in this subject." : `Added “${r.document.title}”`, { description: r.duplicate ? undefined : `${plural(r.document.chunks, "passage")}` });
      setUrl("");
      await refresh(qc, subjectId);
    } catch (err) { setUrlError(friendlyError(err)); }
    finally { setFetching(false); }
  }

  const icon = { waiting: Loader2, uploading: Loader2, reading: Loader2, done: CheckCircle2, duplicate: CheckCircle2, warn: XCircle, error: XCircle };
  return (
    <div className="rounded-xl border border-border/80 bg-surface p-4 shadow-card sm:p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold">Add material</h2>
          <p className="text-sm text-muted">Nexus reads it, splits it into passages and finds its topics. Only your own files are ever used to answer.</p>
        </div>
        <Field label="This material is" htmlFor="doc-role" className="w-full sm:w-56">
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger id="doc-role" className="h-9 text-sm"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="notes">Notes or a textbook</SelectItem>
              <SelectItem value="syllabus">A syllabus</SelectItem>
              <SelectItem value="pyq">Past exam papers</SelectItem>
            </SelectContent>
          </Select>
        </Field>
      </div>
      {role === "pyq" && <Alert tone="info" className="mt-3">Past papers are not turned into topics. Nexus counts which topics they ask about and puts those first in your plan.</Alert>}
      <Tabs defaultValue="files" className="mt-4">
        <TabsList><TabsTrigger value="files"><UploadCloud />Files</TabsTrigger><TabsTrigger value="web"><Globe />Web page</TabsTrigger></TabsList>
        <TabsContent value="files" className="mt-3">
          <label htmlFor="file-input"
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); send(e.dataTransfer.files); }}
            className={cn("flex min-h-36 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-center transition-colors focus-within:ring-4 focus-within:ring-brand/20",
              drag ? "border-brand bg-brand-wash" : "border-brand/25 bg-surface-2 hover:border-brand/50 hover:bg-brand-wash")}>
            <span className="grid h-12 w-12 place-items-center rounded-full bg-brand text-white shadow-[0_6px_18px_-6px_rgb(1_148_226/.8)]"><UploadCloud className="h-6 w-6" aria-hidden="true" /></span>
            <span className="font-semibold">Drop files here, or choose them</span>
            <span className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[13px] text-muted">
              <span className="inline-flex items-center gap-1"><FileText className="h-3.5 w-3.5" />PDF, Word, text</span>
              <span className={cn("inline-flex items-center gap-1", !ocr && "line-through")}><FileImage className="h-3.5 w-3.5" />photos and scans (OCR)</span>
              <span>up to {MAX_MB} MB each</span>
            </span>
            <input id="file-input" ref={input} type="file" multiple className="sr-only" onChange={(e) => send(e.target.files)}
              accept={`.pdf,.docx,.txt,.md,text/plain,application/pdf${ocr ? ",image/png,image/jpeg,image/webp,image/tiff,image/bmp" : ""}`} />
          </label>
          <AnimatePresence initial={false}>
            {queue.length > 0 && (
              <motion.ul initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-3 space-y-2" aria-live="polite">
                {queue.map((q) => {
                  const Icon = icon[q.state];
                  const busy = ["waiting", "uploading", "reading"].includes(q.state);
                  return (
                    <li key={q.key} className="rounded-lg border border-border bg-surface px-3 py-2">
                      <div className="flex items-center gap-2 text-sm">
                        <Icon className={cn("h-4 w-4 shrink-0", busy && "animate-spin text-brand", q.state === "done" || q.state === "duplicate" ? "text-strong" : "", q.state === "error" || q.state === "warn" ? "text-weak" : "")} aria-hidden="true" />
                        <span className="min-w-0 flex-1 truncate font-medium">{q.name}</span>
                        <span className="shrink-0 text-[12.5px] text-muted">{q.state === "uploading" ? `${q.pct}%` : q.state === "reading" ? "Reading and indexing…" : q.state === "waiting" ? "Waiting" : q.note}</span>
                      </div>
                      {busy && <Progress value={q.state === "reading" ? 100 : q.pct} className="mt-2 h-1.5" indicatorClassName={q.state === "reading" ? "animate-pulse" : ""} />}
                    </li>
                  );
                })}
              </motion.ul>
            )}
          </AnimatePresence>
        </TabsContent>
        <TabsContent value="web" className="mt-3">
          <form onSubmit={addPage} className="space-y-3">
            <p className="text-sm text-muted">Public pages only (articles, documentation, lecture notes). Nexus keeps the readable text as it is today.</p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input type="url" inputMode="url" aria-label="Web address" placeholder="https://en.wikipedia.org/wiki/Queue_(abstract_data_type)" value={url} onChange={(e) => setUrl(e.target.value)} maxLength={2000} />
              <Button type="submit" loading={fetching}><Globe className="h-4 w-4" />Add page</Button>
            </div>
            {urlError && <Alert tone="danger">{urlError}</Alert>}
          </form>
        </TabsContent>
      </Tabs>
    </div>
  );
}
