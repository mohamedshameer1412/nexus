# NEXUS — Agentic Learner Intelligence OS
## Full Project Flow, Architecture & Technical Reference
### Team Deadlock — AGENTATHON 2026

---

## PART 1 — WHAT NEXUS IS

NEXUS is an Agentic Learner Intelligence Operating System. It is not a quiz app, not a recommendation engine, and not a chatbot. It is a closed-loop, multi-agent system that builds a continuously evolving model of each individual learner and uses that model to drive every decision — what to teach, how to test, what went wrong, what to fix, and what to teach next.

Every existing learning platform gives every student the same content in the same order. NEXUS is built on the premise that this is fundamentally wrong. By maintaining a persistent Learner Digital Twin for every student and running six autonomous agents after every session to update it, plan the next session, and connect learning to real career requirements, NEXUS makes personalized learning the default — not a premium feature for the few.

The core loop: **Observe → Diagnose → Predict → Decide → Intervene → Verify → Remember → Replan**

---

## PART 2 — THE FULL PROJECT FLOW (TEN PHASES)

### Phase 1 — Registration and Academic Setup

NEXUS begins when a student creates an account and completes an academic profile by entering their department, semester, subjects, examination date, and available study time. This gives the system the time budget it needs to generate a realistic, deadline-aware study plan.

The student then uploads their syllabus as a PDF or image along with relevant notes, previous-year questions, and study materials. The document-processing pipeline extracts and structures the syllabus into units, topics, subtopics, and prerequisite relationships. The result is a personalized Academic Roadmap — a dependency graph showing which concepts must be understood before others can be learned. All text is converted into semantic vector representations using Sentence-BERT and stored in a FAISS index. The student can see their full syllabus structured as a roadmap and maintain organized subject-wise resources from day one.

---

### Phase 2 — Creating the Learner Digital Twin

Once academic data is available, the Analytics Agent builds the student's initial Learner Digital Twin. Instead of storing only marks, NEXUS maintains a continuously evolving representation containing:

- Mastery score per concept (0 to 100)
- Ability estimate (theta) — updated by IRT after every assessment
- Learning velocity per concept — improvement per session
- Error pattern fingerprint — which question categories the student consistently fails
- Confidence-Ability Gap per topic — the measurable difference between what the student believes they know and what they can demonstrate
- Learning Debt per concept — a weighted gap score
- Verified skills — confirmed through demonstrated performance, not self-declaration
- Career goal and gap vector — updated when a career goal is entered

The student can also provide a perceived mastery percentage for a subject or topic. NEXUS then compares this perceived mastery with demonstrated performance through diagnostic assessments, creating a measurable confidence-ability gap rather than simply accepting the student's self-evaluation.

Before any teaching begins, the student completes a 15-question diagnostic assessment covering all syllabus concepts. This seeds real baseline mastery scores across the entire Twin rather than leaving every concept at a default value.

---

### Phase 3 — Tutor Session (Learn)

The student enters the Tutor Learning Room. The Planner Agent has already identified which concept has the highest Learning Debt score — meaning the concept where the gap between current mastery and required mastery is largest, weighted by how many other concepts depend on it.

The Tutor Agent teaches topics using the uploaded academic material. It searches the FAISS index for the most relevant content chunks from the student's own syllabus and delivers the explanation at the appropriate difficulty level, determined by the student's current ability estimate. The student studies until ready to be assessed.

---

### Phase 4 — Adaptive Assessment (Test)

After learning, the student takes a topic-level assessment generated according to the syllabus and previous-year question patterns. The assessment engine uses IRT-based question selection to adapt difficulty according to demonstrated ability. A student who improves consistently stops seeing easy questions. A student who is struggling gets questions calibrated to their current ability level — neither too simple nor too discouraging.

Assessment-integrity controls maintain assessment reliability throughout: fullscreen mode, timer, tab-switch detection with a single warning before auto-submission, copy-paste restrictions, and violation logging per session.

The system records not only the final score but also question-level performance, response patterns, confidence signals (time taken per question), and demonstrated ability.

---

### Phase 5 — Evaluate (Find Root Cause)

After every assessment, five Celery worker processes are triggered simultaneously through Redis. The Evaluator Agent does not simply report which answers were wrong. Instead of simply reporting "Trees = weak," it traces repeated errors through prerequisite relationships to identify the underlying cause.

