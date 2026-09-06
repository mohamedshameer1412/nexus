
'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

/**
 * ImageUploadField Component
 * Handles image upload with preview and removal functionality
 * 
 * Usage in QuestionsManagement.js:
 * import ImageUploadField from '@/components/ui/ImageUploadField';
 * 
 * <ImageUploadField
 *   value={formData.image}
 *   onChange={(file) => setFormData({ ...formData, image: file })}
 * />
 */
export default function ImageUploadField({ value, onChange, className = '' }) {
    const [preview, setPreview] = useState(null);

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            // Validate file size (5MB max)
            if (file.size > 5 * 1024 * 1024) {
                alert('File size must be less than 5MB');
                return;
            }

            // Validate file type
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file');
                return;
            }

            onChange(file);

            // Create preview
            const reader = new FileReader();
            reader.onloadend = () => {
                setPreview(reader.result);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleRemove = () => {
        onChange(null);
        setPreview(null);
    };

    // Handle existing image URL (for edit mode)
    const displayImage = preview || (typeof value === 'string' ? value : null);

    return (
        <div className={className}>
            <label className="block text-sm font-medium mb-2">
                Question Image (Optional)
            </label>

            <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90 cursor-pointer"
            />

            {displayImage && (
                <div className="mt-3 relative inline-block">
                    <img
                        src={displayImage}
                        alt="Question preview"
                        className="max-h-48 rounded-lg border-2 border-border shadow-md"
                    />
                    <button
                        type="button"
                        onClick={handleRemove}
                        className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground p-1.5 rounded-full hover:bg-destructive/90 shadow-lg transition-all"
                        title="Remove image"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            <p className="text-xs text-muted-foreground mt-2">
                Supported formats: JPG, PNG, GIF, WebP (Max 5MB)
            </p>
        </div>
    );
}
