'use client';

import { useState, useEffect } from 'react';
import { quizAPI } from '@/lib/api';
import { Loader2, CheckCircle, XCircle, AlertTriangle, FileText, Search, User, Clock, Brain } from 'lucide-react';
import Toast from '@/components/ui/Toast';

export default function GradingPage() {
    const [loading, setLoading] = useState(true);
    const [responses, setResponses] = useState([]);
    const [selectedResponse, setSelectedResponse] = useState(null);
    const [toast, setToast] = useState(null);

    // Grading Form State
    const [teacherScore, setTeacherScore] = useState('');
    const [teacherFeedback, setTeacherFeedback] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        loadPendingReviews();
    }, []);

    const loadPendingReviews = async () => {
        setLoading(true);
        try {
            const data = await quizAPI.getPendingReviews();
            setResponses(data.pending_reviews || []);
        } catch (err) {
            console.error('Failed to load reviews:', err);
            setToast({ type: 'error', title: 'Error', message: 'Failed to load pending reviews.' });
        } finally {
            setLoading(false);
        }
    };

    const handleOpenGrading = (response) => {
        setSelectedResponse(response);
        setTeacherScore(response.ai_score || ''); // Pre-fill with AI score if available
        setTeacherFeedback(response.ai_feedback ? `AI Feedback: ${response.ai_feedback}\n\nTeacher Feedback: ` : '');
    };

    const handleSubmitGrade = async () => {
        if (!selectedResponse) return;

        setIsSubmitting(true);
        try {
            await quizAPI.submitTeacherReview(selectedResponse.response_id, {
                teacher_score: teacherScore,
                teacher_feedback: teacherFeedback,
                finalize: true
            });

            setToast({ type: 'success', title: 'Graded', message: 'Response graded successfully!' });
            setSelectedResponse(null);
            loadPendingReviews(); // Refresh list
        } catch (err) {
            setToast({ type: 'error', title: 'Error', message: err.response?.data?.error || 'Failed to submit grade.' });
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8">
            {toast && <Toast {...toast} onClose={() => setToast(null)} />}

            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-foreground">Teacher Grading</h1>
                    <p className="text-muted-foreground mt-2">Review and grade pending short answer responses.</p>
                </div>
                <button
                    onClick={loadPendingReviews}
                    className="p-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-colors"
                >
                    Refresh List
                </button>
            </div>

            {loading ? (
                <div className="flex justify-center p-12">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                </div>
            ) : responses.length === 0 ? (
                <div className="text-center p-12 bg-card border rounded-2xl shadow-sm">
                    <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                    <h3 className="text-xl font-semibold">All Caught Up!</h3>
                    <p className="text-muted-foreground">No pending responses to grade.</p>
                </div>
            ) : (
                <div className="grid gap-6">
                    {responses.map(response => (
                        <div key={response.response_id} className="bg-card border rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <h3 className="font-semibold text-lg">{response.quiz_title}</h3>
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                                        <User className="w-4 h-4" />
                                        {response.student_name}
                                        <span className="mx-2">•</span>
                                        <Clock className="w-4 h-4" />
                                        {new Date(response.submitted_at).toLocaleDateString('en-GB')}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-xs font-semibold">
                                    <Brain className="w-3 h-3" />
                                    AI Score: {response.ai_score ? response.ai_score.toFixed(1) : 'N/A'}
                                </div>
                            </div>

                            <div className="bg-secondary/30 p-4 rounded-lg mb-4">
                                <p className="font-medium text-sm text-muted-foreground mb-2">Question:</p>
                                <p className="text-foreground">{response.question_text}</p>
                            </div>

                            <div className="flex justify-end">
                                <button
                                    onClick={() => handleOpenGrading(response)}
                                    className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
                                >
                                    Grade Response
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Grading Modal */}
            {selectedResponse && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedResponse(null)} />
                    <div className="relative bg-card w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
                        <div className="p-6 border-b flex justify-between items-center">
                            <h2 className="text-xl font-bold">Grade Response</h2>
                            <button onClick={() => setSelectedResponse(null)} className="text-muted-foreground hover:text-foreground">
                                <XCircle className="w-6 h-6" />
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto space-y-6">
                            {/* Student Answer Section */}
                            <div>
                                <h3 className="font-semibold mb-2 flex items-center gap-2">
                                    <FileText className="w-4 h-4" /> Student Answer
                                </h3>
                                <div className="p-4 bg-secondary/20 border rounded-xl text-lg leading-relaxed whitespace-pre-wrap">
                                    {selectedResponse.student_answer}
                                </div>
                                <div className="mt-2 text-xs text-muted-foreground text-right">
                                    Word Count: {selectedResponse.word_count}
                                </div>
                            </div>

                            {/* AI Analysis Section */}
                            {selectedResponse.ai_score !== null && (
                                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-xl">
                                    <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2 flex items-center gap-2">
                                        <Brain className="w-4 h-4" /> AI Analysis
                                    </h3>
                                    <div className="grid grid-cols-2 gap-4 mb-3">
                                        <div>
                                            <span className="text-xs text-blue-700 dark:text-blue-300 uppercase font-bold">Recommended Score</span>
                                            <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">{selectedResponse.ai_score.toFixed(1)}/10</p>
                                        </div>
                                        <div>
                                            <span className="text-xs text-blue-700 dark:text-blue-300 uppercase font-bold">Similarity</span>
                                            <p className="text-lg font-medium text-blue-900 dark:text-blue-100">{(selectedResponse.similarity_score * 100).toFixed(0)}% Match</p>
                                        </div>
                                    </div>
                                    <p className="text-sm text-blue-800 dark:text-blue-200">{selectedResponse.ai_feedback}</p>
                                </div>
                            )}

                            {/* Grading Form */}
                            <div className="space-y-4 pt-4 border-t">
                                <div>
                                    <label className="block text-sm font-semibold mb-1">Final Score (0-10)</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="10"
                                        step="0.1"
                                        value={teacherScore}
                                        onChange={(e) => setTeacherScore(e.target.value)}
                                        className="w-full p-3 bg-background border rounded-lg focus:ring-2 focus:ring-primary outline-none"
                                        placeholder="Enter score 0-10"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-semibold mb-1">Feedback</label>
                                    <textarea
                                        value={teacherFeedback}
                                        onChange={(e) => setTeacherFeedback(e.target.value)}
                                        className="w-full p-3 bg-background border rounded-lg focus:ring-2 focus:ring-primary outline-none h-32 resize-none"
                                        placeholder="Add constructive feedback for the student..."
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="p-6 border-t bg-secondary/10 flex justify-end gap-3">
                            <button
                                onClick={() => setSelectedResponse(null)}
                                className="px-5 py-2 text-muted-foreground hover:text-foreground font-medium"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSubmitGrade}
                                disabled={isSubmitting || !teacherScore}
                                className="px-8 py-2 bg-primary text-primary-foreground rounded-lg font-bold hover:bg-primary/90 transition-all disabled:opacity-50 flex items-center gap-2"
                            >
                                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                Submit Grade
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
