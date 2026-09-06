'use client';

import { useState, useEffect } from 'react';
import { quizAPI, analyticsAPI } from '@/lib/api';
import {
    BarChart3,
    Search,
    Download,
    Eye,
    AlertTriangle,
    CheckCircle2,
    Clock,
    RotateCcw
} from 'lucide-react';

import CustomSelect from '@/components/ui/CustomSelect';
import Toast from '@/components/ui/Toast';
import ConfirmResetModal from '@/components/ui/ConfirmResetModal';
import ErrorDisplay from '@/components/ui/ErrorDisplay';
import { parseApiError } from '@/lib/errorHandler';

export default function QuizReporting() {
    const [quizzes, setQuizzes] = useState([]);
    const [selectedQuizId, setSelectedQuizId] = useState('all');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [resetConfirmation, setResetConfirmation] = useState({ isOpen: false, studentId: null, studentName: '', quizId: '', quizTitle: '' });
    const [toast, setToast] = useState(null);

    useEffect(() => {
        loadQuizzes();
    }, []);

    useEffect(() => {
        if (selectedQuizId) {
            loadResults(selectedQuizId);
        } else {
            // Default to all if nothing selected, or just empty
            loadResults('all');
        }
    }, [selectedQuizId]);

    const loadQuizzes = async () => {
        try {
            const data = await quizAPI.getQuizzes();
            setQuizzes(Array.isArray(data) ? data : data.results || []);
        } catch (error) {
            console.error("Failed to load quizzes", error);
            const parsedError = parseApiError(error);
            setToast({
                message: parsedError.message,
                type: 'error',
                title: parsedError.title
            });
        }
    };

    const loadResults = async (quizId) => {
        setLoading(true);
        setError(null);
        try {
            let data;
            if (quizId === 'all' || !quizId) {
                data = await analyticsAPI.getAllQuizResults();
            } else {
                data = await analyticsAPI.getQuizResults(quizId);
            }
            setResults(data);
        } catch (error) {
            console.error("Failed to load results", error);
            const parsedError = parseApiError(error);
            setError(parsedError);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const filteredResults = results.filter(r =>
        r.student_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        r.student_email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const handleResetClick = (studentId, studentName) => {
        // Use the selected quiz from dropdown
        const quizId = selectedQuizId; // Can be 'all' or specific quiz ID
        const quizTitle = selectedQuizId === 'all'
            ? 'All Quizzes'
            : quizzes.find(q => q.id === selectedQuizId)?.title || 'Selected Quiz';

        setResetConfirmation({
            isOpen: true,
            studentId,
            studentName,
            quizId,
            quizTitle
        });
    };

    const handleConfirmReset = async () => {
        try {
            const result = await quizAPI.resetAttempts(
                resetConfirmation.studentId,
                resetConfirmation.quizId
            );
            setToast({ message: result.message, type: 'success', title: 'Success' });
            setResetConfirmation({ isOpen: false, studentId: null, studentName: '', quizId: '', quizTitle: '' });
            // Refresh results
            if (selectedQuizId) {
                loadResults(selectedQuizId);
            }
        } catch (error) {
            const parsedError = parseApiError(error);
            setToast({
                message: parsedError.message,
                type: 'error',
                title: parsedError.title
            });
            setResetConfirmation({ isOpen: false, studentId: null, studentName: '', quizId: '', quizTitle: '' });
        }
    };

    const handleDownloadReport = async (sessionId, studentName) => {
        try {
            const blob = await quizAPI.exportReport(sessionId);
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `report_${studentName.replace(/\s+/g, '_')}_${sessionId}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            setToast({ message: 'Report downloaded successfully', type: 'success' });
        } catch (error) {
            console.error('Download failed:', error);
            setToast({ message: 'Failed to download report', type: 'error' });
        }
    };

    const handleExportAll = async () => {
        if (!selectedQuizId) return;
        try {
            const blob = await quizAPI.exportResultsCsv(selectedQuizId);
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `quiz_results_${selectedQuizId}.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            setToast({ message: 'Results exported successfully', type: 'success' });
        } catch (error) {
            console.error('Export failed:', error);
            setToast({ message: 'Failed to export results', type: 'error' });
        }
    };

    const quizOptions = [
        { label: 'All Quizzes', value: 'all' },
        ...quizzes.map(q => ({ label: q.title, value: q.id }))
    ];

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center border-b border-border pb-6">
                <div>
                    <h2 className="text-2xl font-bold text-foreground tracking-tight">Quiz Results & Proctoring</h2>
                    <p className="text-muted-foreground mt-1">View student performance and integrity reports</p>
                </div>
            </div>

            {/* Controls */}
            <div className="card-enterprise p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="text-sm font-semibold mb-2 block text-foreground">Select Quiz</label>
                    <div className="max-w-md">
                        <CustomSelect
                            options={quizOptions}
                            value={selectedQuizId}
                            onChange={setSelectedQuizId}
                            placeholder="All Quizzes"
                            icon={BarChart3}
                        />
                    </div>
                </div>

                <div className="flex flex-col">
                    <label className="text-sm font-semibold mb-2 block text-foreground">Actions</label>
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <input
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                placeholder="Search students..."
                                className="w-full pl-10 p-2.5 rounded-md border border-input bg-background text-foreground focus:ring-1 focus:ring-ring focus:border-input outline-none transition-all placeholder:text-muted-foreground font-medium text-sm"
                            />
                        </div>
                        <button
                            onClick={handleExportAll}
                            disabled={!selectedQuizId || loading}
                            className="btn-enterprise-primary"
                        >
                            <Download className="w-4 h-4" />
                            Export CSV
                        </button>
                    </div>
                </div>
            </div>

            {/* Results Table */}
            {
                selectedQuizId ? (
                    <div className="card-enterprise overflow-hidden p-0">
                        {loading ? (
                            <div className="p-12 flex justify-center">
                                <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full"></div>
                            </div>
                        ) : error ? (
                            <div className="p-6">
                                <ErrorDisplay
                                    error={error}
                                    onRetry={() => loadResults(selectedQuizId)}
                                    showRetry={true}
                                />
                            </div>
                        ) : filteredResults.length === 0 ? (
                            <div className="p-12 text-center text-muted-foreground font-medium">
                                No results found for this quiz yet.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm text-left">
                                    <thead className="bg-secondary text-muted-foreground font-medium border-b border-border">
                                        <tr>
                                            <th className="px-6 py-4">Student</th>
                                            {selectedQuizId === 'all' && <th className="px-6 py-4">Quiz</th>}
                                            <th className="px-6 py-4">Score</th>
                                            <th className="px-6 py-4">Accuracy</th>
                                            <th className="px-6 py-4">Time Taken</th>
                                            <th className="px-6 py-4">Integrity</th>
                                            <th className="px-6 py-4">Completed At</th>
                                            <th className="px-6 py-4">Attempts</th>
                                            <th className="px-6 py-4 text-right">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border">
                                        {filteredResults.map((result) => (
                                            <tr key={result.session_id} className="hover:bg-muted/50 transition-colors">
                                                <td className="px-6 py-4">
                                                    <div className="font-medium text-foreground">{result.student_name}</div>
                                                    <div className="text-xs text-muted-foreground">{result.student_email}</div>
                                                </td>
                                                {selectedQuizId === 'all' && (
                                                    <td className="px-6 py-4 font-medium text-foreground">
                                                        {result.quiz_title}
                                                    </td>
                                                )}
                                                <td className="px-6 py-4">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${result.score >= 80 ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                                                        result.score >= 60 ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                                                            'bg-red-500/10 text-red-400 border-red-500/20'
                                                        }`}>
                                                        {Math.round(result.score)}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 font-medium text-white">
                                                    {Math.round(result.accuracy)}%
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-1.5 text-slate-400">
                                                        <Clock className="w-3.5 h-3.5" />
                                                        <span>{Math.round(result.time_taken)}m</span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-2">
                                                        {result.behavior_score >= 90 ? (
                                                            <>
                                                                <CheckCircle2 className="w-4 h-4 text-green-500" />
                                                                <span className="text-sm font-bold text-green-400">{result.behavior_score}</span>
                                                            </>
                                                        ) : result.behavior_score >= 70 ? (
                                                            <>
                                                                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                                                                <span className="text-sm font-bold text-yellow-400">{result.behavior_score}</span>
                                                            </>
                                                        ) : (
                                                            <>
                                                                <AlertTriangle className="w-4 h-4 text-red-500" />
                                                                <span className="text-sm font-bold text-red-400">{result.behavior_score}</span>
                                                            </>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-muted-foreground">
                                                    {new Date(result.completed_at).toLocaleDateString('en-GB')}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className="inline-flex items-center px-2 py-1 rounded bg-secondary text-xs font-medium text-muted-foreground">
                                                        Attempt {result.attempt_number || 1}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <div className="flex justify-end gap-2">
                                                        <button
                                                            onClick={() => handleDownloadReport(result.session_id, result.student_name)}
                                                            className="p-2 hover:bg-secondary rounded-md text-muted-foreground hover:text-foreground transition-colors"
                                                            title="Download Report PDF"
                                                        >
                                                            <Download className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => handleResetClick(
                                                                result.student_id || result.session_id,
                                                                result.student_name
                                                            )}
                                                            className="p-2 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-md text-orange-600 dark:text-orange-400 transition-colors"
                                                            title={selectedQuizId === 'all' ? "Reset all quiz attempts for this student" : "Reset this quiz for this student"}
                                                        >
                                                            <RotateCcw className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="card-enterprise p-16 text-center">
                        <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center mx-auto mb-4">
                            <BarChart3 className="w-8 h-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-bold text-foreground mb-2">Select a Quiz to View Results</h3>
                        <p className="text-muted-foreground max-w-sm mx-auto">
                            Choose a quiz from the dropdown above to see detailed student performance and integrity reports.
                        </p>
                    </div>
                )
            }

            {/* Reset Confirmation Modal */}
            <ConfirmResetModal
                isOpen={resetConfirmation.isOpen}
                onClose={() => setResetConfirmation({ isOpen: false, studentId: null, studentName: '', quizId: '', quizTitle: '' })}
                onConfirm={handleConfirmReset}
                resetType={resetConfirmation.quizId === 'all' ? 'all_quizzes' : 'specific'}
                studentName={resetConfirmation.studentName}
                quizTitle={resetConfirmation.quizTitle}
                sessionCount={results.filter(r => r.student_id === resetConfirmation.studentId).length}
                loading={loading}
            />

            {/* Toast Notification */}
            {
                toast && (
                    <Toast
                        message={toast.message}
                        type={toast.type}
                        onClose={() => setToast(null)}
                    />
                )
            }
        </div >
    );
}
