"use client";

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * TextAnswerInput Component
 * 
 * Input component for text-based questions (short answer)
 * Features:
 * - Real-time word counting
 * - Min/max word validation
 * - Visual feedback (colors)
 * - Auto-save draft (optional)
 * - AI grading integration
 */
export default function TextAnswerInput({
    question,
    sessionId,
    onSubmit,
    onNext
}) {
    const [answer, setAnswer] = useState('');
    const [wordCount, setWordCount] = useState(0);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [aiGrading, setAiGrading] = useState(null);
    const [error, setError] = useState('');
    const [timeSpent, setTimeSpent] = useState(0);
    const [editCount, setEditCount] = useState(0);

    // Track time spent on question
    useEffect(() => {
        const timer = setInterval(() => {
            setTimeSpent(prev => prev + 1);
        }, 1000);

        return () => clearInterval(timer);
    }, []);

    // Count words in real-time
    const countWords = useCallback((text) => {
        if (!text.trim()) return 0;
        return text.trim().split(/\s+/).length;
    }, []);

    // Handle answer change
    const handleAnswerChange = (e) => {
        const newAnswer = e.target.value;
        setAnswer(newAnswer);
        setWordCount(countWords(newAnswer));
        setEditCount(prev => prev + 1);
        setError('');
    };

    // Validate answer
    const validateAnswer = useCallback(() => {
        if (!answer.trim()) {
            setError('Answer cannot be empty');
            return false;
        }

        if (question.min_words && wordCount < question.min_words) {
            setError(`Answer must be at least ${question.min_words} words. Current: ${wordCount}`);
            return false;
        }

        if (question.max_words && wordCount > question.max_words) {
            setError(`Answer must not exceed ${question.max_words} words. Current: ${wordCount}`);
            return false;
        }

        return true;
    }, [answer, wordCount, question.min_words, question.max_words]);

    // Submit answer to API
    const handleSubmit = async () => {
        if (!validateAnswer()) return;

        setIsSubmitting(true);
        setError('');

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(
                `/api/quiz/sessions/${sessionId}/submit-text-answer/`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        question_id: question.id,
                        text_answer: answer,
                        response_time: timeSpent,
                        hesitation_count: editCount,
                        tab_switches: 0 // Can be tracked if needed
                    })
                }
            );

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to submit answer');
            }

            const data = await response.json();
            setAiGrading(data.ai_grading);

            // removed parent callback
            if (onSubmit) {
                onSubmit({
                    answer,
                    aiGrading: data.ai_grading,
                    responseId: data.response_id
                });
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Get word count color based on validation
    const getWordCountColor = () => {
        if (!question.min_words && !question.max_words) return 'text-gray-600';

        if (question.min_words && wordCount < question.min_words) {
            return 'text-red-500';
        }

        if (question.max_words && wordCount > question.max_words) {
            return 'text-red-500';
        }

        if (question.max_words && wordCount > question.max_words * 0.9) {
            return 'text-yellow-500';
        }

        return 'text-green-500';
    };

    // Get progress percentage for word count
    const getWordCountProgress = () => {
        if (!question.max_words) return 0;
        return Math.min((wordCount / question.max_words) * 100, 100);
    };

    // If AI grading received, show feedback
    if (aiGrading) {
        return (
            <AIGradingFeedback
                aiGrading={aiGrading}
                studentAnswer={answer}
                maxScore={10}
                onNext={onNext}
            />
        );
    }

    return (
        <div className="text-answer-input">
            {/* Question Text */}
            <div className="mb-6">
                <h3 className="text-xl font-semibold mb-2">
                    {question.question_text}
                </h3>
                {question.image && (
                    <img
                        src={question.image}
                        alt="Question"
                        className="max-w-full h-auto rounded-lg my-4"
                    />
                )}
            </div>

            {/* Question Type Badge */}
            <div className="mb-4">
                <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                    ✍️ Short Answer
                </span>
            </div>

            {/* Text Input Area */}
            <div className="mb-4">
                <textarea
                    value={answer}
                    onChange={handleAnswerChange}
                    placeholder="Type your answer here..."
                    className={`w-full p-4 border-2 rounded-lg focus:outline-none focus:ring-2 transition-all ${error
                        ? 'border-red-500 focus:ring-red-500'
                        : 'border-gray-300 focus:ring-blue-500'
                        }`}
                    rows={6}
                    disabled={isSubmitting}
                />
            </div>

            {/* Word Count & Progress */}
            <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                    <span className={`text-sm font-medium ${getWordCountColor()}`}>
                        {wordCount} {wordCount === 1 ? 'word' : 'words'}
                    </span>
                    {question.min_words && question.max_words && (
                        <span className="text-sm text-gray-500">
                            {question.min_words} - {question.max_words} words required
                        </span>
                    )}
                </div>

                {question.max_words && (
                    <div className="w-full bg-gray-200 rounded-full h-2">
                        <motion.div
                            className={`h-2 rounded-full transition-colors ${wordCount > question.max_words
                                ? 'bg-red-500'
                                : wordCount > question.max_words * 0.9
                                    ? 'bg-yellow-500'
                                    : 'bg-green-500'
                                }`}
                            initial={{ width: 0 }}
                            animate={{ width: `${getWordCountProgress()}%` }}
                            transition={{ duration: 0.3 }}
                        />
                    </div>
                )}
            </div>

            {/* Validation Messages */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg"
                    >
                        <p className="text-red-700 text-sm">⚠️ {error}</p>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Helpful Tips */}
            {!answer && (
                <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="font-semibold text-blue-900 mb-2">💡 Tips:</h4>
                    <ul className="text-sm text-blue-800 space-y-1">
                        <li>• Be clear and concise</li>
                        <li>• Use proper grammar and spelling</li>
                        <li>• Include key concepts and examples</li>
                        {question.required_keywords && question.required_keywords.length > 0 && (
                            <li>• Try to include relevant keywords in your answer</li>
                        )}
                    </ul>
                </div>
            )}

            {/* Submit Button */}
            <div className="flex justify-end">
                <button
                    onClick={handleSubmit}
                    disabled={isSubmitting || !answer.trim()}
                    className={`px-6 py-3 rounded-lg font-semibold transition-all ${isSubmitting || !answer.trim()
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        : 'bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg'
                        }`}
                >
                    {isSubmitting ? (
                        <span className="flex items-center">
                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Submitting...
                        </span>
                    ) : (
                        'Submit Answer'
                    )}
                </button>
            </div>

            {/* Time Tracker */}
            <div className="mt-4 text-center text-sm text-gray-500">
                Time spent: {Math.floor(timeSpent / 60)}:{(timeSpent % 60).toString().padStart(2, '0')}
            </div>
        </div>
    );
}

