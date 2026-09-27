from rest_framework import serializers
from .models import (CompetencyDomain, CompetencySkill, OfficerRole, OfficerProfile,
    DiagnosticQuestion, DiagnosticSession, CompetencyDigitalTwin, LearningDebtItem,
    IGOTCourse, TPACProgram, LearningPathway, CareerCompetencyRecord)


class CompetencyDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetencyDomain
        fields = '__all__'


class CompetencySkillSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    class Meta:
        model = CompetencySkill
        fields = '__all__'


class OfficerRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficerRole
        fields = '__all__'


class OfficerProfileSerializer(serializers.ModelSerializer):
    role_title = serializers.CharField(source='role.title', read_only=True)
    class Meta:
        model = OfficerProfile
        fields = '__all__'


class OfficerOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficerProfile
        fields = ['role', 'employee_id', 'designation', 'department',
                  'years_of_experience', 'current_assignment', 'career_goal']


class DiagnosticQuestionSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    class Meta:
        model = DiagnosticQuestion
        exclude = ['correct_answer', 'explanation']


class DiagnosticSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticSession
        fields = '__all__'


class SubmitDiagnosticSerializer(serializers.Serializer):
    responses = serializers.ListField(
        child=serializers.DictField(),
        help_text='[{question_id, chosen_answer}, ...]'
    )


class CompetencyDigitalTwinSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetencyDigitalTwin
        fields = '__all__'


class LearningDebtItemSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_domain = serializers.CharField(source='skill.domain.name', read_only=True)
    root_cause_name = serializers.CharField(source='root_cause_skill.name', read_only=True)
    class Meta:
        model = LearningDebtItem
        fields = '__all__'


class IGOTCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = IGOTCourse
        fields = '__all__'


class TPACProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = TPACProgram
        fields = '__all__'


class LearningPathwaySerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPathway
        fields = '__all__'


class CareerCompetencyRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerCompetencyRecord
        fields = '__all__'
