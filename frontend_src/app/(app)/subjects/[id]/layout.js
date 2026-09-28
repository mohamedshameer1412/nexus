"use client";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Download } from "lucide-react";
import { SECTIONS } from "@/components/nexus/nav-data";
import { getSubject, keys } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { ErrorState } from "@/components/nexus/common";
import { LevelPrompt } from "@/components/nexus/level-prompt";
import { SubjectActions } from "@/components/nexus/subject-actions";
import { Badge, Button, Skeleton, Tooltip } from "@/components/ui/primitives";

const LEVEL = { new: "New learner", intermediate: "Intermediate", professional: "Professional" };

/** The subject workspace: header, section tabs (a bottom bar on phones), then the section. */
export default function SubjectLayout({ children }) {
  const { id } = useParams();
  const pathname = usePathname();
  const tabs = useRef(null);
  const { data: subject, isPending, error, refetch } = useQuery({ queryKey: keys.subject(id), queryFn: () => getSubject(id) });
  const base = `/subjects/${id}`;
  const active = (slug) => pathname === `${base}/${slug}` || pathname.startsWith(`${base}/${slug}/`);
  const current = SECTIONS.find((s) => active(s.slug));
  const inQuiz = /\/quiz\/\d+$/.test(pathname);
  useEffect(() => { tabs.current?.querySelector('[aria-current="page"]')?.scrollIntoView({ block: "nearest", inline: "center" }); }, [pathname]);

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isPending) return <div className="space-y-4"><Skeleton className="h-6 w-40" /><Skeleton className="h-16 w-full" /><Skeleton className="h-10 w-full" /><Skeleton className="h-64 w-full" /></div>;
  const c = subject.counts;

  return (
    <div>
      <nav aria-label="Breadcrumb" className="no-print mb-2 flex items-center gap-1 text-[13px] text-muted">
        <Link href="/subjects" className="text-muted no-underline hover:text-brand-deep">Subjects</Link>
        <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
        <Link href={`${base}/materials`} className="max-w-[40vw] truncate text-muted no-underline hover:text-brand-deep">{subject.name}</Link>
        {current && <><ChevronRight className="h-3.5 w-3.5" aria-hidden="true" /><span className="text-foreground">{current.label}</span></>}
      </nav>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="break-anywhere font-display text-[26px] font-semibold leading-tight sm:text-[28px]">{subject.name}</h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[13px] text-muted">
            {subject.level && <Badge tone="neutral">{LEVEL[subject.level]}</Badge>}
            <span className="tabular">{c.documents} files</span><span aria-hidden="true">·</span>
            <span className="tabular">{c.topics} topics</span><span aria-hidden="true">·</span>
            <span className="tabular">{c.practice_questions} practice questions</span>
          </div>
          {subject.description && <p className="break-anywhere mt-1.5 max-w-3xl text-sm text-muted">{subject.description}</p>}
        </div>
        <div className="no-print flex items-center gap-2">
          <Tooltip content="A formatted PDF report of this subject">
            <Button asChild variant="secondary" size="sm"><a href={`/api/v1/subjects/${id}/report.pdf`} download className="no-underline"><Download className="h-4 w-4" />PDF report</a></Button>
          </Tooltip>
          <SubjectActions subject={subject} redirect />
        </div>
      </div>

      {!inQuiz && (
        <nav aria-label="Subject sections" className="no-print sticky top-14 z-20 -mx-4 mt-4 hidden border-b border-border bg-background/90 px-4 backdrop-blur sm:block sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
          <ul ref={tabs} className="nx-scroll-light -mb-px flex gap-1 overflow-x-auto whitespace-nowrap">
            {SECTIONS.map(({ slug, label, Icon }) => (
              <li key={slug}>
                <Link href={`${base}/${slug}`} aria-current={active(slug) ? "page" : undefined}
                  className={cn("inline-flex h-11 items-center gap-2 border-b-2 px-3 text-[13.5px] font-semibold no-underline transition-colors",
                    active(slug) ? "border-brand text-brand-deep" : "border-transparent text-muted hover:border-brand/30 hover:text-foreground")}>
                  <Icon className="h-4 w-4" aria-hidden="true" />{label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}

      {!inQuiz && (
        <nav aria-label="Subject sections" className="no-print fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur sm:hidden">
          <ul className="flex overflow-x-auto">
            {SECTIONS.map(({ slug, label, Icon }) => (
              <li key={slug} className="shrink-0">
                <Link href={`${base}/${slug}`} aria-current={active(slug) ? "page" : undefined}
                  className={cn("flex h-14 min-w-[4.7rem] flex-col items-center justify-center gap-0.5 px-1 text-[11px] font-semibold no-underline", active(slug) ? "text-brand-deep" : "text-muted")}>
                  <Icon className="h-5 w-5" aria-hidden="true" />{label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}

      <div className="mt-6">
        {/\/(materials|ask|notes|practice)$/.test(pathname) && <LevelPrompt subject={subject} />}
        {children}
      </div>
    </div>
  );
}
