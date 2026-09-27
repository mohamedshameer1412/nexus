"""
sih/engine.py - NEXUS SIH Intelligence Engine
Core algorithms: Learning Debt computation, Pathway generation, Promotion readiness.
"""
from .models import (CompetencySkill, CompetencyDomain, LearningDebtItem,
    IGOTCourse, TPACProgram, LearningPathway)


def compute_learning_debt(twin, profile):
    """
    Compute Learning Debt for each skill gap.
    debt_score = gap_score * (1 + downstream_impact_weight)
    Root cause = traverse prerequisite graph to find deepest unmastered skill.
    """
    role = profile.role
    if not role:
        return

    required_levels = role.required_competency_levels  # {domain_code: required_pct}

    # Clear old unresolved debt items
    LearningDebtItem.objects.filter(twin=twin, is_resolved=False).delete()

    domain_scores = twin.domain_scores  # {domain_code: score}
    new_items = []
    total_debt = 0.0

    for domain in CompetencyDomain.objects.all():
        required = float(required_levels.get(domain.code, 75))
        achieved = float(domain_scores.get(domain.code, 0))
        gap = max(0, required - achieved)
        if gap <= 0:
            continue

        for skill in CompetencySkill.objects.filter(domain=domain):
            # Impact = number of skills that depend on this one
            dependents_count = skill.dependent_skills.count()
            impact_score = min(100, dependents_count * 20 + gap)
            debt_score = round(gap * (1 + dependents_count * 0.2), 1)

            # Priority
            if debt_score >= 60:
                priority = 'critical'
            elif debt_score >= 40:
                priority = 'high'
            elif debt_score >= 20:
                priority = 'medium'
            else:
                priority = 'low'

            # Root cause: find deepest unmastered prerequisite
            root_cause = _find_root_cause(skill, domain_scores, required_levels)

            item = LearningDebtItem(
                twin=twin,
                skill=skill,
                gap_score=gap,
                impact_score=impact_score,
                debt_score=debt_score,
                priority=priority,
                root_cause_skill=root_cause
            )
            new_items.append(item)
            total_debt += debt_score

    LearningDebtItem.objects.bulk_create(new_items)

    # Update twin
    twin.learning_debt_score = round(min(100, total_debt / max(len(new_items), 1)), 1)
    twin.save(update_fields=['learning_debt_score'])


def _find_root_cause(skill, domain_scores, required_levels):
    """Traverse prerequisite graph to find the deepest unmastered skill."""
    visited = set()
    queue = list(skill.prerequisites.all())
    root = None
    while queue:
        prereq = queue.pop(0)
        if prereq.id in visited:
            continue
        visited.add(prereq.id)
        domain_score = float(domain_scores.get(prereq.domain.code, 0))
        required = float(required_levels.get(prereq.domain.code, 75))
        if domain_score < required:
            root = prereq
            queue.extend(list(prereq.prerequisites.all()))
    return root


def generate_pathway(twin, profile):
    """
    Generate personalized learning pathway from Learning Debt items.
    Maps each gap to iGOT courses and TPAC programs.
    """
    # Deactivate old pathways
    LearningPathway.objects.filter(officer=profile, is_active=True).update(is_active=False)

    debt_items = list(twin.debt_items.filter(is_resolved=False).order_by('-debt_score')[:10])
    steps = []
    total_hours = 0.0
    # A course/programme can cover more than one skill, and two different
    # debt items can both point to it — track what's already in the plan so
    # the officer is never told to take the same thing twice.
    seen = set()

    for item in debt_items:
        # Find iGOT courses covering this skill
        igot_courses = IGOTCourse.objects.filter(
            skills_covered=item.skill, is_active=True
        )[:2]
        for course in igot_courses:
            key = ('igot', course.id)
            if key in seen:
                continue
            seen.add(key)
            steps.append({
                'type': 'igot',
                'item_id': str(course.id),
                'title': course.title,
                'provider': course.provider,
                'duration_hours': course.duration_hours,
                'url': course.url,
                'level': course.level,
                'reason': f'Addresses gap in {item.skill.name} ({item.priority} priority)',
                'skill': item.skill.name,
                'domain': item.skill.domain.name
            })
            total_hours += course.duration_hours

        # Find TPAC programs
        tpac_programs = TPACProgram.objects.filter(
            skills_covered=item.skill, is_active=True
        )[:1]
        for program in tpac_programs:
            key = ('tpac', program.id)
            if key in seen:
                continue
            seen.add(key)
            steps.append({
                'type': 'tpac',
                'item_id': str(program.id),
                'title': program.title,
                'provider': 'NSSTA TPAC',
                'duration_hours': program.duration_days * 8,
                'mode': program.mode,
                'reason': f'TPAC program for {item.skill.name}',
                'skill': item.skill.name,
                'domain': item.skill.domain.name
            })
            total_hours += program.duration_days * 8

    pathway = LearningPathway.objects.create(
        officer=profile,
        twin=twin,
        is_active=True,
        pathway_steps=steps,
        total_hours=total_hours,
        completion_percentage=0.0
    )
    pathway.addresses_debt.set(debt_items)
    return pathway


def compute_promotion_readiness(twin, profile):
    """
    Compute promotion readiness score (0-100).
    Based on: overall competency score, gaps closed, learning history.
    """
    base = twin.overall_competency_score
    gaps_closed = twin.debt_items.filter(is_resolved=True).count()
    total_gaps = twin.debt_items.count()
    gap_ratio = (gaps_closed / max(total_gaps, 1)) * 30
    learning_bonus = min(10, len(twin.learning_history) * 2)
    readiness = round(min(100, base * 0.6 + gap_ratio + learning_bonus), 1)
    return readiness
