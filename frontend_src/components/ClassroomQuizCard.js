'use client';

import { useState } from 'react';
import { classroomAPI } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { BookOpen, Clock, CheckCircle, AlertCircle, Trophy, Target } from 'lucide-react';

export default function ClassroomQuizCard({ classroom }) {
    const router = useRouter();
    const [loading, setLoading] = useState(null);
    const [error, setError] = useState('');

    const handleStartQuiz = async (assignment) => {
        if (assignment.attempts_remaining === 0) {
            setError('No attempts remaining for this quiz');
            return;
        }

        setLoading(assignment.id);
        setError('');

        try {
            const response = await classroomAPI.startClassroomQuizAttempt(assignment.id);
            // Redirect to quiz session
            router.push(`/quiz/${response.session_id}`);
        } catch (err) {
            console.error('Error starting quiz:', err);
            setError(err.response?.data?.error || 'Failed to start quiz');
        } finally {
            setLoading(null);
        }
    };

    const getModeColor = (mode) => {
        return mode === 'practice'
            ? 'bg-blue-100 text-blue-800 border-blue-200'
            : 'bg-purple-100 text-purple-800 border-purple-200';
    };

    const getModeIcon = (mode) => {
        return mode === 'practice' ? <Target className="w-4 h-4" /> : <Trophy className="w-4 h-4" />;
    };

    if (!classroom.quizzes || classroom.quizzes.length === 0) {
        return null;
    }

    return (
        <div className="bg-[#13161f] rounded-xl shadow-sm border border-white/5 overflow-hidden mb-6">
            {/* Classroom Header */}
            <div className="bg-gradient-to-r from-primary/20 to-primary/5 border-b border-white/5 px-6 py-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="text-lg font-bold text-white tracking-tight">{classroom.classroom_name}</h3>
                        <p className="text-sm text-slate-400">Instructor: <span className="text-primary font-medium">{classroom.teacher_name}</span></p>
                    </div>
                    <div className="bg-primary/20 border border-primary/20 px-3 py-1 rounded-full">
                        <span className="text-primary-foreground text-sm font-bold">{classroom.quizzes.length} Quiz{classroom.quizzes.length !== 1 ? 'zes' : ''}</span>
                    </div>
                </div>
            </div>

            {/* Quizzes List */}
            <div className="divide-y divide-white/5">
                {classroom.quizzes.map((assignment) => (
                    <div key={assignment.id} className="p-6 hover:bg-white/5 transition-colors">
                        <div className="flex items-start justify-between gap-4">
                            {/* Quiz Info */}
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="p-2 rounded-lg bg-white/5 text-slate-400">
                                        <BookOpen className="w-5 h-5" />
                                    </div>
                                    <h4 className="text-lg font-bold text-white">{assignment.quiz_title}</h4>
                                </div>
                                {/* Mode Badge below title */}
                                <div className="ml-11 mb-2">
                                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${assignment.quiz_mode === 'practice'
                                        ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                        : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                                        }`}>
                                        {getModeIcon(assignment.quiz_mode)}
                                        {assignment.quiz_mode === 'practice' ? 'Practice' : 'Assessment'}
                                    </span>
                                    {/* Edit/Delete only for practice quizzes */}
                                    {assignment.quiz_mode === 'practice' && (
                                        <span className="inline-flex items-center gap-1 ml-2">
                                            <button className="p-1 rounded-full bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20" title="Edit Practice Quiz">
                                                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l2 2-8 8-2 2v-2l8-8z"/><path d="M2 12v2h2"/></svg>
                                            </button>
                                            <button className="p-1 rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20" title="Delete Practice Quiz">
                                                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h10"/><path d="M6 6v6"/><path d="M10 6v6"/><path d="M5 4h6l1 2H4l1-2z"/></svg>
                                            </button>
                                        </span>
                                    )}
                                </div>
                                {assignment.quiz_description && (
                                    <p className="text-sm text-slate-400 mb-4 ml-11">{assignment.quiz_description}</p>
                                )}

                                {/* Stats Row */}
                                <div className="flex items-center gap-6 text-sm ml-11">
                                    {/* Attempts */}
                                    <div className="flex items-center gap-2">
                                        <CheckCircle className="w-4 h-4 text-slate-500" />
                                        <span className="text-slate-400">
                                            <span className="font-bold text-white">{assignment.attempts_used}</span>
                                            {assignment.attempts_remaining === -1
                                                ? ' / Unlimited'
                                                : ` / ${assignment.attempts_used + assignment.attempts_remaining}`
                                            } attempts
                                        </span>
                                    </div>

                                    {/* Last Score */}
                                    {assignment.last_attempt_score !== null && (
                                        <div className="flex items-center gap-2">
                                            <Trophy className="w-4 h-4 text-yellow-500" />
                                            <span className="text-slate-400">
                                                Last Score: <span className="font-bold text-white">{assignment.last_attempt_score}%</span>
                                            </span>
                                        </div>
                                    )}

                                    {/* Due Date */}
                                    {assignment.due_date && (
                                        <div className="flex items-center gap-2">
                                            <Clock className="w-4 h-4 text-slate-500" />
                                            <span className="text-slate-400">
                                                Due: {new Date(assignment.due_date).toLocaleDateString('en-GB')}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Action Button */}
                            <div className="flex flex-col items-end gap-2">
                                <button
                                    onClick={() => handleStartQuiz(assignment)}
                                    disabled={loading === assignment.id || assignment.attempts_remaining === 0}
                                    className={`px-6 py-2.5 rounded-xl font-bold text-sm transition-all shadow-lg ${assignment.attempts_remaining === 0
                                        ? 'bg-white/5 text-slate-500 cursor-not-allowed shadow-none'
                                        : assignment.quiz_mode === 'practice'
                                            ? 'bg-blue-600 text-white hover:bg-blue-500 shadow-blue-900/20'
                                            : 'bg-purple-600 text-white hover:bg-purple-500 shadow-purple-900/20'
                                        }`}
                                >
                                    {loading === assignment.id ? (
                                        <span className="flex items-center gap-2">
                                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            Starting...
                                        </span>
                                    ) : assignment.attempts_remaining === 0 ? (
                                        'No Attempts Left'
                                    ) : assignment.attempts_used > 0 ? (
                                        'Retake Quiz'
                                    ) : (
                                        'Start Quiz'
                                    )}
                                </button>

                                {assignment.attempts_remaining > 0 && assignment.attempts_remaining !== -1 && (
                                    <span className="text-xs text-slate-500 font-medium">
                                        {assignment.attempts_remaining} attempt{assignment.attempts_remaining !== 1 ? 's' : ''} left
                                    </span>
                                )}
                            </div>
                        </div>

                        {error && (
                            <div className="mt-4 ml-11 flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-lg">
                                <AlertCircle className="w-4 h-4" />
                                {error}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
