'use client';

import { X, AlertTriangle, Info, CheckCircle, XCircle } from 'lucide-react';

export default function ConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    variant = 'default', // 'default' | 'destructive' | 'warning' | 'info'
    icon: CustomIcon = null,
    showCancel = true
}) {
    if (!isOpen) return null;

    const getVariantStyles = () => {
        switch (variant) {
            case 'destructive':
                return {
                    iconBg: 'bg-red-100 dark:bg-red-900/20',
                    iconColor: 'text-red-600 dark:text-red-400',
                    confirmBtn: 'bg-red-600 hover:bg-red-700 text-white',
                    Icon: XCircle
                };
            case 'warning':
                return {
                    iconBg: 'bg-yellow-100 dark:bg-yellow-900/20',
                    iconColor: 'text-yellow-600 dark:text-yellow-400',
                    confirmBtn: 'bg-yellow-600 hover:bg-yellow-700 text-white',
                    Icon: AlertTriangle
                };
            case 'info':
                return {
                    iconBg: 'bg-blue-100 dark:bg-blue-900/20',
                    iconColor: 'text-blue-600 dark:text-blue-400',
                    confirmBtn: 'bg-blue-600 hover:bg-blue-700 text-white',
                    Icon: Info
                };
            default:
                return {
                    iconBg: 'bg-green-100 dark:bg-green-900/20',
                    iconColor: 'text-green-600 dark:text-green-400',
                    confirmBtn: 'bg-primary hover:bg-primary/90 text-primary-foreground',
                    Icon: CheckCircle
                };
        }
    };

    const styles = getVariantStyles();
    const IconComponent = CustomIcon || styles.Icon;

    const handleConfirm = () => {
        onConfirm();
        onClose();
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-card border border-border rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden animate-in fade-in zoom-in duration-200">
                {/* Close Button */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-2 rounded-lg hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
                >
                    <X className="w-5 h-5" />
                </button>

                {/* Content */}
                <div className="p-6 pt-8">
                    {/* Icon */}
                    <div className={`w-16 h-16 rounded-full ${styles.iconBg} flex items-center justify-center mx-auto mb-4`}>
                        <IconComponent className={`w-8 h-8 ${styles.iconColor}`} />
                    </div>

                    {/* Title */}
                    <h2 className="text-2xl font-bold text-center mb-3 text-foreground">
                        {title}
                    </h2>

                    {/* Message */}
                    <p className="text-center text-muted-foreground mb-6 leading-relaxed">
                        {message}
                    </p>

                    {/* Actions */}
                    <div className="flex gap-3">
                        {showCancel && (
                            <button
                                onClick={onClose}
                                className="flex-1 px-4 py-3 rounded-xl font-medium bg-secondary text-foreground hover:bg-secondary/80 transition-all border border-border"
                            >
                                {cancelText}
                            </button>
                        )}
                        <button
                            onClick={handleConfirm}
                            className={`flex-1 px-4 py-3 rounded-xl font-medium transition-all shadow-lg ${styles.confirmBtn}`}
                        >
                            {confirmText}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
