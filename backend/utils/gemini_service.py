
import os
import time
import json
import hashlib
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from django.core.cache import cache


class GeminiAPIService:
    """
    Smart Gemini API service with automatic key rotation and fallback.
    Uses the google.genai SDK (required for AQ. prefix API keys).
    """

    def __init__(self):
        # Initialize from settings instead of hardcoding
        from django.conf import settings
        self.api_keys = []

        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            keys = settings.GEMINI_API_KEY.split(',')
            self.api_keys.extend([k.strip() for k in keys if k.strip()])
        else:
            # Fallback to environment if settings are not loaded (for scripts)
            env_key = os.getenv('GEMINI_API_KEY')
            if env_key:
                keys = env_key.split(',')
                self.api_keys.extend([k.strip() for k in keys if k.strip()])

        if not self.api_keys:
            print("WARNING: No Gemini API keys found. AI features will fail.")

        self.current_key_index = 0
        # gemini-3.6-flash - latest model supported by AQ. prefix keys
        self.model_name = "gemini-3.6-flash"
        self.last_request_time = 0
        self.min_interval = 1.0  # Seconds between requests
        self._client = None
        self._configure_client()

    def _configure_client(self):
        """Create the google.genai client with the current API key."""
        if not self.api_keys:
            return
        self._client = genai.Client(api_key=self.api_keys[self.current_key_index])

    def rotate_key(self):
        """Rotate to the next API key."""
        if not self.api_keys:
            return
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._configure_client()
        print(f"Rotated to API key #{self.current_key_index + 1}")

    def generate_cache_key(self, prompt: str, context: str = "") -> str:
        """Generate a cache key for the prompt."""
        combined = f"{prompt}:{context}"
        return f"gemini_cache_{hashlib.md5(combined.encode()).hexdigest()}"

    def wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits by waiting if necessary."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            print(f"Rate limit: Waiting {wait_time:.2f}s...")
            time.sleep(wait_time)
        self.last_request_time = time.time()

    def call_api_with_fallback(self, prompt: str, use_cache: bool = True, max_retries: int = 6) -> Optional[str]:
        """
        Call Gemini API with automatic fallback to other keys.

        Args:
            prompt: The prompt to send to Gemini
            use_cache: Whether to use Django cache
            max_retries: Maximum number of key rotations to try

        Returns:
            Generated text or None if all keys fail
        """
        # Check cache first
        cache_key = None
        if use_cache:
            cache_key = self.generate_cache_key(prompt)
            cached_response = cache.get(cache_key)
            if cached_response:
                print(f"Cache hit for prompt: {prompt[:50]}...")
                return cached_response

        attempts = 0
        last_error = None

        while attempts < max_retries:
            try:
                self.wait_for_rate_limit()
                print(f"Attempting API call with key #{self.current_key_index + 1} ({self.model_name})")

                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )

                result_text = response.text
                if result_text:
                    result = result_text.strip()

                    # Cache the successful response
                    if use_cache and cache_key:
                        cache.set(cache_key, result, timeout=86400)  # 24 hours

                    return result
                else:
                    raise Exception("Empty response from API")

            except Exception as e:
                last_error = str(e)
                print(f"API call failed with key #{self.current_key_index + 1}: {last_error}")

                # Check if it's a rate limit or quota error
                if "quota" in last_error.lower() or "rate" in last_error.lower() or "429" in last_error:
                    print("Rate limit detected, rotating key...")
                    self.rotate_key()
                    # Backoff strategy: wait longer if we're hitting rate limits
                    time.sleep(5)
                elif "invalid" in last_error.lower() or "api" in last_error.lower() or "404" in last_error:
                    print("Invalid key or model error, rotating...")
                    self.rotate_key()
                    time.sleep(1)
                else:
                    # For other errors, wait a bit longer
                    time.sleep(2)
                    self.rotate_key()

                attempts += 1

        print(f"All {max_retries} attempts failed. Last error: {last_error}")
        return None

    def grade_text_answer(
        self,
        question_text: str,
        student_answer: str,
        model_answer: str,
        required_keywords: List[str],
        max_score: int = 100
    ) -> Dict[str, Any]:
        """
        Grade a text-based answer using Gemini AI.

        Returns:
            {
                'score': int (0-100),
                'feedback': str,
                'keywords_found': List[str],
                'is_correct': bool
            }
        """
        prompt = f"""You are an expert educational assessor. Grade the following student answer.

Question: {question_text}

Model Answer: {model_answer}

Student Answer: {student_answer}

Required Keywords: {', '.join(required_keywords)}

Please provide:
1. A score from 0 to {max_score}
2. Constructive feedback (2-3 sentences)
3. Which required keywords were found
4. Whether the answer is correct (score >= 70)

Format your response as JSON:
{{
    "score": <number>,
    "feedback": "<feedback text>",
    "keywords_found": ["keyword1", "keyword2"],
    "is_correct": <true/false>
}}
"""

        response_text = self.call_api_with_fallback(prompt, use_cache=False)

        if not response_text:
            # Fallback to keyword-based grading
            return self._fallback_keyword_grading(student_answer, required_keywords, max_score)

        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                return result
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            return self._fallback_keyword_grading(student_answer, required_keywords, max_score)

    def _fallback_keyword_grading(
        self,
        student_answer: str,
        required_keywords: List[str],
        max_score: int
    ) -> Dict[str, Any]:
        """Fallback grading based on keyword matching."""
        student_lower = student_answer.lower()
        keywords_found = [kw for kw in required_keywords if kw.lower() in student_lower]

        if not required_keywords:
            score = 50  # Neutral score if no keywords
        else:
            score = int((len(keywords_found) / len(required_keywords)) * max_score)

        return {
            'score': score,
            'feedback': f"Found {len(keywords_found)} out of {len(required_keywords)} required keywords.",
            'keywords_found': keywords_found,
            'is_correct': score >= 70
        }

    def generate_explanation(self, question_text: str, correct_answer: str, topic: str) -> str:
        """Generate an explanation for why an answer is correct."""
        prompt = f"""Provide a clear, educational explanation for why this is the correct answer.

Topic: {topic}
Question: {question_text}
Correct Answer: {correct_answer}

Write 2-3 sentences explaining the reasoning. Be educational and helpful."""

        response = self.call_api_with_fallback(prompt, use_cache=True)
        return response or f"This is correct because it aligns with {topic} principles."

    def generate_flashcards(self, text_content: str, count: int = 10) -> List[Dict[str, str]]:
        """
        Generate "Perfect Flashcards" from educational text.
        Focuses on high-retention concepts and clear front-back mappings.
        """
        prompt = f"""You are an educational expert specializing in Spaced Repetition Systems (SRS). 
Generate {count} "Perfect Flashcards" from the provided text.

CRITERIA FOR PERFECT FLASHCARDS:
1. One concept per card: Avoid multi-part answers.
2. Clear and concise: 15-20 words max for the back.
3. Active recall: Use questions or fill-in-the-blanks on the front.
4. High impact: Focus on core principles, definitions, and transformative facts.

Text Content:
{text_content[:3000]}...

Return ONLY a JSON array of objects: [{{"front": "Clear Question/Prompt", "back": "Concise Answer"}}]
"""
        response = self.call_api_with_fallback(prompt, use_cache=True)

        if not response:
            print("Gemini returned None for flashcards.")
            return []

        try:
            # Better JSON extraction
            cleaned_response = response.strip()
            if '```' in cleaned_response:
                # Remove markdown code blocks if present
                for block in ['```json', '```JSON', '```']:
                    if block in cleaned_response:
                        parts = cleaned_response.split(block)
                        if len(parts) >= 3:
                            cleaned_response = parts[1]
                        elif len(parts) == 2:
                            cleaned_response = parts[1]

            # Find the actual JSON structure
            start_arr = cleaned_response.find('[')
            start_obj = cleaned_response.find('{')

            # If we found an array, prefer it
            if start_arr >= 0 and (start_obj < 0 or start_arr < start_obj):
                end_arr = cleaned_response.rfind(']') + 1
                data = json.loads(cleaned_response[start_arr:end_arr])
                return data if isinstance(data, list) else [data]

            # If we only found an object, wrap it in a list
            if start_obj >= 0:
                end_obj = cleaned_response.rfind('}') + 1
                data = json.loads(cleaned_response[start_obj:end_obj])
                return [data] if isinstance(data, dict) else []

        except Exception as e:
            print(f"Error parsing flashcards JSON: {e}")
            print(f"Original response: {response[:200]}...")

        return []

    def generate_questions_from_text(self, text_content: str, count: int = 5, question_type: str = 'mcq') -> List[Dict[str, Any]]:
        """
        Generate high-quality quiz questions from educational text.
        Supports: mcq.
        """
        # Default to MCQ instruction
        type_instruction = """Generate Multiple Choice Questions.
Format: {"question_text": "...", "options": { "A": "...", "B": "...", "C": "...", "D": "..." }, "correct_answer": "A", "explanation": "...", "confidence_score": 0.95, "difficulty": 3}"""

        prompt = f"""You are an expert educator. Create {count} {question_type} questions based on this text.
{type_instruction}

Difficulty 1-5 where 1 is basic and 5 is advanced.
Confidence 0.0-1.0 representing your certainty in the accuracy.

Text Content:
{text_content[:3000]}...

Return ONLY a JSON array of objects following the specified format. No additional text.
"""
        response = self.call_api_with_fallback(prompt, use_cache=False)

        if not response:
            print("Gemini returned None for questions.")
            return []

        try:
            cleaned_response = response.strip()
            if '```' in cleaned_response:
                for block in ['```json', '```JSON', '```']:
                    if block in cleaned_response:
                        parts = cleaned_response.split(block)
                        if len(parts) >= 3:
                            cleaned_response = parts[1]
                        elif len(parts) == 2:
                            cleaned_response = parts[1]

            start_arr = cleaned_response.find('[')
            start_obj = cleaned_response.find('{')

            if start_arr >= 0 and (start_obj < 0 or start_arr < start_obj):
                end_arr = cleaned_response.rfind(']') + 1
                data = json.loads(cleaned_response[start_arr:end_arr])
                return data if isinstance(data, list) else [data]

            if start_obj >= 0:
                end_obj = cleaned_response.rfind('}') + 1
                data = json.loads(cleaned_response[start_obj:end_obj])
                return [data] if isinstance(data, dict) else []

        except Exception as e:
            print(f"Error parsing generated questions JSON: {e}")
            print(f"Original response: {response[:200]}...")

        return []


# Singleton instance
_gemini_service = None


def get_gemini_service() -> GeminiAPIService:
    """Get or create the singleton Gemini service instance."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiAPIService()
    return _gemini_service
