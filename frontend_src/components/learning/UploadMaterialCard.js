'use client';

import { useState, useRef } from 'react';
import { Upload, FileText, Sparkles, User, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

export default function UploadMaterialCard({ onFileSelect, onModeChange, selectedFile, extractionMode }) {
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef(null);

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const file = e.dataTransfer.files[0];
            if (file.type === 'application/pdf') {
                onFileSelect(file);
            } else {
                alert('Please upload a PDF file.');
            }
        }
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            onFileSelect(e.target.files[0]);
        }
    };

    return (
        <div className="space-y-6">
            <div className="bg-card p-8 rounded-3xl border border-border shadow-sm">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h2 className="text-xl font-bold text-foreground">Learning Materials</h2>
                        <p className="text-sm text-muted-foreground">Upload content for AI analysis or manual setup</p>
                    </div>
                    {selectedFile && (
                        <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-500 rounded-full text-xs font-bold border border-emerald-500/20">
                            <CheckCircle className="w-3 h-3" /> Ready to process
                        </div>
                    )}
                </div>

                {/* Drag & Drop Area */}
                <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`relative border-2 border-dashed rounded-3xl p-10 text-center transition-all cursor-pointer group
                        ${isDragging
                            ? 'border-primary bg-primary/10 scale-[1.01]'
                            : 'border-white/10 hover:border-white/20 hover:bg-white/5'}
                        ${selectedFile ? 'border-emerald-500/30 bg-emerald-500/5' : ''}
                    `}
                >
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept=".pdf"
                        className="hidden"
                    />

                    {!selectedFile ? (
                        <div className="space-y-4">
                            <div className="w-16 h-16 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mx-auto group-hover:scale-110 transition-transform shadow-sm">
                                <Upload className="w-8 h-8" />
                            </div>
                            <div>
                                <p className="text-lg font-bold text-foreground">Drop your PDF here</p>
                                <p className="text-sm text-muted-foreground">or click to browse from device</p>
                            </div>
                            <div className="flex items-center justify-center gap-4 pt-2">
                                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest bg-white/5 px-2 py-1 rounded shadow-sm border border-white/5">PDF ONLY</span>
                                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest bg-white/5 px-2 py-1 rounded shadow-sm border border-white/5">MAX 20MB</span>
                            </div>
                        </div>
                    ) : (
                        <div className="flex items-center justify-between bg-card p-4 rounded-2xl border border-emerald-500/20 shadow-sm animate-in zoom-in-95">
                            <div className="flex items-center gap-4 text-left">
                                <div className="w-12 h-12 bg-emerald-500/10 text-emerald-500 rounded-xl flex items-center justify-center">
                                    <FileText className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="font-bold text-foreground text-sm line-clamp-1">{selectedFile.name}</p>
                                    <p className="text-xs text-muted-foreground">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                                </div>
                            </div>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onFileSelect(null);
                                }}
                                className="p-2 hover:bg-red-500/10 text-muted-foreground hover:text-red-500 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    )}
                </div>

                {/* Mode Selection */}
                <div className="mt-8 grid grid-cols-2 gap-4">
                    <button
                        type="button"
                        onClick={() => onModeChange('ai')}
                        className={`flex flex-col items-center gap-3 p-5 rounded-2xl border-2 transition-all relative overflow-hidden ${extractionMode === 'ai'
                            ? 'border-primary/50 bg-primary/10'
                            : 'border-white/5 hover:border-white/10 hover:bg-white/5'
                            }`}
                    >
                        {extractionMode === 'ai' && (
                            <div className="absolute top-0 right-0 w-8 h-8 bg-primary text-primary-foreground rounded-bl-2xl flex items-center justify-center">
                                <CheckCircle className="w-4 h-4" />
                            </div>
                        )}
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center shadow-sm ${extractionMode === 'ai' ? 'bg-primary text-primary-foreground' : 'bg-white/5 text-muted-foreground'
                            }`}>
                            <Sparkles className="w-6 h-6" />
                        </div>
                        <div className="text-center">
                            <p className="font-bold text-foreground">Generate with AI</p>
                            <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tight">Best for quick module setup</p>
                        </div>
                    </button>

                    <button
                        type="button"
                        onClick={() => onModeChange('manual')}
                        className={`flex flex-col items-center gap-3 p-5 rounded-2xl border-2 transition-all relative overflow-hidden ${extractionMode === 'manual'
                            ? 'border-white/20 bg-white/10'
                            : 'border-white/5 hover:border-white/10 hover:bg-white/5'
                            }`}
                    >
                        {extractionMode === 'manual' && (
                            <div className="absolute top-0 right-0 w-8 h-8 bg-foreground text-background rounded-bl-2xl flex items-center justify-center">
                                <CheckCircle className="w-4 h-4" />
                            </div>
                        )}
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center shadow-sm ${extractionMode === 'manual' ? 'bg-foreground text-background' : 'bg-white/5 text-muted-foreground'
                            }`}>
                            <User className="w-6 h-6" />
                        </div>
                        <div className="text-center">
                            <p className="font-bold text-foreground">Setup Manually</p>
                            <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tight">Add your own questions</p>
                        </div>
                    </button>
                </div>
            </div>

            {/* AI Warning/Hint */}
            {extractionMode === 'ai' && !selectedFile && (
                <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/20 p-4 rounded-2xl animate-in slide-in-from-left-2">
                    <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5" />
                    <p className="text-xs text-amber-500/90 leading-relaxed">
                        <span className="font-bold block mb-0.5 text-amber-500">PDF Required for AI</span>
                        Upload a PDF to let our AI analyze the content and automatically generate high-quality quizzes and flashcards for you.
                    </p>
                </div>
            )}
        </div>
    );
}
