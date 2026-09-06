'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    Upload, FileText, Loader2, ArrowLeft, CheckCircle, Brain,
    Sparkles, User, HelpCircle, FileQuestion, GraduationCap, Send
} from 'lucide-react';
import { learningAPI, classroomAPI } from '@/lib/api';
import UploadMaterialCard from '@/components/learning/UploadMaterialCard';
import CustomSelect from '@/components/ui/CustomSelect';

export default function CreateModulePage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [step, setStep] = useState('create'); // 'create' | 'confirming' | 'generating' | 'success'
    const [genStep, setGenStep] = useState(0); // 0: Parsing, 1: Generating, 2: Structuring

    const [classrooms, setClassrooms] = useState([]);

    const [formData, setFormData] = useState({
        title: '',
        description: '',
        classroom: '',
        pdf_file: null,
        extractionMode: 'ai',
        selectedTypes: {
            quiz: true,
            flashcard: true,
            essay: true
        }
    });

    useEffect(() => {
        fetchClassrooms();
    }, []);

    const fetchClassrooms = async () => {
        try {
            const data = await classroomAPI.getTeachingClassrooms();
            const classroomList = Array.isArray(data) ? data : data?.results || [];
            setClassrooms(classroomList);
            if (classroomList.length > 0) {
                setFormData(prev => ({ ...prev, classroom: classroomList[0].id }));
            }
        } catch (error) {
            console.error('Failed to fetch classrooms:', error);
        }
    };

    const toggleType = (type) => {
        setFormData(prev => ({
            ...prev,
            selectedTypes: {
                ...prev.selectedTypes,
                [type]: !prev.selectedTypes[type]
            }
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!formData.pdf_file && formData.extractionMode === 'ai') {
            alert('Please upload a PDF for AI extraction.');
            return;
        }
        setStep('confirming');
    };

    const handleConfirm = async () => {
        setLoading(true);

        try {
            const submitData = new FormData();
            submitData.append('title', formData.title);
            submitData.append('description', formData.description);
            submitData.append('classroom', formData.classroom);
            if (formData.pdf_file) {
                submitData.append('pdf_file', formData.pdf_file);
            }

            const module = await learningAPI.createModule(submitData);

            if (module.id && formData.extractionMode === 'ai') {
                setStep('generating');

                setGenStep(0); // Parsing
                const parsingTimer = setTimeout(() => setGenStep(1), 2500);

                const types = Object.keys(formData.selectedTypes).filter(t => formData.selectedTypes[t]);
                await learningAPI.generateAIContent(module.id, { types });

                clearTimeout(parsingTimer);
                setGenStep(2); // Structuring
                setTimeout(() => setStep('success'), 1500);
            } else {
                setStep('success');
            }

            setTimeout(() => {
                router.push(`/dashboard/learning/${module.id}`);
            }, 3500);
        } catch (error) {
            console.error('Error creating module:', error);
            alert('Failed to create module. Please try again.');
            setLoading(false);
            setStep('create');
        }
    };

    if (step === 'generating') {
        const steps = [
            { id: 0, label: 'Parsing Content', sub: 'Analyzing PDF structure and text extraction' },
            { id: 1, label: 'Generating Questions', sub: 'AI is framing challenges based on keys concepts' },
            { id: 2, label: 'Structuring Module', sub: 'Finalizing flashcards and quiz organization' }
        ];

        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center max-w-lg mx-auto p-8 bg-card rounded-[40px] shadow-2xl shadow-primary/10 border border-white/5">
                <div className="relative mb-12">
                    <div className="w-24 h-24 rounded-full border-[6px] border-white/5 border-t-primary animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                        <Sparkles className="w-8 h-8 text-primary animate-pulse" />
                    </div>
                </div>

                <div className="space-y-4 w-full mb-10">
                    <h2 className="text-3xl font-black text-foreground tracking-tight">AI Generation in Progress</h2>
                    <p className="text-muted-foreground font-medium">Sit tight! We're transforming your PDF into interactive study material.</p>
                </div>

                <div className="w-full space-y-3">
                    {steps.map((s, idx) => (
                        <div key={s.id} className={`flex items-center gap-4 p-4 rounded-2xl transition-all duration-500 ${genStep === idx ? 'bg-primary/10 scale-100 opacity-100 border border-primary/20' :
                            genStep > idx ? 'opacity-40 grayscale-[0.5]' : 'opacity-20 translate-y-2'
                            }`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${genStep === idx ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20' :
                                genStep > idx ? 'bg-emerald-500 text-white' : 'bg-muted text-muted-foreground'
                                }`}>
                                {genStep > idx ? <CheckCircle className="w-4 h-4" /> : idx + 1}
                            </div>
                            <div className="text-left flex-1">
                                <p className={`font-black text-sm ${genStep === idx ? 'text-primary' : 'text-muted-foreground'}`}>{s.label}</p>
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">{s.sub}</p>
                            </div>
                            {genStep === idx && <Loader2 className="w-4 h-4 text-primary animate-spin" />}
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (step === 'success') {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-6">
                <div className="w-24 h-24 bg-emerald-500/20 text-emerald-500 rounded-full flex items-center justify-center animate-bounce shadow-lg shadow-emerald-500/20">
                    <CheckCircle className="w-12 h-12" />
                </div>
                <div>
                    <h2 className="text-3xl font-black text-foreground tracking-tight">Module Created!</h2>
                    <p className="text-muted-foreground font-medium mt-2">Perfect. We're taking you to the review dashboard.</p>
                </div>
            </div>
        );
    }

    if (step === 'confirming') {
        return (
            <div className="max-w-2xl mx-auto pb-20">
                <button
                    onClick={() => setStep('create')}
                    className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors font-bold text-sm"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Edit
                </button>

                <div className="bg-card rounded-[32px] p-10 shadow-xl shadow-black/20 border border-border">
                    <div className="flex items-center gap-4 mb-8">
                        <div className="w-14 h-14 bg-primary/10 text-primary rounded-2xl flex items-center justify-center shadow-inner">
                            <GraduationCap className="w-8 h-8" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-black text-foreground tracking-tight">Final Confirmation</h1>
                            <p className="text-muted-foreground font-medium">Review your module settings</p>
                        </div>
                    </div>

                    <div className="space-y-6 bg-muted/20 border border-white/5 rounded-[24px] p-8 mb-10">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div>
                                <p className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.15em] mb-2">Module Title</p>
                                <p className="font-bold text-foreground text-lg leading-tight">{formData.title}</p>
                            </div>
                            <div>
                                <p className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.15em] mb-2">Strategy</p>
                                <div className="flex items-center gap-2 text-primary font-black text-sm">
                                    {formData.extractionMode === 'ai' ? (
                                        <><Sparkles className="w-4 h-4" /> AI Auto-Extract</>
                                    ) : (
                                        <><User className="w-4 h-4" /> Manual Setup</>
                                    )}
                                </div>
                            </div>
                        </div>

                        {formData.extractionMode === 'ai' && (
                            <div className="pt-6 border-t border-white/5">
                                <p className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.15em] mb-3">AI Deliverables</p>
                                <div className="flex flex-wrap gap-2">
                                    {formData.selectedTypes.quiz && (
                                        <span className="px-3 py-1.5 bg-card border border-white/10 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm text-foreground">
                                            <FileQuestion className="w-3.5 h-3.5 text-purple-400" /> Quiz MCQs
                                        </span>
                                    )}
                                    {formData.selectedTypes.flashcard && (
                                        <span className="px-3 py-1.5 bg-card border border-white/10 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm text-foreground">
                                            <Brain className="w-3.5 h-3.5 text-amber-400" /> Spaced Cards
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleConfirm}
                        disabled={loading}
                        className="w-full py-5 rounded-[22px] font-black text-lg text-white transition-all transform flex items-center justify-center gap-3 btn-enterprise-primary hover:scale-[1.01] active:scale-[0.98]"
                    >
                        {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : <CheckCircle className="w-6 h-6" />}
                        Confirm & Launch AI
                    </button>
                    <p className="text-center text-muted-foreground text-[10px] font-bold uppercase tracking-widest mt-6">
                        Generation process takes ~15-30 seconds
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto">
            <button
                onClick={() => router.back()}
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors font-bold text-sm"
            >
                <ArrowLeft className="w-4 h-4" />
                Back to Learning
            </button>

            <div className="bg-card rounded-[32px] p-10 shadow-xl shadow-black/20 border border-border">
                <h1 className="text-3xl font-black text-foreground tracking-tight mb-8">Create Module</h1>

                <form onSubmit={handleSubmit} className="space-y-10">
                    <div>
                        <label className="block text-xs font-black text-muted-foreground uppercase tracking-widest mb-3">
                            General Information
                        </label>
                        <div className="space-y-4">
                            <input
                                type="text"
                                placeholder="Module Title (e.g., Photosynthesis)"
                                className="w-full px-5 py-4 rounded-2xl border border-white/10 bg-black/20 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-bold text-foreground placeholder:text-muted-foreground/50"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                required
                            />
                            <textarea
                                placeholder="Brief description of what students will learn..."
                                className="w-full px-5 py-4 rounded-2xl border border-white/10 bg-black/20 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all h-32 resize-none font-medium text-foreground placeholder:text-muted-foreground/50"
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div>
                            <CustomSelect
                                label="Classroom Target"
                                options={classrooms.map(c => ({ value: c.id, label: c.name }))}
                                value={formData.classroom}
                                onChange={(val) => setFormData({ ...formData, classroom: val })}
                                placeholder="Select a classroom"
                                required
                            />
                        </div>
                    </div>

                    <UploadMaterialCard
                        onFileSelect={(file) => setFormData({ ...formData, pdf_file: file })}
                        onModeChange={(mode) => setFormData({ ...formData, extractionMode: mode })}
                        selectedFile={formData.pdf_file}
                        extractionMode={formData.extractionMode}
                    />

                    {formData.extractionMode === 'ai' && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-top-4 duration-500">
                            <label className="block text-xs font-black text-muted-foreground uppercase tracking-widest mb-1">
                                Content Strategy
                            </label>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                {[
                                    { id: 'quiz', label: 'AI Quiz', icon: FileQuestion, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
                                    { id: 'flashcard', label: 'Cards', icon: Brain, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
                                    { id: 'essay', label: 'Prep Qs', icon: Sparkles, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20' }
                                ].map(type => (
                                    <button
                                        key={type.id}
                                        type="button"
                                        onClick={() => toggleType(type.id)}
                                        className={`flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition-all shadow-sm ${formData.selectedTypes[type.id]
                                            ? `border-primary bg-primary/10`
                                            : 'border-white/5 hover:border-white/10 opacity-60'
                                            }`}
                                    >
                                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${type.bg} ${type.color} border ${type.border} shadow-sm`}>
                                            <type.icon className="w-5 h-5" />
                                        </div>
                                        <span className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">{type.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="pt-6 border-t border-white/5 pb-20">
                        <button
                            type="submit"
                            disabled={formData.extractionMode === 'ai' && !formData.pdf_file}
                            className={`w-full py-5 rounded-[22px] font-black text-lg transition-all transform flex items-center justify-center gap-3 shadow-2xl ${formData.extractionMode === 'ai' && !formData.pdf_file
                                ? 'bg-muted text-muted-foreground cursor-not-allowed grayscale'
                                : 'btn-enterprise-primary hover:scale-[1.01] active:scale-[0.98]'
                                }`}
                        >
                            Next: Review & Confirm
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
