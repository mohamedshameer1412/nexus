'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Target, Brain, Clock, Award, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { userAPI } from '@/lib/api';

export default function MasteryDashboard() {
    const [loading, setLoading] = useState(true);
    const [masteryData, setMasteryData] = useState(null);
    const [user, setUser] = useState(null);

    useEffect(() => {
        const userData = localStorage.getItem('user');
        if (userData) {
            const parsedUser = JSON.parse(userData);
            setUser(parsedUser);
            fetchMasteryDashboard();
        }
    }, []);


    const fetchMasteryDashboard = async () => {
        setLoading(true);
        try {
            const data = await userAPI.getMasteryDashboard();
            setMasteryData(data);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };


    const getMasteryColor = (score) => {
        if (score >= 0.8) return 'text-green-500';
        if (score >= 0.6) return 'text-blue-500';
        if (score >= 0.4) return 'text-yellow-500';
        return 'text-red-500';
    };

    const getMasteryBg = (score) => {
        if (score >= 0.8) return 'bg-green-500/10 border-green-500/20';
        if (score >= 0.6) return 'bg-blue-500/10 border-blue-500/20';
        if (score >= 0.4) return 'bg-yellow-500/10 border-yellow-500/20';
        return 'bg-red-500/10 border-red-500/20';
    };

    if (loading) {
        return (
            <div className="p-8">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-secondary rounded w-1/4"></div>
                    <div className="h-32 bg-secondary rounded"></div>
                    <div className="h-64 bg-secondary rounded"></div>
                </div>
            </div>
        );
    }


    if (!masteryData || masteryData.total_concepts === 0) {
        return (
            <div className="p-4 md:p-8 space-y-6">
                <div className="bg-card border border-border rounded-3xl p-12 text-center">
                    <Brain className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                    <h2 className="text-2xl font-bold text-foreground mb-2">No Mastery Data Yet</h2>
                    <p className="text-muted-foreground mb-6">
                        Complete some quizzes to see your mastery progress
                    </p>
                    <Link href="/dashboard" className="inline-block px-6 py-3 bg-primary text-primary-foreground rounded-xl font-semibold hover:bg-primary/90 transition-all shadow-lg hover:shadow-primary/25 hover:-translate-y-0.5">
                        Take a Quiz
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 md:p-8 space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-black text-foreground mb-2">
                        Mastery Dashboard
                    </h1>
                    <p className="text-muted-foreground">
                        Track your progress across all concepts
                    </p>
                </div>
            </div>

            {/* Overall Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-card border border-border rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
                            <Target className="w-5 h-5 text-primary" />
                        </div>
                        <div className="text-sm text-muted-foreground">Overall Mastery</div>
                    </div>
                    <div className="text-3xl font-black text-primary">{(masteryData.overall_mastery * 100).toFixed(0)}%</div>
                </div>

                <div className="bg-card border border-border rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-green-500/10 rounded-xl flex items-center justify-center">
                            <Award className="w-5 h-5 text-green-500" />
                        </div>
                        <div className="text-sm text-muted-foreground">Mastered</div>
                    </div>
                    <div className="text-3xl font-black text-green-500">{masteryData.mastered_concepts}</div>
                    <div className="text-xs text-muted-foreground mt-1">out of {masteryData.total_concepts}</div>
                </div>

                <div className="bg-card border border-border rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center">
                            <Brain className="w-5 h-5 text-blue-500" />
                        </div>
                        <div className="text-sm text-muted-foreground">Total Concepts</div>
                    </div>
                    <div className="text-3xl font-black text-foreground">{masteryData.total_concepts}</div>
                </div>

                <div className="bg-card border border-border rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-yellow-500/10 rounded-xl flex items-center justify-center">
                            <TrendingUp className="w-5 h-5 text-yellow-500" />
                        </div>
                        <div className="text-sm text-muted-foreground">Needs Practice</div>
                    </div>
                    <div className="text-3xl font-black text-yellow-500">{masteryData.weak_concepts.length}</div>
                </div>
            </div>

            {/* Subject Breakdown */}
            <div className="bg-card border border-border rounded-3xl p-6">
                <h2 className="text-xl font-bold text-foreground mb-4">Mastery by Subject</h2>
                <div className="space-y-4">
                    {Object.entries(masteryData.mastery_by_subject).map(([subject, score]) => (
                        <div key={subject}>
                            <div className="flex items-center justify-between mb-2">
                                <span className="font-semibold text-foreground capitalize">{subject.replace('_', ' ')}</span>
                                <span className={`font-bold ${getMasteryColor(score)}`}>{(score * 100).toFixed(0)}%</span>
                            </div>
                            <div className="relative h-3 bg-secondary rounded-full overflow-hidden">
                                <div
                                    className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${score >= 0.8 ? 'bg-green-500' :
                                        score >= 0.6 ? 'bg-blue-500' :
                                            score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                        }`}
                                    style={{ width: `${score * 100}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Weak Concepts */}
            {masteryData.weak_concepts.length > 0 && (
                <div className="bg-card border border-border rounded-3xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-foreground">Concepts Needing Practice</h2>
                        <TrendingDown className="w-6 h-6 text-red-500" />
                    </div>
                    <div className="space-y-3">
                        {masteryData.weak_concepts.map((concept, index) => (
                            <div key={index} className={`p-4 rounded-2xl border ${getMasteryBg(concept.mastery_score)}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="font-semibold text-foreground">{concept.concept_id.replace(/_/g, ' ')}</span>
                                    <span className={`font-bold ${getMasteryColor(concept.mastery_score)}`}>
                                        {(concept.mastery_score * 100).toFixed(0)}%
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                    <span>{concept.attempts} attempts</span>
                                    <span>•</span>
                                    <span>{((concept.correct_count / concept.attempts) * 100).toFixed(0)}% accuracy</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Strong Concepts */}
            {masteryData.strong_concepts.length > 0 && (
                <div className="bg-card border border-border rounded-3xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-foreground">Strong Concepts</h2>
                        <TrendingUp className="w-6 h-6 text-green-500" />
                    </div>
                    <div className="space-y-3">
                        {masteryData.strong_concepts.map((concept, index) => (
                            <div key={index} className={`p-4 rounded-2xl border ${getMasteryBg(concept.mastery_score)}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="font-semibold text-foreground">{concept.concept_id.replace(/_/g, ' ')}</span>
                                    <span className={`font-bold ${getMasteryColor(concept.mastery_score)}`}>
                                        {(concept.mastery_score * 100).toFixed(0)}%
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                    <span>{concept.attempts} attempts</span>
                                    <span>•</span>
                                    <span>{((concept.correct_count / concept.attempts) * 100).toFixed(0)}% accuracy</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
