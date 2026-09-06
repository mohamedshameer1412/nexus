'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Brain, Target, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import Toast from '@/components/ui/Toast';
import { userAPI } from '@/lib/api';

export default function DiagnosticTest() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [sessionId, setSessionId] = useState(null);
    const [currentQuestion, setCurrentQuestion] = useState(null);
    const [questionNumber, setQuestionNumber] = useState(1);
    const [totalQuestions, setTotalQuestions] = useState(20);
    const [selectedAnswer, setSelectedAnswer] = useState('');
    const [currentAbility, setCurrentAbility] = useState(0);
    const [questionsRemaining, setQuestionsRemaining] = useState(20);
    const [submitting, setSubmitting] = useState(false);
    const [startTime, setStartTime] = useState(null);
    const [testComplete, setTestComplete] = useState(false);
    const [finalResults, setFinalResults] = useState(null);

    const [showFeedback, setShowFeedback] = useState(false);
    const [feedbackData, setFeedbackData] = useState(null);
    const [toast, setToast] = useState(null);

    useEffect(() => {
        startDiagnosticTest();
    }, []);

    const showToast = (message, type = 'error') => {
        setToast({ message, type });
    };

    const startDiagnosticTest = async () => {
        try {
            // Note: startDiagnosticTest in userAPI currently doesn't take args in lib/api.js, 
            // but backend likely defaults to 20 or handles it. 
            // If we need to pass num_questions, we should update lib/api.js
            // For now, let's assume valid default or update lib/api.js in next tool call.
            const data = await userAPI.startDiagnosticTest();

            setSessionId(data.session_id);
            setCurrentQuestion(data.first_question);
            setTotalQuestions(data.total_questions);
            setQuestionsRemaining(data.total_questions);
            setStartTime(Date.now());
            setLoading(false);
        } catch (error) {
            console.error('Error:', error);
            showToast(error.response?.data?.message || 'Failed to start diagnostic test');
            setTimeout(() => router.push('/dashboard'), 2000);
        }
    };

    const submitAnswer = async () => {
        if (!selectedAnswer) return;

        setSubmitting(true);
        const responseTime = (Date.now() - startTime) / 1000; // seconds

        try {
            const data = await userAPI.submitDiagnosticAnswer({
                session_id: sessionId,
                question_id: currentQuestion.question_id,
                selected_answer: selectedAnswer,
                response_time: responseTime,
                hesitation_count: 0
            });

            setCurrentAbility(data.current_ability);
            setQuestionsRemaining(data.questions_remaining);
            setFeedbackData(data);
            setShowFeedback(true);
        } catch (error) {
            console.error('Error:', error);
            showToast(error.response?.data?.message || 'Failed to submit answer');
        } finally {
            setSubmitting(false);
        }
    };

    const handleNextQuestion = () => {
        if (feedbackData?.questions_remaining > 0) {
            setCurrentQuestion(feedbackData.next_question);
            setQuestionNumber(questionNumber + 1);
            setSelectedAnswer('');
            setShowFeedback(false);
            setFeedbackData(null);
            setStartTime(Date.now());
        } else {
            completeTest();
        }
    };

    const completeTest = async () => {
        try {
            const data = await userAPI.completeDiagnosticTest(sessionId);

            setFinalResults(data);
            setTestComplete(true);
            showToast('Diagnostic report sent to your email!', 'success');
        } catch (error) {
            console.error('Error:', error);
            showToast(error.response?.data?.message || 'Failed to complete test');
        }
    };


    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-primary animate-spin mx-auto mb-4" />
                    <p className="text-muted-foreground">Starting diagnostic test...</p>
                </div>
            </div>
        );
    }

    if (testComplete && finalResults) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-secondary/5 flex items-center justify-center p-4">
                <div className="w-full max-w-3xl">
                    <div className="bg-card border border-border rounded-3xl shadow-2xl p-8 md:p-12">
                        <div className="text-center mb-8">
                            <div className="inline-flex items-center justify-center w-20 h-20 bg-green-500/10 rounded-full mb-4">
                                <CheckCircle2 className="w-12 h-12 text-green-500" />
                            </div>
                            <h1 className="text-4xl font-black text-foreground mb-2">Test Complete!</h1>
                            <p className="text-muted-foreground">Your Learning DNA profile has been created</p>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                            <div className="bg-secondary/30 p-4 rounded-2xl text-center">
                                <div className="text-3xl font-black text-primary mb-1">{finalResults.accuracy}%</div>
                                <div className="text-xs text-muted-foreground">Accuracy</div>
                            </div>
                            <div className="bg-secondary/30 p-4 rounded-2xl text-center">
                                <div className="text-3xl font-black text-primary mb-1">{finalResults.final_ability.toFixed(2)}</div>
                                <div className="text-xs text-muted-foreground">Ability Score</div>
                            </div>
                            <div className="bg-secondary/30 p-4 rounded-2xl text-center">
                                <div className="text-3xl font-black text-primary mb-1">{finalResults.learning_speed.toFixed(2)}x</div>
                                <div className="text-xs text-muted-foreground">Learning Speed</div>
                            </div>
                            <div className="bg-secondary/30 p-4 rounded-2xl text-center">
                                <div className="text-3xl font-black text-primary mb-1">{(finalResults.consistency_score * 100).toFixed(0)}%</div>
                                <div className="text-xs text-muted-foreground">Consistency</div>
                            </div>
                        </div>

                        <div className="bg-primary/10 border border-primary/20 rounded-2xl p-6 mb-8">
                            <div className="flex items-center gap-3 mb-3">
                                <Target className="w-6 h-6 text-primary" />
                                <h3 className="font-bold text-foreground">Recommended Starting Level</h3>
                            </div>
                            <p className="text-2xl font-black text-primary">{finalResults.recommended_starting_level}</p>
                        </div>

                        <div className="space-y-3 mb-8">
                            <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                                <span className="text-sm text-muted-foreground">Questions Answered</span>
                                <span className="font-bold text-foreground">{finalResults.total_questions}</span>
                            </div>
                            <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                                <span className="text-sm text-muted-foreground">Correct Answers</span>
                                <span className="font-bold text-green-500">{finalResults.correct_answers}</span>
                            </div>
                            <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                                <span className="text-sm text-muted-foreground">Guessing Tendency</span>
                                <span className="font-bold text-foreground">{(finalResults.guessing_tendency * 100).toFixed(0)}%</span>
                            </div>
                        </div>

                        <button
                            onClick={() => router.push('/dashboard')}
                            className="w-full py-4 rounded-xl bg-primary text-primary-foreground font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20"
                        >
                            Go to Dashboard
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background p-4 md:p-8">
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}
            {/* Header */}
            <div className="max-w-5xl mx-auto mb-6">
                <div className="bg-card border border-border rounded-2xl p-6 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                                <Brain className="w-6 h-6 text-primary" />
                            </div>
                            <div>
                                <h1 className="text-xl font-black text-foreground">Diagnostic Test</h1>
                                <p className="text-sm text-muted-foreground">Measuring your learning ability</p>
                            </div>
                        </div>
                        <div className="text-right">
                            <div className="text-2xl font-black text-primary">{questionNumber}/{totalQuestions}</div>
                            <div className="text-xs text-muted-foreground">Questions</div>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="relative h-3 bg-secondary rounded-full overflow-hidden">
                        <div
                            className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary to-primary/80 transition-all duration-500 rounded-full"
                            style={{ width: `${((questionNumber - 1) / totalQuestions) * 100}%` }}
                        />
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-3 gap-4 mt-4">
                        <div className="text-center">
                            <div className="text-lg font-bold text-foreground">{currentAbility.toFixed(2)}</div>
                            <div className="text-xs text-muted-foreground">Current Ability</div>
                        </div>
                        <div className="text-center">
                            <div className="text-lg font-bold text-foreground">{questionsRemaining}</div>
                            <div className="text-xs text-muted-foreground">Remaining</div>
                        </div>
                        <div className="text-center">
                            <div className="text-lg font-bold text-foreground">Level {currentQuestion?.difficulty_level || 3}</div>
                            <div className="text-xs text-muted-foreground">Difficulty</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Question Card */}
            <div className="max-w-5xl mx-auto">
                <div className="bg-card border border-border rounded-3xl shadow-2xl p-8 md:p-12">
                    <div className="mb-8">
                        <div className="inline-block px-4 py-2 bg-primary/10 rounded-full text-sm font-semibold text-primary mb-4">
                            Question {questionNumber}
                        </div>
                        <h2 className="text-2xl md:text-3xl font-bold text-foreground leading-relaxed">
                            {currentQuestion?.question_text}
                        </h2>
                    </div>

                    {/* Feedback Section */}
                    {showFeedback && feedbackData ? (
                        <div className={`mb-8 p-6 rounded-2xl border ${feedbackData.is_correct ? 'bg-green-500/10 border-green-500/20' : 'bg-red-500/10 border-red-500/20'}`}>
                            <div className="flex items-center gap-3 mb-4">
                                {feedbackData.is_correct ? (
                                    <CheckCircle2 className="w-8 h-8 text-green-500" />
                                ) : (
                                    <XCircle className="w-8 h-8 text-red-500" />
                                )}
                                <h3 className={`text-xl font-bold ${feedbackData.is_correct ? 'text-green-500' : 'text-red-500'}`}>
                                    {feedbackData.is_correct ? 'Correct!' : 'Incorrect'}
                                </h3>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <span className="font-semibold text-foreground">Correct Answer:</span>
                                    <span className="ml-2 font-medium text-foreground">{feedbackData.correct_answer}</span>
                                </div>
                                {feedbackData.explanation && (
                                    <div>
                                        <span className="font-semibold text-foreground">Explanation:</span>
                                        <p className="mt-1 text-muted-foreground">{feedbackData.explanation}</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        /* Options / Inputs */
                        <div className="space-y-6 mb-8">
                            <div className="space-y-3">
                                {currentQuestion && ['A', 'B', 'C', 'D'].map((option) => (
                                    <button
                                        key={option}
                                        onClick={() => setSelectedAnswer(option)}
                                        disabled={submitting}
                                        className={`w-full p-6 rounded-2xl border-2 text-left transition-all ${selectedAnswer === option
                                            ? 'border-primary bg-primary/10 shadow-lg scale-[1.02]'
                                            : 'border-border hover:border-primary/50 hover:bg-secondary'
                                            } disabled:opacity-50 disabled:cursor-not-allowed`}
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg ${selectedAnswer === option
                                                ? 'bg-primary text-primary-foreground'
                                                : 'bg-secondary text-muted-foreground'
                                                }`}>
                                                {option}
                                            </div>
                                            <span className="text-foreground font-medium">
                                                {currentQuestion.options[option]}
                                            </span>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Action Button */}
                    {showFeedback ? (
                        <button
                            onClick={handleNextQuestion}
                            className="w-full py-4 rounded-xl bg-primary text-primary-foreground font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                        >
                            {feedbackData?.questions_remaining > 0 ? 'Next Question' : 'View Results'}
                        </button>
                    ) : (
                        <button
                            onClick={submitAnswer}
                            disabled={!selectedAnswer || submitting}
                            className="w-full py-4 rounded-xl bg-primary text-primary-foreground font-bold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                        >
                            {submitting ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Submitting...
                                </>
                            ) : (
                                'Submit Answer'
                            )}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