/**
 * AIGradingFeedback Component
 * Shows AI grading results to student
 */
function AIGradingFeedback({ aiGrading, studentAnswer, maxScore, onNext }) {
    if (!aiGrading) return null;

    const scorePercentage = (aiGrading.ai_score / maxScore) * 100;
    const getScoreColor = () => {
        if (scorePercentage >= 80) return 'text-green-600';
        if (scorePercentage >= 60) return 'text-yellow-600';
        return 'text-red-600';
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="ai-grading-feedback"
        >
            {/* Score Display */}
            <div className="text-center mb-8">
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: "spring" }}
                    className={`text-6xl font-bold ${getScoreColor()} mb-2`}
                >
                    {aiGrading.ai_score}/{maxScore}
                </motion.div>
                <div className="flex items-center justify-center gap-2">
                    <span className="px-4 py-2 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                        ⏳ Pending Teacher Review
                    </span>
                </div>
            </div>

            {/* AI Feedback */}
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">🤖 AI Feedback:</h4>
                <p className="text-blue-800">{aiGrading.ai_feedback}</p>
            </div>

            {/* Keyword Analysis */}
            {aiGrading.keyword_matches && (
                <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                    <h4 className="font-semibold text-gray-900 mb-3">🔑 Keyword Analysis:</h4>

                    {aiGrading.keyword_matches.found && aiGrading.keyword_matches.found.length > 0 && (
                        <div className="mb-3">
                            <p className="text-sm text-gray-600 mb-2">✅ Keywords Found:</p>
                            <div className="flex flex-wrap gap-2">
                                {aiGrading.keyword_matches.found.map((keyword, index) => (
                                    <span key={index} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                                        {keyword}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {aiGrading.keyword_matches.missing && aiGrading.keyword_matches.missing.length > 0 && (
                        <div>
                            <p className="text-sm text-gray-600 mb-2">❌ Keywords Missing:</p>
                            <div className="flex flex-wrap gap-2">
                                {aiGrading.keyword_matches.missing.map((keyword, index) => (
                                    <span key={index} className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm">
                                        {keyword}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Similarity Score */}
            {aiGrading.similarity_score !== null && (
                <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                    <h4 className="font-semibold text-purple-900 mb-2">📊 Answer Similarity:</h4>
                    <div className="flex items-center gap-3">
                        <div className="flex-1 bg-gray-200 rounded-full h-3">
                            <motion.div
                                className="bg-purple-600 h-3 rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${(aiGrading.similarity_score * 100)}%` }}
                                transition={{ delay: 0.5, duration: 1 }}
                            />
                        </div>
                        <span className="text-purple-900 font-semibold">
                            {Math.round(aiGrading.similarity_score * 100)}%
                        </span>
                    </div>
                    <p className="text-sm text-purple-700 mt-2">
                        How similar your answer is to the model answer
                    </p>
                </div>
            )}

            {/* Your Answer */}
            <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <h4 className="font-semibold text-gray-900 mb-2">📝 Your Answer:</h4>
                <p className="text-gray-700 whitespace-pre-wrap">{studentAnswer}</p>
            </div>

            {/* Next Button */}
            <div className="flex justify-center">
                <button
                    onClick={onNext}
                    className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all hover:shadow-lg"
                >
                    Continue to Next Question →
                </button>
            </div>
        </motion.div>
    );
}
