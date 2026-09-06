'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    BookOpen,
    Upload,
    Plus,
    FileText,
    MoreVertical,
    Play,
    CheckCircle,
    Clock,
    Brain,
    Loader2,
    Trash2,
    Edit,
    AlertTriangle,
    X,
    Search,
    Video,
    Link as LinkIcon,
    Download,
    Share2,
    ExternalLink
} from 'lucide-react';
import { learningAPI } from '../../../lib/api';

export default function LearningDashboard() {
    const router = useRouter();
    const [user, setUser] = useState(null);
    const [modules, setModules] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deletingId, setDeletingId] = useState(null);
    const [editingModule, setEditingModule] = useState(null);
    const [editForm, setEditForm] = useState({ title: '', description: '' });
    const [activeMenuId, setActiveMenuId] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterType, setFilterType] = useState('all');

    useEffect(() => {
        const userData = localStorage.getItem('user');
        if (userData) {
            setUser(JSON.parse(userData));
            fetchModules();
        }
    }, []);

    const fetchModules = async () => {
        try {
            const data = await learningAPI.getModules();
            setModules(Array.isArray(data) ? data : data?.results || []);
        } catch (error) {
            console.error('Failed to fetch modules:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (e, id) => {
        e.stopPropagation();
        setDeletingId(id);
        setActiveMenuId(null);
    };

    const confirmDelete = async () => {
        try {
            await learningAPI.deleteModule(deletingId);
            setModules(modules.filter(m => m.id !== deletingId));
            setDeletingId(null);
        } catch (error) {
            console.error('Failed to delete module:', error);
            alert('Failed to delete module. Please try again.');
        }
    };

    const handleEdit = (e, module) => {
        e.stopPropagation();
        setEditingModule(module);
        setEditForm({
            title: module.title,
            description: module.description || ''
        });
        setActiveMenuId(null);
    };

    const confirmEdit = async () => {
        try {
            const formData = new FormData();
            formData.append('title', editForm.title);
            formData.append('description', editForm.description);

            const updatedModule = await learningAPI.updateModule(editingModule.id, formData);
            setModules(modules.map(m => m.id === updatedModule.id ? updatedModule : m));
            setEditingModule(null);
        } catch (error) {
            console.error('Failed to update module:', error);
            alert('Failed to update module. Please try again.');
        }
    };

    if (loading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    // Simple filter logic
    const filteredModules = modules.filter(m => {
        const matchesSearch = (m.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
            (m.description || '').toLowerCase().includes(searchQuery.toLowerCase());
        const matchesType = filterType === 'all' || m.type === filterType;
        return matchesSearch && matchesType;
    });

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Enterprise Header */}
            <div className="relative overflow-hidden bg-card border border-border rounded-3xl shadow-xl w-full">
                {/* Background Gradient Mesh */}
                <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] pointer-events-none opacity-60" />
                <div className="absolute bottom-0 left-0 translate-y-1/2 -translate-x-1/2 w-[400px] h-[400px] bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none opacity-40" />

                <div className="relative p-8 lg:p-10 flex flex-col lg:flex-row lg:items-end justify-between gap-6 z-10">
                    <div>
                        <h1 className="text-4xl font-black text-white tracking-tight leading-tight mb-2">
                            Learning <span className="text-primary">Hub</span>
                        </h1>
                        <p className="text-lg text-muted-foreground font-medium max-w-xl">
                            Access your intelligent study materials, AI-generated summaries, and quizzes.
                        </p>
                    </div>
                    {user?.role === 'teacher' && (
                        <button
                            onClick={() => router.push('/dashboard/learning/create')}
                            className="btn-enterprise-primary px-6 py-3 flex items-center justify-center gap-2 shadow-xl shadow-primary/20 group hover:scale-105 transition-transform"
                        >
                            <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform" />
                            Create Module
                        </button>
                    )}
                </div>
            </div>

            {/* Search Bar Only */}
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between p-1">
                <div className="relative w-full group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground group-focus-within:text-primary transition-colors" />
                    <input
                        type="text"
                        placeholder="Search materials..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full bg-card/50 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all font-medium"
                    />
                </div>
            </div>

            {/* Modules Grid */}
            {filteredModules.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredModules.map((module) => (
                        <div
                            key={module.id}
                            onClick={() => router.push(`/dashboard/learning/${module.id}`)}
                            className="group bg-card hover:bg-white/5 border border-white/5 hover:border-white/10 rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl cursor-pointer relative overflow-hidden"
                        >
                            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full -mr-16 -mt-16 blur-xl group-hover:bg-primary/10 transition-colors" />

                            <div className="flex justify-between items-start mb-4 relative z-10">
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center border transition-colors ${module.processing_status === 'completed'
                                    ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                    : 'bg-amber-500/10 text-amber-500 border-amber-500/20 animate-pulse'
                                    }`}>
                                    {module.type === 'video' ? <Video className="w-6 h-6" /> :
                                        module.type === 'link' ? <LinkIcon className="w-6 h-6" /> :
                                            <FileText className="w-6 h-6" />}
                                </div>
                                <div className="flex gap-2">
                                    {module.processing_status === 'processing' && (
                                        <span className="px-2 py-1 rounded-md bg-amber-500/10 text-amber-500 text-[10px] font-bold uppercase border border-amber-500/20 flex items-center gap-1">
                                            <Loader2 className="w-3 h-3 animate-spin" /> Processing
                                        </span>
                                    )}
                                    <button
                                        onClick={(e) => handleEdit(e, module)}
                                        className="p-2 text-slate-500 hover:text-primary hover:bg-primary/10 rounded-lg transition-colors z-20"
                                    >
                                        <Edit className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={(e) => handleDelete(e, module.id)}
                                        className="p-2 text-slate-500 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors z-20"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            <h3 className="text-xl font-bold text-white mb-2 line-clamp-1 group-hover:text-primary transition-colors">
                                {module.title}
                            </h3>
                            <p className="text-slate-400 text-sm mb-6 line-clamp-2 min-h-[40px]">
                                {module.description || 'No description provided'}
                            </p>

                            <div className="flex items-center gap-4 text-xs font-bold text-slate-500 uppercase tracking-wider border-t border-white/5 pt-4">
                                <span className="flex items-center gap-1.5">
                                    <Clock className="w-3.5 h-3.5" />
                                    {new Date(module.created_at).toLocaleDateString('en-GB')}
                                </span>
                                <span className="flex items-center gap-1.5">
                                    <Brain className="w-3.5 h-3.5" />
                                    AI Ready
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-20 text-center bg-card/30 border border-white/5 rounded-3xl border-dashed">
                    <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4 text-slate-500">
                        <BookOpen className="w-8 h-8 opacity-50" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">No Material Found</h3>
                    <p className="text-slate-400 max-w-sm mx-auto mb-6">
                        We couldn't find any learning materials matching your criteria.
                    </p>
                    {user?.role === 'teacher' && (
                        <button
                            onClick={() => router.push('/dashboard/learning/create')}
                            className="btn-enterprise-primary px-6 py-2.5"
                        >
                            Create First Module
                        </button>
                    )}
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {deletingId && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="w-full max-w-md bg-[#0F1117] border border-red-500/20 rounded-2xl shadow-2xl scale-95 animate-in zoom-in-95 duration-200">
                        <div className="p-6 text-center">
                            <div className="w-16 h-16 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
                                <AlertTriangle className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-bold text-white mb-2">Delete Module?</h3>
                            <p className="text-slate-400 mb-6">
                                This action cannot be undone. All AI-generated content associated with this module will be lost.
                            </p>
                            <div className="flex gap-3 justify-center">
                                <button
                                    onClick={() => setDeletingId(null)}
                                    className="px-6 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-xl font-bold transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={confirmDelete}
                                    className="px-6 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-xl font-bold transition-colors shadow-lg shadow-red-900/20"
                                >
                                    Delete Forever
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Module Modal */}
            {editingModule && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="w-full max-w-md bg-[#0F1117] border border-white/5 rounded-2xl shadow-2xl scale-95 animate-in zoom-in-95 duration-200">
                        <div className="p-8">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="w-10 h-10 bg-primary/10 text-primary rounded-xl flex items-center justify-center">
                                    <Edit className="w-5 h-5" />
                                </div>
                                <h3 className="text-xl font-bold text-white">Edit Module</h3>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-2 block">Title</label>
                                    <input
                                        type="text"
                                        value={editForm.title}
                                        onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                                        className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-bold"
                                        placeholder="Module Title"
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-2 block">Description</label>
                                    <textarea
                                        value={editForm.description}
                                        onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                                        className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all h-32 resize-none font-medium"
                                        placeholder="Brief description..."
                                    />
                                </div>
                            </div>

                            <div className="flex gap-3 mt-8">
                                <button
                                    onClick={() => setEditingModule(null)}
                                    className="flex-1 px-6 py-3 bg-white/5 hover:bg-white/10 text-white rounded-xl font-bold transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={confirmEdit}
                                    className="flex-1 px-6 py-3 bg-primary hover:bg-primary/90 text-white rounded-xl font-bold transition-colors shadow-lg shadow-primary/20"
                                >
                                    Save Changes
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
