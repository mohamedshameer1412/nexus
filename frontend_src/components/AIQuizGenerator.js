'use client';

import { useState, useEffect } from 'react';
import { quizAPI } from '@/lib/api';
import { X, Sparkles, Loader2, Check, AlertCircle, Trash2, Edit2 } from 'lucide-react';

export default function AIQuizGenerator({ isOpen, onClose, onSuccess }) {
    const [step, setStep] = useState(1); // 1: Form, 2: Generating, 3: Preview
    const [topics, setTopics] = useState([]);
    const [formData, setFormData] = useState({
        topic_id: '',
        num_questions: 10,
        difficulty: 'medium',
        question_type: 'mcq',
        model: 'gemini-2.0-flash-exp'  // Free and fast!
    });
    const [generatedQuestions, setGeneratedQuestions] = useState([]);
    const [metadata, setMetadata] = useState(null);
    const [prompt, setPrompt] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchTopics();
        }
    }, [isOpen]);

    const fetchTopics = async () => {
        try {
            const data = await quizAPI.getTopics();
            setTopics(Array.isArray(data) ? data : data.results || []);
        } catch (error) {
            console.error('Error fetching topics:', error);
            setError('Failed to load topics');
        }
    };

    const handleGenerate = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        setStep(2);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/quiz/generate-questions/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate questions');
            }

            setGeneratedQuestions(data.questions);
            setMetadata(data.metadata);
            setPrompt(data.prompt);
            setStep(3);
        } catch (error) {
            console.error('Error generating questions:', error);
            setError(error.message || 'Failed to generate questions. Please check your API key.');
            setStep(1);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setError('');

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/quiz/save-generated-questions/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    topic_id: formData.topic_id,
                    questions: generatedQuestions,
                    metadata: metadata,
                    prompt: prompt
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to save questions');
            }

            if (onSuccess) onSuccess();
            onClose();
        } catch (error) {
            console.error('Error saving questions:', error);
            setError(error.message || 'Failed to save questions');
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteQuestion = (index) => {
        setGeneratedQuestions(prev => prev.filter((_, i) => i !== index));
    };

    const handleEditQuestion = (index, field, value) => {
        setGeneratedQuestions(prev => prev.map((q, i) =>
            i === index ? { ...q, [field]: value } : q
        ));
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-[#1e293b] rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col border border-white/10">
                {/* Header */}
                <div className="p-6 border-b border-white/10 flex items-center justify-between bg-[#0f172a]/50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/20">
                            <Sparkles className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white">AI Quiz Generator</h2>
                            <p className="text-sm text-slate-400">Generate questions using AI in seconds</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-slate-400 hover:text-white" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                    {/* Step 1: Form */}
                    {step === 1 && (
                        <form onSubmit={handleGenerate} className="space-y-6">
                            {error && (
                                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3">
                                    <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
                                    <p className="text-sm text-red-200">{error}</p>
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-semibold text-slate-300 mb-2">
                                    Topic *
                                </label>
                                <select
                                    value={formData.topic_id}
                                    onChange={(e) => setFormData({ ...formData, topic_id: e.target.value })}
                                    className="w-full px-4 py-3 bg-[#0f172a] border border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-slate-500"
                                    required
                                >
                                    <option value="">Select a topic</option>
                                    {topics.map(topic => (
                                        <option key={topic.id} value={topic.id}>
                                            {topic.name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-semibold text-slate-300 mb-2">
                                        Number of Questions *
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.num_questions}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            if (val === '' || /^[0-9]*$/.test(val)) {
                                                setFormData({ ...formData, num_questions: val });
                                            }
                                        }}
                                        className="w-full px-4 py-3 bg-[#0f172a] border border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-semibold text-slate-300 mb-2">
                                        Difficulty *
                                    </label>
                                    <select
                                        value={formData.difficulty}
                                        onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
                                        className="w-full px-4 py-3 bg-[#0f172a] border border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white"
                                    >
                                        <option value="easy">Easy</option>
                                        <option value="medium">Medium</option>
                                        <option value="hard">Hard</option>
                                    </select>
                                </div>
                            </div>

                            {/* AI Model Selector Removed - Defaulting to Gemini 2.0 Flash internally */}

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:from-purple-500 hover:to-blue-500 transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                <Sparkles className="w-5 h-5" />
                                Generate Questions
                            </button>
                        </form>
                    )}

                    {/* Step 2: Generating */}
                    {step === 2 && (
                        <div className="flex flex-col items-center justify-center py-12">
                            <Loader2 className="w-16 h-16 text-blue-500 animate-spin mb-4" />
                            <h3 className="text-xl font-bold text-white mb-2">Generating Questions...</h3>
                            <p className="text-slate-400">AI is creating {formData.num_questions} questions for you</p>
                        </div>
                    )}

                    {/* Step 3: Preview */}
                    {step === 3 && (
                        <div className="space-y-6">
                            {error && (
                                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3">
                                    <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
                                    <p className="text-sm text-red-200">{error}</p>
                                </div>
                            )}

                            {/* Metadata */}
                            {metadata && (
                                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                                    <div className="grid grid-cols-3 gap-4 text-sm">
                                        <div>
                                            <p className="text-slate-400">Model</p>
                                            <p className="font-semibold text-white">{metadata.model}</p>
                                        </div>
                                        <div>
                                            <p className="text-slate-400">Generation Time</p>
                                            <p className="font-semibold text-white">{metadata.generation_time}s</p>
                                        </div>
                                        <div>
                                            <p className="text-slate-400">Questions</p>
                                            <p className="font-semibold text-white">{generatedQuestions.length}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Questions List */}
                            <div className="space-y-4">
                                {generatedQuestions.map((question, index) => (
                                    <div key={index} className="bg-[#0f172a]/50 border border-white/10 rounded-xl p-4 hover:border-white/20 transition-all">
                                        <div className="flex items-start justify-between mb-3">
                                            <h4 className="font-semibold text-white flex-1">
                                                {index + 1}. {question.question_text}
                                            </h4>
                                            <button
                                                onClick={() => handleDeleteQuestion(index)}
                                                className="p-2 hover:bg-white/10 rounded-lg text-red-400 transition-colors"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>

                                        <div className="space-y-2 mb-3">
                                            {['A', 'B', 'C', 'D'].map(option => (
                                                <div
                                                    key={option}
                                                    className={`p-2 rounded-lg text-sm ${question.correct_answer === option
                                                        ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-200'
                                                        : 'bg-white/5 border border-white/5 text-slate-300'
                                                        }`}
                                                >
                                                    <span className="font-bold opacity-70">{option}.</span> {question[`option_${option.toLowerCase()}`]}
                                                    {question.correct_answer === option && (
                                                        <Check className="w-4 h-4 text-emerald-500 inline ml-2" />
                                                    )}
                                                </div>
                                            ))}
                                        </div>

                                        {question.explanation && (
                                            <p className="text-sm text-slate-400 italic">
                                                💡 {question.explanation}
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                {step === 3 && (
                    <div className="p-6 border-t border-white/10 bg-[#0f172a]/50 flex gap-3">
                        <button
                            onClick={() => setStep(1)}
                            className="flex-1 py-3 border border-white/10 text-white rounded-xl font-semibold hover:bg-white/5 transition-all"
                        >
                            Generate More
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={saving || generatedQuestions.length === 0}
                            className="flex-1 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:from-purple-500 hover:to-blue-500 transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                            {saving ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Check className="w-5 h-5" />
                                    Save to Quiz Bank ({generatedQuestions.length})
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
