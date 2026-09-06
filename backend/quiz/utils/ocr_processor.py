"""
OCR Processor for Handwritten Answer Recognition
Uses Tesseract OCR to extract text from images
"""
import pytesseract
from PIL import Image
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Process handwritten answers using OCR"""
    
    def __init__(self):
        # Configure Tesseract path (adjust for your system)
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass
    
    def preprocess_image(self, image_path):
        """Preprocess image for better OCR accuracy"""
        try:
            # Read image
            img = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)
            
            return denoised
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            raise
    
    def extract_text(self, image_path):
        """Extract text from image using OCR"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_path)
            
            # Perform OCR
            text = pytesseract.image_to_string(processed_img, lang='eng')
            
            # Clean text
            text = text.strip()
            
            logger.info(f"OCR extracted {len(text)} characters")
            return text
            
        except Exception as e:
            logger.error(f"OCR text extraction failed: {str(e)}")
            raise
    
    def extract_with_confidence(self, image_path):
        """Extract text with confidence scores"""
        try:
            processed_img = self.preprocess_image(image_path)
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
            
            # Extract text with confidence
            results = []
            for i, word in enumerate(data['text']):
                if word.strip():
                    results.append({
                        'text': word,
                        'confidence': data['conf'][i]
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"OCR confidence extraction failed: {str(e)}")
            raise
    
    def validate_answer(self, extracted_text, correct_answer):
        """
        Validate extracted text against correct answer
        Uses fuzzy matching for handwriting variations
        """
        from difflib import SequenceMatcher
        
        # Clean both texts
        extracted = extracted_text.lower().strip()
        correct = correct_answer.lower().strip()
        
        # Calculate similarity
        similarity = SequenceMatcher(None, extracted, correct).ratio()
        
        # Consider match if > 80% similar
        is_match = similarity > 0.8
        
        return {
            'is_match': is_match,
            'similarity': similarity,
            'extracted_text': extracted_text,
            'correct_answer': correct_answer
        }
