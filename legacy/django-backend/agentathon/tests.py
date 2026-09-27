from django.test import TestCase
from unittest.mock import patch, MagicMock
from agentathon.models import AgentathonSession, AgentLog
from agentathon.pipeline import run_real_agent_pipeline
import os

class AgentathonPipelineTest(TestCase):
    def setUp(self):
        self.session_id = "test_session_001"
        self.session = AgentathonSession.objects.create(session_id=self.session_id)
        
        # Create a dummy file
        self.test_file_path = "dummy_test.pdf"
        with open(self.test_file_path, "w") as f:
            f.write("dummy PDF content")

    def tearDown(self):
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)

    @patch('agentathon.pipeline.content_agent_extract')
    @patch('agentathon.pipeline.tutor_agent_summarize')
    @patch('agentathon.pipeline.evaluator_agent_quiz')
    @patch('agentathon.pipeline.analytics_agent_diagnose')
    @patch('agentathon.pipeline.planner_agent_pathway')
    @patch('agentathon.pipeline.mentor_agent_motivate')
    def test_pipeline_success(self, mock_mentor, mock_planner, mock_analytics, mock_evaluator, mock_tutor, mock_content):
        # Setup mocks
        mock_content.return_value = "Extracted test text"
        mock_tutor.return_value = ["Concept A", "Concept B"]
        mock_evaluator.return_value = [{"id": "q1", "question": "Q?", "options": ["A", "B"], "correct": "A", "explanation": "E"}]
        mock_analytics.return_value = "Diagnosis gap"
        mock_planner.return_value = [{"id": "p1", "title": "Test Course", "type": "Course", "duration": "1hr"}]
        mock_mentor.return_value = "You can do it!"

        # Run pipeline
        run_real_agent_pipeline(self.session_id, self.test_file_path)

        # Assertions
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "completed")
        self.assertEqual(len(self.session.quiz_data), 1)
        self.assertEqual(len(self.session.pathway_data), 1)
        
        # Check logs
        logs = AgentLog.objects.filter(session=self.session)
        self.assertTrue(logs.count() > 0)
        
        # Ensure file was cleaned up
        self.assertFalse(os.path.exists(self.test_file_path))

    @patch('agentathon.pipeline.content_agent_extract')
    def test_pipeline_failure(self, mock_content):
        # Simulate extraction failure
        mock_content.return_value = ""

        run_real_agent_pipeline(self.session_id, self.test_file_path)

        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "error")
        
        error_logs = AgentLog.objects.filter(session=self.session, agent_name="system")
        self.assertTrue(error_logs.exists())
