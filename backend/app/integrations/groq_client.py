
from groq import Groq

from backend.app.config import settings


def ask_llm(prompt: str) -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY missing. Add it to the project .env file."
        )

    client = Groq(api_key=settings.GROQ_API_KEY)

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI travel planning assistant. "
                    "Create practical travel plans, respect the "
                    "user's budget, and clearly label estimates. "
                    "Never claim that a booking has been confirmed."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content
    return content or "No travel plan was generated."
