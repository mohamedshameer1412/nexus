'use client';

import { AlertTriangle, XCircle, RefreshCw, Info } from 'lucide-react';

/**
 * ErrorDisplay Component
 * Beautiful, user-friendly error display with retry functionality
 */
export default function ErrorDisplay({
    error,
    onRetry,
    showRetry = true,
    compact = false,
    className = ''
}) {
    if (!error) return null;

    const getIcon = () => {
        switch (error.type) {
            case 'PERMISSION_DENIED':
            case 'UNAUTHORIZED':
                return <XCircle className="w-12 h-12 text-red-500" />;
            case 'NOT_FOUND':
                return <Info className="w-12 h-12 text-blue-500" />;
            case 'NETWORK_ERROR':
            case 'TIMEOUT':
                return <AlertTriangle className="w-12 h-12 text-orange-500" />;
            default:
                return <AlertTriangle className="w-12 h-12 text-red-500" />;
        }
    };

    const getBackgroundColor = () => {
        switch (error.type) {
            case 'PERMISSION_DENIED':
            case 'UNAUTHORIZED':
                return 'bg-red-500/10 border-red-500/20';
            case 'NOT_FOUND':
                return 'bg-blue-500/10 border-blue-500/20';
            case 'NETWORK_ERROR':
            case 'TIMEOUT':
                return 'bg-orange-500/10 border-orange-500/20';
            default:
                return 'bg-red-500/10 border-red-500/20';
        }
    };

    if (compact) {
        return (
            <div className={`flex items-center gap-3 p-4 rounded-lg border-2 ${getBackgroundColor()} ${className}`}>
                <div className="flex-shrink-0">
                    {error.icon && <span className="text-2xl">{error.icon}</span>}
                </div>
                <div className="flex-1">
                    <p className="text-sm font-semibold text-foreground">{error.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{error.message}</p>
                </div>
                {showRetry && onRetry && (
                    <button
                        onClick={onRetry}
                        className="flex-shrink-0 px-3 py-1.5 bg-card border-2 border-border rounded-lg hover:bg-secondary transition-colors text-sm font-medium text-foreground"
                    >
                        Retry
                    </button>
                )}
            </div>
        );
    }

    return (
        <div className={`rounded-xl border-2 ${getBackgroundColor()} p-12 ${className}`}>
            <div className="max-w-md mx-auto text-center space-y-4">
                {/* Icon */}
                <div className="flex justify-center">
                    <div className="w-20 h-20 rounded-full bg-card flex items-center justify-center shadow-sm border border-border">
                        {getIcon()}
                    </div>
                </div>

                {/* Emoji */}
                {error.icon && (
                    <div className="text-5xl">
                        {error.icon}
                    </div>
                )}

                {/* Title */}
                <div>
                    <h3 className="text-xl font-bold text-foreground mb-2">
                        {error.title}
                    </h3>
                    <p className="text-muted-foreground font-medium">
                        {error.message}
                    </p>
                </div>

                {/* Action guidance */}
                {error.action && (
                    <p className="text-sm text-foreground bg-card/50 px-4 py-2 rounded-lg border border-border">
                        💡 {error.action}
                    </p>
                )}

                {/* Status code (for debugging) */}
                {error.statusCode && process.env.NODE_ENV === 'development' && (
                    <p className="text-xs text-slate-500 font-mono">
                        Error Code: {error.statusCode}
                    </p>
                )}

                {/* Retry button */}
                {showRetry && onRetry && (
                    <div className="pt-4">
                        <button
                            onClick={onRetry}
                            className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 transition-all font-semibold shadow-sm"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Try Again
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

/**
 * InlineError Component
 * Small inline error message for form fields
 */
export function InlineError({ message, className = '' }) {
    if (!message) return null;

    return (
        <div className={`flex items-center gap-2 mt-1 text-red-500 ${className}`}>
            <XCircle className="w-4 h-4 flex-shrink-0" />
            <span className="text-sm font-medium">{message}</span>
        </div>
    );
}

/**
 * ValidationErrors Component
 * Display multiple validation errors
 */
export function ValidationErrors({ errors, className = '' }) {
    if (!errors || errors.length === 0) return null;

    return (
        <div className={`bg-red-500/10 border-2 border-red-500/20 rounded-lg p-4 ${className}`}>
            <div className="flex items-start gap-3">
                <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                    <h4 className="text-sm font-bold text-red-700 dark:text-red-400 mb-2">
                        Please fix the following errors:
                    </h4>
                    <ul className="space-y-1">
                        {errors.map((error, index) => (
                            <li key={index} className="text-sm text-red-600 dark:text-red-300">
                                <span className="font-semibold capitalize">{error.field}:</span>{' '}
                                {Array.isArray(error.messages) ? error.messages.join(', ') : error.messages}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        </div>
    );
}
