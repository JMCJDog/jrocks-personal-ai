# Agent Authority Context: JRock's Personal AI

## 1. Project Identity & Core Vision

**Identity**: `jrocks-personal-ai` is a comprehensive AI ecosystem for building digital consciousness - with JROCK as the reference implementation.

### 🎯 End Objectives

1. **Turnkey Framework**: Deliver a complete, production-ready solution that anyone can deploy to create their own AI consciousness
2. **Scalable Architecture**: Support multiple users with isolated persona stores, configurable models, and cloud-native deployment options  
3. **Reference Implementation**: JROCK serves as the proof-of-concept, demonstrating the full capability of the platform

### Primary Capabilities
- Ingest multimedia, files, and personal data into a Small Language Model (SLM)
- Learn personality, writing style, and knowledge domains from source material
- Generate content, conversations, and potentially visual likeness
- Evolve over time through continuous learning and memory synthesis

> **The Vision**: Not just an AI for JROCK, but a **productizable platform** where anyone can create an AI that truly "knows" them and represents them authentically.

---

## 2. Architecture Overview

```
📥 DATA INGESTION          ⚙️ PROCESSING           🧠 AI CORE              📤 GENERATION
─────────────────────────────────────────────────────────────────────────────────────────
Documents/PDFs ──┐                                                        ┌─→ Chatbot
Images ──────────┼─→ Embedding → Vector Store ──→ RAG ──→ SLM ──→ Persona ┼─→ Avatar
Video/Audio ─────┤    Pipeline    (ChromaDB)     Engine    ↓     Engine   ├─→ Content
Text/Chats ──────┘                                     Consciousness        └─→ Creator
```

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **SLM Engine** | `src/app/core/slm_engine.py` | Ollama integration, model management, prompt templates |
| **Persona Engine** | `src/app/core/persona.py` | JROCK personality, writing style, tone calibration |
| **Consciousness** | `src/app/core/consciousness.py` | LangGraph stateful workflows, long-term memory, self-reflection |
| **Ingest Pipeline** | `src/app/ingest/` | Document, media, and embedding processing |
| **Google Drive** | `src/app/ingest/providers/google_drive_provider.py` | Index "The Book", docs, and sheets |
| **Media Nodes** | `src/app/ingest/` (vision/location) | Face recognition and location history analysis |
| **Chat History Sync** | `src/app/ingest/providers/` + `sync/` | Multi-provider chat import from OpenAI, Anthropic, Google, Ollama |
| **Knowledge Graph** | `src/app/knowledge/extractors.py` | Extract ideologies, business ideas, and persona from docs |
| **RAG System** | `src/app/rag/` | Semantic retrieval, knowledge graph |
| **Generation** | `src/app/generation/` | Chatbot, avatar, content creation, voice cloning |

---

## 3. Technology Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| **SLM** | Ollama | Run local language models |
| **Models** | Llama 3 / Mistral / Phi-3 | Text generation |
| **Orchestration** | LangGraph | Stateful agent workflows |
| **Vector DB** | ChromaDB (local) / Pinecone (cloud) | Semantic search |
| **Embeddings** | sentence-transformers | Text embeddings |
| **Backend** | FastAPI | REST API |
| **Storage** | Supabase | Metadata & artifacts |
| **Image Gen** | Stable Diffusion (optional) | Avatar generation |
| **Frontend** | Next.js + Vercel AI SDK | Chat interface |

---

## 4. Structural Logic

| Path | Purpose | Agent Action |
|------|---------|--------------|
| `src/app/core/` | AI engine, persona, consciousness | **Core intelligence** - edit with care |
| `src/app/ingest/` | Data processing pipelines | Add new data source handlers here |
| `src/app/rag/` | Retrieval and knowledge graph | Semantic search improvements |
| `src/app/generation/` | Output generation modules | Chatbot, avatar, content |
| `src/app/api/routes/` | FastAPI endpoints | New API functionality |
| `src/app/models/` | Pydantic schemas | Data validation |
| `tests/` | Pytest suite | Add tests for new features |
| `Resources/` | Dependencies | `requirements.txt` management |

---

## 5. Development Standards

### Coding Standards
- **Docstrings**: REQUIRED for all modules and functions (Google style)
- **Type Hints**: REQUIRED for all function arguments and returns
- **Package Management**: `pip` with `setup.cfg` (editable install)
- **Testing**: `pytest` with minimum 80% coverage for new code

### Development Cycle
1. **Plan** with `/plan` for non-trivial features
2. **Implement** in `src/app/`
3. **Test** with `/test` workflow
4. **Verify** with `/verify` workflow
5. **Commit** with `/git-push`

---

## 6. Implementation Phases

| Phase | Deliverables | Status |
|-------|--------------|--------|
| **1** | Project scaffold, scalable SLM integration | ✅ Complete |
| **2** | Data ingestion pipeline, vector store | 🔄 In Progress |
| **3** | RAG system, chatbot interface | ⏳ Pending |
| **4** | Persona fine-tuning, content generation | ⏳ Pending |
| **5** | Frontend, likeness generation | ⏳ Pending |
| **6** | Continuous training and refinement | ⏳ Ongoing |

---

## 7. Key Design Decisions

1. **Local-First**: Privacy-focused with Ollama for on-device SLM execution
2. **Modular Architecture**: Separate concerns for easy component swapping
3. **LangGraph for State**: Complex multi-step conversations with memory
4. **Hybrid Storage**: Local ChromaDB for development, Pinecone option for production
5. **Persona as Configuration**: JROCK's personality traits are configurable parameters

---

## 8. Agent Tips

- **Consciousness Module**: The `consciousness.py` is the heart of the system - it maintains JROCK's "self" across interactions
- **Testing SLM**: Ensure Ollama is running with `ollama run llama3.2` before testing
- **Embedding Size**: Match embedding dimensions with your chosen model (typically 384, 768, or 1536)
- **Context Windows**: Be mindful of token limits when building RAG context
- **Prefer Workflows**: Use `/test`, `/dev`, `/verify` for consistent execution
