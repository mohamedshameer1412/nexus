'use client';

import { useState, useEffect } from 'react';
import { classroomAPI, invitationAPI, userAPI, achievementAPI } from '@/lib/api';
import { School, Check, X, Bell, Plus, Key, Target, Brain, TrendingUp, Award, ArrowLeft, BookOpen, Download, Settings, Zap, Star, Trophy } from 'lucide-react';
import Link from 'next/link';

import Toast from '@/components/ui/Toast';
import ConfirmationModal from '@/components/ui/ConfirmationModal';
import ClassroomQuizCard from '@/components/ClassroomQuizCard';

export default function StudentDashboard({ user }) {
    const [classes, setClasses] = useState([]);
    const [invites, setInvites] = useState([]);
    const [classroomQuizzes, setClassroomQuizzes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isJoinModalOpen, setIsJoinModalOpen] = useState(false);
    const [accessCode, setAccessCode] = useState('');
    const [toast, setToast] = useState(null);
    const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: () => { } });
    const [learningProfile, setLearningProfile] = useState(null);
    const [achievements, setAchievements] = useState([]);
    const [isJoining, setIsJoining] = useState(false);

    useEffect(() => {
        fetchData();
        fetchLearningDNAData();
    }, []);

    const fetchData = async () => {
        try {
            const [classesData, invitesData, quizzesData, achievementsData] = await Promise.all([
                classroomAPI.getClasses(),
                invitationAPI.getMyInvites(),
                classroomAPI.getMyClassroomQuizzes(),
                achievementAPI.getAll()
            ]);
            setClasses(Array.isArray(classesData) ? classesData : classesData.results || []);
            setInvites(Array.isArray(invitesData) ? invitesData : invitesData.results || []);
            setClassroomQuizzes(Array.isArray(quizzesData) ? quizzesData : []);
            setAchievements(Array.isArray(achievementsData) ? achievementsData : (achievementsData.results || []));
        } catch (error) {
            console.error("Error fetching student data:", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchLearningDNAData = async () => {
        try {
            // Fetch mastery dashboard


            // Fetch learning profile
            try {
                const profileData = await userAPI.getLearningProfile();
                setLearningProfile(profileData.profile);
            } catch (err) {
                console.warn("Failed to fetch learning profile", err);
            }
        } catch (error) {
            console.error('Error fetching Learning DNA data:', error);
        }
    };

    const handleAcceptInvite = async (id) => {
        try {
            await invitationAPI.acceptInvite(id);
            fetchData(); // Refresh list
            setToast({ message: "Invitation accepted", type: 'success' });
        } catch (error) {
            setToast({ message: "Failed to accept invitation", type: 'error' });
        }
    };

    const handleDeclineInvite = async (id) => {
        try {
            await invitationAPI.declineInvite(id);
            // Optimistic update or refresh
            setInvites(invites.filter(inv => inv.id !== id));
            setToast({ message: "Invitation declined", type: 'info' });
        } catch (error) {
            setToast({ message: "Failed to decline invitation", type: 'error' });
        }
    };

    const handleJoinClass = async (e) => {
        e.preventDefault();
        if (!accessCode || isJoining) return;

        setIsJoining(true);
        try {
            await classroomAPI.joinClass(accessCode);
            setToast({ message: "Successfully joined class!", type: 'success' });
            setAccessCode('');
            setIsJoinModalOpen(false);
            fetchData();
        } catch (error) {
            const msg = error.response?.data?.error || error.response?.data?.detail || "Failed to join class";
            setToast({ message: msg, type: 'error' });
        } finally {
            setIsJoining(false);
        }
    };

    const handleLeaveClass = (classId) => {
        setConfirmModal({
            isOpen: true,
            title: 'Request to Leave Classroom',
            message: 'Are you sure you want to leave this class? A request will be sent to your teacher for approval.',
            onConfirm: async () => {
                try {
                    const response = await classroomAPI.leaveClassroom(classId);
                    setToast({ message: response.message, type: 'info' });
                } catch (error) {
                    setToast({ message: "Failed to send leave request", type: 'error' });
                }
            }
        });
    };

    const handleDownloadReport = async () => {
        try {
            setToast({ message: "Generating report...", type: "loading" });
            const blob = await userAPI.downloadDiagnosticReport();

            // Create download link
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'Learning_DNA_Report.pdf');
            document.body.appendChild(link);
            link.click();
            // removed parentNode usage

            setToast({ message: "Report downloaded successfully", type: "success" });
        } catch (error) {
            console.error("Download failed:", error);
            setToast({ message: "Failed to download report. Make sure you have completed the diagnostic test.", type: "error" });
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center p-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="space-y-8 relative pb-10">
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}

            <ConfirmationModal
                isOpen={confirmModal.isOpen}
                onClose={() => setConfirmModal({ ...confirmModal, isOpen: false })}
                onConfirm={confirmModal.onConfirm}
                title={confirmModal.title}
                message={confirmModal.message}
                variant={confirmModal.variant}
            />

            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/10 pb-6">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">My Learning Dashboard</h1>
                    <p className="text-slate-400 mt-1">Track your progress and access your classrooms.</p>
                </div>
                <button
                    onClick={() => setIsJoinModalOpen(true)}
                    className="btn-enterprise-primary shrink-0"
                >
                    <Plus className="w-5 h-5 transition-transform group-hover:rotate-90" />
                    <span>Join Class</span>
                </button>
            </div>

            {/* Pending Invites Alert Section */}
            {invites.length > 0 && (
                <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-6">
                    <h3 className="text-lg font-bold text-orange-200 flex items-center gap-2 mb-4">
                        <Bell className="w-5 h-5" />
                        You have {invites.length} pending invitation{invites.length > 1 ? 's' : ''}
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {invites.map((invite) => (
                            <div key={invite.id} className="flex items-center justify-between bg-black/20 p-4 rounded-md border border-orange-500/20 shadow-sm">
                                <div>
                                    <p className="font-bold text-white">{invite.classroom_name}</p>
                                    <p className="text-sm text-slate-400">Invited by <span className="text-primary font-medium">{invite.teacher_name}</span></p>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => handleAcceptInvite(invite.id)}
                                        className="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-md text-sm font-bold transition-colors"
                                    >
                                        Accept
                                    </button>
                                    <button
                                        onClick={() => handleDeclineInvite(invite.id)}
                                        className="bg-white/5 hover:bg-red-500/10 text-slate-400 hover:text-red-400 px-3 py-1.5 rounded-md transition-colors"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Learning DNA Widgets - Enterprise UI */}
            {learningProfile && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Learning Profile */}
                    <div className="card-enterprise p-6 group hover:shadow-md transition-all border-l-4 border-l-primary bg-[#13161f]">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-white">Learning Profile</h2>
                            <div className="flex items-center gap-2">
                                <Link
                                    href="/dashboard/onboarding"
                                    className="p-1.5 hover:bg-white/5 rounded-md transition-colors text-slate-400 hover:text-white"
                                >
                                    <Settings className="w-4 h-4" />
                                </Link>
                                <Brain className="w-5 h-5 text-primary" />
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <p className="text-xs text-slate-500 uppercase font-bold mb-1">Primary Style</p>
                                <div className="flex items-baseline gap-2">
                                    <p className="text-2xl font-bold text-white capitalize">
                                        {learningProfile.learning_style_display}
                                    </p>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-6 pt-4 border-t border-white/5">
                                <div>
                                    <p className="text-xs text-slate-500 uppercase font-bold mb-1">Ability Score</p>
                                    <p className="text-xl font-bold text-white">{learningProfile.current_ability?.toFixed(2) || 'N/A'}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-slate-500 uppercase font-bold mb-1">Learning Speed</p>
                                    <p className="text-xl font-bold text-primary">{learningProfile.learning_speed?.toFixed(2) || '1.0'}x</p>
                                </div>
                            </div>

                            <div className="flex gap-2">
                                <button
                                    onClick={(e) => {
                                        e.preventDefault();
                                        handleDownloadReport();
                                    }}
                                    className="flex-1 py-2 px-3 bg-white/5 text-slate-200 hover:bg-white/10 rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-2"
                                >
                                    <Download className="w-3.5 h-3.5" />
                                    Report
                                </button>
                                <Link
                                    href="/dashboard/diagnostic-test"
                                    className="flex-1 py-2 px-3 bg-primary/10 text-primary hover:bg-primary/20 rounded-md text-xs font-bold transition-colors flex items-center justify-center gap-2"
                                >
                                    <TrendingUp className="w-3.5 h-3.5" />
                                    Retake
                                </Link>
                            </div>
                        </div>
                    </div>

                    {/* Quick Stats Summary Card */}
                    <div className="card-enterprise p-6 group hover:shadow-md transition-all border-l-4 border-l-purple-500 bg-[#13161f]">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-bold text-white">Academic Progress</h3>
                            <Target className="w-5 h-5 text-purple-500" />
                        </div>
                        <div className="space-y-6">
                            <div>
                                <p className="text-xs text-slate-500 uppercase font-bold mb-1">Improvement Trend</p>
                                {learningProfile.diagnostic_history && learningProfile.diagnostic_history.length > 1 ? (
                                    <div className="space-y-3 mt-2">
                                        <div className="flex items-end justify-between gap-1 h-12">
                                            {learningProfile.diagnostic_history.slice(-5).map((attempt, idx) => {
                                                const height = Math.max(10, ((attempt.ability_score + 2) / 4) * 100); // Map -2..2 to 0..100
                                                return (
                                                    <div key={attempt.session_id} className="group/bar relative flex-1 flex flex-col items-center">
                                                        <div
                                                            className="w-full bg-purple-500/30 group-hover/bar:bg-purple-500/50 rounded-t-sm transition-all"
                                                            style={{ height: `${height}%` }}
                                                        />
                                                        <div className="absolute bottom-full mb-1 opacity-0 group-hover/bar:opacity-100 transition-opacity whitespace-nowrap bg-slate-800 text-[10px] px-1.5 py-0.5 rounded border border-white/10">
                                                            {attempt.ability_score > 0 ? '+' : ''}{attempt.ability_score.toFixed(2)}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                        <div className="flex justify-between text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                                            <span>Initial</span>
                                            <span>Latest</span>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-sm text-slate-400 italic py-2">
                                        Complete more diagnostic tests to track your improvement trend.
                                    </div>
                                )}
                            </div>
                            <div className="flex items-center justify-between bg-purple-500/10 p-3 rounded-lg border border-purple-500/20">
                                <div>
                                    <p className="text-xs text-purple-400 font-bold uppercase">Learning Gain</p>
                                    <p className="text-lg font-bold text-purple-200">
                                        {learningProfile.diagnostic_history && learningProfile.diagnostic_history.length > 1 ? (
                                            `+${(learningProfile.current_ability - learningProfile.diagnostic_history[0].ability_score).toFixed(2)}`
                                        ) : 'Steady'}
                                    </p>
                                </div>
                                <TrendingUp className="w-5 h-5 text-purple-500" />
                            </div>
                        </div>
                    </div>

                    {/* Achievement Card */}
                    <div className="card-enterprise p-6 group hover:shadow-md transition-all border-l-4 border-l-yellow-500 bg-[#13161f]">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-bold text-white">Badges & Awards</h3>
                            <Award className="w-5 h-5 text-yellow-500" />
                        </div>
                        <div className="flex flex-wrap gap-3 mt-4">
                            {achievements.length > 0 ? (
                                achievements.map((achievement) => {
                                    const IconComponent = {
                                        zap: Zap,
                                        star: Star,
                                        trophy: Trophy,
                                        award: Award
                                    }[achievement.icon_type] || Award;

                                    return (
                                        <div
                                            key={achievement.id}
                                            className="w-12 h-12 rounded-lg bg-yellow-500/10 flex items-center justify-center border border-yellow-500/20 group/badge relative cursor-help"
                                            title={achievement.description}
                                        >
                                            <IconComponent className="w-6 h-6 text-yellow-500" />
                                            {/* Tooltip */}
                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-2 bg-slate-800 text-[10px] text-white rounded opacity-0 group-hover/badge:opacity-100 transition-opacity w-32 pointer-events-none z-10 border border-white/10 text-center">
                                                <p className="font-bold mb-1 underline">{achievement.title}</p>
                                                <p className="text-slate-400 leading-tight">{achievement.description}</p>
                                            </div>
                                        </div>
                                    );
                                })
                            ) : (
                                <div className="flex items-center gap-3 text-slate-500 italic text-sm py-2">
                                    <Award className="w-5 h-5 opacity-20" />
                                    <span>No badges earned yet. Complete your diagnostic test!</span>
                                </div>
                            )}
                            {achievements.length > 0 && achievements.length < 4 && (
                                <div className="w-12 h-12 rounded-lg bg-white/5 border border-dashed border-white/10 flex items-center justify-center text-slate-500 text-xl font-bold">
                                    +
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Classroom Quizzes Section */}
            {classroomQuizzes.length > 0 && (
                <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                    <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
                        <BookOpen className="w-5 h-5 text-primary" />
                        Assigned Learning Modules
                    </h2>
                    <div className="space-y-4">
                        {classroomQuizzes.map((classroom) => (
                            <ClassroomQuizCard key={classroom.classroom_id} classroom={classroom} />
                        ))}
                    </div>
                </div>
            )}

            {/* Enrolled Classes Grid */}
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
                    <School className="w-5 h-5 text-primary" />
                    Academic Communities
                </h2>
                {classes.length === 0 ? (
                    <div className="card-enterprise p-12 text-center border-dashed bg-[#13161f] border-white/5">
                        <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                            <School className="w-8 h-8 text-slate-500" />
                        </div>
                        <p className="text-white font-bold text-lg mb-2">You haven't joined any classes yet.</p>
                        <button
                            onClick={() => setIsJoinModalOpen(true)}
                            className="text-primary font-bold text-sm hover:underline"
                        >
                            Find Your First Class →
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {classes.map((cls) => (
                            <div key={cls.id} className="card-enterprise p-6 group hover:shadow-md transition-all relative overflow-hidden bg-[#13161f] border-white/5">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="p-2 bg-white/5 rounded-lg text-slate-400 group-hover:text-primary transition-colors">
                                        <School className="w-5 h-5" />
                                    </div>
                                    <span className="text-[10px] bg-green-500/10 text-green-400 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">Online</span>
                                </div>
                                <div className="mb-6">
                                    <h3 className="text-xl font-bold text-white leading-tight mb-1">{cls.name}</h3>
                                    <p className="text-xs text-slate-500 uppercase font-bold tracking-wider">Lead by {cls.teacher_name}</p>
                                </div>

                                <div className="flex items-center justify-between pt-4 border-t border-white/5">
                                    <div className="flex items-center gap-2">
                                        <div className="flex -space-x-2">
                                            {[1, 2, 3].map(i => <div key={i} className="w-6 h-6 rounded-full bg-slate-700 border-2 border-[#13161f]"></div>)}
                                        </div>
                                        <span className="text-xs text-slate-400 font-medium">12+ Classmates</span>
                                    </div>
                                    <button
                                        onClick={() => handleLeaveClass(cls.id)}
                                        className="text-xs text-red-400 hover:bg-red-500/10 px-2 py-1 rounded transition-colors font-medium"
                                    >
                                        Leave
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Join Class Modal */}
            {isJoinModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                    <div className="bg-[#0f111a] border border-white/10 p-8 rounded-xl w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200 ring-1 ring-white/10">
                        <div className="flex flex-col items-center text-center gap-4 mb-6">
                            <div className="p-3 bg-primary/10 text-primary rounded-full">
                                <Key className="w-6 h-6" />
                            </div>
                            <h2 className="text-2xl font-bold text-white">Join Classroom</h2>
                            <p className="text-slate-400 text-sm">Enter the 6-character access code provided by your teacher.</p>
                        </div>
                        <form onSubmit={handleJoinClass} className="space-y-4">
                            <input
                                type="text"
                                value={accessCode}
                                onChange={(e) => setAccessCode(e.target.value.toUpperCase())}
                                maxLength={6}
                                className="w-full py-3 text-center text-2xl font-mono font-bold rounded-lg bg-black/30 border border-white/10 focus:border-primary/50 focus:ring-2 focus:ring-primary/20 outline-none uppercase transition-all placeholder:text-slate-600 text-white"
                                placeholder="******"
                                required
                            />
                            <div className="flex flex-col gap-2 pt-2">
                                <button
                                    type="submit"
                                    className="btn-enterprise-primary w-full justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                                    disabled={!accessCode || isJoining}
                                >
                                    {isJoining ? (
                                        <div className="flex items-center gap-2">
                                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            <span>Verifying...</span>
                                        </div>
                                    ) : 'Verify & Join'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => { setIsJoinModalOpen(false); setAccessCode(''); }}
                                    className="w-full py-2.5 rounded-lg text-slate-400 hover:bg-white/5 transition-all font-medium text-sm"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
