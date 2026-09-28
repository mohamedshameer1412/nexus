from django.urls import reverse
from rest_framework import status
from utils.test_utils import BaseTestCase

class AnalyticsTests(BaseTestCase):
    def test_get_dashboard_data(self):
        # Using default router, action 'dashboard' usually maps to /api/analytics/dashboard/
        url = '/api/analytics/dashboard/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_sessions', response.data)
        self.assertIn('average_score', response.data)

    def test_get_performance_trends(self):
        url = '/api/analytics/performance-trends/'
        response = self.client.get(url)
        # Even with no data, it should return 200 or a specific message structure
        # Based on view logic: returns 200 with message if < 2 sessions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_get_weak_topics(self):
        url = '/api/analytics/weak-topics/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('weak_topics', response.data)

    def test_predict_performance(self):
        url = '/api/analytics/predict-performance/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthorized_access(self):
        self.client.credentials() # Clear auth
        url = '/api/analytics/dashboard/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

