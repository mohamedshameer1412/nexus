"use client";
import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { MailCheck, Send } from "lucide-react";
import { api } from "@/lib/api";
import { keys } from "@/lib/queries";
import { friendlyError } from "@/lib/utils";
import { Alert, Button, Card, Checkbox, Input, Label } from "@/components/ui/primitives";

/** Add and verify an email address (needed to reset a forgotten password), and the optional weekly summary. */
export function EmailSettings({ info }) {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: keys.account });
  const [email, setEmail] = useState(info.login ?? "");
  const [code, setCode] = useState("");
  const [problem, setProblem] = useState("");
  const [wait, setWait] = useState(0);
  const [pending, setPending] = useState(info.pending);
  useEffect(() => setPending(info.pending), [info.pending]);
  useEffect(() => {
    if (wait <= 0) return undefined;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);
  const fail = (e) => { if (e.status === 429 && e.retry_after) setWait(e.retry_after); setProblem(friendlyError(e)); };

  const sendCode = useMutation({
    mutationFn: (address) => api("/account/email", { method: "PUT", json: { email: address } }),
    onSuccess: (r) => { setPending(r.pending); setCode(""); setProblem(""); setWait(60); toast.success("Code sent. Check your inbox (and spam)."); },
    onError: fail,
  });
  const verify = useMutation({
    mutationFn: () => api("/account/email/verify", { method: "POST", json: { code } }),
    onSuccess: () => { setCode(""); setProblem(""); setPending(null); toast.success("Email verified"); refresh(); },
    onError: fail,
  });
  const weekly = useMutation({
    mutationFn: (enabled) => api("/account/weekly", { method: "PUT", json: { enabled } }),
    onSuccess: (r) => { toast.success(r.weekly ? "Weekly summary on" : "Weekly summary off"); refresh(); },
    onError: (e) => toast.error(friendlyError(e)),
  });
  const now = useMutation({
    mutationFn: () => api("/account/digest/send-now", { method: "POST" }),
    onSuccess: () => toast.success("Sent. Check your inbox."),
    onError: (e) => toast.error(friendlyError(e)),
  });

  return (
    <Card className="mt-6 p-5">
      <h2 className="font-display text-lg font-semibold">Email and sign-in</h2>
      {info.login && <p className="mt-1 text-sm">You sign in with <b className="break-anywhere">{info.login}</b>{info.verified ? "." : ". It is not verified yet."}</p>}
      <p className="mt-1 text-sm">A verified email lets you reset a forgotten password with a one-time code, and lets Nexus send you a weekly summary if you want one. It is never shown to anyone or used for anything else.</p>
      {!info.can_send && <Alert tone="warning" className="mt-3">The server has no email account set up yet, so codes cannot be sent. An administrator adds it in the server settings (.env).</Alert>}

      {info.verified ? (
        <div className="mt-3 space-y-3">
          <p className="flex items-center gap-2 text-sm"><MailCheck className="h-5 w-5 text-strong" aria-hidden="true" /> <b className="break-anywhere">{info.address}</b> <span className="text-strong">verified</span></p>
          <label className="flex min-h-11 cursor-pointer items-center gap-3">
            <Checkbox aria-label="Send me a weekly summary" checked={info.weekly} onCheckedChange={(c) => weekly.mutate(!!c)} />
            <span className="text-sm font-semibold">Send me a weekly summary of my progress</span>
          </label>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" onClick={() => now.mutate()} disabled={now.isPending || !info.can_send}><Send className="h-4 w-4" aria-hidden="true" /> {now.isPending ? "Sending…" : "Send this week’s summary now"}</Button>
          </div>
          <details className="rounded-lg border border-border p-3 text-sm">
            <summary className="cursor-pointer font-semibold">Change my email address</summary>
            <form onSubmit={(e) => { e.preventDefault(); setProblem(""); sendCode.mutate(email.trim()); }} className="mt-3 max-w-sm space-y-3">
              <p className="text-muted">A code is sent to the new address. Your login changes to it only after you enter the code.</p>
              <div><Label htmlFor="acc-email-new">New email address</Label><Input id="acc-email-new" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required maxLength={254} /></div>
              {problem && <Alert tone="danger">{problem}</Alert>}
              <Button type="submit" size="sm" disabled={sendCode.isPending || wait > 0 || !info.can_send}>{sendCode.isPending ? "Sending…" : wait > 0 ? `Wait ${wait} s` : "Send a verification code"}</Button>
            </form>
          </details>
        </div>
      ) : (
        <div className="mt-3 max-w-sm space-y-3">
          {!pending ? (
            <form onSubmit={(e) => { e.preventDefault(); setProblem(""); sendCode.mutate(email.trim()); }} className="space-y-3">
              <div><Label htmlFor="acc-email">Email address</Label><Input id="acc-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required maxLength={254} /></div>
              {problem && <Alert tone="danger">{problem}</Alert>}
              <Button type="submit" disabled={sendCode.isPending || wait > 0 || !info.can_send}>{sendCode.isPending ? "Sending…" : wait > 0 ? `Wait ${wait} s` : "Send a verification code"}</Button>
            </form>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); setProblem(""); verify.mutate(); }} className="space-y-3">
              <p className="text-sm">A 6-digit code was sent to <b className="break-anywhere">{pending}</b>. It expires in 10 minutes.</p>
              <div><Label htmlFor="acc-code">6-digit code</Label><Input id="acc-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required className="text-center text-xl tracking-[0.4em]" /></div>
              {problem && <Alert tone="danger">{problem}</Alert>}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={verify.isPending || code.length !== 6}>{verify.isPending ? "Checking…" : "Verify"}</Button>
                <Button type="button" variant="ghost" disabled={sendCode.isPending || wait > 0} onClick={() => sendCode.mutate(pending)}>{wait > 0 ? `Resend in ${wait} s` : "Send a new code"}</Button>
                <Button type="button" variant="ghost" onClick={() => { setPending(null); setProblem(""); }}>Use a different address</Button>
              </div>
            </form>
          )}
        </div>
      )}
    </Card>
  );
}
