import logging
import json
from google import genai
from pydantic import BaseModel
from django.conf import settings
import PyPDF2

logger = logging.getLogger(__name__)

# Initialize Gemini Client
client = genai.Client()
MODEL_ID = "gemini-3.7-flash"

class QuizQuestion(BaseModel):
    id: str
    question: str
    options: list[str]
    correct: str
    explanation: str

class QuizList(BaseModel):
    questions: list[QuizQuestion]

class PathwayCourse(BaseModel):
    id: str
    title: str
    type: str
    duration: str

class PathwayList(BaseModel):
    courses: list[PathwayCourse]

def content_agent_extract(file_path: str) -> str:
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text[:100000]
    except Exception as e:
        logger.error(f"Error in Content Agent: {e}")
        return ""

def tutor_agent_summarize(text: str) -> str:
    prompt = f"Analyze the following text and extract exactly 3 to 5 core concepts or learning objectives. Return them as a comma-separated list.\n\nText:\n{text[:50000]}"
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error in Tutor Agent: {e}")
        return "Data Analysis, Missing Values, General Concepts"

def evaluator_agent_quiz(concepts: str) -> list:
    prompt = f"Create 2 multiple-choice questions based on these concepts: {concepts}."
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuizList,
            )
        )
        data = json.loads(response.text)
        return data.get("questions", [])
    except Exception as e:
        logger.error(f"Error in Evaluator Agent: {e}")
        return []

def analytics_agent_diagnose(text: str) -> str:
    prompt = f"Based on this text, what is the most likely area where a beginner would struggle? Give a 1-sentence answer.\n\nText:\n{text[:10000]}"
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error in Analytics Agent: {e}")
        return "Beginners often struggle with applying the theoretical statistical models to messy, real-world data."

def planner_agent_pathway(concepts: str) -> list:
    prompt = f"Based on the following concepts: '{concepts}', recommend exactly 2 targeted courses or workshops (e.g., from iGOT Karmayogi or NSSTA TPAC) that a government officer should take. Return a structured list."
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PathwayList,
            )
        )
        data = json.loads(response.text)
        return data.get("courses", [])
    except Exception as e:
        logger.error(f"Error in Planner Agent: {e}")
        return []

def mentor_agent_motivate(concepts: str) -> str:
    prompt = f"Write a 2-sentence encouraging message to a learner who is about to study these concepts: {concepts}. Keep it professional but highly motivating."
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error in Mentor Agent: {e}")
        return "You're taking a great step forward in your professional journey. Mastering these concepts will significantly enhance your capabilities!"
