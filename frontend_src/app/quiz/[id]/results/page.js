'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { quizAPI } from '@/lib/api';
import { Loader2, Download, ArrowLeft, TrendingUp, Clock, Target, Award, Shield, Brain, FileText } from 'lucide-react';
import Toast from '@/components/ui/Toast';

export default function QuizResultsPage() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id;

    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [toast, setToast] = useState(null);
    const [downloading, setDownloading] = useState(false);

    useEffect(() => {
        loadResults();
    }, [sessionId]);

    const loadResults = async () => {
        setLoading(true);
        try {
            const data = await quizAPI.getResults(sessionId);
            setResults(data);
        } catch (err) {
            console.error(err);
            setError('Failed to load results. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const downloadPDF = async () => {
        setDownloading(true);
        try {
            const blob = await quizAPI.downloadReport(sessionId);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `quiz_report_${sessionId}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            setToast({ type: 'success', title: 'Success', message: 'Report downloaded successfully!' });
        } catch (err) {
            console.error(err);
            setToast({ type: 'error', title: 'Error', message: 'Failed to download report.' });
        } finally {
            setDownloading(false);
        }
    };

    const getGradeColor = (grade) => {
        const colors = {
            'A': 'text-green-600 dark:text-green-400',
            'B': 'text-blue-600 dark:text-blue-400',
            'C': 'text-yellow-600 dark:text-yellow-400',
            'D': 'text-orange-600 dark:text-orange-400',
            'F': 'text-red-600 dark:text-red-400'
        };
        return colors[grade] || 'text-foreground';
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (error || !results) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-8 bg-background">
                <p className="text-xl text-destructive mb-4">{error || 'No results found'}</p>
                <button
                    onClick={() => router.back()}
                    className="px-4 py-2 bg-secondary rounded-lg text-foreground border border-border"
                >
                    Go Back
                </button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-secondary/30 py-8 px-4">
            {toast && <Toast {...toast} onClose={() => setToast(null)} />}

            <div className="max-w-5xl mx-auto">
                {/* Header */}
                <div className="bg-card border border-border rounded-2xl p-8 mb-6 shadow-sm">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h1 className="text-4xl font-bold text-primary mb-2">ADAPTIVE AI QUIZ PLATFORM</h1>
                            <p className="text-muted-foreground">Quiz Results Report</p>
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={downloadPDF}
                                disabled={downloading}
                                className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
                            >
                                {downloading ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Download className="w-4 h-4" />
                                )}
                                Download PDF
                            </button>
                            <button
                                onClick={() => router.push('/dashboard/classrooms')}
                                className="flex items-center gap-2 px-4 py-2 bg-secondary text-foreground rounded-lg border border-border hover:bg-secondary/80"
                            >
                                <ArrowLeft className="w-4 h-4" />
                                Back
                            </button>
                        </div>
                    </div>

                    {/* Student Info */}
                    <div className="grid grid-cols-2 gap-4 bg-secondary/50 p-4 rounded-xl">
                        <div>
                            <span className="text-sm text-muted-foreground">Student Name:</span>
                            <p className="font-semibold text-foreground">{results.student_name}</p>
                        </div>
                        <div>
                            <span className="text-sm text-muted-foreground">Email:</span>
                            <p className="font-semibold text-foreground">{results.student_email}</p>
                        </div>
                        <div>
                            <span className="text-sm text-muted-foreground">Quiz Title:</span>
                            <p className="font-semibold text-foreground">{results.quiz_title}</p>
                        </div>
                        <div>
                            <span className="text-sm text-muted-foreground">Date Taken:</span>
                            <p className="font-semibold text-foreground">
                                {new Date(results.date_taken).toLocaleDateString('en-GB')}
                            </p>
                        </div>
                        <div>
                            <span className="text-sm text-muted-foreground">Attempt Number:</span>
                            <p className="font-semibold text-foreground">{results.attempt_number}</p>
                        </div>
                    </div>
                </div>

                {/* Performance Summary */}
                <div className="bg-card border border-border rounded-2xl p-8 mb-6 shadow-sm">
                    <h2 className="text-2xl font-bold text-primary mb-6">Performance Summary</h2>

                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <tbody>
                                <tr className="border-b border-border">
                                    <td className="py-4 px-4 bg-primary/10 font-semibold text-foreground">Overall Score</td>
                                    <td className="py-4 px-4 font-bold text-foreground">{results.overall_score}%</td>
                                    <td className={`py-4 px-4 font-bold text-2xl ${getGradeColor(results.grade)}`}>{results.grade}</td>
                                </tr>
                                <tr className="border-b border-border">
                                    <td className="py-4 px-4 text-foreground">Accuracy</td>
                                    <td className="py-4 px-4 font-semibold text-foreground" colSpan="2">{results.accuracy}%</td>
                                </tr>
                                <tr className="border-b border-border">
                                    <td className="py-4 px-4 text-foreground">Correct Answers</td>
                                    <td className="py-4 px-4 font-semibold text-green-600 dark:text-green-400" colSpan="2">{results.correct_answers}</td>
                                </tr>
                                <tr className="border-b border-border">
                                    <td className="py-4 px-4 text-foreground">Incorrect Answers</td>
                                    <td className="py-4 px-4 font-semibold text-red-600 dark:text-red-400" colSpan="2">{results.incorrect_answers}</td>
                                </tr>
                                <tr className="border-b border-border">
                                    <td className="py-4 px-4 text-foreground">Time Taken</td>
                                    <td className="py-4 px-4 font-semibold text-foreground" colSpan="2">{results.time_taken_minutes} minutes</td>
                                </tr>
                                <tr>
                                    <td className="py-4 px-4 text-foreground">Avg Response Time</td>
                                    <td className="py-4 px-4 font-semibold text-foreground" colSpan="2">{results.avg_response_time_seconds} seconds</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Topic Performance Breakdown */}
                {results.topic_performance && results.topic_performance.length > 0 && (
                    <div className="bg-card border border-border rounded-2xl p-8 mb-6 shadow-sm">
                        <h2 className="text-2xl font-bold text-primary mb-6">Topic Performance Breakdown</h2>

                        <div className="space-y-4">
                            {results.topic_performance.map((topic, idx) => (
                                <div key={idx}>
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-foreground font-medium">{topic.topic}</span>
                                        <span className="text-foreground font-bold">{topic.score}%</span>
                                    </div>
                                    <div className="h-8 bg-secondary rounded-lg overflow-hidden">
                                        <div
                                            className="h-full bg-primary flex items-center justify-center text-primary-foreground font-semibold transition-all duration-500"
                                            style={{ width: `${topic.score}%` }}
                                        >
                                            {topic.score > 15 && `${topic.score}%`}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Behavior & Integrity Summary */}
                <div className="bg-card border border-border rounded-2xl p-8 mb-6 shadow-sm">
                    <h2 className="text-2xl font-bold text-primary mb-6">Behavior & Integrity Summary</h2>

                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <tbody>
                                <tr className="border-b border-border">
                                    <td className="py-4 px-4 bg-purple-100 dark:bg-purple-900/20 font-semibold text-foreground">Behavior Score</td>
                                    <td className="py-4 px-4 font-bold text-foreground">{results.behavior_score}/100</td>
                                    <td className="py-4 px-4 font-bold text-purple-600 dark:text-purple-400">{results.overall_conduct}</td>
                                </tr>
                                <tr className="border-b border-border">
                                    <td className="py-4 px-4 text-foreground">Tab Switches</td>
                                    <td className="py-4 px-4 font-semibold text-foreground" colSpan="2">{results.tab_switches}</td>
                                </tr>
                                <tr className="border-b border-border">
                                    <td className="py-4 px-4 text-foreground">Hesitations</td>
                                    <td className="py-4 px-4 font-semibold text-foreground" colSpan="2">{results.hesitations}</td>
                                </tr>
                                <tr>
                                    <td className="py-4 px-4 text-foreground">Overall Conduct</td>
                                    <td className="py-4 px-4 font-semibold text-foreground" colSpan="2">{results.overall_conduct}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* AI-Powered Insights */}
                <div className="bg-card border border-border rounded-2xl p-8 mb-6 shadow-sm">
                    <h2 className="text-2xl font-bold text-primary mb-6">AI-Powered Insights</h2>

                    <div className="space-y-4">
                        <div className="flex items-center gap-3 p-4 bg-secondary/50 rounded-xl">
                            <Brain className="w-6 h-6 text-primary" />
                            <div>
                                <p className="text-sm text-muted-foreground">Detected Learning Mindset:</p>
                                <p className="font-bold text-foreground capitalize">{results.detected_mindset}</p>
                            </div>
                        </div>

                        {results.recommendations && results.recommendations.length > 0 && (
                            <div className="p-4 bg-secondary/50 rounded-xl">
                                <p className="font-semibold text-foreground mb-3">Recommendations for Improvement:</p>
                                <ul className="list-disc list-inside space-y-2 text-muted-foreground">
                                    {results.recommendations.map((rec, idx) => (
                                        <li key={idx}>{rec}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>

                {/* Question-by-Question Review */}
                {results.responses && results.responses.length > 0 && (
                    <div className="bg-card border border-border rounded-2xl p-8 shadow-sm">
                        <h2 className="text-2xl font-bold text-primary mb-6">Question-by-Question Review</h2>

                        <div className="space-y-6">
                            {results.responses.map((response, idx) => (
                                <div
                                    key={idx}
                                    className={`p-6 rounded-xl border-2 ${response.is_correct
                                        ? 'border-green-500/30 bg-green-50 dark:bg-green-900/10'
                                        : 'border-red-500/30 bg-red-50 dark:bg-red-900/10'
                                        }`}
                                >
                                    <div className="flex justify-between items-start mb-4">
                                        <h3 className="font-bold text-lg text-foreground">Question {response.question_number}</h3>
                                        <div className="flex items-center gap-2">
                                            {response.is_correct ? (
                                                <span className="px-3 py-1 bg-green-500 text-white rounded-full text-sm font-semibold">
                                                    ✓ Correct
                                                </span>
                                            ) : (
                                                <span className="px-3 py-1 bg-red-500 text-white rounded-full text-sm font-semibold">
                                                    ✗ Incorrect
                                                </span>
                                            )}
                                            <span className="text-sm text-muted-foreground">
                                                {response.time_taken}s
                                            </span>
                                        </div>
                                    </div>

                                    <p className="text-foreground mb-4 leading-relaxed">{response.question_text}</p>

                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div className="p-3 bg-background rounded-lg">
                                            <p className="text-sm text-muted-foreground mb-1">Your Answer:</p>
                                            <p className="font-semibold text-foreground">{response.your_answer}</p>
                                        </div>
                                        {response.correct_answer && (
                                            <div className="p-3 bg-background rounded-lg">
                                                <p className="text-sm text-muted-foreground mb-1">Correct Answer:</p>
                                                <p className="font-semibold text-green-600 dark:text-green-400">{response.correct_answer}</p>
                                            </div>
                                        )}
                                    </div>

                                    {response.explanation && (
                                        <div className="p-4 bg-background rounded-lg">
                                            <p className="text-sm font-semibold text-foreground mb-2">Explanation:</p>
                                            <p className="text-muted-foreground leading-relaxed">{response.explanation}</p>
                                        </div>
                                    )}

                                    {response.ai_feedback && (
                                        <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800 rounded-lg">
                                            <p className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                                                <Brain className="w-4 h-4 text-purple-600" />
                                                AI Feedback:
                                            </p>
                                            <p className="text-muted-foreground">{response.ai_feedback}</p>
                                            {response.ai_score !== null && (
                                                <p className="text-xs text-purple-600 font-bold mt-1">Score: {response.ai_score}/100</p>
                                            )}
                                        </div>
                                    )}

                                    {response.teacher_feedback && (
                                        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg">
                                            <p className="text-sm font-semibold text-foreground mb-2">Teacher Feedback:</p>
                                            <p className="text-muted-foreground">{response.teacher_feedback}</p>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
