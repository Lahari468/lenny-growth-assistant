"""
Vector store implementation supporting PostgreSQL + pgvector with SQLite fallback.
Provides semantic retrieval, metadata ranking, and traceability back to source transcripts.
"""

import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import TranscriptModel, TranscriptChunkModel
from app.retrieval.embeddings import get_embedding_engine
from app.schemas.message import Citation

logger = logging.getLogger("lenny_growth.vector_store")

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

class VectorStore:
    def __init__(self):
        self.embedding_engine = get_embedding_engine()

    async def search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 4,
        min_similarity: float = 0.20,
    ) -> List[Citation]:
        """
        Embed the query and retrieve top-K relevant chunks with full transcript metadata.
        Returns empty list if no chunks meet the minimum similarity threshold.
        """
        query_embedding = self.embedding_engine.embed_text(query)
        
        # Query all chunks with their associated transcript
        stmt = (
            select(
                TranscriptChunkModel.id,
                TranscriptChunkModel.transcript_id,
                TranscriptChunkModel.content,
                TranscriptChunkModel.embedding_json,
                TranscriptChunkModel.metadata_json,
                TranscriptModel.title,
                TranscriptModel.guest,
                TranscriptModel.source_url,
            )
            .join(TranscriptModel, TranscriptChunkModel.transcript_id == TranscriptModel.id)
        )
        
        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            logger.warning("Vector store is empty! No transcript chunks found.")
            return []

        STOP_WORDS = {
            "how", "should", "what", "where", "when", "why", "who", "which",
            "does", "doesnt", "would", "could", "will", "with", "from", "that",
            "this", "about", "have", "more", "most", "been", "being", "were",
            "their", "there", "they", "your", "into", "some", "such"
        }
        import re
        query_terms = [t for t in re.findall(r"\b[a-z0-9_-]{3,}\b", query.lower()) if t not in STOP_WORDS]

        scored_candidates = []
        for row in rows:
            chunk_id, transcript_id, content, emb_json, meta_json, ep_title, guest, source_url = row
            try:
                emb_vec = json.loads(emb_json)
                cos_score = cosine_similarity(query_embedding, emb_vec)
                if cos_score >= min_similarity:
                    # Hybrid scoring: combine dense semantic similarity with lexical keyword overlap
                    lex_score = 0.0
                    if query_terms:
                        text_lower = f"{content} {ep_title} {guest}".lower()
                        matches = sum(
                            1 for t in query_terms
                            if t in text_lower or (len(t) > 4 and t.rstrip("s") in text_lower)
                        )
                        lex_score = matches / len(query_terms)
                    
                    combined_score = (0.5 * cos_score) + (0.5 * lex_score)
                    scored_candidates.append({
                        "chunk_id": chunk_id,
                        "transcript_id": transcript_id,
                        "content": content,
                        "episode_title": ep_title,
                        "guest": guest,
                        "source_url": source_url,
                        "similarity_score": round(combined_score, 4),
                        "snippet": content.strip(),
                    })
            except Exception as parse_err:
                logger.error("Failed to parse chunk embedding for %s: %s", chunk_id, parse_err)


        # Sort descending by similarity score
        scored_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_matches = scored_candidates[:top_k]

        logger.info(
            "Vector search query='%s' evaluated %d chunks -> found %d matches (top score=%.3f)",
            query[:40],
            len(rows),
            len(top_matches),
            top_matches[0]["similarity_score"] if top_matches else 0.0,
        )

        return [
            Citation(
                chunk_id=m["chunk_id"],
                transcript_id=m["transcript_id"],
                episode_title=m["episode_title"],
                guest=m["guest"],
                source_url=m["source_url"],
                snippet=m["snippet"],
                similarity_score=m["similarity_score"],
            )
            for m in top_matches
        ]

    async def get_chunk_count(self, db: AsyncSession) -> int:
        """Get total number of chunks stored."""
        result = await db.execute(select(func.count(TranscriptChunkModel.id)))
        return result.scalar_one() or 0

# Global vector store instance
vector_store = VectorStore()
