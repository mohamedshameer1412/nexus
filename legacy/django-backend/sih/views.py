"""
sih/views.py - NEXUS SIH API Views
All 7 core endpoints for the SIH demo flow.
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (OfficerProfile, OfficerRole, CompetencyDomain, CompetencySkill,
    DiagnosticQuestion, DiagnosticSession, CompetencyDigitalTwin, LearningDebtItem,
    IGOTCourse, TPACProgram, LearningPathway, CareerCompetencyRecord)
from .serializers import (OfficerProfileSerializer, OfficerOnboardingSerializer,
    CompetencyDomainSerializer, DiagnosticQuestionSerializer, DiagnosticSessionSerializer,
    CompetencyDigitalTwinSerializer, LearningDebtItemSerializer, IGOTCourseSerializer,
    TPACProgramSerializer, LearningPathwaySerializer, CareerCompetencyRecordSerializer)
from .engine import compute_learning_debt, generate_pathway, compute_promotion_readiness


# ─────────────────────────────────────────────
# 1. ONBOARDING
# ─────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def onboarding(request):
    """GET: get current profile. POST: create/update officer profile."""
    if request.method == 'GET':
        try:
            profile = OfficerProfile.objects.get(user=request.user)
            return Response(OfficerProfileSerializer(profile).data)
        except OfficerProfile.DoesNotExist:
            roles = OfficerRole.objects.all().values('id', 'title', 'grade', 'department')
            return Response({'profile': None, 'roles': list(roles)})

    # POST: create or update
    profile, created = OfficerProfile.objects.get_or_create(
        user=request.user,
        defaults={'designation': '', 'department': ''}
    )
    serializer = OfficerOnboardingSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save(onboarding_complete=True)
        # Create twin + career record if first time
        CompetencyDigitalTwin.objects.get_or_create(officer=profile)
        CareerCompetencyRecord.objects.get_or_create(officer=profile)
        return Response({'success': True, 'profile': OfficerProfileSerializer(profile).data},
                        status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────
# 2. DIAGNOSTIC ASSESSMENT
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_diagnostic_questions(request):
    """Return 15 questions: 4 per domain (D1,D2,D3) + 3 for D4."""
    domains = CompetencyDomain.objects.order_by('order')
    questions = []
    counts = {0: 4, 1: 4, 2: 4, 3: 3}
    for i, domain in enumerate(domains):
        n = counts.get(i, 3)
        qs = DiagnosticQuestion.objects.filter(domain=domain).order_by('?')[:n]
        questions.extend(DiagnosticQuestionSerializer(qs, many=True).data)
    return Response({'questions': questions, 'total': len(questions)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_diagnostic(request):
    """
    Submit diagnostic responses. Compute domain scores. Update Digital Twin.
    Body: {responses: [{question_id, chosen_answer}]}
    """
    try:
        profile = OfficerProfile.objects.get(user=request.user)
    except OfficerProfile.DoesNotExist:
        return Response({'error': 'Complete onboarding first'}, status=400)

    responses = request.data.get('responses', [])
    if not responses:
        return Response({'error': 'No responses provided'}, status=400)

    # Score each response
    domain_correct = {}
    domain_total = {}
    scored_responses = []

    for resp in responses:
        try:
            q = DiagnosticQuestion.objects.get(id=resp['question_id'])
            correct = q.correct_answer.lower() == resp.get('chosen_answer', '').lower()
            domain_code = q.domain.code
            domain_correct[domain_code] = domain_correct.get(domain_code, 0) + (1 if correct else 0)
            domain_total[domain_code] = domain_total.get(domain_code, 0) + 1
            scored_responses.append({
                'question_id': str(q.id),
                'domain': domain_code,
                'chosen': resp.get('chosen_answer', ''),
                'correct_answer': q.correct_answer,
                'is_correct': correct,
                'explanation': q.explanation
            })
        except DiagnosticQuestion.DoesNotExist:
            continue

    # Compute domain scores (%)
    domain_scores = {}
    for code in domain_correct:
        total = domain_total.get(code, 1)
        domain_scores[code] = round((domain_correct[code] / total) * 100, 1)

    overall = round(sum(domain_scores.values()) / max(len(domain_scores), 1), 1)

    # Create session
    session = DiagnosticSession.objects.create(
        officer=profile,
        status='completed',
        completed_at=timezone.now(),
        domain_scores=domain_scores,
        overall_score=overall,
        responses=scored_responses
    )

    # Update Digital Twin
    twin, _ = CompetencyDigitalTwin.objects.get_or_create(officer=profile)
    twin.domain_scores = domain_scores
    twin.overall_competency_score = overall
    twin.learning_history.append({
        'date': timezone.now().isoformat(),
        'activity': 'Diagnostic Assessment',
        'domain': 'All',
        'scores': domain_scores
    })
    twin.save()

    # Compute and save learning debt
    compute_learning_debt(twin, profile)

    return Response({
        'session_id': session.id,
        'domain_scores': domain_scores,
        'overall_score': overall,
        'responses': scored_responses,
        'message': 'Assessment complete. Digital Twin updated.'
    })


# ─────────────────────────────────────────────
# 3. DIGITAL TWIN
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_digital_twin(request):
    """Return the officer's Competency Digital Twin."""
    try:
        profile = OfficerProfile.objects.get(user=request.user)
        twin = CompetencyDigitalTwin.objects.get(officer=profile)
        domains = CompetencyDomain.objects.order_by('order')
        domain_data = []
        for d in domains:
            domain_data.append({
                'code': d.code,
                'name': d.name,
                'icon': d.icon,
                'score': twin.domain_scores.get(d.code, 0),
                'required': profile.role.required_competency_levels.get(d.code, 75) if profile.role else 75
            })
        return Response({
            'twin': CompetencyDigitalTwinSerializer(twin).data,
            'domains': domain_data,
            'role': profile.role.title if profile.role else None
        })
    except (OfficerProfile.DoesNotExist, CompetencyDigitalTwin.DoesNotExist):
        return Response({'error': 'No twin found. Complete assessment first.'}, status=200)


