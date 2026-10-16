
from fastapi import FastAPI
from backend.app.api.routes import health, travel

app = FastAPI(
    title="AI Travel Operations Agent",
    description="AI travel planning with FastAPI, LangGraph and Groq",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(travel.router)


@app.get("/")
def root():
    return {
        "message": "AI Travel Operations Agent API is running!"
    }
