
from django.test import TestCase
from sih.models import CompetencyDomain, CompetencySkill, OfficerRole, OfficerProfile, CompetencyDigitalTwin, LearningDebtItem, IGOTCourse, TPACProgram, LearningPathway
from sih.engine import compute_learning_debt, _find_root_cause, generate_pathway, compute_promotion_readiness
import uuid
from django.contrib.auth import get_user_model

class SIHEngineTest(TestCase):
    def setUp(self):
        self.domain = CompetencyDomain.objects.create(code='DOM_A', name='Domain A', description='Test')
        self.skill_a = CompetencySkill.objects.create(domain=self.domain, name='Skill A')
        self.skill_b = CompetencySkill.objects.create(domain=self.domain, name='Skill B')
        self.skill_c = CompetencySkill.objects.create(domain=self.domain, name='Skill C')
        
        # A -> B -> C
        self.skill_b.prerequisites.add(self.skill_a)
        self.skill_c.prerequisites.add(self.skill_b)
        
        self.igot = IGOTCourse.objects.create(title='IGOT C', provider='Provider', duration_hours=1.0, is_active=True)
        self.igot.skills_covered.add(self.skill_c)
        
        self.tpac = TPACProgram.objects.create(title='TPAC C', mode='ONLINE', duration_days=1, is_active=True)
        self.tpac.skills_covered.add(self.skill_c)

        self.role = OfficerRole.objects.create(title='Test Role', required_competency_levels={'DOM_A': 80.0})
        User = get_user_model()
        self.user = User.objects.create(username='testuser_sih_' + str(uuid.uuid4())[:8])
        self.profile = OfficerProfile.objects.create(user=self.user, role=self.role)
        self.twin = CompetencyDigitalTwin.objects.create(officer=self.profile, domain_scores={'DOM_A': 50.0}, overall_competency_score=50.0)

    def test_learning_debt_computed_for_gap(self):
        compute_learning_debt(self.twin, self.profile)
        self.assertTrue(self.twin.debt_items.count() > 0)
        skill_c_debt = self.twin.debt_items.get(skill=self.skill_c)
        self.assertEqual(str(skill_c_debt.root_cause_skill.id), str(self.skill_a.id))

    def test_find_root_cause(self):
        root = _find_root_cause(self.skill_c, self.twin.domain_scores, self.role.required_competency_levels)
        self.assertIsNotNone(root)
        self.assertEqual(str(root.id), str(self.skill_a.id))

    def test_generate_pathway(self):
        compute_learning_debt(self.twin, self.profile)
        pathway = generate_pathway(self.twin, self.profile)
        self.assertIsNotNone(pathway)
        self.assertTrue(len(pathway.pathway_steps) > 0)

    def test_compute_promotion_readiness(self):
        self.twin.overall_competency_score = 90.0
        self.twin.save()
        readiness = compute_promotion_readiness(self.twin, self.profile)
        self.assertTrue(readiness >= 40.0)
