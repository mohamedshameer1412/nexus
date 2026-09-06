import { useState } from 'react';
import api from '@/lib/api';
import { User, Mail, Calendar, Camera, Save, Loader2, Link, Phone, Shield } from 'lucide-react';
import PhoneInput from 'react-phone-input-2';
import 'react-phone-input-2/lib/style.css';
import Toast from '../ui/Toast';

export default function ProfileSettings({ user, onUpdate, onToast }) {
    const [isEditing, setIsEditing] = useState(false);
    const [loading, setLoading] = useState(false);
    const [localToast, setLocalToast] = useState(null);
    const [formData, setFormData] = useState({
        username: user.username || '',
        email: user.email || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        phone_number: user.phone_number || '',
        date_of_birth: user.date_of_birth || '',
        profile_picture: null,
    });

    const showToast = (message, type) => {
        if (onToast) {
            onToast(message, type);
        } else {
            setLocalToast({ message, type });
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handlePhoneChange = (value) => {
        setFormData(prev => ({ ...prev, phone_number: value }));
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFormData(prev => ({ ...prev, profile_picture: e.target.files[0] }));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const data = new FormData();
            if (formData.username) data.append('username', formData.username);
            if (formData.email) data.append('email', formData.email);
            if (formData.first_name) data.append('first_name', formData.first_name);
            if (formData.last_name) data.append('last_name', formData.last_name);
            if (formData.phone_number) data.append('phone_number', formData.phone_number);
            if (formData.date_of_birth) data.append('date_of_birth', formData.date_of_birth);
            if (formData.profile_picture) data.append('profile_picture', formData.profile_picture);

            const response = await api.patch('/api/auth/profile/', data, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const updatedUser = { ...user, ...response.data };
            localStorage.setItem('user', JSON.stringify(updatedUser));
            if (onUpdate) onUpdate(updatedUser);

            setIsEditing(false);
            showToast('Profile updated successfully!', 'success');
        } catch (error) {
            console.error('Update failed:', error);
            showToast('Failed to update profile', 'error');
        } finally {
            setLoading(false);
        }
    };

    if (!isEditing) {
        return (
            <div className="space-y-8">
                {localToast && (
                    <Toast
                        message={localToast.message}
                        type={localToast.type}
                        onClose={() => setLocalToast(null)}
                    />
                )}

                <div className="flex flex-col lg:flex-row gap-10 items-start">
                    {/* Avatar Section */}
                    <div className="w-full lg:w-auto flex flex-col items-center gap-4 flex-shrink-0">
                        <div className="relative group">
                            <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-muted bg-background shadow-lg">
                                {user.profile_picture ? (
                                    <img src={user.profile_picture} alt="Profile" className="w-full h-full object-cover" />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center bg-primary/10 text-primary">
                                        <User className="w-12 h-12" />
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="text-center">
                            <h3 className="font-bold text-foreground text-xl">
                                {user.first_name} {user.last_name}
                            </h3>
                            <p className="text-muted-foreground text-sm">@{user.username}</p>
                            <span className="inline-block mt-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold uppercase tracking-wider">
                                {user.role}
                            </span>
                        </div>
                    </div>

                    {/* Details Grid */}
                    <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                        {/* Email */}
                        <div className="p-5 rounded-xl bg-card border border-border/50 hover:border-primary/20 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <Mail className="w-4 h-4 text-primary" />
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Email Address</span>
                            </div>
                            <p className="text-foreground font-medium truncate" title={user.email}>{user.email}</p>
                        </div>

                        {/* Phone */}
                        <div className="p-5 rounded-xl bg-card border border-border/50 hover:border-primary/20 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <Phone className="w-4 h-4 text-primary" />
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Phone Number</span>
                            </div>
                            <p className="text-foreground font-medium">{user.phone_number || 'Not provided'}</p>
                        </div>

                        {/* DOB */}
                        <div className="p-5 rounded-xl bg-card border border-border/50 hover:border-primary/20 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <Calendar className="w-4 h-4 text-primary" />
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Date of Birth</span>
                            </div>
                            <p className="text-foreground font-medium">{user.date_of_birth ? new Date(user.date_of_birth).toLocaleDateString('en-GB') : 'Not provided'}</p>
                        </div>

                        {/* Role (duplicated contextually if needed, but keeping grid balanced) */}
                        <div className="p-5 rounded-xl bg-card border border-border/50 hover:border-primary/20 transition-colors">
                            <div className="flex items-center gap-3 mb-2">
                                <Shield className="w-4 h-4 text-primary" />
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Account Type</span>
                            </div>
                            <p className="text-foreground font-medium capitalize">{user.role}</p>
                        </div>
                    </div>
                </div>

                <div className="flex justify-end pt-6 border-t border-border">
                    <button
                        onClick={() => setIsEditing(true)}
                        className="btn-enterprise-primary px-8"
                    >
                        Edit Profile
                    </button>
                </div>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-8">
            <div className="flex flex-col lg:flex-row gap-10">
                {/* Avatar Upload */}
                <div className="w-full lg:w-auto flex flex-col items-center gap-4 flex-shrink-0">
                    <div className="relative group cursor-pointer">
                        <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-muted bg-background shadow-lg group-hover:border-primary transition-colors">
                            {formData.profile_picture instanceof File ? (
                                <img src={URL.createObjectURL(formData.profile_picture)} alt="Preview" className="w-full h-full object-cover opacity-50 group-hover:opacity-40 transition-opacity" />
                            ) : user.profile_picture ? (
                                <img src={user.profile_picture} alt="Profile" className="w-full h-full object-cover opacity-100 group-hover:opacity-40 transition-opacity" />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center bg-primary/10 text-primary">
                                    <User className="w-12 h-12" />
                                </div>
                            )}

                            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                <Camera className="w-8 h-8 text-foreground" />
                            </div>
                            <input
                                type="file"
                                accept="image/*"
                                onChange={handleFileChange}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            />
                        </div>
                        <p className="text-xs text-muted-foreground">Click to upload new photo</p>
                    </div>
                </div>

                {/* Edit Form Grid */}
                <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">First Name</label>
                        <input
                            type="text"
                            name="first_name"
                            value={formData.first_name}
                            onChange={handleChange}
                            className="w-full px-4 h-11 rounded-lg bg-background border border-input text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">Last Name</label>
                        <input
                            type="text"
                            name="last_name"
                            value={formData.last_name}
                            onChange={handleChange}
                            className="w-full px-4 h-11 rounded-lg bg-background border border-input text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">Username</label>
                        <input
                            type="text"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            className="w-full px-4 h-11 rounded-lg bg-background border border-input text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">Email</label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            className="w-full px-4 h-11 rounded-lg bg-background border border-input text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">Phone Number</label>
                        <div className="phone-input-container">
                            <PhoneInput
                                country={'in'}
                                value={formData.phone_number}
                                onChange={handlePhoneChange}
                                containerClass="!w-full"
                                inputClass="!w-full !h-11 !bg-background !border-input !text-foreground !rounded-lg focus:!ring-2 focus:!ring-primary/20 focus:!border-primary !transition-all"
                                buttonClass="!bg-background !border-input !rounded-l-lg hover:!bg-muted"
                                dropdownClass="!bg-background !text-foreground"
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">Date of Birth</label>
                        <input
                            type="date"
                            name="date_of_birth"
                            value={formData.date_of_birth}
                            onChange={handleChange}
                            className="w-full px-4 h-11 rounded-lg bg-background border border-input text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all [color-scheme:dark]"
                        />
                    </div>
                </div>
            </div>

            <div className="flex gap-4 justify-end pt-6 border-t border-border">
                <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    className="px-6 py-2.5 rounded-lg border border-border text-muted-foreground hover:bg-muted hover:text-foreground transition-colors font-medium"
                    disabled={loading}
                >
                    Cancel
                </button>
                <button
                    type="submit"
                    disabled={loading}
                    className="btn-enterprise-primary px-8 flex items-center gap-2"
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Saving...
                        </>
                    ) : (
                        <>
                            <Save className="w-4 h-4" />
                            Save Changes
                        </>
                    )}
                </button>
            </div>
        </form>
    );
}
