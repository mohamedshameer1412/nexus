'use client';

import { useState } from 'react';
import { quizAPI } from '@/lib/api';
import { Upload, X, FileText, Sparkles, Check, AlertCircle, Trash2, Edit2, Info } from 'lucide-react';
import Toast from './Toast';
import { parseApiError } from '@/lib/errorHandler';

export default function PDFImportModal({ isOpen, onClose, topics, subtopics = [], onSuccess }) {
    const [step, setStep] = useState(1); // 1: Upload, 2: Review, 3: Confirm
    const [pdfFile, setPdfFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [importing, setImporting] = useState(false);
    const [parsedQuestions, setParsedQuestions] = useState([]);
    const [selectedTopic, setSelectedTopic] = useState('');
    const [selectedSubtopic, setSelectedSubtopic] = useState('');
    const [toast, setToast] = useState(null);
    const [editingIndex, setEditingIndex] = useState(null);
    const [editedQuestion, setEditedQuestion] = useState(null);

    if (!isOpen) return null;

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && file.type === 'application/pdf') {
            if (file.size > 10 * 1024 * 1024) {
                setToast({ message: 'File size must be less than 10MB', type: 'error', title: 'File Too Large' });
                return;
            }
            setPdfFile(file);
        } else {
            setToast({ message: 'Please select a valid PDF file', type: 'error', title: 'Invalid File' });
        }
    };

    const handleUploadAndParse = async () => {
        if (!pdfFile) {
            setToast({ message: 'Please select a PDF file', type: 'error', title: 'No File Selected' });
            return;
        }

        setUploading(true);
        try {
            const initialResult = await quizAPI.importPDF(pdfFile, true);

            if (initialResult.task_id) {
                const pollInterval = setInterval(async () => {
                    try {
                        const result = await quizAPI.checkImportStatus(initialResult.task_id);
                        if (result.status !== 'processing') {
                            clearInterval(pollInterval);
                            setUploading(false);
                            
                            if (result.status === 'success') {
                                console.log("PARSED QUESTIONS DEBUG:", result.questions);
                                setParsedQuestions(result.questions);
                                setStep(2);
                                setToast({ message: `Successfully parsed ${result.total_questions} questions!`, type: 'success', title: 'Success' });
                            } else if (result.status === 'partial_success') {
                                const detailedError = result.error ? `: ${result.error}` : '';
                                setToast({ message: result.message + detailedError, type: 'warning', title: 'Partial Success' });
                            } else if (result.status === 'error') {
                                setToast({ message: result.message || 'Failed to parse PDF', type: 'error', title: 'Error' });
                            }
                        }
                    } catch (error) {
                        clearInterval(pollInterval);
                        setUploading(false);
                        const parsedError = parseApiError(error);
                        setToast({ message: parsedError.message, type: 'error', title: parsedError.title });
                    }
                }, 3000);
            } else {
               setUploading(false);
               setToast({ message: 'Failed to start AI parsing.', type: 'error', title: 'Error' });
            }
        } catch (error) {
            setUploading(false);
            const parsedError = parseApiError(error);
            setToast({
                message: parsedError.message,
                type: 'error',
                title: parsedError.title
            });
        }
    };

    const handleEditQuestion = (index) => {
        setEditingIndex(index);
        setEditedQuestion({ ...parsedQuestions[index] });
    };

    const handleSaveEdit = () => {
        const updated = [...parsedQuestions];
        updated[editingIndex] = editedQuestion;
        setParsedQuestions(updated);
        setEditingIndex(null);
        setEditedQuestion(null);
    };

    const handleDeleteQuestion = (index) => {
        setParsedQuestions(prev => prev.filter((_, i) => i !== index));
        setToast({ message: 'Question removed', type: 'info', title: 'Removed' });
    };

    const handleConfirmImport = async () => {
        if (!selectedTopic) {
            setToast({ message: 'Please select a topic', type: 'error', title: 'Topic Required' });
            return;
        }

        if (parsedQuestions.length === 0) {
            setToast({ message: 'No questions to import', type: 'error', title: 'No Questions' });
            return;
        }

        setImporting(true);
        try {
            const result = await quizAPI.confirmImport(
                parsedQuestions,
                selectedTopic,
                selectedSubtopic || null
            );

            setToast({ message: result.message, type: 'success', title: 'Success' });
            setTimeout(() => {
                onSuccess();
                handleClose();
            }, 1500);
        } catch (error) {
            const parsedError = parseApiError(error);
            setToast({
                message: parsedError.message,
                type: 'error',
                title: parsedError.title
            });
        } finally {
            setImporting(false);
        }
    };

    const handleClose = () => {
        setStep(1);
        setPdfFile(null);
        setParsedQuestions([]);
        setSelectedTopic('');
        setSelectedSubtopic('');
        setEditingIndex(null);
        setEditedQuestion(null);
        onClose();
    };

    const filteredSubtopics = selectedTopic ? subtopics.filter(s => s.topic == selectedTopic) : [];

    return (
        <>
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
                <div className="bg-card rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
                    {/* Header */}
                    <div className="flex justify-between items-center p-6 border-b border-slate-200 bg-gradient-to-r from-primary/5 to-purple-500/5">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-foreground">Import Questions from PDF</h2>
                                <p className="text-sm text-muted-foreground">AI-powered question extraction</p>
                            </div>
                        </div>
                        <button onClick={handleClose} className="text-muted-foreground hover:text-foreground transition-colors">
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    {/* Progress Steps */}
                    <div className="flex items-center justify-center gap-4 p-4 bg-secondary border-b border-border">
                        <div className={`flex items-center gap-2 ${step >= 1 ? 'text-primary' : 'text-muted-foreground'}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-primary text-white' : 'bg-slate-200'}`}>
                                {step > 1 ? <Check className="w-5 h-5" /> : '1'}
                            </div>
                            <span className="font-medium">Upload</span>
                        </div>
                        <div className="w-12 h-0.5 bg-slate-200" />
                        <div className={`flex items-center gap-2 ${step >= 2 ? 'text-primary' : 'text-muted-foreground'}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-primary text-white' : 'bg-slate-200'}`}>
                                {step > 2 ? <Check className="w-5 h-5" /> : '2'}
                            </div>
                            <span className="font-medium">Review</span>
                        </div>
                        <div className="w-12 h-0.5 bg-slate-200" />
                        <div className={`flex items-center gap-2 ${step >= 3 ? 'text-primary' : 'text-muted-foreground'}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 3 ? 'bg-primary text-white' : 'bg-slate-200'}`}>
                                3
                            </div>
                            <span className="font-medium text-muted-foreground">Import</span>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="p-6 overflow-y-auto max-h-[calc(90vh-250px)]">
                        {step === 1 && (
                            <div className="space-y-6">
                                {/* File Upload */}
                                <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary transition-colors">
                                    <input
                                        type="file"
                                        accept=".pdf"
                                        onChange={handleFileSelect}
                                        className="hidden"
                                        id="pdf-upload"
                                    />
                                    <label htmlFor="pdf-upload" className="cursor-pointer">
                                        <FileText className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                                        {pdfFile ? (
                                            <div className="space-y-2">
                                                <p className="text-lg font-semibold text-foreground">{pdfFile.name}</p>
                                                <p className="text-sm text-muted-foreground">{(pdfFile.size / 1024).toFixed(2)} KB</p>
                                            </div>
                                        ) : (
                                            <div className="space-y-2">
                                                <p className="text-lg font-semibold text-foreground">Click to upload PDF</p>
                                                <p className="text-sm text-muted-foreground">or drag and drop</p>
                                                <p className="text-xs text-muted-foreground/60">Maximum file size: 10MB</p>
                                            </div>
                                        )}
                                    </label>
                                </div>

                                {/* Info */}
                                <div className="bg-primary/5 border border-primary/10 rounded-xl p-4">
                                    <div className="flex gap-3">
                                        <AlertCircle className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                                        <div className="text-sm text-primary">
                                            <p className="font-semibold mb-1">AI-Powered Extraction</p>
                                            <p>Our AI will automatically extract questions, options, and answers from your PDF. You'll be able to review and edit before importing.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {step === 2 && (
                            <div className="space-y-4">
                                <div className="flex justify-between items-center">
                                    <h3 className="text-lg font-bold text-foreground">
                                        Review Questions ({parsedQuestions.length})
                                    </h3>
                                    <button
                                        onClick={() => setStep(3)}
                                        className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
                                    >
                                        Continue to Import
                                    </button>
                                </div>

                                {parsedQuestions.map((q, index) => (
                                    <div key={index} className="border border-border rounded-xl p-4 hover:border-primary/50 transition-colors">
                                        {editingIndex === index ? (
                                            <div className="space-y-3">
                                                <input
                                                    value={editedQuestion.question_text}
                                                    onChange={(e) => setEditedQuestion({ ...editedQuestion, question_text: e.target.value })}
                                                    className="w-full p-2 border border-border rounded-lg"
                                                    placeholder="Question text"
                                                />

                                                {/* Edit Mode: Type Selector (Optional, maybe just keep what AI detected) */}

                                                {(editedQuestion.question_type?.toLowerCase() === 'mcq' || !editedQuestion.question_type || editedQuestion.option_a) ? (
                                                    <>
                                                        {['a', 'b', 'c', 'd'].map(opt => (
                                                            <input
                                                                key={opt}
                                                                value={editedQuestion[`option_${opt}`] || ''}
                                                                onChange={(e) => setEditedQuestion({ ...editedQuestion, [`option_${opt}`]: e.target.value })}
                                                                className="w-full p-2 border border-border rounded-lg"
                                                                placeholder={`Option ${opt.toUpperCase()}`}
                                                            />
                                                        ))}
                                                        <div className="flex gap-2 items-center text-sm">
                                                            <span>Correct:</span>
                                                            <select
                                                                value={editedQuestion.correct_answer || 'A'}
                                                                onChange={(e) => setEditedQuestion({ ...editedQuestion, correct_answer: e.target.value })}
                                                                className="p-1 border rounded"
                                                            >
                                                                {['A', 'B', 'C', 'D'].map(o => <option key={o} value={o}>{o}</option>)}
                                                            </select>
                                                        </div>
                                                    </>
                                                ) : (
                                                    <div>
                                                        <label className="text-xs text-muted-foreground">Model Answer</label>
                                                        <textarea
                                                            value={editedQuestion.model_answer || ''}
                                                            onChange={(e) => setEditedQuestion({ ...editedQuestion, model_answer: e.target.value })}
                                                            className="w-full p-2 border border-border rounded-lg h-20 text-sm"
                                                            placeholder="Enter model answer..."
                                                        />
                                                    </div>
                                                )}

                                                <div className="flex gap-2">
                                                    <button onClick={handleSaveEdit} className="px-4 py-2 bg-green-600 text-white rounded-lg">Save</button>
                                                    <button onClick={() => setEditingIndex(null)} className="px-4 py-2 bg-secondary rounded-lg">Cancel</button>
                                                </div>
                                            </div>
                                        ) : (
                                            <>
                                                <div className="flex justify-between items-start mb-3">
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <span className="text-xs font-bold uppercase text-primary bg-primary/10 px-2 py-0.5 rounded">
                                                                {q.question_type === 'short_answer' ? 'Short Answer' : 'MCQ'}
                                                            </span>
                                                        </div>
                                                        <p className="font-semibold text-foreground">{index + 1}. {q.question_text}</p>
                                                    </div>
                                                    <div className="flex gap-2">
                                                        <button onClick={() => handleEditQuestion(index)} className="text-primary hover:text-primary/80">
                                                            <Edit2 className="w-4 h-4" />
                                                        </button>
                                                        <button onClick={() => handleDeleteQuestion(index)} className="text-red-600 hover:text-red-700">
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </div>

                                                {(q.question_type?.toLowerCase() === 'mcq' || !q.question_type || q.option_a) ? (
                                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                                        {['a', 'b', 'c', 'd'].map(opt => (
                                                            <div key={opt} className={`p-2 rounded-lg ${q.correct_answer?.toLowerCase() === opt ? 'bg-green-500/10 border border-green-500/30' : 'bg-secondary'}`}>
                                                                <span className="font-semibold">{opt.toUpperCase()}.</span> {q[`option_${opt}`]}
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div className="bg-secondary p-3 rounded-lg text-sm">
                                                        <span className="font-semibold text-muted-foreground block mb-1">Model Answer:</span>
                                                        <p>{q.model_answer || 'No model answer provided'}</p>
                                                    </div>
                                                )}

                                                {/* Explanation Display */}
                                                {q.explanation && (
                                                    <div className="flex items-start gap-3 mt-3 pt-3 border-t border-dashed border-border/60">
                                                        <Info className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                                                        <div className="text-sm">
                                                            <span className="text-xs font-bold text-primary uppercase tracking-wider block mb-0.5">Explanation</span>
                                                            <p className="text-muted-foreground leading-relaxed">{q.explanation}</p>
                                                        </div>
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {step === 3 && (
                            <div className="space-y-6">
                                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
                                    <p className="text-emerald-700 dark:text-emerald-400 font-semibold">
                                        ✓ {parsedQuestions.length} questions ready to import
                                    </p>
                                </div>

                                {/* Topic Selection */}
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-2">Select Topic *</label>
                                    <select
                                        value={selectedTopic}
                                        onChange={(e) => {
                                            setSelectedTopic(e.target.value);
                                            setSelectedSubtopic('');
                                        }}
                                        className="w-full p-3 border border-border bg-card text-foreground rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                    >
                                        <option value="">Choose a topic...</option>
                                        {topics.map(topic => (
                                            <option key={topic.id} value={topic.id}>{topic.name}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Subtopic Selection */}
                                {filteredSubtopics.length > 0 && (
                                    <div>
                                        <label className="block text-sm font-medium text-foreground mb-2">Select Subtopic (Optional)</label>
                                        <select
                                            value={selectedSubtopic}
                                            onChange={(e) => setSelectedSubtopic(e.target.value)}
                                            className="w-full p-3 border border-border bg-card text-foreground rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                        >
                                            <option value="">No subtopic</option>
                                            {filteredSubtopics.map(subtopic => (
                                                <option key={subtopic.id} value={subtopic.id}>{subtopic.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="flex justify-between items-center p-6 border-t border-border bg-secondary/50">
                        {step > 1 && (
                            <button
                                onClick={() => setStep(step - 1)}
                                className="px-6 py-2 text-muted-foreground hover:text-foreground font-medium"
                            >
                                Back
                            </button>
                        )}
                        <div className="flex gap-3 ml-auto">
                            <button
                                onClick={handleClose}
                                className="px-6 py-2 border border-border rounded-lg hover:bg-secondary text-foreground font-medium"
                            >
                                Cancel
                            </button>
                            {step === 1 && (
                                <button
                                    onClick={handleUploadAndParse}
                                    disabled={!pdfFile || uploading}
                                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
                                >
                                    {uploading ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Parsing...
                                        </>
                                    ) : (
                                        <>
                                            <Upload className="w-4 h-4" />
                                            Upload & Parse
                                        </>
                                    )}
                                </button>
                            )}
                            {step === 3 && (
                                <button
                                    onClick={handleConfirmImport}
                                    disabled={!selectedTopic || importing}
                                    className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
                                >
                                    {importing ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Importing...
                                        </>
                                    ) : (
                                        <>
                                            <Check className="w-4 h-4" />
                                            Import Questions
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}
        </>
    );
}
