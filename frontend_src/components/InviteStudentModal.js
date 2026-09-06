'use client';

import { useState } from 'react';
import { X, Copy, Check, Mail, Share2, Key } from 'lucide-react';
import { classroomAPI } from '@/lib/api';

export default function InviteStudentModal({ classroomId, onClose, onSuccess, setToast }) {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [copied, setCopied] = useState(false);

    // In a real app, this would be fetched or passed down. Assuming code is available or fetched.
    // For now, let's fetch the classroom details to get the code if not passed?
    // removed parent connection logic and comments
    // For now, I'll fetch the classroom details again inside here OR assume the user has the code.
    // Better yet, let's just implement the email invite and a generic "copy link" feature.

    // Wait, the design in `ClassroomDetailsPage` showed the code. I can just pass it.
    // I'll update `ClassroomDetailsPage` to pass `classroom.access_code` too.

    const handleInvite = async (e) => {
        e.preventDefault();
        if (!email) return;

        setLoading(true);
        try {
            await classroomAPI.addStudent(classroomId, { email });
            setToast({ message: 'Invitation sent successfully', type: 'success' });
            setEmail('');
            if (onSuccess) onSuccess();
            onClose();
        } catch (error) {
            console.error('Invite failed:', error);
            setToast({
                message: error.response?.data?.error || 'Failed to send invitation',
                type: 'error'
            });
        } finally {
            setLoading(false);
        }
    };

    const handleCopyLink = () => {
        // Assuming a standard invite link format
        const link = `${window.location.origin}/join/${classroomId}`;
        navigator.clipboard.writeText(link);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        setToast({ message: 'Invite link copied to clipboard', type: 'success' });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-[#0F1117] border border-white/10 rounded-2xl shadow-2xl scale-95 animate-in zoom-in-95 duration-200">
                <div className="flex items-center justify-between p-6 border-b border-white/5">
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        <UserPlus className="w-5 h-5 text-indigo-400" />
                        Invite Students
                    </h3>
                    <button
                        onClick={onClose}
                        className="p-2 text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Invite Link Section */}
                    <div className="space-y-3">
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Share Invite Link</label>
                        <div className="flex items-center gap-2">
                            <div className="flex-1 bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-sm text-slate-300 truncate font-mono">
                                {typeof window !== 'undefined' ? `${window.location.origin}/join/${classroomId}` : `.../join/${classroomId}`}
                            </div>
                            <button
                                onClick={handleCopyLink}
                                className="p-3 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20 rounded-xl transition-all active:scale-95"
                                title="Copy Link"
                            >
                                {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                            </button>
                        </div>
                    </div>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-white/10"></div>
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-[#0F1117] px-2 text-slate-500 font-bold">Or invite by email</span>
                        </div>
                    </div>

                    {/* Email Invite Form */}
                    <form onSubmit={handleInvite} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Student Email</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="student@example.com"
                                    className="w-full bg-black/30 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all font-medium"
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold shadow-lg shadow-indigo-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <>
                                    <Send className="w-5 h-5" />
                                    Send Invitation
                                </>
                            )}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

import { UserPlus, Send } from 'lucide-react';