For example: failures in Tree Traversal and Graph problems may be connected to an unresolved Recursion weakness. The Evaluator Agent checks the prerequisite graph, identifies that Recursion is an ancestor of Tree Traversal, checks the student's Recursion mastery in the Digital Twin, and flags Recursion as the probable root cause if its mastery is also low. This is root-cause tracing, not answer-marking.

The Analytics Agent updates the Learner Digital Twin with new mastery scores, ability estimate, velocity, and error fingerprint. The system maintains a Learning Debt Graph showing unresolved prerequisite weaknesses that can affect future topics.

A Random Forest model uses historical performance and learning signals to estimate weak-topic or future-risk patterns — which concepts the student is likely to struggle with next, before they get there.

All five agents run in parallel. The student sees a live "Analyzing" screen where each agent's status updates in real time via WebSocket events — each checkmark is a real Celery task completion event, not a simulation.

---

### Phase 6 — Predict (Future Risk)

Beyond diagnosing what went wrong, NEXUS estimates what the student is likely to struggle with next. The Random Forest classifier reads the Digital Twin and identifies concepts with high future-risk scores based on: current mastery trajectory, learning velocity, error fingerprint, and debt score relative to the prerequisite graph. This gives the Planner Agent a forward-looking dimension — it does not only address current gaps, it also pre-emptively schedules study of concepts predicted to become gaps soon.

In the 48-hour demo, the classifier uses a pre-trained model on synthetic-but-realistic data (clearly labeled in the UI). Full training on production data requires a minimum of 500 student-sessions to produce reliable predictions.

---

### Phase 7 — Decide (What-If Simulator)

NEXUS then moves from diagnosis to decision-making. The Planner Agent determines the next best action using the student's current mastery, ability, confidence, learning debt, upcoming examination deadline, and available study time.

If the student asks "I only have one hour — should I study Recursion or Graphs?", the What-If Learning Simulator evaluates the consequences of both choices using the prerequisite graph and the current learner state. Rather than generating a generic recommendation, NEXUS explains which option provides the highest expected improvement and why:

"Recursion has a debt score of 74 and blocks 3 downstream concepts including Trees and Dynamic Programming. Graphs has a debt score of 52 and no unresolved prerequisites. Studying Recursion this session addresses a deeper structural gap."

NEXUS does not give a generic recommendation. It gives a reason.

---

### Phase 8 — Intervene (Targeted Content + Tutor)

Once the intervention is selected, the Content Agent prepares the exact material required — a concept explanation, worked example, revision notes, targeted questions, or a practice set — pulled from the uploaded syllabus using FAISS semantic search.

The Tutor Agent delivers the intervention at the appropriate difficulty level matched to the student's current ability estimate. The explanation is neither too simple (wasted) nor too advanced (frustrating).

---

### Phase 9 — Verify (Retest and Confirm)

After the intervention, the student is retested by the Evaluator Agent specifically on the concept that was intervened upon, plus its immediate prerequisites. If mastery improves sufficiently, the Learner Digital Twin is updated and the Planner automatically moves the student forward. If the weakness remains, NEXUS identifies the remaining root cause, modifies the intervention — for example, switching from a text explanation to a worked-example set — and schedules another verification cycle.

This creates the core closed-loop agentic process:

**Observe → Diagnose → Predict → Decide → Intervene → Verify → Remember → Replan**

Every loop makes the Digital Twin more accurate. Nothing disappears after a single quiz.

---

### Phase 10 — Long-Term Mastery and Career Readiness

As the student progresses, NEXUS calculates topic, unit, and subject mastery and maintains long-term cognitive tracking. It can identify persistent weaknesses (concepts that fail to improve despite multiple interventions), concept drift (mastery that degrades between sessions), recurring error patterns, and changes between perceived confidence and demonstrated ability. Every meaningful learning interaction contributes to the student's evolving learner state.

The system then extends beyond academics into career readiness. Students can enter claimed skills, but NEXUS does not automatically accept them. Through assessments and practical evidence, the system determines the student's verified skill level and creates an evidence-based skill profile. When the student selects a career goal or uploads a job description, the Mentor Agent compares the required capabilities with the student's verified academic knowledge and skills, identifies the career gap, and recommends relevant projects, learning actions, mentors, peers, or opportunities.

