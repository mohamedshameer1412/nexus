'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
    BookOpen, ArrowLeft, Clock, CheckCircle, Brain,
    FileText, Play, ChevronRight, Maximize2,
    Layout, Sparkles, Trophy, Star
} from 'lucide-react';
import { learningAPI, API_BASE_URL } from '@/lib/api';

export default function StudentViewPage() {
    const { id } = useParams();
    const router = useRouter();
    const [module, setModule] = useState(null);
    const [loading, setLoading] = useState(true);
    const [studyTime, setStudyTime] = useState(0);
    const [activeTab, setActiveTab] = useState('study'); // 'study' | 'flashcards'
    const [completed, setCompleted] = useState(false);

    const timerRef = useRef(null);

    useEffect(() => {
        fetchData();

        // Start timer
        timerRef.current = setInterval(() => {
            setStudyTime(prev => prev + 1);
        }, 1000);

        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
            // Auto-save time spent
            savePulse();
        };
    }, [id]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const data = await learningAPI.getModule(id);
            setModule(data);
            // Check if already completed from progress API
            // For now assume False unless marked
        } catch (error) {
            console.error('Fetch error:', error);
        } finally {
            setLoading(false);
        }
    };

    const savePulse = async () => {
        try {
            await learningAPI.updateProgress({
                module_id: id,
                time_spent: studyTime,
                status: completed ? 'completed' : 'in_progress'
            });
        } catch (e) {
            console.error('Progress sync failed');
        }
    };

    const handleComplete = async () => {
        setCompleted(true);
        await learningAPI.updateProgress({
            module_id: id,
            time_spent: studyTime,
            status: 'completed'
        });
        // Scroll to top or show celebration?
    };

    const formatTime = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h > 0 ? h + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    if (loading) return (
        <div className="flex items-center justify-center min-h-screen bg-slate-900">
            <div className="w-12 h-12 border-4 border-white/10 border-t-blue-500 rounded-full animate-spin" />
        </div>
    );

    return (
        <div className="h-screen flex flex-col bg-slate-950 text-white overflow-hidden font-sans">
            {/* Minimal Focus Header */}
            <header className="h-14 bg-slate-900/50 backdrop-blur-xl border-b border-white/5 px-6 flex items-center justify-between flex-shrink-0 z-50">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.push(`/dashboard/learning/${id}`)}
                        className="p-1.5 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div className="h-4 w-[1px] bg-white/10" />
                    <h1 className="text-sm font-black tracking-tight text-slate-200">
                        {module?.title}
                    </h1>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
                        <span className="text-[10px] font-black font-mono text-blue-400 uppercase tracking-widest">
                            Learning: {formatTime(studyTime)}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={handleComplete}
                        disabled={completed}
                        className={`px-4 py-1.5 rounded-xl font-black text-xs transition-all flex items-center gap-2 ${completed
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : 'bg-white text-slate-900 hover:bg-blue-50 shadow-lg shadow-white/5'
                            }`}
                    >
                        {completed ? <><CheckCircle className="w-3.5 h-3.5" /> Completed</> : 'Finish Lesson'}
                    </button>
                </div>
            </header>

            <div className="flex-1 flex overflow-hidden">
                {/* Left: Progression Sidebar */}
                <div className="w-64 bg-slate-900/30 border-r border-white/5 flex flex-col p-4">
                    <div className="mb-6">
                        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Course Progress</p>
                        <div className="space-y-1">
                            {[
                                { id: 'study', label: 'Study Content', icon: BookOpen },
                                { id: 'flashcards', label: 'Flashcards', icon: Brain }
                            ].map(item => (
                                <button
                                    key={item.id}
                                    onClick={() => setActiveTab(item.id)}
                                    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === item.id
                                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                                        : 'text-slate-400 hover:bg-white/5'
                                        }`}
                                >
                                    <item.icon className="w-4 h-4" />
                                    <span className="text-xs font-bold">{item.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                </div>

                {/* Right: Content Area */}
                <div className="flex-1 flex flex-col relative bg-[#020617]">
                    {completed && (
                        <div className="absolute inset-x-0 top-0 h-1 bg-green-500 shadow-[0_0_15px_rgba(34,197,94,0.5)] z-20" />
                    )}

                    {activeTab === 'study' && (
                        <div className="flex-1 flex flex-col overflow-hidden">
                            {module?.pdf_file ? (
                                <iframe
                                    src={`${module.pdf_file.startsWith('http') ? module.pdf_file : API_BASE_URL + module.pdf_file}#toolbar=0&view=FitH`}
                                    className="w-full h-full grayscale-[0.2] invert-[0.02] opacity-90"
                                    title="Study Material"
                                />
                            ) : (
                                <div className="flex-1 overflow-y-auto p-12 custom-scrollbar">
                                    <div className="max-w-3xl mx-auto">
                                        <div className="mb-12">
                                            <div className="flex items-center gap-2 text-blue-400 mb-4">
                                                <FileText className="w-5 h-5" />
                                                <span className="text-sm font-black uppercase tracking-widest">Document Text</span>
                                            </div>
                                            <h2 className="text-4xl font-black text-white mb-6 leading-tight uppercase tracking-tight">
                                                {module?.title}
                                            </h2>
                                            <p className="text-slate-400 text-lg leading-relaxed font-medium">
                                                {module?.description}
                                            </p>
                                        </div>

                                        <div className="bg-slate-900/50 rounded-[32px] p-10 border border-white/5 shadow-2xl">
                                            <div className="whitespace-pre-wrap text-slate-300 leading-loose text-xl font-serif">
                                                {module?.content_text || "No text content available."}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'flashcards' && (
                        <div className="flex-1 flex items-center justify-center p-8 bg-[#020617]">
                            <FlashcardCenter deck={module?.flashcard_decks?.[0]} />
                        </div>
                    )}
                </div>
            </div>

            {/* Completion Celebration Overlay */}
        </div>
    );
}

