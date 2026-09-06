"""
ml_engine/irt.py
1-Parameter Logistic (1PL) Rasch Item Response Theory model.
CPU-only, pure Python + NumPy. No training data required at launch.

Two functions:
  1. update_theta(theta, responses)
     -> updates student ability estimate after a quiz session

  2. select_next_question(theta, candidate_questions)
     -> selects the question whose difficulty is closest to student ability
        (maximises information, minimises guessing/ceiling effects)
"""
import math
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# IRT constants
DEFAULT_THETA    = 0.0    # starting ability (logit scale, N(0,1) assumed)
DEFAULT_DIFF     = 0.0    # default item difficulty if not calibrated
LEARNING_RATE    = 0.3    # step size for ability update (ELO-style)
MAX_THETA        =  3.0   # clamp ability to ±3 logits
MIN_THETA        = -3.0


def probability_correct(theta: float, difficulty: float) -> float:
    """
    1PL Rasch model: P(correct | theta, b) = 1 / (1 + exp(-(theta - b)))
    theta = student ability (logit)
    b     = item difficulty (logit)
    """
    return 1.0 / (1.0 + math.exp(-(theta - difficulty)))


def update_theta(
    current_theta: float,
    responses: List[Dict],
) -> Dict:
    """
    Update student ability after a set of responses.
    Uses gradient step: theta += lr * (observed - expected)

    Args:
        current_theta: float — current ability estimate
        responses: list of dicts:
          [{"difficulty": float, "is_correct": bool}, ...]

    Returns:
      {
        "new_theta":   float,
        "delta":       float,
        "items_used":  int,
        "avg_p_correct": float,
      }
    """
    if not responses:
        return {
            "new_theta": current_theta,
            "delta": 0.0,
            "items_used": 0,
            "avg_p_correct": 0.0,
        }

    theta = current_theta
    total_expected = 0.0

    for resp in responses:
        b         = resp.get("difficulty", DEFAULT_DIFF)
        observed  = 1.0 if resp.get("is_correct", False) else 0.0
        expected  = probability_correct(theta, b)
        residual  = observed - expected
        theta    += LEARNING_RATE * residual
        total_expected += expected

    # Clamp to valid range
    theta = max(MIN_THETA, min(MAX_THETA, theta))
    delta = round(theta - current_theta, 4)

    logger.debug(f"[IRT] theta {current_theta:.3f} -> {theta:.3f} (delta={delta})")

    return {
        "new_theta":     round(theta, 4),
        "delta":         delta,
        "items_used":    len(responses),
        "avg_p_correct": round(total_expected / len(responses), 4),
    }


def select_next_question(
    theta: float,
    candidate_questions: List[Dict],
    answered_ids: Optional[List] = None,
) -> Optional[Dict]:
    """
    Select the next question to maximise information for this student.
    Strategy: choose the question whose difficulty b is closest to theta.
    This minimises guessing (too easy) and frustration (too hard).

    Args:
        theta:               student ability estimate
        candidate_questions: list of dicts with at least:
          {"id": any, "difficulty": float, ...}
        answered_ids:        list of already-answered question IDs (skip these)

    Returns: the selected question dict, or None if no candidates remain
    """
    answered_ids = set(answered_ids or [])

    eligible = [
        q for q in candidate_questions
        if q.get("id") not in answered_ids
    ]

    if not eligible:
        return None

    # Score each question: lower |b - theta| = better match
    def information(q):
        b = q.get("difficulty", DEFAULT_DIFF)
        p = probability_correct(theta, b)
        # Fisher information: p * (1-p) — peaks when p=0.5 (b ≈ theta)
        return p * (1 - p)

    best = max(eligible, key=information)
    logger.debug(
        f"[IRT] theta={theta:.3f} -> selected question {best.get('id')} "
        f"(difficulty={best.get('difficulty', 0):.3f})"
    )
    return best


def calibrate_difficulty(item_responses: List[bool]) -> float:
    """
    Simple difficulty estimate for a question from historical responses.
    difficulty = logit(1 - proportion_correct)
    Proportion correct 0.5 -> difficulty 0.0 (average)
    Proportion correct 0.1 -> difficulty ~2.2 (hard)
    Proportion correct 0.9 -> difficulty ~-2.2 (easy)

    Only used in production calibration — not needed at demo stage.
    """
    if not item_responses:
        return DEFAULT_DIFF
    n_correct = sum(item_responses)
    p = n_correct / len(item_responses)
    # Clamp to avoid log(0)
    p = max(0.01, min(0.99, p))
    return round(math.log((1 - p) / p), 4)
