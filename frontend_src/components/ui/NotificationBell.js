'use client';

import { useState, useRef, useEffect } from 'react';
import { useNotifications } from '../../hooks/useNotifications';
import { useRouter } from 'next/navigation';

export default function NotificationBell() {
    const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);
    const router = useRouter();

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleNotificationClick = (notification) => {
        if (!notification.is_read) {
            markAsRead(notification.id);
        }
        setIsOpen(false);

        // Navigate based on type or related object
        if (notification.related_object_type === 'quiz_session') {
            router.push(`/dashboard/history`); // Generalized for now
        } else if (notification.related_object_type === 'classroom') {
            router.push('/dashboard/classrooms');
        } else {
            router.push('/dashboard/notifications'); // Default fallback
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 text-muted-foreground hover:bg-secondary rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                aria-label="Notifications"
            >
                {/* Bell Icon */}
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                </svg>

                {unreadCount > 0 && (
                    <span className="absolute top-0.5 right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold text-white shadow-sm">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-80 md:w-96 origin-top-right rounded-lg border border-border bg-card shadow-xl ring-1 ring-black ring-opacity-5 z-50">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/50 rounded-t-lg">
                        <h3 className="text-sm font-semibold text-foreground">Notifications</h3>
                        {unreadCount > 0 && (
                            <button
                                onClick={markAllAsRead}
                                className="text-xs text-primary hover:text-primary/80 font-medium hover:underline"
                            >
                                Mark all read
                            </button>
                        )}
                    </div>

                    <div className="max-h-[60vh] overflow-y-auto">
                        {!notifications || notifications.length === 0 ? (
                            <div className="p-8 text-center flex flex-col items-center text-muted-foreground">
                                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="mb-2 opacity-20">
                                    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                                    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                                    <line x1="2" y1="2" x2="22" y2="22" />
                                </svg>
                                <p className="text-sm">No notifications yet</p>
                            </div>
                        ) : (
                            <div className="divide-y divide-border">
                                {notifications.map((notification) => (
                                    <div
                                        key={notification.id}
                                        onClick={() => handleNotificationClick(notification)}
                                        className={`group p-4 cursor-pointer hover:bg-muted/50 transition-all ${!notification.is_read ? 'bg-primary/5 border-l-2 border-l-primary' : 'border-l-2 border-l-transparent'
                                            }`}
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="flex-1 space-y-1">
                                                <div className="flex justify-between items-start gap-2">
                                                    <p className={`text-sm ${!notification.is_read ? 'font-semibold text-foreground' : 'text-muted-foreground'
                                                        }`}>
                                                        {notification.title}
                                                    </p>
                                                    <span className="text-[10px] text-muted-foreground whitespace-nowrap mt-0.5">
                                                        {new Date(notification.created_at).toLocaleDateString('en-GB')}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                                                    {notification.message}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
