"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, Trash2 } from "lucide-react";
import { api, fetchSession } from "@/lib/api";
import { getAccount, keys } from "@/lib/queries";
import { friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { EmailSettings } from "@/components/nexus/email-settings";
import { useLogout } from "@/components/nexus/shell";
import { ErrorState, PageHeader } from "@/components/nexus/common";
import { SystemCard } from "@/components/nexus/system-card";
import { Alert, Button, Card, Checkbox, Dialog, DialogClose, DialogContent, DialogTrigger, Input, Label, Skeleton, Switch } from "@/components/ui/primitives";

function ProfileName({ user }) {
  const qc = useQueryClient();
  const [username, setUsername] = useState(user.username);
  const [problem, setProblem] = useState("");
  const save = useMutation({
    mutationFn: () => api("/account/profile", { method: "PUT", json: { username } }),
    onSuccess: (r) => { setUsername(r.username); setProblem(""); qc.invalidateQueries({ queryKey: keys.session }); qc.invalidateQueries({ queryKey: keys.account }); toast.success("Name updated"); },
    onError: (e) => setProblem(friendlyError(e)),
  });
  return (
    <Card id="profile" className="mt-5 scroll-mt-20 p-5">
      <div className="flex items-center gap-4">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-brand font-display text-2xl font-semibold uppercase text-white" aria-hidden="true">{user.username.slice(0, 1)}</span>
        <div className="min-w-0">
          <h2 className="break-anywhere text-lg font-bold">{user.username}</h2>
          <p className="break-anywhere text-sm text-muted">{user.email ?? "No email on this account"}</p>
        </div>
      </div>
      <form className="mt-4 grid max-w-xl gap-3 sm:grid-cols-[1fr_auto] sm:items-end" onSubmit={(e) => { e.preventDefault(); setProblem(""); save.mutate(); }}>
        <div>
          <Label htmlFor="ac-name">Username</Label>
          <Input id="ac-name" value={username} maxLength={32} onChange={(e) => setUsername(e.target.value)} autoCapitalize="none" spellCheck={false} />
          <p className="mt-1 text-xs text-muted">Shown in the top bar. 3 to 32 letters, digits, dot, dash or underscore.</p>
        </div>
        <Button type="submit" disabled={save.isPending || username.trim() === user.username}>{save.isPending ? "Saving…" : "Save name"}</Button>
      </form>
      {problem && <Alert tone="danger" className="mt-3">{problem}</Alert>}
    </Card>
  );
}

function Academic({ initial }) {
  const qc = useQueryClient();
  const [department, setDepartment] = useState(initial?.department ?? "");
  const [semester, setSemester] = useState(initial?.semester ? String(initial.semester) : "");
  const [problem, setProblem] = useState("");
  const save = useMutation({
    mutationFn: () => api("/account/academic", { method: "PUT", json: { department, semester: semester ? Number(semester) : null } }),
    onSuccess: () => { setProblem(""); qc.invalidateQueries({ queryKey: keys.account }); qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "twin" }); toast.success("Saved"); },
    onError: (e) => setProblem(friendlyError(e)),
  });
  return (
    <Card className="mt-6 p-5" id="study">
      <h2 className="font-display text-lg font-semibold">Study setup</h2>
      <p className="mt-1 text-sm text-muted">Shown on your learner profile. Set each subject&apos;s exam date on its Roadmap tab.</p>
      <form className="mt-3 grid max-w-xl gap-3 sm:grid-cols-[1fr_9rem_auto] sm:items-end" onSubmit={(e) => { e.preventDefault(); setProblem(""); save.mutate(); }}>
        <div><Label htmlFor="ac-dept">Department or course</Label><Input id="ac-dept" value={department} maxLength={80} onChange={(e) => setDepartment(e.target.value)} placeholder="e.g. Computer Science" /></div>
        <div><Label htmlFor="ac-sem">Semester</Label><Input id="ac-sem" type="number" min={1} max={12} value={semester} onChange={(e) => setSemester(e.target.value)} /></div>
        <Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save"}</Button>
      </form>
      {problem && <Alert tone="danger" className="mt-3">{problem}</Alert>}
    </Card>
  );
}