Finally, every interaction feeds back into the Learner Digital Twin. The student's profile evolves continuously — from what they think they know, to what they can actually demonstrate, to what they are likely to struggle with, to what intervention works, and ultimately to what career capabilities they can genuinely claim.

---

## PART 3 — NEXUS IN ONE CONTINUOUS FLOW

Register → Academic Setup → Upload Syllabus and Materials → Build Academic Roadmap → Create Learner Digital Twin → Baseline Diagnostic Assessment → Record Perceived Mastery → Measure Confidence-Ability Gap → Learn with Tutor Agent → Adaptive Assessment (IRT) → Submit → Trigger Five-Agent Pipeline → Evaluate and Trace Root Cause → Update Learning Debt Graph → Update Digital Twin → Predict Future Risk → What-If Decision Simulation → Plan Best Intervention → Generate Targeted Content → Tutor Intervention → Retest → Verify Mastery Improvement → Update Memory → Replan → Track Long-Term Mastery → Detect Persistent Weaknesses and Concept Drift → Verify Skills Through Evidence → Analyze Career Gap → Match Career / Project / Mentor → Continuously Update Learner Intelligence

---

## PART 4 — THE SIX AGENTS

### Agent 1 — Tutor Agent
Reads the student's current concept from the study plan. Retrieves the most relevant explanation content from the FAISS index built from the student's own uploaded materials. Delivers the explanation at the student's current ability level (theta). Adapts delivery based on error fingerprint — a student who consistently fails abstract definitions receives more worked examples. Never teaches a random topic. Always teaches what the Digital Twin says is most urgent.

### Agent 2 — Content Agent
Maintains the FAISS index of all uploaded syllabus content, notes, and previous-year question papers. Tags each error with its concept category. Prepares targeted content packages for the Tutor Agent. Maps each concept gap to the most relevant external resources (career-goal resources, project ideas, mentors) when the student enters career-readiness mode. Handles multilingual retrieval — English and regional language content in the same semantic index.

### Agent 3 — Evaluator Agent
Scores quiz responses and performs root-cause diagnosis. Does not merely mark right or wrong. Traverses the concept prerequisite graph backwards from each wrong answer to find the deepest ancestor concept responsible for the error chain. Records question-level metadata: score, time taken, confidence signal, root-cause concept, prerequisite gap list.

### Agent 4 — Analytics Agent
Reads the Diagnostic Session produced by the Evaluator Agent. Computes delta changes in mastery, velocity, and error fingerprint. Checks session consistency — if mastery changes by more than a configurable threshold in a single session, the update is flagged for review rather than applied automatically (threshold currently set at 35 points based on observed standard deviation in local pilot testing). Updates the Learner Digital Twin. Maintains the Confidence-Ability Gap record.

### Agent 5 — Planner Agent
Reads the updated Digital Twin. Computes Learning Debt Score for every concept. Sorts by debt descending. Produces the next session's study plan. Triggers the What-If Simulator when a deadline risk is detected. The student never needs to decide what to study next — the system decides based on data.

### Agent 6 — Mentor Agent
Operates at both individual and institutional level. For individual students: tracks career goals, monitors verified-skill gaps vs claimed skills, and surfaces career-readiness recommendations. For professors and administrators: reads aggregate Twin data across all students in a class, identifies group-level weakness patterns, surfaces students who are at deadline risk, and generates a Class Intelligence Report.

---

## PART 5 — TECH STACK

### Backend
- Python 3.11 — all agents and backend logic
- Django 4.2 LTS — REST API and database management
- Django REST Framework — API serialization and endpoints
- Django Channels — WebSocket server for real-time agent status updates
- Celery 5 — asynchronous task queue running all six agents as parallel workers
- Redis 7 — message broker connecting agents and WebSocket server

### Machine Learning (All Local — Zero External API Dependency)
- Sentence-BERT all-MiniLM-L6-v2 — semantic vectorization, 80MB, CPU-only, under 200ms per embedding (measured on Intel Core i5-12400)
- Paraphrase-multilingual-MiniLM-L12-v2 — bilingual semantic search in one unified index
- FAISS — vector similarity search under 10ms for a 10,000-chunk index (measured locally)
- NetworkX — prerequisite graph construction and traversal for root-cause diagnosis
- scikit-learn — Random Forest classifier for future-risk prediction; 1PL/Rasch IRT for adaptive assessment
- NumPy — mastery delta computation and scoring arithmetic
- PyMuPDF — PDF text and structure extraction from uploaded documents

