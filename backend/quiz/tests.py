from django.urls import reverse
from rest_framework import status
from utils.test_utils import BaseTestCase
from quiz.models import Topic, Quiz, Question

class QuizTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.teacher = self.authenticate_as_teacher()
        self.topic = Topic.objects.create(name='Math', created_by=self.teacher)
        self.quiz = Quiz.objects.create(
            title='Math Quiz',
            created_by=self.teacher,
            total_questions=5,
            is_active=True
        )
        self.quiz.topics.add(self.topic)
        
        # Create a question
        self.question = Question.objects.create(
            topic=self.topic,
            question_text='What is 2+2?',
            question_type='mcq',
            option_a='3',
            option_b='4',
            option_c='5',
            option_d='6',
            correct_answer='B',
            created_by=self.teacher
        )

    def test_create_quiz_teacher(self):
        url = '/api/quiz/quizzes/'
        data = {
            'title': 'New Quiz',
            'topics': [self.topic.id],
            'total_questions': 10,
            'is_active': True
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_student_get_quizzes(self):
        # Switch to student
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        url = '/api/quiz/quizzes/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see the active quiz
        self.assertTrue(len(response.data) > 0)

    def test_start_quiz_session(self):
        # Switch to student
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        url = '/api/quiz/sessions/'
        data = {'quiz_id': self.quiz.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)

    def test_create_quiz_student_unauthorized(self):
        # Switch to student
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        url = '/api/quiz/quizzes/'
        data = {
            'title': 'Student Quiz',
            'topics': [self.topic.id]
        }
        response = self.client.post(url, data, format='json')
        # Assuming only teachers can create quizzes
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

