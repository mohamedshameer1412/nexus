"""
Celery tasks for background processing
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_parent_report_email(user_id, report_data):
    """
    Send weekly performance report to parent
    """
    from users.models import User
    
    try:
        user = User.objects.get(id=user_id)
        
        if not user.parent_email:
            logger.warning(f"No parent email for user {user_id}")
            return False
        
        # Render email template
        html_message = render_to_string('emails/parent_report.html', {
            'student_name': user.get_full_name(),
            'report_data': report_data
        })
        
        # Send email
        send_mail(
            subject=f'Weekly Progress Report - {user.get_full_name()}',
            message='',  # Plain text version
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.parent_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Parent report sent to {user.parent_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send parent report: {str(e)}")
        return False


@shared_task
def generate_pdf_quiz(pdf_file_path, user_id):
    """
    Generate quiz from PDF file using AI
    """
    from quiz.utils.pdf_parser import PDFQuizGenerator
    
    try:
        generator = PDFQuizGenerator()
        questions = generator.generate_from_pdf(pdf_file_path, user_id)
        
        logger.info(f"Generated {len(questions)} questions from PDF")
        return {
            'success': True,
            'questions_count': len(questions),
            'questions': questions
        }
        
    except Exception as e:
        logger.error(f"Failed to generate quiz from PDF: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def process_ocr_answer(image_path, question_id):
    """
    Process handwritten answer using OCR
    """
    from quiz.utils.ocr_processor import OCRProcessor
    
    try:
        processor = OCRProcessor()
        text = processor.extract_text(image_path)
        
        logger.info(f"OCR extracted text: {text[:100]}...")
        return {
            'success': True,
            'extracted_text': text
        }
        
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def train_ml_models_periodic():
    """
    Periodic task to retrain ML models with new data
    """
    from ml_engine.train_models import train_all_models
    
    try:
        results = train_all_models()
        logger.info(f"ML models retrained: {results}")
        return results
        
    except Exception as e:
        logger.error(f"ML model training failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_quiz_reminder(user_id):
    """
    Send reminder to complete pending quizzes
    """
    from users.models import User
    from quiz.models import QuizSession
    
    try:
        user = User.objects.get(id=user_id)
        pending_sessions = QuizSession.objects.filter(
            user=user,
            is_active=True
        ).count()
        
        if pending_sessions > 0:
            send_mail(
                subject='Complete Your Pending Quizzes',
                message=f'You have {pending_sessions} pending quiz(es). Complete them to track your progress!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Quiz reminder sent to {user.email}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to send quiz reminder: {str(e)}")
        return False
