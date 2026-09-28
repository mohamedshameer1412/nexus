"use client";
// Sign in, sign up and password reset: the NEXUS brand hero with a form card, Tailwind only.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertCircle, ArrowRight, Eye, EyeOff, KeyRound, Lock, Mail, UserRound } from "lucide-react";
import { api, clearOfflineData, fetchSession } from "@/lib/api";
import { keys } from "@/lib/queries";
import { cn, friendlyError } from "@/lib/utils";
import {
  Alert, Button, Checkbox, Segmented,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/primitives";

// ------------------------------------------------------------------------------------------------ fields

export function AuthField({ label, hideLabel = false, icon: Icon = null, error = null, hint = "", end = null, id: given = undefined, inputRef = null, className = "", ...input }) {
  const auto = useId();
  const id = given ?? auto;
  const describedBy = [error ? `${id}-err` : null, hint ? `${id}-hint` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className={hideLabel ? "sr-only" : "mb-1.5 block text-[13px] font-semibold"}>{label}</label>
      <div className={cn("flex items-center gap-2 border bg-surface transition-[border,box-shadow] focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/15", hideLabel ? "h-12 rounded-xl px-4" : "h-11 rounded-lg px-3",
        error ? "border-weak ring-weak/10" : "border-border hover:border-brand/40")}>
        {Icon && <Icon className="h-[18px] w-[18px] shrink-0 text-muted" aria-hidden="true" />}
        <input id={id} ref={inputRef} aria-invalid={!!error} aria-describedby={describedBy} className="h-full min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-muted/70 focus-visible:outline-none" {...input} />
        {end}
      </div>
      {error ? <p id={`${id}-err`} role="alert" className="mt-1.5 text-[13px] font-medium text-weak">{error}</p>
        : hint ? <p id={`${id}-hint`} className="mt-1.5 text-[12.5px] text-muted">{hint}</p> : null}
    </div>
  );
}

export function strength(pw) {
  const p = pw || "";
  if (!p) return { score: 0, label: "", tip: "" };
  let points = 0;
  if (p.length >= 8) points += 1;
  if (p.length >= 12) points += 1;
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) points += 1;
  if (/\d/.test(p) && /[^A-Za-z0-9]/.test(p)) points += 1;
  if (/^(.)\1+$/.test(p) || /^(password|12345678|qwertyui)/i.test(p)) points = Math.min(points, 1);
  const score = Math.max(1, Math.min(4, points));
  return { score, label: ["", "Weak", "Fair", "Good", "Strong"][score], tip: p.length < 8 ? "Use at least 8 characters" : score < 3 ? "A longer phrase with mixed characters is stronger" : "" };
}

export function PasswordField({ label, hideLabel = false, value, onChange, error = null, hint = "", showStrength = false, id = undefined, name = "", placeholder = "", autoComplete = "" }) {
  const [visible, setVisible] = useState(false);
  const [caps, setCaps] = useState(false);
  const s = strength(value);
  const colors = ["bg-border", "bg-weak", "bg-mid", "bg-brand", "bg-strong"];
  return (
    <div>
      <AuthField id={id} name={name} label={label} hideLabel={hideLabel} icon={Lock} error={error} hint={hint} placeholder={placeholder} autoComplete={autoComplete}
        type={visible ? "text" : "password"} value={value} onChange={(e) => onChange(e.target.value)} maxLength={128} spellCheck={false} autoCapitalize="none"
        onKeyUp={(e) => setCaps(e.getModifierState?.("CapsLock") ?? false)} onBlur={() => setCaps(false)}
        end={<button type="button" onClick={() => setVisible((v) => !v)} aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible}
          className="grid h-8 w-8 place-items-center rounded-md text-muted hover:bg-brand-wash hover:text-foreground">{visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>} />
      {caps && <p role="status" className="mt-1.5 text-[12.5px] font-semibold text-mid">Caps Lock is on.</p>}
      {showStrength && value && (
        <div className="mt-2">
          <div className="grid grid-cols-4 gap-1" aria-hidden="true">{[1, 2, 3, 4].map((i) => <span key={i} className={cn("h-1.5 rounded-full transition-colors", i <= s.score ? colors[s.score] : "bg-border")} />)}</div>
          <p role="status" className="mt-1 text-[12.5px] text-muted">Strength: <b className="text-foreground">{s.label}</b>{s.tip ? `. ${s.tip}` : ""}</p>
        </div>
      )}
    </div>
  );
}

