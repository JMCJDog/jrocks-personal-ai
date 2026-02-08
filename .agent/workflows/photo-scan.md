---
description: Scan local photos for facial recognition and add to AI memory
---

# Photo Scan Workflow

1. Execute the photo scan batch script. 
   **Note**: You must replace `PATH_TO_PHOTOS` with the actual directory path provided by the user (e.g., download folder or export location).

```powershell
.\run_photo_scan.bat "PATH_TO_PHOTOS" --copy
```

2. If the user wants to copy matches to a specific location (optional):

```powershell
.\run_photo_scan.bat "PATH_TO_PHOTOS" --output "TARGET_OUTPUT_DIR"
```
