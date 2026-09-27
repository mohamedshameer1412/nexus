"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { keys } from "@/lib/queries";
import { friendlyError, plural } from "@/lib/utils";
import {
  Alert, Button, ConfirmDialog, Dialog, DialogContent, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, Field, Input, Textarea,
} from "@/components/ui/primitives";

/** Create a subject. Opens itself when `open` is controlled (e.g. /subjects?new=1). */
export function NewSubjectDialog({ open, onOpenChange, trigger = true }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [inner, setInner] = useState(false);
  const isOpen = open ?? inner;
  const setOpen = onOpenChange ?? setInner;
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [problem, setProblem] = useState("");
  const create = useMutation({
    mutationFn: () => api("/subjects", { method: "POST", json: { name: name.trim(), description: description.trim() } }),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: keys.subjects });
      qc.invalidateQueries({ queryKey: keys.dashboard });
      toast.success(`Created “${s.name}”`, { description: "Upload your first material to get started." });
      setOpen(false);
      setName(""); setDescription("");
      router.push(`/subjects/${s.id}/materials`);
    },
    onError: (e) => setProblem(friendlyError(e)),
  });
  return (
    <Dialog open={isOpen} onOpenChange={(o) => { setOpen(o); setProblem(""); }}>
      {trigger && <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />New subject</Button>}
      <DialogContent title="New subject" description="Each subject keeps its own materials, questions, quizzes and progress.">
        <form className="space-y-4" noValidate onSubmit={(e) => {
          e.preventDefault(); setProblem("");
          if (!name.trim()) return setProblem("Give the subject a name.");
          create.mutate();
        }}>
          {problem && <Alert tone="danger">{problem}</Alert>}
          <Field label="Name" htmlFor="ns-name" hint="For example: Data Structures, Organic Chemistry, Macroeconomics.">
            <Input id="ns-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} autoFocus />
          </Field>
          <Field label="Description (optional)" htmlFor="ns-desc"><Textarea id="ns-desc" value={description} onChange={(e) => setDescription(e.target.value)} maxLength={500} rows={3} /></Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create subject</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** Rename a subject or change its description. Controlled by the actions menu. */
function EditSubjectDialog({ subject, open, onOpenChange }) {
  const qc = useQueryClient();
  const [name, setName] = useState(subject.name);
  const [description, setDescription] = useState(subject.description ?? "");
  const [problem, setProblem] = useState("");
  const save = useMutation({
    mutationFn: () => api(`/subjects/${subject.id}`, { method: "PATCH", json: { name, description } }),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: keys.subjects });
      qc.setQueryData(keys.subject(String(subject.id)), s);
      toast.success("Subject updated");
      onOpenChange(false);
    },
    onError: (e) => setProblem(friendlyError(e)),
  });
  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); setProblem(""); if (o) { setName(subject.name); setDescription(subject.description ?? ""); } }}>
      <DialogContent title="Edit subject" description="Changing the name or description does not touch your materials or progress.">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setProblem(""); if (!name.trim()) return setProblem("Give the subject a name."); save.mutate(); }}>
          {problem && <Alert tone="danger">{problem}</Alert>}
          <Field label="Name" htmlFor={`en-${subject.id}`}><Input id={`en-${subject.id}`} value={name} maxLength={80} onChange={(e) => setName(e.target.value)} autoFocus /></Field>
          <Field label="Description (optional)" htmlFor={`ed-${subject.id}`}><Textarea id={`ed-${subject.id}`} value={description} maxLength={500} onChange={(e) => setDescription(e.target.value)} rows={3} /></Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" loading={save.isPending}>Save changes</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** Edit / delete in one menu. `redirect` sends the student to the subject list after deleting. */
export function SubjectActions({ subject, redirect = false, variant = "secondary" }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [edit, setEdit] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const c = subject.counts ?? {};
  const remove = useMutation({
    mutationFn: () => api(`/subjects/${subject.id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.removeQueries({ predicate: (q) => Array.isArray(q.queryKey) && q.queryKey[1] === String(subject.id) });
      qc.invalidateQueries({ queryKey: keys.subjects });
      qc.invalidateQueries({ queryKey: keys.dashboard });
      toast.success(`Deleted “${subject.name}”`);
      setConfirm(false);
      if (redirect) router.replace("/subjects");
    },
    onError: (e) => toast.error(friendlyError(e)),
  });
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant={variant} size="icon-sm" aria-label={`Actions for ${subject.name}`} onClick={(e) => e.stopPropagation()}><MoreHorizontal className="h-4 w-4" /></Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onSelect={() => setEdit(true)}><Pencil />Edit name and description</DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setConfirm(true)} className="text-weak data-[highlighted]:bg-weak-bg data-[highlighted]:text-weak"><Trash2 />Delete subject</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <EditSubjectDialog subject={subject} open={edit} onOpenChange={setEdit} />
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={`Delete “${subject.name}”?`} confirm="Delete subject" loading={remove.isPending} onConfirm={() => remove.mutate()}
        description={`This permanently removes ${plural(c.documents ?? 0, "material")}, ${plural(c.practice_questions ?? 0, "practice question")}, ${plural(c.questions ?? 0, "answered question")}, and every quiz, note and progress record in this subject. It cannot be undone.`} />
    </>
  );
}
