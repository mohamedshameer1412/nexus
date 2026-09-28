"""
evaluator_agent/graph.py
Builds a prerequisite DAG from syllabus topic data (NetworkX).
Performs backwards BFS to find root cause of a concept failure.
"""
import networkx as nx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def build_prerequisite_graph(topics: list) -> nx.DiGraph:
    """
    Build a directed acyclic graph of topic prerequisites.

    Args:
        topics: list of dicts with keys:
          - id: str
          - name: str
          - prerequisites: list of topic ids

    Returns: nx.DiGraph where edge A -> B means "A is a prerequisite of B"
    """
    G = nx.DiGraph()
    for topic in topics:
        tid = str(topic.get("id") or topic.get("topic_id"))
        G.add_node(tid, name=topic.get("name", tid))
        for prereq in topic.get("prerequisites", []):
            G.add_edge(str(prereq), tid)   # prereq → topic
    return G


def find_root_cause(
    G: nx.DiGraph,
    failed_topic_id: str,
    verified_mastery: dict,
    mastery_threshold: float = 70.0,
) -> dict:
    """
    Given a topic the student failed, walk BACKWARDS through the prerequisite
    graph to find the deepest ancestor that is also below threshold.

    This is the root cause: the concept they never actually learned,
    that is silently breaking everything downstream.

    Returns:
      {
        "failed_topic":   str,
        "root_cause":     str,   # the deepest weak ancestor
        "chain":          list,  # path from root_cause -> failed_topic
        "all_weak_ancestors": list,
      }
    """
    if failed_topic_id not in G:
        logger.warning(f"[EvaluatorAgent] Topic {failed_topic_id} not in graph")
        return {
            "failed_topic": failed_topic_id,
            "root_cause": failed_topic_id,
            "chain": [failed_topic_id],
            "all_weak_ancestors": [],
        }

    # BFS backwards through predecessors
    weak_ancestors = []
    visited = set()
    queue = [failed_topic_id]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        mastery = verified_mastery.get(current, 0.0)
        if mastery < mastery_threshold and current != failed_topic_id:
            weak_ancestors.append(current)

        # Walk to predecessors (prerequisite topics)
        for predecessor in G.predecessors(current):
            if predecessor not in visited:
                queue.append(predecessor)

    # Find the deepest root (furthest from failed_topic in graph distance)
    root_cause = failed_topic_id
    max_distance = 0

    for ancestor in weak_ancestors:
        try:
            # Shortest path length from ancestor to failed_topic
            dist = nx.shortest_path_length(G, source=ancestor, target=failed_topic_id)
            if dist > max_distance:
                max_distance = dist
                root_cause = ancestor
        except nx.NetworkXNoPath:
            pass

    # Build chain: root_cause -> ... -> failed_topic
    chain = [failed_topic_id]
    try:
        if root_cause != failed_topic_id:
            chain = nx.shortest_path(G, source=root_cause, target=failed_topic_id)
    except nx.NetworkXNoPath:
        pass

    return {
        "failed_topic":       failed_topic_id,
        "root_cause":         root_cause,
        "chain":              chain,
        "all_weak_ancestors": weak_ancestors,
        "diagnosis": _make_diagnosis(root_cause, chain, G),
    }


def _make_diagnosis(root_cause: str, chain: list, G: nx.DiGraph) -> str:
    root_name = G.nodes[root_cause].get("name", root_cause) if root_cause in G else root_cause
    if len(chain) <= 1:
        return f"The topic itself ({root_name}) is the issue — no prerequisite gap found."
    chain_names = [G.nodes[n].get("name", n) if n in G else n for n in chain]
    return (
        f"Root cause: '{root_name}'. "
        f"It blocks {len(chain) - 1} downstream concept(s): {' → '.join(chain_names)}."
    )
