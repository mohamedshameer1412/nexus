"""
ml_engine/faiss_index.py
Builds and queries a FAISS vector index from syllabus text chunks.
Uses Sentence-BERT (all-MiniLM-L6-v2) — CPU-only, no GPU required.

Two operations:
  1. build_index(chunks)  -> saves index + metadata to disk
  2. query_index(query, top_k) -> returns top-k matching chunks
"""
import json
import logging
import numpy as np
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_model():
    """Lazy-load Sentence-BERT once and cache it."""
    if not hasattr(_get_model, "_model"):
        from sentence_transformers import SentenceTransformer
        model_name = settings.NEXUS.get("SBERT_MODEL", "all-MiniLM-L6-v2")
        logger.info(f"[FAISS] Loading SBERT model: {model_name}")
        _get_model._model = SentenceTransformer(model_name)
    return _get_model._model


def _get_index_paths():
    index_path = Path(settings.NEXUS["FAISS_INDEX_PATH"])
    meta_path  = Path(settings.NEXUS["FAISS_META_PATH"])
    index_path.parent.mkdir(parents=True, exist_ok=True)
    return index_path, meta_path


def build_index(chunks: list) -> dict:
    """
    Build a FAISS flat-L2 index from a list of text chunks.

    Args:
        chunks: list of dicts with keys:
          - id:      unique identifier
          - text:    the text content to embed
          - topic:   topic name (for filtering)
          - source:  source document name

    Returns: {"indexed": int, "index_path": str}
    """
    import faiss

    if not chunks:
        logger.warning("[FAISS] No chunks provided to build_index")
        return {"indexed": 0}

    model = _get_model()
    texts = [c["text"] for c in chunks]

    logger.info(f"[FAISS] Embedding {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    embeddings = embeddings.astype(np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    index_path, meta_path = _get_index_paths()

    faiss.write_index(index, str(index_path))
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    logger.info(f"[FAISS] Index built: {len(chunks)} vectors, dim={dim} -> {index_path}")
    return {"indexed": len(chunks), "index_path": str(index_path)}


def query_index(query_text: str, top_k: int = 5) -> list:
    """
    Query the FAISS index for the top-k most relevant chunks.

    Args:
        query_text: the student's query or topic name
        top_k:      number of results to return

    Returns: list of chunk dicts with added "score" field (lower = more similar)
    """
    import faiss

    index_path, meta_path = _get_index_paths()

    if not index_path.exists() or not meta_path.exists():
        logger.warning("[FAISS] Index not found. Run build_index first.")
        return []

    model = _get_model()
    index = faiss.read_index(str(index_path))

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    query_vec = model.encode([query_text], convert_to_numpy=True).astype(np.float32)
    distances, indices = index.search(query_vec, min(top_k, index.ntotal))

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        chunk = dict(metadata[idx])
        chunk["score"] = round(float(dist), 4)
        results.append(chunk)

    return results


def build_index_from_syllabus(syllabus_upload_id: str) -> dict:
    """
    Convenience wrapper: loads chunks from a SyllabusUpload model
    and builds the FAISS index. Called by the syllabus processing pipeline.
    """
    try:
        from syllabus.models import SyllabusUpload, Topic
        upload = SyllabusUpload.objects.get(id=syllabus_upload_id)
        topics = Topic.objects.filter(syllabus=upload)

        chunks = []
        for topic in topics:
            chunks.append({
                "id":     str(topic.id),
                "text":   f"{topic.name}. {getattr(topic, 'description', '')}".strip(),
                "topic":  topic.name,
                "source": upload.filename if hasattr(upload, "filename") else "syllabus",
            })

        if not chunks:
            return {"indexed": 0, "reason": "no topics found"}

        return build_index(chunks)

    except Exception as e:
        logger.error(f"[FAISS] build_index_from_syllabus failed: {e}")
        return {"indexed": 0, "error": str(e)}
