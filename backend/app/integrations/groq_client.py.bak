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
                    "You are a practical AI travel planner. "
                    "Respect the supplied dates and authoritative "
                    "budget totals. Never invent prices, availability, "
                    "weather, or bookings. Clearly disclose missing "
                    "data and label estimates accurately. "
                    "Keep the itinerary concise and useful."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.3,
        max_tokens=1800,
    )

    content = response.choices[0].message.content

    if not content or not content.strip():
        return "No travel plan was generated."

    return content.strip()
