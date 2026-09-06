'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api';
import { Brain, Loader2, ArrowRight, Eye, EyeOff, Lock, Mail, User, Calendar, Phone } from 'lucide-react';
import PhoneInput from 'react-phone-input-2';
import 'react-phone-input-2/lib/style.css';
import Toast from '@/components/ui/Toast';

export default function LoginPage() {
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [toast, setToast] = useState(null);

    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const [formData, setFormData] = useState({
        username: '',
        password: '',
        confirmPassword: '',
        email: '',
        first_name: '',
        last_name: '',
        role: 'student',
        phone_number: '',
        date_of_birth: '',
    });

    useEffect(() => {
        const savedTab = localStorage.getItem('login_tab');
        if (savedTab) {
            setIsLogin(savedTab === 'login');
        }
    }, []);

    useEffect(() => {
        localStorage.setItem('login_tab', isLogin ? 'login' : 'register');
    }, [isLogin]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setToast(null);

        if (!isLogin) {
            if (formData.password !== formData.confirmPassword) {
                setError('Passwords do not match');
                return;
            }
            if (formData.password.length < 8) {
                setError('Password must be at least 8 characters long');
                return;
            }
            if (formData.date_of_birth) {
                const dob = new Date(formData.date_of_birth);
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                if (dob >= today) {
                    setError('Date of Birth cannot be today or in the future');
                    return;
                }
            } else {
                setError('Date of Birth is required');
                return;
            }
        }

        setLoading(true);

        try {
            if (isLogin) {
                const data = await authAPI.login(formData.email, formData.password);
                localStorage.setItem('access_token', data.tokens.access);
                localStorage.setItem('refresh_token', data.tokens.refresh);
                localStorage.setItem('user', JSON.stringify(data.user));
                const params = new URLSearchParams(window.location.search);
                const returnUrl = params.get('returnUrl') || '/dashboard';
                router.push(decodeURIComponent(returnUrl));
            } else {
                const registerData = {
                    ...formData,
                    password2: formData.password,
                };
                delete registerData.confirmPassword;
                await authAPI.register(registerData);
                setIsLogin(true);
                setToast({ message: 'Registration successful! Please login with your email.', type: 'success' });
            }
        } catch (err) {
            console.error(err);
            setError(err.response?.data?.error || err.response?.data?.detail || 'Authentication failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handlePhoneChange = (value) => {
        setFormData(prev => ({ ...prev, phone_number: value }));
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

            {/* Gradient Background */}
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
                        {isLogin ? 'Welcome back' : 'Create an account'}
                    </h1>
                    <p className="text-sm text-muted-foreground mt-2">
                        {isLogin ? 'Enter your credentials to access your account' : 'Start your adaptive learning journey today'}
                    </p>
                </div>

                <div className="card-enterprise p-8 backdrop-blur-xl bg-card/50 border-white/10">
                    <form onSubmit={handleSubmit} className="space-y-5" autoComplete="off">
                        {/* Role Selection Tabs (Register Only) */}
                        {!isLogin && (
                            <div className="grid grid-cols-2 gap-2 p-1 bg-muted/50 rounded-md border border-border mb-6">
                                {['student', 'teacher'].map((role) => (
                                    <button
                                        key={role}
                                        type="button"
                                        onClick={() => setFormData(prev => ({ ...prev, role }))}
                                        className={`py-2 text-xs font-semibold uppercase tracking-wider rounded-sm transition-all ${formData.role === role
                                            ? 'bg-background text-foreground shadow-sm'
                                            : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                                            }`}
                                    >
                                        {role}
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Registration Fields */}
                        {!isLogin && (
                            <div className="grid grid-cols-2 gap-4">
                                <div className="col-span-2 space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground">Full Name</label>
                                    <div className="relative">
                                        <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                        <input
                                            type="text"
                                            name="username"
                                            value={formData.username}
                                            onChange={handleChange}
                                            className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                                            placeholder="John Doe"
                                            required={!isLogin}
                                        />
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <input
                                    type="email"
                                    name="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                                    placeholder="name@example.com"
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground">Password</label>
                            <div className="relative group">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    name="password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    className="w-full pl-9 pr-10 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                                    placeholder="••••••••"
                                    required
                                />
                                <button
                                    type="button"
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                    onClick={() => setShowPassword(!showPassword)}
                                >
                                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                        </div>

                        {!isLogin && (
                            <>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground">Confirm Password</label>
                                    <div className="relative group">
                                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                        <input
                                            type={showConfirmPassword ? "text" : "password"}
                                            name="confirmPassword"
                                            value={formData.confirmPassword}
                                            onChange={handleChange}
                                            className="w-full pl-9 pr-10 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                                            placeholder="••••••••"
                                            required={!isLogin}
                                        />
                                        <button
                                            type="button"
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                        >
                                            {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                        </button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-medium text-muted-foreground">Date of Birth</label>
                                        <div className="relative">
                                            <input
                                                type="date"
                                                name="date_of_birth"
                                                value={formData.date_of_birth}
                                                onChange={handleChange}
                                                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                                                required={!isLogin}
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-medium text-muted-foreground">Phone</label>
                                        <div className="relative">
                                            <PhoneInput
                                                country={'in'}
                                                value={formData.phone_number}
                                                onChange={handlePhoneChange}
                                                containerClass="!w-full"
                                                inputClass="!w-full !bg-background !border-border !text-foreground !h-[38px] !pl-[48px] !text-sm !rounded-md focus:!ring-1 focus:!ring-primary focus:!border-primary"
                                                buttonClass="!bg-background !border-border !rounded-l-md hover:!bg-muted"
                                                dropdownClass="!bg-popover !text-popover-foreground !border-border"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}

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
                                    <span>{isLogin ? 'Authenticating...' : 'Creating Account...'}</span>
                                </>
                            ) : (
                                <>
                                    <span>{isLogin ? 'Sign In' : 'Create Account'}</span>
                                    <ArrowRight className="w-4 h-4" />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="mt-6 pt-6 border-t border-border text-center">
                        <p className="text-sm text-muted-foreground">
                            {isLogin ? "Don't have an account?" : "Already have an account?"}
                            <button
                                onClick={() => { setIsLogin(!isLogin); setError(''); }}
                                className="ml-1.5 font-medium text-primary hover:text-primary/90 hover:underline transition-all"
                            >
                                {isLogin ? 'Register' : 'Login'}
                            </button>
                        </p>
                    </div>
                </div>

                <p className="text-center text-xs text-muted-foreground mt-8">
                    © 2026 LearnMate AI. Enterprise Learning Platform.
                </p>
            </div>
        </div>
    );
}
