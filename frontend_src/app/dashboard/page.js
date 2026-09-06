'use client';

import { useState, useEffect } from 'react';
import TeacherDashboard from '@/components/dashboard/TeacherDashboard';
import StudentDashboard from '@/components/dashboard/StudentDashboard';

export default function DashboardPage() {
    const [userData, setUserData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            setUserData(JSON.parse(userStr));
        }
        setLoading(false);
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (!userData) {
        return <div className="p-8 text-center">Please log in to view dashboard.</div>;
    }

    return (
        <>
            {userData.role === 'teacher' ? (
                <TeacherDashboard user={userData} />
            ) : (
                <StudentDashboard user={userData} />
            )}
        </>
    );
}
