'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Upload, FileText, Loader2, ArrowLeft, CheckCircle, Save } from 'lucide-react';
import { learningAPI, classroomAPI } from '@/lib/api';

export default function EditModulePage() {
    const router = useRouter();
    const { id } = useParams();
    const [loading, setLoading] = useState(false);
    const [fetching, setFetching] = useState(true);
    const [step, setStep] = useState('edit'); // 'edit' | 'saving' | 'success'
    const [classrooms, setClassrooms] = useState([]);

    // Form State
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        classroom: '',
        pdf_file: null
    });

    useEffect(() => {
        fetchClassrooms();
        fetchModule();
    }, [id]);

    const fetchClassrooms = async () => {
        try {
            const data = await classroomAPI.getTeachingClassrooms();
            const classroomList = Array.isArray(data) ? data : data?.results || [];
            setClassrooms(classroomList);
        } catch (error) {
            console.error('Failed to fetch classrooms:', error);
        }
    };

    const fetchModule = async () => {
        try {
            const module = await learningAPI.getModule(id);
            setFormData({
                title: module.title || '',
                description: module.description || '',
                classroom: module.classroom || '',
                pdf_file: null // Don't pre-fill file input
            });
        } catch (error) {
            console.error('Failed to fetch module:', error);
            alert('Failed to load module data.');
            router.push('/dashboard/learning');
        } finally {
            setFetching(false);
        }
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFormData({ ...formData, pdf_file: e.target.files[0] });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setStep('saving');

        try {
            const submitData = new FormData();
            submitData.append('title', formData.title);
            submitData.append('description', formData.description);
            submitData.append('classroom', formData.classroom);
            if (formData.pdf_file) {
                submitData.append('pdf_file', formData.pdf_file);
            }

            await learningAPI.updateModule(id, submitData);

            setStep('success');
            setTimeout(() => {
                router.push(`/dashboard/learning/${id}`);
            }, 1500);
        } catch (error) {
            console.error('Error updating module:', error);
            alert('Failed to update module. Please try again.');
            setLoading(false);
            setStep('edit');
        }
    };

    if (fetching) {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh]">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-4" />
                <p className="text-slate-500">Loading module data...</p>
            </div>
        );
    }

    if (step === 'saving') {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-6">
                <div className="relative">
                    <div className="w-20 h-20 rounded-full border-4 border-slate-100 border-t-blue-500 animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                        <Save className="w-8 h-8 text-blue-500 animate-pulse" />
                    </div>
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-slate-800">Saving Changes...</h2>
                    <p className="text-slate-500 max-w-md mt-2">
                        Updating module details. One moment please.
                    </p>
                </div>
            </div>
        );
    }

    if (step === 'success') {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-6">
                <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center animate-bounce">
                    <CheckCircle className="w-10 h-10" />
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-slate-800">Module Updated!</h2>
                    <p className="text-slate-500 mt-2">Redirecting you to the module...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto">
            <button
                onClick={() => router.back()}
                className="flex items-center gap-2 text-slate-500 hover:text-slate-800 mb-6 transition-colors"
            >
                <ArrowLeft className="w-4 h-4" />
                Back
            </button>

            <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-100">
                <h1 className="text-2xl font-bold mb-6">Edit Learning Module</h1>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Overview
                        </label>
                        <input
                            type="text"
                            placeholder="Module Title"
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all mb-4"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            required
                        />
                        <textarea
                            placeholder="Brief description..."
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all h-32 resize-none"
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Assigned Classroom
                        </label>
                        <select
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all bg-white"
                            value={formData.classroom}
                            onChange={(e) => setFormData({ ...formData, classroom: e.target.value })}
                            required
                        >
                            <option value="" disabled>Select a classroom</option>
                            {classrooms.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Update Material (Optional)
                        </label>
                        <div className="border-2 border-dashed border-slate-200 rounded-2xl p-8 text-center hover:bg-slate-50 transition-colors cursor-pointer relative">
                            <input
                                type="file"
                                accept=".pdf"
                                onChange={handleFileChange}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            />
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-12 h-12 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center">
                                    <Upload className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="font-semibold text-slate-700">
                                        {formData.pdf_file ? formData.pdf_file.name : "Click to replace PDF"}
                                    </p>
                                    <p className="text-xs text-slate-400 mt-1">
                                        Leave empty to keep existing material.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="pt-4 flex gap-4">
                        <button
                            type="button"
                            onClick={() => router.back()}
                            className="flex-1 py-4 rounded-xl font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className={`flex-[2] py-4 rounded-xl font-bold text-white transition-all transform hover:scale-[1.02] active:scale-[0.98] ${loading ? 'bg-slate-400 cursor-not-allowed' : 'btn-primary'
                                }`}
                        >
                            {loading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Saving...
                                </span>
                            ) : (
                                'Save Changes'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
