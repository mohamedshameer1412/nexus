"""
syllabus/prerequisite_graph.py
Auto-infers prerequisite relationships between topics from syllabus structure.

Two strategies:
  1. Heading hierarchy  — topics under the same heading are sequentially dependent
  2. Keyword overlap    — topics sharing significant vocabulary are likely linked

This produces an initial prerequisite graph even when the teacher
has NOT manually specified prerequisites. The Evaluator Agent uses this graph
for root-cause diagnosis.
"""
import re
import logging
from typing import List, Dict, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

# Common filler words to ignore when computing keyword overlap
STOPWORDS = {
    "the","a","an","is","are","of","in","to","and","or","that","this",
    "for","with","be","by","as","at","it","its","from","on","not","can",
    "which","we","will","but","have","has","their","they","use","used",
    "using","based","given","also","each","other","through","between",
}


def extract_keywords(text: str, min_length: int = 4) -> set:
    """Tokenise text and return meaningful keywords."""
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]+\b', text.lower())
    return {w for w in words if len(w) >= min_length and w not in STOPWORDS}


def infer_prerequisites_from_structure(topics: List[dict]) -> List[Tuple[str, str]]:
    """
    Strategy 1: Heading hierarchy.
    Topics listed later in the syllabus are assumed to require earlier ones.
    Returns edges as (prerequisite_id, dependent_id).

    Only links ADJACENT topics with >= OVERLAP_THRESHOLD keyword overlap.
    """
    OVERLAP_THRESHOLD = 2  # minimum shared keywords to create a link

    edges = []
    keyword_sets = {
        t["id"]: extract_keywords(f"{t.get('name','')} {t.get('description','')}".strip())
        for t in topics
    }

    # Compare each topic to previous topics (within same unit/section if possible)
    for i, topic in enumerate(topics):
        tid = topic["id"]
        for j in range(max(0, i - 3), i):  # look back max 3 topics
            prev = topics[j]
            pid  = prev["id"]
            if pid == tid:
                continue
            shared = keyword_sets[pid] & keyword_sets[tid]
            if len(shared) >= OVERLAP_THRESHOLD:
                edges.append((pid, tid))
                logger.debug(
                    f"[PrereqGraph] {prev.get('name')} -> {topic.get('name')} "
                    f"(shared: {shared})"
                )

    return edges


def infer_prerequisites_from_keywords(topics: List[dict]) -> List[Tuple[str, str]]:
    """
    Strategy 2: Global keyword overlap across all topics.
    A topic whose name appears in another topic's description is likely a prerequisite.
    """
    edges = []
    for i, topic_a in enumerate(topics):
        name_a = topic_a.get("name", "").lower()
        keywords_a = extract_keywords(name_a)

        for j, topic_b in enumerate(topics):
            if i == j:
                continue
            desc_b = topic_b.get("description", "").lower()
            # If topic A's name is mentioned in topic B's description -> A is prereq of B
            if name_a and name_a in desc_b and len(name_a) > 4:
                edges.append((topic_a["id"], topic_b["id"]))

            # Keyword overlap across full descriptions
            keywords_b = extract_keywords(desc_b)
            if len(keywords_a & keywords_b) >= 3 and i < j:
                edges.append((topic_a["id"], topic_b["id"]))

    # Deduplicate
    return list(set(edges))


def build_and_save_prerequisite_graph(syllabus_upload_id: str) -> dict:
    """
    Full pipeline:
    1. Load topics from SyllabusUpload
    2. Infer prerequisites via both strategies
    3. Deduplicate and validate (no cycles)
    4. Save edges to Topic.prerequisites
    5. Return summary
    """
    try:
        import networkx as nx
        from syllabus.models import SyllabusUpload, Topic

        upload = SyllabusUpload.objects.get(id=syllabus_upload_id)
        topics_qs = Topic.objects.filter(syllabus=upload).order_by("order", "id")

        topic_list = [
            {
                "id":          str(t.id),
                "name":        t.name,
                "description": getattr(t, "description", "") or "",
            }
            for t in topics_qs
        ]

        if len(topic_list) < 2:
            return {"edges_created": 0, "reason": "Not enough topics to infer prerequisites"}

        # Run both strategies
        edges_struct  = infer_prerequisites_from_structure(topic_list)
        edges_keyword = infer_prerequisites_from_keywords(topic_list)
        all_edges     = list(set(edges_struct + edges_keyword))

        # Validate: remove edges that create cycles
        G = nx.DiGraph()
        valid_edges = []
        for (prereq_id, dep_id) in all_edges:
            G.add_edge(prereq_id, dep_id)
            if nx.is_directed_acyclic_graph(G):
                valid_edges.append((prereq_id, dep_id))
            else:
                G.remove_edge(prereq_id, dep_id)

        # Save to DB
        topic_map = {str(t.id): t for t in topics_qs}
        saved = 0
        for prereq_id, dep_id in valid_edges:
            if prereq_id in topic_map and dep_id in topic_map:
                prereq_topic = topic_map[prereq_id]
                dep_topic    = topic_map[dep_id]
                if hasattr(dep_topic, "prerequisites"):
                    dep_topic.prerequisites.add(prereq_topic)
                    saved += 1

        logger.info(
            f"[PrereqGraph] syllabus={syllabus_upload_id}: "
            f"{len(all_edges)} inferred, {saved} valid edges saved"
        )
        return {
            "topics":        len(topic_list),
            "edges_inferred": len(all_edges),
            "edges_saved":    saved,
            "cycles_removed": len(all_edges) - len(valid_edges),
        }

    except Exception as e:
        logger.error(f"[PrereqGraph] build_and_save failed: {e}")
        return {"error": str(e)}
