'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
    LayoutDashboard,
    BookOpen,
    LineChart,
    Settings,
    LogOut,
    Menu,
    X,
    Shield,
    FileQuestion,
    ClipboardList,
    Users,
    Brain,
    Target,
    History
} from 'lucide-react';

import NotificationBell from '../../components/ui/NotificationBell';
import OnboardingCheck from '../../components/OnboardingCheck';

export default function DashboardLayout({ children }) {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [user, setUser] = useState(null);
    const pathname = usePathname();
    const router = useRouter();

    useEffect(() => {
        const userData = localStorage.getItem('user');
        if (userData) {
            const parsedUser = JSON.parse(userData);
            setUser(parsedUser);
            
            // Sync with backend to ensure data (like profile pic) is fresh
            import('@/lib/api').then(({ authAPI }) => {
                authAPI.getProfile().then(freshUser => {
                    setUser(freshUser);
                    localStorage.setItem('user', JSON.stringify(freshUser));
                }).catch(err => console.error("Profile sync failed:", err));
            });
        } else {
            router.push('/login');
        }
    }, [router]);

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        router.push('/login');
    };

    const allNavItems = [
        { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['all'] },
        { name: 'Classrooms', href: '/dashboard/classrooms', icon: Users, roles: ['all'] },
        { name: 'Learning', href: '/dashboard/learning', icon: BookOpen, roles: ['all'] },
        { name: 'Topics', href: '/dashboard/topics', icon: BookOpen, roles: ['teacher', 'admin'] },
        { name: 'Question Bank', href: '/dashboard/questions', icon: FileQuestion, roles: ['teacher', 'admin'] },
        { name: 'Quizzes', href: '/dashboard/quizzes', icon: BookOpen, roles: ['teacher', 'admin'] },
        { name: 'History', href: '/dashboard/history', icon: History, roles: ['all'] },
        { name: 'Settings', href: '/dashboard/settings', icon: Settings, roles: ['all'] },
    ];

    // Filter nav items based on role if needed (currently all are 'all')
    const navItems = allNavItems.filter(item =>
        item.roles.includes('all') || (user && item.roles.includes(user.role))
    );

    if (!user) return null;

    return (
        <OnboardingCheck>
            <div className="h-screen w-full bg-background text-foreground flex overflow-hidden font-sans">
                {/* Mobile Sidebar Overlay */}
                {sidebarOpen && (
                    <div
                        className="fixed inset-0 bg-black/60 z-40 lg:hidden transition-opacity backdrop-blur-sm"
                        onClick={() => setSidebarOpen(false)}
                    />
                )}

                {/* Sidebar */}
                <aside className={`
                fixed lg:static inset-y-0 left-0 z-50 w-72 flex-shrink-0
                transform transition-transform duration-300 ease-in-out
                ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
                sidebar-gradient
                flex flex-col h-full shadow-xl
            `}>
                    {/* Logo Header */}
                    <div className="h-16 flex-shrink-0 flex items-center px-6 border-b border-white/10 bg-white/5 backdrop-blur-md">
                        <Link href="/dashboard" className="flex items-center gap-3 group">
                            <div className="p-1.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg shadow-lg shadow-primary/30 group-hover:scale-105 transition-transform ring-1 ring-white/20">
                                <Brain className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-lg font-bold tracking-tight text-white/90">
                                LearnMate AI
                            </span>
                        </Link>
                        <button
                            className="lg:hidden ml-auto text-muted-foreground hover:text-foreground"
                            onClick={() => setSidebarOpen(false)}
                        >
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1 custom-scrollbar">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.name}
                                    href={item.href}
                                    className={`
                                    sidebar-link
                                    ${isActive ? 'active shadow-lg shadow-primary/10' : ''}
                                `}
                                >
                                    <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-slate-200'}`} />
                                    <span>{item.name}</span>
                                </Link>
                            );
                        })}
                    </nav>

                    {/* User Profile & Logout - Pinned to bottom */}
                    <div className="p-4 border-t border-white/10 bg-black/20 flex-shrink-0">
                        <div className="flex items-center gap-3 px-2 py-2 mb-2">
                            {user.profile_picture ? (
                                <img
                                    src={user.profile_picture}
                                    alt={`${user.first_name} ${user.last_name}`}
                                    className="w-9 h-9 rounded-full object-cover ring-2 ring-white/10"
                                />
                            ) : (
                                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-md ring-2 ring-white/10">
                                    {user.username?.[0]?.toUpperCase()}
                                </div>
                            )}
                            <div className="overflow-hidden">
                                <p className="text-sm font-semibold truncate text-slate-100 leading-none">{user.first_name} {user.last_name}</p>
                                <p className="text-xs text-slate-400 truncate mt-1">{user.role || 'User'}</p>
                            </div>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-all text-sm font-medium"
                        >
                            <LogOut className="w-4 h-4" />
                            <span>Sign out</span>
                        </button>
                    </div>
                </aside>

                {/* Main Content Area */}
                <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative">
                    {/* Top Header */}
                    <header className="h-16 flex-shrink-0 flex items-center justify-between px-4 lg:px-8 border-b border-white/5 bg-background/50 backdrop-blur-md sticky top-0 z-30">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => setSidebarOpen(true)}
                                className="lg:hidden p-2 -ml-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-white/5 transition-colors"
                            >
                                <Menu className="w-6 h-6" />
                            </button>
                            <h2 className="text-xl font-bold tracking-tight text-white/90 capitalize mb-0">
                                {(() => {
                                    if (pathname === '/dashboard') return 'Overview';
                                    if (pathname.startsWith('/dashboard/learning/')) {
                                        return 'Learning Module';
                                    }
                                    if (pathname.startsWith('/dashboard/classrooms/')) {
                                        const segments = pathname.split('/');
                                        if (segments.length > 3) return 'Classroom Details';
                                    }
                                    if (pathname.startsWith('/dashboard/results/')) {
                                        return 'Quiz Results';
                                    }
                                    const lastSegment = pathname.split('/').pop();
                                    const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(lastSegment);
                                    if (isUUID) return 'Details';
                                    return lastSegment.replace(/-/g, ' ');
                                })()}
                            </h2>
                        </div>

                        <div className="flex items-center gap-4">
                            <NotificationBell />
                        </div>
                    </header>

                    {/* Page Content Container */}
                    <main className="flex-1 overflow-y-auto p-4 lg:p-8 scroll-smooth hover:scroll-auto">
                        <div className="max-w-7xl mx-auto space-y-6 animate-fade-in pb-10">
                            {children}
                        </div>
                    </main>
                </div>
            </div>
        </OnboardingCheck>
    );
}

