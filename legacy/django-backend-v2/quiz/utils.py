"""
Utility functions for image processing and CSV handling
"""
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import os
import re
import sys


def sanitize_filename(filename):
    """
    Sanitize filename to prevent path traversal attacks
    """
    # Remove any path components
    filename = os.path.basename(filename)
    # Remove any non-alphanumeric characters except dots, dashes, and underscores
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Remove multiple dots
    filename = re.sub(r'\.+', '.', filename)
    return filename


def validate_image(image_file):
    """
    Validate image file type and size
    Returns: (is_valid, error_message)
    """
    # Check file size (2MB max)
    max_size = 2 * 1024 * 1024  # 2MB in bytes
    if image_file.size > max_size:
        return False, f"Image size ({image_file.size / 1024 / 1024:.2f}MB) exceeds maximum allowed size (2MB)"
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    file_ext = os.path.splitext(image_file.name)[1].lower()
    if file_ext not in allowed_extensions:
        return False, f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
    
    # Verify it's actually an image
    try:
        img = Image.open(image_file)
        img.verify()
        return True, None
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"


def compress_image(image_file, max_size_mb=2):
    """
    Compress image if it exceeds max size
    Returns: compressed image file
    """
    try:
        # Open image
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Calculate target size
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # If image is already small enough, return original
        if image_file.size <= max_size_bytes:
            image_file.seek(0)
            return image_file
        
        # Compress image
        output = BytesIO()
        quality = 85
        
        # Try different quality levels until size is acceptable
        while quality > 20:
            output.seek(0)
            output.truncate()
            
            # Save with current quality
            img.save(output, format='JPEG', quality=quality, optimize=True)
            
            # Check size
            if output.tell() <= max_size_bytes:
                break
            
            quality -= 5
        
        # Create new InMemoryUploadedFile
        output.seek(0)
        compressed_file = InMemoryUploadedFile(
            output,
            'ImageField',
            f"{os.path.splitext(image_file.name)[0]}.jpg",
            'image/jpeg',
            sys.getsizeof(output),
            None
        )
        
        return compressed_file
    
    except Exception as e:
        # If compression fails, return original
        image_file.seek(0)
        return image_file


def validate_csv_row(row, topics_dict):
    """
    Validate a single CSV row for question import
    Returns: (is_valid, error_message, cleaned_data)
    """
    required_fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'topic_name', 'difficulty_level']
    
    # Check required fields
    for field in required_fields:
        if field not in row or not row[field]:
            return False, f"Missing required field: {field}", None
    
    # Validate correct_answer
    if row['correct_answer'].upper() not in ['A', 'B', 'C', 'D']:
        return False, f"Invalid correct_answer: {row['correct_answer']}. Must be A, B, C, or D", None
    
    # Validate difficulty_level
    try:
        difficulty = int(row['difficulty_level'])
        if difficulty < 1 or difficulty > 5:
            return False, f"Invalid difficulty_level: {difficulty}. Must be between 1 and 5", None
    except ValueError:
        return False, f"Invalid difficulty_level: {row['difficulty_level']}. Must be a number", None
    
    # Get or validate topic
    topic_name = row['topic_name'].strip()
    if topic_name not in topics_dict:
        return False, f"Topic not found: {topic_name}", None
    
    # Clean data
    cleaned_data = {
        'question_text': row['question_text'].strip(),
        'option_a': row['option_a'].strip(),
        'option_b': row['option_b'].strip(),
        'option_c': row['option_c'].strip(),
        'option_d': row['option_d'].strip(),
        'correct_answer': row['correct_answer'].upper(),
        'topic': topics_dict[topic_name],
        'difficulty_level': difficulty,
        'explanation': row.get('explanation', '').strip() if 'explanation' in row else ''
    }
    
    return True, None, cleaned_data
