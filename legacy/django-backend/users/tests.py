from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from utils.test_utils import BaseTestCase

User = get_user_model()

class UsersTests(BaseTestCase):
    def test_user_registration(self):
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpassword123',
            'role': 'student'
        }
        # Registration should involve no auth
        self.client.credentials() 
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_user_login(self):
        url = reverse('login') # Assuming URL name is login
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        self.client.credentials() 
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_get_profile(self):
        # Assuming URL pattern for profile is /api/users/profile/ or similar
        # Need to verify actual URL structure first, but will try common pattern
        # If specific URL name is not known, I will use path
        url = '/api/users/profile/' 
        
        # Authenticated request (BaseTestCase handles auth in setUp)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)

    def test_get_profile_unauthorized(self):
        url = '/api/users/profile/'
        self.client.credentials() # Clear auth
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

