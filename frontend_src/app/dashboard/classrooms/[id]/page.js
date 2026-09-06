'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { classroomAPI, analyticsAPI, teacherAPI } from '@/lib/api';
import {
    ArrowLeft,
    Users,
    BookOpen,
    TrendingUp,
    Settings as SettingsIcon,
    Loader2,
    Key,
    Calendar,
    Mail,
    Trash2,
    UserPlus,
    LogOut,
    School,
    Brain,
    Trophy,
    History,
    Phone,
    MoreVertical,
    FileText,
    CheckCircle2,
    Clock,
    Eye,
    AlertCircle,
    Pencil,
    Plus as PlusIcon
} from 'lucide-react';
import Toast from '@/components/ui/Toast';
import ConfirmationModal from '@/components/ui/ConfirmationModal';
import StudentLearningDNAModal from '@/components/dashboard/StudentLearningDNAModal';
import InviteStudentModal from '@/components/InviteStudentModal';
import SettingsTab from '@/components/dashboard/classroom/SettingsTab';
import AnalyticsTab from '@/components/dashboard/classroom/AnalyticsTab';
import AssignQuizModal from '@/components/dashboard/classrooms/AssignQuizModal';

export default function ClassroomDetailsPage() {
    const router = useRouter();
    const params = useParams();
    const classroomId = params.id;

    const [user, setUser] = useState(null);
    const [classroom, setClassroom] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [toast, setToast] = useState(null);
    const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: () => { } });
    const [analyticsSummary, setAnalyticsSummary] = useState(null);

    useEffect(() => {
        const userData = localStorage.getItem('user');
        if (userData) {
            setUser(JSON.parse(userData));
        }
        fetchClassroom();
        fetchAnalyticsSummary();
    }, [classroomId]);

    const fetchAnalyticsSummary = async () => {
        const userData = localStorage.getItem('user');
        const role = userData ? JSON.parse(userData).role : null;
        if (role !== 'teacher') return;
        try {
            const data = await teacherAPI.getClassroomMasteryAnalytics(classroomId);
            setAnalyticsSummary(data);
        } catch (error) {
            console.warn('Analytics summary fetch failed');
        }
    };

    const fetchClassroom = async () => {
        try {
            const data = await classroomAPI.getClassDetails(classroomId);
            setClassroom(data);
        } catch (error) {
            console.error('Error fetching classroom:', error);
            setToast({ message: 'Failed to load classroom details', type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleLeaveClass = () => {
        setConfirmModal({
            isOpen: true,
            title: 'Leave Classroom?',
            message: 'Are you sure you want to leave this class? You will lose access to content.',
            variant: 'danger',
            onConfirm: async () => {
                try {
                    await classroomAPI.leaveClassroom(classroomId);
                    router.push('/dashboard/classrooms');
                } catch (error) {
                    setToast({ message: 'Failed to leave class', type: 'error' });
                }
            }
        });
    };

    const handleUnassignQuiz = (assignmentId) => {
        setConfirmModal({
            isOpen: true,
            title: 'Remove Quiz?',
            message: 'Are you sure you want to remove this quiz from the classroom? Students will lose access.',
            variant: 'danger',
            onConfirm: async () => {
                try {
                    await classroomAPI.unassignQuiz(classroomId, assignmentId);
                    setToast({ message: 'Quiz removed successfully', type: 'success' });
                    fetchClassroom(); // Refresh classroom data
                } catch (error) {
                    setToast({ message: 'Failed to remove quiz', type: 'error' });
                }
            }
        });
    };

    const isTeacher = user?.role === 'teacher';
    const isOwner = user?.id === classroom?.teacher;

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!classroom) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="w-16 h-16 bg-muted/50 rounded-full flex items-center justify-center mb-4 text-muted-foreground">
                    <School className="w-8 h-8" />
                </div>
                <h2 className="text-xl font-bold text-foreground">Classroom not found</h2>
                <button onClick={() => router.push('/dashboard')} className="mt-6 btn-enterprise-primary">
                    Return to Dashboard
                </button>
            </div>
        );
    }

    const tabs = [
        { id: 'overview', label: 'Overview', icon: TrendingUp },
        { id: 'students', label: 'Students', icon: Users },
        { id: 'quizzes', label: 'Quizzes', icon: BookOpen },
        { id: 'analytics', label: 'Analytics', icon: TrendingUp },
    ];

    if (isOwner) {
        tabs.push({ id: 'settings', label: 'Settings', icon: SettingsIcon });
    }

    return (
        <div className="space-y-8 max-w-7xl mx-auto pb-10 animate-in fade-in duration-700">
            {/* Enterprise Hero Header */}
            <div className="relative overflow-hidden bg-card border border-border rounded-3xl shadow-xl w-full">
                {/* Background Gradient Mesh */}
                <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] pointer-events-none opacity-60" />
                <div className="absolute bottom-0 left-0 translate-y-1/2 -translate-x-1/2 w-[400px] h-[400px] bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none opacity-40" />

                <div className="relative p-8 lg:p-10 flex flex-col lg:flex-row lg:items-end justify-between gap-6 z-10">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-4">
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider border border-primary/20">
                                <School className="w-3 h-3" /> Classroom
                            </span>
                            {classroom.is_join_by_code_enabled && (
                                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-muted text-muted-foreground text-xs font-bold uppercase tracking-wider border border-white/5">
                                    <Key className="w-3 h-3" /> {classroom.access_code}
                                </span>
                            )}
                        </div>
                        <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight leading-tight mb-2">
                            {classroom.name}
                        </h1>
                        <p className="text-lg text-muted-foreground font-medium flex items-center gap-2">
                            <Calendar className="w-4 h-4" />
                            Established {new Date(classroom.created_at).toLocaleDateString('en-GB')}
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-3">
                        <button
                            onClick={() => router.push(`/dashboard/history?classroom_id=${classroomId}`)}
                            className="px-5 py-2.5 rounded-lg bg-secondary/50 hover:bg-secondary text-secondary-foreground border border-white/5 font-semibold transition-all flex items-center gap-2"
                        >
                            <History className="w-4 h-4" /> History
                        </button>
                        {isTeacher ? (
                            <button
                                onClick={() => setShowInviteModal(true)}
                                className="btn-enterprise-primary px-6 py-2.5 flex items-center gap-2"
                            >
                                <UserPlus className="w-4 h-4" /> Invite Students
                            </button>
                        ) : user?.role === 'student' ? (
                            <button
                                onClick={handleLeaveClass}
                                className="px-5 py-2.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 font-semibold transition-all flex items-center gap-2"
                            >
                                <LogOut className="w-4 h-4" /> Leave Class
                            </button>
                        ) : null}
                    </div>
                </div>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <DetailStatCard label="Total Students" value={classroom.students?.length || 0} icon={Users} color="indigo" />
                <DetailStatCard label="Active Quizzes" value={classroom.quizzes_count || 0} icon={BookOpen} color="blue" />
                <DetailStatCard
                    label="Class Average"
                    value={analyticsSummary ? `${Math.round(analyticsSummary.class_average_mastery * 100)}%` : "--"}
                    icon={TrendingUp}
                    color="emerald"
                />
                <DetailStatCard label="Last Updated" value={new Date().toLocaleDateString('en-GB')} icon={Clock} color="amber" />
            </div>

            {/* Enterprise Tabs */}
            <div className="flex flex-wrap gap-2 p-1.5 bg-card/50 border border-white/5 rounded-xl w-full md:w-fit backdrop-blur-sm">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`
                            px-6 py-2.5 rounded-lg transition-all font-bold text-sm flex items-center gap-2
                            ${activeTab === tab.id
                                ? 'bg-primary text-primary-foreground shadow-md'
                                : 'text-muted-foreground hover:text-foreground hover:bg-white/5'}
                        `}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="min-h-[400px]">
                {activeTab === 'overview' && <OverviewTab classroom={classroom} user={user} />}
                {activeTab === 'students' && (
                    <StudentsTab
                        classroom={classroom}
                        isTeacher={isTeacher}
                        onUpdate={fetchClassroom}
                        setConfirmModal={setConfirmModal}
                        setToast={setToast}
                    />
                )}
                {activeTab === 'quizzes' && (
                    <QuizzesTab
                        classroom={classroom}
                        isTeacher={isTeacher}
                        onUpdate={fetchClassroom}
                        setToast={setToast}
                        setConfirmModal={setConfirmModal}
                        onUnassign={handleUnassignQuiz}
                    />
                )}
                {activeTab === 'analytics' && <AnalyticsTab classroom={classroom} />}
                {activeTab === 'settings' && (
                    <SettingsTab
                        classroom={classroom}
                        onUpdate={fetchClassroom}
                        setToast={setToast}
                        setConfirmModal={setConfirmModal}
                    />
                )}
            </div>

            {/* Modals */}
            {showInviteModal && (
                <InviteStudentModal
                    classroomId={classroomId}
                    onClose={() => setShowInviteModal(false)}
                    onSuccess={fetchClassroom}
                    setToast={setToast}
                />
            )}
            {toast && (
                <div className="fixed bottom-8 right-8 z-[200]">
                    <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
                </div>
            )}
            <ConfirmationModal
                isOpen={confirmModal.isOpen}
                onClose={() => setConfirmModal({ ...confirmModal, isOpen: false })}
                onConfirm={confirmModal.onConfirm}
                title={confirmModal.title}
                message={confirmModal.message}
                variant={confirmModal.variant}
            />
        </div>
    );
}

