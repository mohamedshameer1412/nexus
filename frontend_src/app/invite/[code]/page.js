'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { classroomAPI } from '@/lib/api';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

export default function InvitePage() {
    const params = useParams();
    const router = useRouter();
    const { code } = params;

    const [status, setStatus] = useState('loading'); // loading, success, error, unauthorized
    const [message, setMessage] = useState('Verifying invitation...');

    useEffect(() => {
        const joinClassroom = async () => {
            try {
                // Check authentication
                const token = localStorage.getItem('access_token');
                const userStr = localStorage.getItem('user');

                if (!token || !userStr) {
                    // Redirect to login with return URL
                    const returnUrl = encodeURIComponent(`/invite/${code}`);
                    router.push(`/login?returnUrl=${returnUrl}`);
                    return;
                }

                const user = JSON.parse(userStr);

                // Prevent teachers from joining
                if (user.role && user.role !== 'student') {
                    setStatus('error');
                    setMessage(`You are logged in as a ${user.role}. Only students can join classrooms.`);
                    return;
                }

                // Attempt to join
                await classroomAPI.joinClass(code);
                setStatus('success');
                setMessage('Successfully joined the classroom!');

                // Redirect to dashboard after delay
                setTimeout(() => {
                    router.push('/dashboard');
                }, 2000);

            } catch (error) {
                console.error(error);
                setStatus('error');
                const errMsg = error.response?.data?.error || error.response?.data?.message || 'Failed to join classroom';

                if (errMsg.includes('Already enrolled')) {
                    setStatus('success'); // Treat as success for UX
                    setMessage('You are already a member of this classroom!');
                    setTimeout(() => {
                        router.push('/dashboard');
                    }, 2000);
                } else if (errMsg.includes('Invalid access code')) {
                    setMessage('This invitation link is invalid or expired.');
                } else {
                    setMessage(errMsg);
                }
            }
        };

        if (code) {
            joinClassroom();
        }
    }, [code, router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
            <div className="bg-white rounded-2xl p-8 shadow-xl max-w-md w-full text-center border border-slate-100">

                {status === 'loading' && (
                    <div className="flex flex-col items-center py-8">
                        <Loader2 className="w-12 h-12 text-primary animate-spin mb-4" />
                        <h2 className="text-xl font-semibold text-slate-800">Joining Classroom...</h2>
                        <p className="text-slate-500 mt-2">Please wait while we process your invitation.</p>
                    </div>
                )}

                {status === 'success' && (
                    <div className="flex flex-col items-center py-8">
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                            <CheckCircle className="w-8 h-8 text-green-600" />
                        </div>
                        <h2 className="text-xl font-semibold text-slate-800">Success!</h2>
                        <p className="text-slate-600 mt-2">{message}</p>
                        <p className="text-sm text-slate-400 mt-4">Redirecting to dashboard...</p>
                    </div>
                )}

                {status === 'error' && (
                    <div className="flex flex-col items-center py-8">
                        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                            <XCircle className="w-8 h-8 text-red-600" />
                        </div>
                        <h2 className="text-xl font-semibold text-slate-800">Unable to Join</h2>
                        <p className="text-red-500 mt-2">{message}</p>

                        <button
                            onClick={() => router.push('/dashboard')}
                            className="mt-6 px-6 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors"
                        >
                            Go to Dashboard
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
