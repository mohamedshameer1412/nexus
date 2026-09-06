'use client';
import { X, AlertTriangle } from 'lucide-react';

export default function ConfirmationModal({ isOpen, onClose, onConfirm, title, message, confirmText = "Confirm", cancelText = "Cancel", variant = "danger" }) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-card border border-border p-6 rounded-xl w-full max-w-sm shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
                <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${variant === 'danger' ? 'bg-red-500/10 text-red-500' : 'bg-primary/10 text-primary'}`}>
                            <AlertTriangle className="w-5 h-5" />
                        </div>
                        <h3 className="text-lg font-bold text-foreground">{title}</h3>
                    </div>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <p className="text-muted-foreground mb-6 text-sm leading-relaxed">
                    {message}
                </p>

                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg hover:bg-secondary transition-colors text-sm font-medium"
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={() => {
                            onConfirm();
                            onClose();
                        }}
                        className={`px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors ${variant === 'danger'
                            ? 'bg-red-500 hover:bg-red-600'
                            : 'bg-primary hover:bg-primary/90'
                            }`}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
}
