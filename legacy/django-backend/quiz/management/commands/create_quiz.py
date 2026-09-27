from django.core.management.base import BaseCommand
from quiz.models import Topic, Subtopic, Question, Quiz
from users.models import User


class Command(BaseCommand):
    help = 'Create a sample quiz for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample quiz...')
        
        # Get or create a user
        user = User.objects.filter(role='teacher').first()
        if not user:
            user = User.objects.filter(is_staff=True).first()
        if not user:
            user = User.objects.first()
        
        # Get topics
        math = Topic.objects.filter(name='Mathematics').first()
        
        if not math:
            self.stdout.write(self.style.ERROR('No topics found. Run seed_db first.'))
            return
        
        # Create quiz
        quiz, created = Quiz.objects.get_or_create(
            id=1,
            defaults={
                'title': 'Mathematics Quiz',
                'description': 'Basic mathematics quiz for testing',
                'total_questions': 10,
                'time_limit': 30,
                'is_adaptive': True,
                'created_by': user
            }
        )
        
        if created:
            quiz.topics.add(math)
            self.stdout.write(self.style.SUCCESS(f'Created quiz: {quiz.title}'))
        else:
            self.stdout.write(self.style.WARNING(f'Quiz already exists: {quiz.title}'))
        
        self.stdout.write(self.style.SUCCESS('Sample quiz ready!'))
