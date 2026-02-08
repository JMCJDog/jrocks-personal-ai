---
description: Index Google Drive metadata for search capability
---

# Google Drive Indexing Workflow

1.  Run the indexing script to crawl Drive and populate the metadata database.
    **Note**: If this is the first run, a browser window will open for you to log in to Google.

```bash
python src/app/scripts/index_drive.py
```

2.  (Optional) Verify the index size:
    
```bash
python -c "from src.app.ingest.drive_metadata_db import DriveMetadataDB; print(DriveMetadataDB().get_stats())"
```
