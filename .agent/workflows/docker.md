---
description: Docker build and run workflow
---

# Docker Workflow

// turbo-all

1. Build Docker image:
```powershell
docker build -t vibe-coding:latest .
```

2. Run container:
```powershell
docker run -p 8000:8000 --env-file .env vibe-coding:latest
```

3. Check running containers:
```powershell
docker ps
```

4. Stop container (replace CONTAINER_ID):
```powershell
docker stop CONTAINER_ID
```
