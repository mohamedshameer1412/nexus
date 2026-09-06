"""
users/career_gap.py
Career Skill Gap Analyzer.
Compares the student's verified_skills in their Digital Twin
against required skills extracted from a job description or career goal.

Uses FAISS cosine similarity on SBERT embeddings — no external API required.

Returns:
  - matched skills (you have these)
  - missing skills (you need these)
  - recommended topics to study (NEXUS maps missing skills -> syllabus topics)
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def analyze_career_gap(
    verified_skills: List[str],
    job_description: str,
    top_k_missing: int = 10,
) -> dict:
    """
    Args:
        verified_skills: list of skill strings from LearnerDigitalTwin.verified_skills
        job_description: raw text from job posting or career goal description
        top_k_missing:   max missing skills to return

    Returns: {
        matched:          list of skills you already have
        missing:          list of required skills you lack
        match_pct:        overall readiness percentage
        recommended_topics: topics from your syllabus to cover the gaps
    }
    """
    try:
        from sentence_transformers import SentenceTransformer
        from django.conf import settings
        import numpy as np

        model_name = settings.NEXUS.get("SBERT_MODEL", "all-MiniLM-L6-v2")
        model = SentenceTransformer(model_name)

        # Extract required skills from JD using simple noun-phrase extraction
        required_skills = _extract_skills_from_jd(job_description)

        if not required_skills:
            return {
                "matched": [],
                "missing": [],
                "match_pct": 0.0,
                "recommended_topics": [],
                "error": "Could not extract skills from job description",
            }

        if not verified_skills:
            return {
                "matched": [],
                "missing": required_skills[:top_k_missing],
                "match_pct": 0.0,
                "recommended_topics": required_skills[:5],
            }

        # Embed all skills
        verified_embs  = model.encode(verified_skills,  convert_to_numpy=True, show_progress_bar=False)
        required_embs  = model.encode(required_skills,  convert_to_numpy=True, show_progress_bar=False)

        # Normalise for cosine similarity
        verified_embs  = verified_embs  / (np.linalg.norm(verified_embs,  axis=1, keepdims=True) + 1e-9)
        required_embs  = required_embs  / (np.linalg.norm(required_embs,  axis=1, keepdims=True) + 1e-9)

        MATCH_THRESHOLD = 0.75  # cosine similarity threshold for a skill to be "matched"

        matched  = []
        missing  = []

        for i, req_skill in enumerate(required_skills):
            # Cosine similarities between this required skill and all verified skills
            sims = required_embs[i] @ verified_embs.T  # shape: (n_verified,)
            best_sim = float(sims.max()) if len(sims) > 0 else 0.0

            if best_sim >= MATCH_THRESHOLD:
                matched.append({
                    "skill":       req_skill,
                    "confidence":  round(best_sim, 3),
                    "matched_to":  verified_skills[int(sims.argmax())],
                })
            else:
                missing.append({
                    "skill":       req_skill,
                    "best_match":  round(best_sim, 3),
                })

        match_pct = (len(matched) / len(required_skills) * 100) if required_skills else 0.0

        # Recommend topics to cover the gaps
        recommended_topics = _map_missing_to_topics(
            [m["skill"] for m in missing[:top_k_missing]]
        )

        return {
            "matched":              matched,
            "missing":              missing[:top_k_missing],
            "total_required":       len(required_skills),
            "match_pct":            round(match_pct, 2),
            "recommended_topics":   recommended_topics,
        }

    except ImportError:
        logger.warning("[CareerGap] sentence-transformers not installed, using keyword fallback")
        return _keyword_fallback(verified_skills, job_description, top_k_missing)
    except Exception as e:
        logger.error(f"[CareerGap] analyze_career_gap failed: {e}")
        return {"error": str(e)}


def _extract_skills_from_jd(jd_text: str) -> List[str]:
    """
    Extract skill keywords from a job description using pattern matching.
    Returns a deduplicated list of skill strings.

    In production this would use spaCy NER or a skills taxonomy.
    For demo: regex for capitalised phrases, tech terms, and known patterns.
    """
    import re

    # Remove special characters, normalise whitespace
    text = re.sub(r'[^\w\s\+\#]', ' ', jd_text)

    # Patterns for skills
    patterns = [
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',          # TitleCase phrases
        r'\b(?:Python|Java|Django|React|SQL|ML|AI|NLP|TensorFlow|PyTorch|'
        r'Docker|Kubernetes|AWS|GCP|REST|API|Git|Linux|Node\.js|Next\.js)\b',
        r'\b\w+(?:-\w+)+\b',                              # hyphenated terms
    ]

    skills = set()
    for pattern in patterns:
        matches = re.findall(pattern, jd_text)
        skills.update(m.strip() for m in matches if len(m.strip()) > 2)

    # Filter out stop words
    STOPS = {"The","And","Or","For","With","This","That","Are","Has","Have"}
    skills = {s for s in skills if s not in STOPS and len(s) > 3}
    return list(skills)[:50]  # cap at 50 skills


def _map_missing_to_topics(missing_skills: List[str]) -> List[str]:
    """Map missing skills to FAISS-indexed syllabus topics."""
    try:
        from ml_engine.faiss_index import query_index
        topics = set()
        for skill in missing_skills[:5]:
            results = query_index(skill, top_k=2)
            for r in results:
                if r.get("topic"):
                    topics.add(r["topic"])
        return list(topics)
    except Exception:
        return missing_skills[:5]  # fallback: return skills themselves


def _keyword_fallback(verified_skills, job_description, top_k_missing) -> dict:
    """Simple keyword match when SBERT is unavailable."""
    jd_lower = job_description.lower()
    matched  = [s for s in verified_skills if s.lower() in jd_lower]
    skills   = _extract_skills_from_jd(job_description)
    missing  = [{"skill": s, "best_match": 0.0} for s in skills if s.lower() not in
                {v.lower() for v in verified_skills}]
    match_pct = (len(matched) / len(skills) * 100) if skills else 0.0
    return {
        "matched":            [{"skill": s, "confidence": 1.0, "matched_to": s} for s in matched],
        "missing":            missing[:top_k_missing],
        "total_required":     len(skills),
        "match_pct":          round(match_pct, 2),
        "recommended_topics": [m["skill"] for m in missing[:5]],
    }
