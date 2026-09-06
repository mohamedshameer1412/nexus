'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
    FileText, ArrowLeft, CheckCircle, Brain, Sparkles,
    Trash2, Save, X, Eye, AlertCircle, ShieldCheck,
    ChevronRight, Settings
} from 'lucide-react';
import { learningAPI } from '@/lib/api';

export default function ReviewPage() {
    const { id } = useParams();
    const router = useRouter();
    const [module, setModule] = useState(null);
    const [drafts, setDrafts] = useState({ flashcards: [], questions: [] });
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('quiz');

    useEffect(() => {
        fetchData();
    }, [id]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const moduleData = await learningAPI.getModule(id);
            setModule(moduleData);
            const draftData = await learningAPI.getDrafts(id);
            setDrafts(draftData);
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [publishSummary, setPublishSummary] = useState(null);

    const handleApprove = async (itemType, itemId) => {
        try {
            await learningAPI.approveItem(id, itemType, itemId);
            fetchData();
        } catch (error) {
            console.error('Approval failed:', error);
        }
    };

    const handleDelete = async (itemType, itemId) => {
        if (!confirm('Are you sure you want to delete this AI-generated item?')) return;
        try {
            await learningAPI.deleteItem(id, itemType, itemId);
            fetchData();
        } catch (error) {
            console.error('Delete failed:', error);
        }
    };

    const handlePublish = async () => {
        try {
            const result = await learningAPI.publish(id);
            setPublishSummary(result);
            setShowConfirmModal(true);
        } catch (error) {
            console.error('Publish failed:', error);
            alert('Failed to publish module.');
        }
    };

    if (loading) return (
        <div className="flex items-center justify-center min-h-screen">
            <div className="w-12 h-12 border-4 border-blue-100 border-t-blue-500 rounded-full animate-spin" />
        </div>
    );

    return (
        <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
            {/* Confirmation Modal */}
            {showConfirmModal && (
                <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] flex items-center justify-center p-6 animate-in fade-in duration-300">
                    <div className="bg-white rounded-[40px] p-10 max-w-lg w-full shadow-2xl animate-in zoom-in-95 duration-300">
                        <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-green-100/50">
                            <ShieldCheck className="w-10 h-10" />
                        </div>
                        <h2 className="text-3xl font-black text-slate-900 tracking-tight text-center mb-2">Success!</h2>
                        <p className="text-slate-500 font-medium text-center mb-10">Your module is now live and students can begin learning.</p>

                        <div className="bg-slate-50 rounded-[32px] p-8 space-y-4 mb-10 border border-slate-100">
                            <div className="flex justify-between items-center bg-white p-4 rounded-2xl shadow-sm border border-slate-50">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 bg-purple-100 text-purple-600 rounded-xl flex items-center justify-center"><CheckCircle className="w-4 h-4" /></div>
                                    <span className="font-black text-xs uppercase text-slate-400">Questions</span>
                                </div>
                                <span className="font-black text-xl text-slate-900">{publishSummary?.questions_published || 0}</span>
                            </div>
                            <div className="flex justify-between items-center bg-white p-4 rounded-2xl shadow-sm border border-slate-50">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 bg-amber-100 text-amber-600 rounded-xl flex items-center justify-center"><Brain className="w-4 h-4" /></div>
                                    <span className="font-black text-xs uppercase text-slate-400">Flashcards</span>
                                </div>
                                <span className="font-black text-xl text-slate-900">{publishSummary?.flashcards_published || 0}</span>
                            </div>
                            {publishSummary?.quiz_created && (
                                <div className="flex items-center gap-2 text-blue-600 font-bold text-[10px] uppercase tracking-widest justify-center pt-2">
                                    <Sparkles className="w-3 h-3" /> Quiz assessment auto-assigned
                                </div>
                            )}
                        </div>

                        <button
                            onClick={() => router.push(`/dashboard/learning/${id}`)}
                            className="w-full py-5 bg-slate-900 text-white font-black text-lg rounded-[22px] shadow-2xl shadow-slate-200 transition-all hover:scale-[1.02] active:scale-[0.98]"
                        >
                            Return to Dashboard
                        </button>
                    </div>
                </div>
            )}

            {/* Header */}
            <header className="h-16 bg-white border-b border-slate-100 px-6 flex items-center justify-between flex-shrink-0 z-30">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.push(`/dashboard/learning/${id}`)}
                        className="p-2 hover:bg-slate-50 rounded-xl text-slate-400 hover:text-slate-800 transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h1 className="text-lg font-black text-slate-900 tracking-tight leading-none mb-1">
                            Reviewing: {module?.title}
                        </h1>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black uppercase text-blue-500 tracking-widest bg-blue-50 px-2 py-0.5 rounded-full">
                                AI DRAFT MODE
                            </span>
                            <span className="text-[10px] font-black uppercase text-slate-400 tracking-widest">
                                {drafts.questions.length + drafts.flashcards.length} items to review
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button className="flex items-center gap-2 px-4 py-2 text-slate-500 font-bold text-sm hover:bg-slate-50 rounded-xl transition-all">
                        <Settings className="w-4 h-4" />
                        Settings
                    </button>
                    <button
                        onClick={handlePublish}
                        className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white font-black text-sm rounded-xl hover:bg-blue-700 shadow-xl shadow-blue-100 transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                        Confirm & Publish
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </header>

            <div className="flex-1 flex overflow-hidden">
                {/* Right: Review Panel (Full Width now) */}
                <div className="flex-1 flex flex-col bg-slate-50 overflow-hidden">
                    {/* Tabs */}
                    <div className="px-8 pt-6 pb-2">
                        <div className="flex items-center gap-6 border-b border-slate-200">
                            {[
                                { id: 'quiz', label: 'Assessment Quiz', count: drafts.questions.length, icon: Sparkles },
                                { id: 'cards', label: 'Flashcards', count: drafts.flashcards.length, icon: Brain }
                            ].map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`pb-4 px-2 relative font-black text-sm flex items-center gap-2 transition-all ${activeTab === tab.id ? 'text-blue-600' : 'text-slate-400 hover:text-slate-600'
                                        }`}
                                >
                                    <tab.icon className="w-4 h-4" />
                                    {tab.label}
                                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-black ${activeTab === tab.id ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400'
                                        }`}>
                                        {tab.count}
                                    </span>
                                    {activeTab === tab.id && (
                                        <div className="absolute bottom-0 left-0 right-0 h-1 bg-blue-600 rounded-t-full shadow-[0_-4px_10px_rgba(37,99,235,0.3)] animate-in slide-in-from-bottom-2 duration-300" />
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Scrollable List */}
                    <div className="flex-1 overflow-y-auto p-8 space-y-6">
                        {activeTab === 'quiz' ? (
                            drafts.questions.map((q, idx) => (
                                <QuestionCard
                                    key={q.id}
                                    question={q}
                                    index={idx}
                                    onApprove={(id) => handleApprove('question', id)}
                                    onDelete={(id) => handleDelete('question', id)}
                                />
                            ))
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {drafts.flashcards.map((f, idx) => (
                                    <FlashcardCard
                                        key={f.id}
                                        card={f}
                                        index={idx}
                                        onApprove={() => handleApprove('flashcard', f.id)}
                                        onDelete={() => handleDelete('flashcard', f.id)}
                                    />
                                ))}
                            </div>
                        )}

                        {(activeTab === 'quiz' && drafts.questions.length === 0) ||
                            (activeTab === 'cards' && drafts.flashcards.length === 0) ? (
                            <div className="h-[40vh] flex flex-col items-center justify-center text-center opacity-50">
                                <AlertCircle className="w-12 h-12 mb-4 text-slate-300" />
                                <h3 className="text-lg font-black text-slate-800 tracking-tight">No Items Generated</h3>
                                <p className="text-sm font-medium text-slate-400 max-w-xs uppercase tracking-widest">
                                    Trigger AI generation to populate this section
                                </p>
                            </div>
                        ) : null}
                    </div>
                </div>
            </div>
        </div>
    );
}

function QuestionCard({ question, index }) {
    const [editedText, setEditedText] = useState(question.text);
    const [editedOptions, setEditedOptions] = useState(question.options);

    const handleSave = async () => {
        try {
            await learningAPI.editItem(question.id.split('-')[0], 'question', question.id, {
                text: editedText,
                options: editedOptions
            });
            setIsEditing(false);
            // In a real app, we'd trigger a refresh or update local state
            question.text = editedText; // Optimistic update
            question.options = editedOptions;
        } catch (error) {
            console.error('Save failed:', error);
        }
    };

    return (
        <div className="group bg-white rounded-3xl p-6 border border-slate-100 shadow-sm hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-300 relative overflow-hidden">
            {/* AI Badge Background Effect */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50/20 translate-x-16 -translate-y-16 rounded-full blur-2xl group-hover:bg-blue-100/30 transition-colors" />

            <div className="relative flex gap-6">
                <div className="flex-1">
                    <div className="flex items-center gap-3 mb-4">
                        <span className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center text-[10px] font-black shadow-lg shadow-slate-200">
                            Q{index + 1}
                        </span>
                        <div className="flex items-center gap-2">
                            <span className={`px-3 py-1 rounded-full text-[10px] font-black border uppercase tracking-wider ${difficultyColors[question.difficulty || 2]}`}>
                                {question.difficulty === 1 ? 'Beginner' :
                                    question.difficulty === 2 ? 'Intermediate' :
                                        question.difficulty === 3 ? 'Advanced' :
                                            question.difficulty === 4 ? 'Expert' : 'Master'}
                            </span>
                            <div className="flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-[10px] font-black border border-blue-100 uppercase tracking-wider">
                                <ShieldCheck className="w-3 h-3" />
                                Confidence: {(question.confidence_score * 100 || 85).toFixed(0)}%
                            </div>
                        </div>
                    </div>

                    {isEditing ? (
                        <textarea
                            value={editedText}
                            onChange={(e) => setEditedText(e.target.value)}
                            className="w-full p-4 bg-slate-50 border border-slate-200 rounded-2xl text-lg font-bold text-slate-800 focus:ring-2 focus:ring-blue-500 mb-6"
                            rows={3}
                        />
                    ) : (
                        <h3 className="text-lg font-black text-slate-800 leading-tight mb-6">
                            {question.text}
                        </h3>
                    )}

                    {question.type === 'mcq' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
                            {Object.entries(editedOptions).map(([key, val]) => (
                                <div
                                    key={key}
                                    className={`p-4 rounded-2xl border-2 transition-all flex items-center gap-3 ${question.correct_answer === key
                                        ? 'border-green-500 bg-green-50/50 font-bold text-green-900 shadow-sm'
                                        : 'border-slate-50 bg-slate-50 text-slate-600'
                                        }`}
                                >
                                    <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-black ${question.correct_answer === key ? 'bg-green-600 text-white shadow-md' : 'bg-white text-slate-400'
                                        }`}>
                                        {key}
                                    </span>
                                    {isEditing ? (
                                        <input
                                            value={val}
                                            onChange={(e) => setEditedOptions({ ...editedOptions, [key]: e.target.value })}
                                            className="bg-transparent border-none focus:ring-0 text-sm w-full font-bold"
                                        />
                                    ) : (
                                        <span className="text-sm">{val}</span>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="bg-slate-50 rounded-2xl p-4 mb-6 border border-slate-100">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Model Answer Reference</p>
                            <p className="text-sm font-medium text-slate-700 leading-relaxed italic line-clamp-2">"{question.model_answer}"</p>
                        </div>
                    )}

                    <div className="flex items-center gap-2">
                        {isEditing ? (
                            <button
                                onClick={handleSave}
                                className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-xl text-xs font-black shadow-lg shadow-green-100 hover:scale-105 active:scale-95 transition-all"
                            >
                                <Save className="w-4 h-4" />
                                Save Changes
                            </button>
                        ) : (
                            <button
                                onClick={() => onApprove(question.id)}
                                className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-black shadow-lg shadow-slate-200 hover:scale-105 active:scale-95 transition-all"
                            >
                                <CheckCircle className="w-4 h-4" />
                                Approve
                            </button>
                        )}
                        <button
                            onClick={() => isEditing ? setIsEditing(false) : onDelete(question.id)}
                            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl text-xs font-black hover:bg-slate-50 transition-all"
                        >
                            {isEditing ? <><X className="w-4 h-4" /> Cancel</> : <><Trash2 className="w-4 h-4" /> Reject</>}
                        </button>
                        {!isEditing && (
                            <button
                                onClick={() => setIsEditing(true)}
                                className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl text-xs font-black hover:bg-slate-50 transition-all ml-auto"
                            >
                                Edit
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

function FlashcardCard({ card, onApprove, onDelete }) {
    const [isEditing, setIsEditing] = useState(false);
    const [editedFront, setEditedFront] = useState(card.front);
    const [editedBack, setEditedBack] = useState(card.back);

    const handleSave = async () => {
        try {
            await learningAPI.editItem(card.id.split('-')[0], 'flashcard', card.id, {
                front: editedFront,
                back: editedBack
            });
            setIsEditing(false);
            card.front = editedFront;
            card.back = editedBack;
        } catch (error) {
            console.error('Flashcard save failed:', error);
        }
    };

    return (
        <div className="group bg-white rounded-3xl p-6 border border-slate-100 shadow-sm hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-300 flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-amber-50/20 translate-x-12 -translate-y-12 rounded-full blur-xl group-hover:bg-amber-100/30 transition-colors" />

            <div className="relative flex-1">
                <div className="flex items-center justify-between mb-6">
                    <span className="px-3 py-1 bg-amber-50 text-amber-600 text-[10px] font-black rounded-full border border-amber-100 uppercase tracking-widest">
                        Active Recall Item
                    </span>
                    {!isEditing && (
                        <button
                            onClick={() => setIsEditing(true)}
                            className="p-1.5 hover:bg-slate-50 text-slate-400 hover:text-blue-500 rounded-xl transition-all"
                        >
                            <Settings className="w-3.5 h-3.5" />
                        </button>
                    )}
                </div>

                <div className="mb-6">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Front Side</p>
                    {isEditing ? (
                        <textarea
                            value={editedFront}
                            onChange={(e) => setEditedFront(e.target.value)}
                            className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold focus:ring-2 focus:ring-blue-500"
                            rows={2}
                        />
                    ) : (
                        <p className="text-lg font-black text-slate-800 leading-tight">{card.front}</p>
                    )}
                </div>

                <div className="pt-6 border-t border-slate-50 mb-8">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Back Side</p>
                    {isEditing ? (
                        <textarea
                            value={editedBack}
                            onChange={(e) => setEditedBack(e.target.value)}
                            className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-blue-500"
                            rows={3}
                        />
                    ) : (
                        <p className="text-sm font-medium text-slate-600 leading-relaxed italic">"{card.back}"</p>
                    )}
                </div>
            </div>

            <div className="relative flex items-center gap-2 mt-auto">
                {isEditing ? (
                    <>
                        <button
                            onClick={handleSave}
                            className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-green-600 text-white rounded-xl text-xs font-black shadow-lg shadow-green-100 hover:scale-[1.02] active:scale-98 transition-all"
                        >
                            <Save className="w-3.5 h-3.5" />
                            Save
                        </button>
                        <button
                            onClick={() => setIsEditing(false)}
                            className="flex items-center justify-center p-2.5 bg-white border border-slate-200 text-slate-400 hover:text-slate-600 rounded-xl transition-all"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </>
                ) : (
                    <>
                        <button
                            onClick={onApprove}
                            className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-black shadow-lg shadow-slate-200 hover:scale-[1.02] active:scale-98 transition-all"
                        >
                            <CheckCircle className="w-3.5 h-3.5" />
                            Approve
                        </button>
                        <button
                            onClick={onDelete}
                            className="flex items-center justify-center p-2.5 bg-white border border-slate-200 text-slate-400 hover:text-red-500 hover:bg-red-50 hover:border-red-100 rounded-xl transition-all"
                            title="Delete Draft"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}
