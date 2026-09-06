'use client';
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import styles from './nexus.module.css';

const AGENTS = [
  { key: 'analytics',  label: 'Analytics',  icon: '📊', href: '/nexus/dashboard' },
  { key: 'tutor',      label: 'Tutor',       icon: '🎓', href: null },
  { key: 'evaluator',  label: 'Evaluator',   icon: '🔬', href: null },
  { key: 'planner',    label: 'Planner',     icon: '🗺️', href: '/nexus/planner' },
  { key: 'content',    label: 'Content',     icon: '📝', href: null },
  { key: 'mentor',     label: 'Mentor',      icon: '🧭', href: null },
];

export default function NexusLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) { router.push('/login'); return; }
    const userData = localStorage.getItem('user');
    if (userData) setUser(JSON.parse(userData));
  }, []);

  const isOnboarding = pathname?.startsWith('/nexus/onboarding');

  if (isOnboarding) {
    return (
      <div className={styles.onboardingShell}>
        <header className={styles.onboardingHeader}>
          <span className={styles.logo}><span className={styles.logoStat}>NEXUS</span></span>
          <span className={styles.tagline}>Agentic Learner Intelligence OS</span>
        </header>
        <main className={styles.onboardingMain}>{children}</main>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      {/* Sidebar */}
      <aside className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : styles.sidebarClosed}`}>
        <div className={styles.sidebarTop}>
          <Link href="/nexus/dashboard" className={styles.logo}>
            <span className={styles.logoStat}>NEXUS</span>
          </Link>
          <button className={styles.sidebarToggle} onClick={() => setSidebarOpen(!sidebarOpen)}>
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        <nav className={styles.nav}>
          <Link href="/nexus/subjects" className={`${styles.navItem} ${pathname === '/nexus/subjects' ? styles.active : ''}`}>
            <span className={styles.navIcon}>📚</span>
            {sidebarOpen && <span>My Subjects</span>}
          </Link>
          <Link href="/nexus/dashboard" className={`${styles.navItem} ${pathname === '/nexus/dashboard' ? styles.active : ''}`}>
            <span className={styles.navIcon}>🧬</span>
            {sidebarOpen && <span>Digital Twin</span>}
          </Link>
          <Link href="/nexus/planner" className={`${styles.navItem} ${pathname === '/nexus/planner' ? styles.active : ''}`}>
            <span className={styles.navIcon}>🗺️</span>
            {sidebarOpen && <span>Planner</span>}
          </Link>
        </nav>

        {sidebarOpen && (
          <div className={styles.agentPanel}>
            <p className={styles.agentLabel}>Active Agents</p>
            {AGENTS.map(a => (
              <div key={a.key} className={styles.agentChip}>
                <span>{a.icon}</span>
                <span className={styles.agentName}>{a.label}</span>
                <span className={styles.agentDot} />
              </div>
            ))}
          </div>
        )}

        {user && sidebarOpen && (
          <div className={styles.userChip}>
            <div className={styles.userAvatar}>{user.username?.[0]?.toUpperCase()}</div>
            <div>
              <div className={styles.userName}>{user.username}</div>
              <div className={styles.userRole}>Student</div>
            </div>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className={styles.main}>{children}</main>
    </div>
  );
}
