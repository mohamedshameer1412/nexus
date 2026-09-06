'use client';

import { useState, useEffect } from 'react';
import { quizAPI, classroomAPI } from '@/lib/api';
import { X, Target, Trophy, Calendar, AlertCircle } from 'lucide-react';

export default function AssignQuizModal({ isOpen = true, onClose, classroom, onSuccess }) {
    const [quizzes, setQuizzes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedQuiz, setSelectedQuiz] = useState(null);
    const [quizMode, setQuizMode] = useState('practice');
    const [settings, setSettings] = useState({
        allow_unlimited_attempts: true,
        show_immediate_feedback: true,
        max_attempts: 3,
        strict_time_limit: true,
        enable_proctoring: false,
        shuffle_questions: true,
        show_results_after_due: true,
        due_date: ''
    });
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (isOpen) {
            fetchQuizzes();
        }
    }, [isOpen]);

    const fetchQuizzes = async () => {
        try {
            const data = await quizAPI.getQuizzes();
            setQuizzes(Array.isArray(data) ? data : data.results || []);
        } catch (err) {
            console.error('Error fetching quizzes:', err);
            setError('Failed to load quizzes');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!selectedQuiz) {
            setError('Please select a quiz');
            return;
        }

        setSubmitting(true);
        setError('');

        try {
            const payload = {
                classroom: classroom.id,
                quiz: selectedQuiz.id,
                quiz_mode: quizMode,
                is_active: true,
                ...settings,
                // In assessment mode, unlimited attempts are not allowed by design in this flow
                allow_unlimited_attempts: quizMode === 'assessment' ? false : settings.allow_unlimited_attempts,
                max_attempts: Number(settings.max_attempts) > 0 ? Number(settings.max_attempts) : 1,
                due_date: settings.due_date || null
            };

            await classroomAPI.createClassroomQuizAssignment(payload);
            onSuccess?.();
            onClose();
        } catch (err) {
            console.error('Error assigning quiz:', err);
            let errorMessage = 'Failed to assign quiz';

            if (err.response?.data) {
                const data = err.response.data;
                if (data.error) {
                    errorMessage = data.error;
                } else if (data.non_field_errors) {
                    errorMessage = Array.isArray(data.non_field_errors) ? data.non_field_errors.join(', ') : data.non_field_errors;
                    if (JSON.stringify(errorMessage).includes('make a unique set')) {
                        errorMessage = 'This quiz is already assigned to this classroom.';
                    }
                } else {
                    // formatting field errors
                    const entries = Object.entries(data);
                    if (entries.length > 0) {
                        const [key, val] = entries[0];
                        const msg = Array.isArray(val) ? val[0] : val;
                        errorMessage = `${key}: ${msg}`;
                    }
                }
            }
            setError(errorMessage);
        } finally {
            setSubmitting(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-card w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl rounded-2xl border border-border">
                {/* Header */}
                <div className="sticky top-0 bg-card border-b border-border px-6 py-4 flex items-center justify-between z-10">
                    <div>
                        <h2 className="text-xl font-bold text-foreground">Assign Quiz</h2>
                        <p className="text-sm text-muted-foreground">To: {classroom?.name}</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-accent text-muted-foreground rounded-lg transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Quiz Selection */}
                    <div>
                        <label className="block text-sm font-semibold text-foreground mb-2">
                            Select Quiz *
                        </label>
                        {loading ? (
                            <div className="text-center py-8">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 gap-3 max-h-60 overflow-y-auto">
                                {quizzes.map((quiz) => (
                                    <button
                                        key={quiz.id}
                                        type="button"
                                        onClick={() => setSelectedQuiz(quiz)}
                                        className={`text-left p-4 rounded-lg border-2 transition-all ${selectedQuiz?.id === quiz.id
                                            ? 'border-primary bg-primary/5 dark:bg-primary/20'
                                            : 'border-border hover:border-primary/50'
                                            }`}
                                    >
                                        <h4 className="font-semibold text-foreground">{quiz.title}</h4>
                                        <p className="text-sm text-muted-foreground mt-1">{quiz.total_questions} questions</p>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Quiz Mode */}
                    <div>
                        <label className="block text-sm font-semibold text-foreground mb-3">
                            Quiz Mode *
                        </label>
                        <div className="grid grid-cols-2 gap-4">
                            <button
                                type="button"
                                onClick={() => setQuizMode('practice')}
                                className={`p-4 rounded-xl border-2 transition-all ${quizMode === 'practice'
                                    ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
                                    : 'border-border hover:bg-accent'
                                    }`}
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <Target className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                    <span className="font-semibold text-foreground">Practice</span>
                                </div>
                                <p className="text-xs text-muted-foreground">Unlimited attempts, immediate feedback</p>
                            </button>

                            <button
                                type="button"
                                onClick={() => setQuizMode('assessment')}
                                className={`p-4 rounded-xl border-2 transition-all ${quizMode === 'assessment'
                                    ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/20'
                                    : 'border-border hover:bg-accent'
                                    }`}
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <Trophy className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                                    <span className="font-semibold text-foreground">Assessment</span>
                                </div>
                                <p className="text-xs text-muted-foreground">Limited attempts, strict timing</p>
                            </button>
                        </div>
                    </div>

                    {/* Settings */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-foreground">Settings</h3>

                        {/* Common Settings */}
                        <label className="flex items-center gap-3">
                            <input
                                type="checkbox"
                                checked={settings.enable_proctoring}
                                onChange={(e) => setSettings({ ...settings, enable_proctoring: e.target.checked })}
                                className="w-4 h-4 text-primary rounded border-input"
                            />
                            <span className="text-sm text-foreground">Enable proctoring</span>
                        </label>

                        <label className="flex items-center gap-3">
                            <input
                                type="checkbox"
                                checked={settings.shuffle_questions}
                                onChange={(e) => setSettings({ ...settings, shuffle_questions: e.target.checked })}
                                className="w-4 h-4 text-primary rounded border-input"
                            />
                            <span className="text-sm text-foreground">Shuffle questions for everyone</span>
                        </label>

                        {quizMode === 'practice' ? (
                            <>
                                <label className="flex items-center gap-3">
                                    <input
                                        type="checkbox"
                                        checked={settings.allow_unlimited_attempts}
                                        onChange={(e) => setSettings({ ...settings, allow_unlimited_attempts: e.target.checked })}
                                        className="w-4 h-4 text-primary rounded border-input"
                                    />
                                    <span className="text-sm text-foreground">Allow unlimited attempts</span>
                                </label>

                                {!settings.allow_unlimited_attempts && (
                                    <div className="ml-7 mb-3 animate-in slide-in-from-top-2 duration-200">
                                        <label className="block text-xs font-semibold text-muted-foreground mb-1">
                                            Attempts Allowed
                                        </label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="50"
                                            value={settings.max_attempts}
                                            onChange={(e) => setSettings({ ...settings, max_attempts: e.target.value === '' ? '' : parseInt(e.target.value) })}
                                            className="w-full max-w-[120px] px-3 py-2 border border-input bg-background rounded-lg focus:ring-2 focus:ring-ring outline-none text-sm text-foreground"
                                        />
                                    </div>
                                )}
                                <label className="flex items-center gap-3">
                                    <input
                                        type="checkbox"
                                        checked={settings.show_immediate_feedback}
                                        onChange={(e) => setSettings({ ...settings, show_immediate_feedback: e.target.checked })}
                                        className="w-4 h-4 text-primary rounded border-input"
                                    />
                                    <span className="text-sm text-foreground">Show immediate feedback</span>
                                </label>
                            </>
                        ) : (
                            <>
                                <div>
                                    <label className="block text-sm text-foreground mb-2">Maximum Attempts</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="10"
                                        value={settings.max_attempts}
                                        onChange={(e) => setSettings({ ...settings, max_attempts: e.target.value === '' ? '' : parseInt(e.target.value) })}
                                        className="w-full px-4 py-2 border border-input bg-background rounded-lg focus:ring-2 focus:ring-ring outline-none text-foreground"
                                    />
                                </div>
                                <label className="flex items-center gap-3">
                                    <input
                                        type="checkbox"
                                        checked={settings.strict_time_limit}
                                        onChange={(e) => setSettings({ ...settings, strict_time_limit: e.target.checked })}
                                        className="w-4 h-4 text-primary rounded border-input"
                                    />
                                    <span className="text-sm text-foreground">Enforce strict time limit</span>
                                </label>
                            </>
                        )}

                        {/* Due Date */}
                        <div>
                            <label className="flex items-center gap-2 text-sm text-foreground mb-2">
                                <Calendar className="w-4 h-4" />
                                Due Date (Optional)
                            </label>
                            <input
                                type="datetime-local"
                                value={settings.due_date}
                                onChange={(e) => setSettings({ ...settings, due_date: e.target.value })}
                                className="w-full px-4 py-2 border border-input bg-background rounded-lg focus:ring-2 focus:ring-ring outline-none text-foreground"
                            />
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="flex items-center gap-2 p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-sm text-destructive">
                            <AlertCircle className="w-4 h-4" />
                            {error}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex justify-end gap-3 pt-4 border-t border-border">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-6 py-2.5 text-muted-foreground hover:bg-accent rounded-lg font-medium transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!selectedQuiz || submitting}
                            className={`px-6 py-2.5 rounded-lg font-semibold text-primary-foreground transition-all ${quizMode === 'practice'
                                ? 'bg-blue-600 hover:bg-blue-700'
                                : 'bg-purple-600 hover:bg-purple-700'
                                } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                            {submitting ? 'Assigning...' : 'Assign Quiz'}
                        </button>
                    </div>
                </form>
            </div >
        </div >
    );
}
