'use client';

import { useState, useEffect } from 'react';
import { classroomAPI, quizAPI } from '@/lib/api';
import {
    Plus,
    Users,
    Mail,
    Copy,
    Check,
    School,
    BookOpen,
    FileQuestion,
    ClipboardList,
    LayoutDashboard,
    RefreshCw,
    BarChart3,
    Search,
    Key,
    Target,
    Loader2,
    Brain
} from 'lucide-react';

import StudentLearningDNAModal from '@/components/dashboard/StudentLearningDNAModal';

// Import the management components
import QuizReporting from './management/QuizReporting';
import Toast from '@/components/ui/Toast';
import ConfirmationModal from '@/components/ui/ConfirmationModal';

export default function TeacherDashboard({ user }) {
    const [activeTab, setActiveTab] = useState('overview');
    const [classes, setClasses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isInviteOpen, setIsInviteOpen] = useState(false);
    const [selectedClassId, setSelectedClassId] = useState(null);
    const [toast, setToast] = useState(null);
    const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: () => { } });
    const [newClassName, setNewClassName] = useState('');
    const [enableCode, setEnableCode] = useState(false);

    useEffect(() => {
        fetchClasses();
    }, []);

    const fetchClasses = async () => {
        try {
            const data = await classroomAPI.getClasses();
            setClasses(Array.isArray(data) ? data : data.results || []);
        } catch (error) {
            console.error("Error fetching classes:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateClass = async (e) => {
        e.preventDefault();
        try {
            await classroomAPI.createClass({
                name: newClassName,
                is_join_by_code_enabled: enableCode
            });
            setNewClassName('');
            setEnableCode(false);
            setIsCreateModalOpen(false);
            fetchClasses();
        } catch (error) {
            setToast({ message: "Failed to create class", type: 'error' });
        }
    };

    const tabs = [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'results', label: 'Results & Reports', icon: BarChart3 },
        { id: 'insights', label: 'Student Insights', icon: Brain },
    ];

    return (
        <div className="space-y-6 max-w-[1600px] mx-auto min-h-screen pb-10 relative">
            {/* Enterprise Dashboard Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/10 pb-6">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Teacher Console</h1>
                    <p className="text-slate-400 mt-1">Manage your classrooms and view student insights.</p>
                </div>

                {/* Horizontal Navigation Tabs - Clean Style */}
                <div className="flex bg-black/20 p-1 rounded-lg border border-white/5">
                    {tabs.map(tab => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${isActive
                                    ? 'bg-primary/20 text-primary shadow-sm border border-primary/20'
                                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                                    }`}
                            >
                                <Icon className={`w-4 h-4 ${isActive ? 'text-primary' : ''}`} />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Dynamic Content Area */}
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                {activeTab === 'overview' && (
                    <OverviewTab
                        classes={classes}
                        loading={loading}
                        onCreateClass={() => setIsCreateModalOpen(true)}
                        refreshClasses={fetchClasses}
                        toast={toast}
                        setToast={setToast}
                        confirmModal={confirmModal}
                        setConfirmModal={setConfirmModal}
                    />
                )}
                {activeTab === 'results' && (
                    <QuizReporting
                        classrooms={classes}
                        loading={loading}
                    />
                )}

                {activeTab === 'insights' && (
                    <StudentInsightsTab
                        classrooms={classes}
                        loading={loading}
                    />
                )}
            </div>


            {/* Overlays */}
            {toast && (
                <div className="fixed bottom-8 right-8 z-[200]">
                    <Toast
                        message={toast.message}
                        type={toast.type}
                        onClose={() => setToast(null)}
                    />
                </div>
            )}

            {/* Global Modals */}
            <ConfirmationModal
                isOpen={confirmModal.isOpen}
                onClose={() => setConfirmModal({ ...confirmModal, isOpen: false })}
                onConfirm={confirmModal.onConfirm}
                title={confirmModal.title}
                message={confirmModal.message}
                variant={confirmModal.variant}
            />

            {/* Create Class Modal - Matches Image 1 */}
            {isCreateModalOpen && (
                <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
                    <div
                        className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300"
                        onClick={() => setIsCreateModalOpen(false)}
                    />
                    <div className="relative bg-[#0f111a] border border-white/10 rounded-[24px] w-full max-w-md overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200 ring-1 ring-white/10">
                        <div className="p-10">
                            <div className="flex justify-between items-start mb-2">
                                <h2 className="text-3xl font-bold font-outfit tracking-tight leading-tight text-white">
                                    Create New Class
                                </h2>
                            </div>
                            <p className="text-slate-400 font-medium mb-8">
                                Organize your students into a new workspace.
                            </p>

                            <form onSubmit={handleCreateClass} className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-slate-300 tracking-wide uppercase ml-1">
                                        Classroom Name
                                    </label>
                                    <input
                                        type="text"
                                        value={newClassName}
                                        onChange={(e) => setNewClassName(e.target.value)}
                                        placeholder="e.g. Mathematics Grade 10"
                                        className="w-full px-5 py-4 bg-black/30 border border-white/10 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:bg-black/50 focus:border-primary/50 transition-all text-white font-semibold placeholder:text-slate-600"
                                        required
                                    />
                                </div>

                                <div
                                    className={`p-5 rounded-2xl border transition-all flex items-start gap-4 cursor-pointer group ${enableCode
                                        ? 'bg-primary/10 border-primary/30'
                                        : 'bg-black/20 border-white/10 hover:bg-black/40'
                                        }`}
                                    onClick={() => setEnableCode(!enableCode)}
                                >
                                    <div className="mt-1">
                                        <div className={`w-6 h-6 rounded-md border-2 transition-all flex items-center justify-center ${enableCode
                                            ? 'bg-primary border-primary'
                                            : 'bg-transparent border-slate-600 group-hover:border-slate-400'
                                            }`}>
                                            {enableCode && <Check className="w-4 h-4 text-white" />}
                                        </div>
                                    </div>
                                    <div className="flex-1">
                                        <p className={`font-bold transition-colors ${enableCode ? 'text-primary-foreground' : 'text-slate-300'}`}>
                                            Enable Join by INVITE
                                        </p>
                                        <p className={`text-xs font-semibold mt-1 transition-colors ${enableCode ? 'text-primary/80' : 'text-slate-500'}`}>
                                            Students can join using a 6-digit INVITE code.
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center justify-end gap-4 pt-4">
                                    <button
                                        type="button"
                                        onClick={() => setIsCreateModalOpen(false)}
                                        className="px-6 py-3 text-slate-400 font-bold hover:text-white transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={!newClassName}
                                        className="btn-enterprise-primary px-8 py-3.5 rounded-[18px] font-black hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20 active:scale-95"
                                    >
                                        Create Class
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function OverviewTab({ classes, loading, onCreateClass, refreshClasses, toast, setToast, confirmModal, setConfirmModal }) {
    const [searchTerm, setSearchTerm] = useState('');
    const [isInviteOpen, setIsInviteOpen] = useState(false);
    const [selectedClassForInvite, setSelectedClassForInvite] = useState(null);
    const [inviteEmail, setInviteEmail] = useState('');

    // Edit State
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingClass, setEditingClass] = useState(null);
    const [editClassName, setEditClassName] = useState('');
    const [editEnableCode, setEditEnableCode] = useState(false);

    const handleOpenInvite = (cls) => {
        setSelectedClassForInvite(cls);
        setIsInviteOpen(true);
    };

    const handleEditStart = (cls) => {
        setEditingClass(cls);
        setEditClassName(cls.name);
        setEditEnableCode(cls.is_join_by_code_enabled);
        setIsEditModalOpen(true);
    };

    const handleEditSubmit = async (e) => {
        e.preventDefault();
        try {
            await classroomAPI.updateClass(editingClass.id, {
                name: editClassName,
                is_join_by_code_enabled: editEnableCode
            });
            setToast({ message: 'Classroom updated successfully', type: 'success' });
            setIsEditModalOpen(false);
            refreshClasses();
        } catch (error) {
            setToast({ message: error.response?.data?.error || "Failed to update classroom", type: 'error' });
        }
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

    const stats = [
        { label: 'Total Classes', value: classes.length, icon: School, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
        { label: 'Total Students', value: classes.reduce((sum, c) => sum + (c.student_count || 0), 0), icon: Users, color: 'text-purple-400', bg: 'bg-purple-500/10' },
        { label: 'Active Codes', value: classes.filter(c => c.is_join_by_code_enabled).length, icon: Key, color: 'text-green-400', bg: 'bg-green-500/10' },
        { label: 'Avg Enrollment', value: classes.length > 0 ? Math.round(classes.reduce((sum, c) => sum + (c.student_count || 0), 0) / classes.length) : 0, icon: BarChart3, color: 'text-pink-400', bg: 'bg-pink-500/10' },
    ];

    const filteredClasses = classes.filter(c =>
        c.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="space-y-8">
            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat, i) => {
                    const Icon = stat.icon;
                    return (
                        <div key={i} className="card-enterprise p-6 flex flex-col justify-between h-full bg-[#13161f] border-white/5">
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-sm font-medium text-slate-400">{stat.label}</span>
                                <div className={`p-2 rounded-md ${stat.bg} ${stat.color}`}>
                                    <Icon className="w-4 h-4" />
                                </div>
                            </div>
                            <div>
                                <p className="text-3xl font-bold text-white tracking-tight">{stat.value}</p>
                                <p className="text-xs text-slate-500 mt-1">Updated just now</p>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Main Action Bar */}
            <div className="bg-[#13161f] border border-white/5 p-4 rounded-2xl shadow-sm flex flex-col md:flex-row justify-between items-center gap-4">
                <div className="flex items-center gap-4 flex-1 w-full">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Find a classroom..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2.5 bg-black/20 border border-white/10 rounded-xl text-sm text-white outline-none focus:border-primary/50 focus:ring-4 focus:ring-primary/5 transition-all placeholder:text-slate-600"
                        />
                    </div>
                    <button
                        onClick={refreshClasses}
                        className="p-2.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all"
                    >
                        <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
                <button
                    onClick={onCreateClass}
                    className="w-full md:w-auto btn-enterprise-primary px-6 py-2.5 rounded-xl flex items-center justify-center gap-2 hover:bg-primary/90 transition-all font-bold text-sm"
                >
                    <Plus className="w-4 h-4" />
                    New Classroom
                </button>
            </div>

            {/* Classes Grid */}
            <div className="relative min-h-[400px]">
                {loading ? (
                    <div className="flex flex-col items-center justify-center p-20">
                        <div className="animate-spin rounded-full h-12 w-12 border-4 border-white/10 border-t-primary mb-4"></div>
                        <p className="text-slate-400 font-medium">Loading your classrooms...</p>
                    </div>
                ) : classes.length === 0 ? (
                    <div className="text-center py-24 bg-black/20 border-2 border-dashed border-white/10 rounded-3xl">
                        <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
                            <School className="w-10 h-10 text-slate-600" />
                        </div>
                        <h3 className="text-xl font-bold mb-2 text-white">No classrooms found</h3>
                        <p className="text-slate-500 mb-8 max-w-xs mx-auto">Build your first virtual classroom to start engaging with students.</p>
                        <button
                            onClick={onCreateClass}
                            className="text-primary font-bold hover:underline inline-flex items-center gap-2"
                        >
                            <Plus className="w-4 h-4" />
                            Create a Class Now
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {filteredClasses.length > 0 ? (
                            filteredClasses.map((cls) => (
                                <ClassCard
                                    key={cls.id}
                                    cls={cls}
                                    refresh={refreshClasses}
                                    setToast={setToast}
                                    setConfirmModal={setConfirmModal}
                                    onInvite={handleOpenInvite}
                                    onEdit={handleEditStart}
                                />
                            ))
                        ) : (
                            <div className="col-span-full py-12 text-center text-slate-500">
                                <p>No classrooms found matching "{searchTerm}"</p>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Global Invite Student Modal */}
            {isInviteOpen && selectedClassForInvite && (
                <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/80 backdrop-blur-sm cursor-default" onClick={() => setIsInviteOpen(false)}>
                    <div className="bg-[#0f111a] border border-white/10 p-8 rounded-2xl w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200 ring-1 ring-white/10" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                                <Mail className="w-5 h-5" />
                            </div>
                            <div>
                                <h3 className="font-bold text-lg text-white">Invite Student</h3>
                                <p className="text-xs text-slate-400">To {selectedClassForInvite.name}</p>
                            </div>
                        </div>

                        <form onSubmit={handleInviteSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">Student Email</label>
                                <input
                                    type="email"
                                    value={inviteEmail}
                                    onChange={(e) => setInviteEmail(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 focus:border-primary/50 focus:ring-4 focus:ring-primary/10 outline-none transition-all placeholder:text-slate-600 text-sm text-white"
                                    placeholder="student@example.com"
                                    required
                                />
                            </div>
                            <div className="flex justify-end gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setIsInviteOpen(false)}
                                    className="px-4 py-2 text-sm font-semibold rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="bg-primary text-white px-6 py-2 text-sm rounded-xl font-bold hover:bg-primary/90 shadow-lg shadow-primary/25 transition-all"
                                >
                                    Send Invite
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit Class Modal - Matches Image 1 UI */}
            {isEditModalOpen && editingClass && (
                <div className="fixed inset-0 z-[120] flex items-center justify-center p-4">
                    <div
                        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-300"
                        onClick={() => setIsEditModalOpen(false)}
                    />
                    <div className="relative bg-card border border-border rounded-[32px] w-full max-w-md overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
                        <div className="p-10">
                            <div className="flex justify-between items-start mb-2">
                                <h2 className="text-[28px] font-black tracking-tight leading-tight">
                                    Edit Classroom
                                </h2>
                            </div>
                            <p className="text-muted-foreground font-semibold mb-8">
                                Update your classroom settings.
                            </p>

                            <form onSubmit={handleEditSubmit} className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-foreground tracking-wide uppercase ml-1">
                                        Classroom Name
                                    </label>
                                    <input
                                        type="text"
                                        value={editClassName}
                                        onChange={(e) => setEditClassName(e.target.value)}
                                        className="w-full px-5 py-4 bg-secondary border border-border rounded-2xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:bg-card focus:border-primary/20 transition-all text-foreground font-semibold placeholder:text-muted-foreground"
                                        required
                                    />
                                </div>

                                <div
                                    className={`p-5 rounded-2xl border transition-all flex items-start gap-4 cursor-pointer group ${editEnableCode
                                        ? 'bg-indigo-50/50 border-indigo-100 dark:bg-indigo-900/20 dark:border-indigo-800'
                                        : 'bg-secondary/50 border-border hover:bg-secondary'
                                        }`}
                                    onClick={() => setEditEnableCode(!editEnableCode)}
                                >
                                    <div className="mt-1">
                                        <div className={`w-6 h-6 rounded-md border-2 transition-all flex items-center justify-center ${editEnableCode
                                            ? 'bg-indigo-600 border-indigo-600'
                                            : 'bg-card border-border group-hover:border-foreground/20'
                                            }`}>
                                            {editEnableCode && <Check className="w-4 h-4 text-white" />}
                                        </div>
                                    </div>
                                    <div className="flex-1">
                                        <p className={`font-bold transition-colors ${editEnableCode ? 'text-indigo-900 dark:text-indigo-100' : 'text-foreground'}`}>
                                            Enable Join by INVITE
                                        </p>
                                        <p className={`text-xs font-semibold mt-1 transition-colors ${editEnableCode ? 'text-indigo-500' : 'text-muted-foreground'}`}>
                                            Students can join using a 6-digit INVITE code.
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center justify-end gap-4 pt-4">
                                    <button
                                        type="button"
                                        onClick={() => setIsEditModalOpen(false)}
                                        className="px-6 py-3 text-muted-foreground font-bold hover:text-foreground transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="bg-indigo-600 text-white px-8 py-3.5 rounded-[18px] font-black hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 active:scale-95"
                                    >
                                        Save Changes
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function ClassCard({ cls, refresh, setToast, setConfirmModal, onInvite, onEdit }) {
    const [copied, setCopied] = useState(false);

    const copyCode = () => {
        navigator.clipboard.writeText(cls.access_code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="card-enterprise p-6 h-full flex flex-col justify-between group hover:shadow-md transition-all bg-[#13161f] border-white/5">
            <div className="mb-6">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3 className="text-lg font-bold text-white leading-tight mb-1 group-hover:text-primary transition-colors">{cls.name}</h3>
                        <p className="text-sm text-slate-400">{cls.student_count || 0} Students Enrolled</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center text-slate-400">
                        <School className="w-5 h-5" />
                    </div>
                </div>

                <div className="space-y-4">
                    {cls.is_join_by_code_enabled ? (
                        <div className="bg-black/30 p-3 rounded-md border border-white/10 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Key className="w-4 h-4 text-slate-500" />
                                <code className="text-lg font-mono font-bold text-primary">{cls.access_code}</code>
                            </div>
                            <button
                                onClick={copyCode}
                                className="p-2 hover:bg-white/5 rounded-md text-slate-500 hover:text-white transition-colors"
                                title="Copy Code"
                            >
                                {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                            </button>
                        </div>
                    ) : (
                        <div className="bg-white/5 p-3 rounded-md border border-dashed border-white/10 flex items-center gap-2 text-slate-500 text-sm">
                            <Key className="w-4 h-4" />
                            <span>Manual Enrollment Only</span>
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-3 pt-2">
                        <button
                            onClick={() => onInvite(cls)}
                            className="col-span-2 w-full py-2 flex items-center justify-center gap-2 bg-primary/10 text-primary border border-primary/20 hover:bg-primary hover:text-white rounded-md text-sm font-medium transition-colors shadow-sm"
                        >
                            <Mail className="w-4 h-4" />
                            Invite Students
                        </button>
                        <button
                            onClick={() => onEdit(cls)}
                            className="py-2 flex items-center justify-center gap-2 bg-transparent border border-white/10 hover:bg-white/5 rounded-md text-sm font-medium text-slate-300 hover:text-white transition-colors"
                        >
                            Configure
                        </button>
                        <button
                            onClick={() => {
                                setConfirmModal({
                                    isOpen: true,
                                    title: 'Confirm deletion',
                                    message: `Delete ${cls.name} classroom permanently?`,
                                    variant: 'danger',
                                    onConfirm: () => {
                                        classroomAPI.deleteClass(cls.id)
                                            .then(() => {
                                                setToast({ message: 'Class deleted successfully', type: 'success' });
                                                refresh();
                                            })
                                            .catch(() => setToast({ message: 'Failed to delete class', type: 'error' }));
                                    }
                                });
                            }}
                            className="py-2 flex items-center justify-center gap-2 bg-transparent border border-red-500/20 text-red-400 hover:bg-red-500/10 rounded-md text-sm font-medium transition-colors"
                        >
                            Archive
                        </button>
                    </div>
                </div>
            </div>

            <LeaveRequestsList classId={cls.id} showToast={setToast} />
        </div>
    );
}

function LeaveRequestsList({ classId, showToast }) {
    const [requests, setRequests] = useState([]);

    useEffect(() => {
        if (classId) loadRequests();
    }, [classId]);

    const loadRequests = async () => {
        try {
            const data = await classroomAPI.getLeaveRequests(classId);
            // console.log(`Requests for ${classId}:`, data);
            setRequests(data);
        } catch (e) {
            console.error(`Failed to load requests for ${classId}:`, e);
        }
    };

    const handleRespond = async (studentId, action) => {
        try {
            await classroomAPI.respondToLeaveRequest(classId, studentId, action);
            loadRequests(); // Refresh
            showToast({ message: `Request ${action}ed successfully`, type: 'success' });
        } catch (e) {
            showToast({ message: 'Failed to process request', type: 'error' });
        }
    };

    if (!requests || requests.length === 0) return null;

    return (
        <div className="bg-yellow-500/5 border-t border-yellow-500/10 p-4">
            <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></div>
                <h4 className="text-xs font-bold text-yellow-500 uppercase tracking-wider">
                    Pending Requests ({requests.length})
                </h4>
            </div>
            <div className="space-y-2">
                {requests.map(req => (
                    <div key={req.id} className="bg-black/20 p-3 rounded-xl border border-yellow-500/20 shadow-sm flex justify-between items-center group">
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-white/5 flex items-center justify-center text-[10px] font-bold text-slate-400">
                                {req.student_name ? req.student_name.charAt(0) : '?'}
                            </div>
                            <span className="text-sm font-semibold text-slate-200">{req.student_name}</span>
                        </div>
                        <div className="flex gap-1 opacity-100 transition-opacity">
                            <button
                                onClick={() => handleRespond(req.student, 'approve')}
                                className="px-3 py-1 bg-green-500/10 hover:bg-green-500/20 text-green-400 text-xs font-bold rounded-lg transition-colors border border-green-500/20"
                            >
                                Approve
                            </button>
                            <button
                                onClick={() => handleRespond(req.student, 'reject')}
                                className="px-3 py-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-bold rounded-lg transition-colors border border-red-500/20"
                            >
                                Reject
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function StudentInsightsTab({ classrooms, loading }) {
    const [selectedStudent, setSelectedStudent] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedClass, setSelectedClass] = useState('all');
    const [detailedClassrooms, setDetailedClassrooms] = useState([]);
    const [loadingDetails, setLoadingDetails] = useState(false);

    // Fetch detailed info (with students) for each classroom
    useEffect(() => {
        const fetchDetails = async () => {
            // removed parent loading
            if (loading) return;
            if (!classrooms || classrooms.length === 0) {
                setDetailedClassrooms([]);
                return;
            }

            setLoadingDetails(true);
            try {
                // Fetch details for all classrooms in parallel
                // This gets the 'students' array which is not present in the list view
                const promises = classrooms.map(c => classroomAPI.getClassDetails(c.id));
                const results = await Promise.all(promises);
                setDetailedClassrooms(results);
            } catch (error) {
                console.error("Failed to fetch classroom details:", error);
                // Fallback to basic info if fail, though students won't be there
                setDetailedClassrooms(classrooms);
            } finally {
                setLoadingDetails(false);
            }
        };

        fetchDetails();
    }, [classrooms, loading]);

    // Aggregate all students from all detailed classes
    const allStudents = detailedClassrooms.reduce((acc, classroom) => {
        if (classroom.students) {
            classroom.students.forEach(student => {
                // Avoid duplicates if student is in multiple classes
                if (!acc.find(s => s.id === student.id)) {
                    acc.push({
                        ...student,
                        classroomName: classroom.name,
                        classroomId: classroom.id // Helpful for filtering
                    });
                }
            });
        }
        return acc;
    }, []);

    const filteredStudents = allStudents.filter(student => {
        const matchesSearch = (student.username?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
            (student.email?.toLowerCase() || '').includes(searchTerm.toLowerCase());
        const matchesClass = selectedClass === 'all' || student.classroomName === selectedClass;
        return matchesSearch && matchesClass;
    });

    if (loading || loadingDetails) {
        return (
            <div className="flex flex-col items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
                <p className="text-muted-foreground">Loading student data...</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-[#13161f] p-4 rounded-xl border border-white/5">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
                    <input
                        type="text"
                        placeholder="Search students..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 bg-black/20 border border-white/10 rounded-lg text-sm text-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none placeholder:text-slate-600"
                    />
                </div>
                <select
                    value={selectedClass}
                    onChange={(e) => setSelectedClass(e.target.value)}
                    className="w-full md:w-auto px-4 py-2 bg-black/20 border border-white/10 rounded-lg text-sm text-white outline-none focus:ring-2 focus:ring-primary"
                >
                    <option value="all" className="bg-card text-foreground">All Classrooms</option>
                    {classrooms.map(c => (
                        <option key={c.id} value={c.name} className="bg-card text-foreground">{c.name}</option>
                    ))}
                </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredStudents.length > 0 ? (
                    filteredStudents.map(student => (
                        <div key={student.id} className="bg-[#13161f] border border-white/5 rounded-xl p-6 hover:shadow-md transition-all cursor-pointer group" onClick={() => setSelectedStudent(student)}>
                            <div className="flex items-start justify-between mb-4">
                                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold text-lg group-hover:bg-primary group-hover:text-white transition-colors">
                                    {student.full_name ? student.full_name[0].toUpperCase() : (student.username?.[0]?.toUpperCase() || 'S')}
                                </div>
                                <div className="p-2 bg-white/5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Brain className="w-4 h-4 text-primary" />
                                </div>
                            </div>
                            <h3 className="font-bold text-lg text-white mb-1">{student.full_name || student.username}</h3>
                            <p className="text-sm text-slate-400 mb-4">{student.email}</p>
                            <div className="flex items-center justify-between text-xs text-slate-500 pt-4 border-t border-white/5">
                                <span className="flex items-center gap-1">
                                    <School className="w-3 h-3" />
                                    {student.classroomName}
                                </span>
                                <span className="flex items-center gap-1 text-primary font-medium">
                                    View DNA <Brain className="w-3 h-3" />
                                </span>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="col-span-full py-12 text-center border-2 border-dashed border-white/10 rounded-xl bg-white/5">
                        <div className="w-16 h-16 bg-black/20 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm">
                            <Users className="w-8 h-8 text-slate-600" />
                        </div>
                        <p className="text-slate-400 font-medium">No students found matching your filters.</p>
                        {allStudents.length === 0 && (
                            <p className="text-xs text-slate-500 mt-2">Try inviting students to your classrooms first.</p>
                        )}
                    </div>
                )}
            </div>

            {selectedStudent && (
                <StudentLearningDNAModal
                    student={{
                        id: selectedStudent.id,
                        name: selectedStudent.full_name || selectedStudent.username,
                        email: selectedStudent.email
                    }}
                    onClose={() => setSelectedStudent(null)}
                />
            )}
        </div>
    );
}
