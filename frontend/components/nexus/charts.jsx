"use client";
// Charts. Recharts for the standard forms; hand-drawn SVG for the Nexus-specific ones (ability intervals, habit heatmap, gauges).
import { useId, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis,
  Radar, RadarChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, ComposedChart,
} from "recharts";
import { cn } from "@/lib/utils";
import { CHART, TONE_HEX, confTone } from "@/lib/format";
import { Card, CardBody, CardHeader } from "@/components/ui/primitives";

export function ChartCard({ title, description, action, children, className, icon, bodyClassName }) {
  return (
    <Card className={cn("flex min-w-0 flex-col", className)}>
      <CardHeader title={title} description={description} action={action} icon={icon} />
      <CardBody className={cn("min-w-0 flex-1", bodyClassName)}>{children}</CardBody>
    </Card>
  );
}

export function NoData({ children = "Nothing to show yet.", height = 180 }) {
  return <div className="grid place-items-center rounded-lg bg-surface-2 text-center text-sm text-muted" style={{ height }}>{children}</div>;
}

function Tip({ active, payload, label, fmt, labelFmt }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-[12.5px] shadow-pop">
      {label != null && <p className="mb-1 font-semibold text-foreground">{labelFmt ? labelFmt(label, payload) : label}</p>}
      {payload.filter((p) => p.value != null).map((p) => (
        <p key={p.dataKey} className="flex items-center gap-2 text-muted">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color || p.payload?.fill }} aria-hidden="true" />
          <span>{p.name}</span><b className="tabular ml-auto pl-3 text-foreground">{fmt ? fmt(p.value, p.dataKey) : p.value}</b>
        </p>
      ))}
    </div>
  );
}

const axis = { tickLine: false, axisLine: false, tick: { fontSize: 12 } };

