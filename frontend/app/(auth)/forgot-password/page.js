"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Mail, MailCheck } from "lucide-react";
import { api, fetchSession } from "@/lib/api";
import { friendlyError } from "@/lib/utils";
import { useTitle } from "@/lib/use-title";
import { AuthField, AuthShell, FormError, PasswordField } from "@/components/nexus/auth";
import { Alert, Button } from "@/components/ui/primitives";

/** Two steps: an email address, then the 6-digit code from the email together with the new password. */
export default function ForgotPasswordPage() {
  useTitle("Reset your password");
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [wait, setWait] = useState(0);

  useEffect(() => { fetchSession().catch(() => {}); }, []);
  useEffect(() => { if (wait <= 0) return undefined; const t = setTimeout(() => setWait((w) => w - 1), 1000); return () => clearTimeout(t); }, [wait]);

  async function send(e) {
    e?.preventDefault();
    setError("");
    setBusy(true);
    try { await api("/auth/password/forgot", { method: "POST", json: { email } }); setStep(2); setWait(60); }
    catch (err) { if (err.status === 429 && err.retry_after) setWait(err.retry_after); setError(friendlyError(err)); }
    finally { setBusy(false); }
  }

  async function reset(e) {
    e.preventDefault();
    setError("");
    if (pw !== pw2) return setError("The two new passwords are not the same.");
    setBusy(true);
    try {
      await api("/auth/password/reset", { method: "POST", json: { email, code: code.trim(), new_password: pw } });
      toast.success("Password changed", { description: "Sign in with your new password." });
      await fetchSession();
      router.replace("/login");
    } catch (err) { setError(friendlyError(err)); }
    finally { setBusy(false); }
  }

  return (
    <AuthShell>
      <h1 className="font-display text-[28px] font-semibold leading-tight">Reset your password</h1>
      <p className="mt-1 text-[15px] text-muted">{step === 1 ? "We will email you a 6-digit code." : "Enter the code and choose a new password."}</p>
      {step === 1 ? (
        <form onSubmit={send} className="mt-7 space-y-4" noValidate>
          <FormError>{error}</FormError>
          <AuthField id="fp-email" label="Email address" icon={Mail} type="email" autoComplete="email" inputMode="email" placeholder="you@example.com" value={email}
            onChange={(e) => setEmail(e.target.value)} required maxLength={254} autoCapitalize="none" spellCheck={false} hint="Use the address you signed up with." />
          <Button type="submit" size="lg" className="w-full" loading={busy} disabled={wait > 0}>{wait > 0 ? `Try again in ${wait} s` : "Send me a code"}</Button>
        </form>
      ) : (
        <form onSubmit={reset} className="mt-7 space-y-4" noValidate>
          <Alert tone="info" icon={MailCheck}>If <b className="break-anywhere">{email}</b> belongs to an account, a code is on its way. It expires in 10 minutes; check your spam folder too.</Alert>
          <FormError>{error}</FormError>
          <AuthField id="fp-code" label="6-digit code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required placeholder="000000" className="[&_input]:tracking-[0.5em] [&_input]:font-semibold" />
          <PasswordField id="fp-pw" label="New password" autoComplete="new-password" value={pw} onChange={setPw} showStrength placeholder="At least 8 characters" />
          <PasswordField id="fp-pw2" label="New password again" autoComplete="new-password" value={pw2} onChange={setPw2} placeholder="Type it again" />
          <Button type="submit" size="lg" className="w-full" loading={busy}>Change password</Button>
          <div className="flex flex-wrap justify-between gap-2 text-[13.5px]">
            <button type="button" className="font-semibold text-link disabled:text-muted" disabled={busy || wait > 0} onClick={send}>{wait > 0 ? `New code in ${wait} s` : "Send a new code"}</button>
            <button type="button" className="font-semibold text-link" onClick={() => { setStep(1); setError(""); setCode(""); }}>Use a different address</button>
          </div>
          <p className="text-[12.5px] text-muted">Never share this code. After five wrong tries it stops working.</p>
        </form>
      )}
      <p className="mt-6 text-center text-[14px]"><Link href="/login" className="font-semibold">Back to sign in</Link></p>
    </AuthShell>
  );
}
