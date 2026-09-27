"""
Seeds the PS 26101 competency framework: the four MoSPI domains, their skills and
prerequisite graph, the iGOT/TPAC catalogs, a diagnostic question bank, and a demo
officer.

Domain codes (D1..D4) are the join key used by the engine — OfficerRole
.required_competency_levels and CompetencyDigitalTwin.domain_scores must both be
keyed by them or compute_learning_debt() silently falls back to its defaults.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from sih.models import (
    CompetencyDomain, CompetencySkill, OfficerRole, OfficerProfile,
    CompetencyDigitalTwin, LearningDebtItem, DiagnosticQuestion,
    IGOTCourse, TPACProgram, CareerCompetencyRecord,
)
from sih.engine import compute_learning_debt, generate_pathway

User = get_user_model()

# code, name, icon, order, description
DOMAINS = [
    ('D1', 'Statistical Competencies', 'bar-chart', 1,
     'Survey design, sampling, national accounts, price and labour statistics, SDG indicators.'),
    ('D2', 'Technical Competencies', 'code', 2,
     'Python, R, SQL, GIS, data visualisation, machine learning, cloud and open data.'),
    ('D3', 'Digital Governance Competencies', 'shield', 3,
     'Cybersecurity, data privacy, digital signatures, government cloud and DPI.'),
    ('D4', 'Behavioural & Managerial Competencies', 'users', 4,
     'Leadership, communication, project management, ethics and decision making.'),
]

# domain_code -> [(skill name, description, [prerequisite skill names])]
SKILLS = {
    'D1': [
        ('Basic Economics', 'Foundational economic concepts underpinning official statistics.', []),
        ('Survey Design', 'Designing statistically valid surveys and questionnaires.', ['Basic Economics']),
        ('Sampling Theory and Methods', 'Probability sampling, estimators and sampling error.', ['Survey Design']),
        ('National Accounts', 'GDP compilation, SNA framework and sectoral accounts.', ['Basic Economics']),
        ('Price Statistics (CPI, WPI)', 'Index number theory applied to price statistics.', ['National Accounts']),
        ('Data Quality Frameworks', 'Assessing and assuring statistical data quality.', ['Sampling Theory and Methods']),
    ],
    'D2': [
        ('Python for Official Statistics', 'Scripting and automation of statistical workflows.', []),
        ('SQL and Data Management', 'Querying and managing relational statistical databases.', []),
        ('Data Visualization', 'Communicating statistics through effective visuals.', ['Python for Official Statistics']),
        ('GIS and Spatial Analysis', 'Spatial data handling and thematic mapping.', ['Data Visualization']),
        ('Machine Learning Foundations', 'Applied ML for prediction and classification.', ['Python for Official Statistics']),
    ],
    'D3': [
        ('Cybersecurity Fundamentals', 'Core information security principles for government systems.', []),
        ('Data Privacy and Protection', 'DPDP Act obligations and personal data handling.', ['Cybersecurity Fundamentals']),
        ('Government Cloud (MeghRaj, NIC)', 'Deploying and operating on government cloud infrastructure.', ['Cybersecurity Fundamentals']),
        ('Digital Public Infrastructure', 'DPI building blocks and interoperability standards.', ['Government Cloud (MeghRaj, NIC)']),
    ],
    'D4': [
        ('Communication and Reporting', 'Drafting briefs, reports and presentations for policy users.', []),
        ('Project Management', 'Planning and delivering statistical projects to schedule.', []),
        ('Leadership', 'Leading teams and building capability.', ['Communication and Reporting']),
        ('Ethics in Public Service', 'Professional conduct and statistical integrity.', []),
    ],
}

# igot_id, title, hours, level, [skill names covered]
IGOT_COURSES = [
    ('IGOT-STAT-101', 'Fundamentals of Official Statistics', 6.0, 'Beginner', ['Basic Economics', 'Survey Design']),
    ('IGOT-STAT-204', 'Sampling Methods for Large Scale Surveys', 10.0, 'Intermediate', ['Sampling Theory and Methods']),
    ('IGOT-STAT-310', 'National Accounts Statistics in Practice', 12.0, 'Advanced', ['National Accounts']),
    ('IGOT-STAT-318', 'Price Index Compilation: CPI and WPI', 8.0, 'Intermediate', ['Price Statistics (CPI, WPI)']),
    ('IGOT-STAT-402', 'Data Quality Assurance Frameworks', 6.0, 'Intermediate', ['Data Quality Frameworks']),
    ('IGOT-TECH-110', 'Python for Data Analysis in Government', 15.0, 'Beginner', ['Python for Official Statistics']),
    ('IGOT-TECH-125', 'SQL for Statistical Databases', 8.0, 'Beginner', ['SQL and Data Management']),
    ('IGOT-TECH-230', 'Data Visualization for Governance', 10.0, 'Intermediate', ['Data Visualization']),
    ('IGOT-TECH-245', 'GIS and Spatial Analysis for Statistics', 12.0, 'Intermediate', ['GIS and Spatial Analysis']),
    ('IGOT-TECH-360', 'Applied Machine Learning for Public Data', 18.0, 'Advanced', ['Machine Learning Foundations']),
    ('IGOT-DIG-101', 'Cyber Security Awareness for Officials', 4.0, 'Beginner', ['Cybersecurity Fundamentals']),
    ('IGOT-DIG-150', 'Data Privacy and the DPDP Act 2023', 6.0, 'Intermediate', ['Data Privacy and Protection']),
    ('IGOT-DIG-210', 'Working with MeghRaj Government Cloud', 8.0, 'Intermediate', ['Government Cloud (MeghRaj, NIC)']),
    ('IGOT-DIG-280', 'Digital Public Infrastructure Essentials', 6.0, 'Intermediate', ['Digital Public Infrastructure']),
    ('IGOT-BEH-105', 'Effective Report Writing for Policy', 5.0, 'Beginner', ['Communication and Reporting']),
    ('IGOT-BEH-140', 'Project Management in the Public Sector', 9.0, 'Intermediate', ['Project Management']),
    ('IGOT-BEH-220', 'Leadership for Statistical Officers', 10.0, 'Advanced', ['Leadership']),
    ('IGOT-BEH-090', 'Ethics and Integrity in Public Service', 4.0, 'Beginner', ['Ethics in Public Service']),
]

# program_code, title, days, mode, [skill names covered]
TPAC_PROGRAMS = [
    ('TPAC-2026-01', 'Advanced Survey Design Workshop', 5, 'Classroom', ['Survey Design', 'Sampling Theory and Methods']),
    ('TPAC-2026-04', 'National Accounts Capacity Building Programme', 4, 'Classroom', ['National Accounts']),
    ('TPAC-2026-07', 'Statistical Data Quality Assessment', 3, 'Online', ['Data Quality Frameworks']),
    ('TPAC-2026-11', 'Python and R for Statistical Officers', 5, 'Blended', ['Python for Official Statistics', 'Machine Learning Foundations']),
    ('TPAC-2026-15', 'Dashboards and Data Storytelling', 3, 'Online', ['Data Visualization']),
    ('TPAC-2026-19', 'Geospatial Statistics Practicum', 4, 'Classroom', ['GIS and Spatial Analysis']),
    ('TPAC-2026-23', 'Information Security for Statistical Systems', 3, 'Online', ['Cybersecurity Fundamentals', 'Data Privacy and Protection']),
    ('TPAC-2026-28', 'Government Cloud Adoption Programme', 3, 'Blended', ['Government Cloud (MeghRaj, NIC)']),
    ('TPAC-2026-33', 'Leadership Development for Deputy Directors', 5, 'Classroom', ['Leadership', 'Project Management']),
    ('TPAC-2026-36', 'Policy Communication Masterclass', 2, 'Online', ['Communication and Reporting']),
]

# domain_code -> [(question, a, b, c, d, correct, explanation)]
QUESTIONS = {
    'D1': [
        ('In a simple random sample without replacement, the sampling error primarily depends on which factor?',
         'The population mean', 'The sample size relative to population variance',
         'The number of enumerators', 'The date of collection', 'b',
         'Sampling error is driven by sample size and population variance, not operational factors.'),
        ('Which index number formula is used for the Indian Consumer Price Index?',
         'Paasche', 'Fisher Ideal', 'Laspeyres', 'Marshall-Edgeworth', 'c',
         'India\'s CPI uses a Laspeyres (base-weighted) formula.'),
        ('Gross Value Added (GVA) at basic prices differs from GDP at market prices by:',
         'Subsidies only', 'Taxes on products less subsidies on products',
         'Total tax revenue', 'Net factor income from abroad', 'b',
         'GDP at market prices = GVA at basic prices + product taxes - product subsidies.'),
        ('A sampling frame that omits part of the target population causes:',
         'Non-response bias', 'Coverage error', 'Processing error', 'Recall bias', 'b',
         'An incomplete frame produces coverage (undercoverage) error.'),
        ('Which is the primary purpose of a pilot survey?',
         'To publish preliminary results', 'To test instruments and field procedures',
         'To replace the main survey', 'To reduce the sample size', 'b',
         'Pilots validate the questionnaire and field operations before full rollout.'),
    ],
    'D2': [
        ('In Python, which library is most commonly used for tabular data manipulation?',
         'NumPy', 'pandas', 'matplotlib', 'requests', 'b',
         'pandas provides the DataFrame structure used for tabular analysis.'),
        ('Which SQL clause filters rows after aggregation has been applied?',
         'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'c',
         'HAVING filters aggregated groups; WHERE filters rows before aggregation.'),
        ('For showing the distribution of a continuous variable, the most appropriate chart is:',
         'Pie chart', 'Histogram', 'Stacked bar chart', 'Donut chart', 'b',
         'Histograms show the distribution of continuous data.'),
        ('In GIS, a choropleth map is used to display:',
         'Point locations', 'Values aggregated over defined areas',
         'Elevation contours', 'Satellite imagery', 'b',
         'Choropleth maps shade predefined regions by an aggregated value.'),
        ('Overfitting in a machine learning model means the model:',
         'Performs poorly on training data', 'Performs well on training but poorly on unseen data',
         'Has too few parameters', 'Cannot converge', 'b',
         'Overfitting is memorising training data at the expense of generalisation.'),
    ],
    'D3': [
        ('Under the DPDP Act 2023, an organisation that determines the purpose of processing personal data is called:',
         'Data Principal', 'Data Fiduciary', 'Data Processor', 'Consent Manager', 'b',
         'The Data Fiduciary determines the purpose and means of processing.'),
        ('The primary purpose of a digital signature on a government record is to ensure:',
         'Compression', 'Authenticity and integrity', 'Faster transmission', 'Encryption at rest', 'b',
         'Digital signatures establish authenticity and detect tampering.'),
        ('MeghRaj refers to:',
         'A statistical survey', 'The Government of India cloud initiative',
         'A cybersecurity audit standard', 'An open data licence', 'b',
         'MeghRaj is the GI Cloud initiative of the Government of India.'),
        ('Which principle requires collecting only the personal data necessary for a stated purpose?',
         'Data minimisation', 'Data portability', 'Data localisation', 'Data replication', 'a',
         'Data minimisation limits collection to what is necessary for the purpose.'),
        ('Multi-factor authentication improves security primarily by:',
         'Encrypting the database', 'Requiring more than one independent credential',
         'Masking the IP address', 'Compressing session data', 'b',
         'MFA requires independent factors, so one stolen credential is insufficient.'),
    ],
    'D4': [
        ('The most effective opening for a policy brief aimed at senior decision makers is:',
         'A detailed methodology section', 'The key finding and recommendation',
         'A literature review', 'A list of annexures', 'b',
         'Policy briefs lead with the finding and recommendation (BLUF).'),
        ('In project management, the critical path is:',
         'The cheapest sequence of tasks', 'The longest sequence of dependent tasks determining duration',
         'The path with most resources', 'The set of optional tasks', 'b',
         'The critical path determines the minimum project duration.'),
        ('A statistical officer discovers an error in already published figures. The correct action is:',
         'Ignore it if the impact is small', 'Issue a documented correction and revision note',
         'Quietly amend the file', 'Wait for the next release cycle', 'b',
         'Statistical integrity requires transparent, documented revisions.'),
        ('Delegation is most appropriate when:',
         'The task is confidential and non-transferable', 'A team member has or can develop the required capability',
         'The deadline has already passed', 'The leader wants to avoid accountability', 'b',
         'Delegation develops capability while the leader retains accountability.'),
    ],
}


class Command(BaseCommand):
    help = "Seeds the PS 26101 competency framework, catalogs, question bank and demo officer."

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding NEXUS SIH data…")

        domains = self._seed_domains()
        skills = self._seed_skills(domains)
        self._seed_prerequisites(skills)
        self._seed_questions(domains, skills)
        self._seed_igot(skills)
        self._seed_tpac(skills)
        profile, twin = self._seed_officer(domains)

        compute_learning_debt(twin, profile)
        pathway = generate_pathway(twin, profile)

        debt_count = LearningDebtItem.objects.filter(twin=twin, is_resolved=False).count()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(domains)} domains, {len(skills)} skills, "
            f"{DiagnosticQuestion.objects.count()} questions, "
            f"{IGOTCourse.objects.count()} iGOT courses, "
            f"{TPACProgram.objects.count()} TPAC programs."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Demo officer: {debt_count} open debt items, "
            f"{len(pathway.pathway_steps)} pathway steps, {pathway.total_hours}h total."
        ))
        self.stdout.write("Login: demo_officer / nexus2025")

    def _seed_domains(self):
        domains = {}
        for code, name, icon, order, desc in DOMAINS:
            domain, _ = CompetencyDomain.objects.update_or_create(
                code=code,
                defaults={'name': name, 'icon': icon, 'order': order, 'description': desc},
            )
            domains[code] = domain

        # Drop domains from earlier framework revisions. Left in place they surface
        # as phantom zero-score domains on the Twin and inflate the debt list.
        stale = CompetencyDomain.objects.exclude(code__in=[d[0] for d in DOMAINS])
        if stale.exists():
            self.stdout.write(f"  pruning stale domains: {', '.join(stale.values_list('code', flat=True))}")
            stale.delete()

        return domains

    def _seed_skills(self, domains):
        skills = {}
        for code, entries in SKILLS.items():
            for name, desc, _ in entries:
                skill, _ = CompetencySkill.objects.update_or_create(
                    domain=domains[code], name=name, defaults={'description': desc},
                )
                skills[name] = skill
        return skills

    def _seed_prerequisites(self, skills):
        for entries in SKILLS.values():
            for name, _, prereqs in entries:
                if prereqs:
                    skills[name].prerequisites.set([skills[p] for p in prereqs])

    def _seed_questions(self, domains, skills):
        for code, entries in QUESTIONS.items():
            for text, a, b, c, d, correct, explanation in entries:
                DiagnosticQuestion.objects.update_or_create(
                    domain=domains[code], question_text=text,
                    defaults={
                        'option_a': a, 'option_b': b, 'option_c': c, 'option_d': d,
                        'correct_answer': correct, 'explanation': explanation,
                    },
                )

    def _seed_igot(self, skills):
        for igot_id, title, hours, level, covered in IGOT_COURSES:
            course, _ = IGOTCourse.objects.update_or_create(
                igot_id=igot_id,
                defaults={
                    'title': title, 'duration_hours': hours, 'level': level,
                    'provider': 'iGOT Karmayogi', 'is_active': True,
                    'url': f'https://igotkarmayogi.gov.in/course/{igot_id}',
                    'description': f'iGOT Karmayogi course covering {", ".join(covered)}.',
                },
            )
            course.skills_covered.set([skills[s] for s in covered])
            course.domains_covered.set({skills[s].domain for s in covered})

    def _seed_tpac(self, skills):
        for code, title, days, mode, covered in TPAC_PROGRAMS:
            program, _ = TPACProgram.objects.update_or_create(
                program_code=code,
                defaults={
                    'title': title, 'duration_days': days, 'mode': mode,
                    'venue': 'NSSTA, Greater Noida' if mode == 'Classroom' else 'Virtual',
                    'is_active': True,
                    'description': f'NSSTA TPAC programme covering {", ".join(covered)}.',
                },
            )
            program.skills_covered.set([skills[s] for s in covered])
            program.domains_covered.set({skills[s].domain for s in covered})

    def _seed_officer(self, domains):
        role, _ = OfficerRole.objects.update_or_create(
            title='Junior Statistical Officer',
            defaults={
                'grade': 'Group B',
                'department': 'Ministry of Statistics and Programme Implementation',
                # Keyed by domain code so the engine can resolve it.
                'required_competency_levels': {'D1': 75.0, 'D2': 65.0, 'D3': 60.0, 'D4': 60.0},
            },
        )

        # Always reset credentials so re-running the seed gives a known-good login
        # even when the demo user already exists from an earlier run.
        user, _ = User.objects.get_or_create(username='demo_officer')
        user.email = 'demo.officer@gov.in'
        user.set_password('nexus2025')
        user.save()

        profile, _ = OfficerProfile.objects.update_or_create(
            user=user,
            defaults={
                'role': role,
                'designation': 'Junior Statistical Officer',
                'department': 'Ministry of Statistics and Programme Implementation',
                'years_of_experience': 2,
                'current_assignment': 'Price Statistics Division',
                'career_goal': 'Deputy Director (Statistics)',
                'onboarding_complete': True,
            },
        )

        # Deliberate gaps against the role requirement, keyed by domain code.
        domain_scores = {'D1': 58.0, 'D2': 41.0, 'D3': 35.0, 'D4': 66.0}
        overall = round(sum(domain_scores.values()) / len(domain_scores), 1)

        twin, _ = CompetencyDigitalTwin.objects.get_or_create(officer=profile)
        twin.domain_scores = domain_scores
        twin.overall_competency_score = overall
        if not twin.learning_history:
            twin.learning_history = [{
                'date': '2026-01-15T10:00:00',
                'activity': 'Baseline Diagnostic Assessment',
                'domain': 'All',
                'scores': domain_scores,
            }]
        twin.save()

        CareerCompetencyRecord.objects.get_or_create(officer=profile)
        return profile, twin
