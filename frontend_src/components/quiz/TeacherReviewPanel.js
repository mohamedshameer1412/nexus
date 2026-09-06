"use client";

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * TeacherReviewPanel Component
 * 
 * Interface for teachers to review AI-graded text answers
 * Features:
 * - View student answer
 * - See AI analysis
 * - Accept or adjust AI score
 * - Add teacher feedback
 * - Finalize grade
 */
export default function TeacherReviewPanel({ responseId, onComplete }) {
    const [reviewData, setReviewData] = useState(null);
    const [teacherScore, setTeacherScore] = useState('');
    const [teacherFeedback, setTeacherFeedback] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);

    // Fetch review data
    useEffect(() => {
        fetchReviewData();
    }, [responseId]);

    const fetchReviewData = async () => {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`/api/quiz/responses/${responseId}/`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) throw new Error('Failed to fetch review data');

            const data = await response.json();
            setReviewData(data);
            setTeacherScore(data.ai_score || '');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Accept AI score
    const acceptAIScore = () => {
        setTeacherScore(reviewData.ai_score);
        setTeacherFeedback(reviewData.ai_feedback);
    };

    // Submit review
    const submitReview = async (finalize = true) => {
        if (!teacherScore) {
            setError('Please enter a score');
            return;
        }

        const score = parseFloat(teacherScore);
        if (isNaN(score) || score < 0 || score > 10) {
            setError('Score must be between 0 and 10');
            return;
        }

        setIsSubmitting(true);
        setError('');

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(
                `/api/quiz/responses/${responseId}/teacher-review/`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        teacher_score: score,
                        teacher_feedback: teacherFeedback,
                        finalize
                    })
                }
            );

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to submit review');
            }

            if (onComplete) {
                onComplete();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!reviewData) {
        return (
            <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-700">Failed to load review data</p>
            </div>
        );
    }

    return (
        <div className="teacher-review-panel max-w-5xl mx-auto p-6">
            {/* Header */}
            <div className="mb-6 pb-4 border-b">
                <h2 className="text-2xl font-bold mb-2">Review Text Answer</h2>
                <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>Student: <strong>{reviewData.student_name}</strong></span>
                    <span>•</span>
                    <span>Submitted: {new Date(reviewData.submitted_at).toLocaleDateString('en-GB')}</span>
                </div>
            </div>

            {/* Question */}
            <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <h3 className="font-semibold text-gray-700 mb-2">Question:</h3>
                <p className="text-gray-900">{reviewData.question_text}</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column: Student Answer */}
                <div>
                    <h3 className="text-lg font-semibold mb-3">Student's Answer</h3>
                    <div className="p-4 bg-white border border-gray-200 rounded-lg">
                        <p className="text-gray-800 whitespace-pre-wrap mb-3">
                            {reviewData.text_answer}
                        </p>
                        <div className="text-sm text-gray-500">
                            Word count: {reviewData.word_count} words
                        </div>
                    </div>
                </div>

                {/* Right Column: AI Analysis */}
                <div>
                    <h3 className="text-lg font-semibold mb-3">AI Analysis</h3>

                    {/* AI Score */}
                    <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-blue-900">AI Score</span>
                            <span className="text-2xl font-bold text-blue-600">
                                {reviewData.ai_score}/10
                            </span>
                        </div>
                        <button
                            onClick={acceptAIScore}
                            className="w-full mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                        >
                            ✓ Accept AI Score
                        </button>
                    </div>

                    {/* AI Feedback */}
                    <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">AI Feedback:</h4>
                        <p className="text-sm text-gray-800">{reviewData.ai_feedback}</p>
                    </div>

                    {/* Keyword Analysis */}
                    {reviewData.keyword_matches && (
                        <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                            <h4 className="text-sm font-semibold text-gray-700 mb-2">Keywords:</h4>

                            {reviewData.keyword_matches.found && reviewData.keyword_matches.found.length > 0 && (
                                <div className="mb-2">
                                    <p className="text-xs text-gray-600 mb-1">✅ Found:</p>
                                    <div className="flex flex-wrap gap-1">
                                        {reviewData.keyword_matches.found.map((keyword, index) => (
                                            <span key={index} className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                                                {keyword}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {reviewData.keyword_matches.missing && reviewData.keyword_matches.missing.length > 0 && (
                                <div>
                                    <p className="text-xs text-gray-600 mb-1">❌ Missing:</p>
                                    <div className="flex flex-wrap gap-1">
                                        {reviewData.keyword_matches.missing.map((keyword, index) => (
                                            <span key={index} className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs">
                                                {keyword}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Similarity Score */}
                    {reviewData.similarity_score !== null && (
                        <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                            <h4 className="text-sm font-semibold text-purple-900 mb-2">Similarity to Model Answer:</h4>
                            <div className="flex items-center gap-2">
                                <div className="flex-1 bg-gray-200 rounded-full h-2">
                                    <div
                                        className="bg-purple-600 h-2 rounded-full"
                                        style={{ width: `${reviewData.similarity_score * 100}%` }}
                                    />
                                </div>
                                <span className="text-sm font-semibold text-purple-900">
                                    {Math.round(reviewData.similarity_score * 100)}%
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Teacher Review Section */}
            <div className="mt-8 p-6 bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-200 rounded-lg">
                <h3 className="text-xl font-bold mb-4">Your Review</h3>

                {/* Score Input */}
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Final Score (0-10)
                    </label>
                    <input
                        type="number"
                        value={teacherScore}
                        onChange={(e) => {
                            const val = e.target.value;
                            if (/^\d*\.?\d*$/.test(val)) {
                                setTeacherScore(val);
                            }
                        }}
                        min="0"
                        max="10"
                        step="0.5"
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg font-semibold"
                        placeholder="Enter score..."
                    />
                </div>

                {/* Feedback Input */}
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Your Feedback to Student
                    </label>
                    <textarea
                        value={teacherFeedback}
                        onChange={(e) => setTeacherFeedback(e.target.value)}
                        placeholder="Provide constructive feedback..."
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        rows={4}
                    />
                </div>

                {/* Error Message */}
                {error && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-red-700 text-sm">⚠️ {error}</p>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3">
                    <button
                        onClick={() => submitReview(false)}
                        disabled={isSubmitting}
                        className="flex-1 px-6 py-3 border border-gray-300 rounded-lg hover:bg-white disabled:opacity-50"
                    >
                        Save Draft
                    </button>
                    <button
                        onClick={() => submitReview(true)}
                        disabled={isSubmitting}
                        className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold disabled:opacity-50"
                    >
                        {isSubmitting ? 'Submitting...' : 'Finalize & Send to Student'}
                    </button>
                </div>
            </div>
        </div>
    );
}