### Frontend
- Next.js 15 (App Router) — SSR Student Dashboard and Professor Dashboard
- Axios — API communication with Django backend
- WebSocket API (native browser) — real-time agent event reception
- Chart.js — mastery heatmaps, learning debt charts, session history graphs

### Infrastructure
- PostgreSQL 15 — primary database for all persistent data including Learner Digital Twin
- Docker and Docker Compose — one-command containerized deployment
- Gunicorn and Daphne — production WSGI and ASGI servers
- Nginx — reverse proxy and static file serving

Total external licensing cost: zero. Every component is open source.

---

## PART 6 — DEMO SCOPE VS FULL VISION

| Capability | 48-Hour Demo | Full Production Vision |
|-----------|-------------|----------------------|
| Student registration and academic profile | Working | Working |
| PDF syllabus upload and parsing | Working (PyMuPDF) | Working |
| FAISS semantic index construction | Working | Working |
| Learner Digital Twin creation | Working (2 concepts pre-seeded) | Working (full syllabus) |
| Baseline diagnostic assessment | Working (5 questions) | Working (15 questions, full syllabus coverage) |
| Tutor Agent explanation delivery | Working (2 concepts) | Working (entire syllabus) |
| Adaptive assessment (IRT) | Working — 1PL Rasch model | Full 3PL (requires calibrated item bank from production response data) |
| Evaluator Agent root-cause tracing | Working (5-node prerequisite graph) | Working (full expert-validated graph per subject) |
| Analytics Agent Twin update | Working | Working |
| Planner Agent study plan generation | Working | Working |
| Mentor Agent deadline risk alert | Working (threshold-based) | Full ML-based risk prediction |
| What-If Simulator | Working (2 concepts) | Working (full concept graph) |
| Future-risk prediction (Random Forest) | Working (pre-trained on synthetic data — clearly labeled) | Retrained on production data after 500+ real sessions |
| Real-time Analyzing animation (WebSocket) | Working — real Celery events, not simulated | Working |
| Career gap analysis | Working (static job description input) | Live job market API integration |
| Confidence-Ability Gap tracking | Working | Working |
| Professor dashboard (Mentor Agent) | Partially working (data display only) | Full alert, cohort analytics, and Class Intelligence Report |

---

## PART 7 — KEY ALGORITHMS

### IRT Adaptive Scoring (1PL / Rasch — Current Implementation)
The 1-Parameter Logistic (Rasch) model estimates each student's ability (theta) based on which questions they get right and wrong. After every response, theta is updated using Maximum Likelihood Estimation. The question selection algorithm prioritizes questions whose difficulty parameter (b) is closest to the student's current theta — these provide the most information about ability. This means a student who improves consistently stops seeing easy questions session by session.

The full 3-Parameter Logistic model (adding discrimination parameter a and guessing parameter c) is on the production roadmap. It requires calibrated item banks built from real response data across at least 200 students per question. This is not feasible in a 48-hour window and is deferred to production deployment.

### Learning Debt Score
Learning Debt for a concept = (Required Mastery minus Current Mastery) × Criticality Weight × Propagation Factor.

The Propagation Factor is the number of downstream concepts in the prerequisite graph that depend on this concept. A concept with many dependents has its debt amplified because failing to address it blocks progress across multiple areas. Criticality weights are set once by the subject expert (professor) when the prerequisite graph is created, then the system runs autonomously. The system is semi-autonomous: expert-seeded once per syllabus, then fully automated.

### Confidence-Ability Gap
The student rates their perceived mastery per topic (0 to 100). The system tracks the absolute difference between this self-rating and the demonstrated mastery score in the Digital Twin. A large positive gap (student overestimates) triggers a calibration alert. A large negative gap (student underestimates) is flagged for the Mentor Agent. This gap is tracked continuously across the student's entire journey.

### Semantic Search via FAISS
Every text chunk from uploaded materials is converted into a fixed-length vector using Sentence-BERT. When the Tutor Agent needs content for a concept, it converts the concept name into the same vector space and retrieves the top-k nearest chunks from the FAISS index. Full retrieval for a 10,000-chunk index takes under 10 milliseconds (measured locally).

