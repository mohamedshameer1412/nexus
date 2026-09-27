import pdfplumber
import os

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file or file-like object.
        
    Returns:
        String containing extracted text.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""
    
    return text.strip()
