"use client";
// Small building blocks shared by the NEXUS mockup screens.
import { useId } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { motion } from "framer-motion";
import { CheckCircle2, CircleDashed, Clock3 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Panel({ className = "", children, ...rest }) {
  return <section className={cn("rounded-2xl border border-[#E3ECF8] bg-white p-5 shadow-[0_2px_14px_rgb(20_100_232/.06)]", className)} {...rest}>{children}</section>;
}

export function PanelTitle({ children, className = "", action = null }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className={cn("text-[16px] font-bold text-[#0B2A5B]", className)}>{children}</h2>
      {action}
    </div>
  );
}

/** Donut ring with the value in the middle, as on the dashboard and competency cards. */
export function Ring({ value, size = 96, stroke = 12, label = true, className = "" }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const grad = `ring${useId().replace(/:/g, "")}`;
  return (
    <div className={cn("relative shrink-0", className)} style={{ width: size, height: size }} role="img" aria-label={`${value}%`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#DCE9FB" strokeWidth={stroke} />
        <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={`url(#${grad})`} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - value / 100) }} transition={{ duration: 1.1, ease: "easeOut" }} />
        <defs><linearGradient id={grad} x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#3B8BFF" /><stop offset="100%" stopColor="#1464E8" /></linearGradient></defs>
      </svg>
      {label && <span className="absolute inset-0 grid place-items-center font-extrabold text-[#0B2A5B]" style={{ fontSize: size * 0.22 }}>{value}%</span>}
    </div>
  );
}

export function Bar({ value, tone = "blue", className = "", height = 8 }) {
  const fill = { blue: "linear-gradient(90deg,#3B8BFF,#1464E8)", green: "linear-gradient(90deg,#34C38F,#16A36A)" }[tone];
  return (
    <div className={cn("w-full overflow-hidden rounded-full bg-[#E4EEFB]", className)} style={{ height }}>
      <motion.div className="h-full rounded-full" style={{ background: fill }} initial={{ width: 0 }} animate={{ width: `${value}%` }} transition={{ duration: 0.9, ease: "easeOut" }} />
    </div>
  );
}

const BADGE = {
  igot: ["iGOT", "bg-[#FF9F1C] text-white"],
  tpac: ["TPAC", "bg-[#16A36A] text-white"],
  internal: ["iGOT", "bg-[#7B3FE4] text-white"],
};
export function SourceBadge({ source }) {
  const [label, cls] = BADGE[source] ?? [source, "bg-[#1464E8] text-white"];
  return <span className={cn("inline-flex h-6 items-center rounded-md px-2 text-[11px] font-extrabold tracking-wide", cls)}>{label}</span>;
}

const STATUS = {
  completed: ["Completed", "bg-[#E3F7EE] text-[#16A36A]", CheckCircle2],
  "in-progress": ["In Progress", "bg-[#E6F0FF] text-[#1464E8]", Clock3],
  "not-started": ["Not Started", "bg-[#EEF2F7] text-[#5A6E8C]", CircleDashed],
};
export function StatusPill({ status, icon = false }) {
  const [label, cls, Icon] = STATUS[status];
  return <span className={cn("inline-flex h-7 items-center gap-1 rounded-md px-2.5 text-[12px] font-semibold", cls)}>{icon && <Icon className="h-3.5 w-3.5" aria-hidden="true" />}{label}</span>;
}

/**
 * Underlined tab strip, on Radix Tabs (arrow-key roving focus and ARIA panels come from the library;
 * only the visual — an underline instead of a pill — is custom). `tabs` is a list of labels;
 * the caller renders the panel for `value` itself, so there's no `Tabs.Content` here.
 */
export function UnderlineTabs({ tabs, value, onChange, className = "" }) {
  return (
    <TabsPrimitive.Root value={value} onValueChange={onChange}>
      <TabsPrimitive.List className={cn("nx-noscroll flex gap-6 overflow-x-auto border-b border-[#E3ECF8]", className)}>
        {tabs.map((t) => (
          <TabsPrimitive.Trigger key={t} value={t}
            className="relative shrink-0 pb-3 pt-1 text-[14px] font-semibold text-[#5A6E8C] outline-none transition-colors hover:text-[#0B2A5B] focus-visible:text-[#0B2A5B] data-[state=active]:text-[#1464E8]">
            {t}
            {value === t && <motion.span layoutId={`tab-${tabs.join()}`} className="absolute inset-x-0 -bottom-px h-[3px] rounded-full bg-[#1464E8]" />}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
    </TabsPrimitive.Root>
  );
}

/** An image cropped from NEXUS_UI_Assets (public/assets/generated). */
export function Asset({ name, alt = "", className = "" }) {
  return <img src={`/assets/generated/${name}.png`} alt={alt} aria-hidden={alt ? undefined : true} className={cn("select-none object-contain", className)} draggable={false} />;
}

export function Initials({ name = "A. Sharma", className = "" }) {
  const text = name.replace(/[^A-Za-z ]/g, "").split(" ").filter(Boolean).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  return <span className={cn("grid shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#7C9CFF] to-[#5B6CF0] font-bold text-white", className)} aria-hidden="true">{text}</span>;
}
