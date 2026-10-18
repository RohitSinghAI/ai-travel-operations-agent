
from typing import Any


def _extract_activities(activity_data: Any) -> list[dict[str, Any]]:
    """Normalize activity data returned by MCP tools or other providers."""

    if isinstance(activity_data, list):
        return [item for item in activity_data if isinstance(item, dict)]

    if not isinstance(activity_data, dict):
        return []

    # Handle MCP/provider response wrappers.
    for key in ("activities", "options", "result", "data"):
        value = activity_data.get(key)

        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

        if isinstance(value, dict):
            nested = _extract_activities(value)
            if nested:
                return nested

    # A single activity object may itself be supplied.
    if any(key in activity_data for key in ("name", "title", "activity")):
        return [activity_data]

    return []


def run_activity_agent(
    activity_data: Any,
    preferences: list[str] | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """
    Process available tourist activities and optionally rank them
    according to the traveller's preferences.

    This function processes supplied data; it does not fetch live data.
    """

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    activities = _extract_activities(activity_data)

    preference_terms = [
        term.strip().lower()
        for term in (preferences or [])
        if isinstance(term, str) and term.strip()
    ]

    results = []

    for activity in activities:
        name = str(
            activity.get("name")
            or activity.get("title")
            or activity.get("activity")
            or "Unnamed activity"
        ).strip()

        description = str(activity.get("description") or "").strip()
        category = str(activity.get("category") or "general").strip()
        searchable_text = f"{name} {description} {category}".lower()

        matched_preferences = [
            term for term in preference_terms
            if term in searchable_text
        ]

        results.append({
            "name": name,
            "description": description,
            "category": category,
            "location": activity.get("location"),
            "price": activity.get("price"),
            "currency": activity.get("currency", "INR"),
            "duration": activity.get("duration"),
            "matched_preferences": matched_preferences,
            "is_live": activity.get("is_live", False),
            "verified": activity.get("verified", False),
        })

    # Activities matching more preferences appear first.
    results.sort(
        key=lambda item: len(item["matched_preferences"]),
        reverse=True,
    )

    selected = results[:max_results]

    return {
        "status": "success" if selected else "unavailable",
        "count": len(selected),
        "preferences": preference_terms,
        "activities": selected,
        "message": (
            "Activities processed and ranked by preference."
            if selected
            else "No usable activities were returned by the data source."
        ),
    }
