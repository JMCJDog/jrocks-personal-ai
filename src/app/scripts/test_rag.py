import logging
import sys
from pathlib import Path

pass

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.rag.engine import RAGEngine
from src.app.core.persona import get_system_prompt

def main():
    logging.basicConfig(level=logging.INFO)
    print("--- RAG & Style Test ---")
    
    # 1. Test System Prompt (Style Injection)
    print("\n[1] Check System Prompt for Style Injection:")
    prompt = get_system_prompt()
    if "Dynamic Style Examples" in prompt:
        print("✅ Style Examples Section FOUND")
        # Print a snippet
        start = prompt.find("Dynamic Style Examples")
        print(prompt[start:start+200] + "...")
    else:
        print("ℹ️ No Style Examples found (Corpus might be empty, which is expected before ingestion)")

    # 2. Test RAG Engine
    print("\n[2] Testing RAG Engine Generation:")
    try:
        engine = RAGEngine()
        # Mocking or using real? 
        # If no ChromaDB, search might return empty.
        response = engine.generate_response("Who is JRock?", enhance_context=True)
        print(f"\nResponse:\n{response}")
    except Exception as e:
        print(f"❌ RAG Engine Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