# ─────────────────────────────────────────────
# 4. LEARNING DEBT + GAP ANALYSIS
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_learning_gaps(request):
    """Return prioritized Learning Debt list with root-cause analysis."""
    try:
        profile = OfficerProfile.objects.get(user=request.user)
        twin = CompetencyDigitalTwin.objects.get(officer=profile)
        debt_items = LearningDebtItem.objects.filter(twin=twin, is_resolved=False)
        return Response({
            'learning_debt_score': twin.learning_debt_score,
            'total_gaps': debt_items.count(),
            'gaps': LearningDebtItemSerializer(debt_items, many=True).data
        })
    except (OfficerProfile.DoesNotExist, CompetencyDigitalTwin.DoesNotExist):
        return Response({'error': 'Complete assessment first.'}, status=200)


# ─────────────────────────────────────────────
# 5. LEARNING PATHWAY (iGOT + TPAC)
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_learning_pathway(request):
    """Return AI-generated iGOT + TPAC learning pathway."""
    try:
        profile = OfficerProfile.objects.get(user=request.user)
        twin = CompetencyDigitalTwin.objects.get(officer=profile)
        pathway = generate_pathway(twin, profile)
        return Response(LearningPathwaySerializer(pathway).data)
    except (OfficerProfile.DoesNotExist, CompetencyDigitalTwin.DoesNotExist):
        return Response({'error': 'Complete assessment first.'}, status=200)


