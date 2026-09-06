import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Bell, Loader2 } from 'lucide-react';

export default function PreferencesSettings({ user, onUpdate }) {
    const [loading, setLoading] = useState(false);
    const [emailNotifs, setEmailNotifs] = useState(user.preference_email_notifications ?? true);

    useEffect(() => {
        setEmailNotifs(user.preference_email_notifications ?? true);
    }, [user.preference_email_notifications]);

    const handleToggle = async (key, value) => {
        setLoading(true);
        if (key === 'preference_email_notifications') {
            setEmailNotifs(value);
        }

        try {
            const data = { [key]: value };
            const response = await api.patch('/api/auth/profile/', data);

            if (onUpdate) {
                onUpdate(curr => ({ ...curr, ...response.data }));
            }
            const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
            localStorage.setItem('user', JSON.stringify({ ...currentUser, ...response.data }));

        } catch (error) {
            console.error('Failed to update preference:', error);
            // Revert
            setEmailNotifs(!value);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-4">
            <div className="p-4 rounded-xl border border-border bg-card/50">
                <h3 className="text-lg font-medium text-foreground mb-1">Application Preferences</h3>
                <p className="text-sm text-muted-foreground">Manage your notification settings.</p>
            </div>

            {/* Email Notifications Toggle */}
            <div className="flex items-center justify-between p-4 rounded-xl border border-border bg-card hover:bg-card/80 transition-colors">
                <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg bg-primary/10 text-primary`}>
                        <Bell className="w-5 h-5" />
                    </div>
                    <div>
                        <p className="font-semibold text-foreground">Email Notifications</p>
                        <p className="text-sm text-muted-foreground">Receive updates about your quizzes and results</p>
                    </div>
                </div>

                <div className="relative inline-flex items-center cursor-pointer">
                    <button
                        onClick={() => handleToggle('preference_email_notifications', !emailNotifs)}
                        className={`w-12 h-6 rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${emailNotifs ? 'bg-primary' : 'bg-muted-foreground/30'}`}
                        disabled={loading}
                    >
                        <span className={`block w-4 h-4 rounded-full bg-white shadow transform transition duration-200 ease-in-out mt-1 ml-1 ${emailNotifs ? 'translate-x-6' : 'translate-x-0'}`} />
                    </button>
                </div>
            </div>
        </div>
    );
}
