'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
    Brain, BookOpen, Target, Zap, ChevronRight, Check,
    Eye, BookText, Puzzle, MessageSquare,
    Calculator, Microscope, Book, Globe, Languages, Laptop,
    Sunrise, Sun, Sunset, Moon
} from 'lucide-react';
import { userAPI } from '@/lib/api';
import Toast from '@/components/ui/Toast';

const LEARNING_STYLES = [
    {
        id: 'visual',
        label: 'Visual Learner',
        icon: Eye,
        description: 'I learn best with diagrams, charts, and images'
    },
    {
        id: 'reading',
        label: 'Reading/Writing',
        icon: BookText,
        description: 'I prefer reading text and taking notes'
    },
    {
        id: 'problem_solving',
        label: 'Problem Solver',
        icon: Puzzle,
        description: 'I learn by doing practice problems'
    },
    {
        id: 'explanation',
        label: 'Explanation-Based',
        icon: MessageSquare,
        description: 'I need detailed step-by-step explanations'
    }
];

const SUBJECTS = [
    { id: 'mathematics', label: 'Mathematics', icon: Calculator },
    { id: 'science', label: 'Science', icon: Microscope },
    { id: 'english', label: 'English', icon: Book },
    { id: 'social_studies', label: 'Social Studies', icon: Globe },
    { id: 'hindi', label: 'Hindi', icon: Languages },
    { id: 'computer_science', label: 'Computer Science', icon: Laptop }
];

const STUDY_TIMES = [
    { id: 'morning', label: 'Morning', icon: Sunrise, time: '6 AM - 12 PM' },
    { id: 'afternoon', label: 'Afternoon', icon: Sun, time: '12 PM - 5 PM' },
    { id: 'evening', label: 'Evening', icon: Sunset, time: '5 PM - 9 PM' },
    { id: 'night', label: 'Night', icon: Moon, time: '9 PM - 12 AM' }
];

