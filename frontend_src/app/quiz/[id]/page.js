'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { quizAPI } from '@/lib/api';
import { Loader2, CheckCircle, ArrowRight, Shield, Expand, Camera, AlertTriangle, XCircle, TrendingUp, Brain, Activity, Clock, Video, RefreshCw, Check } from 'lucide-react';
import Toast from '@/components/ui/Toast';
import ConfirmModal from '@/components/ui/ConfirmModal';
import * as faceapi from 'face-api.js';

export default function QuizSessionPage() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id;

    // Quiz State
    const [loading, setLoading] = useState(true);
    const [question, setQuestion] = useState(null);
    const [selectedOption, setSelectedOption] = useState(null);
    const [textAnswer, setTextAnswer] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [completed, setCompleted] = useState(false);
    const [error, setError] = useState(null);
    const [toast, setToast] = useState(null);
    const [progress, setProgress] = useState({ current: 0, total: 0 });

    // Stats State
    const [quizTitle, setQuizTitle] = useState('');
    const [difficulty, setDifficulty] = useState(3);
    const [mindset, setMindset] = useState('Neutral');
    const [timeLeft, setTimeLeft] = useState(null);
    const [quizStartedAt, setQuizStartedAt] = useState(null);
    const [timeLimit, setTimeLimit] = useState(null);
    const [showAnswersImmediately, setShowAnswersImmediately] = useState(false);

    // Proctoring State
    const [enableProctoring, setEnableProctoring] = useState(false);
    const [proctoringStarted, setProctoringStarted] = useState(false);
    const [tabSwitches, setTabSwitches] = useState(0);
    const [cameraStream, setCameraStream] = useState(null);
    const [cameraReady, setCameraReady] = useState(false);
    const [fullscreenReady, setFullscreenReady] = useState(false);
    const [cameraError, setCameraError] = useState(null);
    const videoRef = useRef(null);
    const setupVideoRef = useRef(null);

    // Face Detection State
    const [faceApiLoaded, setFaceApiLoaded] = useState(false);
    const [faceDetected, setFaceDetected] = useState(true);
    const [noFaceCount, setNoFaceCount] = useState(0);
    const MAX_NO_FACE_VIOLATIONS = 3;

    // Modal State
    const [showQuitModal, setShowQuitModal] = useState(false);
    const [showValidationModal, setShowValidationModal] = useState(false);
    const [validationMessage, setValidationMessage] = useState('');
    const [showFullscreenWarning, setShowFullscreenWarning] = useState(false);
    const [showAnswerFeedback, setShowAnswerFeedback] = useState(false);
    const [feedbackData, setFeedbackData] = useState(null);

    // Validation State
    const [wordCount, setWordCount] = useState(0);
    const [violationCount, setViolationCount] = useState(0);
    const MAX_VIOLATIONS = 3;

    // Load face-api models
    useEffect(() => {
        loadFaceApiModels();
    }, []);

    const loadFaceApiModels = async () => {
        try {
            // Try CDN first, fallback to local
            const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model';
            await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
            setFaceApiLoaded(true);
            console.log('Face detection models loaded');
        } catch (err) {
            console.error('Failed to load face detection models:', err);
            setToast({ type: 'warning', title: 'Face Detection Unavailable', message: 'Continuing without face detection.' });
        }
    };

    // Load initial question
    useEffect(() => {
        if (sessionId) loadNextQuestion();
    }, [sessionId]);

    // Timer countdown
    useEffect(() => {
        if (!quizStartedAt || !timeLimit) return;

        const interval = setInterval(() => {
            const startTime = new Date(quizStartedAt);
            const now = new Date();
            const elapsedSeconds = (now - startTime) / 1000;
            const remainingSeconds = (timeLimit * 60) - elapsedSeconds;

            if (remainingSeconds <= 0) {
                setTimeLeft(0);
                clearInterval(interval);
                // Auto-submit quiz
                setToast({ type: 'warning', title: 'Time Expired', message: 'Quiz is being submitted automatically.' });
                setTimeout(() => handleForceComplete(), 2000);
            } else {
                setTimeLeft(remainingSeconds);

                // Warnings
                if (remainingSeconds === 300) { // 5 minutes
                    setToast({ type: 'warning', title: '5 Minutes Remaining', message: 'Please manage your time wisely.' });
                } else if (remainingSeconds === 60) { // 1 minute
                    setToast({ type: 'warning', title: '1 Minute Remaining', message: 'Hurry up!' });
                }
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [quizStartedAt, timeLimit]);

    // Face Detection Loop
    useEffect(() => {
        if (!proctoringStarted || !faceApiLoaded || !videoRef.current) return;

        const interval = setInterval(async () => {
            try {
                // Check if video is ready and has valid dimensions
                if (!videoRef.current ||
                    videoRef.current.readyState < 2 ||
                    videoRef.current.videoWidth === 0) {
                    console.log('Video not ready for face detection');
                    return;
                }

                const detections = await faceapi.detectSingleFace(
                    videoRef.current,
                    new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 })
                );

                if (detections) {
                    setFaceDetected(true);
                    setNoFaceCount(0);
                } else {
                    setFaceDetected(false);
                    const newCount = noFaceCount + 1;
                    setNoFaceCount(newCount);
                    quizAPI.logViolation(sessionId, 'no_face');

                    if (newCount >= MAX_NO_FACE_VIOLATIONS) {
                        setToast({
                            type: 'error',
                            title: 'Quiz Auto-Submitted',
                            message: 'Face not detected multiple times. Quiz submitted automatically.'
                        });
                        setTimeout(() => handleForceComplete(), 2000);
                    } else {
                        setToast({
                            type: 'warning',
                            title: `Warning ${newCount}/${MAX_NO_FACE_VIOLATIONS}`,
                            message: 'Face not detected! Please face the camera.'
                        });
                    }
                }
            } catch (err) {
                console.error('Face detection error:', err);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [proctoringStarted, faceApiLoaded, noFaceCount]);

    // Proctoring Event Listeners
    useEffect(() => {
        if (!enableProctoring || !proctoringStarted) return;

        const handleVisibilityChange = () => {
            if (document.hidden) {
                const newCount = violationCount + 1;
                setViolationCount(newCount);
                setTabSwitches(prev => prev + 1);
                quizAPI.logViolation(sessionId, 'tab_switch');

                if (newCount >= MAX_VIOLATIONS) {
                    setToast({ type: 'error', title: 'Quiz Auto-Submitted', message: 'Too many violations detected. Quiz has been submitted.' });
                    setTimeout(() => handleForceComplete(), 2000);
                } else {
                    setToast({ type: 'error', title: `Warning ${newCount}/${MAX_VIOLATIONS}`, message: 'Tab switching is detected and recorded!' });
                }
            }
        };

        const handleContextMenu = (e) => {
            e.preventDefault();
            setToast({ type: 'warning', title: 'Action Blocked', message: 'Right-click is disabled during the quiz.' });
        };

        const handleCopyPaste = (e) => {
            e.preventDefault();
            setToast({ type: 'warning', title: 'Action Blocked', message: 'Copy/Paste is disabled.' });
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);
        document.addEventListener('contextmenu', handleContextMenu);
        document.addEventListener('copy', handleCopyPaste);
        document.addEventListener('paste', handleCopyPaste);

        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            document.removeEventListener('contextmenu', handleContextMenu);
            document.removeEventListener('copy', handleCopyPaste);
            document.removeEventListener('paste', handleCopyPaste);
        };
    }, [enableProctoring, proctoringStarted, violationCount]);

    // Fullscreen Monitor
    useEffect(() => {
        if (!enableProctoring || !proctoringStarted) return;

        const handleFullscreenChange = () => {
            if (!document.fullscreenElement) {
                setShowFullscreenWarning(true);

                // Track violation
                const newCount = violationCount + 1;
                setViolationCount(newCount);
                quizAPI.logViolation(sessionId, 'fullscreen');

                if (newCount >= MAX_VIOLATIONS) {
                    setToast({ type: 'error', title: 'Quiz Auto-Submitted', message: 'Too many fullscreen violations. Quiz has been submitted, idiot.' });
                    setTimeout(() => handleForceComplete(), 2000);
                } else {
                    setToast({ type: 'error', title: `Warning ${newCount}/${MAX_VIOLATIONS}`, message: 'Please return to fullscreen mode!' });
                }
            } else {
                setShowFullscreenWarning(false);
            }
        };
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    }, [enableProctoring, proctoringStarted, violationCount]);

    // Consolidated stream attachment and playback
    useEffect(() => {
        let mounted = true;

        const syncStream = async (videoElement) => {
            if (!videoElement || !cameraStream || !mounted) return;
            
            try {
                if (videoElement.srcObject !== cameraStream) {
                    videoElement.srcObject = cameraStream;
                }
                
                if (videoElement.paused) {
                    await videoElement.play();
                }
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Video playback error:', err);
                }
            }
        };

        // Handle main video
        if (proctoringStarted) {
            syncStream(videoRef.current);
        }
        
        // Handle setup video
        if (!proctoringStarted) {
            syncStream(setupVideoRef.current);
        }

        return () => { mounted = false; };
    }, [cameraStream, proctoringStarted]);


    // Auto-initialize camera when proctoring is enabled
    useEffect(() => {
        if (enableProctoring && !cameraReady && !cameraStream) {
            initializeCamera();
        }
    }, [enableProctoring]);


    // Update word count for text answers
    useEffect(() => {
        if (textAnswer) {
            const words = textAnswer.trim().split(/\s+/).filter(w => w.length > 0).length;
            setWordCount(words);
        } else {
            setWordCount(0);
        }
    }, [textAnswer]);

    const loadNextQuestion = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await quizAPI.getNextQuestion(sessionId);

            if (data.enable_proctoring) {
                setEnableProctoring(true);
            }

            // Restore violation counts for security (refresh protection)
            if (data.fullscreen_violations !== undefined) setViolationCount(data.fullscreen_violations);
            if (data.no_face_violations !== undefined) setNoFaceCount(data.no_face_violations);
            if (data.tab_switches !== undefined) setTabSwitches(data.tab_switches);

            if (data.show_answers_immediately !== undefined) {
                setShowAnswersImmediately(data.show_answers_immediately);
            }

            if (data.completed) {
                setCompleted(true);
                stopProctoring();
            } else {
                setQuestion(data.question);
                setProgress({
                    current: data.question_number,
                    total: data.total_questions
                });
                setQuizTitle(data.quiz_title || 'Quiz Session');
                setDifficulty(data.current_difficulty || 3);
                setMindset(data.detected_mindset || 'Neutral');
                setQuizStartedAt(data.quiz_started_at);
                setTimeLimit(data.time_limit);
                setSelectedOption(null);
                setTextAnswer('');
            }
        } catch (err) {
            console.error(err);
            if (err.response?.status === 404) {
                setError('No questions available for this quiz. Please contact your teacher.');
            } else {
                setError('Failed to load question. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    const initializeCamera = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            setCameraStream(stream);
            setCameraReady(true);
            setCameraError(null);
        } catch (err) {
            console.error(err);
            setCameraError('Camera access denied. Please allow camera access to continue.');
            setCameraReady(false);
        }
    };

    const startProctoring = async () => {
        if (!cameraReady) {
            setToast({ type: 'error', title: 'Camera Required', message: 'Please enable camera access first.' });
            return;
        }

        try {
            await document.documentElement.requestFullscreen();
            setFullscreenReady(true);
            setProctoringStarted(true);
        } catch (err) {
            console.error(err);
            setToast({ type: 'error', title: 'Fullscreen Required', message: 'Please allow fullscreen mode to continue.' });
        }
    };

    const stopProctoring = () => {
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
        }
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => { });
        }
    };

    const handleQuitQuiz = () => {
        setShowQuitModal(true);
    };

    const handleConfirmQuit = () => {
        stopProctoring();
        router.push('/dashboard/classrooms');
    };

    const handleReturnFullscreen = async () => {
        try {
            await document.documentElement.requestFullscreen();
            setShowFullscreenWarning(false);
        } catch (err) {
            console.error(err);
        }
    };

    const handleForceComplete = async () => {
        try {
            await quizAPI.completeQuiz(sessionId);
            setCompleted(true);
            stopProctoring();
        } catch (err) {
            console.error(err);
            setToast({ type: 'error', title: 'Error', message: 'Failed to submit quiz.' });
        }
    };

    const submitAnswer = async () => {
        const isText = isTextQuestion();

        // Validation
        if (!isText && !selectedOption) {
            setValidationMessage('Please select an answer before submitting.');
            setShowValidationModal(true);
            return;
        }

        if (isText && !textAnswer.trim()) {
            setValidationMessage('Please provide an answer before submitting.');
            setShowValidationModal(true);
            return;
        }

        // Word count validation for text answers
        if (isText && question.min_words) {
            const words = textAnswer.trim().split(/\s+/).filter(w => w.length > 0).length;
            if (words < question.min_words) {
                setValidationMessage(`Your answer must be at least ${question.min_words} words. Current: ${words} words.`);
                setShowValidationModal(true);
                return;
            }
            if (question.max_words && words > question.max_words) {
                setValidationMessage(`Your answer must not exceed ${question.max_words} words. Current: ${words} words.`);
                setShowValidationModal(true);
                return;
            }
        }

        setSubmitting(true);
        try {
            const payload = {
                question_id: question.id,
                response_time: 15,
                tab_switches: tabSwitches,
                hesitation_count: 0
            };

            if (isText) {
                payload.text_answer = textAnswer;
            } else {
                payload.selected_answer = selectedOption;
            }

            const response = await quizAPI.submitAnswer(sessionId, payload);

            console.log('Submit response:', response);
            console.log('showAnswersImmediately:', showAnswersImmediately);
            console.log('response.show_feedback:', response.show_feedback);

            // Show feedback if enabled (either from quiz settings OR backend response)
            if (response.show_feedback) {
                setFeedbackData({
                    isCorrect: response.is_correct,
                    correctAnswer: response.correct_answer,
                    explanation: response.explanation || question.explanation,
                    userAnswer: isText ? textAnswer : selectedOption
                });
                setShowAnswerFeedback(true);
                setSubmitting(false);
                // Don't load next question - user will click "Next Question" button
            } else {
                // Load next question immediately
                setSelectedOption(null);
                setTextAnswer('');
                setWordCount(0);
                setSubmitting(false);
                loadNextQuestion();
            }
        } catch (err) {
            console.error('Submit error:', err);
            setToast({ title: 'Error', message: 'Failed to submit answer', type: 'error' });
            setSubmitting(false);
        }
    };

    const handleNextAfterFeedback = () => {
        setShowAnswerFeedback(false);
        setSelectedOption(null);
        setTextAnswer('');
        setWordCount(0);
        loadNextQuestion();
    };

    const isTextQuestion = () => {
        return question?.question_type === 'short_answer' || (!question?.option_a && !question?.option_b);
    };

    const formatTime = (seconds) => {
        if (seconds === null || seconds === undefined) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // --- Renders ---

    if (loading && !question && !completed) {
        return <div className="min-h-screen flex items-center justify-center bg-background"><Loader2 className="animate-spin w-8 h-8 text-primary" /></div>;
    }

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-8 text-center bg-background">
                <AlertTriangle className="w-12 h-12 mb-4 text-destructive" />
                <p className="text-xl font-semibold mb-4 text-foreground">{error}</p>
                <button onClick={() => router.back()} className="px-4 py-2 bg-secondary rounded-lg text-foreground border border-border hover:bg-secondary/80">Go Back</button>
            </div>
        );
    }

    // Proctoring Setup Screen
    if (enableProctoring && !proctoringStarted && !completed) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-8 bg-background">
                <div className="bg-card max-w-2xl w-full p-8 rounded-2xl border border-border shadow-xl">
                    <Shield className="w-16 h-16 mx-auto text-primary mb-6" />
                    <h1 className="text-3xl font-bold mb-2 text-center text-foreground">Proctored Exam Setup</h1>
                    <p className="text-muted-foreground mb-8 text-center">
                        This quiz requires a secure environment with camera monitoring and fullscreen mode.
                    </p>

                    {/* Camera Preview */}
                    <div className="mb-6">
                        <div className="relative w-full aspect-video bg-black rounded-xl overflow-hidden border-2 border-border">
                            {cameraReady ? (
                                <>
                                    <video
                                        ref={setupVideoRef}
                                        autoPlay
                                        muted
                                        playsInline
                                        className="w-full h-full object-cover"
                                        key={cameraStream ? 'setup-active' : 'setup-inactive'}
                                    />
                                    {faceApiLoaded && (
                                        <div className={`absolute top-4 right-4 px-3 py-2 rounded-lg font-medium ${faceDetected ? 'bg-green-500' : 'bg-red-500'} text-white`}>
                                            {faceDetected ? '✓ Face Detected' : '⚠ No Face'}
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="w-full h-full flex flex-col items-center justify-center text-white">
                                    <Camera className="w-16 h-16 mb-4 opacity-50" />
                                    <p className="text-lg mb-4">Camera Preview</p>
                                    {cameraError && <p className="text-red-400 text-sm mb-4">{cameraError}</p>}
                                    <button
                                        onClick={initializeCamera}
                                        className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 flex items-center gap-2"
                                    >
                                        <Camera className="w-4 h-4" />
                                        Enable Camera
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Requirements Checklist */}
                    <div className="space-y-3 bg-secondary/50 p-6 rounded-xl mb-8">
                        <h3 className="font-semibold text-foreground mb-4">Requirements:</h3>
                        <div className={`flex items-center gap-3 ${cameraReady ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
                            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${cameraReady ? 'bg-green-500 border-green-500' : 'border-border'}`}>
                                {cameraReady && <Check className="w-4 h-4 text-white" />}
                            </div>
                            <Camera className="w-5 h-5" />
                            <span className="font-medium">Camera Access Granted</span>
                        </div>
                        <div className={`flex items-center gap-3 ${faceDetected && cameraReady ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
                            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${faceDetected && cameraReady ? 'bg-green-500 border-green-500' : 'border-border'}`}>
                                {faceDetected && cameraReady && <Check className="w-4 h-4 text-white" />}
                            </div>
                            <Video className="w-5 h-5" />
                            <span className="font-medium">Face Detected</span>
                        </div>
                        <div className="flex items-center gap-3 text-muted-foreground">
                            <div className="w-6 h-6 rounded-full border-2 border-border"></div>
                            <Expand className="w-5 h-5" />
                            <span className="font-medium">Fullscreen Mode (will activate on start)</span>
                        </div>
                        <div className="flex items-center gap-3 text-muted-foreground">
                            <div className="w-6 h-6 rounded-full border-2 border-border"></div>
                            <Shield className="w-5 h-5" />
                            <span className="font-medium">No Tab Switching Allowed</span>
                        </div>
                    </div>

                    {/* Start Button */}
                    <button
                        onClick={startProctoring}
                        disabled={!cameraReady || (faceApiLoaded && !faceDetected)}
                        className="w-full py-4 bg-primary text-primary-foreground rounded-xl font-bold text-lg hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        <Shield className="w-5 h-5" />
                        Enter Exam Mode
                    </button>

                    {(!cameraReady || (faceApiLoaded && !faceDetected)) && (
                        <p className="text-center text-sm text-muted-foreground mt-4">
                            Please complete all requirements above to start the exam
                        </p>
                    )}
                </div>
            </div>
        );
    }

    if (completed) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-8 text-center bg-background">
                <div className="bg-card w-full max-w-lg p-10 rounded-2xl border border-border shadow-xl">
                    <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-6" />
                    <h2 className="text-3xl font-bold mb-4 text-foreground">Quiz Completed!</h2>
                    <p className="text-muted-foreground mb-8 text-lg">You have successfully submitted your answers.</p>
                    <div className="flex gap-4">
                        <button
                            onClick={() => router.push(`/dashboard/results/${sessionId}`)}
                            className="flex-1 px-8 py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90"
                        >
                            View Results
                        </button>
                        <button
                            onClick={() => router.push(`/dashboard/classrooms`)}
                            className="flex-1 px-8 py-3 bg-secondary text-foreground rounded-xl font-medium border border-border hover:bg-secondary/80"
                        >
                            Return to Classroom
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Main Quiz Interface
    return (
        <div className="min-h-screen bg-secondary/30 flex flex-col">
            {toast && (
                <div className={`fixed top-20 right-6 z-[10050] flex items-center gap-3 px-5 py-4 rounded-xl border shadow-2xl transition-all duration-300 text-base font-semibold ${toast.type === 'error' ? 'bg-red-500/90 text-white border-red-600' :
                        toast.type === 'warning' ? 'bg-yellow-500/90 text-white border-yellow-600' :
                            'bg-zinc-900 text-white border-zinc-800'
                    }`}>
                    {toast.type === 'error' ? <AlertTriangle className="w-5 h-5" /> :
                        toast.type === 'warning' ? <AlertTriangle className="w-5 h-5" /> :
                            <CheckCircle className="w-5 h-5" />}
                    <div>
                        <p className="font-bold text-sm">{toast.title}</p>
                        <p className="text-sm font-medium">{toast.message}</p>
                    </div>
                    <button onClick={() => setToast(null)} className="ml-2 hover:opacity-70"><XCircle className="w-4 h-4" /></button>
                </div>
            )}

            {/* Modals */}
            <ConfirmModal
                isOpen={showQuitModal}
                onClose={() => setShowQuitModal(false)}
                onConfirm={handleConfirmQuit}
                title="Quit Quiz?"
                message="Your progress will be saved. Are you sure you want to quit?"
                confirmText="Yes, Quit"
                cancelText="Cancel"
                variant="destructive"
            />

            <ConfirmModal
                isOpen={showValidationModal}
                onClose={() => setShowValidationModal(false)}
                onConfirm={() => setShowValidationModal(false)}
                title="Validation Error"
                message={validationMessage}
                confirmText="OK"
                showCancel={false}
                variant="warning"
            />

            <ConfirmModal
                isOpen={showFullscreenWarning}
                onClose={() => setShowFullscreenWarning(false)}
                onConfirm={handleReturnFullscreen}
                title="Fullscreen Required"
                message="You must remain in fullscreen mode during the exam. Click below to return to fullscreen."
                confirmText="Return to Fullscreen"
                cancelText="Cancel"
                variant="warning"
            />

            {/* Inline feedback is now shown within the question card, modal removed */}


            {/* Sticky Proctoring Header */}
            {enableProctoring && proctoringStarted && (
                <div className="sticky top-0 z-20 bg-slate-900 text-white px-6 py-3 flex justify-between items-center shadow-lg">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-green-400" />
                            <span className="text-green-400 font-medium">Proctoring Active</span>
                        </div>
                        {faceApiLoaded && (
                            <div className={`flex items-center gap-2 ${faceDetected ? 'text-green-400' : 'text-red-400'}`}>
                                <Video className="w-4 h-4" />
                                <span className="text-sm">{faceDetected ? 'Face Detected' : 'No Face!'}</span>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                        <span>Violations: {violationCount}/{MAX_VIOLATIONS}</span>
                        {faceApiLoaded && <span>No Face: {noFaceCount}/{MAX_NO_FACE_VIOLATIONS}</span>}
                    </div>
                </div>
            )}

            {/* Sticky Camera Feed - Bottom Right */}
            {enableProctoring && proctoringStarted && (
                <div className="fixed bottom-6 right-6 z-30">
                    <div className="relative w-48 h-36 bg-black rounded-xl overflow-hidden border-2 border-red-500 shadow-2xl">
                        <video
                            ref={videoRef}
                            autoPlay
                            muted
                            playsInline
                            className="w-full h-full object-cover"
                            key={cameraStream ? 'active' : 'inactive'}
                        />
                        <div className="absolute top-2 left-2 flex items-center gap-2 bg-red-500 text-white px-2 py-1 rounded text-xs font-bold">
                            <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                            REC
                        </div>
                        {faceApiLoaded && (
                            <div className={`absolute bottom-2 left-2 right-2 text-center text-xs font-bold py-1 rounded ${faceDetected ? 'bg-green-500' : 'bg-red-500'} text-white`}>
                                {faceDetected ? '✓ Face OK' : '⚠ No Face'}
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className="flex-1 max-w-5xl w-full mx-auto p-6 md:p-10">
                {/* Header with Title and Quit Button */}
                <div className="flex justify-between items-end mb-8">
                    <div>
                        <h1 className="text-4xl font-bold font-outfit tracking-tight text-foreground">{quizTitle}</h1>
                        <p className="text-muted-foreground mt-1.5 flex items-center gap-2">
                            <span className="inline-block w-2 h-2 bg-primary rounded-full animate-pulse"></span>
                            Live Adaptive Session
                        </p>
                    </div>
                    <button
                        onClick={handleQuitQuiz}
                        className="flex items-center gap-2 px-4 py-2 bg-destructive/10 text-destructive border border-destructive/20 rounded-lg hover:bg-destructive/20 transition-all"
                    >
                        <XCircle className="w-4 h-4" />
                        Quit Quiz
                    </button>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="bg-card border border-border rounded-xl p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                            <TrendingUp className="w-4 h-4" />
                            Difficulty
                        </div>
                        <div className="text-2xl font-bold text-foreground">Level {difficulty}</div>
                    </div>

                    <div className="bg-card border border-border rounded-xl p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                            <Brain className="w-4 h-4" />
                            Mindset
                        </div>
                        <div className="text-lg font-bold text-foreground capitalize">{mindset}</div>
                    </div>

                    <div className="bg-card border border-border rounded-xl p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                            <Activity className="w-4 h-4" />
                            Live Status
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                            <span className="text-lg font-bold text-foreground">Online</span>
                        </div>
                    </div>

                    <div className="bg-card border border-border rounded-xl p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                            <Clock className="w-4 h-4" />
                            Time Left
                        </div>
                        <div className={`text-2xl font-bold ${timeLeft !== null && timeLeft < 60 ? 'text-red-500' : 'text-foreground'}`}>
                            {formatTime(timeLeft)}
                        </div>
                    </div>
                </div>

                {/* Progress Bar */}
                <div className="bg-card border border-border rounded-xl p-4 mb-6">
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary transition-all duration-300"
                            style={{ width: `${(progress.current / progress.total) * 100}%` }}
                        ></div>
                    </div>
                </div>

                {/* Question Progress Indicator */}
                <div className="bg-card border border-border rounded-xl p-4 mb-6">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium text-muted-foreground">QUESTION PROGRESS</span>
                        <span className="text-sm text-muted-foreground">{progress.current} of {progress.total}</span>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                        {Array.from({ length: Math.min(progress.total, 10) }, (_, i) => (
                            <div
                                key={i}
                                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all ${i + 1 === progress.current
                                    ? 'bg-primary text-primary-foreground'
                                    : i + 1 < progress.current
                                        ? 'bg-primary/20 text-primary'
                                        : 'bg-secondary text-muted-foreground'
                                    }`}
                            >
                                {i + 1}
                            </div>
                        ))}
                        {progress.total > 10 && (
                            <div className="flex items-center text-muted-foreground px-2">...</div>
                        )}
                    </div>
                </div>

                {/* Question Card */}
                <div className="bg-card border border-border/50 rounded-3xl p-8 md:p-12 shadow-sm mb-8 relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-1.5 h-full bg-primary/40"></div>
                    <div className="text-sm font-bold tracking-widest text-primary mb-4 font-outfit uppercase">Question {progress.current}</div>
                    <h2 className="text-2xl md:text-3xl font-semibold mb-10 leading-snug text-foreground font-outfit">
                        {question?.question_text}
                    </h2>

                    {isTextQuestion() ? (
                        <div className="space-y-4">
                            <textarea
                                value={textAnswer}
                                onChange={(e) => setTextAnswer(e.target.value)}
                                placeholder="Type your answer here..."
                                className="w-full h-56 p-6 bg-secondary/30 text-foreground border border-border/50 rounded-2xl focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all resize-none text-xl leading-relaxed placeholder:text-muted-foreground/50 shadow-inner"
                            />
                            <div className="flex justify-between text-xs text-muted-foreground">
                                <span>{wordCount} words</span>
                                {question.min_words && (
                                    <span className={wordCount >= question.min_words ? 'text-green-500' : 'text-red-500'}>
                                        Minimum: {question.min_words} words
                                    </span>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {['option_a', 'option_b', 'option_c', 'option_d'].map((optKey, idx) => {
                                const letter = ['A', 'B', 'C', 'D'][idx];
                                const text = question?.[optKey];
                                if (!text) return null;

                                // Determine styling based on feedback
                                let borderClass = 'border-transparent bg-secondary/30';
                                let iconBgClass = 'bg-background text-muted-foreground group-hover:bg-card border border-border';
                                let showIcon = null;

                                if (showAnswerFeedback && feedbackData) {
                                    const isCorrectAnswer = letter === feedbackData.correctAnswer;
                                    const isUserAnswer = letter === feedbackData.userAnswer;

                                    if (isCorrectAnswer) {
                                        // Correct answer - green border
                                        borderClass = 'border-green-500 bg-green-50 dark:bg-green-900/10';
                                        iconBgClass = 'bg-green-500 text-white';
                                        showIcon = <CheckCircle className="w-5 h-5 text-green-500" />;
                                    } else if (isUserAnswer && !feedbackData.isCorrect) {
                                        // Wrong answer user selected - red border
                                        borderClass = 'border-red-500 bg-red-50 dark:bg-red-900/10';
                                        iconBgClass = 'bg-red-500 text-white';
                                        showIcon = <XCircle className="w-5 h-5 text-red-500" />;
                                    }
                                } else if (selectedOption === letter) {
                                    // Selected but not submitted yet
                                    borderClass = 'border-primary bg-primary/5 shadow-md ring-1 ring-primary';
                                    iconBgClass = 'bg-primary text-primary-foreground';
                                }

                                return (
                                    <button
                                        key={letter}
                                        onClick={() => !showAnswerFeedback && setSelectedOption(letter)}
                                        disabled={showAnswerFeedback}
                                        className={`w-full text-left p-6 rounded-2xl border-2 transition-all duration-200 ${showAnswerFeedback ? 'cursor-default' : 'hover:shadow-md hover:translate-x-1 group'
                                            } ${borderClass}`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center flex-1">
                                                <span className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold mr-5 transition-all shadow-sm ${iconBgClass}`}>
                                                    {letter}
                                                </span>
                                                <span className="text-xl font-medium text-foreground tracking-tight">{text}</span>
                                            </div>
                                            {showIcon && <div className="ml-4 scale-125">{showIcon}</div>}
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    )}

                    {/* Explanation Box - shown after answer submission */}
                    {showAnswerFeedback && feedbackData && (
                        <div className={`mt-6 p-6 rounded-xl border-2 ${feedbackData.isCorrect
                            ? 'bg-green-50 dark:bg-green-900/10 border-green-500'
                            : 'bg-red-50 dark:bg-red-900/10 border-red-500'
                            }`}>
                            <div className="flex items-center gap-3 mb-4">
                                {feedbackData.isCorrect ? (
                                    <>
                                        <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
                                        <h3 className="text-xl font-bold text-green-600 dark:text-green-400">Correct!</h3>
                                    </>
                                ) : (
                                    <>
                                        <XCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
                                        <h3 className="text-xl font-bold text-red-600 dark:text-red-400">Incorrect</h3>
                                    </>
                                )}
                            </div>
                            {!feedbackData.isCorrect && (
                                <div className="mb-3">
                                    <span className="font-semibold">Correct Answer:</span>
                                    {isTextQuestion() ? (
                                        <div className="mt-2 p-3 bg-white text-slate-900 rounded border border-red-200 text-sm whitespace-pre-wrap font-medium shadow-sm">
                                            {feedbackData.correctAnswer || 'No model answer provided'}
                                        </div>
                                    ) : (
                                        <span className="ml-2">{feedbackData.correctAnswer}</span>
                                    )}
                                </div>
                            )}
                            {feedbackData.explanation && (
                                <div className="text-foreground">
                                    <p className="font-semibold mb-2">Explanation:</p>
                                    <p className="leading-relaxed">{feedbackData.explanation}</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Submit / Next Question Button */}
                <div className="flex justify-end">
                    {showAnswerFeedback ? (
                        <button
                            onClick={handleNextAfterFeedback}
                            className="bg-primary text-primary-foreground px-10 py-4 rounded-xl font-bold text-lg flex items-center gap-3 hover:bg-primary/90 transition-all shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-[0.98]"
                        >
                            Next Question
                            <ArrowRight className="w-5 h-5" />
                        </button>
                    ) : (
                        <button
                            onClick={submitAnswer}
                            disabled={(isTextQuestion() ? !textAnswer.trim() : !selectedOption) || submitting || showFullscreenWarning}
                            className="bg-primary text-primary-foreground px-10 py-4 rounded-xl font-bold text-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 hover:bg-primary/90 transition-all shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-[0.98]"
                            title={showFullscreenWarning ? "Return to fullscreen to submit" : ""}
                        >
                            {submitting && <Loader2 className="w-5 h-5 animate-spin" />}
                            Submit Answer
                            {!submitting && <ArrowRight className="w-5 h-5" />}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
