from typing import List, Dict, Optional
import logging

from ..ingest.embedding_pipeline import get_pipeline
from ..core.slm_engine import SLMEngine, ModelConfig

logger = logging.getLogger(__name__)

class RAGEngine:
    """Retrieval-Augmented Generation Engine with Advanced Features.
    
    Pipeline:
    1. Query Expansion (Optional)
    2. Multi-Source Retrieval (Memories + Docs)
    3. Deduplication
    4. Re-Ranking (Cross-Encoder)
    5. Context Construction
    6. LLM Generation
    """
    
    def __init__(self, model_config: Optional[ModelConfig] = None, slm_engine: Optional[SLMEngine] = None) -> None:
        """Initialize the RAG engine."""
        if slm_engine:
            self.slm_engine = slm_engine
        else:
            self.slm_engine = SLMEngine(model_config)
        self.embedding_pipeline = get_pipeline()
        
        # Advanced RAG components
        try:
            from .reranker import ReRanker
            from .query_expander import QueryExpander
            self.reranker = ReRanker()
            self.query_expander = QueryExpander()
            self.use_advanced_rag = True
            logger.info("Advanced RAG initialized (ReRanker + QueryExpander).")
        except ImportError:
            logger.warning("Advanced RAG components not found/installed. Falling back to simple RAG.")
            self.use_advanced_rag = False

    def generate_response(
        self, 
        user_query: str, 
        system_prompt: Optional[str] = None, 
        enhance_context: bool = True,
        images: Optional[list[bytes]] = None,
        context: Optional[dict] = None
    ) -> str:
        """Generate a response using RAG."""
        context_text = ""
        
        if enhance_context:
            try:
                candidates = {} # Map ID (or content hash) to doc dict to deduplicate
                
                # 1. Query Expansion (if enabled)
                queries = [user_query]
                if self.use_advanced_rag:
                    expanded = self.query_expander.expand_query(user_query, num_variations=2)
                    queries = expanded # Contains original + variations
                    
                # 2. Retrieval (Multi-query)
                for q in queries:
                    # Search Documents & Memories
                    results = self.embedding_pipeline.search(q, n_results=10)
                    for res in results:
                        # Deduplicate by ID if available, else content
                        doc_id = res.get('id') or hash(res.get('content', ''))
                        if doc_id not in candidates:
                            candidates[doc_id] = res

                # 3. Re-ranking
                candidate_list = list(candidates.values())
                
                if self.use_advanced_rag and candidate_list:
                    # Re-rank against ORIGINAL user query (not expanded ones)
                    ranked = self.reranker.rerank(user_query, candidate_list, top_k=5)
                else:
                    # Fallback or Simple RAG
                    ranked = candidate_list[:5]
                
                # 4. Context Construction
                context_chunks = []
                for res in ranked:
                    content = res.get('content', '').strip()
                    meta = res.get('metadata', {})
                    msg_type = meta.get('type', 'document')
                    score = res.get('score', 0.0)
                    
                    if msg_type == 'memory':
                        date = meta.get('date', 'Unknown')
                        context_chunks.append(f"[MEMORY] ({date}) [Score: {score:.2f}]: {content}")
                    else:
                        source = meta.get('source', 'unknown')
                        date = meta.get('date_str', '')
                        citation = f"Source: {source} ({date})" if date else f"Source: {source}"
                        context_chunks.append(f"[{citation}] [Score: {score:.2f}]\n{content}")
                        
                if context_chunks:
                    context_text = "\n\n".join(context_chunks)
                    logger.info(f"RAG: Used {len(queries)} queries. Retrieved {len(candidates)} candidates. Selected {len(ranked)} contexts.")
                else:
                    logger.info("No relevant context found.")
                    
            except Exception as e:
                logger.error(f"RAG retrieval failed: {e}")
                import traceback
                traceback.print_exc()
        
        # 5. Construct Augmented Prompt
        final_prompt = user_query
        
        if context_text:
            final_prompt = (
                f"The following context contains retrieved MEMORIES from your own life and writings. "
                f"Use these details to answer the User's question as Jared (First Person).\n"
                f"Do not refer to the context as 'context' or 'documents'. Treat it as your own knowledge.\n\n"
                f"--- YOUR MEMORIES ---\n{context_text}\n----------------\n\n"
                f"User Question: {user_query}"
            )
            
        # 6. Generate
        # Note: slm_engine.generate handles system_prompt via set_system_prompt if needed, 
        # or we update it to accept it. Here we pass images.
        if system_prompt:
            self.slm_engine.set_system_prompt(system_prompt)
            
        return self.slm_engine.generate(final_prompt, images=images)
