"""
PDF to Quiz Generator
Extracts text from PDF and generates quiz questions using AI
"""
import PyPDF2
from google import genai
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)


class PDFQuizGenerator:
    """Generate quiz questions from PDF content"""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = 'gemini-3.6-flash'
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text content from PDF file"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            
            return text.strip()
        except Exception as e:
            logger.error(f"PDF text extraction failed: {str(e)}")
            raise
    
    def generate_questions_from_text(self, text, num_questions=10, difficulty='medium'):
        """Generate quiz questions from text using AI"""
        
        prompt = f"""
        Based on the following text, generate {num_questions} multiple-choice quiz questions.
        Difficulty level: {difficulty}
        
        TEXT:
        {text[:4000]}  # Limit to avoid token limits
        
        Generate questions in JSON format:
        [
            {{
                "question_text": "Question here?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "correct_answer": "A",
                "explanation": "Why this is correct",
                "difficulty_level": 3,
                "topic": "Main topic"
            }}
        ]
        
        Return ONLY valid JSON array, no additional text.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            text_response = response.text.strip()
            
            # Extract JSON from response
            if '```json' in text_response:
                text_response = text_response.split('```json')[1].split('```')[0].strip()
            elif '```' in text_response:
                text_response = text_response.split('```')[1].split('```')[0].strip()
            
            questions = json.loads(text_response)
            return questions
            
        except Exception as e:
            logger.error(f"Question generation failed: {str(e)}")
            raise
    
    def generate_from_pdf(self, pdf_path, user_id, num_questions=10):
        """Complete pipeline: PDF -> Questions"""
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text:
            raise ValueError("No text extracted from PDF")
        
        # Generate questions
        questions = self.generate_questions_from_text(text, num_questions)
        
        # Save to database
        from quiz.models import Question, Topic, Subtopic
        from users.models import User
        
        saved_questions = []
        user = User.objects.get(id=user_id)
        
        for q_data in questions:
            # Get or create topic
            topic, _ = Topic.objects.get_or_create(
                name=q_data.get('topic', 'General'),
                defaults={'description': f'Generated from PDF'}
            )
            
            # Create question
            question = Question.objects.create(
                topic=topic,
                question_text=q_data['question_text'],
                option_a=q_data['option_a'],
                option_b=q_data['option_b'],
                option_c=q_data['option_c'],
                option_d=q_data['option_d'],
                correct_answer=q_data['correct_answer'],
                explanation=q_data.get('explanation', ''),
                difficulty_level=q_data.get('difficulty_level', 3),
                irt_difficulty=0.0,
                irt_discrimination=1.0
            )
            
            saved_questions.append(question)
        
        logger.info(f"Saved {len(saved_questions)} questions from PDF")
        return saved_questions
