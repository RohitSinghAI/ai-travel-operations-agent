
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "AI Travel Operations Agent"
    APP_VERSION: str = "1.0.0"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    )


settings = Settings()
