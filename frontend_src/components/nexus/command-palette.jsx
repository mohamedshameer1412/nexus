"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Command } from "cmdk";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { BarChart3, Bookmark, Briefcase, LayoutDashboard, LibraryBig, Search, User } from "lucide-react";
import { getSubjects, keys } from "@/lib/queries";
import { SECTIONS } from "@/components/nexus/nav-data";

const PAGES = [
  { label: "Dashboard", href: "/dashboard", Icon: LayoutDashboard },
  { label: "Competency profile", href: "/competency", Icon: BarChart3 },
  { label: "Learning path", href: "/learn", Icon: LibraryBig },
  { label: "Diagnostic assessment", href: "/assess", Icon: LibraryBig },
  { label: "AI Tutor", href: "/ai-tutor", Icon: LibraryBig },
  { label: "Profile", href: "/profile", Icon: User },
  { label: "Subjects", href: "/subjects", Icon: LibraryBig },
  { label: "Search materials", href: "/search", Icon: Search },
  { label: "Saved answers", href: "/saved", Icon: Bookmark },
  { label: "Career goals", href: "/career", Icon: Briefcase },
  { label: "Account", href: "/account", Icon: User },
];

const FlashIcon = SECTIONS[2].Icon;
const item = "flex h-10 cursor-pointer items-center gap-3 rounded-md px-3 text-sm text-foreground data-[selected=true]:bg-brand-wash data-[selected=true]:text-brand-deep";

/** Ctrl+K (⌘K): jump to any page or subject section from the keyboard, or search all your materials. */
export function CommandPalette({ open, onOpenChange }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const { data: subjects } = useQuery({ queryKey: keys.subjects, queryFn: getSubjects, enabled: open });
  const go = (href) => { onOpenChange(false); setText(""); router.push(href); };
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-brand-ink/45 backdrop-blur-[2px]" />
        <DialogPrimitive.Content className="fixed left-1/2 top-[12vh] z-50 w-[min(94vw,40rem)] -translate-x-1/2 overflow-hidden rounded-2xl border border-border bg-surface shadow-pop focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95">
          <DialogPrimitive.Title className="sr-only">Search and jump</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">Type to filter pages and subjects, use the arrow keys, and press Enter.</DialogPrimitive.Description>
          <Command label="Search and jump" loop>
            <div className="flex items-center gap-2 border-b border-border px-4">
              <Search className="h-5 w-5 shrink-0 text-brand" aria-hidden="true" />
              <Command.Input value={text} onValueChange={setText} autoFocus placeholder="Jump to a page or subject, or search your materials" className="h-14 flex-1 bg-transparent text-base outline-none placeholder:text-muted" />
            </div>
            <Command.List className="nx-scroll-light max-h-[55vh] overflow-y-auto p-2">
              <Command.Empty className="px-3 py-8 text-center text-sm text-muted">Nothing matches. Press Enter to search your materials.</Command.Empty>
              {text.trim().length >= 2 && (
                <Command.Group heading="Search" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:text-muted">
                  <Command.Item value={`search ${text}`} onSelect={() => go(`/search?q=${encodeURIComponent(text.trim())}`)} className={item}>
                    <Search className="h-4 w-4" />Search all materials for “{text.trim()}”
                  </Command.Item>
                </Command.Group>
              )}
              <Command.Group heading="Pages" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:text-muted">
                {PAGES.map((p) => <Command.Item key={p.href} value={p.label} onSelect={() => go(p.href)} className={item}><p.Icon className="h-4 w-4" />{p.label}</Command.Item>)}
              </Command.Group>
              {(subjects ?? []).map((s) => (
                <Command.Group key={s.id} heading={s.name} className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:text-muted">
                  {SECTIONS.map(({ slug, label, Icon }) => (
                    <Command.Item key={slug} value={`${s.name} ${label}`} onSelect={() => go(`/subjects/${s.id}/${slug}`)} className={item}>
                      <Icon className="h-4 w-4" /><span className="flex-1">{label}</span><span className="text-xs text-muted">{s.name}</span>
                    </Command.Item>
                  ))}
                  <Command.Item value={`${s.name} flashcards`} onSelect={() => go(`/subjects/${s.id}/practice/flashcards`)} className={item}>
                    <FlashIcon className="h-4 w-4" /><span className="flex-1">Flashcards</span><span className="text-xs text-muted">{s.name}</span>
                  </Command.Item>
                </Command.Group>
              ))}
            </Command.List>
            <p className="border-t border-border px-4 py-2 text-xs text-muted">Arrow keys to move, Enter to open, Esc to close</p>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
