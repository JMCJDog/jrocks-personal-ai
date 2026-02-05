"""Check setup for Feedback Loop."""
import sys
import os
from pathlib import Path

def check():
    print("Checking dependencies...")
    missing = []
    try:
        import google_auth_oauthlib
    except ImportError:
        missing.append("google-auth-oauthlib")
        
    try:
        import googleapiclient
    except ImportError:
        missing.append("google-api-python-client")
        
    if missing:
        print(f"MISSING_DEPS: {','.join(missing)}")
    else:
        print("DEPS_OK")
        
    # Check for credentials
    paths = [
        "credentials.json",
        "client_secret.json",
        "../credentials.json",
        "../client_secret.json"
    ]
    
    found = None
    for p in paths:
        if os.path.exists(p):
            found = p
            break
            
    if found:
        print(f"CREDS_FOUND: {found}")
    else:
        print("CREDS_MISSING")

if __name__ == "__main__":
    check()
