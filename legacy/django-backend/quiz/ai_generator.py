"""
AI Quiz Generator Service - Gemini Only
Generates quiz questions using Google Gemini AI
"""
import json
import time
from typing import List, Dict
from google import genai
from google.genai import types
from django.conf import settings
from django.core.cache import cache
from quiz.models import Topic, Question, AIGeneratedQuestion
from utils.gemini_service import get_gemini_service


class QuizGenerator:
    """Service class for AI-powered quiz question generation using Gemini"""
    
    def __init__(self, model="gemini-flash-latest"):
        """
        Initialize the quiz generator with Gemini Service (Rate Limited)
        """
        self.gemini_service = get_gemini_service()
        self.model = model
    
    def generate_questions(
        self,
        topic: Topic,
        num_questions: int,
        difficulty: str,
        question_type: str = "mcq",
        user=None
    ) -> Dict:
        """
        Generate quiz questions using Gemini AI
        
        Args:
            topic: Topic object
            num_questions: Number of questions to generate (5-50)
            difficulty: "easy", "medium", or "hard"
            question_type: "mcq", "true_false", or "fill_blank"
            user: User who requested generation
            
        Returns:
            Dict with generated questions and metadata
        """
        start_time = time.time()
        
        # Build prompt
        prompt = self._build_prompt(topic, num_questions, difficulty, question_type)
        
        # Check cache
        cache_key = f"quiz_gen_{topic.id}_{difficulty}_{question_type}_{num_questions}"
        cached_response = cache.get(cache_key)
        if cached_response:
             print(f"Cache hit for quiz generation: {topic.name}")
             return cached_response

        # Generate questions with Gemini Service (Handles Rate Limiting)
        try:
            # We use the raw prompt since the service handles the API call
            response_text = self.gemini_service.call_api_with_fallback(prompt)
            
            if not response_text:
                raise ValueError("Failed to generate questions after retries.")
            
            generation_time = time.time() - start_time
            
            # Parse and validate response
            questions_data = self._parse_response(response_text)
            
            # Build metadata
            metadata = {
                "model": self.model,
                "provider": "gemini",
                "generation_time": round(generation_time, 2),
                "prompt_length": len(prompt),
                "topic_id": str(topic.id),
                "topic_name": topic.name,
                "difficulty": difficulty,
                "question_type": question_type,
                "estimated_cost": 0.0  # Gemini Flash is free
            }
            
            result = {
                "status": "success",
                "questions": questions_data,
                "metadata": metadata,
                "prompt": prompt
            }
            
            # Cache success result for 24 hours
            cache.set(cache_key, result, timeout=86400)
            
            return result
            
        except Exception as e:
            raise ValueError(f"Gemini API error: {str(e)}")
    
    def _build_prompt(self, topic: Topic, num_questions: int, difficulty: str, question_type: str) -> str:
        """Build the prompt for AI generation"""
        
        difficulty_instructions = {
            "easy": "suitable for beginners, testing basic recall and understanding",
            "medium": "requiring application and analysis of concepts",
            "hard": "challenging, requiring synthesis and evaluation"
        }
        
        type_instructions = {
            "mcq": "multiple-choice questions with 4 options (A, B, C, D)",
            "true_false": "true/false questions",
            "fill_blank": "fill-in-the-blank questions"
        }
        
        prompt = f"""Generate {num_questions} {difficulty} {type_instructions[question_type]} about the topic: "{topic.name}".

Topic Description: {topic.description if topic.description else 'No description provided'}

Requirements:
1. Questions should be {difficulty_instructions[difficulty]}
2. Each question must be clear, unambiguous, and educationally valuable
3. Avoid trick questions or overly complex language
4. Ensure correct answers are definitively correct
5. Make distractors (wrong options) plausible but clearly incorrect

Return ONLY a valid JSON object in this exact format:
{{
  "questions": [
    {{
      "question_text": "What is...?",
      "option_a": "First option",
      "option_b": "Second option",
      "option_c": "Third option",
      "option_d": "Fourth option",
      "correct_answer": "A",
      "explanation": "Brief explanation of why this is correct",
      "difficulty_level": {self._difficulty_to_number(difficulty)},
      "irt_difficulty": {self._difficulty_to_irt(difficulty)},
      "irt_discrimination": 1.0
    }}
  ]
}}

CRITICAL: Return ONLY the JSON object, no markdown formatting, no additional text."""
        
        return prompt
    
    def _parse_response(self, response_text) -> List[Dict]:
        """Parse Gemini response and extract questions"""
        try:
            # Get text from Gemini response (handled by service now)
            content = response_text
            
            # Parse JSON
            # Find JSON if wrapped in markdown
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0:
                content = content[json_start:json_end]
                
            data = json.loads(content)
            
            if "questions" not in data:
                raise ValueError("Response missing 'questions' key")
            
            questions = data["questions"]
            
            # Validate each question
            for q in questions:
                self._validate_question(q)
            
            return questions
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing response: {e}")
    
    def _validate_question(self, question: Dict):
        """Validate a single question structure"""
        required_fields = [
            "question_text", "option_a", "option_b", "option_c", "option_d",
            "correct_answer", "explanation", "difficulty_level"
        ]
        
        for field in required_fields:
            if field not in question:
                raise ValueError(f"Question missing required field: {field}")
        
        # Validate correct_answer
        if question["correct_answer"] not in ["A", "B", "C", "D"]:
            raise ValueError(f"Invalid correct_answer: {question['correct_answer']}")
        
        # Validate difficulty_level
        if not isinstance(question["difficulty_level"], int) or not (1 <= question["difficulty_level"] <= 5):
            raise ValueError(f"Invalid difficulty_level: {question['difficulty_level']}")
    
    def _difficulty_to_number(self, difficulty: str) -> int:
        """Convert difficulty string to number (1-5)"""
        mapping = {
            "easy": 2,
            "medium": 3,
            "hard": 4
        }
        return mapping.get(difficulty.lower(), 3)
    
    def _difficulty_to_irt(self, difficulty: str) -> float:
        """Convert difficulty to IRT difficulty parameter"""
        mapping = {
            "easy": -0.5,
            "medium": 0.0,
            "hard": 0.5
        }
        return mapping.get(difficulty.lower(), 0.0)
    
    def save_generated_questions(
        self,
        questions_data: List[Dict],
        topic: Topic,
        metadata: Dict,
        prompt: str,
        user
    ) -> List[Question]:
        """
        Save generated questions to database
        
        Returns:
            List of created Question objects
        """
        created_questions = []
        
        for q_data in questions_data:
            # Create Question
            question = Question.objects.create(
                topic=topic,
                question_text=q_data["question_text"],
                option_a=q_data["option_a"],
                option_b=q_data["option_b"],
                option_c=q_data["option_c"],
                option_d=q_data["option_d"],
                correct_answer=q_data["correct_answer"],
                explanation=q_data.get("explanation", ""),
                difficulty_level=q_data["difficulty_level"],
                irt_difficulty=q_data.get("irt_difficulty", 0.0),
                irt_discrimination=q_data.get("irt_discrimination", 1.0),
                created_by=user
            )
            
            # Create AI metadata
            AIGeneratedQuestion.objects.create(
                question=question,
                generation_prompt=prompt,
                model_used=self.model,
                generation_metadata=metadata,
                generated_by=user,
                is_approved=False  # Requires teacher review
            )
            
            created_questions.append(question)
        
        return created_questions
