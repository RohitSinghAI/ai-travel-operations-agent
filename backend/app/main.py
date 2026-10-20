
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.app.api.routes import health, travel
from backend.app.api.routes import live_data


app = FastAPI(
    title="AI Travel Operations Agent",
    description=(
        "AI-powered travel planning using FastAPI, "
        "LangGraph, Groq, and MCP."
    ),
    version="1.0.0",
)


# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

# Load additional frontend origins from environment variables.
origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

# Allow local React/Vite development servers.
local_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

for origin in local_origins:
    if origin not in origins:
        origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# --------------------------------------------------
# API ROUTERS
# --------------------------------------------------

app.include_router(health.router)
app.include_router(travel.router)
app.include_router(live_data.router)


# --------------------------------------------------
# FRONTEND FILE CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_FILE = PROJECT_ROOT / "frontend" / "index.html"


# --------------------------------------------------
# ROOT ENDPOINT
# --------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "AI Travel Operations Agent API is running!",
        "docs": "/docs",
        "health": "/health",
    }


# --------------------------------------------------
# HEALTH CHECK ALIAS
# --------------------------------------------------

@app.get("/health-check", include_in_schema=False)
def health_check_alias():
    return {
        "status": "ok",
        "message": "AI Travel Operations Agent is running",
    }


# --------------------------------------------------
# FRONTEND ENDPOINT
# --------------------------------------------------

@app.get("/ui", include_in_schema=False)
def frontend():
    if not FRONTEND_FILE.exists():
        return {
            "error": "Frontend file not found.",
            "expected_path": str(FRONTEND_FILE),
        }

    return FileResponse(FRONTEND_FILE)
