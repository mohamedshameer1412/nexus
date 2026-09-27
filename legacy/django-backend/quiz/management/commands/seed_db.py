from django.core.management.base import BaseCommand
from quiz.models import Topic, Subtopic, Question
from users.models import User
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = 'Seed database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')
        
        # Create topics
        math = Topic.objects.get_or_create(name='Mathematics', defaults={'description': 'Math concepts'})[0]
        science = Topic.objects.get_or_create(name='Science', defaults={'description': 'Science topics'})[0]
        english = Topic.objects.get_or_create(name='English', defaults={'description': 'Language arts'})[0]
        
        # Create subtopics
        algebra = Subtopic.objects.get_or_create(topic=math, name='Algebra', defaults={'description': 'Algebraic expressions'})[0]
        geometry = Subtopic.objects.get_or_create(topic=math, name='Geometry', defaults={'description': 'Shapes and angles'})[0]
        physics = Subtopic.objects.get_or_create(topic=science, name='Physics', defaults={'description': 'Laws of motion'})[0]
        grammar = Subtopic.objects.get_or_create(topic=english, name='Grammar', defaults={'description': 'Sentence structure'})[0]
        
        # Create sample questions
        Question.objects.get_or_create(
            topic=math, subtopic=algebra,
            question_text='Solve for x: 2x + 5 = 15',
            defaults={
                'option_a': 'x = 5', 'option_b': 'x = 10', 'option_c': 'x = 7.5', 'option_d': 'x = 20',
                'correct_answer': 'A', 'difficulty_level': 2,
                'explanation': 'Subtract 5 from both sides: 2x = 10, then divide by 2: x = 5'
            }
        )
        
        Question.objects.get_or_create(
            topic=math, subtopic=geometry,
            question_text='What is the sum of angles in a triangle?',
            defaults={
                'option_a': '90 degrees', 'option_b': '180 degrees', 'option_c': '270 degrees', 'option_d': '360 degrees',
                'correct_answer': 'B', 'difficulty_level': 1,
                'explanation': 'The sum of all angles in any triangle is always 180 degrees'
            }
        )
        
        # Create test users
        User.objects.get_or_create(
            username='student1',
            defaults={'email': 'student1@test.com', 'role': 'student', 'password': make_password('test123')}
        )
        
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
        self.stdout.write(f'Topics: {Topic.objects.count()}')
        self.stdout.write(f'Subtopics: {Subtopic.objects.count()}')
        self.stdout.write(f'Questions: {Question.objects.count()}')
        self.stdout.write(f'Users: {User.objects.count()}')