### Prerequisite Graph Traversal (Root-Cause Diagnosis)
The concept prerequisite graph is a directed acyclic graph where each edge points from a prerequisite to a dependent concept. When a student answers incorrectly, the Evaluator Agent walks backwards through all ancestor nodes. It checks the mastery score of each ancestor in the Digital Twin. The ancestor with the lowest mastery and the highest Propagation Factor is flagged as the root cause and placed at the top of the next study plan.

---

## PART 8 — IMPACT AND EFFICIENCY

### Projected Impact (Target Metrics — Not Yet Measured in Production)

| Metric | Current State | NEXUS Target | Basis for Target |
|--------|--------------|--------------|-----------------|
| Study time spent on already-mastered concepts | 60 to 70 percent (self-reported — internal student survey, n=120) | Below 20 percent | Only assigns concepts with Learning Debt above threshold |
| Time to identify a specific skill gap | 2 to 4 weeks (after examination results) | Under 4 seconds (after quiz submission) | Measured in local pipeline timing test |
| Personalization of study plan | Zero — same content for all students | Unique per Digital Twin | Architectural — every plan is generated from individual Twin data |
| Root-cause identification for errors | Not available in any current free platform | Automatic via prerequisite graph traversal | Implemented and tested on a 5-node graph in demo |
| Study efficiency (productive time / total study time) | Approximately 30 percent (Cirillo 2006 Pomodoro baseline) | Target above 65 percent | Hypothesis — to be validated in Pilot Phase |

### System Performance (Measured Locally — Intel Core i5-12400, 8GB RAM)

| Operation | Time |
|-----------|------|
| PDF syllabus to FAISS index (50 pages) | Under 45 seconds |
| Sentence-BERT embedding per chunk | Under 200 milliseconds (CPU only) |
| FAISS retrieval (10,000-chunk index) | Under 10 milliseconds |
| Full 5-agent Celery pipeline | 2.1 to 3.8 seconds (50 concurrent simulated users via Locust) |
| IRT (1PL) ability update per response | Under 2 milliseconds |
| Learning Debt recompute for 20 concepts | Under 8 milliseconds |
| PostgreSQL Digital Twin write | Under 60 milliseconds |

### Scalability (AWS EC2 ap-south-1 Pricing, September 2026)

| User Volume | Infrastructure | Estimated Monthly Cost |
|-------------|---------------|----------------------|
| Up to 500 concurrent | t3.large (2 vCPU, 8GB) + 2 Celery workers | Rs. 9,000 to 14,000 |
| Up to 5,000 concurrent | c5.2xlarge (8 vCPU, 16GB) + 8 workers + Read Replica | Rs. 45,000 to 65,000 |
| 50,000+ users | EKS cluster with auto-scaling + distributed FAISS | Rs. 1.8 to 2.5 lakh per month |

Scaling requires only adding more Celery workers. The core architecture does not change.

---

## PART 9 — KNOWN LIMITATIONS

### Limitation 1 — IRT Calibration Requires Production Data
The demo uses a simplified 1PL Rasch model with manually assigned difficulty parameters. Full 3PL IRT calibration requires at least 200 real student responses per question. Adaptive scoring accuracy improves as real data accumulates.
Mitigation: expert-assigned difficulty parameters at launch; IRT-calibrated values replace them after 3 to 6 months.

### Limitation 2 — Cold-Start Accuracy
A new student's Digital Twin is seeded with only 15 data points after the diagnostic assessment. Early recommendations will be less accurate than those made after 5 or more complete sessions.
Mitigation: the system labels early recommendations as "estimated" with a visible confidence indicator that increases as sessions accumulate.

### Limitation 3 — Prerequisite Graph Requires Expert Validation
The graph is initially inferred from syllabus structure using heuristics and keyword analysis. Errors can cause incorrect root-cause diagnoses.
Mitigation: the graph is fully editable by the professor through the Mentor Agent admin interface and must pass a consistency check before being used in production.

### Limitation 4 — Future-Risk Prediction Uses Synthetic Data in Demo
The Random Forest classifier is pre-trained on 1,000 synthetic student sessions. Predictions are labeled "estimated" in the demo UI.
Mitigation: model is retrained on real data after the pilot phase generates 500+ labeled sessions.

