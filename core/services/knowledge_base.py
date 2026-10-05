"""
core/services/knowledge_base.py — Grounded Knowledge Retriever for Guidance Chatbot

Indexes verified university policies, office hours, and counseling resources.
Provides lightweight, zero-dependency relevance scoring to ground LLM generations
and prevent hallucinations.
"""

import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge')


class GuidanceKnowledgeBase:
    _docs: List[Dict[str, Any]] = []
    _loaded: bool = False

    @classmethod
    def load(cls, force_reload: bool = False):
        """Loads all JSON files from core/knowledge/ into memory."""
        if cls._loaded and not force_reload:
            return

        cls._docs = []
        if not os.path.exists(KNOWLEDGE_DIR):
            logger.warning("Knowledge directory not found: %s", KNOWLEDGE_DIR)
            return

        for fname in sorted(os.listdir(KNOWLEDGE_DIR)):
            if fname.endswith('.json'):
                fpath = os.path.join(KNOWLEDGE_DIR, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            cls._docs.extend(data)
                except Exception as e:
                    logger.error("Failed to load knowledge file %s: %s", fname, e)

        cls._loaded = True
        logger.info("Loaded %d knowledge records from %s", len(cls._docs), KNOWLEDGE_DIR)

    @classmethod
    def retrieve(cls, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most relevant knowledge articles for a user's query.
        Uses keyword-overlap and token matching with weighted scoring.
        """
        if not cls._loaded:
            cls.load()

        if not cls._docs or not query.strip():
            return []

        words = [w.lower().strip("?,.!:;\"'") for w in query.split() if len(w) > 2]
        scored_docs = []

        for doc in cls._docs:
            keywords = [k.lower() for k in doc.get('keywords', [])]
            content = doc.get('content', '').lower()
            topic = doc.get('topic', '').lower()

            score = 0
            for word in words:
                # Direct keyword tag match
                if any(word in kw for kw in keywords):
                    score += 4
                # Title / topic match
                if word in topic:
                    score += 2
                # Content match
                if word in content:
                    score += 1

            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:top_k]]

    @classmethod
    def get_grounded_context_block(cls, query: str) -> str:
        """
        Formats retrieved knowledge into a clean context block for prompt injection.
        """
        chunks = cls.retrieve(query, top_k=2)
        if not chunks:
            return "No specific reference documents found for this query in the university guidance handbook."

        lines = []
        for i, c in enumerate(chunks, 1):
            lines.append(f"[{i}. {c.get('topic')}]:\n{c.get('content')}")
        return "\n\n".join(lines)
