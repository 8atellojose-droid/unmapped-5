"""
Optional Hugging Face semantic matching for UNMAPPED.

This module adds a lightweight multilingual semantic retrieval layer on top of
the existing deterministic taxonomy matcher. It is designed to improve recall
for informal, messy, or cross-lingual profile text without replacing the
audit-friendly rule-based pipeline.
"""

from __future__ import annotations

import importlib.util
import os
from functools import lru_cache

import numpy as np

from taxonomy import GLOBAL_TAXONOMY, SKILL_NORMALIZATION_MAP


DEFAULT_EMBEDDING_MODEL = os.getenv(
    "UNMAPPED_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
DEFAULT_ROLE_THRESHOLD = float(os.getenv("UNMAPPED_ROLE_SIM_THRESHOLD", "0.32"))
FALLBACK_ROLE_THRESHOLD = float(os.getenv("UNMAPPED_FALLBACK_ROLE_THRESHOLD", "0.24"))
ROLE_SIMILARITY_WEIGHT = float(os.getenv("UNMAPPED_ROLE_SIM_WEIGHT", "3.5"))
DEFAULT_SKILL_THRESHOLD = float(os.getenv("UNMAPPED_SKILL_SIM_THRESHOLD", "0.36"))
FORCE_OFFLINE_EMBEDDINGS = os.getenv("UNMAPPED_EMBEDDING_OFFLINE", "0").strip().lower() in {
    "1", "true", "yes", "on"
}

_MODEL = None
_MODEL_LOAD_ATTEMPTED = False
_MODEL_LOAD_ERROR: str | None = None


def semantic_matching_enabled() -> bool:
    flag = os.getenv("UNMAPPED_ENABLE_SEMANTIC_MATCHING", "1").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def sentence_transformers_installed() -> bool:
    return importlib.util.find_spec("sentence_transformers") is not None


def semantic_backend_status() -> dict:
    return {
        "enabled": semantic_matching_enabled(),
        "package_installed": sentence_transformers_installed(),
        "model_name": DEFAULT_EMBEDDING_MODEL,
        "model_loaded": _MODEL is not None,
        "load_attempted": _MODEL_LOAD_ATTEMPTED,
        "load_error": _MODEL_LOAD_ERROR,
        "offline_mode": FORCE_OFFLINE_EMBEDDINGS,
        "role_threshold": DEFAULT_ROLE_THRESHOLD,
        "fallback_threshold": FALLBACK_ROLE_THRESHOLD,
        "skill_threshold": DEFAULT_SKILL_THRESHOLD,
        "similarity_weight": ROLE_SIMILARITY_WEIGHT,
    }


def _load_model():
    global _MODEL, _MODEL_LOAD_ATTEMPTED, _MODEL_LOAD_ERROR
    if _MODEL is not None:
        return _MODEL
    if _MODEL_LOAD_ATTEMPTED:
        return None

    _MODEL_LOAD_ATTEMPTED = True

    if not semantic_matching_enabled():
        _MODEL_LOAD_ERROR = "Semantic matching disabled by UNMAPPED_ENABLE_SEMANTIC_MATCHING."
        return None
    if not sentence_transformers_installed():
        _MODEL_LOAD_ERROR = "sentence-transformers is not installed."
        return None

    try:
        from sentence_transformers import SentenceTransformer

        # Prefer local cache first so once the model has been pulled, the demo
        # keeps working cleanly in restricted or low-bandwidth environments.
        try:
            _MODEL = SentenceTransformer(
                DEFAULT_EMBEDDING_MODEL,
                local_files_only=True,
            )
            _MODEL_LOAD_ERROR = None
            return _MODEL
        except Exception as local_exc:
            if FORCE_OFFLINE_EMBEDDINGS:
                _MODEL_LOAD_ERROR = f"{type(local_exc).__name__}: {local_exc}"
                return None

        _MODEL = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
        _MODEL_LOAD_ERROR = None
        return _MODEL
    except Exception as exc:  # pragma: no cover - graceful fallback for offline envs
        _MODEL_LOAD_ERROR = f"{type(exc).__name__}: {exc}"
        return None


def _role_document(role_id: str, role: dict) -> str:
    examples = " ".join(role.get("cross_market_examples", {}).values())
    signals = ", ".join(role.get("skill_signals", []))
    core = ", ".join(role.get("core_skills", []))
    bridges = ", ".join(role.get("bridge_skills", []))
    opportunity_types = ", ".join(role.get("opportunity_types", []))
    return (
        f"{role_id}. {role.get('title', '')}. {role.get('isco_like_category', '')}. "
        f"Signals: {signals}. Core skills: {core}. Bridge skills: {bridges}. "
        f"Country examples: {examples}. Opportunity types: {opportunity_types}."
    )


@lru_cache(maxsize=1)
def _role_corpus() -> tuple[list[str], list[str]]:
    role_ids = list(GLOBAL_TAXONOMY.keys())
    role_docs = [
        _role_document(role_id, GLOBAL_TAXONOMY[role_id])
        for role_id in role_ids
    ]
    return role_ids, role_docs


@lru_cache(maxsize=1)
def _role_embeddings():
    model = _load_model()
    if model is None:
        return None
    _, role_docs = _role_corpus()
    return model.encode(role_docs, normalize_embeddings=True)


@lru_cache(maxsize=1)
def _skill_corpus() -> tuple[list[str], list[str], dict[str, list[str]]]:
    grouped: dict[str, list[str]] = {}
    for raw_phrase, canonical in SKILL_NORMALIZATION_MAP.items():
        grouped.setdefault(canonical, []).append(raw_phrase)

    skill_names = sorted(grouped.keys())
    skill_docs = [
        f"{skill}. Example phrases: {', '.join(sorted(grouped[skill]))}."
        for skill in skill_names
    ]
    return skill_names, skill_docs, grouped


@lru_cache(maxsize=1)
def _skill_embeddings():
    model = _load_model()
    if model is None:
        return None
    _, skill_docs, _ = _skill_corpus()
    return model.encode(skill_docs, normalize_embeddings=True)


def score_roles_semantically(profile_text: str, top_k: int | None = None) -> list[dict]:
    """
    Return semantic role matches for a free-text profile.

    Scores are cosine similarities over sentence embeddings. Results are sorted
    descending and truncated to top_k when provided.
    """
    model = _load_model()
    if model is None:
        return []

    text = (profile_text or "").strip()
    if not text:
        return []

    role_embeddings = _role_embeddings()
    if role_embeddings is None:
        return []

    role_ids, role_docs = _role_corpus()
    query_embedding = model.encode([text], normalize_embeddings=True)[0]
    similarities = np.matmul(role_embeddings, query_embedding)

    matches = []
    for role_id, role_doc, similarity in zip(role_ids, role_docs, similarities):
        role = GLOBAL_TAXONOMY[role_id]
        matches.append({
            "role_id": role_id,
            "role_title": role.get("title", ""),
            "semantic_score": float(similarity),
            "semantic_evidence": role_doc,
        })

    matches.sort(key=lambda item: item["semantic_score"], reverse=True)
    if top_k is not None:
        return matches[:top_k]
    return matches


def score_skills_semantically(profile_text: str, top_k: int | None = None) -> list[dict]:
    """
    Return semantic matches against the canonical skill vocabulary.

    This is intentionally kept separate from deterministic extraction so the
    UI can distinguish explicit evidence from semantic hints.
    """
    model = _load_model()
    if model is None:
        return []

    text = (profile_text or "").strip()
    if not text:
        return []

    skill_embeddings = _skill_embeddings()
    if skill_embeddings is None:
        return []

    skill_names, _, grouped = _skill_corpus()
    query_embedding = model.encode([text], normalize_embeddings=True)[0]
    similarities = np.matmul(skill_embeddings, query_embedding)

    matches = []
    for skill_name, similarity in zip(skill_names, similarities):
        matches.append({
            "canonical_skill": skill_name,
            "semantic_score": float(similarity),
            "example_phrases": grouped.get(skill_name, [])[:5],
        })

    matches.sort(key=lambda item: item["semantic_score"], reverse=True)
    if top_k is not None:
        return matches[:top_k]
    return matches
