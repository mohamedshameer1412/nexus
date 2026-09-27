from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class BaseTestCase(APITestCase):
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
            'role': 'student'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.token = self.get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def create_teacher_user(self):
        teacher_data = {
            'username': 'teacheruser',
            'email': 'teacher@example.com',
            'password': 'teacherpassword123',
            'role': 'teacher'
        }
        return User.objects.create_user(**teacher_data)

    def authenticate_as_teacher(self):
        self.teacher = self.create_teacher_user()
        token = self.get_tokens_for_user(self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return self.teacher
