import { useState, useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

export default function Toast({ message, type = 'success', duration = 3000, onClose }) {
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsVisible(false);
            setTimeout(onClose, 300); // Wait for fade out animation
        }, duration);

        return () => clearTimeout(timer);
    }, [duration, onClose]);

    const icons = {
        success: <CheckCircle className="w-5 h-5 text-green-500" />,
        error: <AlertCircle className="w-5 h-5 text-red-500" />,
        info: <Info className="w-5 h-5 text-blue-500" />
    };

    const bgColors = {
        success: 'bg-zinc-900 text-white border-l-4 border-l-green-500 shadow-2xl',
        error: 'bg-zinc-900 text-white border-l-4 border-l-red-500 shadow-2xl',
        info: 'bg-zinc-900 text-white border-l-4 border-l-blue-500 shadow-2xl'
    };

    return (
        <div
            className={`fixed z-[10050] flex items-center gap-3 px-5 py-4 rounded-xl border shadow-2xl transition-all duration-300 text-base font-semibold ${
                // Mobile: Top-Center
                'top-6 left-1/2 -translate-x-1/2 w-[95%] max-w-md ' +
                // Desktop (md and up): Top-Right
                'md:left-auto md:right-8 md:translate-x-0 md:w-auto ' +
                (isVisible
                    ? 'opacity-100 translate-y-0'
                    : 'opacity-0 -translate-y-2')
                } ${bgColors[type]}`}
            style={{ pointerEvents: 'auto', boxShadow: '0 8px 32px 0 rgba(0,0,0,0.25)', wordBreak: 'break-word' }}
        >
            {icons[type]}
            <p className="text-sm font-medium">{message}</p>
            <button
                onClick={() => {
                    setIsVisible(false);
                    setTimeout(onClose, 300);
                }}
                className="ml-2 hover:opacity-70 transition-opacity"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    );
}
