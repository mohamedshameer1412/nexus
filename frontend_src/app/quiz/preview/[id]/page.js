'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { quizAPI, classroomAPI, api } from '@/lib/api';
import {
    Loader2,
    BookOpen,
    Clock,
    ArrowLeft,
    CheckCircle2,
    HelpCircle,
    AlertCircle,
    ChevronRight,
    Brain,
    Shield
} from 'lucide-react';

export default function QuizPreviewPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const router = useRouter();
    const quizId = params.id;
    const classroomId = searchParams.get('classroom_id');

    const [loading, setLoading] = useState(true);
    const [quiz, setQuiz] = useState(null);
    const [questions, setQuestions] = useState([]);
    const [classroom, setClassroom] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (quizId) {
            fetchData();
        }
    }, [quizId]);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Fetch Quiz Details
            const quizData = await quizAPI.getQuiz(quizId);
            setQuiz(quizData);

            // Fetch Classroom Details if available
            if (classroomId) {
                const classData = await classroomAPI.getClassroom(classroomId);
                setClassroom(classData);
            }

            // Fetch Sample Questions from the quiz's topics
            if (quizData.topics && quizData.topics.length > 0) {
                // Fetch first 5-10 questions as a preview
                // We'll use a simple approach: fetch questions for the first topic
                const response = await api.get(`/api/quiz/questions/?topic=${quizData.topics[0]}&page_size=10`);
                setQuestions(response.data.results || response.data || []);
            }
        } catch (err) {
            console.error('Failed to fetch preview data:', err);
            setError('Failed to load quiz preview. You may not have permission to view these questions.');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="text-center">
                    <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto mb-4" />
                    <p className="text-slate-500 font-medium">Loading Quiz Preview...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-8 bg-slate-50">
                <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 max-w-md w-full text-center">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-slate-800 mb-2">Access Denied</h2>
                    <p className="text-slate-500 mb-6">{error}</p>
                    <button
                        onClick={() => router.back()}
                        className="w-full py-3 bg-slate-100 text-slate-700 rounded-xl font-bold hover:bg-slate-200 transition-colors"
                    >
                        Go Back
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 pb-20">
            {/* Header */}
            <div className="bg-blue-600 text-white pt-10 pb-20 px-6">
                <div className="max-w-5xl mx-auto">
                    <button
                        onClick={() => router.back()}
                        className="flex items-center gap-2 text-blue-100 hover:text-white mb-8 transition-colors group"
                    >
                        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                        <span className="font-bold text-sm uppercase tracking-widest">Back to Classroom</span>
                    </button>

                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                        <div>
                            <div className="flex items-center gap-3 mb-3">
                                <span className="px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-[10px] font-black uppercase tracking-widest">
                                    Quiz Preview
                                </span>
                                {quiz.is_adaptive && (
                                    <span className="px-3 py-1 bg-emerald-500/20 backdrop-blur-md rounded-full text-[10px] font-black uppercase tracking-widest text-emerald-100 flex items-center gap-1">
                                        <Brain className="w-3 h-3" />
                                        Adaptive Mode
                                    </span>
                                )}
                            </div>
                            <h1 className="text-4xl font-black mb-3">{quiz.title}</h1>
                            <p className="text-blue-100 max-w-2xl font-medium leading-relaxed opacity-90">
                                {quiz.description || "Review the diagnostic and practice questions available in this session."}
                            </p>
                        </div>

                        <div className="bg-white/10 backdrop-blur-xl p-6 rounded-2xl border border-white/20 w-full md:w-auto">
                            <div className="grid grid-cols-2 gap-8">
                                <div>
                                    <p className="text-blue-200 text-[10px] font-bold uppercase tracking-widest mb-1">Questions</p>
                                    <p className="text-2xl font-black">{quiz.total_questions}</p>
                                </div>
                                <div>
                                    <p className="text-blue-200 text-[10px] font-bold uppercase tracking-widest mb-1">Time Limit</p>
                                    <p className="text-2xl font-black">{quiz.time_limit || 'None'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-5xl mx-auto -mt-10 px-6">
                <div className="bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden">
                    <div className="p-8 border-b border-slate-100 bg-slate-50/50">
                        <h2 className="text-xl font-black text-slate-800 flex items-center gap-3">
                            <BookOpen className="w-6 h-6 text-blue-600" />
                            Sample Questions
                            <span className="text-sm font-bold text-slate-400 ml-auto">
                                Showing {questions.length} samples
                            </span>
                        </h2>
                    </div>

                    <div className="divide-y divide-slate-100">
                        {questions.length > 0 ? (
                            questions.map((q, idx) => (
                                <div key={q.id} className="p-8 hover:bg-slate-50 transition-colors group">
                                    <div className="flex gap-6">
                                        <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center text-blue-600 font-black text-sm">
                                            {idx + 1}
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-3">
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest ${q.difficulty_level <= 2 ? 'bg-emerald-100 text-emerald-700' :
                                                    q.difficulty_level === 3 ? 'bg-amber-100 text-amber-700' :
                                                        'bg-rose-100 text-rose-700'
                                                    }`}>
                                                    Lvl {q.difficulty_level}
                                                </span>
                                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                                    {q.question_type === 'mcq' ? 'Multiple Choice' : 'Free Text'}
                                                </span>
                                            </div>

                                            <p className="text-lg font-bold text-slate-800 mb-6 leading-relaxed">
                                                {q.question_text}
                                            </p>

                                            {q.question_type === 'mcq' && (
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                    {['a', 'b', 'c', 'd'].map(opt => (
                                                        q[`option_${opt}`] && (
                                                            <div
                                                                key={opt}
                                                                className={`p-4 rounded-xl border flex items-center gap-3 transition-all ${q.correct_answer === opt.toUpperCase()
                                                                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                                                                    : 'bg-white border-slate-100 text-slate-500'
                                                                    }`}
                                                            >
                                                                <span className={`w-6 h-6 rounded flex items-center justify-center text-[10px] font-black ${q.correct_answer === opt.toUpperCase()
                                                                    ? 'bg-emerald-500 text-white'
                                                                    : 'bg-slate-100 text-slate-400'
                                                                    }`}>
                                                                    {opt.toUpperCase()}
                                                                </span>
                                                                <span className="font-bold text-sm">{q[`option_${opt}`]}</span>
                                                                {q.correct_answer === opt.toUpperCase() && (
                                                                    <CheckCircle2 className="w-4 h-4 text-emerald-500 ml-auto" />
                                                                )}
                                                            </div>
                                                        )
                                                    ))}
                                                </div>
                                            )}

                                            {q.explanation && (
                                                <div className="mt-6 p-4 bg-blue-50/50 rounded-xl border border-blue-100">
                                                    <p className="text-[10px] font-black text-blue-600 uppercase tracking-widest mb-2 flex items-center gap-2">
                                                        <HelpCircle className="w-3 h-3" />
                                                        Explanation
                                                    </p>
                                                    <p className="text-sm text-blue-800 font-medium">
                                                        {q.explanation}
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="p-20 text-center">
                                <HelpCircle className="w-16 h-16 text-slate-200 mx-auto mb-6" />
                                <h3 className="text-xl font-bold text-slate-600 mb-2">No Sample Questions</h3>
                                <p className="text-slate-400 max-w-sm mx-auto font-medium">
                                    We couldn't retrieve sample questions for this quiz preview.
                                </p>
                            </div>
                        )}
                    </div>
                </div>

                <div className="mt-12 bg-amber-50 rounded-3xl p-8 border border-amber-100 flex items-start gap-6">
                    <div className="w-12 h-12 bg-amber-100 rounded-2xl flex items-center justify-center flex-shrink-0">
                        <Shield className="w-6 h-6 text-amber-600" />
                    </div>
                    <div>
                        <h4 className="text-lg font-black text-amber-900 mb-2">Teacher & Proctoring Note</h4>
                        <p className="text-amber-700 font-medium leading-relaxed text-sm">
                            This is a <span className="font-black underline">preview mode</span> for educational review.
                            The actual questions a student sees may vary based on our adaptive AI.
                            If proctoring is enabled, students will be monitored via camera and locked into fullscreen mode during the real session.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
