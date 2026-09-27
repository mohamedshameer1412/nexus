"use client";
// Sign in, sign up and password reset: one split-screen frame, Tailwind only.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertCircle, ArrowRight, BarChart2, BookOpen, Eye, EyeOff, Globe, Lock, Mail, ShieldCheck, TrendingUp, UserRound, Users } from "lucide-react";
import { api, clearOfflineData, fetchSession } from "@/lib/api";
import { keys } from "@/lib/queries";
import { cn, friendlyError } from "@/lib/utils";
import { Button, Checkbox } from "@/components/ui/primitives";
import { Logo } from "@/components/nexus/common";

// ------------------------------------------------------------------------------------------------ fields

export function AuthField({ label, icon: Icon = null, error = null, hint = "", end = null, id: given = undefined, inputRef = null, className = "", ...input }) {
  const auto = useId();
  const id = given ?? auto;
  const describedBy = [error ? `${id}-err` : null, hint ? `${id}-hint` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-[13px] font-semibold">{label}</label>
      <div className={cn("flex h-11 items-center gap-2 rounded-lg border bg-surface px-3 transition-[border,box-shadow] focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/15",
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

export function PasswordField({ label, value, onChange, error = null, hint = "", showStrength = false, id = undefined, name = "", placeholder = "", autoComplete = "" }) {
  const [visible, setVisible] = useState(false);
  const [caps, setCaps] = useState(false);
  const s = strength(value);
  const colors = ["bg-border", "bg-weak", "bg-mid", "bg-brand", "bg-strong"];
  return (
    <div>
      <AuthField id={id} name={name} label={label} icon={Lock} error={error} hint={hint} placeholder={placeholder} autoComplete={autoComplete}
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

// ─── Splash / Showcase ───────────────────────────────────────────────────────

const PILLARS = [
  { Icon: BarChart2, label: "Smarter\nSkills" },
  { Icon: BookOpen,  label: "Continuous\nLearning" },
  { Icon: Users,     label: "Stronger\nOfficers" },
  { Icon: Globe,     label: "Data-Driven\nNation" },
];

function Showcase() {
  return (
    <div className="relative hidden overflow-hidden lg:flex" style={{ background: "#F7FAFE", minHeight: "100dvh" }}>

      {/* ── Blue wave shapes — sit behind building ── */}
      <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 900 700"
        preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        {/* Top wave */}
        <path d="M0,0 L900,0 L900,120 C700,240 500,60 300,180 C150,270 50,180 0,140 Z" fill="#C8DEFF" opacity="0.55" />
        <path d="M0,0 L900,0 L900,80 C650,200 380,30 180,120 C80,165 20,120 0,100 Z" fill="#A8CCFA" opacity="0.35" />
        {/* Bottom wave */}
        <path d="M0,700 L900,700 L900,560 C700,480 500,600 280,520 C120,460 30,520 0,540 Z" fill="#C8DEFF" opacity="0.5" />
        <path d="M0,700 L900,700 L900,610 C680,540 460,640 240,570 C100,525 20,570 0,585 Z" fill="#A8CCFA" opacity="0.35" />
      </svg>

      {/* ── Government building — right 58%, bleeds to edge, fades on left ── */}
      <motion.div
        initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
        className="pointer-events-none absolute bottom-0 right-0 top-0 w-[58%]"
      >
        <img
          src="/fort.png"
          alt="Fort Scene"
          className="h-full w-full object-cover object-left-top"
          style={{
            maskImage: "linear-gradient(to right, transparent 0%, rgba(0,0,0,0.4) 15%, black 30%)",
            WebkitMaskImage: "linear-gradient(to right, transparent 0%, rgba(0,0,0,0.4) 15%, black 30%)",
          }}
        />
      </motion.div>

      {/* ── Foreground content: 3-row flex ── */}
      <div className="relative z-10 flex w-full flex-col justify-between px-10 py-10" style={{ minHeight: "100dvh" }}>

        {/* TOP — govt brand left, tagline right */}
        <div className="flex items-start justify-between">
          <div className="flex flex-col items-start gap-1">
            <div className="flex items-center gap-2">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#0B2A5B]">Government of India</p>
                <p className="text-[11px] font-semibold text-[#5A6E8C] tracking-wide">MoSPI</p>
              </div>
            </div>
          </div>

          {/* Top-right italic tagline */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1, duration: 0.7 }}
            className="text-right">
            <p className="text-[11.5px] font-medium italic leading-[1.8] text-[#0B2A5B]/70">
              Right Learning.<br />Real Progress.<br />Stronger Officers.<br />Data-Driven Nation.
            </p>
            <span className="mt-1.5 block h-0.5 w-10 rounded-full bg-[#1464E8] ml-auto" />
          </motion.div>
        </div>

        {/* CENTER — NEXUS hero text + loading bar */}
        <motion.div
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
          className="max-w-[45%]"
        >
          <p className="text-[10.5px] font-bold uppercase tracking-[0.22em] text-[#1464E8]">
            Adaptive Competency &amp; Career Learning Loop
          </p>
          <h1 className="mt-1 font-black leading-none text-[#0B2A5B]"
            style={{ fontSize: "clamp(58px, 7vw, 88px)", letterSpacing: "-0.025em" }}>
            NEX<span className="text-[#1464E8]">U</span>S
          </h1>
          <p className="mt-2.5 text-[16px] font-bold leading-snug text-[#0B2A5B]/85">
            Adaptive Competency &amp;<br />Career Learning Loop
          </p>
          <p className="mt-1.5 text-[13.5px] leading-relaxed text-[#5A6E8C]">
            Empowering Statistical Officers<br />for a Data-Ready India
          </p>

          {/* Animated progress bar */}
          <div className="mt-6 flex items-center gap-3">
            <div className="relative h-[6px] w-52 overflow-hidden rounded-full bg-[#EAF4FF]">
              <motion.div
                className="absolute inset-y-0 left-0 rounded-full bg-[#1464E8]"
                initial={{ width: "0%" }} animate={{ width: "100%" }}
                transition={{ duration: 2.6, ease: "easeInOut", delay: 0.6 }}
              />
            </div>
            <span className="text-[11.5px] font-medium text-[#5A6E8C]">Loading…</span>
          </div>
        </motion.div>

        {/* BOTTOM — 4-column feature pillar row */}
        <motion.div
          initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4, ease: "easeOut" }}
          className="flex items-end gap-8"
        >
          {PILLARS.map(({ Icon, label }) => (
            <div key={label} className="flex flex-col items-center gap-2 text-center">
              <span className="grid h-11 w-11 place-items-center rounded-xl shadow-md"
                style={{ background: "#1464E8", boxShadow: "0 4px 14px rgb(20 100 232 / .28)" }}>
                <Icon className="h-5 w-5 text-white" aria-hidden="true" />
              </span>
              <span className="whitespace-pre-line text-[11.5px] font-semibold leading-tight text-[#0B2A5B]">{label}</span>
            </div>
          ))}
        </motion.div>

      </div>
    </div>
  );
}

export function AuthShell({ children }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,1.18fr)_minmax(0,1fr)]">
      <Showcase />
      {/* Right: login form panel */}
      <main id="main" className="flex items-center justify-center bg-white px-6 py-10 sm:px-12">
        <div className="w-full max-w-[400px]">
          {/* Mobile-only branding */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <Logo className="text-[#0B2A5B]" />
          </div>
          {/* Govt stripe - desktop top of form */}
          <div className="mb-6 hidden lg:block">
            <div className="flex items-center gap-2 mb-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-widest text-[#0B2A5B]">Government of India · MoSPI</p>
              </div>
            </div>
            <div className="govt-header-stripe rounded-full" />
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}

// ─── Sign in / Sign up ────────────────────────────────────────────────────────

const EMAIL = /^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$/;
const USERNAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{2,31}$/;

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

export function AuthScreen({ initial = "login" }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [mode, setMode] = useState(initial);
  const [form, setForm] = useState({ username: "", email: "", password: "", confirm: "", agree: false });
  /** @type {any} */
  const initialErrors = {};
  const [errors, setErrors] = useState(initialErrors);
  const [serverError, setServerError] = useState("");
  const [pending, setPending] = useState(false);
  const first = useRef(null);
  const isLogin = mode === "login";

  useEffect(() => { (async () => { const s = await fetchSession(); if (s.authenticated) router.replace("/dashboard"); })(); }, [router]);
  useEffect(() => { document.title = isLogin ? "Sign in · Nexus" : "Create your account · Nexus"; first.current?.focus(); }, [isLogin]);

  const set = (name, value) => { setForm((f) => ({ ...f, [name]: value })); setErrors((e) => ({ ...e, [name]: undefined })); };
  const switchTo = (next) => { setServerError(""); setErrors({}); setMode(next); window.history.replaceState(null, "", next === "register" ? "/register" : "/login"); };

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
      if (!isLogin) toast.success("Welcome to Nexus", { description: `We sent a code to ${form.email.trim()}. Enter it under Account to verify your address.`, duration: 9000 });
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
          <h1 className="font-display text-[28px] font-semibold leading-tight">{isLogin ? "Welcome back" : "Create your account"}</h1>
          <p className="mt-1 text-[15px] text-muted">{isLogin ? "Sign in to pick up where you left off." : "It takes less than a minute."}</p>
          <form className="mt-7 space-y-4" onSubmit={submit} noValidate>
            <FormError>{serverError}</FormError>
            {!isLogin && <AuthField label="Username" icon={UserRound} placeholder="e.g. priya.k" autoComplete="nickname" inputRef={first} name="username" value={form.username}
              onChange={(e) => set("username", e.target.value)} error={errors.username} maxLength={32} spellCheck={false} autoCapitalize="none" hint="Shown in the top bar." />}
            <AuthField label={isLogin ? "Email or username" : "Email address"} icon={Mail} placeholder="you@example.com" type={isLogin ? "text" : "email"} inputMode="email" name="email"
              autoComplete={isLogin ? "username" : "email"} inputRef={isLogin ? first : undefined} value={form.email} onChange={(e) => set("email", e.target.value)} error={errors.email}
              maxLength={254} spellCheck={false} autoCapitalize="none" hint={isLogin ? undefined : "You sign in and reset your password with this."} />
            <PasswordField label="Password" name="password" placeholder={isLogin ? "Your password" : "At least 8 characters"} autoComplete={isLogin ? "current-password" : "new-password"}
              value={form.password} onChange={(v) => set("password", v)} error={errors.password} showStrength={!isLogin} />
            {!isLogin && <PasswordField label="Confirm password" name="confirm" placeholder="Type it again" autoComplete="new-password" value={form.confirm} onChange={(v) => set("confirm", v)} error={errors.confirm} />}
            {isLogin ? (
              <div className="flex justify-end"><Link href="/forgot-password" className="text-[13.5px] font-semibold">Forgot password?</Link></div>
            ) : (
              <div>
                <label className="flex cursor-pointer items-start gap-2.5 text-[13.5px] text-muted">
                  <Checkbox checked={form.agree} onCheckedChange={(v) => set("agree", !!v)} aria-invalid={!!errors.agree} className="mt-0.5" />
                  <span>My study materials are stored on this server and are sent to a cloud model only if I allow it under Account.</span>
                </label>
                {errors.agree && <p role="alert" className="mt-1.5 text-[13px] font-medium text-weak">{errors.agree}</p>}
              </div>
            )}
            <Button type="submit" size="lg" className="w-full" loading={pending}>{isLogin ? "Sign in" : "Create account"}{!pending && <ArrowRight className="h-4 w-4" />}</Button>
          </form>
          <p className="mt-6 text-center text-[14px] text-muted">
            {isLogin ? "New to Nexus?" : "Already have an account?"}{" "}
            <button type="button" className="font-semibold text-link hover:underline" onClick={() => switchTo(isLogin ? "register" : "login")}>{isLogin ? "Create an account" : "Sign in"}</button>
          </p>
        </motion.div>
      </AnimatePresence>
    </AuthShell>
  );
}