// Enterprise Stat Card
function DetailStatCard({ label, value, icon: Icon, color }) {
    const colorStyles = {
        indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
        blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    }[color] || 'bg-primary/10 text-primary border-primary/20';

    return (
        <div className="bg-card p-6 rounded-2xl border border-border/50 shadow-sm hover:shadow-md transition-all group">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 border ${colorStyles}`}>
                <Icon className="w-6 h-6" />
            </div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
            <h4 className="text-3xl font-bold text-foreground tracking-tight">{value}</h4>
        </div>
    );
}

// Refactored Overview Tab
function OverviewTab({ classroom, user }) {
    const isStudent = user?.role === 'student';

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
                <div className="bg-card p-8 rounded-3xl border border-border shadow-sm">
                    <h3 className="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
                        <School className="w-5 h-5 text-primary" />
                        Classroom Details
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-y-8 gap-x-12">
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Class Name</p>
                            <p className="text-lg font-semibold text-foreground">{classroom.name}</p>
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Created On</p>
                            <p className="text-lg font-semibold text-foreground">{new Date(classroom.created_at).toLocaleDateString('en-GB')}</p>
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Participation</p>
                            <p className="text-lg font-semibold text-foreground">{classroom.students?.length || 0} Enrolled Students</p>
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Curriculum</p>
                            <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-bold">
                                <Brain className="w-4 h-4" /> Adaptive Learning
                            </div>
                        </div>
                    </div>
                </div>

                <div className="bg-card p-8 rounded-3xl border border-border shadow-sm">
                    <h3 className="text-xl font-bold text-foreground mb-6">Recent Activity</h3>
                    <div className="flex items-center gap-4 p-4 bg-muted/30 rounded-2xl border border-white/5">
                        <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                        <p className="text-sm font-bold text-foreground flex-1">Classroom environment ready</p>
                        <span className="text-xs font-bold text-emerald-500 uppercase tracking-wider">Live</span>
                    </div>
                </div>

                {isStudent && (
                    <div className="bg-gradient-to-br from-primary/10 to-indigo-500/10 p-8 rounded-3xl border border-primary/10">
                        <div className="flex items-start gap-6">
                            <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-primary/20">
                                <Trophy className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-foreground mb-2">Your Progress</h3>
                                <p className="text-muted-foreground mb-4">You're doing great! Keep completing quizzes to earn more mastery points.</p>
                                <div className="flex gap-4">
                                    <div className="px-4 py-2 bg-card rounded-xl border border-border/50">
                                        <p className="text-xs text-muted-foreground uppercase font-bold">Quizzes</p>
                                        <p className="text-xl font-black text-primary">0</p>
                                    </div>
                                    <div className="px-4 py-2 bg-card rounded-xl border border-border/50">
                                        <p className="text-xs text-muted-foreground uppercase font-bold">Avg Score</p>
                                        <p className="text-xl font-black text-emerald-500">0%</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <div className="space-y-6">
                <div className="bg-card p-6 rounded-3xl border border-border shadow-sm">
                    <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-4">Instructors</h4>
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
                                {(classroom.teacher.username || 'T')[0]?.toUpperCase()}
                            </div>
                            <div>
                                <p className="font-bold text-foreground text-sm">{classroom.teacher.full_name || classroom.teacher.username}</p>
                                <p className="text-xs text-primary font-medium">Lead Teacher</p>
                            </div>
                        </div>
                        {classroom.co_teachers?.map(ct => (
                            <div key={ct.id} className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground font-bold">
                                    {(ct.username || 'C')[0]?.toUpperCase()}
                                </div>
                                <div>
                                    <p className="font-bold text-foreground text-sm">{ct.full_name || ct.username}</p>
                                    <p className="text-xs text-muted-foreground">Co-Teacher</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-card p-6 rounded-3xl border border-border shadow-sm">
                    <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-4">Quick Actions</h4>
                    <div className="space-y-2">
                        <button onClick={() => window.location.href = '/dashboard/learning'} className="w-full text-left px-4 py-3 rounded-xl hover:bg-muted/50 transition-colors flex items-center gap-3 text-sm font-medium text-foreground">
                            <BookOpen className="w-4 h-4 text-blue-500" /> Browse Learning Modules
                        </button>
                        <button onClick={() => window.location.href = '/dashboard/history'} className="w-full text-left px-4 py-3 rounded-xl hover:bg-muted/50 transition-colors flex items-center gap-3 text-sm font-medium text-foreground">
                            <History className="w-4 h-4 text-purple-500" /> View History
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Refactored Students Tab
function StudentsTab({ classroom, isTeacher, onUpdate, setConfirmModal, setToast }) {
    const [selectedStudent, setSelectedStudent] = useState(null);

    const handleRemove = async (studentId) => {
        setConfirmModal({
            isOpen: true,
            title: 'Remove Student?',
            message: 'Are you sure you want to remove this student from the class?',
            variant: 'danger',
            onConfirm: async () => {
                try {
                    await classroomAPI.removeStudent(classroom.id, studentId);
                    setToast({ message: 'Student removed successfully', type: 'success' });
                    onUpdate();
                } catch (error) {
                    setToast({ message: 'Failed to remove student', type: 'error' });
                }
            }
        });
    };

    if (!classroom.students || classroom.students.length === 0) {
        return (
            <div className="bg-card p-16 rounded-3xl border border-border text-center">
                <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center mx-auto mb-6">
                    <Users className="w-10 h-10 text-muted-foreground" />
                </div>
                <h3 className="text-xl font-bold text-foreground mb-2">No Students Yet</h3>
                <p className="text-muted-foreground mb-6">Share the invite code to start teaching.</p>
                {isTeacher && (
                    <div className="inline-block px-4 py-2 bg-muted rounded-lg border border-border font-mono text-sm">
                        {classroom.access_code}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="bg-card rounded-3xl border border-border shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-muted/50 border-b border-white/5">
                            <tr>
                                <th className="text-left p-6 font-bold text-xs text-muted-foreground uppercase tracking-wider">Student</th>
                                <th className="text-left p-6 font-bold text-xs text-muted-foreground uppercase tracking-wider">Joined</th>
                                {isTeacher && <th className="text-right p-6 font-bold text-xs text-muted-foreground uppercase tracking-wider">Actions</th>}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {classroom.students.map((student, index) => (
                                <tr key={index} className="hover:bg-muted/30 transition-colors group">
                                    <td className="p-6">
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center font-bold text-primary">
                                                {(student.username || 'S')[0]?.toUpperCase()}
                                            </div>
                                            <div>
                                                <p className="font-bold text-foreground">{student.full_name || student.username}</p>
                                                <p className="text-xs text-muted-foreground">{student.email}</p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-6">
                                        <div className="flex items-center gap-2 text-sm text-foreground">
                                            <Calendar className="w-4 h-4 text-muted-foreground" />
                                            {student.date_joined ? new Date(student.date_joined).toLocaleDateString('en-GB') : '--'}
                                        </div>
                                    </td>
                                    {isTeacher && (
                                        <td className="p-6 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => setSelectedStudent(student)}
                                                    className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                                                    title="View Insights"
                                                >
                                                    <Brain className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => handleRemove(student.id)}
                                                    className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                                                    title="Remove Student"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            {selectedStudent && (
                <StudentLearningDNAModal
                    student={selectedStudent}
                    onClose={() => setSelectedStudent(null)}
                />
            )}
        </div>
    );
}



// Refactored Quizzes Tab
function QuizzesTab({ classroom, isTeacher, onUpdate, setToast, setConfirmModal, onUnassign }) {
    const router = useRouter();
    const [assignedQuizzes, setAssignedQuizzes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
    const [editingAssignment, setEditingAssignment] = useState(null);

    useEffect(() => {
        if (classroom?.id) {
            fetchAssignedQuizzes();
        }
    }, [classroom]);

    const fetchAssignedQuizzes = async () => {
        try {
            const data = await classroomAPI.getAssignedQuizzes(classroom.id);
            setAssignedQuizzes(Array.isArray(data) ? data : data.results || []);
        } catch (error) {
            console.error('Failed to fetch quizzes');
        } finally {
            setLoading(false);
        }
    };

    const handleAssignQuiz = async (quizId, config) => {
        try {
            await classroomAPI.assignQuiz(classroom.id, quizId, config);
            setToast({ message: 'Quiz assigned successfully', type: 'success' });
            setIsAssignModalOpen(false);
            fetchAssignedQuizzes();
        } catch (error) {
            setToast({ message: 'Failed to assign quiz', type: 'error' });
        }
    };

    const handleStartQuiz = async (assignment) => {
        try {
            // Use assignment_id for the API call
            const response = await classroomAPI.startClassroomQuizAttempt(assignment.assignment_id);
            router.push(`/quiz/${response.session_id}`);
        } catch (error) {
            setToast({ message: 'Failed to start quiz', type: 'error' });
        }
    };

    const handleUpdateAssignment = async (assignmentId, config) => {
        try {
            await classroomAPI.updateClassroomQuizAssignment(assignmentId, config);
            setToast({ message: 'Assignment updated successfully', type: 'success' });
            setEditingAssignment(null);
            fetchAssignedQuizzes();
        } catch (error) {
            setToast({ message: 'Failed to update assignment', type: 'error' });
        }
    };

    if (loading) return <div className="p-16 text-center"><Loader2 className="w-10 h-10 animate-spin mx-auto text-primary" /></div>;

    if (!assignedQuizzes || assignedQuizzes.length === 0) {
        return (
            <>
                <div className="bg-card/50 p-20 rounded-3xl border border-white/5 text-center flex flex-col items-center justify-center">
                    <div className="w-24 h-24 bg-primary/10 rounded-full flex items-center justify-center mb-6 animate-pulse">
                        <BookOpen className="w-12 h-12 text-primary" />
                    </div>
                    <h3 className="text-2xl font-black text-foreground mb-3">No Quizzes Active</h3>
                    <p className="text-muted-foreground max-w-md mx-auto mb-8 text-lg">
                        {isTeacher ? "Assign a quiz to your students to get started." : "Your teacher hasn't assigned any quizzes yet."}
                    </p>
                    {isTeacher && (
                        <button onClick={() => setIsAssignModalOpen(true)} className="btn-enterprise-primary px-8 py-3">
                            Assign New Quiz
                        </button>
                    )}
                </div>
                <AssignQuizModal
                    isOpen={isAssignModalOpen}
                    onClose={() => setIsAssignModalOpen(false)}
                    onAssign={handleAssignQuiz}
                />
            </>
        );
    }

    return (
        <div className="space-y-6">
            {isTeacher && (
                <div className="flex justify-end">
                    <button
                        onClick={() => setIsAssignModalOpen(true)}
                        className="btn-enterprise-primary px-5 py-2.5 flex items-center gap-2 text-sm"
                    >
                        <PlusIcon className="w-4 h-4" /> Assign Quiz
                    </button>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {assignedQuizzes.map((quiz) => (
                    <div
                        key={quiz.assignment_id || quiz.id}
                        className="group relative bg-white/5 hover:bg-white/[0.07] border border-white/10 rounded-2xl p-6 transition-all duration-300 hover:shadow-xl hover:shadow-primary/10 hover:-translate-y-1"
                    >
                        {/* Action Buttons - Top Right (Visible on hover) */}
                        {isTeacher && (
                            <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-all z-20">
                                <button
                                    onClick={() => setEditingAssignment(quiz)}
                                    className="w-8 h-8 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 flex items-center justify-center transition-all cursor-pointer"
                                    title="Edit Assignment"
                                >
                                    <Pencil className="w-4 h-4 text-blue-400" />
                                </button>
                                <button
                                    onClick={() => onUnassign(quiz.assignment_id || quiz.id)}
                                    className="w-8 h-8 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 flex items-center justify-center transition-all cursor-pointer"
                                    title="Remove Quiz"
                                >
                                    <Trash2 className="w-4 h-4 text-red-400" />
                                </button>
                            </div>
                        )}

                        {/* Quiz Icon & Mode Badge */}
                        <div className="flex justify-between items-start mb-4">
                            <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-primary/10 border border-primary/20">
                                <FileText className="w-6 h-6 text-primary" />
                            </div>

                        </div>

                        {/* Quiz Title */}
                        <h3 className="text-lg font-bold text-foreground mb-2 line-clamp-2 min-h-[3.5rem]">
                            {quiz.title || 'Untitled Quiz'}
                        </h3>
                        <div className="flex gap-2 my-3">
                            <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider ${quiz.quiz_mode === 'assessment'
                                ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                                : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                                }`}>
                                {quiz.quiz_mode || 'Practice'}
                            </span>
                        </div>

                        {/* Quiz Stats */}
                        <div className="space-y-2 mb-4">
                            <div className="flex items-center justify-between text-sm text-muted-foreground">
                                <span className="flex items-center gap-1.5">
                                    <Clock className="w-4 h-4 text-blue-400" />
                                    {quiz.time_limit_minutes ? `${quiz.time_limit_minutes} mins` : 'No Limit'}
                                </span>
                                <span className="flex items-center gap-1.5">
                                    <Trophy className="w-4 h-4 text-amber-400" />
                                    {quiz.total_marks || 0} pts
                                </span>
                            </div>
                            {quiz.due_date && (
                                <p className="text-xs text-red-400 flex items-center gap-1">
                                    <AlertCircle className="w-3 h-3" /> Due: {new Date(quiz.due_date).toLocaleDateString('en-GB')}
                                </p>
                            )}
                        </div>

                        {/* Action Buttons */}
                        {isTeacher ? (
                            <div className="space-y-2">
                                <button
                                    onClick={() => handleStartQuiz(quiz)}
                                    className="w-full px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-foreground font-semibold text-sm transition-all flex items-center justify-center gap-2 border border-white/10"
                                >
                                    <Eye className="w-4 h-4" />
                                    Preview as Student
                                </button>
                            </div>
                        ) : (
                            <button
                                onClick={() => handleStartQuiz(quiz)}
                                className="w-full px-4 py-2.5 rounded-xl bg-primary hover:bg-primary/90 text-white font-semibold text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary/20"
                            >
                                <Brain className="w-4 h-4" />
                                {quiz.quiz_mode === 'assessment' ? 'Start Assessment' : 'Start Practice'}
                            </button>
                        )}
                    </div>
                ))}
            </div>

            <AssignQuizModal
                isOpen={isAssignModalOpen || !!editingAssignment}
                onClose={() => {
                    setIsAssignModalOpen(false);
                    setEditingAssignment(null);
                }}
                onAssign={handleAssignQuiz}
                onUpdate={handleUpdateAssignment}
                initialAssignment={editingAssignment}
            />
        </div>
    );
}
