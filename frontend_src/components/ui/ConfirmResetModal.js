'use client';

import { AlertTriangle, Users, BookOpen, Trash2, X } from 'lucide-react';

export default function ConfirmResetModal({
    isOpen,
    onClose,
    onConfirm,
    resetType, // 'specific' | 'all_students' | 'all_quizzes' | 'all_all'
    studentName,
    quizTitle,
    sessionCount,
    loading = false
}) {
    if (!isOpen) return null;

    const getSeverity = () => {
        if (resetType === 'all_all') return 'danger';
        if (resetType === 'all_students' || resetType === 'all_quizzes') return 'warning';
        return 'info';
    };

    const severity = getSeverity();

    const colors = {
        danger: {
            bg: 'bg-red-500/10',
            border: 'border-red-500/30',
            text: 'text-red-700 dark:text-red-400',
            icon: 'text-red-600 dark:text-red-400',
            button: 'bg-red-600 hover:bg-red-700 text-white'
        },
        warning: {
            bg: 'bg-orange-500/10',
            border: 'border-orange-500/30',
            text: 'text-orange-700 dark:text-orange-400',
            icon: 'text-orange-600 dark:text-orange-400',
            button: 'bg-orange-600 hover:bg-orange-700 text-white'
        },
        info: {
            bg: 'bg-blue-500/10',
            border: 'border-blue-500/30',
            text: 'text-blue-700 dark:text-blue-400',
            icon: 'text-blue-600 dark:text-blue-400',
            button: 'bg-blue-600 hover:bg-blue-700 text-white'
        }
    };

    const color = colors[severity];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-card rounded-2xl p-6 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-200 border border-border">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-xl ${color.bg} flex items-center justify-center`}>
                            <AlertTriangle className={`w-6 h-6 ${color.icon}`} />
                        </div>
                        <h2 className="text-xl font-bold text-foreground">Confirm Reset</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Warning Box */}
                <div className={`p-4 rounded-xl border ${color.bg} ${color.border} mb-4`}>
                    <p className={`font-semibold mb-3 ${color.text}`}>
                        You are about to reset:
                    </p>
                    <ul className={`space-y-2 text-sm ${color.text}`}>
                        {studentName && (
                            <li className="flex items-center gap-2">
                                <Users className="w-4 h-4" />
                                <span>Student: <strong>{studentName}</strong></span>
                            </li>
                        )}
                        {quizTitle && (
                            <li className="flex items-center gap-2">
                                <BookOpen className="w-4 h-4" />
                                <span>Quiz: <strong>{quizTitle}</strong></span>
                            </li>
                        )}
                        {sessionCount !== undefined && (
                            <li className="flex items-center gap-2">
                                <Trash2 className="w-4 h-4" />
                                <span>Sessions to delete: <strong>{sessionCount}</strong></span>
                            </li>
                        )}
                    </ul>
                </div>

                {/* Warning Message */}
                <div className="bg-secondary/50 border border-border rounded-lg p-3 mb-6">
                    <p className="text-sm text-muted-foreground">
                        <strong>⚠️ This action cannot be undone.</strong>
                        <br />
                        {resetType === 'all_all' && 'All students will be able to retake all quizzes.'}
                        {resetType === 'all_students' && 'All students will be able to retake this quiz.'}
                        {resetType === 'all_quizzes' && 'This student will be able to retake all quizzes.'}
                        {resetType === 'specific' && 'This student will be able to retake this quiz.'}
                    </p>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                    <button
                        onClick={onClose}
                        disabled={loading}
                        className="flex-1 px-4 py-3 border-2 border-border rounded-xl hover:bg-secondary text-foreground font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={loading}
                        className={`flex-1 px-4 py-3 rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${color.button} flex items-center justify-center gap-2`}
                    >
                        {loading ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Resetting...
                            </>
                        ) : (
                            <>
                                <Trash2 className="w-4 h-4" />
                                Reset Attempts
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
