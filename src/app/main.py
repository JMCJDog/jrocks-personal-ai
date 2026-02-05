"""JRock's Personal AI - FastAPI application.

A comprehensive AI ecosystem that ingests multimedia and data
into a Small Language Model to build a digital consciousness
representing JROCK.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, ingest, agents, mcp, security

app = FastAPI(
    title="JRock's Personal AI",
    description="A digital consciousness ecosystem with chatbot, likeness generation, "
                "and content creation powered by local SLMs.",
    version="0.1.0",
    contact={
        "name": "JMCJDOG",
        "email": "jared.cohen55@gmail.com",
    },
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat.router, prefix="/api/chat")
app.include_router(ingest.router, prefix="/api/ingest")
app.include_router(agents.router)
app.include_router(mcp.router)
app.include_router(security.router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning welcome message.
    
    Returns:
        dict: Status and welcome message.
    """
    return {
        "status": "ok",
        "message": "Welcome to JRock's Personal AI",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Health status indicator.
    """
    return {"status": "healthy"}
