'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';

export default function CustomSelect({
    options,
    value,
    onChange,
    placeholder = "Select an option",
    label,
    className = "",
    required = false
}) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    const selectedOption = options.find(opt => opt.value === value);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelect = (val) => {
        onChange(val);
        setIsOpen(false);
    };

    return (
        <div className={`relative ${className}`} ref={dropdownRef}>
            {label && (
                <label className="block text-xs font-black text-muted-foreground uppercase tracking-widest mb-3">
                    {label} {required && <span className="text-primary">*</span>}
                </label>
            )}

            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className={`w-full px-5 py-4 rounded-2xl border transition-all flex items-center justify-between font-bold text-left outline-none focus:ring-2 focus:ring-primary/50 group ${isOpen
                        ? 'border-primary bg-black/40 ring-2 ring-primary/20'
                        : 'border-white/10 bg-black/20 hover:border-white/20 hover:bg-black/30'
                    }`}
            >
                <span className={selectedOption ? "text-foreground" : "text-muted-foreground"}>
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <ChevronDown className={`w-5 h-5 text-muted-foreground transition-transform duration-200 ${isOpen ? 'rotate-180 text-primary' : 'group-hover:text-foreground'}`} />
            </button>

            {isOpen && (
                <div className="absolute z-50 w-full mt-2 bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 origin-top backdrop-blur-xl">
                    <div className="max-h-60 overflow-y-auto p-1 custom-scrollbar">
                        {options.length > 0 ? (
                            options.map((option) => (
                                <button
                                    key={option.value}
                                    type="button"
                                    onClick={() => handleSelect(option.value)}
                                    className={`w-full px-4 py-3 text-left text-sm font-medium rounded-lg transition-colors flex items-center justify-between group ${value === option.value
                                            ? 'bg-primary/20 text-primary'
                                            : 'text-foreground/80 hover:bg-white/5 hover:text-foreground'
                                        }`}
                                >
                                    {option.label}
                                    {value === option.value && (
                                        <Check className="w-4 h-4 text-primary" />
                                    )}
                                </button>
                            ))
                        ) : (
                            <div className="px-4 py-3 text-sm text-muted-foreground text-center italic">
                                No options available
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
