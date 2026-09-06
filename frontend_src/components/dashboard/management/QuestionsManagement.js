'use client';

import { useState, useEffect } from 'react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { quizAPI } from '@/lib/api';
import {
    Plus,
    Edit,
    Trash2,
    Search,
    Filter,
    Loader2,
    FileQuestion,
    X,
    Upload,
    Download,
    FileSpreadsheet,
    ChevronLeft,
    ChevronRight,
    Search as SearchIcon,
    FileText,
    Edit3,
    FileSignature,
    CheckSquare,
    Info
} from 'lucide-react';
import AlertModal from '@/components/ui/AlertModal';
import PDFImportModal from '@/components/ui/PDFImportModal';
import ConfirmationModal from '@/components/ui/ConfirmationModal';
import TextQuestionForm from '@/components/quiz/TextQuestionForm';

export default function QuestionsManagement() {
    const [questions, setQuestions] = useState([]);
    const [topics, setTopics] = useState([]);
    const [subtopics, setSubtopics] = useState([]); // Added subtopics state
    const [loading, setLoading] = useState(false);
    const [isInitialLoading, setIsInitialLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterTopic, setFilterTopic] = useState('all');
    const [filterDifficulty, setFilterDifficulty] = useState('all');
    const [filterQuestionType, setFilterQuestionType] = useState('mcq'); // Default to mcq
    const [showModal, setShowModal] = useState(false);
    const [editingQuestion, setEditingQuestion] = useState(null);
    const [showImportModal, setShowImportModal] = useState(false);
    const [showPDFImportModal, setShowPDFImportModal] = useState(false);
    const [importFile, setImportFile] = useState(null);
    const [isImporting, setIsImporting] = useState(false);
    const [alertModal, setAlertModal] = useState({ isOpen: false, title: '', message: '', variant: 'info' });
    const [confirmationModal, setConfirmationModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null });
    const [selectedQuestions, setSelectedQuestions] = useState([]);
    const [isSelectionMode, setIsSelectionMode] = useState(false); // Enterprise Selection Mode
    const [showExportModal, setShowExportModal] = useState(false);
    const [exportCount, setExportCount] = useState(100);


    // Pagination State
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);

    const [formData, setFormData] = useState({
        question_text: '',
        question_type: 'mcq', // mcq
        topic: '',
        subtopic: '', // Added subtopic field
        option_a: '',
        option_b: '',
        option_c: '',
        option_d: '',
        correct_answer: 'A',
        difficulty_level: 3,
        explanation: ''
    });

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            fetchData(1);
        }, 500);
        return () => clearTimeout(timer);
    }, [searchTerm]);

    // Fetch on filter change
    useEffect(() => {
        fetchData(1);
    }, [filterTopic, filterDifficulty, filterQuestionType]);

    const fetchData = async (page = 1) => {
        setLoading(true);
        try {
            // If filters are applied, backend might not support filtering + pagination on same endpoint easily 
            // without custom filterset. Assuming backend 'list' handles basic pagination.
            // But we filter locally in 'filteredQuestions'. 
            // If we paginate on backend, local filtering only filters the CURRENT PAGE. 
            // For true pagination + filtering, we need backend filtering.
            // The USER asked for pagination. We re-enabled backend pagination. 
            // So we MUST use backend filtering if we want search to work across all pages.
            // For now, let's just implement basic pagination fetching.

            const params = {
                page: page,
                topic: filterTopic !== 'all' ? filterTopic : undefined,
                difficulty: filterDifficulty !== 'all' ? filterDifficulty : undefined,
                question_type: filterQuestionType !== 'all' ? filterQuestionType : undefined,
                search: searchTerm || undefined
            };

            const promises = [quizAPI.getQuestions(params)];

            // Only fetch topics and subtopics if they are empty
            if (topics.length === 0) promises.push(quizAPI.getTopics());
            if (subtopics.length === 0) promises.push(quizAPI.getSubtopics());

            const results = await Promise.all(promises);
            const questionsData = results[0];
            let topicsData = null;
            let subtopicsData = null;

            let resultIndex = 1;
            if (topics.length === 0) topicsData = results[resultIndex++];
            if (subtopics.length === 0) subtopicsData = results[resultIndex++];

            if (questionsData.results) {
                setQuestions(questionsData.results);
                setTotalItems(questionsData.count);
                setTotalPages(Math.ceil(questionsData.count / 20));
            } else {
                setQuestions(Array.isArray(questionsData) ? questionsData : []);
            }

            if (topicsData) {
                setTopics(Array.isArray(topicsData) ? topicsData : topicsData.results || []);
            }
            if (subtopicsData) {
                setSubtopics(Array.isArray(subtopicsData) ? subtopicsData : subtopicsData.results || []);
            }
            setCurrentPage(page);
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setLoading(false);
            setIsInitialLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // Use FormData if image is present
            if (formData.image && typeof formData.image !== 'string') {
                const formDataObj = new FormData();

                // Append all fields
                Object.keys(formData).forEach(key => {
                    if (key === 'image') {
                        formDataObj.append('image', formData.image);
                    } else if (key === 'required_keywords') {
                        formDataObj.append('required_keywords', JSON.stringify(formData[key]));
                    } else if (formData[key] !== null && formData[key] !== '') {
                        formDataObj.append(key, formData[key]);
                    }
                });

                if (editingQuestion) {
                    await quizAPI.updateQuestion(editingQuestion.id, formDataObj);
                } else {
                    await quizAPI.createQuestion(formDataObj);
                }
            } else {
                // Regular JSON payload
                const payload = { ...formData };
                if (!payload.subtopic) payload.subtopic = null;

                if (editingQuestion) {
                    await quizAPI.updateQuestion(editingQuestion.id, payload);
                } else {
                    await quizAPI.createQuestion(payload);
                }
            }

            setShowModal(false);
            setEditingQuestion(null);
            resetForm();
            fetchData();
        } catch (error) {
            console.error('Error saving question:', error);
            setAlertModal({
                isOpen: true,
                title: 'Error',
                message: 'Failed to save question',
                variant: 'error'
            });
        }
    };

    const handleDelete = async (id) => {
        setConfirmationModal({
            isOpen: true,
            title: 'Delete Question?',
            message: 'Are you sure you want to delete this question? This action cannot be undone.',
            onConfirm: async () => {
                try {
                    await quizAPI.deleteQuestion(id);
                    fetchData();
                    setAlertModal({
                        isOpen: true,
                        title: 'Success',
                        message: 'Question deleted successfully',
                        variant: 'success'
                    });
                } catch (error) {
                    setAlertModal({
                        isOpen: true,
                        title: 'Error',
                        message: 'Failed to delete question',
                        variant: 'error'
                    });
                }
            }
        });
    };

    const handleBulkDelete = () => {
        if (selectedQuestions.length === 0) return;

        setConfirmationModal({
            isOpen: true,
            title: 'Delete Selected Questions?',
            message: `Are you sure you want to delete ${selectedQuestions.length} questions? This action cannot be undone.`,
            onConfirm: async () => {
                try {
                    await Promise.all(selectedQuestions.map(id => quizAPI.deleteQuestion(id)));
                    setSelectedQuestions([]);
                    setIsSelectionMode(false); // Exit selection mode
                    fetchData(currentPage);
                    setAlertModal({
                        isOpen: true,
                        title: 'Success',
                        message: 'Selected questions deleted successfully',
                        variant: 'success'
                    });
                } catch (error) {
                    setAlertModal({
                        isOpen: true,
                        title: 'Error',
                        message: 'Failed to delete some questions',
                        variant: 'error'
                    });
                }
            }
        });
    };

    const toggleSelectQuestion = (id) => {
        setSelectedQuestions(prev =>
            prev.includes(id) ? prev.filter(qId => qId !== id) : [...prev, id]
        );
    };

    const toggleSelectAll = () => {
        if (selectedQuestions.length === filteredQuestions.length) {
            setSelectedQuestions([]);
        } else {
            setSelectedQuestions(filteredQuestions.map(q => q.id));
        }
    };


    const resetForm = () => {
        setFormData({
            question_text: '',
            question_type: 'mcq',
            topic: '',
            subtopic: '',
            option_a: '',
            option_b: '',
            option_c: '',
            option_d: '',
            correct_answer: 'A',
            difficulty_level: 3,
            explanation: '',
            image: null
        });
    };

    const openCreateModal = () => {
        setEditingQuestion(null);
        resetForm();
        setShowModal(true);
    };

    const handleExportClick = () => {
        setShowExportModal(true);
    };

    const handleConfirmExport = async () => {
        setLoading(true);
        try {
            // Fetch questions specifically for export with custom page_size
            const params = {
                page: 1,
                page_size: selectedQuestions.length > 0 ? selectedQuestions.length : exportCount,
                topic: filterTopic !== 'all' ? filterTopic : undefined,
                difficulty: filterDifficulty !== 'all' ? filterDifficulty : undefined,
                question_type: filterQuestionType !== 'all' ? filterQuestionType : undefined,
                search: searchTerm || undefined,
                ids: selectedQuestions.length > 0 ? selectedQuestions.join(',') : undefined
            };

            const response = await quizAPI.getQuestions(params);
            const questionsToExport = response.results || response || [];

            if (questionsToExport.length === 0) {
                setAlertModal({
                    isOpen: true,
                    title: 'No Questions',
                    message: 'There are no questions to export with current filters.',
                    variant: 'info'
                });
                return;
            }

            const doc = new jsPDF();
            doc.text('Question Bank Export', 14, 15);

            const tableData = questionsToExport.map(q => [
                q.topic_name || '',
                q.question_text || '',
                q.question_type === 'mcq' ? `A: ${q.option_a}\nB: ${q.option_b}\nC: ${q.option_c}\nD: ${q.option_d}` : '',
                q.correct_answer || '',
                q.difficulty_level || '',
                q.explanation || ''
            ]);

            autoTable(doc, {
                head: [['Topic', 'Question', 'Options/Type', 'Correct', 'Diff', 'Explanation']],
                body: tableData,
                startY: 20,
                styles: { fontSize: 8 },
                columnStyles: {
                    1: { cellWidth: 50 },
                    2: { cellWidth: 40 }
                }
            });

            doc.save(`questions_export_${new Date().toISOString().split('T')[0]}.pdf`);

            setAlertModal({
                isOpen: true,
                title: 'Success',
                message: `Successfully exported ${questionsToExport.length} questions to PDF.`,
                variant: 'success'
            });

        } catch (error) {
            console.error('Export failed:', error);
            setAlertModal({
                isOpen: true,
                title: 'Error',
                message: 'Failed to export questions to PDF.',
                variant: 'error'
            });
        } finally {
            setLoading(false);
        }
    };


    const handleImport = async (e) => {
        e.preventDefault();
        if (!importFile) return;

        setIsImporting(true);
        const formData = new FormData();
        formData.append('file', importFile);

        try {
            await quizAPI.bulkUploadQuestions(formData);
            setAlertModal({
                isOpen: true,
                title: 'Success',
                message: 'Questions imported successfully!',
                variant: 'success'
            });
            setShowImportModal(false);
            setImportFile(null);
            fetchData();
        } catch (error) {
            console.error('Import failed:', error);
            setAlertModal({
                isOpen: true,
                title: 'Import Failed',
                message: error.response?.data?.error || 'Failed to import questions. Please check the file format.',
                variant: 'danger'
            });
        } finally {
            setIsImporting(false);
        }
    };

    const openEditModal = (question) => {
        setEditingQuestion(question);
        setFormData({
            question_text: question.question_text,
            question_type: question.question_type || 'mcq',
            topic: question.topic,
            subtopic: question.subtopic || '',
            option_a: question.option_a || '',
            option_b: question.option_b || '',
            option_c: question.option_c || '',
            option_d: question.option_d || '',
            correct_answer: question.correct_answer || 'A',
            difficulty_level: question.difficulty_level,
            explanation: question.explanation || '',
            model_answer: question.model_answer || '',
            required_keywords: question.required_keywords || [],
            min_words: question.min_words || 30,
            max_words: question.max_words || 150,
            auto_grade: question.auto_grade !== undefined ? question.auto_grade : true,
            image: question.image || null
        });
        setShowModal(true);
    };

    // Server-side filtering now active, questions array IS the filtered list
    const filteredQuestions = questions; // Alias for compatibility with existing render logic

    // const filteredQuestions = questions.filter(q => {
    //     const matchesSearch = q.question_text.toLowerCase().includes(searchTerm.toLowerCase());
    //     const matchesTopic = filterTopic === 'all' || q.topic === parseInt(filterTopic);
    //     const matchesDifficulty = filterDifficulty === 'all' || q.difficulty_level.toString() === filterDifficulty;
    //     return matchesSearch && matchesTopic && matchesDifficulty;
    // });

    if (isInitialLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-10 h-10 animate-spin text-primary" />
                    <p className="text-muted-foreground animate-pulse">Loading Question Bank...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold">Question Bank</h2>
                    <p className="text-muted-foreground">Manage quiz questions and answers</p>
                </div>
            </div>
            <div className="flex gap-2">
                <button
                    onClick={() => {
                        setIsSelectionMode(!isSelectionMode);
                        if (!isSelectionMode) setSelectedQuestions([]);
                    }}
                    className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 shadow-sm ${isSelectionMode ? 'bg-primary text-white ring-2 ring-primary/20' : 'bg-card border border-border text-foreground hover:bg-secondary'
                        }`}
                >
                    <CheckSquare className="w-4 h-4" />
                    {isSelectionMode ? 'Exit Selection' : 'Selection Mode'}
                </button>
                <button
                    onClick={handleExportClick}
                    className="bg-card border border-border text-foreground px-4 py-2 rounded-lg font-medium hover:bg-secondary transition-all flex items-center gap-2 shadow-sm"
                >
                    <FileText className="w-4 h-4" />
                    Export PDF
                </button>
                <button
                    onClick={() => setShowPDFImportModal(true)}
                    className="bg-purple-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-purple-700 transition-all flex items-center gap-2 shadow-sm shadow-purple-500/20"
                >
                    <FileText className="w-4 h-4" />
                    Import PDF (AI)
                </button>
                <button
                    onClick={openCreateModal}
                    className="bg-primary text-primary-foreground px-4 py-2 rounded-lg font-medium hover:bg-primary/90 transition-all flex items-center gap-2 shadow-sm shadow-primary/20"
                >
                    <Plus className="w-5 h-5" />
                    Add Question
                </button>
            </div>


            {/* Filters */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search questions..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-10 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    {loading && !isInitialLoading && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2">
                            <Loader2 className="w-4 h-4 animate-spin text-primary" />
                        </div>
                    )}
                </div>
                <div className="relative">
                    <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <select
                        value={filterTopic}
                        onChange={(e) => setFilterTopic(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary appearance-none cursor-pointer"
                    >
                        <option value="all">All Topics</option>
                        {topics.map(topic => (
                            <option key={topic.id} value={topic.id}>{topic.name}</option>
                        ))}
                    </select>
                </div>
                <div className="relative">
                    <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <select
                        value={filterDifficulty}
                        onChange={(e) => setFilterDifficulty(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary appearance-none cursor-pointer"
                    >
                        <option value="all">All Difficulties</option>
                        <option value="1">Very Easy</option>
                        <option value="2">Easy</option>
                        <option value="3">Medium</option>
                        <option value="4">Hard</option>
                        <option value="5">Very Hard</option>
                    </select>
                </div>
                <div className="relative">
                    <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        value="Multiple Choice"
                        disabled
                        className="w-full pl-10 pr-4 py-3 bg-secondary/50 border border-border rounded-lg text-muted-foreground cursor-not-allowed focus:outline-none"
                    />
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-card border border-border p-4 rounded-xl shadow-sm">
                    <p className="text-sm text-muted-foreground">Total Questions</p>
                    <p className="text-2xl font-bold text-foreground">{totalItems}</p>
                </div>
                <div className="bg-card border border-border p-4 rounded-xl shadow-sm">
                    <p className="text-sm text-muted-foreground">Filtered</p>
                    <p className="text-2xl font-bold text-foreground">{totalItems}</p>
                </div>
                <div className="bg-card border border-border p-4 rounded-xl shadow-sm">
                    <p className="text-sm text-muted-foreground">Topics</p>
                    <p className="text-2xl font-bold text-foreground">{topics.length}</p>
                </div>
            </div>

            {/* Bulk Actions (Selection Mode) */}
            {isSelectionMode && (
                <div className="bg-secondary/50 border border-border p-4 rounded-xl flex items-center justify-between mb-4 animate-in slide-in-from-top-2">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={filteredQuestions.length > 0 && selectedQuestions.length === filteredQuestions.length}
                                onChange={toggleSelectAll}
                                className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                            />
                            <span className="text-sm font-medium">Select All</span>
                        </div>
                        <div className="h-4 w-px bg-border"></div>
                        <span className="text-sm font-medium text-primary">{selectedQuestions.length} Selected</span>
                    </div>
                    {selectedQuestions.length > 0 && (
                        <button
                            onClick={handleBulkDelete}
                            className="bg-destructive text-destructive-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-destructive/90 transition-colors flex items-center gap-2"
                        >
                            <Trash2 className="w-4 h-4" />
                            Delete
                        </button>
                    )}
                </div>
            )}

            {/* Old Selection Header removed as it's now integrated in Bulk Bar */}

            {/* Selection Header */}


            {/* Questions List */}
            <div className={`space-y-3 transition-opacity duration-200 ${loading && !isInitialLoading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
                {filteredQuestions.length > 0 ? (
                    filteredQuestions.map((question) => (
                        <QuestionCard
                            key={question.id}
                            question={question}
                            topics={topics}
                            subtopics={subtopics}
                            onEdit={() => openEditModal(question)}
                            onDelete={() => handleDelete(question.id)}
                            selected={selectedQuestions.includes(question.id)}
                            onSelect={() => toggleSelectQuestion(question.id)}
                            selectionMode={isSelectionMode}
                            setAlertModal={setAlertModal}
                        />
                    ))
                ) : (
                    <div className="text-center py-12 bg-card rounded-xl border border-border border-dashed">
                        <FileQuestion className="w-16 h-16 mx-auto text-muted-foreground mb-4 opacity-50" />
                        <p className="text-muted-foreground font-medium">No questions found</p>
                    </div>
                )}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
                <div className="flex justify-between items-center mt-6">
                    <p className="text-sm text-muted-foreground">
                        Showing {questions.length} of {totalItems} questions
                    </p>
                    <div className="flex gap-2">
                        <button
                            onClick={() => fetchData(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="p-2 rounded-lg border border-border hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed text-foreground"
                        >
                            <ChevronLeft className="w-5 h-5" />
                        </button>
                        <span className="flex items-center px-4 font-medium text-muted-foreground">
                            Page {currentPage} of {totalPages}
                        </span>
                        <button
                            onClick={() => fetchData(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className="p-2 rounded-lg border border-border hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed text-foreground"
                        >
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            )}

            {/* Create/Edit Modal */}
            {
                showModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                        <div className="bg-background border border-border rounded-xl w-full max-w-2xl shadow-2xl max-h-[90vh] overflow-y-auto">
                            <div className="sticky top-0 bg-background border-b border-border p-6 flex justify-between items-center">
                                <h2 className="text-xl font-bold">
                                    {editingQuestion ? 'Edit Question' : 'Create New Question'}
                                </h2>
                                <button onClick={() => setShowModal(false)} className="p-2 hover:bg-secondary rounded-lg">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <form onSubmit={handleSubmit} className="p-6 space-y-4">
                                {/* Question Type Selector */}
                                <div>
                                    <label className="block text-sm font-medium mb-2">Question Type *</label>
                                    <div className="relative">
                                        <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                                        <input
                                            type="text"
                                            value="Multiple Choice (MCQ)"
                                            disabled
                                            className="w-full pl-10 pr-4 py-3 bg-secondary/50 border border-border rounded-lg text-muted-foreground cursor-not-allowed"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-2">Topic *</label>
                                    <select
                                        value={formData.topic}
                                        onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                                        className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        required
                                    >
                                        <option value="">Select a topic</option>
                                        {topics.map(topic => (
                                            <option key={topic.id} value={topic.id}>{topic.name}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Subtopic Selection */}
                                <div>
                                    <label className="block text-sm font-medium mb-2">Subtopic (Optional)</label>
                                    <select
                                        value={formData.subtopic || ''}
                                        onChange={(e) => setFormData({ ...formData, subtopic: e.target.value })}
                                        className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                        disabled={!formData.topic}
                                    >
                                        <option value="">Select Subtopic...</option>
                                        {subtopics
                                            .filter(s => s.topic === formData.topic)
                                            .map(subtopic => (
                                                <option key={subtopic.id} value={subtopic.id}>
                                                    {subtopic.name}
                                                </option>
                                            ))
                                        }
                                    </select>
                                    {!formData.topic && <p className="text-xs text-muted-foreground mt-1">Select a topic first</p>}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-2">Question Text *</label>
                                    <textarea
                                        value={formData.question_text}
                                        onChange={(e) => setFormData({ ...formData, question_text: e.target.value })}
                                        className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary h-24 resize-none"
                                        placeholder="Enter your question..."
                                        required
                                    />
                                </div>


                                {/* MCQ Fields */}
                                {formData.question_type === 'mcq' && (
                                    <>
                                        <div className="grid grid-cols-2 gap-4">
                                            {['A', 'B', 'C', 'D'].map((option) => (
                                                <div key={option}>
                                                    <label className="block text-sm font-medium mb-2">Option {option} *</label>
                                                    <input
                                                        type="text"
                                                        value={formData[`option_${option.toLowerCase()}`]}
                                                        onChange={(e) => setFormData({ ...formData, [`option_${option.toLowerCase()}`]: e.target.value })}
                                                        className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                                        placeholder={`Option ${option}`}
                                                        required
                                                    />
                                                </div>
                                            ))}
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium mb-2">Correct Answer *</label>
                                            <div className="flex gap-4">
                                                {['A', 'B', 'C', 'D'].map((option) => (
                                                    <label key={option} className="flex items-center gap-2 cursor-pointer">
                                                        <input
                                                            type="radio"
                                                            name="correct_answer"
                                                            value={option}
                                                            checked={formData.correct_answer === option}
                                                            onChange={(e) => setFormData({ ...formData, correct_answer: e.target.value })}
                                                            className="w-4 h-4"
                                                        />
                                                        <span>{option}</span>
                                                    </label>
                                                ))}
                                            </div>
                                        </div>
                                    </>
                                )}

                                {/* Text Question Fields */}

                                <div>
                                    <label className="block text-sm font-medium mb-2">Difficulty Level *</label>
                                    <select
                                        value={formData.difficulty_level}
                                        onChange={(e) => setFormData({ ...formData, difficulty_level: parseInt(e.target.value) })}
                                        className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    >
                                        <option value="1">1 - Very Easy</option>
                                        <option value="2">2 - Easy</option>
                                        <option value="3">3 - Medium</option>
                                        <option value="4">4 - Hard</option>
                                        <option value="5">5 - Very Hard</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-2">Explanation (Optional)</label>
                                    <textarea
                                        value={formData.explanation}
                                        onChange={(e) => setFormData({ ...formData, explanation: e.target.value })}
                                        className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary h-20 resize-none"
                                        placeholder="Explain why the answer is correct..."
                                    />
                                </div>

                                <div className="flex gap-3 pt-4">
                                    <button
                                        type="button"
                                        onClick={() => setShowModal(false)}
                                        className="flex-1 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition-all"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="flex-1 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-all"
                                    >
                                        {editingQuestion ? 'Update Question' : 'Create Question'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }

            {/* Import Modal */}
            {showImportModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="bg-card border border-border rounded-2xl w-full max-w-md p-6 m-4 shadow-2xl animate-in zoom-in-95">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold font-foreground">Import Questions</h3>
                            <button
                                onClick={() => setShowImportModal(false)}
                                className="p-2 hover:bg-secondary rounded-full transition-colors"
                            >
                                <X className="w-5 h-5 text-muted-foreground" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div className="bg-secondary/50 p-4 rounded-xl border border-border">
                                <p className="text-sm font-semibold text-primary mb-2">Supported Formats: CSV, Excel (.xlsx)</p>
                                <p className="text-xs text-muted-foreground">
                                    <strong>Required:</strong> topic_name, question_text, difficulty_level<br />
                                    <strong>MCQ:</strong> option_a, option_b, option_c, option_d, correct_answer<br />
                                    <strong>Text:</strong> question_type (short_answer), model_answer
                                </p>
                            </div>

                            <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary/50 transition-colors cursor-pointer relative bg-card">
                                <input
                                    type="file"
                                    accept=".csv,.xlsx,.xls"
                                    onChange={(e) => setImportFile(e.target.files[0])}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                />
                                <div className="flex flex-col items-center gap-2 pointer-events-none">
                                    {importFile ? (
                                        <>
                                            <FileSpreadsheet className="w-8 h-8 text-green-500" />
                                            <span className="text-sm font-medium text-foreground">{importFile.name}</span>
                                        </>
                                    ) : (
                                        <>
                                            <Upload className="w-8 h-8 text-muted-foreground/50" />
                                            <span className="text-sm font-medium text-muted-foreground">Click to upload or drag and drop</span>
                                        </>
                                    )}
                                </div>
                            </div>

                            <div className="flex gap-3 mt-6">
                                <button
                                    onClick={() => setShowImportModal(false)}
                                    className="flex-1 px-4 py-2 rounded-lg font-semibold text-muted-foreground hover:bg-secondary transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleImport}
                                    disabled={!importFile || isImporting}
                                    className="flex-1 bg-primary text-primary-foreground px-4 py-2 rounded-lg font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                    {isImporting ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Importing...
                                        </>
                                    ) : (
                                        'Import Questions'
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <ConfirmationModal
                isOpen={confirmationModal.isOpen}
                onClose={() => setConfirmationModal({ ...confirmationModal, isOpen: false })}
                title={confirmationModal.title}
                message={confirmationModal.message}
                onConfirm={confirmationModal.onConfirm}
            />

            <AlertModal
                isOpen={alertModal.isOpen}
                onClose={() => setAlertModal({ ...alertModal, isOpen: false })}
                title={alertModal.title}
                message={alertModal.message}
                variant={alertModal.variant}
            />

            {/* PDF Import Modal */}
            <PDFImportModal
                isOpen={showPDFImportModal}
                onClose={() => setShowPDFImportModal(false)}
                topics={topics}
                subtopics={subtopics} // Pass subtopics
                onSuccess={() => {
                    fetchData();
                    setShowPDFImportModal(false);
                }}
            />
            {/* Export Modal */}
            {showExportModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-card w-full max-w-md shadow-2xl rounded-2xl border border-border p-6 font-sans">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="text-xl font-bold text-foreground">Export Questions</h3>
                                <p className="text-sm text-muted-foreground">Select how many items you want to export</p>
                            </div>
                            <button
                                onClick={() => setShowExportModal(false)}
                                className="p-2 hover:bg-accent rounded-lg text-muted-foreground transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-semibold text-foreground mb-2">
                                    Number of items to export
                                </label>
                                <div className="relative">
                                    <input
                                        type="number"
                                        min="1"
                                        max="1000"
                                        value={exportCount}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            setExportCount(val === '' ? '' : parseInt(val));
                                        }}
                                        className="w-full pl-4 pr-24 py-3 border border-input bg-background rounded-xl focus:ring-2 focus:ring-primary outline-none text-foreground font-medium transition-all [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                                    />
                                    <div className="absolute right-3 top-1/2 -translate-y-1/2 px-2 py-1 bg-secondary rounded-lg text-[10px] font-black text-muted-foreground uppercase tracking-wider border border-border/50 pointer-events-none">
                                        Max 1000
                                    </div>
                                </div>
                                {selectedQuestions.length > 0 ? (
                                    <div className="flex items-center gap-2 mt-3 p-3 bg-primary/5 rounded-lg border border-primary/10 text-primary">
                                        <CheckSquare className="w-4 h-4" />
                                        <p className="text-[11px] leading-tight font-bold">
                                            Exporting {selectedQuestions.length} manually selected questions.
                                        </p>
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-2 mt-3 p-3 bg-secondary/50 rounded-lg">
                                        <Info className="w-4 h-4 text-primary" />
                                        <p className="text-[11px] text-muted-foreground leading-tight">
                                            Total available with current filters: <span className="text-foreground font-bold">{totalItems}</span>.
                                            Questions will be exported based on your active filters and search.
                                        </p>
                                    </div>
                                )}
                            </div>

                            <div className="flex justify-end gap-3 pt-6 border-t border-border mt-4">
                                <button
                                    onClick={() => setShowExportModal(false)}
                                    className="px-5 py-2.5 text-sm font-bold text-muted-foreground hover:bg-accent rounded-xl transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleConfirmExport}
                                    disabled={loading || !exportCount}
                                    className="px-6 py-2.5 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-primary/20 transition-all active:scale-95"
                                >
                                    {loading ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Download className="w-4 h-4" />
                                    )}
                                    Start Export
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>

    );
}

function QuestionCard({ question, topics, subtopics, onEdit, onDelete, selected, onSelect, selectionMode, setAlertModal }) {
    const topic = topics.find(t => t.id === question.topic);
    const subtopic = subtopics ? subtopics.find(s => s.id === question.subtopic) : null;
    const [isExpanded, setIsExpanded] = useState(false);

    // Matching difficulty colors from the reference image exactly
    const difficultyStyles = {
        1: { bg: 'bg-primary', text: 'text-primary-foreground', label: 'Very Easy' },
        2: { bg: 'bg-primary', text: 'text-primary-foreground', label: 'Easy' },
        3: { bg: 'bg-amber-500', text: 'text-white', label: 'Medium' },
        4: { bg: 'bg-orange-600', text: 'text-white', label: 'Hard' },
        5: { bg: 'bg-rose-600', text: 'text-white', label: 'Very Hard' }
    };

    const style = difficultyStyles[question.difficulty_level] || difficultyStyles[3];

    return (
        <div
            className={`group bg-white dark:bg-card border border-border/60 p-7 rounded-2xl transition-shadow duration-300 hover:shadow-lg relative overflow-hidden ${selected ? 'ring-2 ring-primary' : ''}`}
            onClick={() => selectionMode && onSelect()}
        >
            {/* Selection Checkbox */}
            {selectionMode && (
                <div className="absolute top-4 left-4 z-10">
                    <div className={`w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all ${selected
                        ? 'bg-primary border-primary text-white'
                        : 'bg-white/80 border-gray-300'
                        }`}>
                        {selected && <CheckSquare className="w-4 h-4" />}
                    </div>
                </div>
            )}

            {/* Header: Question & Action Icons */}
            <div className={`flex justify-between items-start gap-4 mb-3 ${selectionMode ? 'pl-8' : ''}`}>
                <div className="flex-1">
                    <h3 className="text-lg font-medium text-foreground tracking-tight">
                        {question.question_text}
                    </h3>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={(e) => { e.stopPropagation(); onEdit(); }}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                        title="Edit"
                    >
                        <Edit className="w-4.5 h-4.5" />
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); onDelete(); }}
                        className="text-rose-400 hover:text-rose-500 transition-colors"
                        title="Delete"
                    >
                        <Trash2 className="w-4.5 h-4.5" />
                    </button>
                </div>
            </div>

            {/* Badges: Topic & Difficulty */}
            <div className="flex items-center gap-2 mb-8">
                <span className="px-4 py-1 bg-secondary text-muted-foreground rounded-full text-xs font-bold leading-none flex items-center h-7 shadow-sm">
                    {question.topic_name || topic?.name || 'Unknown Topic'}
                    {subtopic && <span className="opacity-50 font-normal ml-1"> / {subtopic.name}</span>}
                </span>
                <span className={`px-4 py-1 ${style.bg} ${style.text} rounded-full text-xs font-bold leading-none flex items-center h-7 shadow-sm`}>
                    {style.label}
                </span>
            </div>

            {/* Question Image (if exists) */}
            {question.image && (
                <div className="mb-8 rounded-xl overflow-hidden border border-border bg-slate-50/50">
                    <img src={question.image} alt="Reference" className="max-h-80 mx-auto object-contain" />
                </div>
            )}

            <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-4">
                    {['A', 'B', 'C', 'D'].map((opt) => {
                        const val = question[`option_${opt.toLowerCase()}`];
                        if (!val) return null;
                        const isCorrect = question.correct_answer === opt;
                        return (
                            <div
                                key={opt}
                                className={`flex items-center gap-4 p-4 rounded-xl transition-all border ${isCorrect
                                    ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-800 dark:text-emerald-400 shadow-sm'
                                    : 'bg-secondary/40 border-transparent text-foreground/80'
                                    }`}
                            >
                                <span className={`font-bold text-[14px] ${isCorrect ? 'text-emerald-700' : 'text-muted-foreground'}`}>
                                    {opt}.
                                </span>
                                <span className="text-[14.5px] flex-1 leading-normal font-medium">{val}</span>
                                {isCorrect && (
                                    <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center text-white text-[10px]">
                                        ✓
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Explanation Section */}
                {question.explanation && (
                    <div className="mt-10 p-6 rounded-2xl bg-primary/5 border border-primary/10">
                        <div className="flex items-center gap-2 mb-3 text-primary">
                            <Info className="w-4 h-4" />
                            <h4 className="text-[11px] font-bold uppercase tracking-widest">Educational Rationale</h4>
                        </div>
                        <p className="text-[13.5px] text-muted-foreground leading-relaxed italic">
                            "{question.explanation}"
                        </p>
                    </div>
                )}
            </div>

            {/* Footer: Metadata & Tracking */}
            <div className="mt-8 pt-5 border-t border-border/40 flex items-center justify-between text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                <div className="flex gap-8">
                    <div className="flex flex-col gap-1.5" title="Percentage of students who answered correctly">
                        <span className="text-muted-foreground/70">Success Rate</span>
                        <span className="text-foreground text-xs font-black">
                            {question.times_asked > 0
                                ? `${Math.round((question.times_correct / question.times_asked) * 100)}%`
                                : '0%'}
                        </span>
                    </div>
                    <div className="flex flex-col gap-1.5" title="Total number of times this question has been answered">
                        <span className="text-muted-foreground/70">Instances</span>
                        <span className="text-foreground text-xs font-black">{question.times_asked}</span>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 bg-secondary/50 dark:bg-white/5 px-3 py-2 rounded-lg border border-border/50 text-foreground/80">
                        <span className="select-all">ID: <span className="font-mono text-foreground">{question.id.substring(0, 8)}</span></span>
                    </div>
                </div>
            </div>
        </div>
    );
}

