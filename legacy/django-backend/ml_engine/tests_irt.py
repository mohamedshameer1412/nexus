from django.test import TestCase
from ml_engine.irt import probability_correct, update_theta

class IRTTest(TestCase):
    def test_probability_correct_baseline(self):
        self.assertAlmostEqual(probability_correct(0, 0), 0.5, places=2)

    def test_high_ability_easy_item(self):
        prob = probability_correct(3, -3)
        self.assertTrue(prob > 0.95)

    def test_low_ability_hard_item(self):
        prob = probability_correct(-3, 3)
        self.assertTrue(prob < 0.05)

    def test_update_theta_all_correct(self):
        current_theta = 0.0
        # Correctly answered an average difficulty item
        new_theta = update_theta(current_theta, [{"difficulty": 0, "is_correct": True}])["new_theta"]
        self.assertTrue(new_theta > current_theta)

    def test_update_theta_all_wrong(self):
        current_theta = 0.0
        new_theta = update_theta(current_theta, [{"difficulty": 0, "is_correct": False}])["new_theta"]
        self.assertTrue(new_theta < current_theta)

    def test_update_theta_empty(self):
        self.assertEqual(update_theta(1.5, [])["new_theta"], 1.5)

    def test_theta_clamped(self):
        # Many correct answers on easy items shouldn't push theta past 3.0
        responses = [(-2, True)] * 20
        new_theta = update_theta(2.5, [{"difficulty": d, "is_correct": c} for d, c in responses])["new_theta"]
        self.assertTrue(new_theta <= 3.0)
