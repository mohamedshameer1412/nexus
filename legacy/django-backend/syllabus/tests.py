from django.test import TestCase
from syllabus.prerequisite_graph import infer_prerequisites_from_structure, infer_prerequisites_from_keywords

class PrerequisiteGraphTest(TestCase):
    def test_infer_prerequisites_from_structure(self):
        # topic_list is a list of dicts with id, name, description
        topic_list = [
            {"id": "1", "name": "1. Introduction to ML", "description": ""},
            {"id": "2", "name": "1.1 Linear Regression", "description": ""},
            {"id": "3", "name": "1.2 Logistic Regression", "description": ""},
            {"id": "4", "name": "2. Advanced ML", "description": ""}
        ]
        edges = infer_prerequisites_from_structure(topic_list)
        self.assertTrue(isinstance(edges, list))

    def test_infer_prerequisites_from_keywords(self):
        topic_list = [
            {"id": "A", "name": "Variables", "description": "Learn about variables"},
            {"id": "B", "name": "Loops", "description": "Uses variables to count"}
        ]
        edges = infer_prerequisites_from_keywords(topic_list)
        # B mentions variables, A is named Variables, so A -> B
        self.assertIn(("A", "B"), edges)
