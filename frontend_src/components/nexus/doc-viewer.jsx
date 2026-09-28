"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Download, ExternalLink, FileText, X } from "lucide-react";
import { getDoc, getDocs, keys } from "@/lib/queries";
import { cn, pageLabel } from "@/lib/utils";
import { Alert, Skeleton, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/primitives";

/** Shows the uploaded material itself: a PDF in the page's own viewer (jumping to a page), or the extracted passages for other files. */
export function DocPane({ subjectId, target, onClose }) {
  const docs = useQuery({ queryKey: keys.docs(subjectId), queryFn: () => getDocs(subjectId) });
  const [docId, setDocId] = useState(target?.docId ?? null);
  useEffect(() => { if (target?.docId) setDocId(target.docId); }, [target]);
  const list = docs.data ?? [];
  const current = docId ?? list[0]?.id ?? null;
  const doc = useQuery({ queryKey: keys.doc(subjectId, current), queryFn: () => getDoc(subjectId, current), enabled: current !== null });
  const cited = useRef(null);
  const quote = target?.docId === current ? target?.quote : null;
  const passageId = target?.docId === current ? target?.passageId : null;

  useEffect(() => {
    const el = cited.current;
    if (el) el.scrollIntoView({ block: "center", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }, [doc.data, passageId, quote]);

  const d = doc.data?.document;
  const fileUrl = `/api/v1/subjects/${subjectId}/materials/${current}/file`;
  const page = target?.docId === current && target?.page ? target.page : 1;
  const marked = (t) => {
    if (!quote) return t;
    const i = t.toLowerCase().indexOf(quote.toLowerCase());
    return i < 0 ? t : <>{t.slice(0, i)}<mark>{t.slice(i, i + quote.length)}</mark>{t.slice(i + quote.length)}</>;
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border p-3">
        <FileText className="h-5 w-5 shrink-0 text-brand" aria-hidden="true" />
        {list.length > 1 ? (
          <Select value={String(current ?? "")} onValueChange={(v) => setDocId(Number(v))}>
            <SelectTrigger aria-label="Document" className="h-9 min-w-0 flex-1 rounded-md text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {list.map((x) => <SelectItem key={x.id} value={String(x.id)}>{x.title}</SelectItem>)}
            </SelectContent>
          </Select>
        ) : <p className="break-anywhere min-w-0 flex-1 truncate text-sm font-semibold">{d?.title ?? "Your material"}</p>}
        {current !== null && <Link href={`/subjects/${subjectId}/materials/${current}`} aria-label="Open the document page" className="inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-brand-wash"><ExternalLink className="h-4 w-4" aria-hidden="true" /></Link>}
        {onClose && <button type="button" onClick={onClose} aria-label="Close the document" className="inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-brand-wash"><X className="h-5 w-5" aria-hidden="true" /></button>}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {docs.isPending || (current !== null && doc.isPending) ? <div className="p-3"><Skeleton className="h-40" /></div>
          : current === null ? <p className="p-4 text-sm text-muted">No material uploaded yet.</p>
          : doc.error ? <div className="p-3"><Alert tone="danger">The document could not be opened.</Alert></div>
          : d.kind === "pdf" ? (
            <iframe key={`${current}-${page}`} src={`${fileUrl}#page=${page}`} title={`${d.title}, page ${page}`} className="h-full min-h-[24rem] w-full border-0" />
          ) : d.kind === "image" && !quote ? (
            <img src={fileUrl} alt={d.title} className="mx-auto max-h-full w-auto p-3" />
          ) : (
            <div className="space-y-2 p-3">
              {d.kind === "url" && <p className="break-anywhere text-xs text-muted">Web page: <a href={d.source} target="_blank" rel="noopener noreferrer">{d.source}</a> (as it was when you added it)</p>}
              {d.kind === "docx" && <a href={fileUrl} download className="inline-flex min-h-11 items-center gap-1 text-sm"><Download className="h-4 w-4" aria-hidden="true" /> Download the Word file</a>}
              {doc.data.passages.map((p) => {
                const isCited = passageId != null ? p.id === passageId : !!quote && p.text.toLowerCase().includes(quote.toLowerCase());
                return (
                  <div key={p.id} ref={isCited ? cited : undefined} className={cn("rounded-md border p-3 text-sm", isCited ? "border-brand bg-brand-wash shadow-[0_0_0_3px_rgb(1_148_226/.12)]" : "border-border bg-surface")}>
                    <p className="break-anywhere text-xs text-muted">#{p.ordinal + 1}{p.heading_path && <> · {p.heading_path}</>}{p.page_start != null && <> · {pageLabel(p.page_start, p.page_end)}</>}</p>
                    <p className="break-anywhere mt-1 whitespace-pre-wrap">{isCited ? marked(p.text) : p.text}</p>
                  </div>
                );
              })}
            </div>
          )}
      </div>
      {d?.kind === "pdf" && quote && <p className="border-t border-border p-2 text-xs text-muted">Cited words: <q className="break-anywhere">{quote}</q> (page {page}). Use the viewer&apos;s search to find them.</p>}
    </div>
  );
}

const DESKTOP = "(min-width: 1024px)";
export function useIsDesktop() {
  const [yes, setYes] = useState(false);
  useEffect(() => {
    const m = window.matchMedia(DESKTOP);
    const on = () => setYes(m.matches);
    on();
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return yes;
}

/** On phones and tablets the viewer slides over the chat as a sheet. */
export function DocSheet({ open, onOpenChange, children }) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-brand-ink/45" />
        <DialogPrimitive.Content className="fixed inset-x-0 bottom-0 z-50 flex h-[88dvh] flex-col overflow-hidden rounded-t-xl bg-surface shadow-xl focus:outline-none">
          <DialogPrimitive.Title className="sr-only">Your document</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">The uploaded material, opened at the place the answer used.</DialogPrimitive.Description>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