export function FormError({ children }) {
  if (!children) return null;
  return <div role="alert" className="flex items-start gap-2 rounded-lg border border-weak/25 bg-weak-bg px-3 py-2.5 text-sm text-[#8F2219]"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{children}</div>;
}

// ─── Brand hero, shared by the splash and sign-in screens ────────────────────

export function Waves() {
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 1200 800" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0 150 C 260 60, 520 250, 820 130 S 1120 40, 1200 90 L1200 0 L0 0 Z" fill="#D8E8FF" opacity=".7" />
      <path d="M0 330 C 300 230, 560 420, 900 300 S 1150 250, 1200 280 L1200 0 L0 0 Z" fill="#E6F0FF" opacity=".55" />
      <path d="M0 800 L0 640 C 240 560, 520 720, 800 640 S 1100 580, 1200 620 L1200 800 Z" fill="#CFE2FF" opacity=".75" />
      <path d="M0 800 L0 710 C 300 650, 560 780, 860 700 S 1120 660, 1200 690 L1200 800 Z" fill="#B9D5FD" opacity=".55" />
    </svg>
  );
}

export function GovLine({ className = "" }) {
  return (
    <p className={cn("text-center text-[13px] font-bold leading-tight text-[#0B2A5B]", className)}>
      Government of India<br /><span className="font-semibold text-[#33476A]">MoSPI</span>
    </p>
  );
}

export function Lockup({ className = "" }) {
  return (
    <div className={cn("text-center", className)}>
      <img src="/assets/generated/nexus-lockup.png" alt="NEXUS: Adaptive Competency & Career Learning Loop" className="mx-auto w-[300px] max-w-full lg:w-[340px]" />
      <p className="mt-3 text-[15px] leading-snug text-[#33476A]">Empowering Statistical Officers<br />for a Data-Ready India</p>
    </div>
  );
}

export const TAGLINE = ["Right Learning.", "Real Progress.", "Stronger Officers.", "Data-Driven Nation."];

export function AuthShell({ children }) {
  return (
    <div className="relative min-h-dvh overflow-hidden bg-gradient-to-br from-[#F7FAFE] via-[#EAF4FF] to-[#DCEBFF]">
      <Waves />
      <div className="relative mx-auto grid min-h-dvh max-w-[1280px] items-center gap-8 px-5 py-8 lg:grid-cols-[1fr_470px] lg:px-12">
        {/* Brand column */}
        <div className="relative flex flex-col items-center lg:h-full lg:justify-start lg:pt-10">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="flex flex-col items-center">
            <GovLine />
            <Lockup className="mt-6 hidden lg:block" />
            <img src="/assets/generated/nexus-wordmark.png" alt="NEXUS" className="mt-4 w-[190px] lg:hidden" />
            <p className="mt-2 text-center text-[15px] font-semibold text-[#0B2A5B] lg:hidden">Adaptive Competency &amp; Career Learning Loop</p>
          </motion.div>
          <motion.img initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.15 }}
            src="/assets/generated/government-building.png" alt="" aria-hidden="true" className="mt-auto hidden w-[440px] max-w-full lg:block [mask-image:linear-gradient(to_bottom,black_82%,transparent)]" />
        </div>
        {/* Card */}
        <main id="main" className="w-full rounded-3xl bg-white/95 p-6 shadow-[0_20px_60px_rgb(20_100_232/.14)] backdrop-blur sm:p-9 lg:self-center">
          {children}
        </main>
      </div>
    </div>
  );
}

// ─── Sign in / Sign up ────────────────────────────────────────────────────────

const EMAIL = /^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$/;
const USERNAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{2,31}$/;
const DEPARTMENTS = ["National Statistics Office (NSO)", "Survey Design & Research Division", "Data Processing Division", "Field Operations Division", "Economic Statistics Division", "NSSTA, Greater Noida", "Computer Centre"];

