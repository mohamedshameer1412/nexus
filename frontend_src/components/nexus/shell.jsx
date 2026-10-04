"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  ArrowLeft, Bell, BookOpen, Bot, ChartNoAxesColumn, ClipboardCheck, FileText, GraduationCap, Home,
  LogOut, Map, Search, Settings, User, WifiOff, X,
} from "lucide-react";
import { CommandPalette } from "@/components/nexus/command-palette";
import { JobWatcher } from "@/components/nexus/job-watcher";
import { Asset, Initials } from "@/components/nexus/kit";
import { api, clearOfflineData, fetchSession } from "@/lib/api";
import { getSession, keys } from "@/lib/queries";
import { OFFICER } from "@/lib/nexus-data";
import { cn } from "@/lib/utils";
import { Skeleton, TooltipProvider } from "@/components/ui/primitives";

export function useLogout() {
  const router = useRouter();
  const qc = useQueryClient();
  return async () => {
    try { await api("/logout", { method: "POST" }); } catch {}
    qc.clear();
    clearOfflineData();
    await fetchSession();
    router.replace("/login");
  };
}

function useOnline() {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const on = () => setOnline(navigator.onLine);
    on();
    window.addEventListener("online", on);
    window.addEventListener("offline", on);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", on); };
  }, []);
  return online;
}

// The mockup's sidebar. "Reports" opens the subject workspaces, where each subject has its report.
const NAV = [
  { href: "/dashboard", Icon: Home, label: "Dashboard" },
  { href: "/learn", Icon: BookOpen, label: "Learn" },
  { href: "/assess", Icon: ClipboardCheck, label: "Assess" },
  { href: "/competency", Icon: ChartNoAxesColumn, label: "Progress" },
  { href: "/career", Icon: Map, label: "Career Path" },
  { href: "/ai-tutor", Icon: Bot, label: "AI Tutor" },
  { href: "/subjects", Icon: FileText, label: "Reports" },
];

const MOBILE_NAV = [
  { href: "/dashboard", Icon: Home, label: "Home" },
  { href: "/learn", Icon: BookOpen, label: "Learn" },
  { href: "/assess", Icon: ClipboardCheck, label: "Assess" },
  { href: "/competency", Icon: ChartNoAxesColumn, label: "Progress" },
  { href: "/profile", Icon: User, label: "Profile" },
];

// Mobile header titles, longest prefix first.
const TITLES = [
  ["/diagnosis/retest", "Re-test Result"], ["/diagnosis", "Root-cause Diagnosis"], ["/learn/", "Course Details"], ["/learn", "My Learning Path"], ["/competency", "Competency Profile"],
  ["/assess", "Assessment"], ["/ai-tutor", "NEXUS AI Tutor"], ["/profile", "Profile"], ["/career", "Career Path"],
  ["/subjects", "Subjects"], ["/account", "Settings"], ["/search", "Search"], ["/saved", "Saved"], ["/faculty", "Faculty"],
];

function useIs() {
  const pathname = usePathname();
  return (href) => pathname === href || pathname.startsWith(`${href}/`);
}

function NavItem({ href, Icon, label, active, onNavigate = undefined }) {
  return (
    <Link href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
      className={cn("flex h-11 items-center gap-3 rounded-xl px-3.5 text-[14px] font-medium no-underline transition-colors",
        active ? "bg-[#E3EEFF] font-semibold text-[#1464E8]" : "text-[#33476A] hover:bg-[#F0F5FD] hover:text-[#0B2A5B]")}>
      <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
      <span className="truncate">{label}</span>
    </Link>
  );
}

