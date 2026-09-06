# NEXUS — Agentic Learner Intelligence OS
### Team Deadlock | AGENTATHON 2026 | SIH 2026 PS 26101

---

## What NEXUS Is

NEXUS is a closed-loop, multi-agent learning intelligence system. It builds a persistent
Learner Digital Twin for every student and runs six autonomous agents after every session
to update it, diagnose errors, predict future risks, plan the next session, and connect
learning to career requirements.

Core loop: Observe -> Diagnose -> Predict -> Decide -> Intervene -> Verify -> Remember -> Replan

---

## Project Structure

nexus/
  backend/
    nexus_core/         Learner Digital Twin models
    tutor_agent/        Tutor Agent (content delivery)
    planner_agent/      Planner Agent (study plan + What-If Simulator)
    evaluator_agent/    Evaluator Agent (root-cause diagnosis)
    analytics/          Analytics Agent (Twin updates)
    ml_engine/          IRT (1PL Rasch), FAISS, Random Forest
    ml_models/          Trained model files
    syllabus/           PDF parser, prerequisite graph (NetworkX)
    learning/           Session management
    proctoring/         Assessment integrity controls
    lib/                Shared utilities
    manage.py
    requirements.txt
    Dockerfile
    docker-compose.yml

  frontend_src/         Next.js 15 (App Router)
    app/                Pages and layouts
    components/         UI components
    hooks/              Custom React hooks
    utils/              API helpers

  docs/
    NEXUS_PROJECT_FLOW.md   Full project flow (AGENTATHON)
    NEXUS_SIH_26101.md      SIH PS 26101 integration (MoSPI)

---

## Tech Stack

Backend:    Python 3.11, Django 4.2 LTS, Django REST Framework
Agents:     Celery 5, Redis 7, Django Channels (WebSocket)
ML (local): Sentence-BERT, FAISS, NetworkX, scikit-learn (IRT + RF)
Frontend:   Next.js 15 (App Router), Chart.js, WebSocket API
Database:   PostgreSQL 15
Infra:      Docker, Docker Compose, Nginx, Gunicorn + Daphne

Zero external API dependency. All ML runs locally (CPU-only).

---

## Quick Start

  Backend:
    cd backend
    pip install -r requirements.txt
    python manage.py migrate
    celery -A config worker --loglevel=info
    python manage.py runserver

  Frontend:
    cd frontend_src
    npm install
    npm run dev

---

## Key Innovations

1. Learner Digital Twin (mastery, ability, velocity, CAG, debt, verified skills)
2. Confidence-Ability Gap — quantified per concept, continuously tracked
3. Learning Debt with Propagation Factor — technical debt applied to learning
4. Root-cause diagnosis via prerequisite graph traversal (NetworkX DAG)
5. What-If Learning Simulator — decision simulation for study planning
6. Real-time 6-agent parallel pipeline (real Celery events via WebSocket)
7. Verified skills through evidence (not self-declaration)

---

Separated from ai_learnmate — 2026-09-06
Team Deadlock
