"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/nexus/twin",       label: "Digital Twin",    icon: "🧠" },
  { href: "/nexus/plan",       label: "Study Plan",      icon: "📋" },
  { href: "/nexus/tutor",      label: "Tutor Session",   icon: "📚" },
  { href: "/nexus/whatif",     label: "What-If",         icon: "⚡" },
  { href: "/nexus/analyze",    label: "Agent Pipeline",  icon: "🤖" },
  { href: "/nexus/career-gap", label: "Career Gap",      icon: "🎯" },
];

export default function NexusNav() {
  const pathname = usePathname();
  return (
    <nav className="nexus-nav">
      <div className="nexus-nav-brand">
        <span className="brand-logo">N</span>
        <span className="brand-name">NEXUS</span>
      </div>
      <ul className="nexus-nav-links">
        {NAV_LINKS.map(link => (
          <li key={link.href}>
            <Link
              href={link.href}
              className={`nav-link ${pathname.startsWith(link.href) ? "nav-link--active" : ""}`}
            >
              <span className="nav-icon">{link.icon}</span>
              <span className="nav-label">{link.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
