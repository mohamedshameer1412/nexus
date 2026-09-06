'use client';

import { AlertTriangle, X } from 'lucide-react';

export default function AlertModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    type = 'warning',
    showCancel = false,
    confirmText = 'Confirm',
    cancelText = 'Cancel'
}) {
    if (!isOpen) return null;

    const typeStyles = {
        warning: {
            bg: 'bg-yellow-500',
            icon: 'text-yellow-500',
            border: 'border-yellow-500'
        },
        error: {
            bg: 'bg-red-500',
            icon: 'text-red-500',
            border: 'border-red-500'
        },
        info: {
            bg: 'bg-blue-500',
            icon: 'text-blue-500',
            border: 'border-blue-500'
        },
        success: {
            bg: 'bg-green-500',
            icon: 'text-green-500',
            border: 'border-green-500'
        }
    };

    const styles = typeStyles[type] || typeStyles.warning;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center animate-in fade-in duration-200">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-[#0f111a] border border-white/10 rounded-2xl shadow-2xl max-w-md w-full mx-4 animate-in zoom-in-95 duration-200 ring-1 ring-white/10">
                {/* Header */}
                <div className={`flex items-center gap-3 p-6 border-b border-white/5`}>
                    <div className={`w-12 h-12 rounded-full ${styles.bg}/10 flex items-center justify-center border border-${styles.border}/20`}>
                        <AlertTriangle className={`w-6 h-6 ${styles.icon}`} />
                    </div>
                    <h3 className="text-xl font-bold flex-1 text-white">{title}</h3>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/10 rounded-lg transition-colors text-slate-400 hover:text-white"
                    >
                        <X className="w-5 h-5" />
                    </button>

                </div>

                {/* Content */}
                <div className="p-6">
                    <p className="text-muted-foreground leading-relaxed">
                        {message}
                    </p>
                </div>

                {/* Footer */}
                <div className="p-6 pt-0 flex justify-end gap-3">
                    {showCancel && (
                        <button
                            onClick={onClose}
                            className="px-6 py-3 bg-secondary hover:bg-secondary/80 text-foreground rounded-xl font-bold transition-all"
                        >
                            {cancelText}
                        </button>
                    )}
                    <button
                        onClick={() => {
                            if (onConfirm) onConfirm();
                            else onClose();
                        }}
                        className={`px-6 py-3 ${styles.bg} text-white rounded-xl font-bold hover:opacity-90 transition-all shadow-lg shadow-${styles.bg}/20`}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
}
