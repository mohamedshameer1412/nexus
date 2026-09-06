'use client';

import { useState, useEffect } from 'react';
import { quizAPI } from '@/lib/api';
import {
    Plus,
    Pencil,
    Trash2,
    Search,
    Loader2,
    ClipboardList,
    Clock,
    FileQuestion,
    X,
    Sparkles,
    CheckSquare,
    RotateCcw,
    CheckCircle2,
    XCircle,
    Eye,
    BookOpen
} from 'lucide-react';
import AlertModal from '../../ui/AlertModal';
import AIQuizGenerator from '../../AIQuizGenerator';

export default function QuizzesManagement() {
    const [quizzes, setQuizzes] = useState([]);
    const [topics, setTopics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingQuiz, setEditingQuiz] = useState(null);
    const [selectedQuizzes, setSelectedQuizzes] = useState([]);
    const [isSelectionMode, setIsSelectionMode] = useState(false); // Enterprise Selection Mode
    const [alertConfig, setAlertConfig] = useState({
        isOpen: false,
        title: '',
        message: '',
        type: 'warning',
        showCancel: false,
        onConfirm: null
    });
    const [showAIGenerator, setShowAIGenerator] = useState(false);

    const showAlert = (config) => {
        setAlertConfig({ ...config, isOpen: true });
    };

    const closeAlert = () => {
        setAlertConfig(prev => ({ ...prev, isOpen: false }));
    };

    const [formData, setFormData] = useState({
        title: '',
        description: '',
        topics: [],
        total_questions: 10,
        time_limit: 30,
        passing_score: 60,
        difficulty_min: 1,
        difficulty_max: 5,
        is_adaptive: true,
        is_active: true,
        allow_retakes: false,
        max_attempts: 1,
        show_answers: false,
        show_explanations: true,
        show_explanations: true,
        question_type: 'mcq' // Default question type
    });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [quizzesData, topicsData] = await Promise.all([
                quizAPI.getQuizzes(),
                quizAPI.getTopics()
            ]);
            setQuizzes(Array.isArray(quizzesData) ? quizzesData : quizzesData.results || []);
            setTopics(Array.isArray(topicsData) ? topicsData : topicsData.results || []);
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setLoading(false);
        }
    };

    // Calculate max available questions based on selected topics
    const maxAvailableQuestions = formData.topics.reduce((acc, topicId) => {
        const topic = topics.find(t => t.id === topicId);
        return acc + (topic?.approved_questions_count || 0);
    }, 0);

    const isQuestionCountValid = formData.topics.length === 0 || formData.total_questions <= maxAvailableQuestions;

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!isQuestionCountValid) {
            showAlert({
                title: 'Invalid Configuration',
                message: `You requested ${formData.total_questions} questions, but only ${maxAvailableQuestions} are available in the selected topics.`,
                type: 'error'
            });
            return;
        }

        try {
            if (editingQuiz) {
                await quizAPI.updateQuiz(editingQuiz.id, formData);
            } else {
                await quizAPI.createQuiz(formData);
            }
            setShowModal(false);
            setEditingQuiz(null);
            resetForm();
            fetchData();
        } catch (error) {
            console.error('Error saving quiz:', error);
            // Show specific validation error if available
            const errorMsg = error.response?.data?.total_questions || error.response?.data?.error || 'Failed to save quiz';
            showAlert({
                title: 'Error',
                message: errorMsg,
                type: 'error'
            });
        }
    };

    const handleDelete = async (id) => {
        showAlert({
            title: 'Delete Quiz?',
            message: 'Are you sure you want to delete this quiz? This action cannot be undone.',
            type: 'warning',
            showCancel: true,
            confirmText: 'Delete',
            cancelText: 'Cancel',
            onConfirm: async () => {
                try {
                    await quizAPI.deleteQuiz(id);
                    fetchData();
                    closeAlert();
                } catch (error) {
                    closeAlert();
                    setTimeout(() => {
                        showAlert({
                            title: 'Error',
                            message: 'Failed to delete quiz',
                            type: 'error'
                        });
                    }, 100);
                }
            }
        });
    };

    const handleBulkDelete = () => {
        if (selectedQuizzes.length === 0) return;

        showAlert({
            title: 'Delete Selected Quizzes?',
            message: `Are you sure you want to delete ${selectedQuizzes.length} quizzes? This action cannot be undone.`,
            type: 'warning',
            showCancel: true,
            confirmText: 'Delete All',
            cancelText: 'Cancel',
            onConfirm: async () => {
                try {
                    await Promise.all(selectedQuizzes.map(id => quizAPI.deleteQuiz(id)));
                    setSelectedQuizzes([]);
                    setIsSelectionMode(false); // Exit selection mode
                    fetchData();
                    closeAlert();
                    setTimeout(() => {
                        showAlert({
                            title: 'Success',
                            message: 'Selected quizzes deleted successfully',
                            type: 'success'
                        });
                    }, 100);
                } catch (error) {
                    closeAlert();
                    setTimeout(() => {
                        showAlert({
                            title: 'Error',
                            message: 'Failed to delete some quizzes',
                            type: 'error'
                        });
                    }, 100);
                }
            }
        });
    };

    const toggleSelectQuiz = (id) => {
        setSelectedQuizzes(prev =>
            prev.includes(id) ? prev.filter(qId => qId !== id) : [...prev, id]
        );
    };

    const toggleSelectAll = () => {
        if (selectedQuizzes.length === filteredQuizzes.length) {
            setSelectedQuizzes([]);
        } else {
            setSelectedQuizzes(filteredQuizzes.map(q => q.id));
        }
    };

    const resetForm = () => {
        setFormData({
            title: '',
            description: '',
            topics: [],
            total_questions: 10,
            time_limit: 30,
            passing_score: 60,
            difficulty_min: 1,
            difficulty_max: 5,
            is_adaptive: true,
            is_active: true,
            allow_retakes: false,
            max_attempts: 1,
            show_answers: false,
            show_explanations: true,
            show_explanations: true,
            question_type: 'mixed'
        });
    };

    const openCreateModal = () => {
        setEditingQuiz(null);
        resetForm();
        setShowModal(true);
    };

    const openEditModal = (quiz) => {
        setEditingQuiz(quiz);
        setFormData({
            title: quiz.title,
            description: quiz.description || '',
            topics: quiz.topics || [],
            total_questions: quiz.total_questions || 10,
            time_limit: quiz.time_limit || 30,
            passing_score: quiz.passing_score || 60,
            difficulty_min: quiz.difficulty_min || 1,
            difficulty_max: quiz.difficulty_max || 5,
            is_adaptive: quiz.is_adaptive !== undefined ? quiz.is_adaptive : true,
            is_active: quiz.is_active !== undefined ? quiz.is_active : true,
            allow_retakes: quiz.allow_retakes !== undefined ? quiz.allow_retakes : false,
            max_attempts: quiz.max_attempts || 1,
            show_answers: quiz.show_answers !== undefined ? quiz.show_answers : false,
            show_explanations: quiz.show_explanations !== undefined ? quiz.show_explanations : true,
            show_explanations: quiz.show_explanations !== undefined ? quiz.show_explanations : true,
            question_type: quiz.question_type || 'mixed'
        });
        setShowModal(true);
    };

    const toggleTopic = (topicId) => {
        setFormData(prev => ({
            ...prev,
            topics: prev.topics.includes(topicId)
                ? prev.topics.filter(id => id !== topicId)
                : [...prev.topics, topicId]
        }));
    };

    const filteredQuizzes = quizzes.filter(q =>
        q.title.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex justify-between items-center border-b border-white/5 pb-6">
                <div>
                    <h2 className="text-2xl font-bold text-white tracking-tight">Quiz Management</h2>
                    <p className="text-slate-400 mt-1">Create, edit, and manage assessments for your students</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => setShowAIGenerator(true)}
                        className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-bold hover:shadow-lg hover:shadow-purple-500/20 transition-all flex items-center gap-2"
                    >
                        <Sparkles className="w-4 h-4" />
                        AI Generator
                    </button>
                    <button
                        onClick={() => {
                            setEditingQuiz(null);
                            resetForm();
                            setShowModal(true);
                        }}
                        className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-500 text-white rounded-lg font-bold hover:shadow-lg hover:shadow-blue-500/20 transition-all flex items-center gap-2"
                    >
                        <Plus className="w-4 h-4" />
                        Create Quiz
                    </button>
                </div>
            </div>

            {/* Controls */}
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-[#13161f] p-4 rounded-xl border border-white/5 shadow-sm">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
                    <input
                        type="text"
                        placeholder="Search quizzes..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-4 py-2.5 bg-black/20 border border-white/10 rounded-lg text-sm text-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none placeholder:text-slate-600 transition-all"
                    />
                </div>

                <div className="flex items-center gap-2 w-full md:w-auto">
                    <button
                        onClick={() => setIsSelectionMode(!isSelectionMode)}
                        className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors border ${isSelectionMode ? 'bg-primary/10 text-primary border-primary/20' : 'bg-transparent text-slate-400 border-white/10 hover:text-white'}`}
                    >
                        {isSelectionMode ? 'Cancel Selection' : 'Select Multiple'}
                    </button>
                    {isSelectionMode && selectedQuizzes.length > 0 && (
                        <button
                            onClick={() => showAlert({
                                title: 'Delete Selected Quizzes',
                                message: `Are you sure you want to delete ${selectedQuizzes.length} quiz${selectedQuizzes.length > 1 ? 'zes' : ''}? This action cannot be undone.`,
                                type: 'error',
                                showCancel: true,
                                confirmText: 'Delete All',
                                onConfirm: handleBulkDelete
                            })}
                            className="px-3 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-sm font-bold hover:bg-red-500/20 transition-colors flex items-center gap-2"
                        >
                            <Trash2 className="w-4 h-4" />
                            Delete ({selectedQuizzes.length})
                        </button>
                    )}
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-[#13161f] border border-white/5 p-4 rounded-xl shadow-sm hover:shadow-md transition-all group">
                    <p className="text-sm text-slate-400 font-medium">Total Quizzes</p>
                    <p className="text-2xl font-bold text-white mt-1 group-hover:text-primary transition-colors">{quizzes.length}</p>
                </div>
                <div className="bg-[#13161f] border border-white/5 p-4 rounded-xl shadow-sm hover:shadow-md transition-all group">
                    <p className="text-sm text-slate-400 font-medium">Active</p>
                    <p className="text-2xl font-bold text-green-400 mt-1 shadow-green-400/20 drop-shadow-sm">
                        {quizzes.filter(q => q.is_active).length}
                    </p>
                </div>
                <div className="bg-[#13161f] border border-white/5 p-4 rounded-xl shadow-sm hover:shadow-md transition-all group">
                    <p className="text-sm text-slate-400 font-medium">Adaptive</p>
                    <p className="text-2xl font-bold text-purple-400 mt-1 shadow-purple-400/20 drop-shadow-sm">
                        {quizzes.filter(q => q.is_adaptive).length}
                    </p>
                </div>
                <div className="bg-[#13161f] border border-white/5 p-4 rounded-xl shadow-sm hover:shadow-md transition-all group">
                    <p className="text-sm text-slate-400 font-medium">Total Attempts</p>
                    <p className="text-2xl font-bold text-blue-400 mt-1 shadow-blue-400/20 drop-shadow-sm">
                        {quizzes.reduce((sum, q) => sum + (q.total_attempts || 0), 0)}
                    </p>
                </div>
            </div>

            {/* Bulk Actions (Selection Mode) */}
            {
                isSelectionMode && (
                    <div className="bg-[#13161f] border border-primary/20 p-4 rounded-xl flex items-center justify-between mb-6 animate-in slide-in-from-top-2 shadow-lg shadow-primary/5">
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={filteredQuizzes.length > 0 && selectedQuizzes.length === filteredQuizzes.length}
                                    onChange={toggleSelectAll}
                                    className="w-4 h-4 rounded border-slate-600 text-primary focus:ring-primary bg-black/50"
                                />
                                <span className="text-sm font-bold text-white">Select All</span>
                            </div>
                            <div className="h-4 w-px bg-white/10"></div>
                            <span className="text-sm font-bold text-primary">{selectedQuizzes.length} Selected</span>
                        </div>
                        {selectedQuizzes.length > 0 && (
                            <button
                                onClick={handleBulkDelete}
                                className="bg-red-500/10 text-red-400 border border-red-500/20 px-4 py-2 rounded-lg text-sm font-bold hover:bg-red-500/20 transition-all flex items-center gap-2"
                            >
                                <Trash2 className="w-4 h-4" />
                                Delete Selected
                            </button>
                        )}
                    </div>
                )
            }

            {/* Quizzes Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredQuizzes.length > 0 ? (
                    filteredQuizzes.map((quiz) => (
                        <QuizCard
                            key={quiz.id}
                            quiz={quiz}
                            topics={topics}
                            onEdit={() => openEditModal(quiz)}
                            onDelete={() => handleDelete(quiz.id)}
                            selected={selectedQuizzes.includes(quiz.id)}
                            onSelect={() => toggleSelectQuiz(quiz.id)}
                            selectionMode={isSelectionMode}
                        />
                    ))
                ) : (
                    <div className="col-span-full text-center py-20 bg-[#13161f] border border-white/5 border-dashed rounded-xl">
                        <div className="w-16 h-16 bg-black/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <ClipboardList className="w-8 h-8 text-slate-600" />
                        </div>
                        <h3 className="text-lg font-bold text-white mb-2">No quizzes found</h3>
                        <p className="text-slate-400">Try adjusting your search or create a new quiz.</p>
                    </div>
                )}
            </div>

            {/* Create/Edit Modal */}
            {/* Create/Edit Modal */}
            {
                showModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300" onClick={() => setShowModal(false)} />
                        <div className="relative bg-[#0f111a] border border-white/10 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl animate-in zoom-in-95 duration-200 ring-1 ring-white/10">
                            <div className="sticky top-0 bg-[#0f111a]/95 backdrop-blur z-10 border-b border-white/10 p-6 flex justify-between items-center">
                                <h2 className="text-xl font-bold text-white">
                                    {editingQuiz ? 'Edit Quiz' : 'Create New Quiz'}
                                </h2>
                                <button onClick={() => setShowModal(false)} className="p-2 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <form onSubmit={handleSubmit} className="p-6 space-y-6">
                                <div>
                                    <label className="block text-sm font-semibold text-slate-300 mb-1.5">Quiz Title *</label>
                                    <input
                                        type="text"
                                        value={formData.title}
                                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                        className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                                        placeholder="e.g., Basic Math Test"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-semibold text-slate-300 mb-1.5">Description</label>
                                    <textarea
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                        className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all h-24 resize-none"
                                        placeholder="Brief description of the quiz..."
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-semibold text-slate-300 mb-1.5">Select Topics * (at least one)</label>
                                    <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2 bg-black/20 border border-white/10 rounded-lg">
                                        {topics.filter(t => t.questions_count > 0).length === 0 && (
                                            <div className="col-span-2 py-4 text-center">
                                                <p className="text-sm text-slate-500">No topics found.</p>
                                                <p className="text-xs text-slate-600">Please add questions to topics first.</p>
                                            </div>
                                        )}
                                        {topics
                                            .filter(t => t.questions_count > 0)
                                            .map(topic => (
                                                <label key={topic.id} className={`flex items-center gap-3 cursor-pointer p-3 rounded-lg border transition-all ${formData.topics.includes(topic.id) ? 'bg-primary/10 border-primary/30' : 'bg-transparent border-transparent hover:bg-white/5 hover:border-white/5'}`}>
                                                    <div className={`w-5 h-5 rounded flex items-center justify-center border ${formData.topics.includes(topic.id) ? 'bg-primary border-primary' : 'border-slate-600 bg-black/40'}`}>
                                                        {formData.topics.includes(topic.id) && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                                                    </div>
                                                    {/* Hidden checkbox for logic */}
                                                    <input
                                                        type="checkbox"
                                                        className="hidden"
                                                        checked={formData.topics.includes(topic.id)}
                                                        onChange={() => toggleTopic(topic.id)}
                                                    />
                                                    <span className="text-sm font-medium text-slate-200">{topic.name} <span className="text-slate-500 text-xs">({topic.questions_count})</span></span>
                                                </label>
                                            ))}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-semibold text-slate-300 mb-1.5">Total Questions *</label>
                                        <input
                                            type="text"
                                            value={formData.total_questions || ''}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                if (val === '' || /^[0-9]*$/.test(val)) {
                                                    setFormData({ ...formData, total_questions: val });
                                                }
                                            }}
                                            className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-semibold text-slate-300 mb-1.5">Time Limit (mins) *</label>
                                        <input
                                            type="text"
                                            value={formData.time_limit || ''}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                if (val === '' || /^[0-9]*$/.test(val)) {
                                                    setFormData({ ...formData, time_limit: val });
                                                }
                                            }}
                                            className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                                            required
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-semibold text-slate-300 mb-1.5">Passing Score (%) *</label>
                                    <input
                                        type="text"
                                        value={formData.passing_score || ''}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            if (val === '' || /^[0-9]*$/.test(val)) {
                                                setFormData({ ...formData, passing_score: val });
                                            }
                                        }}
                                        className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                                        required
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-semibold text-slate-300 mb-1.5">Min Difficulty</label>
                                        <select
                                            value={formData.difficulty_min}
                                            onChange={(e) => setFormData({ ...formData, difficulty_min: parseInt(e.target.value) })}
                                            className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all appearance-none"
                                        >
                                            <option value="1">1 - Very Easy</option>
                                            <option value="2">2 - Easy</option>
                                            <option value="3">3 - Medium</option>
                                            <option value="4">4 - Hard</option>
                                            <option value="5">5 - Very Hard</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-semibold text-slate-300 mb-1.5">Max Difficulty</label>
                                        <select
                                            value={formData.difficulty_max}
                                            onChange={(e) => setFormData({ ...formData, difficulty_max: parseInt(e.target.value) })}
                                            className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all appearance-none"
                                        >
                                            <option value="1">1 - Very Easy</option>
                                            <option value="2">2 - Easy</option>
                                            <option value="3">3 - Medium</option>
                                            <option value="4">4 - Hard</option>
                                            <option value="5">5 - Very Hard</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="flex flex-col gap-3 p-4 bg-black/20 rounded-xl border border-white/5">
                                    <label className="flex items-center gap-3 cursor-pointer group">
                                        <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${formData.is_adaptive ? 'bg-primary border-primary' : 'border-slate-600 bg-black/40'}`}>
                                            {formData.is_adaptive && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                                        </div>
                                        <input
                                            type="checkbox"
                                            className="hidden"
                                            checked={formData.is_adaptive}
                                            onChange={(e) => setFormData({ ...formData, is_adaptive: e.target.checked })}
                                        />
                                        <div>
                                            <span className="block text-sm font-bold text-slate-200 group-hover:text-white">Adaptive Mode</span>
                                            <span className="block text-xs text-slate-500">Automatically adjust difficulty based on performance</span>
                                        </div>
                                    </label>

                                    <label className="flex items-center gap-3 cursor-pointer group">
                                        <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${formData.is_active ? 'bg-green-500 border-green-500' : 'border-slate-600 bg-black/40'}`}>
                                            {formData.is_active && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                                        </div>
                                        <input
                                            type="checkbox"
                                            className="hidden"
                                            checked={formData.is_active}
                                            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                        />
                                        <div>
                                            <span className="block text-sm font-bold text-slate-200 group-hover:text-white">Active Status</span>
                                            <span className="block text-xs text-slate-500">Make this quiz visible to students immediately</span>
                                        </div>
                                    </label>
                                </div>

                                {/* Question Type Settings */}
                                <div>
                                    <label className="block text-sm font-semibold text-slate-300 mb-1.5">Answer Type</label>
                                    <input
                                        type="text"
                                        value="Multiple Choice (MCQ)"
                                        disabled
                                        className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white/50 cursor-not-allowed focus:outline-none"
                                    />
                                    <p className="text-xs text-slate-500 mt-1">
                                        Select the type of questions for this quiz.
                                    </p>
                                </div>

                                {/* Retake Settings */}
                                <div className="border-t border-white/10 pt-4 space-y-4">
                                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wide">Advanced Settings</h3>

                                    <div className="flex flex-col gap-3">
                                        <label className="flex items-center gap-3 cursor-pointer group">
                                            <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${formData.allow_retakes ? 'bg-primary border-primary' : 'border-slate-600 bg-black/40'}`}>
                                                {formData.allow_retakes && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                                            </div>
                                            <input
                                                type="checkbox"
                                                className="hidden"
                                                checked={formData.allow_retakes}
                                                onChange={(e) => setFormData({ ...formData, allow_retakes: e.target.checked })}
                                            />
                                            <span className="text-sm font-medium text-slate-200 group-hover:text-white">Allow Retakes</span>
                                        </label>

                                        {formData.allow_retakes && (
                                            <div className="pl-8 animate-in slide-in-from-top-2">
                                                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Max Attempts</label>
                                                <input
                                                    type="number"
                                                    min="1"
                                                    max="999"
                                                    value={formData.max_attempts || ''}
                                                    onChange={(e) => setFormData({ ...formData, max_attempts: parseInt(e.target.value) })}
                                                    className="w-full md:w-1/2 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                                                />
                                                <p className="text-[10px] text-slate-500 mt-1">Set to 999 for unlimited attempts</p>
                                            </div>
                                        )}

                                        <div className="flex gap-6">
                                            <label className="flex items-center gap-3 cursor-pointer group">
                                                <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${formData.show_answers ? 'bg-primary border-primary' : 'border-slate-600 bg-black/40'}`}>
                                                    {formData.show_answers && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                                                </div>
                                                <input
                                                    type="checkbox"
                                                    className="hidden"
                                                    checked={formData.show_answers}
                                                    onChange={(e) => setFormData({ ...formData, show_answers: e.target.checked })}
                                                />
                                                <span className="text-sm font-medium text-slate-200 group-hover:text-white">Show Correct Answers</span>
                                            </label>

                                            <label className="flex items-center gap-3 cursor-pointer group">
                                                <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${formData.show_explanations ? 'bg-primary border-primary' : 'border-slate-600 bg-black/40'}`}>
                                                    {formData.show_explanations && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                                                </div>
                                                <input
                                                    type="checkbox"
                                                    className="hidden"
                                                    checked={formData.show_explanations}
                                                    onChange={(e) => setFormData({ ...formData, show_explanations: e.target.checked })}
                                                />
                                                <span className="text-sm font-medium text-slate-200 group-hover:text-white">Show Explanations</span>
                                            </label>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex gap-3 pt-6 border-t border-white/10 sticky bottom-0 bg-[#0f111a] pb-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowModal(false)}
                                        className="flex-1 px-4 py-3 bg-white/5 hover:bg-white/10 text-slate-300 font-bold rounded-xl transition-all"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="flex-1 btn-enterprise-primary"
                                        disabled={formData.topics.length === 0}
                                    >
                                        {editingQuiz ? 'Update Quiz' : 'Create Quiz'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }

            {/* AI Quiz Generator Modal */}
            <AIQuizGenerator
                isOpen={showAIGenerator}
                onClose={() => setShowAIGenerator(false)}
                onSuccess={() => {
                    setShowAIGenerator(false);
                    fetchData();
                }}
            />

            {/* Alert Modal */}
            <AlertModal
                isOpen={alertConfig.isOpen}
                onClose={closeAlert}
                onConfirm={alertConfig.onConfirm}
                title={alertConfig.title}
                message={alertConfig.message}
                type={alertConfig.type}
                showCancel={alertConfig.showCancel}
                confirmText={alertConfig.confirmText}
                cancelText={alertConfig.cancelText}
            />
        </div >
    );
}

