"""Vibe Coding FastAPI application.

This module defines the main FastAPI application with health check
and status endpoints.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Vibe Coding API",
    description="A starter local/edge AI project scaffolded for development and deployment.",
    version="0.0.1",
    contact={
        "name": "JMCJDOG",
        "email": "jared.cohen55@gmail.com",
    },
)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning welcome message.
    
    Returns:
        dict: Status and welcome message.
    """
    return {"status": "ok", "message": "Welcome to Vibe Coding"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Health status indicator.
    """
    return {"status": "healthy"}
