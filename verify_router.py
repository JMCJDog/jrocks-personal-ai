
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from app.core.model_router import ModelRouter
from app.core.surveillance import default_surveillance

def test_router():
    print("\n--- Testing Model Router ---")
    router = ModelRouter()
    
    # Test local provider (should always work if Ollama is running, assuming llama3.2 is pulled)
    # If not running, it might fail, but we'll see the error.
    try:
        provider = router.get_provider("llama3.2")
        print(f"Llama Provider: {provider}")
        if provider.is_available():
            print("Llama is available.")
        else:
            print("Llama is NOT available (Ollama might be down).")
    except Exception as e:
        print(f"Llama Provider Error: {e}")

    # Test Gemini Provider (requires key)
    try:
        gemini = router.get_provider("gemini-1.5-flash")
        print(f"Gemini Provider: {gemini}")
        if gemini.is_available():
            print("Gemini is available (Key found).")
        else:
            print("Gemini is NOT available (Key missing).")
    except Exception as e:
        print(f"Gemini Provider Error: {e}")

def test_surveillance():
    print("\n--- Testing Surveillance System ---")
    
    # Simulate a "clean" log
    clean_log = "User jared logged in from 192.168.1.5. Accessed dashboard. Viewed 2 files."
    print(f"Scanning Clean Log: '{clean_log}'")
    result_clean = default_surveillance.scan(clean_log)
    print(f"Result: {result_clean}")

    # Simulate a "suspicious" log
    suspicious_log = "Multiple failed login attempts from IP 45.2.1.9 (Russia). Tried admin/root/test. SQL injection attempt detected in query params."
    print(f"\nScanning Suspicious Log: '{suspicious_log}'")
    result_suspicious = default_surveillance.scan(suspicious_log)
    print(f"Result: {result_suspicious}")

if __name__ == "__main__":
    test_router()
    test_surveillance()