function QuizCard({ quiz, topics, onEdit, onDelete, selected, onSelect, selectionMode }) {
    const quizTopics = topics.filter(t => quiz.topics?.includes(t.id));

    return (
        <div
            className={`
                relative bg-[#13161f] border rounded-xl transition-all duration-300 group overflow-hidden
                ${selected
                    ? 'border-primary ring-1 ring-primary shadow-lg shadow-primary/10'
                    : 'border-white/5 hover:border-primary/50 hover:shadow-xl hover:shadow-primary/5'
                }
            `}
            onClick={selectionMode ? onSelect : undefined}
        >
            {/* Selection Overlay */}
            {selectionMode && (
                <div className={`absolute inset-0 z-10 transition-colors ${selected ? 'bg-primary/5' : 'hover:bg-white/5 cursor-pointer'}`} />
            )}

            <div className="p-6">
                <div className="flex justify-between items-start mb-4 relative z-20">
                    <div className="flex items-start gap-3 flex-1">
                        {selectionMode && (
                            <div className="pt-1 animate-in fade-in zoom-in duration-200">
                                <div className={`w-5 h-5 rounded flex items-center justify-center border transition-all ${selected ? 'bg-primary border-primary' : 'border-slate-600 bg-black/40'}`}>
                                    {selected && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                                </div>
                            </div>
                        )}
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2 group-hover:text-primary transition-colors">{quiz.title}</h3>
                            <p className="text-sm text-slate-400 line-clamp-2 mb-3">
                                {quiz.description || 'No description provided'}
                            </p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={(e) => { e.stopPropagation(); onEdit(); }}
                            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-slate-400 hover:text-white"
                            title="Edit Quiz"
                        >
                            <Pencil className="w-4 h-4" />
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); onDelete(); }}
                            className="p-2 hover:bg-red-500/10 rounded-lg transition-colors text-slate-400 hover:text-red-400"
                            title="Delete Quiz"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Topics */}
                <div className="flex flex-wrap gap-2 mb-6">
                    {quizTopics.slice(0, 2).map(topic => (
                        <span key={topic.id} className="px-2.5 py-1 bg-white/5 border border-white/5 rounded-full text-xs font-medium text-slate-300">
                            {topic.name}
                        </span>
                    ))}
                    {quizTopics.length > 2 && (
                        <span className="px-2.5 py-1 bg-white/5 border border-white/5 rounded-full text-xs font-medium text-slate-300">
                            +{quizTopics.length - 2} more
                        </span>
                    )}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 mb-6">
                    <div className="flex items-center gap-2 text-xs text-slate-400 bg-black/20 p-2 rounded-lg border border-white/5">
                        <FileQuestion className="w-3.5 h-3.5 text-primary" />
                        <span>{quiz.total_questions || 0} Questions</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-400 bg-black/20 p-2 rounded-lg border border-white/5">
                        <Clock className="w-3.5 h-3.5 text-blue-400" />
                        <span>{quiz.time_limit || 0} Minutes</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-400 bg-black/20 p-2 rounded-lg border border-white/5 col-span-2">
                        <RotateCcw className="w-3.5 h-3.5 text-orange-400" />
                        <span>
                            {quiz.allow_retakes
                                ? (quiz.max_attempts >= 999 ? 'Unlimited Retakes Allowed' : `${quiz.max_attempts} Retakes Allowed`)
                                : 'No Retakes Allowed'}
                        </span>
                    </div>
                </div>

                {/* Badges & Properties */}
                <div className="flex flex-wrap gap-2 pt-4 border-t border-white/5">
                    {quiz.is_adaptive && (
                        <span className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-500/10 text-purple-400 rounded-lg text-xs font-bold border border-purple-500/20 shadow-sm shadow-purple-500/5">
                            <Sparkles className="w-3 h-3" />
                            Adaptive
                        </span>
                    )}
                    {quiz.is_active ? (
                        <span className="flex items-center gap-1.5 px-2.5 py-1 bg-green-500/10 text-green-400 rounded-lg text-xs font-bold border border-green-500/20 shadow-sm shadow-green-500/5">
                            <CheckCircle2 className="w-3 h-3" />
                            Active
                        </span>
                    ) : (
                        <span className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-500/10 text-slate-400 rounded-lg text-xs font-bold border border-slate-500/20">
                            <XCircle className="w-3 h-3" />
                            Inactive
                        </span>
                    )}

                    {/* Settings Badges */}
                    <div className="flex items-center gap-2 ml-auto">
                        {quiz.show_answers && (
                            <span className="w-6 h-6 rounded-full bg-white/5 flex items-center justify-center text-slate-400" title="Answers Visible">
                                <Eye className="w-3.5 h-3.5" />
                            </span>
                        )}
                        {quiz.show_explanations && (
                            <span className="w-6 h-6 rounded-full bg-white/5 flex items-center justify-center text-slate-400" title="Explanations Enabled">
                                <BookOpen className="w-3.5 h-3.5" />
                            </span>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
