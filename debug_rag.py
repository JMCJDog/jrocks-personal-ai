
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app.rag.engine import RAGEngine
from src.app.core.persona import default_persona

async def test_retrieval():
    print("Initializing RAG Engine...")
    # Initialize basic SLM engine for RAG
    rag = RAGEngine()
    
    queries = [
        "What is my Date of Birth according to my health records?",
        "What is 'The Book'?"
    ]
    
    for query in queries:
        print(f"\nQuerying: '{query}'")
    
        # 1. Test Retrieval Direct
        print("\n--- Direct Retrieval Check ---")
        results = rag.embedding_pipeline.search(query, n_results=5)
        
        if not results:
            print("NO DOCUMENTS FOUND IN DB.")
        else:
            print(f"Found {len(results)} results.")
            for i, res in enumerate(results):
                content = res.get('content', '')
                metadata = res.get('metadata', {})
                print(f"\nResult {i+1} (Source: {metadata.get('source', 'unknown')}):")
                # Handle potential encoding issues in print
                try:
                    print(f"Content: {content[:300]}...") 
                except UnicodeEncodeError:
                    print(f"Content: {content[:300].encode('utf-8', errors='replace')}...")
                
        # 2. Test Full Generation
        print("\n--- Full Generation Check ---")
        real_system_prompt = default_persona.generate_system_prompt()
        print(f"System Prompt Length: {len(real_system_prompt)}")
        response = rag.generate_response(query, system_prompt=real_system_prompt)
        print(f"\nResponse:\n{response}")

if __name__ == "__main__":
    asyncio.run(test_retrieval())
