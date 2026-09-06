
"""
Auto-Grading Management Command
Usage: python manage.py auto_grade_responses
"""
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management.base import BaseCommand
from quiz.models import Response, Question
from utils.gemini_service import get_gemini_service

class Command(BaseCommand):
    help = 'Auto-grade pending text-based responses using Gemini AI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of responses to grade in one run'
        )
        parser.add_argument(
            '--question-id',
            type=str,
            help='Grade responses for a specific question only'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        question_id = options.get('question_id')
        
        # Get pending responses for text-based questions
        filters = {
            'question__question_type__in': ['short_answer', 'essay'],
            'question__auto_grade': True,
            'grading_status': 'pending'
        }
        
        if question_id:
            filters['question_id'] = question_id
        
        pending_responses = Response.objects.filter(**filters).select_related('question')[:limit]
        
        if not pending_responses:
            self.stdout.write(self.style.SUCCESS('No pending responses to grade.'))
            return
        
        self.stdout.write(f'Found {pending_responses.count()} pending responses to grade...')
        
        gemini = get_gemini_service()
        graded_count = 0
        failed_count = 0
        
        for response in pending_responses:
            question = response.question
            
            try:
                self.stdout.write(f'\nGrading response {response.id} for question: {question.question_text[:50]}...')
                
                result = gemini.grade_text_answer(
                    question_text=question.question_text,
                    student_answer=response.text_answer or '',
                    model_answer=question.model_answer or '',
                    required_keywords=question.required_keywords or [],
                    max_score=100
                )
                
                # Update response with AI grading
                response.ai_score = result['score']
                response.ai_feedback = result['feedback']
                response.is_correct = result['is_correct']
                response.grading_status = 'graded'
                response.save()
                
                graded_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Graded: {result["score"]}/100'))
                
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Failed: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n\nGrading Complete:'))
        self.stdout.write(f'  Successfully graded: {graded_count}')
        self.stdout.write(f'  Failed: {failed_count}')
