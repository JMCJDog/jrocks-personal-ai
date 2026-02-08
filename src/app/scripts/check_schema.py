import sqlite3
import os

def check_schema():
    db_path = "data/drive_index.db"
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(drive_files)")
    columns = cursor.fetchall()
    for col in columns:
        print(col)

if __name__ == "__main__":
    check_schema()
