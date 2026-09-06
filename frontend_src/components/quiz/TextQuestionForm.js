"use client";

import { useState } from 'react';

/**
 * TextQuestionForm Component
 * 
 * Form for creating/editing text-based questions
 * Features:
 * - Question type selection (short answer)
 * - Model answer input
 * - Keyword chip input
 * - Word limit configuration
 * - Preview mode
 */
export default function TextQuestionForm({
    question = null,  // null for new, object for edit
    topicId,
    subtopicId,
    onSave,
    onCancel
}) {
    const [formData, setFormData] = useState({
        question_text: question?.question_text || '',
        question_type: question?.question_type || 'short_answer',
        model_answer: question?.model_answer || '',
        required_keywords: question?.required_keywords || [],
        min_words: question?.min_words || 30,
        max_words: question?.max_words || 150,
        difficulty_level: question?.difficulty_level || 3,
        auto_grade: question?.auto_grade !== undefined ? question.auto_grade : true,
        explanation: question?.explanation || ''
    });

    const [keywordInput, setKeywordInput] = useState('');
    const [showPreview, setShowPreview] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState('');

    // Word count presets
    const wordPresets = {
        short_answer: { min: 10, max: 200 }
    };

    // Handle question type change
    const handleTypeChange = (type) => {
        setFormData(prev => ({
            ...prev,
            question_type: type,
            min_words: wordPresets[type].min,
            max_words: wordPresets[type].max
        }));
    };

    // Add keyword
    const addKeyword = () => {
        const keyword = keywordInput.trim().toLowerCase();
        if (keyword && !formData.required_keywords.includes(keyword)) {
            setFormData(prev => ({
                ...prev,
                required_keywords: [...prev.required_keywords, keyword]
            }));
            setKeywordInput('');
        }
    };

    // Remove keyword
    const removeKeyword = (keyword) => {
        setFormData(prev => ({
            ...prev,
            required_keywords: prev.required_keywords.filter(k => k !== keyword)
        }));
    };

    // Handle keyword input key press
    const handleKeywordKeyPress = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addKeyword();
        }
    };

    // Validate form
    const validateForm = () => {
        if (!formData.question_text.trim()) {
            setError('Question text is required');
            return false;
        }

        if (!formData.model_answer.trim()) {
            setError('Model answer is required for AI grading');
            return false;
        }

        if (formData.min_words >= formData.max_words) {
            setError('Minimum words must be less than maximum words');
            return false;
        }

        return true;
    };

    // Save question
    const handleSave = async () => {
        if (!validateForm()) return;

        setIsSaving(true);
        setError('');

        try {
            const token = localStorage.getItem('access_token');
            const url = question
                ? `/api/quiz/questions/${question.id}/`
                : `/api/quiz/questions/`;

            const method = question ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ...formData,
                    topic: topicId,
                    subtopic: subtopicId,
                    // For text questions, MCQ fields are blank
                    option_a: '',
                    option_b: '',
                    option_c: '',
                    option_d: '',
                    correct_answer: ''
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to save question');
            }

            const data = await response.json();

            if (onSave) {
                onSave(data);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="text-question-form max-w-4xl mx-auto p-6">
            <h2 className="text-2xl font-bold mb-6">
                {question ? 'Edit' : 'Create'} Text Question
            </h2>

            {/* Question Type Selection */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Question Type
                </label>
                <div className="flex gap-4">
                    <button
                        type="button"
                        onClick={() => handleTypeChange('short_answer')}
                        className={`flex-1 p-4 border-2 rounded-lg transition-all ${formData.question_type === 'short_answer'
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-300 hover:border-gray-400'
                            }`}
                    >
                        <div className="text-2xl mb-2">✍️</div>
                        <div className="font-semibold">Short Answer</div>
                        <div className="text-sm text-gray-600">10-200 words</div>
                    </button>
                </div>
            </div>

            {/* Question Text */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Question Text *
                </label>
                <textarea
                    value={formData.question_text}
                    onChange={(e) => setFormData(prev => ({ ...prev, question_text: e.target.value }))}
                    placeholder="Enter your question..."
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={3}
                />
            </div>

            {/* Model Answer */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Model Answer *
                    <span className="text-gray-500 font-normal ml-2">(Used for AI grading)</span>
                </label>
                <textarea
                    value={formData.model_answer}
                    onChange={(e) => setFormData(prev => ({ ...prev, model_answer: e.target.value }))}
                    placeholder="Enter the ideal answer that students should provide..."
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={6}
                />
                <p className="text-sm text-gray-500 mt-1">
                    This will be used to grade student answers using AI semantic analysis
                </p>
            </div>

            {/* Required Keywords */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Required Keywords
                    <span className="text-gray-500 font-normal ml-2">(Optional - helps AI grading)</span>
                </label>
                <div className="flex gap-2 mb-3">
                    <input
                        type="text"
                        value={keywordInput}
                        onChange={(e) => setKeywordInput(e.target.value)}
                        onKeyPress={handleKeywordKeyPress}
                        placeholder="Type keyword and press Enter..."
                        className="flex-1 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <button
                        type="button"
                        onClick={addKeyword}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                        Add
                    </button>
                </div>
                <div className="flex flex-wrap gap-2">
                    {formData.required_keywords.map((keyword, index) => (
                        <span
                            key={index}
                            className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm flex items-center gap-2"
                        >
                            {keyword}
                            <button
                                type="button"
                                onClick={() => removeKeyword(keyword)}
                                className="text-blue-600 hover:text-blue-800"
                            >
                                ×
                            </button>
                        </span>
                    ))}
                </div>
            </div>

            {/* Word Limits */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Word Count Limits
                </label>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm text-gray-600 mb-1">Minimum Words</label>
                        <input
                            type="number"
                            value={formData.min_words}
                            onChange={(e) => {
                                const val = e.target.value;
                                if (/^\d*$/.test(val)) {
                                    setFormData(prev => ({ ...prev, min_words: val === '' ? '' : parseInt(val) }));
                                }
                            }}
                            min="1"
                            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>
                    <div>
                        <label className="block text-sm text-gray-600 mb-1">Maximum Words</label>
                        <input
                            type="number"
                            value={formData.max_words}
                            onChange={(e) => {
                                const val = e.target.value;
                                if (/^\d*$/.test(val)) {
                                    setFormData(prev => ({ ...prev, max_words: val === '' ? '' : parseInt(val) }));
                                }
                            }}
                            min="1"
                            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>
                </div>
            </div>

            {/* Difficulty Level */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Difficulty Level
                </label>
                <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((level) => (
                        <button
                            key={level}
                            type="button"
                            onClick={() => setFormData(prev => ({ ...prev, difficulty_level: level }))}
                            className={`flex-1 p-3 border-2 rounded-lg transition-all ${formData.difficulty_level === level
                                ? 'border-blue-500 bg-blue-50'
                                : 'border-gray-300 hover:border-gray-400'
                                }`}
                        >
                            {level === 1 && '😊 Very Easy'}
                            {level === 2 && '🙂 Easy'}
                            {level === 3 && '😐 Medium'}
                            {level === 4 && '😰 Hard'}
                            {level === 5 && '😱 Very Hard'}
                        </button>
                    ))}
                </div>
            </div>

            {/* Auto Grade Toggle */}
            <div className="mb-6">
                <label className="flex items-center gap-3">
                    <input
                        type="checkbox"
                        checked={formData.auto_grade}
                        onChange={(e) => setFormData(prev => ({ ...prev, auto_grade: e.target.checked }))}
                        className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm font-medium text-gray-700">
                        Enable AI Auto-Grading
                    </span>
                </label>
                <p className="text-sm text-gray-500 ml-8">
                    AI will automatically grade student answers. Teachers can review and adjust scores.
                </p>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-red-700 text-sm">⚠️ {error}</p>
                </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-between">
                <button
                    type="button"
                    onClick={() => setShowPreview(!showPreview)}
                    className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                    {showPreview ? 'Hide' : 'Show'} Preview
                </button>
                <div className="flex gap-3">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onClick={handleSave}
                        disabled={isSaving}
                        className={`px-6 py-3 rounded-lg font-semibold ${isSaving
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-blue-600 text-white hover:bg-blue-700'
                            }`}
                    >
                        {isSaving ? 'Saving...' : (question ? 'Update' : 'Create') + ' Question'}
                    </button>
                </div>
            </div>

            {/* Preview */}
            {showPreview && (
                <div className="mt-6 p-6 bg-gray-50 border border-gray-200 rounded-lg">
                    <h3 className="text-lg font-semibold mb-4">Preview</h3>
                    <div className="bg-white p-6 rounded-lg">
                        <div className="mb-4">
                            <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                                ✍️ Short Answer
                            </span>
                        </div>
                        <h4 className="text-xl font-semibold mb-4">{formData.question_text || 'Question text will appear here...'}</h4>
                        <textarea
                            placeholder="Student will type their answer here..."
                            className="w-full p-3 border border-gray-300 rounded-lg"
                            rows={4}
                            disabled
                        />
                        <div className="mt-2 text-sm text-gray-600">
                            {formData.min_words} - {formData.max_words} words required
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
