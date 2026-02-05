# JRock's Personal AI

![CI](https://github.com/JMCJDOG/jrocks-personal-ai/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🧠 **A comprehensive AI ecosystem** that ingests multimedia, files, and various data types into a Small Language Model (SLM) to build a digital consciousness representing JROCK, complete with chatbot, likeness generation, and interactive capabilities.

## ✨ Features

- **Personal SLM Integration** - Local AI models via Ollama (Llama 3, Mistral, Phi-3)
- **Data Ingestion Pipeline** - Documents, images, video, and text processing
- **RAG-Powered Knowledge Base** - Semantic search over personal artifacts
- **Digital Consciousness** - Stateful persona with LangGraph orchestration
- **Chatbot Interface** - Natural conversations with JROCK's AI
- **Content Generation** - Blog posts, social media, and creative writing
- **Likeness Generation** - Avatar and image generation (Stable Diffusion)

## 🏗️ Architecture

```
src/app/
├── core/           # SLM engine, persona, consciousness state
├── ingest/         # Document, media, embedding pipelines
├── rag/            # Retrieval and knowledge graph
├── generation/     # Chatbot, avatar, content creation
├── api/            # FastAPI routes
└── models/         # Pydantic schemas
```

## 🚀 Quickstart

1. **Create and activate virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   make install
   ```

3. **Ensure Ollama is running with a model:**
   ```powershell
   ollama run llama3.2
   ```

4. **Run the app:**
   ```powershell
   make run
   ```

5. **Access the API:** http://localhost:8000/docs

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root endpoint with welcome message |
| GET | `/health` | Health check for monitoring |
| POST | `/api/chat` | Chat with JROCK's AI |
| POST | `/api/ingest` | Upload documents/media |
| POST | `/api/generate` | Generate content |
| GET | `/docs` | Interactive Swagger UI |

## 🧪 Testing

```powershell
make test
```

## 🐳 Docker

```powershell
make docker-build
make docker-run
```

## 📄 License

MIT - See [LICENSE](LICENSE) for details.
