"""
AI Text Answer Grading Service
Provides hybrid AI+manual grading for subjective questions
"""
import re
import time
from typing import Dict, List, Tuple
from google import genai
from google.genai import types
from django.conf import settings


class TextAnswerGrader:
    """Service class for AI-powered text answer grading"""
    
    def __init__(self, model="gemini-1.5-flash"):
        """
        Initialize the grader with Gemini
        
        Args:
            model: Gemini model to use (default: gemini-1.5-flash - stable and free)
        """
        self.model = model
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def grade_answer(
        self,
        student_answer: str,
        model_answer: str,
        question_text: str,
        required_keywords: List[str] = None,
        max_score: float = 10.0
    ) -> Dict:
        """
        Grade a text answer using hybrid AI approach
        
        Args:
            student_answer: Student's text response
            model_answer: Reference/model answer
            question_text: The question being answered
            required_keywords: List of keywords to check
            max_score: Maximum possible score
            
        Returns:
            Dict with grading results:
            {
                "ai_score": float,
                "ai_feedback": str,
                "similarity_score": float,
                "keyword_matches": {
                    "found": [...],
                    "missing": [...]
                },
                "grading_breakdown": {
                    "content_score": float,
                    "keyword_score": float,
                    "structure_score": float
                }
            }
        """
        start_time = time.time()
        
        # 1. Keyword Analysis
        keyword_result = self._check_keywords(student_answer, required_keywords or [])
        keyword_score = keyword_result["score"]
        
        # 2. LLM-based Semantic Grading
        llm_result = self._llm_grade(
            student_answer=student_answer,
            model_answer=model_answer,
            question_text=question_text,
            max_score=max_score
        )
        
        # 3. Combine scores (weighted average)
        # 70% LLM content score, 20% keyword score, 10% structure
        final_score = (
            llm_result["content_score"] * 0.7 +
            keyword_score * 0.2 +
            llm_result["structure_score"] * 0.1
        )
        
        # Ensure score doesn't exceed max
        final_score = min(final_score, max_score)
        
        generation_time = time.time() - start_time
        
        return {
            "ai_score": round(final_score, 2),
            "ai_feedback": llm_result["feedback"],
            "similarity_score": llm_result["similarity"],
            "keyword_matches": keyword_result["matches"],
            "grading_breakdown": {
                "content_score": llm_result["content_score"],
                "keyword_score": keyword_score,
                "structure_score": llm_result["structure_score"]
            },
            "generation_time": round(generation_time, 2),
            "requires_teacher_review": final_score < (max_score * 0.6)  # Flag low scores
        }
    
    def _check_keywords(self, student_answer: str, required_keywords: List[str]) -> Dict:
        """
        Check for required keywords in student answer
        
        Returns:
            {
                "score": float (0-10),
                "matches": {
                    "found": [...],
                    "missing": [...]
                }
            }
        """
        if not required_keywords:
            return {
                "score": 10.0,
                "matches": {"found": [], "missing": []}
            }
        
        # Normalize answer for matching
        answer_lower = student_answer.lower()
        
        found_keywords = []
        missing_keywords = []
        
        for keyword in required_keywords:
            # Check for keyword (case-insensitive, whole word)
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, answer_lower):
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        # Calculate score based on percentage of keywords found
        if len(required_keywords) > 0:
            keyword_score = (len(found_keywords) / len(required_keywords)) * 10.0
        else:
            keyword_score = 10.0
        
        return {
            "score": round(keyword_score, 2),
            "matches": {
                "found": found_keywords,
                "missing": missing_keywords
            }
        }
    
    def _llm_grade(
        self,
        student_answer: str,
        model_answer: str,
        question_text: str,
        max_score: float
    ) -> Dict:
        """
        Use Gemini LLM to grade the answer semantically
        
        Returns:
            {
                "content_score": float,
                "structure_score": float,
                "similarity": float,
                "feedback": str
            }
        """
        prompt = f"""You are an expert teacher grading a student's answer. Evaluate the answer based on:
1. **Content Accuracy** (0-10): How correct and complete is the answer?
2. **Structure & Clarity** (0-10): How well-organized and clear is the answer?
3. **Semantic Similarity** (0-1): How similar is it to the model answer in meaning?

**Question:**
{question_text}

**Model Answer (Reference):**
{model_answer}

**Student's Answer:**
{student_answer}

Return ONLY a valid JSON object in this exact format:
{{
  "content_score": 8.5,
  "structure_score": 7.0,
  "similarity": 0.85,
  "feedback": "Good explanation of X. Missing Y. Consider improving Z.",
  "strengths": ["Clear explanation", "Good examples"],
  "weaknesses": ["Missing key concept", "Could be more concise"]
}}

Be fair but constructive. Focus on what's correct AND what can be improved."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for consistent grading
                    max_output_tokens=1000,
                    response_mime_type="application/json"
                )
            )
            
            # Parse response
            import json
            result = json.loads(response.text)
            
            # Validate and normalize scores
            result["content_score"] = min(max(result.get("content_score", 5.0), 0), 10)
            result["structure_score"] = min(max(result.get("structure_score", 5.0), 0), 10)
            result["similarity"] = min(max(result.get("similarity", 0.5), 0), 1)
            
            return result
            
        except Exception as e:
            # Fallback if AI fails
            return {
                "content_score": 5.0,
                "structure_score": 5.0,
                "similarity": 0.5,
                "feedback": f"AI grading unavailable. Please review manually. Error: {str(e)}",
                "strengths": [],
                "weaknesses": []
            }
    
    def batch_grade(
        self,
        answers: List[Dict]
    ) -> List[Dict]:
        """
        Grade multiple answers in batch
        
        Args:
            answers: List of dicts with:
                {
                    "student_answer": str,
                    "model_answer": str,
                    "question_text": str,
                    "required_keywords": List[str],
                    "max_score": float
                }
        
        Returns:
            List of grading results
        """
        results = []
        for answer_data in answers:
            result = self.grade_answer(
                student_answer=answer_data["student_answer"],
                model_answer=answer_data["model_answer"],
                question_text=answer_data["question_text"],
                required_keywords=answer_data.get("required_keywords", []),
                max_score=answer_data.get("max_score", 10.0)
            )
            results.append(result)
        
        return results