function Sidebar({ onNavigate = undefined }) {
  const is = useIs();
  const { data: session } = useQuery({ queryKey: keys.session, queryFn: getSession, staleTime: 60_000 });
  const faculty = session?.user?.role === "faculty";
  return (
    <nav aria-label="Main" className="flex h-full flex-col px-4 pb-5 pt-6">
      <Link href="/dashboard" onClick={onNavigate} aria-label="NEXUS home" className="mb-7 block px-2">
        <Asset name="nexus-wordmark" alt="NEXUS" className="h-7 w-auto" />
      </Link>
      <ul className="space-y-1">
        {NAV.map((n) => <li key={n.href}><NavItem {...n} active={is(n.href)} onNavigate={onNavigate} /></li>)}
        {faculty && <li><NavItem href="/faculty" Icon={GraduationCap} label="Faculty" active={is("/faculty")} onNavigate={onNavigate} /></li>}
      </ul>
      <div className="mt-auto space-y-3 pt-6">
        <NavItem href="/account" Icon={Settings} label="Settings" active={is("/account")} onNavigate={onNavigate} />
        <Link href="/profile" onClick={onNavigate} className="flex items-center gap-3 rounded-xl px-2 py-2 no-underline hover:bg-[#F0F5FD]">
          <Initials name={OFFICER.name} className="h-10 w-10 text-[14px]" />
          <span className="min-w-0">
            <span className="block truncate text-[14px] font-bold text-[#0B2A5B]">{OFFICER.name}</span>
            <span className="block truncate text-[12px] text-[#5A6E8C]">{faculty ? "Faculty, NSSTA" : "Statistical Officer"}</span>
          </span>
        </Link>
      </div>
    </nav>
  );
}

function IconButton({ label, onClick = undefined, dot = false, children, className = "" }) {
  return (
    <button type="button" onClick={onClick} aria-label={label}
      className={cn("relative grid h-10 w-10 place-items-center rounded-full text-[#0B2A5B] transition-colors hover:bg-[#E8F0FC]", className)}>
      {children}
      {dot && <span className="absolute right-2 top-2 h-2 w-2 rounded-full border border-white bg-[#E5484D]" aria-hidden="true" />}
    </button>
  );
}