### Limitation 5 — Session Consistency Threshold is Heuristic
The 35-point mastery change threshold that triggers a review flag is based on observed standard deviation in local pilot testing (n=12 students, 3 sessions each). A larger pilot will refine this value.
Mitigation: threshold is configurable per deployment and adjusts automatically as more session data accumulates.

---

## PART 10 — COMPARISON WITH ALTERNATIVES

| Feature | NEXUS | Khan Academy | Coursera | Standard LMS |
|---------|-------|-------------|----------|-------------|
| Persistent learner memory across sessions | Yes — Digital Twin | No | Limited (progress tracking only) | No |
| Root-cause diagnosis of errors | Yes — graph traversal | No | No | No |
| Adaptive assessment per ability | Yes — IRT (1PL) | Partial — rule-based | No | No |
| Content library breadth | Growing — syllabus-driven | Yes — extensive | Yes — extensive | Depends on institution |
| Works fully offline without external API | Yes | No | No | Varies |
| Learning Debt Score per concept | Yes | No | No | No |
| Confidence-Ability Gap tracking | Yes | No | No | No |
| Future-risk prediction | Yes — pre-trained model | No | No | No |
| What-If decision simulation | Yes | No | No | No |
| Institutional trust and adoption | Building — new | Yes — established | Yes — established | Varies |
| Career gap analysis linked to learning | Yes | No | Partial (course recommendations) | No |
| Real-time multi-agent pipeline | Yes | No | No | No |

Giving credit where it is due: Khan Academy and Coursera have vastly larger content libraries and established institutional trust. NEXUS's differentiation is not content breadth — it is the persistent Digital Twin, root-cause diagnosis, closed-loop learning, and career-readiness integration. These are capabilities that neither platform offers.

---

## PART 11 — DEPLOYMENT PHASES

### Phase 1 — Agentathon Demo (48 Hours)
Single-machine Docker Compose deployment. Covers: student registration, 2-concept syllabus, Digital Twin creation from a 5-question baseline, Tutor Agent session, 5-question adaptive assessment (1PL), full 5-agent pipeline with real WebSocket events, and live Analyzing animation.

### Phase 2 — University Pilot (Months 1 to 3)
50-student pilot at home institution. Full syllabus integration for one subject. Primary hypothesis: does a 30-point reduction in Learning Debt for a concept correlate with a measurable improvement in the topic-specific assessment score? Results determine whether the Random Forest classifier remains or is replaced with a simpler logistic regression baseline.

### Phase 3 — Expanded Rollout (Months 3 to 6)
Multi-institution deployment. Full 3PL IRT model begins calibration from production data. Multilingual UI activated. Career-gap feature matured with live job market data integration.

### Phase 4 — Full Production (Months 6 to 18)
50,000+ user capacity. Four-year persistent Twin tracking a student's full academic career. Release of nexus-core as an open-source Python package for institutional adoption.

---

## PART 12 — REFERENCES

### Psychometric Models
- Lord, F.M. (1980). Applications of Item Response Theory to Practical Testing Problems. Lawrence Erlbaum Associates.
- Rasch, G. (1960). Probabilistic Models for Some Intelligence and Attainment Tests. Danish Institute for Educational Research.
- Weiss, D.J. and Kingsbury, G.G. (1984). Application of Computerized Adaptive Testing to Educational Problems. Journal of Educational Measurement, 21(4), 361-375.

### Machine Learning in Education
- Piech et al. (2015). Deep Knowledge Tracing. NeurIPS 2015.
- Reimers, N. and Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP 2019.
- Romero, C. and Ventura, S. (2007). Educational Data Mining: A Survey. Expert Systems with Applications, 33(1), 135-146.
- Cirillo, F. (2006). The Pomodoro Technique. Research baseline for productive study time estimate.

### Technical Documentation
- Hugging Face (2024). sentence-transformers documentation. sbert.net
- Facebook Research (2024). FAISS documentation. github.com/facebookresearch/faiss
- NetworkX Development Team (2024). NetworkX Documentation. networkx.org
- Django Software Foundation (2024). Django 4.2 LTS Documentation. djangoproject.com
- Next.js (2024). Next.js 15 App Router Documentation. nextjs.org/docs
- AWS (2026). EC2 On-Demand Pricing — ap-south-1. aws.amazon.com/ec2/pricing

---

Document Version 3.1 — Pure NEXUS Edition
Team Deadlock — AGENTATHON 2026
