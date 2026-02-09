import requests
import json

url = "http://localhost:8000/api/chat/"
payload = {
    "message": "Hello",
    "session_id": "debug-session",
    "include_context": False
}
headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