function MobileHeader({ onMenu }) {
  const pathname = usePathname();
  const router = useRouter();
  const home = pathname === "/dashboard";
  const title = TITLES.find(([p]) => pathname.startsWith(p))?.[1] ?? "NEXUS";
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-[#E3ECF8] bg-white/90 px-3 backdrop-blur lg:hidden">
      {home ? (
        <Asset name="nexus-wordmark" alt="NEXUS" className="ml-1 h-6 w-auto" />
      ) : (
        <>
          <IconButton label="Back" onClick={() => (history.length > 1 ? router.back() : router.push("/dashboard"))}><ArrowLeft className="h-5 w-5" /></IconButton>
          <h1 className="truncate text-[17px] font-bold text-[#0B2A5B]">{title}</h1>
        </>
      )}
      <div className="ml-auto flex items-center gap-1">
        {!home && <IconButton label="Notifications" dot><Bell className="h-5 w-5" /></IconButton>}
        <button type="button" onClick={onMenu} aria-label="Open menu" className="relative rounded-full">
          <Initials name={OFFICER.name} className="h-9 w-9 text-[13px]" />
          {home && <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-[#E5484D]" aria-hidden="true" />}
        </button>
      </div>
    </header>
  );
}

function MobileBottomNav() {
  const is = useIs();
  const pathname = usePathname();
  // A subject workspace has its own bottom bar of sections (Materials, Ask, Practice, ...) on phones; two fixed bars would overlap.
  if (/^\/subjects\/[^/]+/.test(pathname)) return null;
  return (
    <nav aria-label="Mobile navigation" className="fixed inset-x-0 bottom-0 z-30 flex justify-around border-t border-[#E3ECF8] bg-white pb-[max(env(safe-area-inset-bottom),6px)] pt-1.5 shadow-[0_-4px_20px_rgb(11_42_91/.06)] lg:hidden">
      {MOBILE_NAV.map(({ href, Icon, label }) => (
        <Link key={href} href={href} aria-current={is(href) ? "page" : undefined}
          className={cn("flex min-w-[60px] flex-col items-center gap-0.5 rounded-lg px-2 py-1 text-[11px] font-semibold no-underline",
            is(href) ? "text-[#1464E8]" : "text-[#5A6E8C]")}>
          <Icon className="h-[22px] w-[22px]" aria-hidden="true" fill={is(href) ? "currentColor" : "none"} fillOpacity={0.15} />
          {label}
        </Link>
      ))}
    </nav>
  );
}

/** Signed-in frame: white sidebar and top bar on desktop, titled header and bottom tabs on mobile. Sends signed-out visitors to /login. */
export function AppShell({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [drawer, setDrawer] = useState(false);
  const [palette, setPalette] = useState(false);
  const online = useOnline();
  const logout = useLogout();
  const { data: session, isPending } = useQuery({ queryKey: keys.session, queryFn: getSession, staleTime: 60_000 });

  useEffect(() => {
    const onKey = (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((o) => !o); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => setDrawer(false), [pathname]);
  useEffect(() => { if (session && !session.authenticated) router.replace("/login"); }, [session, router]);

  if (isPending || !session?.authenticated) {
    return (
      <div className="min-h-dvh bg-[#F3F7FD] lg:pl-[232px]" aria-busy="true">
        <div className="mx-auto max-w-6xl space-y-4 p-6"><Skeleton className="h-9 w-56" /><Skeleton className="h-28 w-full" /><Skeleton className="h-64 w-full" /></div>
      </div>
    );
  }
  return (
    <TooltipProvider>
      <div className="min-h-dvh bg-[#F3F7FD]">
        <aside id="app-sidebar" aria-label="Sidebar"
          className="nx-scroll-light fixed inset-y-0 left-0 z-20 hidden w-[232px] overflow-y-auto border-r border-[#E3ECF8] bg-gradient-to-b from-white to-[#F6F9FE] lg:block">
          <Sidebar />
        </aside>

        <MobileHeader onMenu={() => setDrawer(true)} />
        <DialogPrimitive.Root open={drawer} onOpenChange={setDrawer}>
          <DialogPrimitive.Portal>
            <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-[#0B2A5B]/40 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
            <DialogPrimitive.Content className="fixed inset-y-0 right-0 z-50 w-72 max-w-[85vw] overflow-y-auto bg-white shadow-pop focus:outline-none data-[state=open]:animate-in data-[state=open]:slide-in-from-right">
              <DialogPrimitive.Title className="sr-only">Menu</DialogPrimitive.Title>
              <DialogPrimitive.Description className="sr-only">Site navigation</DialogPrimitive.Description>
              <DialogPrimitive.Close className="absolute right-3 top-4 grid h-9 w-9 place-items-center rounded-full text-[#0B2A5B] hover:bg-[#E8F0FC]" aria-label="Close menu"><X className="h-5 w-5" /></DialogPrimitive.Close>
              <Sidebar onNavigate={() => setDrawer(false)} />
              <div className="px-4 pb-6">
                <button type="button" onClick={logout} className="flex h-11 w-full items-center gap-3 rounded-xl px-3.5 text-[14px] font-medium text-[#D64545] hover:bg-[#FDECEC]"><LogOut className="h-[18px] w-[18px]" />Log out</button>
              </div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        </DialogPrimitive.Root>

        <CommandPalette open={palette} onOpenChange={setPalette} />
        <JobWatcher />

        <div className="lg:pl-[232px]">
          <div className="hidden h-[72px] items-center justify-end gap-2 px-8 lg:flex">
            {pathname === "/dashboard" && (
              <button type="button" onClick={() => setPalette(true)} aria-keyshortcuts="Control+K"
                className="mr-auto ml-[22%] flex h-11 w-full max-w-md items-center gap-2.5 rounded-xl border border-[#E3ECF8] bg-white px-4 text-left text-[14px] text-[#8193B0] shadow-[0_2px_10px_rgb(20_100_232/.05)] hover:border-[#C8DAF5]">
                <Search className="h-4 w-4" aria-hidden="true" />Search courses, skills or topics…
              </button>
            )}
            <IconButton label="Search" onClick={() => setPalette(true)} className={pathname === "/dashboard" ? "hidden" : ""}><Search className="h-5 w-5" /></IconButton>
            <IconButton label="Notifications" dot><Bell className="h-5 w-5" /></IconButton>
            <Link href="/profile" aria-label="Profile" className="ml-1 rounded-full"><Initials name={OFFICER.name} className="h-10 w-10 text-[14px]" /></Link>
          </div>
          {!online && (
            <p role="status" className="flex items-center justify-center gap-2 bg-mid-bg px-4 py-2 text-center text-sm font-semibold text-mid">
              <WifiOff className="h-4 w-4" />You are offline. Pages you opened before still work; asking, quizzes and saving need a connection.
            </p>
          )}
          <main id="main" className="mx-auto max-w-[1240px] px-4 pb-28 pt-4 sm:px-6 lg:px-8 lg:pb-10 lg:pt-0">{children}</main>
        </div>

        <MobileBottomNav />
      </div>
    </TooltipProvider>
  );
}

