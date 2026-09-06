import { useState } from 'react';
import api from '@/lib/api';
import { Lock, Eye, EyeOff, Loader2 } from 'lucide-react';

export default function PasswordSettings({ onToast }) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        current_password: '',
        new_password: '',
        confirm_password: ''
    });
    const [showPasswords, setShowPasswords] = useState({
        current: false,
        new: false,
        confirm: false
    });

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const togglePasswordVisibility = (field) => {
        setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (formData.new_password !== formData.confirm_password) {
            onToast('Passwords do not match', 'error');
            return;
        }

        if (formData.new_password.length < 8) {
            onToast('Password must be at least 8 characters', 'error');
            return;
        }

        setLoading(true);

        try {
            await api.post('/api/auth/change-password/', {
                old_password: formData.current_password,
                new_password: formData.new_password
            });

            onToast('Password changed successfully!', 'success');
            setFormData({
                current_password: '',
                new_password: '',
                confirm_password: ''
            });
        } catch (error) {
            console.error('Password change failed:', error);
            const errorMsg = error.response?.data?.error || 'Failed to change password';
            onToast(errorMsg, 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6 w-full">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                {/* Current Password - Full Width on Mobile, Half on Desktop if you want, or keep full width for passwords as they are sensitive. 
                   Let's keep them full width logically or half width to match profile inputs? 
                   Passwords usually look better stacked or in a narrower column, but to fill the wide card, let's use the grid.
                */}

                <div className="col-span-1 md:col-span-2 space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Current Password</label>
                    <div className="relative group">
                        <input
                            type={showPasswords.current ? 'text' : 'password'}
                            name="current_password"
                            value={formData.current_password}
                            onChange={handleChange}
                            className="w-full px-4 h-11 pr-10 rounded-lg bg-background border border-input text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                            placeholder="Enter current password"
                            required
                        />
                        <button
                            type="button"
                            onClick={() => togglePasswordVisibility('current')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                        >
                            {showPasswords.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    </div>
                </div>

                {/* New Password */}
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">New Password</label>
                    <div className="relative group">
                        <input
                            type={showPasswords.new ? 'text' : 'password'}
                            name="new_password"
                            value={formData.new_password}
                            onChange={handleChange}
                            className="w-full px-4 h-11 pr-10 rounded-lg bg-background border border-input text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                            placeholder="At least 8 characters"
                            required
                        />
                        <button
                            type="button"
                            onClick={() => togglePasswordVisibility('new')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                        >
                            {showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    </div>
                </div>

                {/* Confirm Password */}
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Confirm New Password</label>
                    <div className="relative group">
                        <input
                            type={showPasswords.confirm ? 'text' : 'password'}
                            name="confirm_password"
                            value={formData.confirm_password}
                            onChange={handleChange}
                            className="w-full px-4 h-11 pr-10 rounded-lg bg-background border border-input text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                            placeholder="Confirm new password"
                            required
                        />
                        <button
                            type="button"
                            onClick={() => togglePasswordVisibility('confirm')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                        >
                            {showPasswords.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    </div>
                </div>
            </div>

            <div className="flex justify-end pt-6 border-t border-border">
                <button
                    type="submit"
                    className="btn-enterprise-primary flex items-center gap-2 px-8"
                    disabled={loading}
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Updating...
                        </>
                    ) : (
                        <>
                            <Lock className="w-4 h-4" />
                            Update Password
                        </>
                    )}
                </button>
            </div>
        </form>
    );
}
