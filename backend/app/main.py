from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from backend.app.schemas import TravelRequest
from backend.app.services.travel_service import create_travel_plan

app = FastAPI(
    title="AI Travel Operations Agent",
    description="AI-powered travel planning using LangGraph and Groq",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "message": "AI Travel Operations Agent API is running",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/travel/plan")
def create_plan(request: TravelRequest):
    try:
        return create_travel_plan(
            request.model_dump(mode="json")
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Detailed errors remain in the server logs
        print(f"Travel planning failed: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Unable to generate the travel plan. Check server logs.",
        ) from exc