import sys
from pathlib import Path

# Add project root
root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(root))

print(f"Project root: {root}")

try:
    print("Importing main...")
    from src.app.main import app
    print("Main imported.")
    
    print("Importing analytics router...")
    from src.app.api.analytics import router
    print("Router imported.")
    
    print("Checking routes...")
    found = False
    for route in app.routes:
        if route.path == "/api/analytics/heatmap":
            found = True
            print("✅ /api/analytics/heatmap found in app routes!")
            break
            
    if not found:
        print("❌ /api/analytics/heatmap NOT found in app routes.")
        for route in app.routes:
            print(f" - {route.path}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