function validate(mode, f) {
  const e = {};
  if (mode === "login") {
    if (!f.email.trim()) e.email = "Enter your email address or username.";
    if (!f.password) e.password = "Enter your password.";
    return e;
  }
  if (!USERNAME.test(f.username.trim())) e.username = "Use 3 to 32 letters, digits, dot, dash or underscore, starting with a letter or digit.";
  if (!EMAIL.test(f.email.trim())) e.email = "Enter a valid email address, for example you@example.com.";
  if (f.password.length < 8) e.password = "Use at least 8 characters.";
  else if (f.password.length > 128) e.password = "Use at most 128 characters.";
  if (!e.password && f.confirm !== f.password) e.confirm = "The two passwords do not match.";
  if (!f.agree) e.agree = "Please confirm this to continue.";
  return e;
}

const METHODS = [{ value: "Government SSO", label: "Government SSO" }, { value: "NIC Email", label: "NIC Email" }];

/** The Government SSO / NIC Email toggle: the shared Radix ToggleGroup Segmented control, sized up for the sign-in card. */
function MethodSegmented({ value, onChange }) {
  return (
    <Segmented value={value} onValueChange={onChange} options={METHODS} label="Sign-in method"
      className="grid w-full grid-cols-2 gap-3 bg-transparent p-0"
      itemClassName="h-12 w-full justify-center rounded-xl text-[14px] font-semibold data-[state=on]:bg-[#1E7BF2] data-[state=on]:text-white data-[state=on]:shadow-[0_6px_16px_rgb(20_100_232/.3)] data-[state=off]:border data-[state=off]:border-[#E3ECF8] data-[state=off]:bg-white data-[state=off]:text-[#0B2A5B] data-[state=off]:hover:border-[#BFD6FA]" />
  );
}

