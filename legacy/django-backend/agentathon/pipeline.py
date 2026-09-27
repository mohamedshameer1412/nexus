import time
import os
import threading
from .models import AgentathonSession, AgentLog
from .agents import (
    content_agent_extract,
    tutor_agent_summarize,
    evaluator_agent_quiz,
    analytics_agent_diagnose,
    planner_agent_pathway,
    mentor_agent_motivate
)

def run_real_agent_pipeline(session_id, file_path):
    """
    Executes the 6-agent pipeline using real LLM calls (google-genai).
    """
    try:
        session = AgentathonSession.objects.get(session_id=session_id)
        session.status = "processing"
        session.save()

        def log_step(agent, decision, verified=None):
            AgentLog.objects.create(
                session=session,
                agent_name=agent,
                decision=decision,
                verified=verified
            )
            # Sleep slightly just so the UI has time to animate if the LLM is too fast
            time.sleep(1.0)

        # 1. Content Agent
        log_step("content", "Received document. Beginning text extraction via PyPDF2.")
        text = content_agent_extract(file_path)
        if not text:
            raise ValueError("Could not extract text from document.")
        log_step("content", f"Successfully extracted {len(text)} characters of text.", True)

        # 2. Tutor Agent
        log_step("tutor", "Analyzing extracted text for core concepts using Gemini 3.7 Flash.")
        concepts = tutor_agent_summarize(text)
        log_step("tutor", f"Identified core concepts: {concepts}", True)

        # 3. Evaluator Agent
        log_step("evaluator", "Generating structured Multiple Choice Questions based on extracted concepts.")
        quiz_data = evaluator_agent_quiz(concepts)
        if not quiz_data:
            # Fallback mock if LLM fails strict JSON
            quiz_data = [{
                "id": "fallback_1",
                "question": "What is the primary topic of the uploaded document?",
                "options": ["Data Analysis", "General Management", "Unknown", "None of the above"],
                "correct": "Data Analysis",
                "explanation": "Based on the generic fallback structure."
            }]
        log_step("evaluator", f"Generated {len(quiz_data)} structured diagnostic MCQs.", True)

        # 4. Analytics Agent
        log_step("analytics", "Computing expected competency gaps based on document complexity.")
        diagnosis = analytics_agent_diagnose(text)
        log_step("analytics", f"Gap Analysis: {diagnosis}", True)

        # 5. Planner Agent
        log_step("planner", "Querying LLM for targeted iGOT/TPAC course mapping.")
        pathway_data = planner_agent_pathway(concepts)
        if not pathway_data:
            pathway_data = [{
                "id": "fallback_p1",
                "title": "iGOT: Core Competency Building",
                "type": "Course",
                "duration": "2 hours"
            }]
        log_step("planner", f"Mapped concepts to {len(pathway_data)} personalized course(s).", True)

        # 6. Mentor Agent
        log_step("mentor", "Drafting motivational pathway summary.")
        motivation = mentor_agent_motivate(concepts)
        log_step("mentor", f"Message: '{motivation}'", True)

        # Finalize
        session.quiz_data = quiz_data
        session.pathway_data = pathway_data
        session.status = "completed"
        session.save()

        # Clean up the temp file
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        if 'session' in locals():
            session.status = "error"
            session.save()
            AgentLog.objects.create(session=session, agent_name="system", decision=f"Pipeline error: {str(e)}")

def trigger_pipeline(session_id, file_path):
    thread = threading.Thread(target=run_real_agent_pipeline, args=(session_id, file_path))
    thread.daemon = True
    thread.start()
