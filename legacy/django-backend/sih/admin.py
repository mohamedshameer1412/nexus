from django.contrib import admin
from .models import (CompetencyDomain, CompetencySkill, OfficerRole, OfficerProfile,
    DiagnosticQuestion, DiagnosticSession, CompetencyDigitalTwin, LearningDebtItem,
    IGOTCourse, TPACProgram, LearningPathway, CareerCompetencyRecord)

admin.site.register(CompetencyDomain)
admin.site.register(CompetencySkill)
admin.site.register(OfficerRole)
admin.site.register(OfficerProfile)
admin.site.register(DiagnosticQuestion)
admin.site.register(DiagnosticSession)
admin.site.register(CompetencyDigitalTwin)
admin.site.register(LearningDebtItem)
admin.site.register(IGOTCourse)
admin.site.register(TPACProgram)
admin.site.register(LearningPathway)
admin.site.register(CareerCompetencyRecord)
