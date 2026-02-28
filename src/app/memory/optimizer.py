"""Memory Optimizer - Background task to consolidate chat history.

Clustering and summarizing chat sessions into episodic memories.
"""

import logging
import uuid
from typing import List

from ..core.slm_engine import SLMEngine, ModelConfig
from ..ingest.embedding_pipeline import get_pipeline, DocumentChunk
from .manager import MemoryManager

logger = logging.getLogger(__name__)

class MemoryOptimizer:
    """Optimizes chat memory by extracting patterns and storing in vector DB."""
    
    def __init__(self):
        self.manager = MemoryManager()
        self.pipeline = get_pipeline()
        
        # Use a lightweight model for summarization if possible, or main model
        self.slm = SLMEngine(ModelConfig(temperature=0.3)) 
        
    def optimize_recent_sessions(self):
        """Process recent sessions and extract memories."""
        sessions = self.manager.get_unprocessed_sessions(limit=5)
        
        if not sessions:
            logger.info("No new sessions to optimize.")
            return
            
        logger.info(f"Optimizing {len(sessions)} sessions...")
        
        for session in sessions:
            try:
                self._process_session(session)
                self.manager.mark_session_processed(session['session_id'])
            except Exception as e:
                logger.error(f"Failed to optimize session {session['session_id']}: {e}")

    def _process_session(self, session: dict):
        """Extract memories from a single session."""
        session_id = session['session_id']
        history = self.manager.get_session_history(session_id)
        
        if not history:
            return
            
        # Format conversation
        conversation_text = ""
        for msg in history:
             import json
             meta = json.loads(msg['metadata']) if msg['metadata'] else {}
             prefix = ""
             if model := meta.get("model"):
                 prefix += f"[{model}] "
             if mode := meta.get("input_mode"):
                 prefix += f"(Mode: {mode}) "
             if files := meta.get("files"):
                 prefix += f"(Files: {', '.join([f['name'] for f in files])}) "
             if images_count := meta.get("images_count"):
                 prefix += f"(Images: {images_count}) "
             
             conversation_text += f"{msg['role'].upper()}: {prefix}{msg['content']}\n"
             
        # Prompt for extraction
        prompt = (
            f"Analyze the following conversation and extract key facts about the user, "
            f"their preferences, work details, or important relationships. "
            f"Focus on long-term relevant information.\n\n"
            f"Conversation:\n{conversation_text}\n\n"
            f"Return ONLY a bulleted list of 1-5 distinct facts. If nothing important, return 'NO_MEMORY'."
        )
        
        response = self.slm.generate(prompt)
        
        if "NO_MEMORY" in response:
            return
            
        # Parse bullets
        facts = [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]
        
        if not facts:
            # Fallback if model didn't use hyphens
            facts = [line.strip() for line in response.split('\n') if line.strip()]
            
        # Store facts
        chunks = []
        for fact in facts:
            if len(fact) < 10: continue
            
            chunk_id = str(uuid.uuid4())
            
            # Store in SQLite
            self.manager.add_episodic_memory(fact, embedding_id=chunk_id, source_session_id=session_id)
            
            # Create chunk for Chroma
            chunks.append(DocumentChunk(
                id=chunk_id,
                content=fact,
                source="episodic_memory",
                chunk_index=0,
                metadata={
                    "type": "memory",
                    "session_id": session_id,
                    "date": session['created_at']
                }
            ))
            
        if chunks:
            self.pipeline.add_chunks(chunks)
            logger.info(f"Extracted {len(chunks)} memories from session {session_id}")

    def check_and_run(self):
        """Run optimization only if 3 months have passed since last run."""
        import json
        from pathlib import Path
        from datetime import datetime, timedelta
        
        state_path = Path("data/memory_optimizer_state.json")
        last_run = None
        
        if state_path.exists():
            try:
                with open(state_path, "r") as f:
                    state = json.load(f)
                    if "last_run" in state:
                        last_run = datetime.fromisoformat(state["last_run"])
            except Exception as e:
                logger.error(f"Failed to read optimizer state: {e}")
        
        # Check interval (90 days)
        should_run = False
        if last_run is None:
            should_run = True
            logger.info("Memory Optimizer running for the first time.")
        else:
            days_since = (datetime.now() - last_run).days
            if days_since >= 90:
                should_run = True
                logger.info(f"Memory Optimizer: {days_since} days since last run. Starting optimization.")
            else:
                logger.info(f"Memory Optimizer: Skipped. Last run was {days_since} days ago (Interval: 90 days).")
        
        if should_run:
            self.optimize_recent_sessions()
            
            # Update state
            with open(state_path, "w") as f:
                json.dump({"last_run": datetime.now().isoformat()}, f)

def run_optimization():
    """Run the optimization process with interval check."""
    optimizer = MemoryOptimizer()
    optimizer.check_and_run()

if __name__ == "__main__":
    from ..core.logging_config import setup_logging
    setup_logging()
    run_optimization()
