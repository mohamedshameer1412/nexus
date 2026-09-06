'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { analyticsAPI, quizAPI } from '@/lib/api';
import {
    Trophy,
    Target,
    Clock,
    Brain,
    ArrowRight,
    Share2,
    CheckCircle2,
    XCircle,
    BarChart,
    Home,
    Download
} from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell, BarChart as RechartsBar, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import AlertModal from '@/components/ui/AlertModal';

export default function ResultsPage() {
    const params = useParams();
    const router = useRouter();
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(true);
    const [downloading, setDownloading] = useState(false);
    const [alertModal, setAlertModal] = useState({ isOpen: false, title: '', message: '', type: 'error' });

    useEffect(() => {
        const fetchResults = async () => {
            try {
                const data = await analyticsAPI.getSessionResults(params.id);
                setResults(data);
            } catch (error) {
                console.error('Error fetching results:', error);
                if (error.response?.status === 404) {
                    setAlertModal({
                        isOpen: true,
                        title: 'Not Found',
                        message: 'The quiz session results could not be found.',
                        type: 'error'
                    });
                } else if (error.response?.status === 403) {
                    setAlertModal({
                        isOpen: true,
                        title: 'Access Denied',
                        message: 'You do not have permission to view these results.',
                        type: 'error'
                    });
                }
            } finally {
                setLoading(false);
            }
        };
        fetchResults();
    }, [params.id]);

    const handleDownloadReport = async () => {
        setDownloading(true);
        try {
            const blob = await quizAPI.exportReport(params.id);

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `quiz_report_${params.id}.pdf`;
            document.body.appendChild(link);
            link.click();

            // Cleanup
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error downloading report:', error);
            setAlertModal({
                isOpen: true,
                title: 'Download Failed',
                message: 'Failed to download report. Please try again.',
                type: 'error'
            });
        } finally {
            setDownloading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (!results) return null;
    // Fallback for title if not present
    const displayTitle = results.quiz_title || results.session_title || results.title || 'Quiz Results';

    // Data for Charts
    const accuracyData = [
        { name: 'Correct', value: results.correct_answers, color: '#22c55e' },
        { name: 'Incorrect', value: results.incorrect_answers, color: '#ef4444' },
    ];

    // Calculate topic breakdown from questions
    const topicBreakdown = {};
    if (results.questions) {
        results.questions.forEach(q => {
            const topic = q.topic_name || 'General';
            if (!topicBreakdown[topic]) {
                topicBreakdown[topic] = { total: 0, correct: 0, accuracy: 0 };
            }
            topicBreakdown[topic].total++;
            if (q.is_correct) topicBreakdown[topic].correct++;
        });

        // Calculate accuracy
        Object.keys(topicBreakdown).forEach(topic => {
            const data = topicBreakdown[topic];
            data.accuracy = Math.round((data.correct / data.total) * 100);
        });
    }

    const topicData = Object.entries(topicBreakdown).map(([name, data]) => ({
        name,
        score: data.accuracy
    }));

    return (
        <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
            <AlertModal
                isOpen={alertModal.isOpen}
                onClose={() => setAlertModal(prev => ({ ...prev, isOpen: false }))}
                title={alertModal.title}
                message={alertModal.message}
                type={alertModal.type}
            />
            {/* Header */}
            <div className="text-center space-y-4">
                <div className="inline-flex p-4 rounded-full bg-primary/20 mb-4 animate-bounce">
                    <Trophy className="w-12 h-12 text-primary" />
                </div>
                <h1 className="text-4xl font-bold gradient-text">Quiz Complete!</h1>
                <p className="text-xl text-muted-foreground">
                    Great job! Here's how you performed on <span className="font-semibold text-primary">{displayTitle}</span>
                </p>
            </div>

            {/* Main Score Card */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass p-8 rounded-2xl md:col-span-2 flex flex-col justify-center items-center relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
                    <h2 className="text-6xl font-bold text-primary mb-2">
                        {Math.round(results.total_score)}
                        <span className="text-2xl text-muted-foreground ml-2">pts</span>
                    </h2>
                    <div className="flex items-center gap-2 mb-6">
                        <span className="px-3 py-1 rounded-full bg-secondary text-sm font-medium">
                            Student Ability: {results.student_ability ? results.student_ability.toFixed(2) : '0.00'} θ
                        </span>
                    </div>
                    <div className="grid grid-cols-3 gap-8 w-full max-w-md text-center">
                        <div>
                            <p className="text-muted-foreground text-sm mb-1">Accuracy</p>
                            <p className="text-xl font-bold">{Math.round(results.accuracy)}%</p>
                        </div>
                        <div>
                            <p className="text-muted-foreground text-sm mb-1">Time</p>
                            <p className="text-xl font-bold">{Math.round(results.avg_response_time)}s avg</p>
                        </div>
                        <div>
                            <p className="text-muted-foreground text-sm mb-1">Mindset</p>
                            <p className="text-xl font-bold capitalize">{results.detected_mindset || 'Neutral'}</p>
                        </div>
                    </div>
                </div>

                {/* Detailed Stats */}
                <div className="space-y-6">
                    <div className="glass p-6 rounded-xl flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-green-500/10 rounded-lg">
                                <CheckCircle2 className="w-5 h-5 text-green-500" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Correct</p>
                                <p className="font-bold">{results.correct_answers}</p>
                            </div>
                        </div>
                    </div>
                    <div className="glass p-6 rounded-xl flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-red-500/10 rounded-lg">
                                <XCircle className="w-5 h-5 text-red-500" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Incorrect</p>
                                <p className="font-bold">{results.incorrect_answers}</p>
                            </div>
                        </div>
                    </div>
                    <div className="glass p-6 rounded-xl flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-orange-500/10 rounded-lg">
                                <Brain className="w-5 h-5 text-orange-500" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Behavior Score</p>
                                <p className="font-bold">{results.behavior_score !== null && results.behavior_score !== undefined ? Math.round(results.behavior_score) : '-'}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Analysis Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="glass p-6 rounded-xl">
                    <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                        <Target className="w-5 h-5 text-primary" />
                        Topic Performance
                    </h3>
                    <div className="h-[250px]">
                        {topicData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <RechartsBarChart data={topicData}>
                                    <XAxis dataKey="name" stroke="#94a3b8" />
                                    <YAxis stroke="#94a3b8" />
                                    <Tooltip
                                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                                    />
                                    <Bar dataKey="score" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                                </RechartsBarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-center px-4">
                                <span className="font-semibold text-lg mb-2">No topic performance data</span>
                                <span className="text-sm">This may occur if quiz questions are not linked to topics. Please contact your instructor if you believe this is an error.</span>
                            </div>
                        )}
                    </div>
                </div>

                <div className="glass p-6 rounded-xl">
                    <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                        <Brain className="w-5 h-5 text-primary" />
                        AI Insights
                    </h3>
                    <div className="space-y-4">
                        <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                            <p className="text-sm text-muted-foreground mb-2">Mindset Analysis</p>
                            <p className="font-medium">
                                You showed a <span className="text-primary font-bold capitalize">{results.detected_mindset || 'neutral'}</span> mindset during this session.
                                {results.detected_mindset === 'focused' ? ' Keep up the great concentration!' : ' Try to take breaks to improve focus.'}
                            </p>
                        </div>

                        <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                            <p className="text-sm text-muted-foreground mb-2">AI-Powered Recommendations</p>
                            {results.recommendations && results.recommendations.length > 0 ? (
                                <ul className="space-y-3 mt-2">
                                    {results.recommendations.map((rec, index) => (
                                        <li key={index} className="flex gap-2 text-base">
                                            <span className="text-primary mt-1">•</span>
                                            <span dangerouslySetInnerHTML={{ __html: rec.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="font-medium">
                                    Based on your results, we recommend reviewing:
                                    <span className="block mt-2 text-primary font-bold">
                                        {topicData.length > 0
                                            ? topicData.sort((a, b) => a.score - b.score)[0].name
                                            : 'Review concepts related to incorrect answers'}
                                    </span>
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-center gap-4 pt-8">
                <button
                    onClick={() => router.push('/dashboard')}
                    className="px-8 py-3 rounded-lg bg-secondary hover:bg-secondary/80 font-medium transition-all flex items-center gap-2"
                >
                    <Home className="w-5 h-5" />
                    Back to Dashboard
                </button>
                <button
                    onClick={handleDownloadReport}
                    disabled={downloading}
                    className="px-8 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700 font-medium transition-all flex items-center gap-2 shadow-lg shadow-green-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {downloading ? (
                        <>
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            Generating...
                        </>
                    ) : (
                        <>
                            <Download className="w-5 h-5" />
                            Download Report
                        </>
                    )}
                </button>
                <button
                    onClick={() => router.push('/dashboard')}
                    className="px-8 py-3 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 font-medium transition-all flex items-center gap-2 shadow-lg shadow-primary/20"
                >
                    Take Another Quiz
                    <ArrowRight className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}

// Recharts wrapper for clean imports
const RechartsBarChart = (props) => {
    // Only render if we have data with non-zero values/valid structure to prevent "width/height" errors
    if (!props.data || props.data.length === 0) {
        return <div className="h-full flex items-center justify-center text-muted-foreground">No chart data available</div>;
    }
    return <RechartsBar {...props} />;
};