/** Filled area trend. series: [{key, name, color}] */
export function TrendArea({ data, x = "label", series, height = 220, yDomain, yFmt, tipFmt, reference, labelFmt, stacked }) {
  const id = useId().replace(/:/g, "");
  if (!data?.length) return <NoData height={height} />;
  return (
    <div style={{ height }} className="-ml-3">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            {series.map((s, i) => (
              <linearGradient key={s.key} id={`${id}-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={s.color || CHART[i]} stopOpacity={0.28} />
                <stop offset="100%" stopColor={s.color || CHART[i]} stopOpacity={0.02} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid vertical={false} strokeDasharray="3 3" />
          <XAxis dataKey={x} {...axis} minTickGap={18} />
          <YAxis {...axis} width={40} domain={yDomain} tickFormatter={yFmt} allowDecimals={false} />
          <Tooltip content={<Tip fmt={tipFmt} labelFmt={labelFmt} />} />
          {reference != null && <ReferenceLine y={reference.y} stroke="#0B2239" strokeDasharray="4 4" strokeOpacity={0.45} label={{ value: reference.label, position: "insideTopRight", fontSize: 11, fill: "#52667D" }} />}
          {series.map((s, i) => (
            <Area key={s.key} type="monotone" dataKey={s.key} name={s.name} stackId={stacked ? "a" : undefined} stroke={s.color || CHART[i]} strokeWidth={2}
              fill={`url(#${id}-${s.key})`} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} connectNulls />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TrendLine({ data, x = "label", series, height = 220, yDomain, yFmt, tipFmt, reference, bars }) {
  if (!data?.length) return <NoData height={height} />;
  return (
    <div style={{ height }} className="-ml-3">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" />
          <XAxis dataKey={x} {...axis} minTickGap={18} />
          <YAxis {...axis} width={40} domain={yDomain} tickFormatter={yFmt} yAxisId="l" />
          {bars && <YAxis {...axis} width={32} orientation="right" yAxisId="r" allowDecimals={false} />}
          <Tooltip content={<Tip fmt={tipFmt} />} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
          {reference != null && <ReferenceLine yAxisId="l" y={reference.y} stroke="#0B2239" strokeDasharray="4 4" strokeOpacity={0.45} label={{ value: reference.label, position: "insideTopLeft", fontSize: 11, fill: "#52667D" }} />}
          {bars?.map((b, i) => <Bar key={b.key} yAxisId="r" dataKey={b.key} name={b.name} fill={b.color || CHART[5 - i]} fillOpacity={0.25} radius={[4, 4, 0, 0]} maxBarSize={28} />)}
          {series.map((s, i) => <Line key={s.key} yAxisId="l" type="monotone" dataKey={s.key} name={s.name} stroke={s.color || CHART[i]} strokeWidth={2.2} dot={data.length <= 16 ? { r: 3, strokeWidth: 0, fill: s.color || CHART[i] } : false} activeDot={{ r: 5 }} connectNulls />)}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Bars. layout="vertical" draws horizontal bars (category on the Y axis). colorBy(row) can colour each bar. */
/** Keeps the same array identity while the contents are unchanged, so a parent re-render does not restart the bar animation. */
function useStableData(data) {
  const key = JSON.stringify(data ?? []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => data, [key]);
}

export function Bars({ data: raw, x = "label", series, height = 220, layout = "horizontal", stacked, yFmt, tipFmt, colorBy, reference, domain, catWidth = 120 }) {
  const data = useStableData(raw);
  if (!data?.length) return <NoData height={height} />;
  const vertical = layout === "vertical";
  return (
    <div style={{ height }} className={vertical ? "" : "-ml-3"}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout={vertical ? "vertical" : "horizontal"} margin={{ top: reference != null && vertical ? 20 : 8, right: 12, bottom: 0, left: 0 }} barCategoryGap="22%">
          <CartesianGrid horizontal={!vertical} vertical={vertical} strokeDasharray="3 3" />
          {vertical ? (<>
            <XAxis type="number" {...axis} domain={domain} tickFormatter={yFmt} />
            <YAxis type="category" dataKey={x} {...axis} width={catWidth} interval={0} tick={{ fontSize: 12, fill: "#0B2239" }} />
          </>) : (<>
            <XAxis dataKey={x} {...axis} minTickGap={8} />
            <YAxis {...axis} width={40} domain={domain} tickFormatter={yFmt} allowDecimals={false} />
          </>)}
          <Tooltip content={<Tip fmt={tipFmt} />} cursor={{ fill: "rgb(217 238 251 / .45)" }} />
          {series.length > 1 && <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />}
          {reference != null && (vertical
            ? <ReferenceLine x={reference.x} stroke="#0B2239" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: reference.label, position: "top", fontSize: 11, fill: "#52667D" }} />
            : <ReferenceLine y={reference.y} stroke="#0B2239" strokeDasharray="4 4" strokeOpacity={0.5} />)}
          {series.map((s, i) => (
            <Bar key={s.key} dataKey={s.key} name={s.name} stackId={stacked ? "a" : undefined} fill={s.color || CHART[i]} radius={stacked ? 0 : vertical ? [0, 4, 4, 0] : [4, 4, 0, 0]} maxBarSize={vertical ? 18 : 34}>
              {colorBy && data.map((row, j) => <Cell key={j} fill={colorBy(row)} />)}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Donut with the total (or a given value) in the middle. data: [{name, value, color}] */
export function Donut({ data, height = 200, center, centerLabel, stacked }) {
  const total = data.reduce((a, d) => a + (d.value || 0), 0);
  if (!total) return <NoData height={height} />;
  return (
    <div className={cn("flex items-center gap-4", stacked ? "flex-col" : "flex-col sm:flex-row")}>
      <div className="relative shrink-0" style={{ width: height, height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data.filter((d) => d.value)} dataKey="value" nameKey="name" innerRadius="64%" outerRadius="96%" paddingAngle={2} stroke="none" startAngle={90} endAngle={-270}>
              {data.filter((d) => d.value).map((d, i) => <Cell key={d.name} fill={d.color || CHART[i]} />)}
            </Pie>
            <Tooltip content={<Tip />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <div><p className="tabular font-display text-2xl font-semibold leading-none">{center ?? total}</p>{centerLabel && <p className="mt-1 text-xs text-muted">{centerLabel}</p>}</div>
        </div>
      </div>
      <ul className="w-full space-y-1.5 text-sm">
        {data.map((d, i) => (
          <li key={d.name} className="flex items-center gap-2 whitespace-nowrap">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: d.color || CHART[i] }} aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate text-muted" title={d.name}>{d.name}</span>
            <b className="tabular">{d.value}</b>
            <span className="tabular w-10 text-right text-xs text-muted">{Math.round((100 * (d.value || 0)) / total)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** A semicircle gauge for a 0..100 score. */
export function Gauge({ value, label, tone, size = 168, suffix = "%" }) {
  const v = value == null ? 0 : Math.max(0, Math.min(100, value));
  const r = 64, c = Math.PI * r;
  const color = TONE_HEX[tone || (value == null ? "muted" : v >= 70 ? "strong" : v >= 45 ? "mid" : "weak")];
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 160 92" width={size} height={size * 0.575} role="img" aria-label={`${label}: ${value == null ? "not enough data" : `${Math.round(v)}${suffix}`}`}>
        <path d="M16 84 A64 64 0 0 1 144 84" fill="none" stroke="rgb(217 238 251)" strokeWidth="13" strokeLinecap="round" />
        <motion.path d="M16 84 A64 64 0 0 1 144 84" fill="none" stroke={color} strokeWidth="13" strokeLinecap="round" strokeDasharray={c}
          initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - v / 100) }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }} />
        <text x="80" y="76" textAnchor="middle" className="font-display" style={{ fontSize: 26, fontWeight: 650, fill: "#0B2239" }}>{value == null ? "–" : `${Math.round(v)}${suffix}`}</text>
      </svg>
      {label && <p className="-mt-1 text-[13px] text-muted">{label}</p>}
    </div>
  );
}

/** Weekday × hour activity grid. matrix[7][24], Monday first (UTC). */
export function HabitHeatmap({ matrix }) {
  const max = Math.max(1, ...matrix.flat());
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  if (!matrix.flat().some(Boolean)) return <NoData height={170}>Answer a few questions and your study rhythm appears here.</NoData>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-separate border-spacing-[3px]" aria-label="Answers by weekday and hour (UTC)">
        <thead><tr><th className="w-10" />{Array.from({ length: 24 }, (_, h) => <th key={h} scope="col" className="text-[10px] font-normal text-muted">{h % 3 === 0 ? h : ""}</th>)}</tr></thead>
        <tbody>
          {matrix.map((row, d) => (
            <tr key={d}>
              <th scope="row" className="pr-1 text-left text-[11px] font-medium text-muted">{days[d]}</th>
              {row.map((n, h) => (
                <td key={h} title={`${days[d]} ${h}:00 UTC: ${n} answer${n === 1 ? "" : "s"}`} className="h-4 rounded-[3px]"
                  style={{ background: n ? `rgb(1 148 226 / ${0.15 + 0.85 * (n / max)})` : "rgb(217 238 251 / .45)" }} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A GitHub-style calendar of daily activity from the timeline [{date, answered, asked, flashcards}]. */
export function ActivityCalendar({ days }) {
  const val = (d) => (d.answered || 0) + (d.asked || 0) + (d.flashcards || 0);
  const max = Math.max(1, ...days.map(val));
  const first = new Date(days[0]?.date + "T00:00:00Z").getUTCDay();
  const pad = (first + 6) % 7;
  const cells = [...Array(pad).fill(null), ...days];
  const weeks = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  const size = weeks.length <= 6 ? 26 : weeks.length <= 15 ? 18 : 13;
  const labels = ["M", "T", "W", "T", "F", "S", "S"];
  return (
    <div className="flex gap-[4px] overflow-x-auto pb-1" role="img" aria-label="Daily study activity">
      <div className="flex flex-col gap-[4px] pr-1 text-[10px] text-muted">{labels.map((l, i) => <span key={i} style={{ height: size, lineHeight: `${size}px` }}>{l}</span>)}</div>
      {weeks.map((w, i) => (
        <div key={i} className="flex flex-col gap-[4px]">
          {w.map((d, j) => d ? (
            <span key={j} title={`${d.date}: ${d.answered} answered, ${d.asked} asked, ${d.flashcards} flashcards`} className="rounded-[4px]"
              style={{ width: size, height: size, background: val(d) ? `rgb(1 148 226 / ${0.18 + 0.82 * (val(d) / max)})` : "rgb(217 238 251 / .6)" }} />
          ) : <span key={j} style={{ width: size, height: size }} />)}
        </div>
      ))}
    </div>
  );
}

/**
 * The Nexus signature: each topic's ability as an interval, not a bare percentage.
 * The dot is the ability estimate θ (Bayesian IRT posterior mean), the bar is ±1 standard error, the dashed line is the
 * proficient line (θ = 0). A wide bar means "not enough answers yet"; a bar entirely right of the line means "reliably strong".
 */
export function AbilityIntervals({ items, target = 0.7, lo = -3, hi = 3, onSelect }) {
  const scored = items.filter((t) => t.theta != null);
  if (!scored.length) return <NoData height={140}>Take a quiz to place your first topics on the ability scale.</NoData>;
  const x = (v) => ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * 100;
  return (
    <div>
      <div className="relative ml-[38%] mr-2 h-5 text-[11px] text-muted sm:ml-[30%]">
        {[-3, -2, -1, 0, 1, 2, 3].map((t) => <span key={t} className="tabular absolute -translate-x-1/2" style={{ left: `${x(t)}%` }}>{t > 0 ? `+${t}` : t}</span>)}
      </div>
      <ul className="space-y-1">
        {scored.map((t, i) => {
          const tone = confTone(t.confidence, target);
          const color = TONE_HEX[tone];
          const se = t.se ?? 1;
          return (
            <li key={t.topic_id ?? t.name}>
              <button type="button" onClick={onSelect ? () => onSelect(t) : undefined} disabled={!onSelect}
                className="group flex w-full items-center gap-2 rounded-md py-1 text-left enabled:hover:bg-brand-wash"
                aria-label={`${t.name}: ability ${t.theta.toFixed(2)} plus or minus ${se.toFixed(2)}, confidence ${Math.round((t.confidence ?? 0) * 100)} percent`}>
                <span className="w-[38%] truncate pl-1 text-[13px] sm:w-[30%]" title={t.name}>{t.name}</span>
                <span className="relative mr-2 h-6 flex-1">
                  <span className="absolute inset-y-[11px] left-0 right-0 rounded-full bg-brand-soft/60" />
                  <span className="absolute inset-y-0 border-l border-dashed border-brand-ink/40" style={{ left: `${x(0)}%` }} />
                  <motion.span className="absolute inset-y-[8px] rounded-full" style={{ background: `${color}33`, border: `1px solid ${color}66` }}
                    initial={{ left: `${x(0)}%`, width: 0 }} animate={{ left: `${x(t.theta - se)}%`, width: `${x(t.theta + se) - x(t.theta - se)}%` }}
                    transition={{ duration: 0.7, delay: 0.04 * i, ease: [0.22, 1, 0.36, 1] }} />
                  <motion.span className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white" style={{ background: color }}
                    initial={{ left: `${x(0)}%` }} animate={{ left: `${x(t.theta)}%` }} transition={{ duration: 0.7, delay: 0.04 * i, ease: [0.22, 1, 0.36, 1] }} />
                </span>
                <span className="tabular w-11 shrink-0 text-right text-[12.5px] font-semibold" style={{ color }}>{t.confidence == null ? "–" : `${Math.round(t.confidence * 100)}%`}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-muted">
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-brand-ink/70" />ability θ</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-5 rounded-full bg-brand-soft ring-1 ring-brand/30" />± uncertainty</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-3 border-l border-dashed border-brand-ink/60" />proficient line</span>
        <span>% = chance you are above the line</span>
      </p>
    </div>
  );
}

export function Sparkline({ values, color = "#0194E2", height = 36, width = 120 }) {
  const v = values.filter((x) => x != null);
  if (v.length < 2) return null;
  const min = Math.min(...v), max = Math.max(...v), span = max - min || 1;
  const pts = v.map((y, i) => `${(i / (v.length - 1)) * width},${height - 3 - ((y - min) / span) * (height - 6)}`).join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export function RadarProfile({ data, height = 260 }) {
  if (!data?.length || data.length < 3) return <NoData height={height}>A profile appears once three or more units have answers.</NoData>;
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="rgb(213 232 245)" />
          <PolarAngleAxis dataKey="name" tick={{ fontSize: 11, fill: "#52667D" }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar dataKey="value" name="Confidence" stroke="#0194E2" fill="#0194E2" fillOpacity={0.22} strokeWidth={2} />
          <Tooltip content={<Tip fmt={(v) => `${v}%`} />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export { LineChart, Line };
