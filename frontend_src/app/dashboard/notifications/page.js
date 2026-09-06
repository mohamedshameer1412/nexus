'use client';

import { useState, useEffect } from 'react';
import { notificationAPI, classroomAPI } from '@/lib/api';
import { Check, X, Bell, UserPlus, BookOpen, Clock, Loader2, AlertCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import Toast from '@/components/ui/Toast';

export default function NotificationsPage() {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(null);
    const [toast, setToast] = useState(null);

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            const response = await notificationAPI.getAll();
            // Handle pagination
            const data = response.results ? response.results : (Array.isArray(response) ? response : []);
            setNotifications(data);

            // Mark all as read when opening page (only if there are unread items)
            if (data.some(n => !n.is_read)) {
                await notificationAPI.markAllRead();
            }
        } catch (error) {
            console.error("Failed to fetch notifications", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchNotifications();
    }, []);


    const handleClassroomInvite = async (notificationId, inviteId, action) => {
        setActionLoading(notificationId);
        try {
            // We need to implement classroomAPI.respondToInvite(inviteId, action)
            setToast({ message: `Invites logic: ${action}ed invite ${inviteId}`, type: 'info' });
            setNotifications(prev => prev.map(n =>
                n.id === notificationId
                    ? { ...n, actionTaken: action }
                    : n
            ));
        } catch (error) {
            setToast({ message: 'Action failed', type: 'error' });
        } finally {
            setActionLoading(null);
        }
    };

    const getIcon = (type) => {
        switch (type) {
            case 'classroom_invite': return <BookOpen className="w-5 h-5 text-purple-500" />;
            case 'quiz_assigned': return <Clock className="w-5 h-5 text-orange-500" />;
            default: return <Bell className="w-5 h-5 text-gray-500" />;
        }
    };

    return (
        <div className="max-w-3xl mx-auto space-y-6 animate-fade-in p-6">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Notifications</h1>
                    <p className="text-muted-foreground">Manage your requests and alerts.</p>
                </div>
                <button
                    onClick={fetchNotifications}
                    className="p-2 hover:bg-secondary rounded-full transition-colors"
                >
                    <Clock className="w-5 h-5 text-muted-foreground" />
                </button>
            </header>

            <div className="space-y-4">
                {loading ? (
                    <div className="text-center py-12">
                        <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
                        <p className="mt-2 text-muted-foreground">Loading notifications...</p>
                    </div>
                ) : notifications.length === 0 ? (
                    <div className="text-center py-16 bg-card border border-dashed border-border rounded-xl">
                        <Bell className="w-12 h-12 mx-auto text-muted-foreground/30 mb-4" />
                        <h3 className="text-lg font-medium">All caught up!</h3>
                        <p className="text-muted-foreground">No new notifications at this time.</p>
                    </div>
                ) : (
                    notifications.map(noti => (
                        <div
                            key={noti.id}
                            className={`
                                relative p-5 bg-card border rounded-xl transition-all hover:shadow-md
                                ${!noti.is_read ? 'border-primary/50 bg-primary/5' : 'border-border'}
                            `}
                        >
                            <div className="flex gap-4">
                                <div className={`mt-1 p-2 rounded-full bg-secondary h-fit`}>
                                    {getIcon(noti.notification_type)}
                                </div>
                                <div className="flex-1 space-y-1">
                                    <div className="flex justify-between items-start">
                                        <h4 className="font-semibold text-foreground">{noti.title}</h4>
                                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                                            {formatDistanceToNow(new Date(noti.created_at), { addSuffix: true })}
                                        </span>
                                    </div>
                                    <p className="text-sm text-foreground/80 leading-relaxed">
                                        {noti.message}
                                    </p>

                                    {/* Link Request Result State (Removed) */}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}
        </div>
    );
}
