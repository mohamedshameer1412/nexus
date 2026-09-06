'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { classroomAPI } from '@/lib/api';
import { Save, Trash2, Key, RefreshCw } from 'lucide-react';
import ConfirmationModal from '@/components/ui/ConfirmationModal';

export default function SettingsTab({ classroom, onUpdate, setToast }) {
    const router = useRouter();
    const [name, setName] = useState(classroom.name || '');
    const [subject, setSubject] = useState(classroom.subject || '');
    const [loading, setLoading] = useState(false);
    const [confirmModal, setConfirmModal] = useState({ isOpen: false });

    // Ensure access_code is defined and handle the boolean correctly
    const [joinByCode, setJoinByCode] = useState(classroom.is_join_by_code_enabled ?? true);

    const handleSave = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await classroomAPI.updateClassroom(classroom.id, {
                name,
                subject,
                is_join_by_code_enabled: joinByCode
            });
            setToast({ message: 'Classroom settings updated', type: 'success' });
            if (onUpdate) onUpdate();
        } catch (error) {
            setToast({ message: 'Failed to update settings', type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = () => {
        setConfirmModal({
            isOpen: true,
            title: 'Delete Classroom?',
            message: 'This action cannot be undone. All data, including student progress and quizzes, will be permanently lost.',
            variant: 'danger',
            onConfirm: async () => {
                try {
                    await classroomAPI.deleteClassroom(classroom.id);
                    router.push('/dashboard/classrooms');
                } catch (error) {
                    setToast({ message: 'Failed to delete classroom', type: 'error' });
                }
            }
        });
    };

    const handleRegenerateCode = async () => {
        try {
            // Assuming an API endpoint exists, or just updating invites. 
            // For now, let's just show a toast as this might need backend support not visible here.
            setToast({ message: 'Code regeneration not implemented yet', type: 'info' });
        } catch (error) {
            console.error(error);
        }
    };

    return (
        <div className="max-w-2xl space-y-8 animate-in fade-in duration-500">
            {/* General Settings Card */}
            <div className="bg-card p-8 rounded-3xl border border-border shadow-sm">
                <h3 className="text-xl font-bold text-foreground mb-6">General Settings</h3>
                <form onSubmit={handleSave} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Classroom Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full bg-muted/50 border border-border rounded-xl px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
                            required
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Subject / Topic</label>
                        <input
                            type="text"
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                            className="w-full bg-muted/50 border border-border rounded-xl px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
                        />
                    </div>

                    <div className="pt-4 border-t border-border">
                        <div className="flex items-center justify-between">
                            <div>
                                <h4 className="font-bold text-foreground">Join by Code</h4>
                                <p className="text-sm text-muted-foreground">Allow students to join using the access code.</p>
                            </div>

                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={joinByCode}
                                    onChange={(e) => setJoinByCode(e.target.checked)}
                                    className="sr-only peer"
                                />
                                <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                            </label>
                        </div>

                        {joinByCode && (
                            <div className="mt-4 p-4 bg-muted/30 rounded-xl border border-border flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-primary/10 rounded-lg text-primary">
                                        <Key className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold text-muted-foreground uppercase">Access Code</p>
                                        <p className="text-lg font-mono font-bold text-foreground tracking-wider">{classroom.access_code}</p>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    onClick={handleRegenerateCode}
                                    className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
                                    title="Regenerate Code"
                                >
                                    <RefreshCw className="w-4 h-4" />
                                </button>
                            </div>
                        )}
                    </div>

                    <div className="flex justify-end pt-4">
                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-enterprise-primary px-8 py-3 flex items-center gap-2"
                        >
                            {loading ? 'Saving...' : (
                                <>
                                    <Save className="w-4 h-4" />
                                    Save Changes
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>

            {/* Danger Zone */}
            <div className="bg-red-500/5 p-8 rounded-3xl border border-red-500/10">
                <h3 className="text-xl font-bold text-red-500 mb-2">Danger Zone</h3>
                <p className="text-red-400/70 text-sm mb-6">Irreversible actions for this classroom.</p>

                <div className="flex items-center justify-between">
                    <div>
                        <h4 className="font-bold text-red-400">Delete Classroom</h4>
                        <p className="text-sm text-red-400/60">Permanently remove this class and all its data.</p>
                    </div>
                    <button
                        onClick={handleDelete}
                        className="px-6 py-2.5 bg-red-500 text-white rounded-xl font-bold hover:bg-red-600 transition-colors shadow-lg shadow-red-900/20 flex items-center gap-2"
                    >
                        <Trash2 className="w-4 h-4" />
                        Delete Class
                    </button>
                </div>
            </div>

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