function FlashcardCenter({ deck }) {
    const [index, setIndex] = useState(0);
    const [flipped, setFlipped] = useState(false);

    if (!deck?.cards?.length) return (
        <div className="text-center opacity-30">
            <Brain className="w-16 h-16 mx-auto mb-4" />
            <p className="font-bold">No flashcards for this module</p>
        </div>
    );

    const card = deck.cards[index];

    return (
        <div className="w-full max-w-xl">
            <div className="text-center mb-8">
                <span className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em]">
                    Active Recall Layer — {index + 1} / {deck.cards.length}
                </span>
            </div>

            <div
                onClick={() => setFlipped(!flipped)}
                className="relative h-80 w-full perspective-1000 cursor-pointer group"
            >
                <div className={`relative w-full h-full transition-all duration-700 preserve-3d ${flipped ? 'rotate-y-180' : ''}`}>
                    {/* Front */}
                    <div className="absolute inset-0 bg-slate-900 border border-white/10 rounded-[40px] flex items-center justify-center p-12 backface-hidden shadow-2xl group-hover:border-blue-500/30 transition-colors">
                        <p className="text-2xl font-black text-center leading-tight">{card.front}</p>
                        <div className="absolute bottom-6 flex items-center gap-2 text-slate-600 text-[10px] font-black uppercase tracking-widest">
                            <Play className="w-3 h-3 fill-current rotate-90" /> Click to flip
                        </div>
                    </div>
                    {/* Back */}
                    <div className="absolute inset-0 bg-blue-600 border border-white/20 rounded-[40px] flex items-center justify-center p-12 backface-hidden rotate-y-180 shadow-2xl" style={{ transform: 'rotateY(180deg)' }}>
                        <p className="text-xl font-bold text-center leading-relaxed">{card.back}</p>
                    </div>
                </div>
            </div>

            <div className="flex justify-center gap-4 mt-8">
                <button
                    onClick={(e) => { e.stopPropagation(); setIndex(prev => (prev - 1 + deck.cards.length) % deck.cards.length); setFlipped(false); }}
                    className="w-12 h-12 rounded-full border border-white/10 flex items-center justify-center hover:bg-white/5 transition-all text-blue-400 border-blue-400/20"
                >
                    <ArrowLeft className="w-5 h-5" />
                </button>
                <button
                    onClick={(e) => { e.stopPropagation(); setIndex(prev => (prev + 1) % deck.cards.length); setFlipped(false); }}
                    className="w-12 h-12 rounded-full border border-white/10 flex items-center justify-center hover:bg-white/5 transition-all text-blue-400 border-blue-400/20"
                >
                    <ChevronRight className="w-6 h-6" />
                </button>
            </div>
        </div>
    );
}
