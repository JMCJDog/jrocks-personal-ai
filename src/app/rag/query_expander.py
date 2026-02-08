"""Query Expander - Generates alternative search queries using SLM.

Helps retrieve documents that use different terminology than the user's query.
"""

import logging
from typing import List

from ..core.slm_engine import SLMEngine, ModelConfig

logger = logging.getLogger(__name__)

class QueryExpander:
    """Expands user queries into multiple semantic variations."""
    
    def __init__(self):
        # Use a higher temperature for creativity
        self.slm = SLMEngine(ModelConfig(temperature=0.7))
        
    def expand_query(self, query: str, num_variations: int = 3) -> List[str]:
        """Generate alternative search queries.
        
        Args:
            query: The original user query.
            num_variations: Number of alternatives to generate.
            
        Returns:
            List[str]: Original query + generated variations.
        """
        prompt = (
            f"You are an AI search assistant. Generate {num_variations} alternative search queries "
            f"for the following user question. Focus on synonyms, related concepts, "
            f"and technical terms that might appear in documents.\n\n"
            f"User Question: \"{query}\"\n\n"
            f"Return ONLY a numbered list of queries. Do not add any explanation."
        )
        
        try:
            response = self.slm.generate(prompt)
            lines = response.strip().split('\n')
            
            variations = []
            for line in lines:
                # specific clean up for "1. query" format
                clean = line.lstrip('0123456789.- ').strip()
                if clean:
                    variations.append(clean)
            
            # Ensure we don't have duplicates or empty strings
            unique_vars = list(dict.fromkeys([query] + variations))
            
            logger.info(f"Expanded '{query}' into {len(unique_vars)} queries: {unique_vars}")
            return unique_vars
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [query]
