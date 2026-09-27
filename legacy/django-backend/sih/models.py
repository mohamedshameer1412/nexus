import uuid
from django.db import models
from django.conf import settings


class CompetencyDomain(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.IntegerField(default=0)
    class Meta:
        db_table = 'sih_competency_domains'
        ordering = ['order']
    def __str__(self): return self.name


class CompetencySkill(models.Model):
    LEVEL_CHOICES = [(1, 'Awareness'), (2, 'Working'), (3, 'Practitioner'), (4, 'Expert')]
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    domain = models.ForeignKey(CompetencyDomain, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    required_level = models.IntegerField(choices=LEVEL_CHOICES, default=2)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependent_skills')
    class Meta:
        db_table = 'sih_competency_skills'
    def __str__(self): return self.name


class OfficerRole(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    title = models.CharField(max_length=100)
    grade = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=100, blank=True)
    required_competency_levels = models.JSONField(default=dict)
    class Meta:
        db_table = 'sih_officer_roles'
    def __str__(self): return self.title


class OfficerProfile(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='officer_profile')
    role = models.ForeignKey(OfficerRole, null=True, on_delete=models.SET_NULL, related_name='officers')
    employee_id = models.CharField(max_length=50, blank=True)
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    years_of_experience = models.IntegerField(default=0)
    current_assignment = models.CharField(max_length=200, blank=True)
    career_goal = models.CharField(max_length=200, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'sih_officer_profiles'
    def __str__(self): return self.designation


class DiagnosticQuestion(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    domain = models.ForeignKey(CompetencyDomain, on_delete=models.CASCADE, related_name='diagnostic_questions')
    skill = models.ForeignKey(CompetencySkill, null=True, blank=True, on_delete=models.SET_NULL, related_name='diagnostic_questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=300)
    option_b = models.CharField(max_length=300)
    option_c = models.CharField(max_length=300, blank=True)
    option_d = models.CharField(max_length=300, blank=True)
    correct_answer = models.CharField(max_length=1)
    explanation = models.TextField(blank=True)
    difficulty = models.IntegerField(default=2)
    class Meta:
        db_table = 'sih_diagnostic_questions'
    def __str__(self): return self.question_text[:60]


class DiagnosticSession(models.Model):
    STATUS_CHOICES = [('in_progress', 'In Progress'), ('completed', 'Completed')]
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    officer = models.ForeignKey(OfficerProfile, on_delete=models.CASCADE, related_name='diagnostic_sessions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    domain_scores = models.JSONField(default=dict)
    overall_score = models.FloatField(default=0.0)
    responses = models.JSONField(default=list)
    class Meta:
        db_table = 'sih_diagnostic_sessions'
        ordering = ['-started_at']
    def __str__(self): return str(self.officer)


class CompetencyDigitalTwin(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    officer = models.OneToOneField(OfficerProfile, on_delete=models.CASCADE, related_name='competency_twin')
    domain_scores = models.JSONField(default=dict)
    skill_evidence = models.JSONField(default=dict)
    learning_history = models.JSONField(default=list)
    error_patterns = models.JSONField(default=dict)
    overall_competency_score = models.FloatField(default=0.0)
    learning_debt_score = models.FloatField(default=0.0)
    promotion_readiness_score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'sih_competency_twins'
    def __str__(self): return str(self.officer)


class LearningDebtItem(models.Model):
    PRIORITY_CHOICES = [('critical', 'Critical'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    twin = models.ForeignKey(CompetencyDigitalTwin, on_delete=models.CASCADE, related_name='debt_items')
    skill = models.ForeignKey(CompetencySkill, on_delete=models.CASCADE)
    gap_score = models.FloatField()
    impact_score = models.FloatField()
    debt_score = models.FloatField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    root_cause_skill = models.ForeignKey(CompetencySkill, null=True, blank=True, on_delete=models.SET_NULL, related_name='caused_debts')
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'sih_learning_debt_items'
        ordering = ['-debt_score']
    def __str__(self): return self.skill.name


class IGOTCourse(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    igot_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=300)
    provider = models.CharField(max_length=100, default='iGOT Karmayogi')
    description = models.TextField(blank=True)
    duration_hours = models.FloatField(default=2.0)
    url = models.URLField(blank=True)
    level = models.CharField(max_length=20, default='Beginner')
    skills_covered = models.ManyToManyField(CompetencySkill, blank=True, related_name='igot_courses')
    domains_covered = models.ManyToManyField(CompetencyDomain, blank=True, related_name='igot_courses')
    is_active = models.BooleanField(default=True)
    class Meta:
        db_table = 'sih_igot_courses'
    def __str__(self): return self.title


class TPACProgram(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    program_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    duration_days = models.IntegerField(default=3)
    venue = models.CharField(max_length=200, blank=True)
    mode = models.CharField(max_length=20, default='Online')
    skills_covered = models.ManyToManyField(CompetencySkill, blank=True, related_name='tpac_programs')
    domains_covered = models.ManyToManyField(CompetencyDomain, blank=True, related_name='tpac_programs')
    is_active = models.BooleanField(default=True)
    class Meta:
        db_table = 'sih_tpac_programs'
    def __str__(self): return self.title


class LearningPathway(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    officer = models.ForeignKey(OfficerProfile, on_delete=models.CASCADE, related_name='learning_pathways')
    twin = models.ForeignKey(CompetencyDigitalTwin, on_delete=models.CASCADE, related_name='pathways')
    is_active = models.BooleanField(default=True)
    pathway_steps = models.JSONField(default=list)
    addresses_debt = models.ManyToManyField(LearningDebtItem, blank=True)
    total_hours = models.FloatField(default=0.0)
    completion_percentage = models.FloatField(default=0.0)
    generated_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'sih_learning_pathways'
        ordering = ['-generated_at']
    def __str__(self): return str(self.officer)


class CareerCompetencyRecord(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    officer = models.OneToOneField(OfficerProfile, on_delete=models.CASCADE, related_name='career_record')
    verified_competencies = models.JSONField(default=dict)
    gaps_closed = models.JSONField(default=list)
    training_completed = models.JSONField(default=list)
    assessment_history = models.JSONField(default=list)
    promotion_readiness = models.FloatField(default=0.0)
    next_role_ready = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'sih_career_records'
    def __str__(self): return str(self.officer)
