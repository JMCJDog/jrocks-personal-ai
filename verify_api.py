import requests
import json
import time

def test_chat(query):
    url = "http://localhost:8000/api/chat/"
    headers = {"Content-Type": "application/json"}
    payload = {
        "message": query,
        "session_id": "verify_rag_session_v1"
    }
    
    print(f"\nSending Query: '{query}'")
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        print("Response received:")
        print(json.dumps(data, indent=2))
        return data.get("response", "")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to localhost:8000. Is the server running?")
        return None
    except Exception as e:
        print(f"Error: {e}")
        if 'response' in locals():
            print(f"Status Code: {response.status_code}")
            print(f"Content: {response.text}")
        return None

if __name__ == "__main__":
    # Wait a bit to ensure potential server restarts are done? 
    # No, we assume server is running from previous session or we started it.
    # Actually, I haven't started the server in THIS session. 
    # I should verify if it's running.
    
    print("Testing API...")
    
    # 1. DOB Test
    dob_response = test_chat("What is my Date of Birth according to my health records?")
    
    # 2. Book Test
    book_response = test_chat("What is 'The Book'?")
