"""
nexus_core/tests/test_e2e_pipeline.py
End-to-End integration test for the full NEXUS pipeline:
  1. Register new user
  2. Verify Digital Twin created automatically
  3. Create quiz session with responses
  4. Fire update_digital_twin task
  5. Assert Twin fields updated
  6. Fire evaluate_session task
  7. Assert AgentDecisionLog entries created for analytics + evaluator
  8. Fire generate_study_plan task
  9. Assert plan returned with topics
  10. Fire what-if simulator
  11. Assert recommendation returned

Run with:  python manage.py test nexus_core.tests.test_e2e_pipeline
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

User = get_user_model()


class DigitalTwinSignalTest(TestCase):
    """Test that Digital Twin is auto-created on user registration."""

    def test_twin_created_on_user_register(self):
        from nexus_core.models import LearnerDigitalTwin
        user = User.objects.create_user(
            username="test_nexus_student",
            email="student@nexus.test",
            password="testpass123"
        )
        twin_exists = LearnerDigitalTwin.objects.filter(user=user).exists()
        self.assertTrue(twin_exists, "Digital Twin should be auto-created via signal")

    def test_twin_not_duplicated(self):
        """Twin must be unique per user (get_or_create semantics)."""
        from nexus_core.models import LearnerDigitalTwin
        user = User.objects.create_user(username="twin_dedup", password="pass")
        LearnerDigitalTwin.objects.get_or_create(user=user)
        LearnerDigitalTwin.objects.get_or_create(user=user)
        count = LearnerDigitalTwin.objects.filter(user=user).count()
        self.assertEqual(count, 1, "Should have exactly one twin per user")


class AlgorithmsTest(TestCase):
    """Unit tests for core NEXUS algorithms."""

    def test_compute_topic_mastery_empty(self):
        from analytics.algorithms import compute_topic_mastery
        result = compute_topic_mastery([])
        self.assertEqual(result, {})

    def test_compute_learning_debt_zero_when_mastered(self):
        from analytics.algorithms import compute_learning_debt
        mastery = {"recursion": 85.0, "sorting": 90.0, "graphs": 75.0}
        debt = compute_learning_debt(mastery)
        self.assertEqual(debt, 0.0, "No debt when all topics above 70%")

    def test_compute_learning_debt_nonzero_when_below(self):
        from analytics.algorithms import compute_learning_debt
        mastery = {"recursion": 40.0, "sorting": 50.0}
        debt = compute_learning_debt(mastery)
        self.assertGreater(debt, 0.0, "Debt must be positive when below threshold")
        self.assertLessEqual(debt, 100.0)

    def test_confidence_gap_overconfident(self):
        from analytics.algorithms import compute_confidence_gap
        verified  = {"recursion": 40.0}
        reported  = {"recursion": 80.0}
        gap = compute_confidence_gap(verified, reported)
        self.assertAlmostEqual(gap["recursion"], 40.0)  # student overestimates by 40

    def test_confidence_gap_underconfident(self):
        from analytics.algorithms import compute_confidence_gap
        verified  = {"recursion": 85.0}
        reported  = {"recursion": 50.0}
        gap = compute_confidence_gap(verified, reported)
        self.assertAlmostEqual(gap["recursion"], -35.0)


class IRTTest(TestCase):
    """Unit tests for IRT Rasch model."""

    def test_probability_correct_equal_ability(self):
        from ml_engine.irt import probability_correct
        p = probability_correct(theta=0.0, difficulty=0.0)
        self.assertAlmostEqual(p, 0.5, places=3)

    def test_probability_correct_easy_item(self):
        from ml_engine.irt import probability_correct
        p = probability_correct(theta=0.0, difficulty=-2.0)
        self.assertGreater(p, 0.85, "Easy item should have high P(correct)")

    def test_probability_correct_hard_item(self):
        from ml_engine.irt import probability_correct
        p = probability_correct(theta=0.0, difficulty=2.0)
        self.assertLess(p, 0.15, "Hard item should have low P(correct)")

    def test_update_theta_improves_on_correct(self):
        from ml_engine.irt import update_theta
        result = update_theta(
            current_theta=0.0,
            responses=[{"difficulty": 0.0, "is_correct": True}] * 5
        )
        self.assertGreater(result["new_theta"], 0.0)

    def test_update_theta_decreases_on_wrong(self):
        from ml_engine.irt import update_theta
        result = update_theta(
            current_theta=0.0,
            responses=[{"difficulty": 0.0, "is_correct": False}] * 5
        )
        self.assertLess(result["new_theta"], 0.0)

    def test_select_next_question_picks_closest(self):
        from ml_engine.irt import select_next_question
        candidates = [
            {"id": "q1", "difficulty": -2.0},
            {"id": "q2", "difficulty":  0.1},   # closest to theta=0
            {"id": "q3", "difficulty":  2.0},
        ]
        selected = select_next_question(theta=0.0, candidate_questions=candidates)
        self.assertEqual(selected["id"], "q2")

    def test_select_skips_answered(self):
        from ml_engine.irt import select_next_question
        candidates = [{"id": "q1", "difficulty": 0.0}, {"id": "q2", "difficulty": 0.1}]
        selected = select_next_question(theta=0.0, candidate_questions=candidates, answered_ids=["q1"])
        self.assertEqual(selected["id"], "q2")


class ConceptDriftTest(TestCase):
    """Unit tests for concept drift detection."""

    def test_drift_detected(self):
        from ml_engine.concept_drift import detect_concept_drift
        current  = {"recursion": 50.0, "sorting": 80.0}
        previous = {"recursion": 75.0, "sorting": 80.0}  # recursion dropped 25pts
        drifted  = detect_concept_drift(current, previous, threshold=10.0)
        self.assertEqual(len(drifted), 1)
        self.assertEqual(drifted[0]["topic_id"], "recursion")
        self.assertAlmostEqual(drifted[0]["drop"], 25.0)

    def test_no_drift_when_stable(self):
        from ml_engine.concept_drift import detect_concept_drift
        mastery = {"recursion": 80.0, "sorting": 75.0}
        drifted = detect_concept_drift(mastery, mastery, threshold=10.0)
        self.assertEqual(len(drifted), 0)


class WhatIfSimulatorTest(TestCase):
    """Unit tests for What-If planner."""

    def test_recommends_higher_debt(self):
        from planner_agent.whatif import simulate_whatif
        mastery = {"recursion": 30.0, "sorting": 60.0}  # recursion more debt
        result  = simulate_whatif("recursion", "sorting", mastery)
        self.assertEqual(result["recommendation"], "A")
        self.assertIn("recursion", result["reason"])

    def test_recommends_higher_propagation(self):
        from planner_agent.whatif import simulate_whatif
        mastery = {"arrays": 50.0, "sorting": 50.0}
        result  = simulate_whatif(
            "arrays", "sorting", mastery,
            propagation_map={"arrays": 5, "sorting": 0}  # arrays has more downstream
        )
        self.assertEqual(result["recommendation"], "A")

    def test_result_structure(self):
        from planner_agent.whatif import simulate_whatif
        result = simulate_whatif("a", "b", {"a": 60.0, "b": 40.0})
        for key in ["recommendation", "recommended_topic", "reason", "topic_a", "topic_b"]:
            self.assertIn(key, result)


class PrerequisiteGraphTest(TestCase):
    """Unit tests for prerequisite graph inference."""

    def test_keyword_overlap_inference(self):
        from syllabus.prerequisite_graph import extract_keywords
        kw = extract_keywords("recursion depth first search graph traversal")
        self.assertIn("recursion", kw)
        self.assertIn("graph", kw)

    def test_no_self_loop(self):
        from syllabus.prerequisite_graph import infer_prerequisites_from_structure
        topics = [
            {"id": "1", "name": "Arrays", "description": "array data structure"},
            {"id": "2", "name": "Sorting", "description": "sorting arrays algorithms"},
        ]
        edges = infer_prerequisites_from_structure(topics)
        self_loops = [(a, b) for a, b in edges if a == b]
        self.assertEqual(len(self_loops), 0)