export default function OnboardingWizard() {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [toast, setToast] = useState(null);

    // Form state
    const [learningStyle, setLearningStyle] = useState('');
    const [studyTime, setStudyTime] = useState('');
    const [subjectConfidences, setSubjectConfidences] = useState({});

    const handleConfidenceChange = (subject, level) => {
        setSubjectConfidences(prev => ({
            ...prev,
            [subject]: level
        }));
    };

    const handleSubmit = async () => {
        setLoading(true);

        try {
            await userAPI.createLearningProfile({
                learning_style: learningStyle,
                preferred_study_time: studyTime,
                subject_confidences: Object.entries(subjectConfidences).map(([subject, confidence_level]) => ({
                    subject,
                    confidence_level
                }))
            });

            // Redirect to diagnostic test
            router.push('/dashboard/diagnostic-test');
        } catch (error) {
            console.error('Error:', error);
            setToast({ message: error.response?.data?.message || 'Failed to create profile', type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const canProceed = () => {
        if (step === 1) return learningStyle !== '';
        if (step === 2) return studyTime !== '';
        if (step === 3) return Object.keys(subjectConfidences).length >= 3;
        return false;
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-secondary/5 flex items-center justify-center p-4">
            <div className="w-full max-w-4xl">
                {/* Progress Bar */}
                <div className="mb-8">
                    <div className="flex items-center justify-between mb-4">
                        {[1, 2, 3].map((s) => (
                            <div key={s} className="flex items-center flex-1">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${s < step ? 'bg-primary text-primary-foreground' :
                                    s === step ? 'bg-primary text-primary-foreground ring-4 ring-primary/20' :
                                        'bg-secondary text-muted-foreground'
                                    }`}>
                                    {s < step ? <Check className="w-5 h-5" /> : s}
                                </div>
                                {s < 3 && (
                                    <div className={`flex-1 h-1 mx-2 rounded-full transition-all ${s < step ? 'bg-primary' : 'bg-secondary'
                                        }`} />
                                )}
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-between text-sm">
                        <span className={step >= 1 ? 'text-primary font-semibold' : 'text-muted-foreground'}>Learning Style</span>
                        <span className={step >= 2 ? 'text-primary font-semibold' : 'text-muted-foreground'}>Study Time</span>
                        <span className={step >= 3 ? 'text-primary font-semibold' : 'text-muted-foreground'}>Subject Confidence</span>
                    </div>
                </div>

                {/* Main Card */}
                <div className="bg-card border border-border rounded-3xl shadow-2xl p-8 md:p-12">
                    {/* Step 1: Learning Style */}
                    {step === 1 && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="text-center mb-8">
                                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-2xl mb-4">
                                    <Brain className="w-8 h-8 text-primary" />
                                </div>
                                <h2 className="text-3xl font-black text-foreground mb-2">How do you learn best?</h2>
                                <p className="text-muted-foreground">Choose the learning style that suits you most</p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {LEARNING_STYLES.map((style) => {
                                    const IconComponent = style.icon;
                                    return (
                                        <button
                                            key={style.id}
                                            onClick={() => setLearningStyle(style.id)}
                                            className={`p-6 rounded-2xl border-2 transition-all text-left ${learningStyle === style.id
                                                ? 'border-primary bg-primary/10 shadow-lg scale-105'
                                                : 'border-border hover:border-primary/50 hover:bg-secondary'
                                                }`}
                                        >
                                            <div className="w-12 h-12 mb-3 text-primary">
                                                <IconComponent className="w-full h-full" />
                                            </div>
                                            <h3 className="font-bold text-lg text-foreground mb-1">{style.label}</h3>
                                            <p className="text-sm text-muted-foreground">{style.description}</p>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Study Time */}
                    {step === 2 && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="text-center mb-8">
                                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-2xl mb-4">
                                    <Zap className="w-8 h-8 text-primary" />
                                </div>
                                <h2 className="text-3xl font-black text-foreground mb-2">When do you study best?</h2>
                                <p className="text-muted-foreground">Select your preferred study time</p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {STUDY_TIMES.map((time) => {
                                    const IconComponent = time.icon;
                                    return (
                                        <button
                                            key={time.id}
                                            onClick={() => setStudyTime(time.id)}
                                            className={`p-6 rounded-2xl border-2 transition-all text-left ${studyTime === time.id
                                                ? 'border-primary bg-primary/10 shadow-lg scale-105'
                                                : 'border-border hover:border-primary/50 hover:bg-secondary'
                                                }`}
                                        >
                                            <div className="w-12 h-12 mb-3 text-primary">
                                                <IconComponent className="w-full h-full" />
                                            </div>
                                            <h3 className="font-bold text-lg text-foreground mb-1">{time.label}</h3>
                                            <p className="text-sm text-muted-foreground">{time.time}</p>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Subject Confidence */}
                    {step === 3 && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="text-center mb-8">
                                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-2xl mb-4">
                                    <Target className="w-8 h-8 text-primary" />
                                </div>
                                <h2 className="text-3xl font-black text-foreground mb-2">Rate your confidence</h2>
                                <p className="text-muted-foreground">How confident are you in each subject? (Select at least 3)</p>
                            </div>

                            <div className="space-y-4">
                                {SUBJECTS.map((subject) => {
                                    const IconComponent = subject.icon;
                                    return (
                                        <div key={subject.id} className="bg-secondary/30 p-6 rounded-2xl border border-border">
                                            <div className="flex items-center justify-between mb-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 text-primary">
                                                        <IconComponent className="w-full h-full" />
                                                    </div>
                                                    <span className="font-bold text-foreground">{subject.label}</span>
                                                </div>
                                                {subjectConfidences[subject.id] && (
                                                    <span className="text-sm font-semibold text-primary">
                                                        Level {subjectConfidences[subject.id]}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex gap-2">
                                                {[1, 2, 3, 4, 5].map((level) => (
                                                    <button
                                                        key={level}
                                                        onClick={() => handleConfidenceChange(subject.id, level)}
                                                        className={`flex-1 py-3 rounded-xl font-bold transition-all ${subjectConfidences[subject.id] === level
                                                            ? 'bg-primary text-primary-foreground shadow-lg scale-105'
                                                            : 'bg-card border border-border hover:bg-secondary text-muted-foreground'
                                                            }`}
                                                    >
                                                        {level}
                                                    </button>
                                                ))}
                                            </div>
                                            <div className="flex justify-between text-xs text-muted-foreground mt-2 px-1">
                                                <span>Very Low</span>
                                                <span>Very High</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {Object.keys(subjectConfidences).length < 3 && (
                                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 text-center">
                                    <p className="text-sm text-yellow-600 dark:text-yellow-400">
                                        Please rate at least 3 subjects to continue
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Navigation Buttons */}
                    <div className="flex items-center justify-between mt-8 pt-6 border-t border-border">
                        {step > 1 ? (
                            <button
                                onClick={() => setStep(step - 1)}
                                className="px-6 py-3 rounded-xl border border-border hover:bg-secondary text-foreground font-semibold transition-all"
                            >
                                Back
                            </button>
                        ) : <div />}

                        {step < 3 ? (
                            <button
                                onClick={() => setStep(step + 1)}
                                disabled={!canProceed()}
                                className="px-8 py-3 rounded-xl bg-primary text-primary-foreground font-bold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-lg shadow-primary/20"
                            >
                                Next
                                <ChevronRight className="w-5 h-5" />
                            </button>
                        ) : (
                            <button
                                onClick={handleSubmit}
                                disabled={!canProceed() || loading}
                                className="px-8 py-3 rounded-xl bg-primary text-primary-foreground font-bold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-lg shadow-primary/20"
                            >
                                {loading ? 'Creating Profile...' : 'Start Diagnostic Test'}
                                <ChevronRight className="w-5 h-5" />
                            </button>
                        )}
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
        </div>
    );
}
