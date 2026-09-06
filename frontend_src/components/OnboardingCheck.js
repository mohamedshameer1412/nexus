'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { userAPI } from '@/lib/api';

export default function OnboardingCheck({ children }) {
    const router = useRouter();
    const pathname = usePathname();
    const [loading, setLoading] = useState(true);
    const [hasProfile, setHasProfile] = useState(false);

    useEffect(() => {
        checkOnboardingStatus();
    }, []);

    const checkOnboardingStatus = async () => {
        // Skip check for non-student pages or onboarding/diagnostic pages
        const skipPaths = ['/dashboard/onboarding', '/dashboard/diagnostic-test', '/dashboard/settings', '/login'];
        if (skipPaths.some(path => pathname.startsWith(path))) {
            setLoading(false);
            return;
        }

        try {
            const user = JSON.parse(localStorage.getItem('user') || '{}');

            // Only check for students
            if (user.role !== 'student') {
                setLoading(false);
                return;
            }

            // Use the centralized API client which handles the base URL and auth tokens automatically
            await userAPI.getLearningProfile();
            setHasProfile(true);

        } catch (error) {
            // Check if profile not found (404)
            if (error.response && error.response.status === 404) {
                // No profile found, redirect to onboarding
                router.push('/dashboard/onboarding');
            } else {
                console.error('Error checking onboarding status:', error);
            }
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading...</p>
                </div>
            </div>
        );
    }

    return children;
}
