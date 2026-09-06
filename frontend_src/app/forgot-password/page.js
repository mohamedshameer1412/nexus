'use client';

import { useState } from 'react';
import { Mail, Brain, ArrowRight, Loader2, ArrowLeft } from 'lucide-react';
import { authAPI } from '../../lib/api';
import Toast from '../../components/ui/Toast';

export default function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const [toast, setToast] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await authAPI.requestPasswordReset(email);
            setSuccess(true);
            setToast({ message: 'Reset link sent to your email', type: 'success' });
        } catch (err) {
            console.error(err);
            setError(err.response?.data?.error || err.response?.data?.detail || 'Failed to send reset link.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background relative overflow-hidden">
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}

            {;/* Gradient Background */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-background to-background"></div>
                <div className="absolute inset-0 bg-grid-white/[0.02] bg-[length:32px_32px] pointer-events-none"></div>
            </div>

            <div className="w-full max-w-md z-10 animate-fade-in">
                {/* Logo Section */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary mb-4 shadow-lg shadow-primary/20">
                        <Brain className="w-6 h-6 text-primary-foreground" />
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-foreground">
                        Forgot Password
                    </h1>
                    <p className="text-sm text-muted-foreground mt-2">
                        Enter your email to receive a password reset link
                    </p>
                </div>

                <div className="card-enterprise p-8 backdrop-blur-xl bg-card/50 border-white/10">
                    {!success ? (
                        <form onSubmit={handleSubmit} className="space-y-5" autoComplete="off">
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-muted-foreground">Email</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                    <input
                                        type="email"
                                        name="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                                        placeholder="name@example.com"
                                        required
                                    />
                                </div>
                            </div>

                            {error && (
                                <div className="p-3 rounded-md text-sm bg-destructive/10 text-destructive border border-destructive/20 flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-destructive flex-shrink-0" />
                                    {error}
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full btn-enterprise-primary flex items-center justify-center gap-2 py-2.5"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span>Sending Link...</span>
                                    </>
                                ) : (
                                    <>
                                        <span>Send Reset Link</span>
                                        <ArrowRight className="w-4 h-4" />
                                    </>
                                )}
                            </button>
                        </form>
                    ) : (
                        <div className="text-center py-4 space-y-4">
                            <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-4">
                                <Mail className="w-6 h-6" />
                            </div>
                            <h3 className="text-lg font-medium text-foreground">Check your email</h3>
                            <p className="text-sm text-muted-foreground">
                                We've sent a password reset link to <span className="text-foreground">{email}</span>.
                            </p>
                        </div>
                    )
}

                    <div className="mt-6 pt-6 border-t border-border text-center">
                        <a
                            href="/login"
                            className="inline-flex items-center text-sm font-medium text-muted-foreground hover:text-primary transition-all"
                        >
                            <ArrowLeft className="w-4 h-4 mr-2" />
                            Back to Login
                        </a>
                    </div>
                </div>

                <p className="text-center text-xs text-muted-foreground mt-8">
                    © 2026 LearnMate AI. Enterprise Learning Platform.
                </p>
            </div>
        </div>
    );
}