import os
from pathlib import Path

def list_files(start_path):
    print(f"Scanning {start_path}...")
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if "contacts" in file.lower() or file.lower().endswith(".vcf") or file.lower().endswith(".csv"):
                print(f"FOUND: {os.path.join(root, file)}")

if __name__ == "__main__":
    list_files("data/takeout/extracted")
