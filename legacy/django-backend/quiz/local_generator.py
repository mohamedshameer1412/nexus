"""
quiz/local_generator.py

Local-model quiz question generation via Ollama. Same public interface as
quiz.ai_generator.QuizGenerator (generate_questions / save_generated_questions)
so ai_views.py can pick either engine without branching on their internals.

Batches requests into groups of BATCH_SIZE questions per Ollama call — a
single large batch (10+ questions in one JSON blob) is where local 7-8B
models most often truncate or emit malformed JSON, so smaller batches trade
a bit of wall-clock time for much higher success rate on modest hardware.
"""
import time
from typing import Dict, List

from quiz.models import Topic, Question, AIGeneratedQuestion
from utils.ollama_service import get_ollama_service, OllamaUnavailableError

BATCH_SIZE = 5


class LocalQuizGenerator:
    """Drop-in replacement for QuizGenerator that runs entirely on-machine."""

    def __init__(self, model: str = None):
        self.service = get_ollama_service(model)
        self.model = self.service.model

    def generate_questions(
        self,
        topic: Topic,
        num_questions: int,
        difficulty: str,
        question_type: str = "mcq",
        user=None,
    ) -> Dict:
        if not self.service.is_available():
            raise ValueError(
                f"Local model '{self.model}' is not available. Run `ollama pull {self.model}` "
                f"and make sure `ollama serve` is running, or choose a cloud model instead."
            )

        start_time = time.time()
        all_questions: List[Dict] = []
        remaining = num_questions
        batch_num = 0

        while remaining > 0:
            batch_num += 1
            n = min(BATCH_SIZE, remaining)
            prompt = self._build_prompt(topic, n, difficulty, question_type, batch_num)
            data = self.service.generate_json(prompt, timeout=60 + n * 40)
            batch_questions = data.get("questions", [])
            if not isinstance(batch_questions, list) or not batch_questions:
                raise ValueError(f"Local model returned no usable questions for batch {batch_num}.")

            for q in batch_questions:
                self._validate_question(q)
                q.setdefault("difficulty_level", self._difficulty_to_number(difficulty))
                q.setdefault("irt_difficulty", self._difficulty_to_irt(difficulty))
                q.setdefault("irt_discrimination", 1.0)

            all_questions.extend(batch_questions[:n])
            remaining -= n

        generation_time = time.time() - start_time

        metadata = {
            "model": self.model,
            "provider": "ollama",
            "generation_time": round(generation_time, 2),
            "topic_id": str(topic.id),
            "topic_name": topic.name,
            "difficulty": difficulty,
            "question_type": question_type,
            "estimated_cost": 0.0,
            "runs_locally": True,
        }

        return {
            "status": "success",
            "questions": all_questions,
            "metadata": metadata,
            "prompt": f"[{batch_num} local batches, {len(all_questions)} questions]",
        }

    def _build_prompt(self, topic: Topic, n: int, difficulty: str, question_type: str, batch_num: int) -> str:
        difficulty_instructions = {
            "easy": "suitable for beginners, testing basic recall and understanding",
            "medium": "requiring application and analysis of concepts",
            "hard": "challenging, requiring synthesis and evaluation",
        }
        type_instructions = {
            "mcq": "multiple-choice questions with 4 options (A, B, C, D)",
            "true_false": "true/false questions phrased as two-option (A=True, B=False) multiple choice",
            "fill_blank": "fill-in-the-blank questions rendered as multiple choice with the blank's answer among 4 options",
        }
        variety_hint = f" This is batch {batch_num} — cover different sub-aspects of the topic than a typical first batch would." if batch_num > 1 else ""

        return f"""Generate exactly {n} {difficulty} {type_instructions[question_type]} about the topic: "{topic.name}".

Topic description: {topic.description or 'No description provided'}

Requirements:
1. Questions should be {difficulty_instructions[difficulty]}.
2. Each question must be clear, unambiguous, and educationally valuable.
3. Ensure the correct answer is definitively correct and distractors are plausible but clearly wrong.{variety_hint}

Output ONLY a JSON object with this exact shape, no markdown, no prose:
{{
  "questions": [
    {{
      "question_text": "string",
      "option_a": "string",
      "option_b": "string",
      "option_c": "string",
      "option_d": "string",
      "correct_answer": "A",
      "explanation": "string"
    }}
  ]
}}
The questions array must contain exactly {n} items."""

    def _validate_question(self, question: Dict):
        required = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer", "explanation"]
        for field in required:
            if field not in question or question[field] in (None, ""):
                raise ValueError(f"Generated question missing required field: {field}")
        if str(question["correct_answer"]).upper() not in ["A", "B", "C", "D"]:
            raise ValueError(f"Invalid correct_answer: {question['correct_answer']}")
        question["correct_answer"] = str(question["correct_answer"]).upper()

    def _difficulty_to_number(self, difficulty: str) -> int:
        return {"easy": 2, "medium": 3, "hard": 4}.get(difficulty.lower(), 3)

    def _difficulty_to_irt(self, difficulty: str) -> float:
        return {"easy": -0.5, "medium": 0.0, "hard": 0.5}.get(difficulty.lower(), 0.0)

    def save_generated_questions(
        self,
        questions_data: List[Dict],
        topic: Topic,
        metadata: Dict,
        prompt: str,
        user,
    ) -> List[Question]:
        """Identical persistence path to QuizGenerator — same Question/
        AIGeneratedQuestion tables, only the generation metadata differs."""
        created_questions = []
        for q_data in questions_data:
            question = Question.objects.create(
                topic=topic,
                question_text=q_data["question_text"],
                option_a=q_data["option_a"],
                option_b=q_data["option_b"],
                option_c=q_data["option_c"],
                option_d=q_data["option_d"],
                correct_answer=q_data["correct_answer"],
                explanation=q_data.get("explanation", ""),
                difficulty_level=q_data.get("difficulty_level", 3),
                irt_difficulty=q_data.get("irt_difficulty", 0.0),
                irt_discrimination=q_data.get("irt_discrimination", 1.0),
                created_by=user,
            )
            AIGeneratedQuestion.objects.create(
                question=question,
                generation_prompt=prompt,
                model_used=self.model,
                generation_metadata=metadata,
                generated_by=user,
                is_approved=False,
            )
            created_questions.append(question)
        return created_questions
