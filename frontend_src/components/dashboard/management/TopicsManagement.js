'use client';

import { useState, useEffect } from 'react';
import { quizAPI } from '@/lib/api';
import {
    Plus,
    Search,
    Loader2,
    BookOpen,
    Edit,
    Trash2,
    Layers,
    Link,
    ArrowLeft,
    Check,
    X,
    CheckSquare
} from 'lucide-react';
import AlertModal from '../../ui/AlertModal';

export default function TopicsManagement() {
    const [topics, setTopics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingTopic, setEditingTopic] = useState(null);
    const [selectedTopics, setSelectedTopics] = useState([]);
    const [isSelectionMode, setIsSelectionMode] = useState(false); // Enterprise Selection Mode
    const [formData, setFormData] = useState({ name: '', description: '' });

    // Subtopic State
    const [subtopics, setSubtopics] = useState([]);
    const [managingTopic, setManagingTopic] = useState(null); // The topic whose subtopics we are managing
    const [editingSubtopic, setEditingSubtopic] = useState(null); // The subtopic we are editing
    const [subtopicView, setSubtopicView] = useState('list'); // 'list' or 'form'
    const [subtopicForm, setSubtopicForm] = useState({ name: '', description: '', prerequisite_subtopics: [] });

    const [alertConfig, setAlertConfig] = useState({
        isOpen: false,
        title: '',
        message: '',
        type: 'warning',
        showCancel: false,
        onConfirm: null
    });

    const showAlert = (config) => {
        setAlertConfig({ ...config, isOpen: true });
    };

    const closeAlert = () => {
        setAlertConfig(prev => ({ ...prev, isOpen: false }));
    };

    useEffect(() => {
        fetchTopics();
    }, []);

    const fetchTopics = async () => {
        try {
            const data = await quizAPI.getTopics();
            setTopics(Array.isArray(data) ? data : data.results || []);
        } catch (error) {
            console.error('Error fetching topics:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingTopic) {
                await quizAPI.updateTopic(editingTopic.id, formData);
            } else {
                await quizAPI.createTopic(formData);
            }
            setShowModal(false);
            setEditingTopic(null);
            setFormData({ name: '', description: '' });
            fetchTopics();
        } catch (error) {
            let message = 'Failed to save topic. Please try again.';
            if (error.response?.data) {
                const data = error.response.data;
                if (typeof data === 'string') message = data;
                else if (data.detail) message = data.detail;
                else if (typeof data === 'object') {
                    message = Object.entries(data)
                        .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
                        .join('\n');
                }
            }
            showAlert({
                title: 'Error',
                message: message,
                type: 'error'
            });
        }
    };

    const handleDelete = async (id) => {
        showAlert({
            title: 'Delete Topic?',
            message: 'Are you sure you want to delete this topic? This action cannot be undone.',
            type: 'warning',
            showCancel: true,
            confirmText: 'Delete',
            cancelText: 'Cancel',
            onConfirm: async () => {
                try {
                    await quizAPI.deleteTopic(id);
                    fetchTopics();
                    closeAlert();
                } catch (error) {
                    closeAlert();
                    setTimeout(() => {
                        showAlert({
                            title: 'Error',
                            message: 'Failed to delete topic',
                            type: 'error'
                        });
                    }, 100);
                }
            }
        });
    };

    const handleBulkDelete = () => {
        if (selectedTopics.length === 0) return;

        showAlert({
            title: 'Delete Selected Topics?',
            message: `Are you sure you want to delete ${selectedTopics.length} topics? Linked questions and subtopics will be affected.`,
            type: 'warning',
            showCancel: true,
            confirmText: 'Delete All',
            cancelText: 'Cancel',
            onConfirm: async () => {
                try {
                    await Promise.all(selectedTopics.map(id => quizAPI.deleteTopic(id)));
                    setSelectedTopics([]);
                    setIsSelectionMode(false); // Exit selection mode
                    fetchTopics();
                    closeAlert();
                    setTimeout(() => {
                        showAlert({
                            title: 'Success',
                            message: 'Selected topics deleted successfully',
                            type: 'success'
                        });
                    }, 100);
                } catch (error) {
                    closeAlert();
                    setTimeout(() => {
                        showAlert({
                            title: 'Error',
                            message: 'Failed to delete some topics',
                            type: 'error'
                        });
                    }, 100);
                }
            }
        });
    };

    const toggleSelectTopic = (id) => {
        setSelectedTopics(prev =>
            prev.includes(id) ? prev.filter(tId => tId !== id) : [...prev, id]
        );
    };

    const toggleSelectAll = () => {
        if (selectedTopics.length === filteredTopics.length) {
            setSelectedTopics([]);
        } else {
            setSelectedTopics(filteredTopics.map(t => t.id));
        }
    };

    // Subtopic Management Functions
    const openSubtopicsModal = async (topic) => {
        setManagingTopic(topic);
        setSubtopicView('list');
        setLoading(true);
        try {
            const allSubtopics = await quizAPI.getSubtopics();
            const topicSubtopics = (Array.isArray(allSubtopics) ? allSubtopics : allSubtopics.results || [])
                .filter(st => st.topic === topic.id);
            setSubtopics(topicSubtopics);
        } catch (error) {
            console.error(error);
            showAlert({ title: 'Error', message: 'Failed to fetch subtopics', type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleSubtopicSubmit = async (e) => {
        e.preventDefault();
        try {
            const payload = {
                ...subtopicForm,
                topic: managingTopic.id
            };

            if (editingSubtopic) {
                await quizAPI.updateSubtopic(editingSubtopic.id, payload);
            } else {
                await quizAPI.createSubtopic(payload);
            }

            // Refresh list
            const allSubtopics = await quizAPI.getSubtopics();
            const topicSubtopics = (Array.isArray(allSubtopics) ? allSubtopics : allSubtopics.results || [])
                .filter(st => st.topic === managingTopic.id);
            setSubtopics(topicSubtopics);
            setSubtopicView('list');
            setEditingSubtopic(null);
            setSubtopicForm({ name: '', description: '', prerequisite_subtopics: [] });
            fetchTopics(); // Refresh counts
        } catch (error) {
            console.error(error);
            let message = 'Failed to save subtopic. Please try again.';
            if (error.response?.data) {
                const data = error.response.data;
                if (typeof data === 'string') message = data;
                else if (data.detail) message = data.detail;
                else if (typeof data === 'object') {
                    message = Object.entries(data)
                        .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
                        .join('\n');
                }
            }
            showAlert({ title: 'Error', message: message, type: 'error' });
        }
    };

    const handleDeleteSubtopic = (id) => {
        showAlert({
            title: 'Delete Subtopic?',
            message: 'Are you sure? Questions linked to this subtopic will be unlinked.',
            type: 'warning',
            showCancel: true,
            confirmText: 'Delete',
            cancelText: 'Cancel',
            onConfirm: async () => {
                try {
                    await quizAPI.deleteSubtopic(id);
                    // Refresh
                    const allSubtopics = await quizAPI.getSubtopics();
                    const topicSubtopics = (Array.isArray(allSubtopics) ? allSubtopics : allSubtopics.results || [])
                        .filter(st => st.topic === managingTopic.id);
                    setSubtopics(topicSubtopics);
                    closeAlert();
                    fetchTopics();
                } catch (error) {
                    closeAlert();
                    showAlert({ title: 'Error', message: 'Failed to delete subtopic', type: 'error' });
                }
            }
        });
    };

    const togglePrerequisite = (id) => {
        setSubtopicForm(prev => ({
            ...prev,
            prerequisite_subtopics: prev.prerequisite_subtopics.includes(id)
                ? prev.prerequisite_subtopics.filter(pid => pid !== id)
                : [...prev.prerequisite_subtopics, id]
        }));
    };

    const filteredTopics = topics.filter(t =>
        t.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading && !subtopics.length && !managingTopic) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold">Topics Management</h2>
                    <p className="text-muted-foreground">Manage subject topics and categories</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => {
                            setIsSelectionMode(!isSelectionMode);
                            setSelectedTopics([]);
                        }}
                        className={`px-4 py-2 border rounded-lg flex items-center gap-2 transition-colors ${isSelectionMode
                            ? 'bg-primary/10 border-primary text-primary'
                            : 'bg-card border-border hover:bg-secondary text-muted-foreground'
                            }`}
                    >
                        <CheckSquare className="w-4 h-4" />
                        {isSelectionMode ? 'Cancel Selection' : 'Select'}
                    </button>
                    <button
                        onClick={() => {
                            setEditingTopic(null);
                            setFormData({ name: '', description: '' });
                            setShowModal(true);
                        }}
                        className="bg-primary text-primary-foreground px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-all"
                    >
                        <Plus className="w-5 h-5" />
                        Add Topic
                    </button>
                </div>
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                    type="text"
                    placeholder="Search topics..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
            </div>

            {/* Bulk Actions (Selection Mode) */}
            {isSelectionMode && (
                <div className="bg-secondary/50 border border-border p-4 rounded-xl flex items-center justify-between mb-4 animate-in slide-in-from-top-2">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={filteredTopics.length > 0 && selectedTopics.length === filteredTopics.length}
                                onChange={toggleSelectAll}
                                className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                            />
                            <span className="text-sm font-medium">Select All</span>
                        </div>
                        <div className="h-4 w-px bg-border"></div>
                        <span className="text-sm font-medium text-primary">{selectedTopics.length} Selected</span>
                    </div>
                    {selectedTopics.length > 0 && (
                        <button
                            onClick={handleBulkDelete}
                            className="bg-destructive text-destructive-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-destructive/90 transition-colors flex items-center gap-2"
                        >
                            <Trash2 className="w-4 h-4" />
                            Delete
                        </button>
                    )}
                </div>
            )}

            {/* Old Selection Header removed */}

            {/* Topics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTopics.length > 0 ? (
                    filteredTopics.map((topic) => (
                        <div key={topic.id} className={`bg-card border p-6 rounded-xl transition-all shadow-sm ${selectedTopics.includes(topic.id) ? 'border-primary ring-1 ring-primary' : 'border-border hover:border-primary/50'}`}>
                            <div className="flex justify-between items-start mb-3">
                                <div className="flex items-center gap-3">
                                    {isSelectionMode && (
                                        <div className="animate-in fade-in zoom-in duration-200">
                                            <input
                                                type="checkbox"
                                                checked={selectedTopics.includes(topic.id)}
                                                onChange={(e) => { e.stopPropagation(); toggleSelectTopic(topic.id); }}
                                                className="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer"
                                            />
                                        </div>
                                    )}
                                    <div className="p-2 bg-primary/10 rounded-lg">
                                        <BookOpen className="w-5 h-5 text-primary" />
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => openSubtopicsModal(topic)}
                                        className="p-2 hover:bg-secondary rounded-lg transition-colors text-primary hover:text-primary/80"
                                        title="Manage Subtopics"
                                    >
                                        <Layers className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => {
                                            setEditingTopic(topic);
                                            setFormData({ name: topic.name, description: topic.description || '' });
                                            setShowModal(true);
                                        }}
                                        className="p-2 hover:bg-secondary rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                                    >
                                        <Edit className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(topic.id)}
                                        className="p-2 hover:bg-destructive/10 rounded-lg transition-colors text-destructive"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                            <h3 className="text-lg font-bold mb-2 text-foreground">{topic.name}</h3>
                            <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                                {topic.description || 'No description'}
                            </p>
                            <div className="flex gap-4 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1"><Layers className="w-3 h-3" /> {topic.subtopics_count || 0} Subtopics</span>
                                <span>{topic.questions_count || 0} Questions</span>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="col-span-full text-center py-12 bg-card border border-dashed border-border rounded-xl">
                        <BookOpen className="w-16 h-16 mx-auto text-muted-foreground mb-4 opacity-50" />
                        <p className="text-muted-foreground font-medium">No topics found</p>
                    </div>
                )}
            </div>

            {/* Topic Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="bg-background border border-border p-6 rounded-xl w-full max-w-md shadow-2xl">
                        <h2 className="text-xl font-bold mb-4">
                            {editingTopic ? 'Edit Topic' : 'Create New Topic'}
                        </h2>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Topic Name *</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                    placeholder="e.g., Algebra"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary h-24 resize-none"
                                    placeholder="Brief description..."
                                />
                            </div>
                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="flex-1 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-all"
                                >
                                    {editingTopic ? 'Update' : 'Create'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Subtopics Management Modal */}
            {managingTopic && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-background border border-border rounded-xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
                        {/* Header */}
                        <div className="p-6 border-b border-border flex justify-between items-center bg-muted/20">
                            <div>
                                <h2 className="text-xl font-bold flex items-center gap-2">
                                    <Layers className="w-5 h-5 text-primary" />
                                    {managingTopic.name} <span className="text-muted-foreground font-normal">/ Subtopics</span>
                                </h2>
                            </div>
                            <button onClick={() => setManagingTopic(null)} className="p-2 hover:bg-secondary rounded-lg">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto p-6">
                            {subtopicView === 'list' ? (
                                <div className="space-y-4">
                                    <button
                                        onClick={() => {
                                            setEditingSubtopic(null);
                                            setSubtopicForm({ name: '', description: '', prerequisite_subtopics: [] });
                                            setSubtopicView('form');
                                        }}
                                        className="w-full py-3 border-2 border-dashed border-border rounded-xl flex items-center justify-center gap-2 hover:border-primary/50 hover:bg-secondary/50 transition-all text-muted-foreground hover:text-primary"
                                    >
                                        <Plus className="w-5 h-5" />
                                        Add New Subtopic
                                    </button>

                                    {subtopics.length > 0 ? (
                                        <div className="grid gap-3">
                                            {subtopics.map(sub => (
                                                <div key={sub.id} className="p-4 bg-secondary/30 border border-border rounded-xl flex justify-between items-center group hover:border-primary/30 transition-all">
                                                    <div>
                                                        <h4 className="font-bold flex items-center gap-2">
                                                            {sub.name}
                                                            {sub.prerequisite_names && sub.prerequisite_names.length > 0 && (
                                                                <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-full flex items-center gap-1" title={`Requires: ${sub.prerequisite_names.join(', ')}`}>
                                                                    <Link className="w-3 h-3" />
                                                                    {sub.prerequisite_names.length} Links
                                                                </span>
                                                            )}
                                                        </h4>
                                                        <p className="text-sm text-muted-foreground">{sub.description || 'No description'}</p>
                                                    </div>
                                                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <button
                                                            onClick={() => {
                                                                setEditingSubtopic(sub);
                                                                setSubtopicForm({
                                                                    name: sub.name,
                                                                    description: sub.description || '',
                                                                    prerequisite_subtopics: sub.prerequisite_subtopics || []
                                                                });
                                                                setSubtopicView('form');
                                                            }}
                                                            className="p-2 hover:bg-background rounded-lg text-muted-foreground hover:text-foreground"
                                                        >
                                                            <Edit className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteSubtopic(sub.id)}
                                                            className="p-2 hover:bg-background rounded-lg text-destructive hover:text-destructive/80"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-center py-12 text-muted-foreground">
                                            No subtopics found. Create one to get started!
                                        </div>
                                    )}
                                </div>
                            ) : (
                                /* Form View */
                                <form onSubmit={handleSubtopicSubmit} className="space-y-4">
                                    <button
                                        type="button"
                                        onClick={() => setSubtopicView('list')}
                                        className="text-sm text-muted-foreground flex items-center gap-1 hover:text-foreground mb-4"
                                    >
                                        <ArrowLeft className="w-4 h-4" /> Back to list
                                    </button>

                                    <div>
                                        <label className="block text-sm font-medium mb-2">Subtopic Name *</label>
                                        <input
                                            type="text"
                                            value={subtopicForm.name}
                                            onChange={(e) => setSubtopicForm({ ...subtopicForm, name: e.target.value })}
                                            className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2">Description</label>
                                        <textarea
                                            value={subtopicForm.description}
                                            onChange={(e) => setSubtopicForm({ ...subtopicForm, description: e.target.value })}
                                            className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary h-20 resize-none"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium mb-2">
                                            Prerequisites (Linking)
                                            <span className="block text-xs font-normal text-muted-foreground">Select subtopics that must be learned BEFORE this one.</span>
                                        </label>
                                        <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto p-3 bg-secondary/50 rounded-lg border border-border">
                                            {subtopics
                                                .filter(s => s.id !== editingSubtopic?.id) // Cannot depend on self
                                                .map(sub => (
                                                    <label key={sub.id} className="flex items-center gap-2 cursor-pointer p-2 hover:bg-secondary rounded transition-colors">
                                                        <div className={`w-4 h-4 rounded border flex items-center justify-center ${subtopicForm.prerequisite_subtopics.includes(sub.id) ? 'bg-primary border-primary' : 'border-muted-foreground'}`}>
                                                            {subtopicForm.prerequisite_subtopics.includes(sub.id) && <Check className="w-3 h-3 text-white" />}
                                                        </div>
                                                        <input
                                                            type="checkbox"
                                                            checked={subtopicForm.prerequisite_subtopics.includes(sub.id)}
                                                            onChange={() => togglePrerequisite(sub.id)}
                                                            className="hidden"
                                                        />
                                                        <span className="text-sm">{sub.name}</span>
                                                    </label>
                                                ))}
                                            {subtopics.filter(s => s.id !== editingSubtopic?.id).length === 0 && (
                                                <p className="col-span-2 text-sm text-muted-foreground text-center py-2">No other subtopics available to link.</p>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex gap-3 pt-4">
                                        <button
                                            type="submit" // Main submit
                                            className="w-full py-3 bg-primary text-primary-foreground rounded-lg font-bold hover:bg-primary/90 transition-all"
                                        >
                                            {editingSubtopic ? 'Update Subtopic' : 'Create Subtopic'}
                                        </button>
                                    </div>
                                </form>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Alert Modal */}
            <AlertModal
                isOpen={alertConfig.isOpen}
                onClose={closeAlert}
                onConfirm={alertConfig.onConfirm}
                title={alertConfig.title}
                message={alertConfig.message}
                type={alertConfig.type}
                showCancel={alertConfig.showCancel}
                confirmText={alertConfig.confirmText}
                cancelText={alertConfig.cancelText}
            />
        </div>
    );
}
