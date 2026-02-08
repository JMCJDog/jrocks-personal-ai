"""Re-Ranker - Scores document relevance using a Cross-Encoder.

Uses a high-precision model to filter and sort retrieved documents.
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class ReRanker:
    """Re-ranks retrieved documents using a Cross-Encoder model."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None
        
    @property
    def model(self):
        """Lazy-load the Cross-Encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading Cross-Encoder model: {self.model_name}...")
                self._model = CrossEncoder(self.model_name)
                logger.info("Cross-Encoder loaded successfully.")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model
        
    def rerank(self, query: str, docs: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Re-rank a list of document chunks based on relevance to the query.
        
        Args:
            query: The search query.
            docs: List of document dicts (must contain 'content' key).
            top_k: Number of results to return.
            
        Returns:
            List[Dict]: Top-k re-ranked documents with 'score' added.
        """
        if not docs:
            return []
            
        # Prepare pairs for the model: (query, doc_text)
        pairs = [(query, doc.get('content', '')) for doc in docs]
        
        try:
            # Get scores
            scores = self.model.predict(pairs)
            
            # Attach scores to docs
            for i, doc in enumerate(docs):
                doc['score'] = float(scores[i])
                doc['original_index'] = i
                
            # Sort by score (descending)
            ranked_docs = sorted(docs, key=lambda x: x['score'], reverse=True)
            
            # Return top_k
            return ranked_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            # Fallback: return original list sliced
            return docs[:top_k]
