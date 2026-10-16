
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from backend.app.api.routes import health, travel

app = FastAPI(
    title="AI Travel Operations Agent",
    description=(
        "AI-powered travel planning using FastAPI, "
        "LangGraph, Groq, and MCP."
    ),
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(travel.router)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_FILE = PROJECT_ROOT / "frontend" / "index.html"


@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "AI Travel Operations Agent API is running!",
        "frontend": "/ui",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/ui", include_in_schema=False)
def frontend():
    if not FRONTEND_FILE.exists():
        return {
            "error": "Frontend file not found.",
            "expected_path": str(FRONTEND_FILE),
        }

    return FileResponse(FRONTEND_FILE)
