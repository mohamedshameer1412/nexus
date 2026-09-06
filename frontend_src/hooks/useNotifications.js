import { useState, useEffect, useCallback } from 'react';
import { notificationAPI } from '../lib/api';
import { parseApiError, isErrorType } from '../lib/errorHandler';

export function useNotifications() {
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchNotifications = useCallback(async () => {
        try {
            const data = await notificationAPI.getAll();
            // Handle pagination (DRF returns { count: ..., results: [...] })
            const notificationsList = Array.isArray(data) ? data : (data.results || []);
            setNotifications(notificationsList);

            // Get accurate unread count
            const countData = await notificationAPI.getUnreadCount();
            setUnreadCount(countData.unread_count);
            setError(null); // Clear any previous errors
        } catch (error) {
            const parsedError = parseApiError(error);

            // Only log non-503 errors (503 means service temporarily unavailable)
            if (parsedError.statusCode !== 503) {
                console.warn("Notifications unavailable:", parsedError.message);
            }

            // Silently handle errors - don't spam console
            // Set empty state instead of showing errors
            setNotifications([]);
            setUnreadCount(0);
            setError(parsedError);
        } finally {
            setLoading(false);
        }
    }, []);

    const markAsRead = async (id) => {
        try {
            await notificationAPI.markRead(id);
            // Optimistic update
            setNotifications(prev => prev.map(n =>
                n.id === id ? { ...n, is_read: true } : n
            ));
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (error) {
            console.error("Failed to mark notification as read:", error);
        }
    };

    const markAllAsRead = async () => {
        try {
            await notificationAPI.markAllRead();
            // Optimistic update
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
            setUnreadCount(0);
        } catch (error) {
            console.error("Failed to mark all as read:", error);
        }
    };

    useEffect(() => {
        // Initial fetch for authenticated users only
        // We'll rely on the API call failing gracefully if not authenticated, 
        // or the component using this hook handling auth state.
        const token = localStorage.getItem('access_token');
        if (token) {
            fetchNotifications();

            // Poll every 60 seconds
            const interval = setInterval(fetchNotifications, 60000);
            return () => clearInterval(interval);
        } else {
            setLoading(false);
        }
    }, [fetchNotifications]);

    return {
        notifications,
        unreadCount,
        loading,
        error,
        fetchNotifications,
        markAsRead,
        markAllAsRead
    };
}
