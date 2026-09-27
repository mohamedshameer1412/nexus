"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { motion } from "framer-motion";
import {
  BarChart2, Bell, BookOpen, BrainCircuit, Briefcase, ChevronRight,
  ClipboardList, GraduationCap, Home, LayoutDashboard, LogOut, Menu,
  PanelLeftClose, PanelLeftOpen, Route, Search, Settings, Shield,
  TrendingUp, User, WifiOff, X,
} from "lucide-react";
import { CommandPalette } from "@/components/nexus/command-palette";
import { JobWatcher } from "@/components/nexus/job-watcher";
import { Logo } from "@/components/nexus/common";
import { SECTIONS } from "@/components/nexus/nav-data";
import { api, clearOfflineData, fetchSession } from "@/lib/api";
import { getSession, getSubjects, keys } from "@/lib/queries";
import { cn } from "@/lib/utils";
import {
  Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger, Kbd, Skeleton, Tooltip, TooltipProvider,
} from "@/components/ui/primitives";

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

const DESKTOP = "(min-width: 1024px)";
function useDesktop() {
  return useSyncExternalStore(
    (cb) => { const m = window.matchMedia(DESKTOP); m.addEventListener("change", cb); return () => m.removeEventListener("change", cb); },
    () => window.matchMedia(DESKTOP).matches,
    () => true,
  );
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

// ------------------------------------------------------------------------------------------------ sidebar

function NavItem({ href, Icon, label, active, compact, sub = false, onNavigate = undefined }) {
  const link = (
    <Link href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex items-center gap-3 rounded-lg text-[14px] font-medium no-underline transition-colors",
        compact ? "mx-auto h-10 w-10 justify-center" : sub ? "h-9 pl-10 pr-3 text-[13.5px]" : "h-10 px-3",
        active ? "bg-white text-brand-deep shadow-[0_2px_10px_rgb(0_40_80/.18)]" : "text-white/90 hover:bg-white/15 hover:text-white",
      )}>
      <Icon className={cn("shrink-0", sub ? "h-4 w-4" : "h-[18px] w-[18px]")} aria-hidden="true" />
      <span className={cn("truncate", compact && "sr-only")}>{label}</span>
    </Link>
  );
  return compact ? <Tooltip content={label} side="right">{link}</Tooltip> : link;
}

function Group({ label, compact, children }) {
  return (
    <div>
      {!compact && <p className="px-3 pb-1.5 text-[12px] font-semibold text-white/70">{label}</p>}
      <ul className="space-y-0.5">{children}</ul>
    </div>
  );
}

// NEXUS-specific navigation sections
const NEXUS_NAV = [
  { href: "/dashboard",  Icon: LayoutDashboard, label: "Dashboard" },
  { href: "/subjects",   Icon: BookOpen,         label: "Learn" },
  { href: "/assess",     Icon: Shield,           label: "Assess" },
  { href: "/analytics",  Icon: TrendingUp,       label: "Progress" },
  { href: "/career",     Icon: Route,            label: "Career Path" },
  { href: "/ai-tutor",   Icon: BrainCircuit,     label: "AI Tutor" },
  { href: "/search",     Icon: ClipboardList,    label: "Reports" },
  { href: "/account",    Icon: Settings,         label: "Settings" },
];

function NavLinks({ compact = false, onNavigate = undefined }) {
  const pathname = usePathname();
  const is = (href) => pathname === href || pathname.startsWith(`${href}/`);
  return (
    <nav aria-label="Main" className="flex min-h-full flex-col px-3 py-5">
      {/* Logo / brand in mobile drawer */}
      <div className="mb-5 flex items-center gap-2.5 px-1">
        <img src="/mospi-logo.png" alt="MoSPI" className="h-7 w-7 object-contain" />
        {!compact && (
          <div>
            <p className="text-[15px] font-black text-white tracking-tight">NEXUS</p>
            <p className="text-[9.5px] font-semibold uppercase tracking-widest text-white/60">MoSPI · GoI</p>
          </div>
        )}
      </div>

      {!compact && <p className="px-1 pb-2 text-[11px] font-bold uppercase tracking-widest text-white/50">Navigation</p>}

      <ul className="space-y-1">
        {NEXUS_NAV.map(({ href, Icon, label }) => (
          <li key={href}>
            <NavItem href={href} Icon={Icon} label={label} active={is(href)} compact={compact} onNavigate={onNavigate} />
          </li>
        ))}
      </ul>

      {/* Government building thumbnail */}
      {!compact && (
        <div className="mx-1 mt-auto overflow-hidden rounded-xl border border-white/10">
          <img src="/government-building.png" alt="" aria-hidden="true"
            className="w-full object-cover object-top opacity-75 saturate-75"
            style={{ maxHeight: "120px" }} />
        </div>
      )}
      {compact && <div className="mt-auto" />}
    </nav>
  );
}

