"""Document embedding pipeline using sentence-transformers for cost-efficient semantic search."""

import hashlib
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import ray
from loguru import logger
from sentence_transformers import SentenceTransformer

from src.core.config import get_settings


class EmbeddingPipeline:
    """
    Embedding pipeline with progressive enhancement strategy:
    1. Start with sentence-transformers (free, local)
    2. Migrate to OpenAI when needed (better quality, costs)
    3. Support for custom fine-tuned models
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding pipeline.
        
        Models by dimension/quality trade-off:
        - all-MiniLM-L6-v2: 384 dim, fast, good for development
        - all-mpnet-base-v2: 768 dim, better quality
        - all-distilroberta-v1: 768 dim, robust to noise
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Initialized {model_name} with {self.dimension} dimensions")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text."""
        return self.model.encode(text, convert_to_numpy=True)
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Embed multiple texts efficiently."""
        return self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100
        )
    
    def embed_with_cache(self, text: str, cache: Dict[str, np.ndarray]) -> np.ndarray:
        """Embed with caching to avoid recomputation."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash not in cache:
            cache[text_hash] = self.embed_text(text)
        
        return cache[text_hash]


@ray.remote
class DistributedEmbedder:
    """Ray actor for distributed embedding generation."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.pipeline = EmbeddingPipeline(model_name)
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process documents and add embeddings."""
        results = []
        
        for doc in documents:
            try:
                # Embed full document
                if "content" in doc:
                    doc["embedding"] = self.pipeline.embed_text(doc["content"]).tolist()
                
                # Embed chunks if present
                if "chunks" in doc:
                    chunk_embeddings = []
                    chunk_texts = [chunk["text"] for chunk in doc["chunks"]]
                    
                    if chunk_texts:
                        embeddings = self.pipeline.embed_batch(chunk_texts)
                        
                        for i, chunk in enumerate(doc["chunks"]):
                            chunk["embedding"] = embeddings[i].tolist()
                            chunk_embeddings.append(embeddings[i])
                    
                    # Create document embedding as mean of chunks
                    if not doc.get("embedding") and chunk_embeddings:
                        doc["embedding"] = np.mean(chunk_embeddings, axis=0).tolist()
                
                doc["embedding_model"] = self.pipeline.model_name
                doc["embedding_dimension"] = self.pipeline.dimension
                results.append(doc)
                
            except Exception as e:
                logger.error(f"Error embedding document: {e}")
                doc["embedding_error"] = str(e)
                results.append(doc)
        
        return results


class SemanticSearch:
    """Semantic search using embeddings."""
    
    def __init__(self, embedding_pipeline: EmbeddingPipeline):
        self.embedding_pipeline = embedding_pipeline
    
    def search(
        self,
        query: str,
        embeddings: np.ndarray,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Search documents using cosine similarity.
        
        Returns:
            List of (similarity_score, document) tuples
        """
        # Embed query
        query_embedding = self.embedding_pipeline.embed_text(query)
        
        # Calculate cosine similarities
        similarities = self._cosine_similarity(query_embedding, embeddings)
        
        # Get top-k results
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            score = similarities[idx]
            if score >= similarity_threshold:
                results.append((score, documents[idx]))
        
        return results
    
    @staticmethod
    def _cosine_similarity(query_embedding: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between query and all embeddings."""
        # Normalize query
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        embeddings_norm = embeddings / norms
        
        # Calculate cosine similarity
        similarities = np.dot(embeddings_norm, query_norm)
        
        return similarities
    
    def rerank_results(
        self,
        query: str,
        initial_results: List[Dict[str, Any]],
        rerank_top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results using cross-encoder for better accuracy.
        This is more expensive but more accurate than bi-encoder embeddings.
        """
        # For now, return as-is. In production, would use cross-encoder model
        # from sentence_transformers import CrossEncoder
        # model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        return initial_results[:rerank_top_k]


class HybridSearch:
    """
    Hybrid search combining semantic and keyword search.
    Better for production as it handles both concept and exact matches.
    """
    
    def __init__(self, semantic_search: SemanticSearch):
        self.semantic_search = semantic_search
    
    def search(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        embeddings: np.ndarray,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        top_k: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Combine semantic and keyword search.
        
        Args:
            semantic_weight: Weight for semantic similarity (0-1)
            keyword_weight: Weight for keyword matching (0-1)
        """
        # Semantic search
        semantic_results = self.semantic_search.search(
            query, embeddings, documents, top_k=top_k * 2
        )
        
        # Keyword search (BM25-like scoring)
        keyword_scores = self._keyword_score(query, documents)
        
        # Combine scores
        combined_scores = {}
        
        for score, doc in semantic_results:
            doc_id = id(doc)  # Use object id as key
            combined_scores[doc_id] = {
                "doc": doc,
                "score": score * semantic_weight
            }
        
        for i, doc in enumerate(documents):
            doc_id = id(doc)
            if doc_id in combined_scores:
                combined_scores[doc_id]["score"] += keyword_scores[i] * keyword_weight
            else:
                combined_scores[doc_id] = {
                    "doc": doc,
                    "score": keyword_scores[i] * keyword_weight
                }
        
        # Sort by combined score
        results = sorted(
            [(v["score"], v["doc"]) for v in combined_scores.values()],
            key=lambda x: x[0],
            reverse=True
        )
        
        return results[:top_k]
    
    def _keyword_score(self, query: str, documents: List[Dict[str, Any]]) -> List[float]:
        """Simple keyword scoring (BM25-inspired)."""
        query_terms = query.lower().split()
        scores = []
        
        for doc in documents:
            text = doc.get("content", "").lower()
            if not text:
                scores.append(0)
                continue
            
            # Term frequency
            score = 0
            for term in query_terms:
                tf = text.count(term)
                # Simple TF-IDF-like scoring
                score += tf / (1 + tf)  # Saturation function
            
            scores.append(score / len(query_terms) if query_terms else 0)
        
        # Normalize scores
        max_score = max(scores) if scores else 1
        if max_score > 0:
            scores = [s / max_score for s in scores]
        
        return scores


def migrate_to_openai_embeddings(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Migration function to upgrade from sentence-transformers to OpenAI embeddings.
    Use when ready for production with budget for API costs.
    """
    # Implementation would use OpenAI API
    # from openai import OpenAI
    # client = OpenAI()
    # for doc in documents:
    #     response = client.embeddings.create(
    #         model="text-embedding-3-small",
    #         input=doc["content"]
    #     )
    #     doc["embedding"] = response.data[0].embedding
    pass