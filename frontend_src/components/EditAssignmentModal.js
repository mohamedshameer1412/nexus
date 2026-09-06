'use client';

import { useState, useEffect } from 'react';
import { classroomAPI } from '@/lib/api';
import { X, Calendar, AlertCircle, Save } from 'lucide-react';
import { quizAPI } from '@/lib/api'; // Import quizAPI if needed for something, but here we update assignment

export default function EditAssignmentModal({ isOpen = true, onClose, assignment, onSuccess }) {
    const [settings, setSettings] = useState({
        allow_unlimited_attempts: true,
        show_immediate_feedback: true,
        max_attempts: 3,
        strict_time_limit: true,
        enable_proctoring: false,
        show_results_after_due: true,
        due_date: '',
        quiz_mode: 'practice'
    });
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (assignment) {
            setSettings({
                allow_unlimited_attempts: assignment.allow_unlimited_attempts,
                show_immediate_feedback: assignment.show_immediate_feedback,
                max_attempts: assignment.max_attempts,
                strict_time_limit: assignment.strict_time_limit,
                enable_proctoring: assignment.enable_proctoring,
                show_results_after_due: assignment.show_results_after_due,
                due_date: assignment.due_date ? assignment.due_date.slice(0, 16) : '', // format for datetime-local
                quiz_mode: assignment.quiz_mode
            });
        }
    }, [assignment]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setError('');

        try {
            // We use api.patch to update assignment
            // Need to expose a method in api.js for this, or use generic axio request if strictly correct
            // But let's assume classroomAPI.updateClassroomQuizAssignment exists or we add it.
            // I will add it to api.js first or use raw api call.
            // Wait, I can use classroomAPI.updateClassroomQuizAssignment which I will add.

            const payload = {
                ...settings,
                max_attempts: Number(settings.max_attempts) > 0 ? Number(settings.max_attempts) : 1,
                due_date: settings.due_date || null
            };

            await classroomAPI.updateClassroomQuizAssignment(assignment.id, payload);
            onSuccess?.();
            onClose();
        } catch (err) {
            console.error('Error updating assignment:', err);
            setError(err.response?.data?.error || 'Failed to update assignment');
        } finally {
            setSubmitting(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-card w-full max-w-md shadow-2xl rounded-2xl border border-border">
                {/* Header */}
                <div className="bg-card border-b border-border px-6 py-4 flex items-center justify-between rounded-t-2xl">
                    <div>
                        <h2 className="text-xl font-bold text-foreground">Edit Assignment</h2>
                        <p className="text-sm text-muted-foreground">{assignment?.quiz_title} ({settings.quiz_mode})</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-accent text-muted-foreground rounded-lg transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Settings based on mode */}
                    <div className="space-y-4">
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

                        {settings.quiz_mode === 'practice' ? (
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
                                    <div className="ml-7">
                                        <label className="block text-xs font-semibold text-muted-foreground mb-1">
                                            Attempts Allowed
                                        </label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="50"
                                            value={settings.max_attempts}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                if (/^\d*$/.test(val)) {
                                                    setSettings({ ...settings, max_attempts: val });
                                                }
                                            }}
                                            className="w-full max-w-[120px] px-3 py-2 border border-input bg-background rounded-lg focus:ring-2 focus:ring-ring outline-none text-sm text-foreground"
                                        />
                                    </div>
                                )}
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
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            if (/^\d*$/.test(val)) {
                                                setSettings({ ...settings, max_attempts: val });
                                            }
                                        }}
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
                            className="px-4 py-2 text-muted-foreground hover:bg-accent rounded-lg font-medium transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={submitting}
                            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-semibold hover:bg-primary/90 transition-colors flex items-center gap-2 disabled:opacity-50"
                        >
                            <Save className="w-4 h-4" />
                            {submitting ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