// ─── Mobile bottom navigation ─────────────────────────────────────────────────
const MOBILE_NAV = [
  { href: "/dashboard", Icon: Home,         label: "Home" },
  { href: "/subjects",  Icon: BookOpen,      label: "Learn" },
  { href: "/assess",    Icon: Shield,        label: "Assess" },
  { href: "/analytics", Icon: TrendingUp,    label: "Progress" },
  { href: "/account",   Icon: User,          label: "Profile" },
];

function MobileBottomNav() {
  const pathname = usePathname();
  const is = (href) => pathname === href || pathname.startsWith(`${href}/`);
  return (
    <nav aria-label="Mobile navigation" className="bottom-nav lg:hidden">
      {MOBILE_NAV.map(({ href, Icon, label }) => (
        <Link key={href} href={href} className={`bottom-nav-item ${is(href) ? "active" : ""}`}>
          <Icon />
          {label}
        </Link>
      ))}
    </nav>
  );
}

// ------------------------------------------------------------------------------------------------ shell

/** Signed-in frame: the blue navbar and sidebar, the command palette and the job watcher. Sends signed-out visitors to /login. */
export function AppShell({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const desktop = useDesktop();
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [palette, setPalette] = useState(false);
  const online = useOnline();
  const logout = useLogout();
  const { data: session, isPending } = useQuery({ queryKey: keys.session, queryFn: getSession, staleTime: 60_000 });

  useEffect(() => { try { setCollapsed(localStorage.getItem("nexus.sidebar") === "collapsed"); } catch {} }, []);
  useEffect(() => {
    const onKey = (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((o) => !o); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => setDrawer(false), [pathname]);
  useEffect(() => { if (session && !session.authenticated) router.replace("/login"); }, [session, router]);

  const toggle = () => {
    if (!desktop) return setDrawer((o) => !o);
    setCollapsed((c) => { try { localStorage.setItem("nexus.sidebar", c ? "expanded" : "collapsed"); } catch {} return !c; });
  };

  if (isPending || !session?.authenticated) {
    return (
      <div className="min-h-dvh" aria-busy="true">
        <div className="h-14 bg-brand" />
        <div className="mx-auto max-w-6xl space-y-4 p-6"><Skeleton className="h-9 w-56" /><Skeleton className="h-28 w-full" /><Skeleton className="h-64 w-full" /></div>
      </div>
    );
  }
  const u = session.user;
  return (
    <TooltipProvider>
      <div className="min-h-dvh">
        <header className="sticky top-0 z-30 text-white shadow-[0_2px_20px_-4px_rgb(0_30_80/.4)]"
          style={{ background: "linear-gradient(95deg, #0B2A5B 0%, #1464E8 100%)" }}>
          <div className="flex h-14 items-center gap-2 px-3 sm:px-4">
            {/* Sidebar toggle */}
            <button id="menu-toggle" onClick={toggle} className="grid h-9 w-9 place-items-center rounded-lg text-white hover:bg-white/15 transition-colors"
              aria-expanded={desktop ? !collapsed : drawer} aria-controls="app-sidebar"
              aria-label={desktop ? (collapsed ? "Expand sidebar" : "Collapse sidebar") : "Open menu"}>
              {desktop ? (collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />) : <Menu className="h-5 w-5" />}
            </button>

            {/* Brand */}
            <Link href="/dashboard" aria-label="NEXUS Dashboard" className="flex items-center gap-2 no-underline">
              <img src="/mospi-logo.png" alt="MoSPI" className="h-7 w-7 object-contain hidden lg:block" />
              <span className="text-[17px] font-black tracking-tight text-white">NEXUS</span>
            </Link>

            {/* Search — desktop */}
            <button type="button" onClick={() => setPalette(true)} aria-keyshortcuts="Control+K"
              className="ml-3 hidden h-9 w-full max-w-sm items-center gap-2 rounded-lg bg-white/12 px-3 text-left text-[13.5px] text-white/80 ring-1 ring-inset ring-white/20 transition-colors hover:bg-white/20 md:flex">
              <Search className="h-4 w-4" aria-hidden="true" />
              <span className="flex-1">Search or jump to…</span>
              <Kbd className="border-white/30 bg-white/10 text-white/85">Ctrl K</Kbd>
            </button>

            <div className="ml-auto flex items-center gap-1.5">
              {/* Mobile search */}
              <button onClick={() => setPalette(true)} className="grid h-9 w-9 place-items-center rounded-lg text-white hover:bg-white/15 md:hidden" aria-label="Search">
                <Search className="h-5 w-5" />
              </button>
              {/* Notifications */}
              <button className="relative grid h-9 w-9 place-items-center rounded-lg text-white hover:bg-white/15 transition-colors" aria-label="Notifications">
                <Bell className="h-5 w-5" />
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#F2A900] border border-white" aria-hidden="true" />
              </button>
              {/* Profile */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button type="button"
                    className="flex h-9 items-center gap-2 rounded-lg px-2 text-white hover:bg-white/15 transition-colors"
                    aria-label={`Account menu for ${u.username}`}>
                    <span className="grid h-8 w-8 place-items-center rounded-full bg-white text-[13px] font-black uppercase text-[#0B2A5B]" aria-hidden="true">
                      {u.username.slice(0, 1)}
                    </span>
                    <span className="hidden max-w-[140px] truncate text-[13.5px] font-semibold sm:block">{u.username}</span>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <div className="px-2.5 py-2">
                    <p className="break-anywhere text-sm font-bold">{u.username}</p>
                    {u.email && <p className="break-anywhere text-xs text-muted">{u.email}</p>}
                    <p className="text-[11px] text-muted mt-0.5">Statistical Officer (Grade-II)</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={() => router.push("/account")}><User />Account</DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => router.push("/analytics")}><BarChart2 />Progress</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={logout}><LogOut />Log out</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>
        <CommandPalette open={palette} onOpenChange={setPalette} />
        <JobWatcher />
        {/* Desktop sidebar */}
        {desktop ? (
          <aside id="app-sidebar" aria-label="Sidebar"
            className={cn("nx-scroll fixed bottom-0 left-0 top-14 z-20 overflow-y-auto text-white transition-[width] duration-200",
              collapsed ? "w-[64px]" : "w-[220px]")}
            style={{ background: "linear-gradient(180deg, #0B2A5B 0%, #0D3470 60%, #0F3F85 100%)" }}>
            <NavLinks compact={collapsed} />
          </aside>
        ) : (
          /* Mobile drawer */
          <DialogPrimitive.Root open={drawer} onOpenChange={setDrawer}>
            <DialogPrimitive.Portal>
              <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-[#0B2A5B]/50 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
              <DialogPrimitive.Content id="app-sidebar"
                onCloseAutoFocus={(e) => { e.preventDefault(); document.getElementById("menu-toggle")?.focus(); }}
                className="nx-scroll fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col overflow-y-auto text-white shadow-pop focus:outline-none data-[state=open]:animate-in data-[state=open]:slide-in-from-left"
                style={{ background: "linear-gradient(180deg, #0B2A5B 0%, #0D3470 60%, #0F3F85 100%)" }}>
                <div className="flex h-14 shrink-0 items-center justify-between border-b border-white/15 px-4">
                  <DialogPrimitive.Title asChild>
                    <span className="text-[16px] font-black text-white tracking-tight">NEXUS</span>
                  </DialogPrimitive.Title>
                  <DialogPrimitive.Close
                    className="grid h-9 w-9 place-items-center rounded-lg text-white hover:bg-white/15"
                    aria-label="Close menu">
                    <X className="h-5 w-5" />
                  </DialogPrimitive.Close>
                </div>
                <DialogPrimitive.Description className="sr-only">Site navigation</DialogPrimitive.Description>
                <NavLinks onNavigate={() => setDrawer(false)} />
              </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
          </DialogPrimitive.Root>
        )}

        {/* Page content area */}
        <div className={cn("transition-[padding] duration-200", desktop && (collapsed ? "pl-[64px]" : "pl-[220px]"))}>
          {!online && (
            <p role="status" className="flex items-center justify-center gap-2 bg-mid-bg px-4 py-2 text-center text-sm font-semibold text-mid">
              <WifiOff className="h-4 w-4" />You are offline. Pages you opened before still work; asking, quizzes and saving need a connection.
            </p>
          )}
          <main id="main" className="mx-auto max-w-[1260px] px-4 pb-24 pt-6 sm:px-6 lg:px-8 lg:pb-10">{children}</main>
        </div>

        {/* Mobile bottom navigation */}
        <MobileBottomNav />
      </div>
    </TooltipProvider>
  );
}
