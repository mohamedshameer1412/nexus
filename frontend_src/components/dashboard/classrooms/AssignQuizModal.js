import { useState, useEffect } from 'react';
import {
    X,
    BookOpen,
    Clock,
    Shield,
    Settings,
    CheckCircle2,
    Calendar,
    AlertCircle,
    ChevronRight,
    Search,
    Filter
} from 'lucide-react';
import { quizAPI } from '@/lib/api';

export default function AssignQuizModal({ isOpen, onClose, onAssign, onUpdate, initialAssignment = null }) {
    const [step, setStep] = useState(1); // 1: Select Quiz, 2: Configure, 3: Review
    const [searchQuery, setSearchQuery] = useState('');
    const [quizzes, setQuizzes] = useState([]);
    const [loading, setLoading] = useState(false);

    // Selection state
    const [selectedQuiz, setSelectedQuiz] = useState(null);
    const [config, setConfig] = useState({
        quiz_mode: 'practice', // practice | assessment
        allow_unlimited_attempts: true,
        max_attempts: 1,
        time_limit_minutes: '', // Empty means use quiz default
        due_date: '',
        show_immediate_feedback: true,
        enable_proctoring: false,
        shuffle_questions: true,
        shuffle_options: true
    });

    useEffect(() => {
        if (isOpen) {
            fetchQuizzes();
            if (initialAssignment) {
                // If editing, jump to configuration step
                setSelectedQuiz({
                    id: initialAssignment.quiz_id || initialAssignment.id,
                    title: initialAssignment.title,
                    time_limit: initialAssignment.time_limit_minutes || initialAssignment.time_limit
                });
                setConfig({
                    quiz_mode: initialAssignment.quiz_mode || 'practice',
                    allow_unlimited_attempts: initialAssignment.allow_unlimited_attempts !== undefined ? initialAssignment.allow_unlimited_attempts : (initialAssignment.quiz_mode === 'practice'),
                    max_attempts: initialAssignment.max_attempts || 1,
                    time_limit_minutes: initialAssignment.time_limit_minutes || '',
                    due_date: initialAssignment.due_date ? new Date(initialAssignment.due_date).toISOString().slice(0, 16) : '',
                    show_immediate_feedback: initialAssignment.show_immediate_feedback !== undefined ? initialAssignment.show_immediate_feedback : true,
                    enable_proctoring: initialAssignment.enable_proctoring || false,
                    shuffle_questions: initialAssignment.shuffle_questions !== undefined ? initialAssignment.shuffle_questions : true,
                    shuffle_options: initialAssignment.shuffle_options !== undefined ? initialAssignment.shuffle_options : true
                });
                setStep(2);
            } else {
                setStep(1);
                setSelectedQuiz(null);
                setConfig({
                    quiz_mode: 'practice',
                    allow_unlimited_attempts: true,
                    max_attempts: 1,
                    time_limit_minutes: '',
                    due_date: '',
                    show_immediate_feedback: true,
                    enable_proctoring: false,
                    shuffle_questions: true,
                    shuffle_options: true
                });
            }
        }
    }, [isOpen, initialAssignment]);

    const fetchQuizzes = async () => {
        setLoading(true);
        try {
            const data = await quizAPI.getAllQuizzes();
            setQuizzes(data.results || data);
        } catch (error) {
            console.error('Failed to fetch quizzes:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleModeChange = (mode) => {
        setConfig(prev => ({
            ...prev,
            quiz_mode: mode,
            // Set defaults based on mode
            allow_unlimited_attempts: mode === 'practice',
            show_immediate_feedback: mode === 'practice',
            enable_proctoring: mode === 'assessment',
            max_attempts: mode === 'assessment' ? 1 : prev.max_attempts
        }));
    };

    const handleSubmit = () => {
        if (initialAssignment && onUpdate) {
            onUpdate(initialAssignment.assignment_id || initialAssignment.id, config);
        } else {
            onAssign(selectedQuiz.id, config);
        }
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-[#1e293b] w-full max-w-4xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="p-6 border-b border-white/10 flex items-center justify-between bg-[#0f172a]/50">
                    <div>
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <BookOpen className="w-5 h-5 text-blue-400" />
                            Assign Quiz to Classroom
                        </h2>
                        <p className="text-sm text-slate-400 mt-1">
                            {step === 1 && "Select a quiz from your library"}
                            {step === 2 && "Configure assignment settings"}
                            {step === 3 && "Review and confirm assignment"}
                        </p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Steps Progress */}
                <div className="px-6 py-4 bg-[#0f172a]/30 border-b border-white/5">
                    <div className="flex items-center gap-2 text-sm">
                        <span className={`px-3 py-1 rounded-full ${step >= 1 ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-slate-500'}`}>1. Select Quiz</span>
                        <ChevronRight className="w-4 h-4 text-slate-600" />
                        <span className={`px-3 py-1 rounded-full ${step >= 2 ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-slate-500'}`}>2. Settings</span>
                        <ChevronRight className="w-4 h-4 text-slate-600" />
                        <span className={`px-3 py-1 rounded-full ${step >= 3 ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-slate-500'}`}>3. Review</span>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">

                    {/* STEP 1: SELECT QUIZ */}
                    {step === 1 && (
                        <div className="space-y-4">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    type="text"
                                    placeholder="Search quizzes..."
                                    className="w-full bg-[#0f172a] border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {quizzes
                                    .filter(q => q.title.toLowerCase().includes(searchQuery.toLowerCase()))
                                    .map(quiz => (
                                        <div
                                            key={quiz.id}
                                            onClick={() => setSelectedQuiz(quiz)}
                                            className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedQuiz?.id === quiz.id
                                                ? 'bg-blue-500/10 border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                                                : 'bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10'
                                                }`}
                                        >
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="p-2 bg-[#0f172a] rounded-lg">
                                                    <BookOpen className={`w-5 h-5 ${selectedQuiz?.id === quiz.id ? 'text-blue-400' : 'text-slate-400'}`} />
                                                </div>
                                                {selectedQuiz?.id === quiz.id && <CheckCircle2 className="w-5 h-5 text-blue-500" />}
                                            </div>
                                            <h3 className="font-bold text-white mb-1">{quiz.title}</h3>
                                            <p className="text-xs text-slate-400 line-clamp-2 mb-3">{quiz.description || 'No description'}</p>
                                            <div className="flex items-center gap-3 text-xs text-slate-500">
                                                <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {quiz.time_limit || 'No'} limit</span>
                                                <span className="flex items-center gap-1"><AlertCircle className="w-3 h-3" /> {quiz.total_questions || 0} Qs</span>
                                            </div>
                                        </div>
                                    ))}
                            </div>
                        </div>
                    )}

                    {/* STEP 2: CONFIGURE */}
                    {step === 2 && (
                        <div className="space-y-8">

                            {/* Mode Selection */}
                            <div className="grid grid-cols-2 gap-4">
                                <button
                                    onClick={() => handleModeChange('practice')}
                                    className={`p-4 rounded-xl border text-left transition-all ${config.quiz_mode === 'practice'
                                        ? 'bg-emerald-500/10 border-emerald-500/50'
                                        : 'bg-white/5 border-white/5 opacity-60 hover:opacity-100'
                                        }`}
                                >
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className={`w-2 h-2 rounded-full ${config.quiz_mode === 'practice' ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                                        <span className={`font-bold ${config.quiz_mode === 'practice' ? 'text-emerald-400' : 'text-white'}`}>Practice Mode</span>
                                    </div>
                                    <p className="text-xs text-slate-400">Unlimited attempts, immediate feedback, no strict timing.</p>
                                </button>

                                <button
                                    onClick={() => handleModeChange('assessment')}
                                    className={`p-4 rounded-xl border text-left transition-all ${config.quiz_mode === 'assessment'
                                        ? 'bg-amber-500/10 border-amber-500/50'
                                        : 'bg-white/5 border-white/5 opacity-60 hover:opacity-100'
                                        }`}
                                >
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className={`w-2 h-2 rounded-full ${config.quiz_mode === 'assessment' ? 'bg-amber-500' : 'bg-slate-500'}`} />
                                        <span className={`font-bold ${config.quiz_mode === 'assessment' ? 'text-amber-400' : 'text-white'}`}>Assessment Mode</span>
                                    </div>
                                    <p className="text-xs text-slate-400">Limited attempts, strict timing, proctoring options.</p>
                                </button>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-6">
                                    <div className="space-y-4">
                                        <h4 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                                            <Settings className="w-4 h-4" /> General Settings
                                        </h4>

                                        <label className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5">
                                            <span className="text-sm text-slate-300">Unlimited Attempts</span>
                                            <input
                                                type="checkbox"
                                                checked={config.allow_unlimited_attempts}
                                                onChange={(e) => setConfig({ ...config, allow_unlimited_attempts: e.target.checked })}
                                            />
                                        </label>

                                        {!config.allow_unlimited_attempts && (
                                            <div className="bg-white/5 p-3 rounded-xl border border-white/5 flex items-center justify-between">
                                                <span className="text-sm text-slate-300">Max Attempts Allowed</span>
                                                <input
                                                    type="text"
                                                    value={config.max_attempts}
                                                    onChange={(e) => {
                                                        const val = e.target.value;
                                                        if (val === '' || /^[0-9]*$/.test(val)) {
                                                            setConfig({ ...config, max_attempts: val });
                                                        }
                                                    }}
                                                    className="w-20 bg-[#0f172a] border border-white/10 rounded-lg px-3 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
                                                />
                                            </div>
                                        )}

                                        <div className="bg-white/5 p-3 rounded-xl border border-white/5 flex flex-col gap-2">
                                            <span className="text-sm text-slate-300">Due Date (Optional)</span>
                                            <input
                                                type="datetime-local"
                                                value={config.due_date}
                                                onChange={(e) => setConfig({ ...config, due_date: e.target.value })}
                                                className="w-full bg-[#0f172a] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 [color-scheme:dark]"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-6">
                                    <div className="space-y-4">
                                        <h4 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                                            <Shield className="w-4 h-4" /> Advanced Controls
                                        </h4>

                                        <div className="bg-white/5 p-3 rounded-xl border border-white/5 flex flex-col gap-2">
                                            <div className="flex justify-between">
                                                <span className="text-sm text-slate-300">Time Limit (Override)</span>
                                                <span className="text-xs text-slate-500">Mins</span>
                                            </div>
                                            <input
                                                type="text"
                                                placeholder={`Default: ${selectedQuiz.time_limit || 'None'}`}
                                                value={config.time_limit_minutes}
                                                onChange={(e) => {
                                                    const val = e.target.value;
                                                    if (val === '' || /^[0-9]*$/.test(val)) {
                                                        setConfig({ ...config, time_limit_minutes: val });
                                                    }
                                                }}
                                                className="w-full bg-[#0f172a] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                                            />
                                            <p className="text-xs text-slate-500">Leave empty to use quiz default.</p>
                                        </div>

                                        <label className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5 cursor-pointer hover:bg-white/10 transition-colors">
                                            <div className="flex flex-col">
                                                <span className="text-sm text-slate-300">AI Proctoring</span>
                                                <span className="text-xs text-slate-500">Detect tab switches & content</span>
                                            </div>
                                            <input
                                                type="checkbox"
                                                checked={config.enable_proctoring}
                                                onChange={(e) => setConfig({ ...config, enable_proctoring: e.target.checked })}
                                            />
                                        </label>

                                        <label className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5 cursor-pointer hover:bg-white/10 transition-colors">
                                            <span className="text-sm text-slate-300">Shuffle Questions</span>
                                            <input
                                                type="checkbox"
                                                checked={config.shuffle_questions}
                                                onChange={(e) => setConfig({ ...config, shuffle_questions: e.target.checked })}
                                            />
                                        </label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* STEP 3: REVIEW */}
                    {step === 3 && (
                        <div className="space-y-6">
                            <div className="bg-blue-500/10 border border-blue-500/20 rounded-2xl p-6 text-center">
                                <h3 className="text-2xl font-bold text-white mb-2">{selectedQuiz.title}</h3>
                                <p className="text-blue-300">Ready to assign • {config.quiz_mode === 'practice' ? 'Practice Mode' : 'Assessment Mode'}</p>
                            </div>

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                                    <p className="text-slate-500 mb-1">Time Limit</p>
                                    <p className="text-white font-semibold">{config.time_limit_minutes || selectedQuiz.time_limit || 'No Limit'} mins</p>
                                </div>
                                <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                                    <p className="text-slate-500 mb-1">Attempts</p>
                                    <p className="text-white font-semibold">{config.allow_unlimited_attempts ? 'Unlimited' : config.max_attempts}</p>
                                </div>
                                <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                                    <p className="text-slate-500 mb-1">Due Date</p>
                                    <p className="text-white font-semibold">{config.due_date ? new Date(config.due_date).toLocaleDateString('en-GB') : 'No Deadline'}</p>
                                </div>
                                <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                                    <p className="text-slate-500 mb-1">Proctoring</p>
                                    <p className={`font-semibold ${config.enable_proctoring ? 'text-amber-400' : 'text-slate-400'}`}>
                                        {config.enable_proctoring ? 'Enabled' : 'Disabled'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Buttons */}
                <div className="p-6 border-t border-white/10 bg-[#0f172a]/50 flex justify-end gap-3">
                    {step > 1 && !initialAssignment && (
                        <button
                            onClick={() => setStep(step - 1)}
                            className="px-6 py-2.5 rounded-xl border border-white/10 text-white hover:bg-white/5 transition-colors font-semibold text-sm"
                        >
                            Back
                        </button>
                    )}

                    {step < 3 ? (
                        <button
                            disabled={!selectedQuiz}
                            onClick={() => setStep(step + 1)}
                            className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-2.5 rounded-xl font-bold text-sm transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Continue
                        </button>
                    ) : (
                        <button
                            onClick={handleSubmit}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-2.5 rounded-xl font-bold text-sm transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2"
                        >
                            <CheckCircle2 className="w-4 h-4" /> Confirm Assignment
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
