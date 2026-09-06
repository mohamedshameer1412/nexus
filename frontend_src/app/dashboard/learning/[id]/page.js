'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
    BookOpen,
    ArrowLeft,
    Clock,
    CheckCircle,
    Brain,
    FileText,
    Play,
    Settings,
    Eye,
    CheckSquare,
    Send,
    BarChart2,
    Trash2,
    Check,
    ChevronDown,
    ChevronUp,
    ChevronRight,
    ShieldCheck,
    Sparkles,
    Loader2,
    Edit3,
    AlertCircle,
    CheckCircle2
} from 'lucide-react';
import { learningAPI, API_BASE_URL } from '@/lib/api';

export default function ModuleViewerPage() {
    const router = useRouter();
    const params = useParams();
    const [module, setModule] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('content'); // 'content' | 'flashcards' | 'review' | 'analytics'
    const [studyTime, setStudyTime] = useState(0);
    const [progressStatus, setProgressStatus] = useState('not_started');
    const [drafts, setDrafts] = useState({ flashcards: [], questions: [] });
    const [analytics, setAnalytics] = useState(null);
    const [isPublishing, setIsPublishing] = useState(false);
    const [user, setUser] = useState(null);
    const [isLearningMode, setIsLearningMode] = useState(false);
    const [modalConfig, setModalConfig] = useState(null); // { type: 'success'|'error'|'confirm', title, message, onConfirm, onCancel }
    const [isEditingLabels, setIsEditingLabels] = useState(false);
    const [editForm, setEditForm] = useState({ title: '', description: '' });
    const timerRef = useRef(null);
    const hasUpdatedRef = useRef(false);


    useEffect(() => {
        const userData = localStorage.getItem('user');
        if (userData) {
            const parsedUser = JSON.parse(userData);
            setUser(parsedUser);
        }
    }, []);

    useEffect(() => {
        if (params.id) {
            fetchModule(params.id);
        }

        // Start study timer
        timerRef.current = setInterval(() => {
            setStudyTime(prev => prev + 1);
        }, 1000);

        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
            // Update progress on unmount/leave
            if (params.id && studyTime > 5) {
                updateProgress(studyTime);
            }
        };
    }, [params.id]);

    const fetchModule = async (id) => {
        try {
            const data = await learningAPI.getModule(id);
            setModule(data);
            setEditForm({ title: data.title, description: data.description });

            // If teacher and not published, fetch drafts
            const userData = localStorage.getItem('user');
            const user = userData ? JSON.parse(userData) : null;

            if (user?.role === 'teacher') {
                const draftData = await learningAPI.getDrafts(id);
                setDrafts(draftData);
                const analyticsData = await learningAPI.getAnalytics(id);
                setAnalytics(analyticsData);
            }

            setLoading(false);
        } catch (error) {
            console.error('Failed to load module:', error);
            setLoading(false);
        }
    };

    const updateProgress = async (timeFn) => {
        // Prevent double updates in strict mode or rapid changes
        if (hasUpdatedRef.current) return;
        // Logic to allow periodic updates would be better, but simplified for now:
        // We'll trust the unmount hook for final update

        try {
            const time = typeof timeFn === 'number' ? timeFn : studyTime;
            await learningAPI.updateProgress({
                module_id: params.id,
                time_spent: time,
                status: 'in_progress' // Default to in_progress
            });
        } catch (error) {
            console.error('Failed to update progress:', error);
        }
    };

    const markAsComplete = async () => {
        try {
            await learningAPI.updateProgress({
                module_id: params.id,
                time_spent: studyTime,
                status: 'completed'
            });
            setProgressStatus('completed');
            setModalConfig({
                type: 'success',
                title: 'Lesson Completed!',
                message: 'Module marked as completed! You can now access the assessment and other learning activities.',
                onConfirm: () => setModalConfig(null)
            });
        } catch (error) {
            console.error('Failed to complete module:', error);
        }
    };

    const handlePublish = async () => {
        if (isPublishing) return;
        setIsPublishing(true);
        try {
            await learningAPI.publish(params.id);
            setModule(prev => ({ ...prev, is_published: true }));
            setModalConfig({
                type: 'success',
                title: module.is_published ? 'Content Synced' : 'Module Published',
                message: module.is_published
                    ? 'All content updates have been successfully synced to the live module.'
                    : 'Your module is now live and the assessment has been assigned to all students.',
                onConfirm: () => setModalConfig(null)
            });
        } catch (error) {
            console.error('Failed to publish module:', error);
            setModalConfig({
                type: 'error',
                title: module.is_published ? 'Sync Failed' : 'Publish Failed',
                message: (error.response?.data?.error || error.message),
                onConfirm: () => setModalConfig(null)
            });
        } finally {
            setIsPublishing(false);
        }
    };

    const handleUpdateDetails = async () => {
        try {
            const formData = new FormData();
            formData.append('title', editForm.title);
            formData.append('description', editForm.description);
            const updated = await learningAPI.updateModule(params.id, formData);
            setModule(prev => ({ ...prev, title: updated.title, description: updated.description }));
            setIsEditingLabels(false);
            setModalConfig({
                type: 'success',
                title: 'Changes Saved',
                message: 'Module details have been updated successfully.',
                onConfirm: () => setModalConfig(null)
            });
        } catch (error) {
            setModalConfig({
                type: 'error',
                title: 'Update Failed',
                message: error.message,
                onConfirm: () => setModalConfig(null)
            });
        }
    };


    if (loading) {
        return <div className="p-8 text-center text-muted-foreground">Loading learning module...</div>;
    }

    if (isLearningMode) {
        return (
            <LearningView
                module={module}
                studyTime={studyTime}
                onExit={() => setIsLearningMode(false)}
                onComplete={markAsComplete}
            />
        );
    }

    if (!module) {
        return <div className="p-8 text-center text-red-500">Module not found.</div>;
    }

    return (
        <div className="max-w-6xl mx-auto h-[calc(100vh-100px)] flex flex-col pt-2 text-foreground">
            {/* Header */}
            <div className="flex items-center justify-between mb-6 flex-shrink-0">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.back()}
                        className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5 text-muted-foreground" />
                    </button>
                    <div>
                        <div className="flex items-center gap-3">
                            {isEditingLabels ? (
                                <input
                                    type="text"
                                    value={editForm.title}
                                    onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                                    className="text-xl md:text-2xl font-bold bg-white/5 border border-blue-500/30 rounded-lg px-2 py-1 outline-none text-white w-[300px]"
                                    autoFocus
                                />
                            ) : (
                                <h1 className="text-xl md:text-2xl font-bold text-foreground truncate max-w-md">{module.title}</h1>
                            )}
                            {user?.role === 'teacher' && (
                                <div className="flex items-center gap-3">
                                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide border ${module.is_published ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                                        {module.is_published ? 'Published' : 'Draft'}
                                    </span>
                                    {!isEditingLabels ? (
                                        <button
                                            onClick={() => setIsEditingLabels(true)}
                                            className="p-1.5 hover:bg-white/10 rounded-lg text-slate-500 hover:text-blue-400 transition-all"
                                            title="Edit module details"
                                        >
                                            <Edit3 className="w-4 h-4" />
                                        </button>
                                    ) : (
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={handleUpdateDetails}
                                                className="p-1 px-3 bg-blue-600 text-white text-[10px] font-black rounded-lg hover:bg-blue-700 uppercase tracking-widest"
                                            >
                                                Save
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setIsEditingLabels(false);
                                                    setEditForm({ title: module.title, description: module.description });
                                                }}
                                                className="p-1 px-3 bg-white/5 text-slate-400 text-[10px] font-black rounded-lg hover:bg-white/10 uppercase tracking-widest"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                        <p className="text-muted-foreground text-sm flex items-center gap-2">
                            <BookOpen className="w-3 h-3" />
                            {module.topic?.name || 'General Topic'}
                        </p>
                    </div>
                </div>
            </div>

            <div className="flex items-center justify-end gap-3 mb-8">
                {user?.role === 'teacher' && (
                    <div className="flex bg-muted/50 p-1 rounded-xl">
                        <button
                            onClick={() => setActiveTab('content')}
                            className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${(['content', 'flashcards', 'knowledge_prep'].includes(activeTab)) ? 'bg-card shadow-sm text-primary' : 'text-muted-foreground hover:text-foreground'}`}
                        >
                            <Eye className="w-4 h-4 inline-block mr-2" />
                            Preview
                        </button>
                        <button
                            onClick={() => setActiveTab('review')}
                            className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'review' ? 'bg-card shadow-sm text-primary' : 'text-muted-foreground hover:text-foreground'}`}
                        >
                            <CheckSquare className="w-4 h-4 inline-block mr-2" />
                            Review Drafts
                            {(() => {
                                const totalUnreviewed = (drafts.flashcards?.filter(f => !f.is_approved).length || 0) +
                                    (drafts.questions?.filter(q => !q.is_approved).length || 0);
                                return totalUnreviewed > 0 && (
                                    <span className="ml-2 bg-amber-500 text-black text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                                        {totalUnreviewed}
                                    </span>
                                );
                            })()}
                        </button>
                        <button
                            onClick={() => setActiveTab('analytics')}
                            className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'analytics' ? 'bg-card shadow-sm text-primary' : 'text-muted-foreground hover:text-foreground'}`}
                        >
                            <BarChart2 className="w-4 h-4 inline-block mr-2" />
                            Analytics
                        </button>
                    </div>
                )}

                {user?.role === 'teacher' && (
                    <button
                        onClick={handlePublish}
                        disabled={isPublishing}
                        className={`flex items-center gap-2 px-6 py-2 rounded-xl font-black transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed ${module.is_published ? 'bg-slate-800 text-slate-400 hover:bg-slate-700' : 'bg-green-600 text-white hover:bg-green-700'}`}
                        data-role="publish-btn"
                    >
                        {isPublishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        {module.is_published ? 'Sync Content' : 'Publish Module'}
                    </button>
                )}

                {user?.role === 'student' && (
                    <button
                        onClick={() => setIsLearningMode(true)}
                        className="flex items-center gap-2 px-6 py-2 bg-slate-900 text-white rounded-xl font-black hover:bg-slate-800 shadow-xl shadow-slate-900/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                        <Play className="w-4 h-4 fill-current" />
                        Start Learning
                    </button>
                )}
            </div>

            {/* Tabs Navigation */}
            <div className="flex gap-2 md:gap-4 border-b border-white/10 mb-4 flex-shrink-0 px-8 overflow-x-auto custom-scrollbar">
                <button
                    onClick={() => setActiveTab('content')}
                    className={`pb-3 px-4 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${activeTab === 'content'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                        }`}
                >
                    <BookOpen className="w-4 h-4" />
                    Study Material
                </button>
                <button
                    onClick={() => setActiveTab('flashcards')}
                    className={`pb-3 px-4 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${activeTab === 'flashcards'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                        }`}
                >
                    <Brain className="w-4 h-4" />
                    Flashcards
                    <span className="bg-white/5 text-slate-400 px-2 py-0.5 rounded-full text-xs">
                        {typeof module.flashcard_decks?.[0]?.card_count === 'object'
                            ? `${module.flashcard_decks[0].card_count.approved} / ${module.flashcard_decks[0].card_count.total}`
                            : (module.flashcard_decks?.[0]?.card_count || 0)
                        }
                    </span>
                </button>
                <button
                    onClick={() => setActiveTab('knowledge_prep')}
                    className={`pb-3 px-4 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${activeTab === 'knowledge_prep'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                        }`}
                >
                    <Sparkles className="w-4 h-4" />
                    Knowledge Prep
                    {module.questions?.length > 0 && (
                        <span className="bg-white/5 text-slate-400 px-2 py-0.5 rounded-full text-xs">
                            {user?.role === 'teacher'
                                ? `${module.questions.filter(q => q.is_approved).length} / ${module.questions.length}`
                                : module.questions.length
                            }
                        </span>
                    )}
                </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 bg-card rounded-3xl shadow-sm border border-white/5 overflow-hidden relative">
                {activeTab === 'content' && (
                    <div className="absolute inset-0 overflow-y-auto p-8 custom-scrollbar">
                        <div className="max-w-4xl mx-auto space-y-8 pb-12">
                            <div className="prose max-w-none">
                                <div className="flex items-center gap-4 mb-4">
                                    <h2 className="text-xl font-bold text-white uppercase tracking-tight">Overview</h2>
                                    {isEditingLabels && (
                                        <span className="text-[10px] font-black text-blue-400 uppercase bg-blue-500/10 px-2 py-0.5 rounded-full">Editing Mode</span>
                                    )}
                                </div>

                                {isEditingLabels ? (
                                    <textarea
                                        value={editForm.description}
                                        onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                                        className="w-full p-4 bg-white/5 border border-blue-500/30 rounded-2xl text-muted-foreground text-lg leading-relaxed mb-8 outline-none focus:ring-1 focus:ring-blue-500"
                                        rows={4}
                                    />
                                ) : (
                                    <p className="text-muted-foreground text-lg leading-relaxed mb-8">{module.description}</p>
                                )}

                                {module.content_text ? (
                                    <div className="bg-muted/30 p-8 rounded-[32px] border border-white/5 shadow-inner">
                                        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-6 flex items-center gap-3">
                                            <div className="p-2 bg-blue-500/10 rounded-lg">
                                                <FileText className="w-5 h-5 text-blue-400" />
                                            </div>
                                            Study Content Doc
                                        </h3>
                                        <div className="whitespace-pre-line text-foreground/90 leading-[2] font-serif text-xl py-6 tracking-wide">
                                            {module.content_text}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center py-20 px-6 rounded-3xl bg-muted/10 border border-white/5 border-dashed">
                                        <div className="w-16 h-16 bg-muted/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <FileText className="w-8 h-8 text-muted-foreground" />
                                        </div>
                                        <h3 className="text-lg font-bold text-foreground mb-2">No Document Content</h3>
                                        <p className="text-muted-foreground text-sm max-w-md mx-auto mb-6">
                                            We couldn't extract text content from this module. You can still view the original PDF.
                                        </p>
                                        {module.pdf_file && (
                                            <a
                                                href={module.pdf_file.startsWith('http') ? module.pdf_file : API_BASE_URL + module.pdf_file}
                                                target="_blank"
                                                className="inline-flex items-center gap-2 px-6 py-2.5 bg-primary/10 text-primary hover:bg-primary/20 rounded-xl font-bold transition-all text-sm"
                                            >
                                                <Eye className="w-4 h-4" />
                                                View Original PDF
                                            </a>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'flashcards' && (
                    <div className="absolute inset-0 overflow-y-auto p-4 bg-black/20 flex flex-col items-center">
                        {module.flashcard_decks && module.flashcard_decks.length > 0 ? (
                            <FlashcardViewer deck={module.flashcard_decks[0]} />
                        ) : (
                            <div className="text-center mt-20 text-slate-400">
                                <Brain className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                <p>No flashcards generated for this module.</p>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'knowledge_prep' && (
                    <div className="absolute inset-0 overflow-y-auto p-8 custom-scrollbar bg-black/20">
                        <KnowledgePrepPanel questions={module.questions} />
                    </div>
                )}

                {activeTab === 'review' && (
                    <div className="absolute inset-0 overflow-y-auto p-8 custom-scrollbar">
                        <div className="max-w-4xl mx-auto pb-12">
                            <ReviewPanel
                                drafts={drafts}
                                moduleId={module.id}
                                moduleTitle={module.title}
                                onUpdate={() => fetchModule(params.id)}
                                onPublish={handlePublish}
                                setModalConfig={setModalConfig}
                                isPublished={module.is_published}
                            />
                        </div>
                    </div>
                )}

                {activeTab === 'analytics' && (
                    <div className="absolute inset-0 overflow-y-auto p-8 custom-scrollbar">
                        <AnalyticsPanel analytics={analytics} />
                    </div>
                )}
            </div>

            {/* Custom Modal */}
            <CustomModal
                config={modalConfig}
                onClose={() => setModalConfig(null)}
            />
        </div>
    );
}

function CustomModal({ config, onClose }) {
    if (!config) return null;

    const { type = 'info', title, message, onConfirm, confirmText = 'OK', cancelText = 'Cancel' } = config;

    const icons = {
        success: <CheckCircle2 className="w-12 h-12 text-green-400" />,
        error: <AlertCircle className="w-12 h-12 text-red-400" />,
        confirm: <ShieldCheck className="w-12 h-12 text-blue-400" />,
        info: <Sparkles className="w-12 h-12 text-blue-400" />
    };

    const colors = {
        success: 'border-green-500/20 bg-green-500/5',
        error: 'border-red-500/20 bg-red-500/5',
        confirm: 'border-blue-500/20 bg-blue-500/5',
        info: 'border-blue-500/20 bg-blue-500/5'
    };

    return (
        <div className="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
            <div className={`max-w-md w-full rounded-[40px] border p-10 shadow-2xl animate-in zoom-in-95 duration-200 ${colors[type]}`}>
                <div className="flex flex-col items-center text-center">
                    <div className={`p-4 rounded-3xl mb-6 ${type === 'success' ? 'bg-green-500/10' : type === 'error' ? 'bg-red-500/10' : 'bg-blue-500/10'}`}>
                        {icons[type]}
                    </div>

                    <h3 className="text-2xl font-black text-white mb-3 tracking-tight">
                        {title}
                    </h3>

                    <p className="text-slate-400 text-base leading-relaxed mb-10">
                        {message}
                    </p>

                    <div className="flex items-center gap-4 w-full">
                        {type === 'confirm' && (
                            <button
                                onClick={() => {
                                    onClose();
                                    if (config.onCancel) config.onCancel();
                                }}
                                className="flex-1 py-4 px-6 rounded-2xl font-bold text-slate-400 hover:bg-white/5 transition-all text-sm"
                            >
                                {cancelText}
                            </button>
                        )}
                        <button
                            onClick={() => {
                                if (onConfirm) onConfirm();
                                onClose();
                            }}
                            className={`flex-1 py-4 px-6 rounded-2xl font-black text-sm shadow-xl transition-all hover:scale-[1.02] active:scale-[0.98] ${type === 'error' ? 'bg-red-600 text-white shadow-red-500/20' :
                                type === 'success' ? 'bg-green-600 text-white shadow-green-500/20' :
                                    'bg-blue-600 text-white shadow-blue-500/20'
                                }`}
                        >
                            {confirmText}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

function formatTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h > 0 ? h + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function LearningView({ module, studyTime, onExit, onComplete }) {
    const [activeSubTab, setActiveSubTab] = useState('study'); // 'study' | 'flashcards'
    const [completed, setCompleted] = useState(false);

    const handleMarkComplete = () => {
        setCompleted(true);
        onComplete();
    };

    return (
        <div className="fixed inset-0 z-[100] bg-slate-950 flex flex-col text-white animate-in fade-in duration-300">
            {/* Immersive Header */}
            <header className="h-16 bg-slate-900/80 backdrop-blur-xl border-b border-white/5 px-6 flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onExit}
                        className="p-2 hover:bg-white/5 rounded-xl text-slate-400 hover:text-white transition-colors flex items-center gap-2 font-bold text-sm"
                    >
                        <ArrowLeft className="w-5 h-5" />
                        Exit Lesson
                    </button>
                    <div className="h-6 w-[1px] bg-white/10" />
                    <h1 className="text-sm font-black tracking-tight text-slate-200">
                        {module?.title}
                    </h1>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-full">
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                        <span className="text-xs font-black font-mono text-blue-400 uppercase tracking-widest">
                            Learning: {formatTime(studyTime)}
                        </span>
                    </div>
                    <button
                        onClick={handleMarkComplete}
                        disabled={completed}
                        className={`px-6 py-2 rounded-xl font-black text-xs transition-all flex items-center gap-2 ${completed
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : 'bg-white text-slate-900 hover:bg-blue-50 shadow-xl shadow-white/10'
                            }`}
                    >
                        {completed ? <><CheckCircle className="w-4 h-4" /> Completed</> : 'Finish Lesson'}
                    </button>
                </div>
            </header>

            <div className="flex-1 flex overflow-hidden">
                {/* Sidebar */}
                <div className="w-64 bg-slate-900/50 border-r border-white/5 flex flex-col p-6">
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-6">Course Progress</p>
                    <div className="space-y-2">
                        {[
                            { id: 'study', label: 'Study Content', icon: BookOpen },
                            { id: 'flashcards', label: 'Flashcards', icon: Brain }
                        ].map(item => (
                            <button
                                key={item.id}
                                onClick={() => setActiveSubTab(item.id)}
                                className={`w-full flex items-center gap-4 p-4 rounded-2xl transition-all ${activeSubTab === item.id
                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                                    }`}
                            >
                                <item.icon className={`w-5 h-5 ${activeSubTab === item.id ? 'text-white' : 'text-slate-500'}`} />
                                <span className="text-sm font-bold">{item.label}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 bg-[#020617] relative">
                    {activeSubTab === 'study' && (
                        <div className="h-full flex flex-col overflow-hidden">
                            {module?.pdf_file ? (
                                <iframe
                                    src={`${module.pdf_file.startsWith('http') ? module.pdf_file : API_BASE_URL + module.pdf_file}#toolbar=0&view=FitH`}
                                    className="w-full h-full grayscale-[0.1] opacity-90"
                                    title="Study Material"
                                />
                            ) : (
                                <div className="h-full overflow-y-auto p-16 custom-scrollbar">
                                    <div className="max-w-3xl mx-auto">
                                        <div className="flex items-center gap-3 text-blue-400 mb-6">
                                            <FileText className="w-6 h-6" />
                                            <span className="text-xs font-black uppercase tracking-[0.2em]">Study Content Doc</span>
                                        </div>
                                        <h2 className="text-5xl font-black text-white mb-10 leading-tight tracking-tighter">
                                            {module?.title}
                                        </h2>
                                        <div className="bg-slate-900/40 rounded-[48px] p-12 border border-white/5 shadow-2xl relative">
                                            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
                                            <div className="whitespace-pre-wrap text-slate-200 leading-[2.2] text-2xl font-serif relative z-10 tracking-wide">
                                                {module?.content_text || "No text content available."}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {activeSubTab === 'flashcards' && (
                        <div className="h-full flex items-center justify-center p-8">
                            <FlashcardViewer deck={module?.flashcard_decks?.[0]} />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function ReviewPanel({ drafts, moduleId, moduleTitle, onUpdate, onPublish, setModalConfig, isPublished }) {
    const handleApprove = async (type, id) => {
        try {
            const response = await learningAPI.approveItem(moduleId, type, id);
            await onUpdate();
            setModalConfig({
                type: 'success',
                title: 'Status Updated',
                message: `The item has been successfully ${response.is_approved ? 'approved' : 'disapproved'}. The preview tabs have been updated.`,
                onConfirm: () => setModalConfig(null)
            });
        } catch (e) {
            setModalConfig({
                type: 'error',
                title: 'Approval Failed',
                message: 'Failed to approve the item. Please try again.',
                onConfirm: () => setModalConfig(null)
            });
        }
    };

    const handleEdit = async (type, id, updates) => {
        try {
            await learningAPI.editItem(moduleId, type, id, updates);
            onUpdate();
        } catch (e) {
            setModalConfig({
                type: 'error',
                title: 'Update Failed',
                message: 'Failed to update the item. Please check your connection.',
                onConfirm: () => setModalConfig(null)
            });
        }
    };

    return (
        <div className="space-y-12">
            {drafts.flashcards.length === 0 && drafts.questions.length === 0 && (
                <div className="bg-muted/10 border-2 border-dashed border-white/10 rounded-3xl p-12 text-center">
                    <div className="w-20 h-20 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Sparkles className="w-10 h-10" />
                    </div>
                    <h3 className="text-xl font-bold text-foreground mb-2">No AI Drafts Found</h3>
                    <p className="text-muted-foreground max-w-sm mx-auto mb-8">
                        You haven't generated any AI content yet. Upload a PDF and let our AI create study materials for you.
                    </p>
                    <button
                        onClick={async () => {
                            const types = ['quiz', 'flashcard', 'essay'];
                            try {
                                const response = await learningAPI.generateAIContent(moduleId, { types });

                                let msg = "AI Generation complete!";
                                if (response.flashcards_created) msg += `\n- ${response.flashcards_created} flashcards`;
                                else if (response.flashcards_error) msg += `\n- Flashcards failed: ${response.flashcards_error}`;

                                if (response.mcqs_created) msg += `\n- ${response.mcqs_created} questions`;
                                else if (response.quiz_error) msg += `\n- Questions failed: ${response.quiz_error}`;

                                if (!response.flashcards_created && !response.mcqs_created && !response.flashcards_error && !response.quiz_error) {
                                    msg += "\n\nNote: No content was generated. The AI might not have found suitable content in the text.";
                                }

                                setModalConfig({
                                    type: 'success',
                                    title: 'AI Content Generated',
                                    message: msg,
                                    onConfirm: () => window.location.reload()
                                });
                            } catch (e) {
                                setModalConfig({
                                    type: 'error',
                                    title: 'Generation Failed',
                                    message: (e.response?.data?.error || e.message || "Unknown error"),
                                    onConfirm: () => setModalConfig(null)
                                });
                            }
                        }}
                        className="btn-enterprise-primary px-8 py-3 rounded-xl font-bold flex items-center gap-2 mx-auto"
                    >
                        <Sparkles className="w-5 h-5" />
                        Generate AI Content
                    </button>
                </div>
            )}

            {drafts.flashcards.length > 0 && (
                <div>
                    <h2 className="text-xl font-bold mb-6 flex items-center gap-3 text-white">
                        <div className="p-2 bg-purple-500/20 rounded-xl">
                            <Brain className="w-6 h-6 text-purple-400" />
                        </div>
                        AI-Generated Flashcards
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {drafts.flashcards.map(card => (
                            <EditableFlashcardCard key={card.id} card={card} onApprove={handleApprove} onEdit={(updates) => handleEdit('flashcard', card.id, updates)} />
                        ))}
                    </div>
                </div>
            )}

            <div>
                <h2 className="text-xl font-bold mb-8 flex items-center gap-3 text-white">
                    <div className="p-2 bg-blue-500/20 rounded-xl">
                        <CheckSquare className="w-6 h-6 text-blue-400" />
                    </div>
                    AI-Generated Questions
                </h2>
                {(drafts.questions.length === 0 && drafts.flashcards.length === 0) ? (
                    <p className="text-muted-foreground italic bg-muted/20 p-8 rounded-[32px] border border-dashed border-white/10 text-center">
                        No AI drafts found for this module.
                    </p>
                ) : (
                    <div className="space-y-12">
                        {drafts.questions.map((q, idx) => (
                            <QuestionReviewCard key={q.id} q={q} idx={idx} onApprove={handleApprove} onEdit={(updates) => handleEdit('question', q.id, updates)} />
                        ))}
                    </div>
                )}
            </div>

            <div className="bg-blue-600/10 p-10 rounded-[40px] border border-blue-500/20 flex flex-col md:flex-row items-center justify-between gap-8 mt-12">
                <div className="flex items-start gap-6">
                    <div className="w-16 h-16 bg-blue-500/20 text-blue-400 rounded-2xl flex items-center justify-center flex-shrink-0">
                        <ShieldCheck className="w-8 h-8" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-white mb-2">Ready to release?</h3>
                        <p className="text-blue-200/60 text-sm max-w-md leading-relaxed">
                            Publishing will make the module visible to students and assign the AI-generated assessment to everyone in <strong>{moduleTitle}</strong>.
                        </p>
                    </div>
                </div>
                <button
                    onClick={async () => {
                        setModalConfig({
                            type: 'confirm',
                            title: isPublished ? 'Sync Content Updates?' : 'Ready to Publish?',
                            message: isPublished
                                ? 'This will update the live module with all currently approved flashcards and questions.'
                                : 'This will publish the module and create a quiz assignment for all students. Continue?',
                            confirmText: isPublished ? 'Yes, Sync Changes' : 'Yes, Publish',
                            cancelText: 'Not Yet',
                            onConfirm: onPublish,
                            onCancel: () => setModalConfig(null)
                        });
                    }}
                    className="px-10 py-5 bg-blue-600 text-white rounded-2xl font-black hover:bg-blue-700 shadow-2xl shadow-blue-500/40 transition-all hover:scale-[1.05] active:scale-95 flex items-center gap-3 whitespace-nowrap"
                >
                    <Send className="w-6 h-6" />
                    {isPublished ? 'Sync Content Updates' : 'Confirm & Release'}
                </button>
            </div>
        </div>
    );
}

function EditableFlashcardCard({ card, onApprove, onEdit }) {
    const [isEditing, setIsEditing] = useState(false);
    const [editedCard, setEditedCard] = useState({ front: card.front, back: card.back });

    const handleSave = () => {
        onEdit(editedCard);
        setIsEditing(false);
    };

    if (isEditing) {
        return (
            <div className="bg-card p-6 rounded-3xl border-2 border-blue-500 shadow-xl space-y-4">
                <div className="space-y-1">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">Front Side</label>
                    <input
                        type="text"
                        value={editedCard.front}
                        onChange={(e) => setEditedCard({ ...editedCard, front: e.target.value })}
                        className="w-full p-3 bg-black/30 border border-white/10 rounded-xl text-sm text-foreground focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                </div>
                <div className="space-y-1">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">Back Side</label>
                    <textarea
                        value={editedCard.back}
                        onChange={(e) => setEditedCard({ ...editedCard, back: e.target.value })}
                        className="w-full p-3 bg-black/30 border border-white/10 rounded-xl text-sm text-foreground focus:ring-2 focus:ring-blue-500 outline-none"
                        rows={3}
                    />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                    <button onClick={() => setIsEditing(false)} className="px-4 py-2 text-xs font-bold text-muted-foreground hover:bg-white/5 rounded-xl transition-all">Cancel</button>
                    <button onClick={handleSave} className="px-4 py-2 text-xs font-bold bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/20">Save</button>
                </div>
            </div>
        );
    }

    return (
        <div key={card.id} className="bg-card p-6 rounded-3xl border border-white/5 shadow-sm flex flex-col justify-between gap-4 group hover:bg-white/5 transition-all hover:border-white/10 relative">
            <div className="flex-1">
                <p className="font-bold text-lg text-foreground mb-2 leading-tight">{card.front}</p>
                <div className="h-px w-8 bg-blue-500/30 mb-3" />
                <p className="text-sm text-muted-foreground leading-relaxed italic">{card.back}</p>
            </div>
            <div className="flex items-center justify-between mt-4">
                <button
                    onClick={() => setIsEditing(true)}
                    className="text-[10px] font-black text-blue-500 flex items-center gap-2 hover:text-blue-400 transition-colors uppercase tracking-widest"
                >
                    <Edit3 className="w-3.5 h-3.5" /> Edit
                </button>
                <button
                    onClick={() => onApprove('flashcard', card.id)}
                    className={`px-4 py-2 rounded-xl transition-all shadow-sm text-xs font-black flex items-center gap-2 ${card.is_approved
                        ? 'bg-green-600 text-white hover:bg-red-500/20 hover:text-red-500'
                        : 'bg-green-500/10 text-green-500 hover:bg-green-500 hover:text-white'
                        }`}
                >
                    {card.is_approved ? <><Check className="w-3.5 h-3.5" /> Approved</> : <><Check className="w-3.5 h-3.5" /> Approve</>}
                </button>
            </div>
        </div>
    );
}

function QuestionReviewCard({ q, idx, onApprove, onEdit }) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editedQ, setEditedQ] = useState({
        text: q.text,
        options: { ...q.options },
        correct_answer: q.correct_answer,
        explanation: q.explanation,
        model_answer: q.model_answer,
        required_keywords: q.required_keywords ? [...q.required_keywords] : []
    });

    const handleSave = (e) => {
        e.stopPropagation();
        onEdit(editedQ);
        setIsEditing(false);
    };

    if (isEditing) {
        return (
            <div className="bg-card rounded-[32px] border-2 border-blue-500 shadow-xl overflow-hidden p-8 space-y-6">
                <div>
                    <label className="text-[10px] font-black text-muted-foreground uppercase tracking-wider mb-2 block">Question Title</label>
                    <textarea
                        value={editedQ.text}
                        onChange={(e) => setEditedQ({ ...editedQ, text: e.target.value })}
                        className="w-full p-4 bg-black/30 border border-white/10 rounded-2xl text-lg font-bold text-foreground focus:ring-2 focus:ring-blue-500 outline-none"
                        rows={3}
                    />
                </div>

                {q.type === 'mcq' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {['A', 'B', 'C', 'D'].map(opt => (
                            <div key={opt} className="relative">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-2 block">Option {opt}</label>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => setEditedQ({ ...editedQ, correct_answer: opt })}
                                        className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black transition-all ${editedQ.correct_answer === opt ? 'bg-green-600 text-white shadow-lg' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}
                                    >
                                        {opt}
                                    </button>
                                    <input
                                        type="text"
                                        value={editedQ.options[opt]}
                                        onChange={(e) => setEditedQ({ ...editedQ, options: { ...editedQ.options, [opt]: e.target.value } })}
                                        className="flex-1 p-3 bg-black/30 border border-white/10 rounded-2xl text-sm outline-none focus:border-blue-500 text-foreground"
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                <div className="flex justify-end gap-3 pt-4 border-t border-white/5">
                    <button
                        onClick={() => setIsEditing(false)}
                        className="px-6 py-3 text-sm font-black text-muted-foreground hover:bg-white/5 rounded-2xl transition-all"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        className="px-8 py-3 bg-blue-600 text-white rounded-2xl font-black hover:bg-blue-700 shadow-lg shadow-blue-500/20 transition-all flex items-center gap-2"
                    >
                        <Check className="w-5 h-5" /> Save Changes
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div key={q.id} className="bg-card rounded-[32px] border border-white/5 shadow-sm overflow-hidden transition-all hover:shadow-xl hover:border-white/10 group">
            <div
                className="p-8 flex justify-between items-center gap-8 cursor-pointer relative"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex-1 flex items-start gap-6">
                    <div className="w-10 h-10 rounded-2xl bg-blue-500/10 text-blue-400 flex items-center justify-center font-black text-sm flex-shrink-0 mt-1 transition-colors group-hover:bg-blue-500 group-hover:text-white">
                        {idx + 1}
                    </div>
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-3">
                            <span className={`text-[10px] uppercase font-black tracking-widest px-3 py-1 rounded-full ${q.type === 'mcq' ? 'bg-blue-500/10 text-blue-400' : 'bg-purple-500/10 text-purple-400'}`}>
                                {q.type === 'mcq' ? 'Multiple Choice' : 'Critical Thinking'}
                            </span>
                        </div>
                        <h4 className="font-bold text-foreground text-xl leading-tight mb-4">{q.text}</h4>
                        <div className="flex items-center gap-6">
                            <p className="text-xs font-medium text-slate-500 flex items-center gap-2">
                                <Sparkles className="w-3 h-3 text-blue-400" />
                                {isExpanded ? 'Click to collapse' : 'Click to review content'}
                            </p>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setIsEditing(true);
                                }}
                                className="flex items-center gap-2 text-xs font-black text-blue-500 hover:text-blue-400 transition-colors"
                            >
                                <Edit3 className="w-3.5 h-3.5" /> Edit Question
                            </button>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    {isExpanded ? <ChevronUp className="w-5 h-5 text-slate-500" /> : <ChevronDown className="w-5 h-5 text-slate-500" />}
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            onApprove('question', q.id);
                        }}
                        className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-black transition-all shadow-sm ${q.is_approved
                            ? 'bg-green-600 text-white hover:bg-red-500/20 hover:text-red-500'
                            : 'bg-green-500/10 text-green-500 hover:bg-green-500 hover:text-white'
                            }`}
                    >
                        <Check className="w-5 h-5" />
                        {q.is_approved ? 'Approved' : 'Approve'}
                    </button>
                </div>
            </div>

            {isExpanded && (
                <div className="px-8 pb-8 pt-0 border-t border-white/5 bg-black/10">
                    <div className="pt-8 space-y-6">
                        {q.type === 'mcq' && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {Object.entries(q.options).map(([key, value]) => (
                                    <div
                                        key={key}
                                        className={`p-5 rounded-2xl border flex items-center gap-4 transition-all ${q.correct_answer === key
                                            ? 'bg-green-500/10 border-green-500/30 text-green-400 font-bold shadow-lg shadow-green-500/5'
                                            : 'bg-white/5 border-white/5 text-muted-foreground'
                                            }`}
                                    >
                                        <span className={`w-8 h-8 rounded-xl flex items-center justify-center font-black text-xs ${q.correct_answer === key ? 'bg-green-500 text-white' : 'bg-white/10'
                                            }`}>
                                            {key}
                                        </span>
                                        <span className="text-sm font-medium">{value}</span>
                                        {q.correct_answer === key && <CheckCircle className="w-5 h-5 ml-auto text-green-500" />}
                                    </div>
                                ))}
                            </div>
                        )}

                        {q.explanation && (
                            <div className="bg-blue-500/5 p-6 rounded-2xl border border-blue-500/10 flex items-start gap-4">
                                <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                                <div>
                                    <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1">AI Explanation</p>
                                    <p className="text-sm text-foreground/80 leading-relaxed font-medium">{q.explanation}</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function AnalyticsPanel({ analytics }) {
    if (!analytics) return <div className="p-8 text-center text-muted-foreground italic text-sm">Loading analytics...</div>;

    const stats = [
        { label: 'Not Started', value: analytics.not_started, color: 'bg-muted text-muted-foreground' },
        { label: 'In Progress', value: analytics.in_progress, color: 'bg-blue-500/20 text-blue-400' },
        { label: 'Completed', value: analytics.completed, color: 'bg-green-500/20 text-green-400' },
        { label: 'Total Students', value: analytics.total_students, color: 'bg-indigo-500/20 text-indigo-400' },
    ];

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-12">
            <h2 className="text-2xl font-bold text-white">Learning Progress</h2>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat, i) => (
                    <div key={i} className={`p-6 rounded-3xl border border-transparent shadow-sm ${stat.color.split(' ')[0]} flex flex-col items-center justify-center text-center`}>
                        <span className="text-3xl font-black mb-1">{stat.value}</span>
                        <span className="text-xs font-bold uppercase tracking-wider opacity-60">{stat.label}</span>
                    </div>
                ))}
            </div>

            <div className="bg-card rounded-3xl border border-white/5 overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-muted/30 border-b border-white/5">
                        <tr>
                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Student</th>
                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Status</th>
                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Time Spent</th>
                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Completion</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {analytics.student_details.map((student, i) => (
                            <tr key={i} className="hover:bg-white/5 transition-colors">
                                <td className="px-6 py-4 font-bold text-foreground text-sm">{student.student_name}</td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded-lg text-[10px] font-bold uppercase ${student.status === 'completed' ? 'bg-green-500/10 text-green-400' :
                                        student.status === 'in_progress' ? 'bg-blue-500/10 text-blue-400' : 'bg-muted text-muted-foreground'
                                        }`}>
                                        {student.status.replace('_', ' ')}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-xs text-muted-foreground font-mono">
                                    {Math.floor(student.time_spent / 60)}m {student.time_spent % 60}s
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-2">
                                        <div className="h-1.5 w-16 bg-muted rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${student.completion}%` }} />
                                        </div>
                                        <span className="text-[10px] font-bold text-muted-foreground">{student.completion}%</span>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function FlashcardViewer({ deck }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isFlipped, setIsFlipped] = useState(false);

    if (!deck || !deck.cards || deck.cards.length === 0) return null;

    const currentCard = deck.cards[currentIndex];

    const nextCard = () => {
        setIsFlipped(false);
        setCurrentIndex((prev) => (prev + 1) % deck.cards.length);
    };

    const prevCard = () => {
        setIsFlipped(false);
        setCurrentIndex((prev) => (prev - 1 + deck.cards.length) % deck.cards.length);
    };

    return (
        <div className="w-full max-w-2xl">
            <div className="flex items-center justify-between mb-6">
                <h3 className="font-bold text-foreground">{deck.name}</h3>
                <span className="text-sm font-mono text-muted-foreground">
                    {currentIndex + 1} / {deck.cards.length}
                </span>
            </div>

            {/* Card */}
            <div
                className="perspective-1000 w-full h-64 md:h-72 cursor-pointer group"
                onClick={() => setIsFlipped(!isFlipped)}
            >
                <div className={`relative w-full h-full transition-transform duration-500 transform-style-3d ${isFlipped ? 'rotate-y-180' : ''}`}>
                    {/* Front */}
                    <div className="absolute inset-0 backface-hidden bg-card rounded-3xl shadow-xl border border-white/10 flex flex-col items-center justify-center p-12 text-center text-foreground">
                        <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-4">Term / Concept</span>
                        <h4 className="text-2xl font-bold">{currentCard.front}</h4>
                        <p className="absolute bottom-6 text-xs text-muted-foreground">Click to flip</p>
                    </div>

                    {/* Back */}
                    <div className="absolute inset-0 backface-hidden bg-card rounded-3xl shadow-xl border border-blue-500/30 rotate-y-180 flex flex-col items-center justify-center p-12 text-center text-foreground ring-4 ring-blue-500/10" style={{ transform: 'rotateY(180deg)' }}>
                        <span className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-4">Definition</span>
                        <p className="text-xl text-muted-foreground leading-relaxed">{currentCard.back}</p>
                    </div>
                </div>
                {/* Draft Badge Overlay for Teachers */}
                {!currentCard.is_approved && (
                    <div className="absolute top-4 right-4 z-20 pointer-events-none">
                        <span className="bg-amber-500/90 text-black text-[10px] font-black px-3 py-1 rounded-full shadow-lg border border-amber-400 uppercase tracking-widest flex items-center gap-1">
                            <Sparkles className="w-3 h-3" /> Draft Item
                        </span>
                    </div>
                )}
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-10 mt-8">
                <button
                    onClick={(e) => { e.stopPropagation(); prevCard(); }}
                    className="p-6 bg-blue-600 text-white rounded-full shadow-lg border-2 border-blue-700 hover:bg-blue-700 transition-transform active:scale-95 flex items-center justify-center focus:outline-none focus:ring-4 focus:ring-blue-300"
                    aria-label="Previous Card"
                >
                    <ArrowLeft className="w-8 h-8 text-white" />
                </button>
                <button
                    onClick={(e) => { e.stopPropagation(); nextCard(); }}
                    className="p-6 bg-blue-600 text-white rounded-full shadow-lg border-2 border-blue-700 hover:bg-blue-700 transition-transform active:scale-95 flex items-center justify-center focus:outline-none focus:ring-4 focus:ring-blue-300"
                    aria-label="Next Card"
                >
                    <ArrowLeft className="w-8 h-8 rotate-180 text-white" />
                </button>
            </div>
        </div>
    );
}

function KnowledgePrepPanel({ questions }) {
    if (!questions || questions.length === 0) {
        return (
            <div className="text-center py-20 text-slate-400 max-w-4xl mx-auto">
                <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No prep questions available yet.</p>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-12">
            <div className="flex flex-col gap-2">
                <h2 className="text-2xl font-black text-white">Self-Assessment Prep</h2>
                <p className="text-muted-foreground font-medium">Study these AI-generated questions and answers to prepare for your final assessment.</p>
            </div>

            <div className="space-y-12">
                {questions.map((q, idx) => (
                    <div key={q.id} className="bg-card rounded-[32px] p-8 border border-white/5 shadow-sm hover:shadow-md transition-all">
                        <div className="flex items-start gap-6">
                            <div className="w-10 h-10 rounded-2xl bg-primary text-white flex items-center justify-center font-black text-sm flex-shrink-0">
                                {idx + 1}
                            </div>
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${q.question_type === 'mcq' ? 'bg-blue-500/10 text-blue-400' : 'bg-purple-500/10 text-purple-400'
                                        }`}>
                                        {q.question_type === 'mcq' ? 'Multiple Choice' : 'Critical Thinking'}
                                    </span>
                                    {!q.is_approved && (
                                        <span className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">
                                            Draft
                                        </span>
                                    )}
                                </div>
                                <h3 className="text-xl font-bold text-foreground leading-tight">
                                    {q.question_text}
                                </h3>
                                {q.question_type === 'mcq' ? (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
                                        {['a', 'b', 'c', 'd'].map(opt => (
                                            <div
                                                key={opt}
                                                className={`p-4 rounded-2xl border flex items-center gap-3 ${q.correct_answer === opt.toUpperCase()
                                                    ? 'bg-green-500/10 border-green-500/20 text-green-400 font-bold'
                                                    : 'bg-black/20 border-white/5 text-muted-foreground'
                                                    }`}
                                            >
                                                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black ${q.correct_answer === opt.toUpperCase() ? 'bg-green-600 text-white' : 'bg-white/10 text-muted-foreground'
                                                    }`}>
                                                    {opt.toUpperCase()}
                                                </span>
                                                {q[`option_${opt}`]}
                                                {q.correct_answer === opt.toUpperCase() && (
                                                    <CheckCircle2 className="w-4 h-4 ml-auto" />
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="bg-blue-500/5 rounded-2xl p-6 border border-blue-500/10 mb-6">
                                        <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-3">Model Answer</p>
                                        <p className="text-foreground leading-relaxed font-medium">
                                            {q.model_answer}
                                        </p>
                                    </div>
                                )}

                                {q.explanation && (
                                    <div className="flex items-start gap-3 bg-white/5 p-4 rounded-xl border border-white/5">
                                        <AlertCircle className="w-4 h-4 text-muted-foreground mt-0.5" />
                                        <div className="text-xs text-muted-foreground leading-relaxed">
                                            <span className="font-bold text-foreground mr-2">Explanation:</span>
                                            {q.explanation}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
