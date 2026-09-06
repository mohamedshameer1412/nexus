'use client';

import { useState, useEffect } from 'react';
import { quizAPI, classroomAPI } from '@/lib/api';
import { X, Plus, Trash2, Save, ArrowRight, Loader2, AlertCircle } from 'lucide-react';

export default function CreateQuizModal({ isOpen, onClose, classroomId, onSuccess }) {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [topics, setTopics] = useState([]);
    const [error, setError] = useState('');

    // Quiz Data State
    const [quizData, setQuizData] = useState({
        title: '',
        description: '',
        topic_ids: [],
        time_limit: 30,
        difficulty: 'medium',
        is_adaptive: true,
        visibility: 'classroom_only' // Default to classroom only
    });

    const [quizMode, setQuizMode] = useState('practice');

    // Questions State
    const [questions, setQuestions] = useState([]);
    const [currentQuestion, setCurrentQuestion] = useState({
        text: '',
        question_type: 'mcq',
        options: ['', '', '', ''],
        correct_answer: '', // 'A', 'B', 'C', 'D' or text
        explanation: '',
        difficulty: 'medium',
        points: 1
    });

    useEffect(() => {
        if (isOpen) {
            fetchTopics();
        }
    }, [isOpen]);

    const fetchTopics = async () => {
        try {
            const data = await quizAPI.getTopics();
            setTopics(Array.isArray(data) ? data : data.results || []);
        } catch (err) {
            console.error('Failed to load topics');
        }
    };

    const handleAddQuestion = () => {
        // Validation
        if (!currentQuestion.text) return setError('Question text is required');
        if (currentQuestion.question_type === 'mcq') {
            if (currentQuestion.options.some(o => !o)) return setError('All options are required');
            if (!currentQuestion.correct_answer) return setError('Select a correct answer');
        }

        setQuestions([...questions, { ...currentQuestion, id: Date.now() }]);
        // Reset
        setCurrentQuestion({
            text: '',
            question_type: 'mcq',
            options: ['', '', '', ''],
            correct_answer: '',
            explanation: '',
            difficulty: 'medium',
            points: 1
        });
        setError('');
    };

    const handleRemoveQuestion = (id) => {
        setQuestions(questions.filter(q => q.id !== id));
    };

    const handleSubmit = async () => {
        if (questions.length === 0) return setError('Please add at least one question');

        setLoading(true);
        setError('');

        try {
            // 1. Create Quiz
            const createdQuiz = await quizAPI.createQuiz({
                ...quizData,
                topics: quizData.topic_ids // API expects list of IDs usually
            });

            // 2. Create Questions
            for (const q of questions) {
                await quizAPI.createQuestion({
                    quiz: createdQuiz.id,
                    text: q.text,
                    question_type: q.question_type,
                    options: q.question_type === 'mcq' ? q.options : undefined,
                    correct_answer: q.correct_answer,
                    explanation: q.explanation,
                    difficulty: q.difficulty,
                    points: q.points,
                    // Map frontend fields to backend fields if mismatched
                    option_a: q.options[0],
                    option_b: q.options[1],
                    option_c: q.options[2],
                    option_d: q.options[3],
                });
            }

            // 3. Assign to Classroom
            // 3. Assign to Classroom
            if (classroomId) {
                await classroomAPI.createClassroomQuizAssignment({
                    classroom: classroomId,
                    quiz: createdQuiz.id,
                    quiz_mode: quizMode,
                    enable_proctoring: quizMode === 'assessment',
                    max_attempts: quizMode === 'assessment' ? 1 : 100, // Default distinct attempts
                    is_active: true
                });
            }

            onSuccess?.();
            onClose();

        } catch (err) {
            console.error('Failed to create quiz:', err);
            setError(err.response?.data?.error || 'Failed to create quiz');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-border flex justify-between items-center bg-slate-50">
                    <div>
                        <h2 className="text-xl font-bold">Create New Quiz</h2>
                        <p className="text-sm text-muted-foreground">Step {step} of 2: {step === 1 ? 'Quiz Details' : 'Add Questions'}</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full"><X className="w-5 h-5" /></button>
                </div>

                <div className="flex-1 overflow-y-auto p-6">
                    {step === 1 ? (
                        <div className="space-y-4 max-w-2xl mx-auto">
                            <div>
                                <label className="block text-sm font-medium mb-1">Title</label>
                                <input
                                    className="w-full p-2 border rounded-lg"
                                    value={quizData.title}
                                    onChange={e => setQuizData({ ...quizData, title: e.target.value })}
                                    placeholder="e.g. Python Basics"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Description</label>
                                <textarea
                                    className="w-full p-2 border rounded-lg"
                                    value={quizData.description}
                                    onChange={e => setQuizData({ ...quizData, description: e.target.value })}
                                    placeholder="Brief description..."
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Time Limit (mins)</label>
                                    <input
                                        type="number"
                                        className="w-full p-2 border rounded-lg"
                                        value={quizData.time_limit}
                                        onChange={e => setQuizData({ ...quizData, time_limit: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Topic</label>
                                    <select
                                        className="w-full p-2 border rounded-lg"
                                        onChange={e => {
                                            const val = e.target.value;
                                            setQuizData(prev => ({
                                                ...prev,
                                                topic_ids: val ? [val] : []
                                            }));
                                        }}
                                    >
                                        <option value="">Select Topic</option>
                                        {topics.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                                    </select>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={quizData.is_adaptive}
                                    onChange={e => setQuizData({ ...quizData, is_adaptive: e.target.checked })}
                                />
                                <label>Enable Adaptive Difficulty</label>
                            </div>

                            {/* Quiz Mode Selection */}
                            <div>
                                <label className="block text-sm font-medium mb-3">Quiz Mode</label>
                                <div className="grid grid-cols-2 gap-4">
                                    <button
                                        type="button"
                                        onClick={() => setQuizMode('practice')}
                                        className={`p-4 border-2 rounded-xl text-left transition-all ${quizMode === 'practice'
                                            ? 'border-blue-600 bg-blue-50'
                                            : 'border-slate-200 hover:border-slate-300'
                                            }`}
                                    >
                                        <div className="font-bold text-slate-900 mb-1">Practice Mode</div>
                                        <p className="text-xs text-slate-600">No proctoring, unlimited attempts. Best for learning.</p>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setQuizMode('assessment')}
                                        className={`p-4 border-2 rounded-xl text-left transition-all ${quizMode === 'assessment'
                                            ? 'border-purple-600 bg-purple-50'
                                            : 'border-slate-200 hover:border-slate-300'
                                            }`}
                                    >
                                        <div className="font-bold text-slate-900 mb-1">Assessment Mode</div>
                                        <p className="text-xs text-slate-600">Proctored, monitored environment. Best for exams.</p>
                                    </button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex gap-6 h-full">
                            {/* Question Form */}
                            <div className="flex-1 space-y-4 overflow-y-auto pr-2">
                                <h3 className="font-bold border-b pb-2">New Question</h3>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Question Type</label>
                                    <select
                                        className="w-full p-2 border rounded-lg"
                                        value={currentQuestion.question_type}
                                        onChange={e => setCurrentQuestion({ ...currentQuestion, question_type: e.target.value })}
                                    >
                                        <option value="mcq">Multiple Choice</option>
                                        <option value="short_answer">Short Answer</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Question Text</label>
                                    <textarea
                                        className="w-full p-2 border rounded-lg"
                                        value={currentQuestion.text}
                                        onChange={e => setCurrentQuestion({ ...currentQuestion, text: e.target.value })}
                                    />
                                </div>

                                {currentQuestion.question_type === 'mcq' && (
                                    <div className="space-y-2">
                                        <label className="block text-sm font-medium">Options</label>
                                        {['A', 'B', 'C', 'D'].map((opt, idx) => (
                                            <div key={opt} className="flex gap-2 items-center">
                                                <span className="font-bold w-4">{opt}</span>
                                                <input
                                                    className="flex-1 p-2 border rounded-lg"
                                                    value={currentQuestion.options[idx]}
                                                    onChange={e => {
                                                        const newOpts = [...currentQuestion.options];
                                                        newOpts[idx] = e.target.value;
                                                        setCurrentQuestion({ ...currentQuestion, options: newOpts });
                                                    }}
                                                    placeholder={`Option ${opt}`}
                                                />
                                                <input
                                                    type="radio"
                                                    name="correct"
                                                    checked={currentQuestion.correct_answer === opt}
                                                    onChange={() => setCurrentQuestion({ ...currentQuestion, correct_answer: opt })}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <div>
                                    <label className="block text-sm font-medium mb-1">Explanation</label>
                                    <textarea
                                        className="w-full p-2 border rounded-lg"
                                        value={currentQuestion.explanation}
                                        onChange={e => setCurrentQuestion({ ...currentQuestion, explanation: e.target.value })}
                                    />
                                </div>

                                <button
                                    onClick={handleAddQuestion}
                                    className="w-full py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800"
                                >
                                    <Plus className="w-4 h-4 inline mr-2" /> Add Question
                                </button>
                            </div>

                            {/* Questions List */}
                            <div className="w-1/3 border-l pl-4 overflow-y-auto">
                                <h3 className="font-bold mb-4">Questions ({questions.length})</h3>
                                <div className="space-y-3">
                                    {questions.map((q, i) => (
                                        <div key={q.id} className="p-3 bg-slate-50 rounded-lg border text-sm relative group">
                                            <button
                                                onClick={() => handleRemoveQuestion(q.id)}
                                                className="absolute top-2 right-2 text-red-500 opacity-0 group-hover:opacity-100"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                            <p className="font-bold truncate">Q{i + 1}: {q.text}</p>
                                            <p className="text-xs text-muted-foreground">{q.question_type}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {error && (
                    <div className="px-6 pb-4 text-red-600 text-sm flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" /> {error}
                    </div>
                )}

                <div className="p-6 border-t border-border bg-slate-50 flex justify-end gap-3">
                    {step === 2 && (
                        <button
                            onClick={() => setStep(1)}
                            className="px-4 py-2 border rounded-lg hover:bg-slate-100"
                        >
                            Back
                        </button>
                    )}
                    {step === 1 ? (
                        <button
                            onClick={() => {
                                if (!quizData.title) return setError('Title is required');
                                if (quizData.topic_ids.length === 0) return setError('Select a topic');
                                setError('');
                                setStep(2);
                            }}
                            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 flex items-center gap-2"
                        >
                            Next <ArrowRight className="w-4 h-4" />
                        </button>
                    ) : (
                        <button
                            onClick={handleSubmit}
                            disabled={loading}
                            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            Create & Assign
                        </button>
                    )}
                </div>
            </div>
        </div >
    );
}