function ChangePassword() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [problem, setProblem] = useState("");
  const save = useMutation({
    mutationFn: () => api("/account/password", { method: "POST", json: { current, new: next } }),
    onSuccess: () => { setCurrent(""); setNext(""); setAgain(""); setProblem(""); toast.success("Password changed. Your other devices were signed out."); },
    onError: (e) => setProblem(friendlyError(e)),
  });
  return (
    <Card className="mt-6 p-5 scroll-mt-20" id="security">
      <h2 className="font-display text-lg font-semibold">Password and security</h2>
      <form className="mt-3 max-w-sm space-y-3" onSubmit={(e) => { e.preventDefault(); setProblem(""); if (next !== again) return setProblem("The two new passwords are not the same."); save.mutate(); }}>
        <div><Label htmlFor="pw-current">Current password</Label><Input id="pw-current" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required /></div>
        <div><Label htmlFor="pw-new">New password</Label><Input id="pw-new" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} required /></div>
        <div><Label htmlFor="pw-again">New password again</Label><Input id="pw-again" type="password" autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} required /></div>
        {problem && <Alert tone="danger">{problem}</Alert>}
        <Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Change password"}</Button>
      </form>
    </Card>
  );
}

function DeleteAccount() {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [problem, setProblem] = useState("");
  const del = useMutation({
    mutationFn: () => api("/account/delete", { method: "POST", json: { password, confirm } }),
    onSuccess: async () => { qc.clear(); await fetchSession(); toast.success("Your account and all its data were deleted."); router.replace("/login"); },
    onError: (e) => setProblem(friendlyError(e)),
  });
  return (
    <Card className="mt-6 p-5 border-weak/40">
      <h2 className="font-display text-lg font-semibold text-weak">Delete my account</h2>
      <p className="mt-1 text-sm">Permanently removes every subject, uploaded file, question, quiz and score, then the account itself. This cannot be undone. Download your data first if you want a copy.</p>
      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) { setPassword(""); setConfirm(""); setProblem(""); } }}>
        <DialogTrigger asChild><Button variant="danger" className="mt-3"><Trash2 className="h-4 w-4" aria-hidden="true" /> Delete my account…</Button></DialogTrigger>
        <DialogContent title="Delete your account?" description="Everything you uploaded and every score will be erased for good.">
          <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); setProblem(""); del.mutate(); }}>
            <div><Label htmlFor="del-pw">Your password</Label><Input id="del-pw" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></div>
            <div><Label htmlFor="del-word">Type DELETE to confirm</Label><Input id="del-word" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" required /></div>
            {problem && <Alert tone="danger">{problem}</Alert>}
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <DialogClose asChild><Button type="button" variant="secondary">Cancel</Button></DialogClose>
              <Button type="submit" variant="danger" disabled={del.isPending || confirm !== "DELETE" || !password}>{del.isPending ? "Deleting…" : "Delete everything"}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

