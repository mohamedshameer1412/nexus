'use client';

import { useState, useEffect } from 'react';
import { User, Shield, Layout, LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api';

import ProfileSettings from '../../../components/settings/ProfileSettings';
import PreferencesSettings from '../../../components/settings/PreferencesSettings';
import PasswordSettings from '../../../components/settings/PasswordSettings';
import Toast from '../../../components/ui/Toast';

export default function SettingsPage() {
    const router = useRouter();
    const [user, setUser] = useState(() => {
        if (typeof window !== 'undefined') {
            return JSON.parse(localStorage.getItem('user') || '{}');
        }
        return {};
    });
    const [toast, setToast] = useState(null);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const userData = await authAPI.getProfile();
                setUser(userData);
                localStorage.setItem('user', JSON.stringify(userData));
            } catch (error) {
                console.error('Failed to fetch profile:', error);
            }
        };
        fetchProfile();
    }, []);

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
    };

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        router.push('/login');
    };

    return (
        <div className="max-w-5xl mx-auto pb-20 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}

            {/* Page Header */}
            <div className="mb-10 text-center">
                <h1 className="text-3xl font-bold tracking-tight text-foreground font-outfit">
                    Account Settings
                </h1>
                <p className="text-muted-foreground mt-2 text-lg">
                    Manage your profile, preferences, and security.
                </p>
            </div>

            <div className="space-y-12">
                {/* Profile Section */}
                <section>
                    <div className="flex items-center gap-3 mb-6 px-2">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                            <User className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-foreground">Profile Information</h2>
                            <p className="text-sm text-muted-foreground">Update your personal details</p>
                        </div>
                    </div>
                    <div className="card-enterprise p-6 md:p-8">
                        <ProfileSettings user={user} onUpdate={setUser} onToast={showToast} />
                    </div>
                </section>

                <hr className="border-border opacity-50" />

                {/* Preferences Section */}
                <section>
                    <div className="flex items-center gap-3 mb-6 px-2">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                            <Layout className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-foreground">App Preferences</h2>
                            <p className="text-sm text-muted-foreground">Customize your experience</p>
                        </div>
                    </div>
                    <div className="card-enterprise p-6 md:p-8">
                        <PreferencesSettings user={user} onUpdate={setUser} />
                    </div>
                </section>

                <hr className="border-border opacity-50" />

                {/* Security Section */}
                <section>
                    <div className="flex items-center gap-3 mb-6 px-2">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                            <Shield className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-foreground">Security</h2>
                            <p className="text-sm text-muted-foreground">Manage your password</p>
                        </div>
                    </div>
                    <div className="card-enterprise p-6 md:p-8">
                        <PasswordSettings onToast={showToast} />
                    </div>
                </section>

                {/* Sign Out Area */}
                <div className="flex justify-center pt-8">
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 px-6 py-3 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors font-medium"
                    >
                        <LogOut className="w-5 h-5" />
                        Sign Out of Account
                    </button>
                </div>
            </div>
        </div>
    );
}
