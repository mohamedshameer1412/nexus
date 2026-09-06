"""
Syllabus AI extraction task.
Runs in a background thread (no Celery required for MVP).
Uses Gemini Flash to parse raw text into structured JSON roadmap.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)


def extract_syllabus_task(upload_id: str):
    """Background task: extract syllabus structure from uploaded file."""
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    from .models import SyllabusUpload, SyllabusRoadmap

    try:
        upload = SyllabusUpload.objects.get(id=upload_id)
    except SyllabusUpload.DoesNotExist:
        logger.error(f"SyllabusUpload {upload_id} not found.")
        return

    upload.status = 'processing'
    upload.save(update_fields=['status'])

    try:
        # Step 1: Extract raw text from file
        raw_text = _extract_text(upload)
        if not raw_text:
            raise ValueError("Could not extract text from file.")

        upload.raw_extracted_text = raw_text
        upload.save(update_fields=['raw_extracted_text'])

        # Step 2: AI structure extraction via Gemini
        roadmap_json = _gemini_extract(raw_text, upload.subject_name)

        # Step 3: Save roadmap
        roadmap, _ = SyllabusRoadmap.objects.get_or_create(upload=upload)
        roadmap.roadmap_json = roadmap_json
        roadmap.subject = upload.subject
        roadmap.save()
        roadmap.compute_stats()

        upload.status = 'done'
        upload.save(update_fields=['status'])
        logger.info(f"Syllabus extraction done for upload {upload_id}")

    except Exception as e:
        logger.error(f"Syllabus extraction failed for {upload_id}: {e}")
        upload.status = 'error'
        upload.error_message = str(e)
        upload.save(update_fields=['status', 'error_message'])


def _extract_text(upload) -> str:
    """Extract raw text from PDF or image file."""
    import os
    file_path = upload.file.path
    ext = upload.file_type.lower()

    if ext == 'pdf':
        return _extract_from_pdf(file_path)
    elif ext in ('jpg', 'jpeg', 'png', 'webp', 'bmp'):
        return _extract_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _extract_from_pdf(file_path: str) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return '\n'.join(text_parts)
    except ImportError:
        raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")


def _extract_from_image(file_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file_path)
        return pytesseract.image_to_string(img)
    except ImportError:
        raise ImportError("pytesseract not installed. Run: pip install pytesseract Pillow")


def _gemini_extract(raw_text: str, subject_name: str) -> dict:
    """Call Gemini Flash to convert raw text into structured roadmap JSON."""
    import google.generativeai as genai

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""You are an expert at parsing academic syllabuses.

Extract the complete structure from this {subject_name} syllabus text and return ONLY valid JSON.

Return this exact structure:
{{
  "units": [
    {{
      "name": "Unit I: <Unit Title>",
      "topics": [
        {{
          "name": "<Topic Name>",
          "subtopics": ["<subtopic 1>", "<subtopic 2>"],
          "lab": ["<lab exercise if any>"]
        }}
      ]
    }}
  ]
}}

Rules:
- Include ALL units, topics, subtopics mentioned in the syllabus
- Preserve the original unit numbering/naming
- If no subtopics are listed, use an empty array []
- If no lab exercises, use an empty array []
- Return ONLY the JSON object, no explanation, no markdown

Syllabus text:
---
{raw_text[:8000]}
---"""

    response = model.generate_content(prompt)
    raw_response = response.text.strip()

    # Clean markdown code blocks if present
    if raw_response.startswith('```'):
        lines = raw_response.split('\n')
        raw_response = '\n'.join(lines[1:-1])

    return json.loads(raw_response)