export default function AccountPage() {
  useTitle("Account");
  const qc = useQueryClient();
  const logout = useLogout();
  const [local, setLocal] = useState(null); // the switch moves the instant it is clicked
  const { data, isPending, error, refetch } = useQuery({ queryKey: keys.account, queryFn: getAccount });
  const save = useMutation({
    mutationFn: (consent) => api("/account/cloud", { method: "PUT", json: { consent } }),
    onSuccess: (r) => toast.success(r.cloud_consent ? "Cloud fallback allowed" : "Cloud fallback off"),
    onError: (e) => toast.error(friendlyError(e)),
    // Whatever happened, take the server's answer and drop the local value (a refused change flips the switch back).
    onSettled: async () => { await qc.invalidateQueries({ queryKey: keys.account }); setLocal(null); },
  });
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <Skeleton className="h-40" />;
  const on = local ?? data.user.cloud_consent;
  return (
    <div>
      <PageHeader title="Account" description="Your profile, sign-in, privacy, AI settings and data." className="mb-0" />
      <div className="lg:grid lg:grid-cols-[12rem_minmax(0,1fr)] lg:gap-8">
        <nav aria-label="Account sections" className="mt-4 flex gap-1 overflow-x-auto pb-1 lg:sticky lg:top-20 lg:mt-5 lg:flex-col lg:self-start lg:overflow-visible">
          {[["profile", "Profile"], ["study", "Study setup"], ["email", "Email and sign-in"], ["security", "Password"], ["ai", "AI models and privacy"], ["system", "Search and OCR"], ["data", "Your data"], ["danger", "Delete account"]].map(([id, label]) => (
            <a key={id} href={`#${id}`} className="inline-flex min-h-11 shrink-0 items-center rounded-md px-3 text-sm font-semibold text-muted no-underline hover:bg-brand-wash hover:text-brand-deep">{label}</a>
          ))}
        </nav>
        <div className="max-w-3xl min-w-0">
      <ProfileName user={{ ...data.user, email: data.email?.login ?? data.user.email }} />
      <Academic key={JSON.stringify(data.academic)} initial={data.academic} />
      <div id="email" className="scroll-mt-20">{data.email && <EmailSettings info={data.email} />}</div>
      <ChangePassword />
      <Card className="mt-6 p-5 scroll-mt-20" id="ai">
        <h2 className="font-display text-lg font-semibold">AI models and privacy</h2>
        <p className="mt-1 text-sm">If you allow it, Nexus asks a fast cloud model (OpenRouter) first, and uses the model on this computer as the backup when the cloud is unavailable or the shared credit runs low. Small checks always run on this computer.</p>
        <p className="mt-2 text-sm"><b>If you allow this, the passages found for your question (a few paragraphs, never your whole files) are sent to OpenRouter and the model provider.</b> If you do not, nothing ever leaves this computer.</p>
        <p className="mt-2 text-xs text-muted">Cloud key configured on the server: <b>{data.key_configured ? "yes" : "no"}</b>{data.allowed_models.length > 0 && <> · allowed models: {data.allowed_models.join(", ")}</>}</p>
        <label className="mt-4 flex min-h-11 cursor-pointer items-center gap-3">
          <Switch aria-label="Use cloud models first, with this computer as the backup" checked={on} onCheckedChange={(checked) => { setLocal(!!checked); save.mutate(!!checked); }} />
          <span className="text-sm font-semibold">Use cloud models (OpenRouter) first, with this computer as the backup</span>
        </label>
      </Card>

      <div id="system" className="scroll-mt-20"><SystemCard /></div>

      <Card className="mt-6 p-5 scroll-mt-20" id="data">
        <h2 className="font-display text-lg font-semibold">Your data</h2>
        <p className="mt-1 text-sm">Download everything the account holds (subjects, the text of your materials, questions, practice questions, quizzes and answers), or your analytics as a formatted workbook.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button asChild variant="secondary"><a href="/api/v1/account/export" download className="no-underline"><Download className="h-4 w-4" aria-hidden="true" />All my data (JSON)</a></Button>
          <Button asChild variant="secondary"><a href="/api/v1/analytics/workbook.xlsx" download className="no-underline"><Download className="h-4 w-4" aria-hidden="true" />Analytics workbook (Excel)</a></Button>
          <Button asChild variant="secondary"><a href="/api/v1/analytics/report.pdf" download className="no-underline"><Download className="h-4 w-4" aria-hidden="true" />Analytics report (PDF)</a></Button>
        </div>
      </Card>

      <div id="danger" className="scroll-mt-20"><DeleteAccount /></div>
      <div className="mt-6"><Button variant="secondary" onClick={logout}>Log out</Button></div>
        </div>
      </div>
    </div>
  );
}