# ─────────────────────────────────────────────
# 6. VERIFY & REPLAN
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_and_replan(request):
    """
    Mark a debt item as resolved (after completing a course).
    Regenerate the learning pathway.
    Body: {debt_item_id: str, course_score: float}
    """
    try:
        profile = OfficerProfile.objects.get(user=request.user)
        twin = CompetencyDigitalTwin.objects.get(officer=profile)
    except (OfficerProfile.DoesNotExist, CompetencyDigitalTwin.DoesNotExist):
        return Response({'error': 'Complete assessment first.'}, status=200)

    debt_item_id = request.data.get('debt_item_id')
    course_score = float(request.data.get('course_score', 0))

    if debt_item_id:
        try:
            item = LearningDebtItem.objects.get(id=debt_item_id, twin=twin)
            if course_score >= 70:
                item.is_resolved = True
                item.resolved_at = timezone.now()
                item.save()
                # Update twin
                twin.learning_history.append({
                    'date': timezone.now().isoformat(),
                    'activity': f'Completed: {item.skill.name}',
                    'domain': item.skill.domain.code,
                    'score': course_score
                })
                twin.save()
        except LearningDebtItem.DoesNotExist:
            pass

    # Recompute debt and regenerate pathway
    compute_learning_debt(twin, profile)
    pathway = generate_pathway(twin, profile)

    return Response({
        'message': 'Learning plan updated.',
        'pathway': LearningPathwaySerializer(pathway).data,
        'remaining_gaps': LearningDebtItem.objects.filter(twin=twin, is_resolved=False).count()
    })


# ─────────────────────────────────────────────
# 7. CAREER RECORD
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_career_report(request):
    """Download the officer's verified competency evidence report as a PDF."""
    from django.http import HttpResponse
    from .reports import generate_career_evidence_report_pdf

    try:
        profile = OfficerProfile.objects.get(user=request.user)
        twin = CompetencyDigitalTwin.objects.get(officer=profile)
    except (OfficerProfile.DoesNotExist, CompetencyDigitalTwin.DoesNotExist):
        return Response({'error': 'Complete assessment first.'}, status=400)

    record, _ = CareerCompetencyRecord.objects.get_or_create(officer=profile)
    readiness = compute_promotion_readiness(twin, profile)
    record.promotion_readiness = readiness
    record.next_role_ready = readiness >= 80
    record.assessment_history = twin.learning_history
    record.save()

    domains = CompetencyDomain.objects.order_by('order')
    domain_data = [{
        'name': d.name,
        'score': twin.domain_scores.get(d.code, 0),
        'required': profile.role.required_competency_levels.get(d.code, 75) if profile.role else 75,
    } for d in domains]

    pdf = generate_career_evidence_report_pdf(request.user, profile, twin, record, domain_data)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="NEXUS_Career_Evidence_Report.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_career_record(request):
    """Return the officer career competency and promotion evidence record."""
    try:
        profile = OfficerProfile.objects.get(user=request.user)
        twin = CompetencyDigitalTwin.objects.get(officer=profile)
        record, _ = CareerCompetencyRecord.objects.get_or_create(officer=profile)
        # Refresh promotion readiness
        readiness = compute_promotion_readiness(twin, profile)
        record.promotion_readiness = readiness
        record.next_role_ready = readiness >= 80
        record.assessment_history = twin.learning_history
        record.save()
        return Response({
            'record': CareerCompetencyRecordSerializer(record).data,
            'twin': CompetencyDigitalTwinSerializer(twin).data,
            'role': profile.role.title if profile.role else None,
            'career_goal': profile.career_goal
        })
    except (OfficerProfile.DoesNotExist, CompetencyDigitalTwin.DoesNotExist):
        return Response({'error': 'Complete assessment first.'}, status=200)


# ─────────────────────────────────────────────
# UTILITY: List domains and roles
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_domains(request):
    domains = CompetencyDomain.objects.order_by('order')
    return Response(CompetencyDomainSerializer(domains, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_roles(request):
    from .serializers import OfficerRoleSerializer
    from .models import OfficerRole
    roles = OfficerRole.objects.all()
    return Response(OfficerRoleSerializer(roles, many=True).data)
