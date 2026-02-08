
import sqlite3
import random
import os

def seed_locations():
    db_path = "data/locations.db"
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if not exists with simple schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lng REAL,
            timestamp TEXT
        )
    """)
    
    # Clear existing if any (optional, but good for clean slate test)
    # cursor.execute("DELETE FROM locations")
    
    print("Seeding locations...")
    
    locations = []
    
    # Random US points (approx bounding box)
    # Lat: 25 to 49, Lng: -125 to -67
    for _ in range(500):
        lat = random.uniform(25, 49)
        lng = random.uniform(-125, -67)
        locations.append((lat, lng, "2023-01-01T12:00:00"))
        
    # Clusters
    # NYC: 40.7128, -74.0060 (dense)
    for _ in range(200):
        lat = random.normalvariate(40.7128, 0.1)
        lng = random.normalvariate(-74.0060, 0.1)
        locations.append((lat, lng, "2023-01-01T12:00:00"))
        
    # SF: 37.7749, -122.4194
    for _ in range(150):
        lat = random.normalvariate(37.7749, 0.05)
        lng = random.normalvariate(-122.4194, 0.05)
        locations.append((lat, lng, "2023-01-02T12:00:00"))

    cursor.executemany("INSERT INTO locations (lat, lng, timestamp) VALUES (?, ?, ?)", locations)
    
    conn.commit()
    print(f"Added {len(locations)} location points.")
    conn.close()

if __name__ == "__main__":
    seed_locations()
