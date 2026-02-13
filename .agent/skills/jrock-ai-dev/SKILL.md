---
name: jrock-ai-dev
description: Development patterns and conventions for the JRock Personal AI codebase
---

# JRock Personal AI Development Skill

## Overview

JRock's Personal AI is a **personal AI consciousness, counter-surveillance, and data technology product** built with a local-first, privacy-focused architecture. JROCK is the reference implementation.

## Architecture

```
📥 DATA INGESTION          ⚙️ PROCESSING           🧠 AI CORE              📤 GENERATION
─────────────────────────────────────────────────────────────────────────────────────────
Documents/PDFs ──┐                                                        ┌─→ Chatbot
Images ──────────┼─→ Embedding → Vector Store ──→ RAG ──→ SLM ──→ Persona ┼─→ Avatar
Video/Audio ─────┤    Pipeline    (ChromaDB)     Engine    ↓     Engine   ├─→ Content
Text/Chats ──────┘                                     Consciousness        └─→ Creator
```

## Key Modules

| Module | Path | Purpose |
|--------|------|---------|
| **SLM Engine** | `src/app/core/slm_engine.py` | Ollama integration, model management |
| **Model Router** | `src/app/core/model_router.py` | Multi-provider routing (Ollama, Gemini, Claude, OpenAI) |
| **Model Registry** | `src/app/core/model_registry.py` | Tier-based model selection (FAST, BALANCED, SMART, CODING, VISION, LOCAL) |
| **Persona Engine** | `src/app/core/persona.py` | JROCK personality traits, writing style, system prompt generation |
| **Consciousness** | `src/app/core/consciousness.py` | LangGraph stateful workflows, emotional state, memory, self-reflection |
| **MCP Providers** | `src/app/mcp/providers.py` | Provider-agnostic LLM layer with tool integration |
| **Agent Coordinator** | `src/app/agents/coordinator.py` | Multi-agent orchestration with task planning and capability routing |
| **Agent Registry** | `src/app/agents/agent_registry.py` | Central agent discovery and registration |
| **Workflows** | `src/app/agents/workflow.py` | Sequential, parallel, and hierarchical workflow patterns |
| **Security** | `src/app/security/` | Access control, audit logging, monitoring, entity management |
| **Ingest** | `src/app/ingest/` | Document, media, embedding pipelines |
| **RAG** | `src/app/rag/` | Semantic retrieval engine |

## Technology Stack

- **SLM Runtime**: Ollama (local models: Llama 3.2, Mistral, Gemma)
- **Cloud LLMs**: Gemini 3 (via `google-genai`), Claude (via `anthropic`), OpenAI (via `openai`)
- **Orchestration**: LangGraph for stateful agent workflows
- **Vector DB**: ChromaDB (local) / Pinecone (cloud)
- **Embeddings**: sentence-transformers
- **Backend**: FastAPI + Uvicorn
- **Frontend**: Next.js + Vercel AI SDK
- **Storage**: Supabase

## Development Patterns

### Adding a New Agent

1. Create a new file in `src/app/agents/` inheriting from `BaseAgent`
2. Define capabilities using `AgentCapability` enum values
3. Register the agent in `agent_registry.py`
4. The `AgentCoordinator` will automatically discover and route to it based on capabilities

```python
from app.agents.base import BaseAgent, AgentResponse, AgentCapability

class MyAgent(BaseAgent):
    """Agent for specific task type."""
    
    def __init__(self):
        super().__init__(
            name="MyAgent",
            capabilities=[AgentCapability.RESEARCH],
        )
    
    async def execute(self, prompt: str, context: dict = None) -> AgentResponse:
        # Implementation
        return AgentResponse(content="...", agent_name=self.name)
```

### Adding a New LLM Provider

1. In `src/app/core/model_router.py`: Create a class inheriting `ModelProvider` with `generate()` and `is_available()`
2. In `src/app/mcp/providers.py`: Create a class inheriting `LLMProvider` with async `complete()` and `stream()`
3. Add the provider type to `ProviderType` enum
4. Register model names in `model_registry.py` tier definitions
5. Update `ModelRegistry.get_provider_for_model()` with name detection

### Adding New Data Sources

1. Create a provider in `src/app/ingest/providers/`
2. Follow the pattern of existing providers (e.g., `google_drive_provider.py`)
3. Register the provider in the ingestion pipeline

## Coding Standards

- **Docstrings**: Google style, REQUIRED for all modules and functions
- **Type Hints**: REQUIRED for all function arguments and returns
- **Testing**: pytest with minimum 80% coverage for new code
- **Package Management**: pip with `setup.cfg` (editable install)
- **Dependencies**: Listed in `Resources/requirements.txt`

## Key Design Constraints

1. **Local-First**: Privacy-focused. Prefer Ollama for on-device execution when possible.
2. **Product-First**: Build amazing features now; don't over-engineer for hypothetical problems.
3. **Modular Architecture**: Separate concerns for easy component swapping.
4. **Persona as Configuration**: JROCK's personality traits are configurable parameters, not hardcoded.
5. **Counter-Surveillance Alignment**: Never route sensitive data through external APIs unnecessarily.

## Common Commands

```powershell
# Run the app
make run

# Run tests
make test

# Install dependencies
make install

# Docker
make docker-build
make docker-run

# Ensure Ollama is running
ollama run llama3.2
```

## API

FastAPI at `http://localhost:8000`:
- `POST /api/chat` — Chat with JROCK's AI
- `POST /api/ingest` — Upload documents/media
- `POST /api/generate` — Generate content
- `GET /health` — Health check
- `GET /docs` — Swagger UI
