'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
    Clock,
    Calendar,
    CheckCircle2,
    Search,
    ChevronRight,
    Play,
    Award,
    Trash2,
    Users,
    Filter,
    Trophy,
    History,
    ArrowRight
} from 'lucide-react';
import { quizAPI } from '@/lib/api';
import ConfirmationModal from '@/components/ui/ConfirmationModal';

const HistoryContent = () => {
    const router = useRouter();
    const searchParams = useSearchParams();
    const classroomId = searchParams.get('classroom_id');
    const studentIdParam = searchParams.get('student_id');

    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterStatus, setFilterStatus] = useState('all');
    const [deleteConfirmation, setDeleteConfirmation] = useState({ isOpen: false, sessionId: null });
    const [user, setUser] = useState(null);

    useEffect(() => {
        const storedUser = localStorage.getItem('user');
        if (storedUser) setUser(JSON.parse(storedUser));
    }, []);

    useEffect(() => {
        if (user) loadHistory();
    }, [user, classroomId, studentIdParam]);

    const loadHistory = async () => {
        setLoading(true);
        try {
            let data;
            const isTeacher = user?.role === 'teacher';

            if (isTeacher) {
                // Teachers see all student results for their quizzes/classrooms
                data = await quizAPI.getAllQuizResults(classroomId);
            } else {
                // Students see personal history
                data = await quizAPI.getSessions(studentIdParam, classroomId);
            }

            const sessionsList = Array.isArray(data) ? data : data.results || [];

            // Map the teacher response (which might have different field names) to common format
            const formatted = sessionsList.map(s => ({
                id: s.id || s.session_id,
                quiz_title: s.quiz_title,
                quiz_topic: s.quiz_topic || 'General',
                started_at: s.started_at || s.completed_at,
                completed_at: s.completed_at,
                is_active: s.is_active || false,
                total_score: s.total_score !== undefined ? s.total_score : s.score,
                score: s.total_score !== undefined ? s.total_score : s.score,
                accuracy: s.accuracy,
                time_spent: s.time_spent || 0,
                student_name: s.student_name,
                student_email: s.student_email,
                quiz_id: s.quiz_id || (s.quiz && s.quiz.id)
            }));

            // Sort by most recent
            formatted.sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
            setSessions(formatted);
        } catch (error) {
            console.error('Failed to load history:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAction = (session) => {
        if (session.is_active) {
            router.push(`/quiz/${session.id}`);
        } else {
            router.push(`/dashboard/results/${session.id}`);
        }
    };

    const handleDeleteClick = (e, sessionId) => {
        e.stopPropagation();
        setDeleteConfirmation({ isOpen: true, sessionId });
    };

    const handleConfirmDelete = async () => {
        if (!deleteConfirmation.sessionId) return;
        try {
            await quizAPI.deleteSession(deleteConfirmation.sessionId);
            setSessions(prev => prev.filter(s => s.id !== deleteConfirmation.sessionId));
            setDeleteConfirmation({ isOpen: false, sessionId: null });
        } catch (error) {
            console.error('Failed to delete session:', error);
        }
    };

    const filteredAttempts = sessions.filter(s => {
        const matchesSearch = (s.quiz_title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
            (s.student_name || '').toLowerCase().includes(searchQuery.toLowerCase());

        if (filterStatus === 'completed') return matchesSearch && !s.is_active;
        if (filterStatus === 'in-progress') return matchesSearch && s.is_active;
        return matchesSearch;
    });

    const isTeacherView = user?.role === 'teacher';

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row gap-6 md:items-center justify-between">
                <div>
                    <h1 className="text-4xl font-black text-white tracking-tight font-outfit mb-2">
                        Quiz <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-violet-400">History</span>
                    </h1>
                    <p className="text-slate-400 font-medium text-lg">
                        Track your progress and review past performance
                    </p>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="glass p-4 rounded-2xl border-white/10 bg-black/20 flex items-center gap-4">
                        <div className="p-3 bg-green-500/10 rounded-xl">
                            <CheckCircle2 className="w-6 h-6 text-green-400" />
                        </div>
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Completed</p>
                            <p className="text-2xl font-black text-white">{sessions.filter(a => !a.is_active).length}</p>
                        </div>
                    </div>
                    <div className="glass p-4 rounded-2xl border-white/10 bg-black/20 flex items-center gap-4">
                        <div className="p-3 bg-amber-500/10 rounded-xl">
                            <Clock className="w-6 h-6 text-amber-400" />
                        </div>
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Avg Time</p>
                            <p className="text-2xl font-black text-white">
                                {Math.round(sessions.reduce((acc, curr) => acc + (curr.time_spent || 0), 0) / (sessions.filter(a => !a.is_active).length || 1))}m
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Filter Bar */}
            <div className="glass p-2 rounded-2xl border-white/10 bg-black/20 flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="relative group w-full sm:max-w-md">
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 p-1 bg-white/5 rounded-lg group-focus-within:bg-primary/20 transition-colors">
                        <Search className="w-4 h-4 text-slate-400 group-focus-within:text-primary" />
                    </div>
                    <input
                        type="text"
                        placeholder="Search usage history..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-14 pr-4 py-3 bg-transparent rounded-xl focus:outline-none text-white font-bold placeholder:text-slate-500"
                    />
                </div>

                <div className="flex gap-2 w-full sm:w-auto overflow-x-auto pb-2 sm:pb-0 scrollbar-hide">
                    {['all', 'completed', 'in-progress'].map((filter) => (
                        <button
                            key={filter}
                            onClick={() => setFilterStatus(filter)}
                            className={`px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all whitespace-nowrap ${filterStatus === filter ? 'bg-primary text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white'
                                }`}
                        >
                            {filter}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content Content - Using a dark table style */}
            <div className="glass rounded-[2.5rem] overflow-hidden border-white/10 shadow-2xl bg-[#0f111a]/50 backdrop-blur-xl">
                {/* Table Header */}
                <div className="grid grid-cols-12 gap-4 p-6 border-b border-white/5 bg-black/20 text-[10px] font-black uppercase tracking-widest text-slate-400 hidden md:grid">
                    <div className="col-span-4 pl-4">Quiz Details</div>
                    <div className="col-span-2 text-center">Score</div>
                    <div className="col-span-2 text-center">Date</div>
                    <div className="col-span-2 text-center">Time Spent</div>
                    <div className="col-span-2 text-right pr-4">Actions</div>
                </div>

                <div className="divide-y divide-white/5">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="w-12 h-12 border-4 border-slate-700 border-t-primary rounded-full animate-spin mb-4" />
                            <p className="text-slate-400 font-bold">Fetching results...</p>
                        </div>
                    ) : filteredAttempts.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-24 text-center">
                            <div className="w-24 h-24 bg-white/5 rounded-full flex items-center justify-center mb-6">
                                <History className="w-10 h-10 text-slate-600" />
                            </div>
                            <h3 className="text-xl font-black text-white mb-2">No History Found</h3>
                            <p className="text-slate-400 max-w-xs mx-auto">
                                You haven&apos;t taken any quizzes yet. Start a quiz to see your history here!
                            </p>
                        </div>
                    ) : (
                        filteredAttempts.map((attempt) => (
                            <div
                                key={attempt.id}
                                className="group relative overflow-hidden transition-all duration-300 hover:bg-white/5"
                            >
                                {/* Mobile View */}
                                <div className="md:hidden p-6 space-y-4">
                                    <div className="flex justify-between items-start">
                                        <div className="flex items-center gap-3">
                                            <div className="p-3 bg-gradient-to-br from-blue-500/20 to-violet-500/20 rounded-2xl border border-white/5">
                                                <Trophy className="w-6 h-6 text-blue-400" />
                                            </div>
                                            <div>
                                                <h3 className="font-bold text-white text-lg">{attempt.quiz_title}</h3>
                                                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">{attempt.quiz_topic}</p>
                                            </div>
                                        </div>
                                        <div className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest border ${attempt.is_active
                                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                            : parseFloat(attempt.score) >= 80
                                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                                : parseFloat(attempt.score) >= 60
                                                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                                    : 'bg-red-500/10 text-red-400 border-red-500/20'
                                            }`}>
                                            {attempt.is_active ? 'Ongoing' : `${Math.round(parseFloat(attempt.score))}%`}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4 py-4 border-t border-white/5">
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <Calendar className="w-4 h-4" />
                                            <span className="text-xs font-bold">{attempt.completed_at ? new Date(attempt.completed_at).toLocaleDateString('en-GB') : 'N/A'}</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <Clock className="w-4 h-4" />
                                            <span className="text-xs font-bold">{attempt.time_spent ? `${attempt.time_spent}m` : 'N/A'}</span>
                                        </div>
                                    </div>

                                    <button
                                        onClick={() => handleAction(attempt)}
                                        className="w-full py-3 bg-white/5 hover:bg-white/10 rounded-xl text-xs font-black uppercase tracking-widest text-white transition-colors flex items-center justify-center gap-2"
                                    >
                                        View Analysis
                                        <ArrowRight className="w-4 h-4" />
                                    </button>
                                </div>

                                {/* Desktop View */}
                                <div className="hidden md:grid grid-cols-12 gap-4 p-6 items-center">
                                    <div className="col-span-4 pl-4 flex items-center gap-4">
                                        <div className="p-3 bg-gradient-to-br from-blue-500/20 to-violet-500/20 rounded-2xl border border-white/5 group-hover:scale-110 transition-transform duration-300">
                                            <Trophy className="w-5 h-5 text-blue-400" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-white text-base group-hover:text-primary transition-colors">{attempt.quiz_title}</h3>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">{attempt.quiz_topic}</p>
                                        </div>
                                    </div>

                                    <div className="col-span-2 flex justify-center">
                                        <div className={`px-4 py-1.5 rounded-xl text-xs font-black border ${attempt.is_active
                                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                            : parseFloat(attempt.score) >= 80
                                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                                : parseFloat(attempt.score) >= 60
                                                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                                    : 'bg-red-500/10 text-red-400 border-red-500/20'
                                            }`}>
                                            {attempt.is_active ? 'Ongoing' : `${Math.round(parseFloat(attempt.score))}%`}
                                        </div>
                                    </div>

                                    <div className="col-span-2 text-center text-sm font-bold text-slate-400">
                                        {attempt.completed_at ? new Date(attempt.completed_at).toLocaleDateString('en-GB') : '-'}
                                    </div>

                                    <div className="col-span-2 text-center text-sm font-bold text-slate-400">
                                        {attempt.time_spent ? `${attempt.time_spent} mins` : '-'}
                                    </div>

                                    <div className="col-span-2 flex justify-end pr-4">
                                        <button
                                            onClick={() => handleAction(attempt)}
                                            className="p-2 hover:bg-white/10 rounded-xl text-slate-400 hover:text-white transition-colors group-hover:translate-x-1 duration-300"
                                            title="View Analysis"
                                        >
                                            <ArrowRight className="w-5 h-5" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            <div className="text-center">
                {isTeacherView && (
                    <p className="text-slate-500 text-sm">You are viewing all student history as a teacher.</p>
                )}
            </div>

            {/* Delete Confirmation Modal */}
            <ConfirmationModal
                isOpen={deleteConfirmation.isOpen}
                onClose={() => setDeleteConfirmation({ isOpen: false, sessionId: null })}
                onConfirm={handleConfirmDelete}
                title="Delete Session"
                message="Are you sure you want to delete this quiz session? This action cannot be undone."
                confirmText="Delete"
                cancelText="Cancel"
                variant="danger"
            />
        </div>
    );
};

const HistoryPage = () => {
    return (
        <Suspense fallback={
            <div className="flex items-center justify-center min-h-screen">
                <div className="w-12 h-12 border-4 border-slate-700 border-t-primary rounded-full animate-spin" />
            </div>
        }>
            <HistoryContent />
        </Suspense>
    );
};

export default HistoryPage;
