'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { classroomAPI, analyticsAPI } from '@/lib/api';
import {
    Plus,
    Search,
    Grid3x3,
    List,
    Loader2,
    Users,
    BookOpen,
    TrendingUp,
    Calendar,
    Key,
    Pencil,
    Trash2,
    X,
    Copy,
    Check,
    Mail
} from 'lucide-react';
import Toast from '@/components/ui/Toast';
import ConfirmationModal from '@/components/ui/ConfirmationModal';

export default function ClassroomsPage() {
    const router = useRouter();
    const [user, setUser] = useState(null);
    const [classrooms, setClassrooms] = useState([]);
    const [stats, setStats] = useState({ avgPerformance: 0, totalQuizzes: 0 });
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [viewMode, setViewMode] = useState('grid');
    const [showJoinModal, setShowJoinModal] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [editingClassroom, setEditingClassroom] = useState(null);
    const [toast, setToast] = useState(null);
    const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: () => { } });

    // Invite Modal State
    const [isInviteOpen, setIsInviteOpen] = useState(false);
    const [selectedClassForInvite, setSelectedClassForInvite] = useState(null);
    const [inviteEmail, setInviteEmail] = useState('');

    useEffect(() => {
        const userData = localStorage.getItem('user');
        if (userData) {
            const parsedUser = JSON.parse(userData);
            setUser(parsedUser);
            fetchClassrooms();
        }
    }, []);


    const fetchClassrooms = async () => {
        setLoading(true);
        try {
            const data = await classroomAPI.getClasses();
            const classes = Array.isArray(data) ? data : data.results || [];
            setClassrooms(classes);

            // If and only if not teacher, calculate aggregate quizzes from class data
            if (user?.role !== 'teacher') {
                const totalQ = classes.reduce((sum, c) => sum + (c.quizzes_count || 0), 0);
                setStats(prev => ({ ...prev, totalQuizzes: totalQ }));

                // Also fetch performance analytics
                try {
                    const analytics = await analyticsAPI.getDashboard();
                    setStats(prev => ({
                        ...prev,
                        avgPerformance: analytics.average_score || 0
                    }));
                } catch (err) {
                    console.error("Failed to fetch analytics", err);
                }
            }
        } catch (error) {
            console.error('Error fetching classrooms:', error);
            setToast({ message: "Failed to load classrooms", type: 'error' });
        } finally {
            setLoading(false);
        }
    };


    const handleDelete = async (id, e) => {
        if (e) e.stopPropagation();
        setConfirmModal({
            isOpen: true,
            title: 'Delete Classroom',
            message: 'Are you sure you want to delete this classroom? This action cannot be undone and will remove all student data associated with it.',
            variant: 'danger',
            confirmText: 'Delete',
            onConfirm: async () => {
                try {
                    await classroomAPI.deleteClass(id);
                    setToast({ message: "Classroom deleted successfully", type: 'success' });
                    fetchClassrooms();
                } catch (error) {
                    console.error('Error deleting classroom:', error);
                    setToast({ message: "Failed to delete classroom", type: 'error' });
                }
            }
        });
    };

    const handleEdit = (classroom, e) => {
        if (e) e.stopPropagation();
        setEditingClassroom(classroom);
    };

    const handleOpenInvite = (classroom, e) => {
        if (e) e.stopPropagation();
        setSelectedClassForInvite(classroom);
        setIsInviteOpen(true);
    };

    const handleInviteSubmit = async (e) => {
        e.preventDefault();
        try {
            await classroomAPI.inviteStudent(selectedClassForInvite.id, inviteEmail);
            setToast({ message: `Invite sent to ${inviteEmail}`, type: 'success' });
            setInviteEmail('');
            setIsInviteOpen(false);
        } catch (error) {
            setToast({ message: error.response?.data?.error || "Failed to invite student", type: 'error' });
        }
    };

    const filteredClassrooms = classrooms.filter(c =>
        c.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const isTeacher = user?.role === 'teacher';

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-10 max-w-[1400px] mx-auto pb-10">
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
                confirmText={confirmModal.confirmText}
            />

            {/* Header Area */}
            <div className="-mx-8 -mt-8 mb-10 p-10 bg-black/20 backdrop-blur-md border-b border-white/5">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 max-w-[1400px] mx-auto">
                    <div>
                        <div className="flex items-center gap-2 text-[10px] font-black tracking-[0.2em] uppercase mb-2">
                            <span className="text-slate-400">Dashboard</span>
                            <span className="text-white/10">/</span>
                            <span className="text-primary">Classrooms</span>
                        </div>
                        <h1 className="text-4xl font-black text-white tracking-tight">
                            {isTeacher ? 'Classroom Management' : 'Academic Classes'}
                        </h1>
                    </div>
                    {isTeacher && (
                        <div className="flex items-center gap-3 w-full md:w-auto">
                            {!isTeacher && (
                                <button
                                    onClick={() => setShowJoinModal(true)}
                                    className="flex-1 md:flex-none px-6 py-3.5 bg-white/5 border border-white/10 hover:bg-white/10 rounded-2xl transition-all flex items-center justify-center gap-2 font-bold text-slate-300 text-sm shadow-sm"
                                >
                                    <Key className="w-4 h-4 text-indigo-400" />
                                    Join with INVITE
                                </button>
                            )}
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="flex-1 md:flex-none btn-enterprise-primary px-7 py-3.5 flex items-center justify-center gap-2"
                            >
                                <Plus className="w-5 h-5" />
                                Create New Class
                            </button>
                        </div>
                    )}
                </div>

            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                    { label: isTeacher ? 'Total Classes' : 'Enrolled', value: classrooms.length, color: 'text-primary', bg: 'bg-primary/10 border-primary/20', icon: Users },
                    { label: isTeacher ? 'Total Students' : 'Active Classes', value: isTeacher ? classrooms.reduce((sum, c) => sum + (c.student_count || 0), 0) : classrooms.length, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20', icon: Users },
                    { label: isTeacher ? 'Active INVITEs' : 'Quizzes', value: isTeacher ? classrooms.filter(c => c.is_join_by_code_enabled).length : stats.totalQuizzes, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20', icon: Key },
                    { label: 'Avg Performance', value: isTeacher ? '--' : `${stats.avgPerformance.toFixed(1)}%`, color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20', icon: TrendingUp },
                ].map((stat, i) => {
                    const Icon = stat.icon;
                    return (
                        <div key={i} className="card-enterprise p-6 group">
                            <div className="flex items-center justify-between mb-4">
                                <div className={`p-3 rounded-xl border ${stat.bg} ${stat.color} shadow-lg shadow-black/5`}>
                                    <Icon className="w-5 h-5" />
                                </div>
                                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest group-hover:text-primary transition-colors">STATS</span>
                            </div>
                            <div>
                                <p className="text-3xl font-black text-white leading-none mb-1">{stat.value}</p>
                                <p className="text-sm font-semibold text-slate-400">{stat.label}</p>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Filter & View Bar */}
            <div className="bg-card p-3 rounded-2xl border border-border shadow-sm flex flex-col md:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Filter by classroom name..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-11 pr-4 py-2.5 bg-secondary border border-border rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:bg-card focus:border-primary/20 transition-all text-sm font-medium"
                    />
                </div>
                <div className="flex gap-2 p-1 bg-secondary rounded-xl border border-border">
                    <button
                        onClick={() => setViewMode('grid')}
                        className={`p-2 rounded-lg transition-all ${viewMode === 'grid'
                            ? 'bg-card text-primary shadow-sm border border-border'
                            : 'text-slate-400 hover:text-slate-600'
                            }`}
                    >
                        <Grid3x3 className="w-5 h-5" />
                    </button>
                    <button
                        onClick={() => setViewMode('list')}
                        className={`p-2 rounded-lg transition-all ${viewMode === 'list'
                            ? 'bg-card text-primary shadow-sm border border-border'
                            : 'text-slate-400 hover:text-slate-600'
                            }`}
                    >
                        <List className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* Content Grid */}
            <div className="relative min-h-[400px]">
                {filteredClassrooms.length > 0 ? (
                    <div className={viewMode === 'grid'
                        ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
                        : "space-y-4"
                    }>
                        {filteredClassrooms.map((classroom) => (
                            viewMode === 'grid' ? (
                                <ClassroomCard
                                    key={classroom.id}
                                    classroom={classroom}
                                    isTeacher={isTeacher}
                                    onClick={() => router.push(`/dashboard/classrooms/${classroom.id}`)}
                                    onEdit={(e) => handleEdit(classroom, e)}
                                    onDelete={(e) => handleDelete(classroom.id, e)}
                                    onInvite={(e) => handleOpenInvite(classroom, e)}
                                />
                            ) : (
                                <ClassroomListItem
                                    key={classroom.id}
                                    classroom={classroom}
                                    isTeacher={isTeacher}
                                    onClick={() => router.push(`/dashboard/classrooms/${classroom.id}`)}
                                    onEdit={(e) => handleEdit(classroom, e)}
                                    onDelete={(e) => handleDelete(classroom.id, e)}
                                    onInvite={(e) => handleOpenInvite(classroom, e)}
                                />
                            )
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-24 bg-card rounded-3xl border-2 border-dashed border-border">
                        <Users className="w-16 h-16 text-muted-foreground/30 mb-4" />
                        <h3 className="text-xl font-bold text-foreground mb-2">No classrooms found</h3>
                        <p className="text-muted-foreground max-w-xs text-center text-sm">
                            {searchTerm ? `No results for "${searchTerm}"` : "You haven't joined or created any classes yet."}
                        </p>
                    </div>
                )}
            </div>

            {/* Modals */}
            {showJoinModal && (
                <JoinByCodeModal
                    onClose={() => setShowJoinModal(false)}
                    onSuccess={() => {
                        fetchClassrooms();
                        setToast({ message: "Joined classroom successfully!", type: 'success' });
                    }}
                    onError={(msg) => setToast({ message: msg, type: 'error' })}
                />
            )}

            {showCreateModal && (
                <CreateClassroomModal
                    onClose={() => setShowCreateModal(false)}
                    onSuccess={() => {
                        setShowCreateModal(false);
                        setToast({ message: "Classroom created successfully!", type: 'success' });
                        fetchClassrooms();
                    }}
                    onError={(msg) => setToast({ message: msg, type: 'error' })}
                />
            )}

            {editingClassroom && (
                <EditClassroomModal
                    classroom={editingClassroom}
                    onClose={() => setEditingClassroom(null)}
                    onSuccess={() => {
                        setEditingClassroom(null);
                        setToast({ message: "Classroom updated successfully", type: 'success' });
                        fetchClassrooms();
                    }}
                    onError={(msg) => setToast({ message: msg, type: 'error' })}
                />
            )}

            {/* Global Invite Student Modal */}
            {isInviteOpen && selectedClassForInvite && (
                <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm cursor-default" onClick={() => setIsInviteOpen(false)}>
                    <div className="bg-card border border-border p-8 rounded-2xl w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                                <Mail className="w-5 h-5" />
                            </div>
                            <div>
                                <h3 className="font-bold text-lg text-foreground">Invite Student</h3>
                                <p className="text-xs text-muted-foreground">To {selectedClassForInvite.name}</p>
                            </div>
                        </div>

                        <form onSubmit={handleInviteSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1.5">Student Email</label>
                                <input
                                    type="email"
                                    value={inviteEmail}
                                    onChange={(e) => setInviteEmail(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl bg-secondary border border-border focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none transition-all placeholder:text-muted-foreground text-sm text-foreground"
                                    placeholder="student@example.com"
                                    required
                                />
                            </div>
                            <div className="flex justify-end gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setIsInviteOpen(false)}
                                    className="px-4 py-2 text-sm font-semibold rounded-xl text-muted-foreground hover:bg-secondary transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="bg-primary text-primary-foreground px-6 py-2 text-sm rounded-xl font-bold hover:bg-primary/90 shadow-lg shadow-primary/25 transition-all"
                                >
                                    Send Invite
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

function ClassroomCard({ classroom, isTeacher, onClick, onEdit, onDelete, onInvite }) {
    const [copied, setCopied] = useState(false);

    const copyCode = (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(classroom.access_code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div
            onClick={onClick}
            className="group card-enterprise relative overflow-hidden cursor-pointer hover:shadow-xl hover:shadow-primary/5 transition-all duration-300"
        >
            <div className="p-6">
                <div className="flex justify-between items-start mb-6">
                    <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center text-slate-400 group-hover:bg-primary/20 group-hover:text-primary transition-colors border border-white/5 group-hover:border-primary/20">
                        <Users className="w-6 h-6" />
                    </div>
                    {isTeacher ? (
                        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                            <button
                                onClick={onInvite}
                                className="p-2 hover:bg-primary/20 rounded-lg text-slate-400 hover:text-primary transition-all"
                                title="Invite Students"
                            >
                                <Mail className="w-4 h-4" />
                            </button>
                            <button
                                onClick={onEdit}
                                className="p-2 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-all"
                            >
                                <Pencil className="w-4 h-4" />
                            </button>
                            <button
                                onClick={onDelete}
                                className="p-2 hover:bg-red-500/10 rounded-lg text-slate-400 hover:text-red-400 transition-all"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    ) : (
                        classroom.is_join_by_code_enabled && (
                            <div className="flex items-center gap-1.5 px-2 py-1 bg-green-500/10 rounded-full border border-green-500/20 shadow-sm shadow-green-500/5">
                                <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]"></div>
                                <span className="text-[10px] font-bold text-green-400 uppercase tracking-tighter">Active</span>
                            </div>
                        )
                    )}
                </div>

                <h3 className="text-xl font-bold text-white mb-2 leading-tight group-hover:text-primary transition-colors">
                    {classroom.name}
                </h3>

                {classroom.is_join_by_code_enabled ? (
                    <div className="mb-6 bg-indigo-500/5 p-4 rounded-xl border border-indigo-500/10 group-hover:border-indigo-500/30 transition-all backdrop-blur-sm">
                        <div className="flex justify-between items-center mb-2">
                            <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">INVITE Code</p>
                            <div className="flex items-center gap-1.5">
                                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></div>
                                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">Active</span>
                            </div>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-2xl font-mono font-bold tracking-widest text-white">{classroom.access_code}</p>
                            <button
                                onClick={copyCode}
                                className="p-2 bg-black/20 rounded-lg shadow-sm border border-white/5 text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 transition-all"
                                title="Copy Code"
                            >
                                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="mb-6 bg-white/5 p-6 rounded-xl border border-dashed border-white/10 flex items-center justify-center gap-2 text-slate-400">
                        <Key className="w-4 h-4 opacity-50" />
                        <span className="text-sm font-medium opacity-70">Invite Only Class</span>
                    </div>
                )}

                <div className="flex items-center justify-between pt-4 border-t border-white/5">
                    <div className="flex items-center gap-2 text-slate-400">
                        <Users className="w-4 h-4 opacity-50" />
                        <span className="text-sm font-bold text-slate-200">{classroom.student_count || 0}</span>
                        <span className="text-xs font-semibold text-slate-500">Students</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-500">
                        <Calendar className="w-4 h-4 opacity-50" />
                        <span className="text-xs font-bold">{new Date(classroom.created_at).toLocaleDateString('en-GB')}</span>
                    </div>
                </div>
            </div>

            <div className="h-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent w-full opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-0 left-0"></div>
        </div>
    );
}

function ClassroomListItem({ classroom, isTeacher, onClick, onEdit, onDelete, onInvite }) {
    return (
        <div
            onClick={onClick}
            className="group card-enterprise p-4 cursor-pointer flex items-center gap-4 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/20 transition-all duration-300"
        >
            <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center text-slate-400 group-hover:bg-primary/20 group-hover:text-primary transition-colors border border-white/5">
                <Users className="w-6 h-6" />
            </div>

            <div className="flex-1">
                <h3 className="text-lg font-bold text-white group-hover:text-primary transition-colors">{classroom.name}</h3>
                <div className="flex items-center gap-6 text-xs font-semibold text-slate-400 mt-1">
                    <div className="flex items-center gap-1.5">
                        <Users className="w-3.5 h-3.5 opacity-70" />
                        <span className="text-slate-500">{classroom.student_count || 0} Students</span>
                    </div>
                    {classroom.access_code && (
                        <div className="flex items-center gap-1.5">
                            <Key className="w-3.5 h-3.5 opacity-70" />
                            <span className="font-mono text-slate-500">{classroom.access_code}</span>
                        </div>
                    )}
                    <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 opacity-70" />
                        <span>{new Date(classroom.created_at).toLocaleDateString('en-GB')}</span>
                    </div>
                </div>
            </div>

            {isTeacher ? (
                <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                        onClick={onInvite}
                        className="p-2.5 hover:bg-primary/20 rounded-xl text-slate-400 hover:text-primary transition-all"
                        title="Invite Students"
                    >
                        <Mail className="w-4 h-4" />
                    </button>
                    <button
                        onClick={onEdit}
                        className="p-2.5 hover:bg-white/5 rounded-xl text-slate-400 hover:text-white transition-all"
                    >
                        <Pencil className="w-4 h-4" />
                    </button>
                    <button
                        onClick={onDelete}
                        className="p-2.5 hover:bg-red-500/10 rounded-xl text-slate-400 hover:text-red-400 transition-all"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            ) : (
                classroom.is_join_by_code_enabled && (
                    <span className="px-3 py-1 bg-green-500/10 text-green-400 rounded-full text-xs font-black uppercase tracking-tight border border-green-500/20 shadow-sm shadow-green-500/5">
                        Active
                    </span>
                )
            )}
        </div>
    );
}

function JoinByCodeModal({ onClose, onSuccess, onError }) {
    const [code, setCode] = useState('');
    const [joining, setJoining] = useState(false);

    const handleJoin = async (e) => {
        e.preventDefault();
        setJoining(true);

        try {
            await classroomAPI.joinClass(code); // Fixed method name from joinByCode to joinClass as per api.js
            onSuccess();
            onClose();
        } catch (error) {
            console.error('Error joining classroom:', error);
            const msg = error.response?.data?.error || 'Check the code and try again.';
            if (onError) onError(msg);
        } finally {
            setJoining(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-md animate-in fade-in duration-300"
                onClick={onClose}
            />
            <div className="relative bg-[#13161f] rounded-[32px] w-full max-w-md overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200 border border-white/10">
                <div className="p-10 text-center">
                    <div className="w-16 h-16 bg-indigo-500/10 rounded-2xl flex items-center justify-center text-indigo-400 mx-auto mb-6 border border-indigo-500/20">
                        <Key className="w-8 h-8" />
                    </div>

                    <h2 className="text-[28px] font-black text-white tracking-tight leading-tight mb-2">
                        Join by INVITE
                    </h2>
                    <p className="text-slate-400 font-semibold mb-8">
                        Enter the 6-character code provided by your teacher.
                    </p>

                    <form onSubmit={handleJoin} className="space-y-6">
                        <input
                            type="text"
                            value={code}
                            onChange={(e) => setCode(e.target.value.toUpperCase())}
                            className="w-full px-5 py-5 bg-black/30 border border-white/10 rounded-2xl focus:outline-none focus:ring-4 focus:ring-primary/20 focus:bg-black/50 focus:border-primary/50 transition-all text-white font-black text-4xl text-center tracking-[0.3em] placeholder:text-slate-600 placeholder:tracking-normal font-mono"
                            placeholder="INVITE"
                            maxLength={6}
                            required
                        />

                        <div className="flex flex-col gap-3 pt-4">
                            <button
                                type="submit"
                                disabled={joining || code.length !== 6}
                                className="w-full btn-enterprise-primary py-4 rounded-[18px] font-black hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20 active:scale-95 flex items-center justify-center"
                            >
                                {joining ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Join Classroom'}
                            </button>
                            <button
                                type="button"
                                onClick={onClose}
                                className="w-full py-3 text-slate-500 font-bold hover:text-slate-300 transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

function CreateClassroomModal({ onClose, onSuccess, onError }) {
    const [name, setName] = useState('');
    const [enableCode, setEnableCode] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await classroomAPI.createClass({
                name: name,
                is_join_by_code_enabled: enableCode
            });
            onSuccess();
        } catch (error) {
            console.error('Create error:', error);
            onError(error.response?.data?.error || "Failed to create classroom");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-md animate-in fade-in duration-300"
                onClick={onClose}
            />
            <div className="relative bg-[#13161f] rounded-[32px] w-full max-w-md overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200 border border-white/10">
                <div className="p-10">
                    <div className="flex justify-between items-start mb-2">
                        <h2 className="text-[28px] font-black text-white tracking-tight leading-tight">
                            Create New Class
                        </h2>
                    </div>
                    <p className="text-slate-400 font-semibold mb-8">
                        Organize your students into a new workspace.
                    </p>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-bold text-slate-400 tracking-wide uppercase ml-1">
                                Classroom Name
                            </label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g. Mathematics Grade 10"
                                className="w-full px-5 py-4 bg-black/30 border border-white/10 rounded-2xl focus:outline-none focus:ring-4 focus:ring-primary/20 focus:bg-black/50 focus:border-primary/50 transition-all text-white font-semibold placeholder:text-slate-600"
                                required
                            />
                        </div>

                        <div
                            className={`p-5 rounded-2xl border transition-all flex items-start gap-4 cursor-pointer group ${enableCode
                                ? 'bg-primary/10 border-primary/20'
                                : 'bg-white/5 border-white/10 hover:bg-white/10'
                                }`}
                            onClick={() => setEnableCode(!enableCode)}
                        >
                            <div className="mt-1">
                                <div className={`w-6 h-6 rounded-md border-2 transition-all flex items-center justify-center ${enableCode
                                    ? 'bg-primary border-primary'
                                    : 'bg-transparent border-slate-600 group-hover:border-slate-500'
                                    }`}>
                                    {enableCode && <Check className="w-4 h-4 text-white" />}
                                </div>
                            </div>
                            <div className="flex-1">
                                <p className={`font-bold transition-colors ${enableCode ? 'text-white' : 'text-slate-300'}`}>
                                    Enable Join by INVITE
                                </p>
                                <p className={`text-xs font-semibold mt-1 transition-colors ${enableCode ? 'text-primary' : 'text-slate-500'}`}>
                                    Students can join using a 6-digit INVITE code.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center justify-end gap-4 pt-4">
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-6 py-3 text-slate-500 font-bold hover:text-slate-300 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={loading || !name}
                                className="btn-enterprise-primary px-8 py-3.5 flex items-center justify-center"
                            >
                                {loading ? 'Creating...' : 'Create Class'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

function EditClassroomModal({ classroom, onClose, onSuccess, onError }) {
    const [name, setName] = useState(classroom.name);
    const [enableCode, setEnableCode] = useState(classroom.is_join_by_code_enabled);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await classroomAPI.updateClass(classroom.id, {
                name: name,
                is_join_by_code_enabled: enableCode
            });
            onSuccess();
        } catch (error) {
            console.error('Update error:', error);
            onError(error.response?.data?.error || "Failed to update classroom");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-md animate-in fade-in duration-300"
                onClick={onClose}
            />
            <div className="relative bg-[#13161f] rounded-[32px] w-full max-w-md overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200 border border-white/10">
                <div className="p-10">
                    <div className="flex justify-between items-start mb-2">
                        <h2 className="text-[28px] font-black text-white tracking-tight leading-tight">
                            Edit Classroom
                        </h2>
                    </div>
                    <p className="text-slate-400 font-semibold mb-8">
                        Update your classroom settings.
                    </p>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-bold text-slate-400 tracking-wide uppercase ml-1">
                                Classroom Name
                            </label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full px-5 py-4 bg-black/30 border border-white/10 rounded-2xl focus:outline-none focus:ring-4 focus:ring-primary/20 focus:bg-black/50 focus:border-primary/50 transition-all text-white font-semibold placeholder:text-slate-600"
                                required
                            />
                        </div>

                        <div
                            className={`p-5 rounded-2xl border transition-all flex items-start gap-4 cursor-pointer group ${enableCode
                                ? 'bg-primary/10 border-primary/20'
                                : 'bg-white/5 border-white/10 hover:bg-white/10'
                                }`}
                            onClick={() => setEnableCode(!enableCode)}
                        >
                            <div className="mt-1">
                                <div className={`w-6 h-6 rounded-md border-2 transition-all flex items-center justify-center ${enableCode
                                    ? 'bg-primary border-primary'
                                    : 'bg-transparent border-slate-600 group-hover:border-slate-500'
                                    }`}>
                                    {enableCode && <Check className="w-4 h-4 text-white" />}
                                </div>
                            </div>
                            <div className="flex-1">
                                <p className={`font-bold transition-colors ${enableCode ? 'text-white' : 'text-slate-300'}`}>
                                    Enable Join by INVITE
                                </p>
                                <p className={`text-xs font-semibold mt-1 transition-colors ${enableCode ? 'text-primary' : 'text-slate-500'}`}>
                                    Students can join using a 6-digit INVITE code.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center justify-end gap-4 pt-4">
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-6 py-3 text-slate-500 font-bold hover:text-slate-300 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={loading || !name}
                                className="btn-enterprise-primary px-8 py-3.5 flex items-center justify-center"
                            >
                                {loading ? 'Saving...' : 'Save Changes'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
