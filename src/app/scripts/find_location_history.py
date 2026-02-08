import sqlite3
import os

def find_files():
    db_path = "data/drive_index.db"
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Search for likely candidates
    patterns = [
        '%Location History%',
        '%Records.json%',
        '%Semantic Location History%',
        '%timeline%'
    ]
    
    for pattern in patterns:
        print(f"Searching for {pattern}...")
        cursor.execute("SELECT name, id, path FROM drive_files WHERE name LIKE ?", (pattern,))
        results = cursor.fetchall()
        for row in results:
            print(f"Found: {row}")

if __name__ == "__main__":
    find_files()