/** Department picker: Radix Select, so it opens as a styled panel instead of the browser's native list. */
function DepartmentSelect({ value, onChange }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id="dept" aria-label="Department" className="h-12 gap-2.5 rounded-xl border-[#E3ECF8] pl-4 text-[14.5px] hover:border-[#BFD6FA]">
        <UserRound className="h-[18px] w-[18px] shrink-0 text-[#0B2A5B]" aria-hidden="true" />
        <SelectValue placeholder="Select Department" />
      </SelectTrigger>
      <SelectContent>
        {DEPARTMENTS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}

export function AuthScreen({ initial = "login" }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [mode, setMode] = useState(initial);
  const [method, setMethod] = useState("Government SSO");
  const [dept, setDept] = useState("");
  const [form, setForm] = useState({ username: "", email: "", password: "", confirm: "", agree: false });
  /** @type {any} */
  const initialErrors = {};
  const [errors, setErrors] = useState(initialErrors);
  const [serverError, setServerError] = useState("");
  const [pending, setPending] = useState(false);
  const first = useRef(null);
  const isLogin = mode === "login";

  useEffect(() => { (async () => { const s = await fetchSession(); if (s.authenticated) router.replace("/dashboard"); })(); }, [router]);
  useEffect(() => { document.title = isLogin ? "Sign in · NEXUS" : "Create your account · NEXUS"; }, [isLogin]);

  const set = (name, value) => { setForm((f) => ({ ...f, [name]: value })); setErrors((e) => ({ ...e, [name]: undefined })); };
  const switchTo = (next) => { setServerError(""); setErrors({}); setMode(next); window.history.replaceState(null, "", next === "register" ? "/register" : "/login"); };
  const fillDemo = () => { setMethod("NIC Email"); setForm((f) => ({ ...f, email: "demo@nexus.local", password: "nexus-demo-2026" })); setErrors({}); };

  async function submit(ev) {
    ev.preventDefault();
    setServerError("");
    const found = validate(mode, form);
    setErrors(found);
    if (Object.keys(found).length) return;
    setPending(true);
    try {
      await api(isLogin ? "/login" : "/register", { method: "POST", json: isLogin ? { email: form.email.trim(), password: form.password } : { username: form.username.trim(), email: form.email.trim(), password: form.password } });
      qc.removeQueries();
      clearOfflineData();
      await qc.invalidateQueries({ queryKey: keys.session });
      if (!isLogin) toast.success("Welcome to NEXUS", { description: `We sent a code to ${form.email.trim()}. Enter it under Settings to verify your address.`, duration: 9000 });
      router.replace(isLogin ? "/dashboard" : "/subjects?new=1");
    } catch (e) {
      setServerError(friendlyError(e));
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div key={mode} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
          <h1 className="text-center text-[26px] font-bold text-[#0B2A5B]">{isLogin ? "Welcome Back" : "Create your account"}</h1>
          <p className="mt-1 text-center text-[14.5px] text-[#5A6E8C]">{isLogin ? "Sign in to continue your learning journey" : "It takes less than a minute."}</p>
          {isLogin && (
            <Alert tone="info" icon={KeyRound} className="mt-5 items-center">
              <div className="flex items-center justify-between gap-3">
                <p className="min-w-0">Demo account:<br /><b className="font-semibold">demo@nexus.local</b> / <b className="font-semibold">nexus-demo-2026</b></p>
                <Button type="button" variant="secondary" size="sm" className="h-8 shrink-0 rounded-lg" onClick={fillDemo}>Use this</Button>
              </div>
            </Alert>
          )}
          <form className="mt-6 space-y-4" onSubmit={submit} noValidate>
            <FormError>{serverError}</FormError>
            {isLogin ? (
              <>
                <MethodSegmented value={method} onChange={setMethod} />
                <DepartmentSelect value={dept} onChange={setDept} />
                <AuthField label={method === "NIC Email" ? "NIC email" : "Username or email"} hideLabel icon={Lock} name="email" autoComplete="username" inputRef={first}
                  placeholder={method === "NIC Email" ? "name@gov.in" : "Enter your credentials"} type="text" inputMode="email"
                  value={form.email} onChange={(e) => set("email", e.target.value)} error={errors.email} maxLength={254} spellCheck={false} autoCapitalize="none" />
                <PasswordField label="Password" hideLabel name="password" placeholder="Password" autoComplete="current-password" value={form.password} onChange={(v) => set("password", v)} error={errors.password} />
                <div className="flex justify-end"><Link href="/forgot-password" className="text-[13px] font-semibold">Forgot password?</Link></div>
              </>
            ) : (
              <>
                <AuthField label="Username" icon={UserRound} placeholder="e.g. priya.k" autoComplete="nickname" inputRef={first} name="username" value={form.username}
                  onChange={(e) => set("username", e.target.value)} error={errors.username} maxLength={32} spellCheck={false} autoCapitalize="none" hint="Shown in the top bar." />
                <AuthField label="Email address" icon={Mail} placeholder="you@example.com" type="email" inputMode="email" name="email" autoComplete="email"
                  value={form.email} onChange={(e) => set("email", e.target.value)} error={errors.email} maxLength={254} spellCheck={false} autoCapitalize="none" />
                <PasswordField label="Password" name="password" placeholder="At least 8 characters" autoComplete="new-password" value={form.password} onChange={(v) => set("password", v)} error={errors.password} showStrength />
                <PasswordField label="Confirm password" name="confirm" placeholder="Type it again" autoComplete="new-password" value={form.confirm} onChange={(v) => set("confirm", v)} error={errors.confirm} />
                <div>
                  <label className="flex cursor-pointer items-start gap-2.5 text-[13.5px] text-muted">
                    <Checkbox checked={form.agree} onCheckedChange={(v) => set("agree", !!v)} aria-invalid={!!errors.agree} className="mt-0.5" />
                    <span>My study materials are stored on this server and are sent to a cloud model only if I allow it under Settings.</span>
                  </label>
                  {errors.agree && <p role="alert" className="mt-1.5 text-[13px] font-medium text-weak">{errors.agree}</p>}
                </div>
              </>
            )}
            <Button type="submit" size="lg" loading={pending} className="relative h-12 w-full rounded-xl bg-[#0B2A5B] text-[15px] hover:bg-[#123A78]">
              {isLogin ? "Sign In" : "Create account"}{!pending && <ArrowRight className="absolute right-5 h-5 w-5" />}
            </Button>
          </form>
          <p className="mt-5 text-center text-[13.5px] text-[#5A6E8C]">
            {isLogin ? "New to NEXUS?" : "Already have an account?"}{" "}
            <button type="button" className="font-semibold text-link hover:underline" onClick={() => switchTo(isLogin ? "register" : "login")}>{isLogin ? "Create an account" : "Sign in"}</button>
          </p>
          <p className="mt-3 text-center text-[13px] text-[#5A6E8C]">Secure <span aria-hidden="true">•</span> Official <span aria-hidden="true">•</span> For a Stronger India</p>
        </motion.div>
      </AnimatePresence>
    </AuthShell>
  );
}

