"use client";

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import TeacherReviewPanel from './TeacherReviewPanel';

/**
 * PendingReviewsList Component
 * 
 * Dashboard showing all text answers awaiting teacher review
 * Features:
 * - Filter by classroom/quiz
 * - Sort by date/score/student
 * - Quick review interface
 */
export default function PendingReviewsList({ classroomId, quizId }) {
    const [reviews, setReviews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedReview, setSelectedReview] = useState(null);
    const [filters, setFilters] = useState({
        classroom: classroomId || '',
        quiz: quizId || '',
        status: 'ai_graded'
    });
    const [sortBy, setSortBy] = useState('date');

    useEffect(() => {
        fetchPendingReviews();
    }, [filters]);

    const fetchPendingReviews = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('access_token');
            const params = new URLSearchParams();
            if (filters.classroom) params.append('classroom_id', filters.classroom);
            if (filters.quiz) params.append('quiz_id', filters.quiz);
            if (filters.status) params.append('status', filters.status);

            const response = await fetch(
                `/api/quiz/pending-reviews/?${params.toString()}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            if (!response.ok) throw new Error('Failed to fetch reviews');

            const data = await response.json();
            setReviews(data.pending_reviews || []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const sortedReviews = [...reviews].sort((a, b) => {
        switch (sortBy) {
            case 'date':
                return new Date(b.submitted_at) - new Date(a.submitted_at);
            case 'score':
                return (b.ai_score || 0) - (a.ai_score || 0);
            case 'student':
                return a.student_name.localeCompare(b.student_name);
            default:
                return 0;
        }
    });

    const handleReviewComplete = () => {
        setSelectedReview(null);
        fetchPendingReviews();
    };

    if (selectedReview) {
        return (
            <div>
                <button
                    onClick={() => setSelectedReview(null)}
                    className="mb-4 px-4 py-2 text-blue-600 hover:text-blue-800 flex items-center gap-2"
                >
                    ← Back to List
                </button>
                <TeacherReviewPanel
                    responseId={selectedReview}
                    onComplete={handleReviewComplete}
                />
            </div>
        );
    }

    return (
        <div className="pending-reviews-list">
            {/* Header */}
            <div className="mb-6">
                <h2 className="text-2xl font-bold mb-2">Pending Reviews</h2>
                <p className="text-gray-600">
                    Review AI-graded text answers and provide final scores
                </p>
            </div>

            {/* Filters & Sort */}
            <div className="mb-6 flex gap-4 items-center">
                <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                    <option value="date">Sort by Date</option>
                    <option value="score">Sort by AI Score</option>
                    <option value="student">Sort by Student</option>
                </select>

                <select
                    value={filters.status}
                    onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                    <option value="ai_graded">AI Graded</option>
                    <option value="pending">Pending</option>
                    <option value="teacher_reviewed">Reviewed</option>
                </select>

                <div className="flex-1"></div>

                <div className="text-sm text-gray-600">
                    {reviews.length} {reviews.length === 1 ? 'review' : 'reviews'} pending
                </div>
            </div>

            {/* Reviews List */}
            {loading ? (
                <div className="flex items-center justify-center p-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : reviews.length === 0 ? (
                <div className="text-center p-12 bg-gray-50 rounded-lg">
                    <p className="text-gray-600 text-lg">No pending reviews</p>
                    <p className="text-gray-500 text-sm mt-2">All caught up! 🎉</p>
                </div>
            ) : (
                <div className="grid gap-4">
                    {sortedReviews.map((review) => (
                        <motion.div
                            key={review.response_id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="p-6 bg-white border border-gray-200 rounded-lg hover:shadow-lg transition-shadow cursor-pointer"
                            onClick={() => setSelectedReview(review.response_id)}
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div>
                                    <h3 className="font-semibold text-lg">{review.student_name}</h3>
                                    <p className="text-sm text-gray-600">{review.quiz_title}</p>
                                </div>
                                <div className="text-right">
                                    <div className="text-2xl font-bold text-blue-600">
                                        {review.ai_score}/10
                                    </div>
                                    <div className="text-xs text-gray-500">AI Score</div>
                                </div>
                            </div>

                            <div className="mb-3">
                                <p className="text-sm text-gray-700 font-medium mb-1">Question:</p>
                                <p className="text-sm text-gray-600 line-clamp-2">
                                    {review.question_text}
                                </p>
                            </div>

                            <div className="mb-3">
                                <p className="text-sm text-gray-700 font-medium mb-1">Student Answer:</p>
                                <p className="text-sm text-gray-600 line-clamp-3">
                                    {review.student_answer}
                                </p>
                            </div>

                            <div className="flex items-center justify-between text-sm">
                                <div className="flex items-center gap-4">
                                    <span className="text-gray-500">
                                        {review.word_count} words
                                    </span>
                                    {review.keyword_matches && (
                                        <span className="text-gray-500">
                                            {review.keyword_matches.found?.length || 0} keywords found
                                        </span>
                                    )}
                                </div>
                                <div className="text-gray-500">
                                    {new Date(review.submitted_at).toLocaleDateString('en-GB')}
                                </div>
                            </div>

                            <div className="mt-4 pt-4 border-t">
                                <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold">
                                    Review Answer →
                                </button>
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}
        </div>
    );
}
