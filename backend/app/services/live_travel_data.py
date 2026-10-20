from __future__ import annotations

from typing import Any
import asyncio
import re

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
WIKIPEDIA_URL = "https://en.wikipedia.org/w/api.php"

# Public Overpass instances can be overloaded. Try more than one.
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)

TIMEOUT = httpx.Timeout(20.0, connect=8.0)
USER_AGENT = "AITravelOperationsAgent/1.0 (travel discovery application)"

# Conservative title filters for obvious event/news articles returned by Wikipedia.
EXCLUDED_TITLE_PATTERNS = (
    r"\battack\b",
    r"\bbombing\b",
    r"\bmassacre\b",
    r"\bbattle of\b",
    r"\bwar of\b",
    r"\bterrorist\b",
    r"\bexplosion\b",
    r"\bincident\b",
    r"\bdisaster\b",
    r"\belection\b",
    r"\bcontroversy\b",
    r"\bscandal\b",
    r"\bdeath of\b",
    r"\b20[0-9]{2}\b",
)


class LiveDataError(Exception):
    """Raised when a live travel-data provider fails."""


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """GET JSON and convert provider/JSON failures into a clear error."""
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise LiveDataError("The data provider returned an unexpected response.")
        return data
    except httpx.HTTPError as exc:
        raise LiveDataError(
            f"Could not reach live data provider ({type(exc).__name__})."
        ) from exc
    except ValueError as exc:
        raise LiveDataError("The data provider returned invalid JSON.") from exc


async def geocode_city(city: str) -> dict[str, Any]:
    """
    Search a complete location query (for example, 'Hyderabad, Telangana, India').

    Nominatim is tried first because it can use the whole query. Open-Meteo is
    a fallback. The resolver below validates country/region hints before use.
    """
    if not isinstance(city, str) or not city.strip():
        raise ValueError("A valid location is required.")

    query = city.strip()
    parts = [part.strip() for part in query.split(",") if part.strip()]
    if not parts:
        raise ValueError("A valid location is required.")

    headers = {"User-Agent": USER_AGENT}
    errors: list[str] = []

    # 1) Search the full query, not only the first word/city.
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            headers=headers,
        ) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "limit": 10,
                },
            )
            response.raise_for_status()
            payload = response.json()

        results: list[dict[str, Any]] = []
        for item in payload if isinstance(payload, list) else []:
            address = item.get("address") or {}
            display_name = str(item.get("display_name") or "")
            name = (
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("municipality")
                or item.get("name")
                or (parts[0] if parts[0].casefold() in display_name.casefold() else None)
            )
            country = address.get("country")
            if not name or not country:
                continue

            try:
                latitude = float(item["lat"])
                longitude = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue

            results.append({
                "name": str(name),
                "country": str(country),
                "country_code": str(address.get("country_code") or "").upper(),
                "admin1": (
                    address.get("state")
                    or address.get("province")
                    or address.get("region")
                ),
                "admin2": (
                    address.get("state_district")
                    or address.get("county")
                    or address.get("municipality")
                ),
                "latitude": latitude,
                "longitude": longitude,
                "timezone": None,
                "population": None,
                "importance": item.get("importance", 0),
                "place_type": item.get("type") or item.get("addresstype"),
                "provider_display_name": display_name,
                "provider": "OpenStreetMap Nominatim",
            })

        if results:
            return {
                "query": query,
                "provider": "OpenStreetMap Nominatim",
                "status": "live",
                "results": results,
            }

    except (httpx.HTTPError, ValueError) as exc:
        errors.append(f"Nominatim: {type(exc).__name__}")

    # 2) Fallback to Open-Meteo. Do not pass full country names to its
    # countryCode filter; search the city name and validate hints afterwards.
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            headers=headers,
        ) as client:
            response = await client.get(
                GEOCODING_URL,
                params={
                    "name": parts[0],
                    "count": 10,
                    "language": "en",
                    "format": "json",
                },
            )
            response.raise_for_status()
            payload = response.json()

        return {
            "query": query,
            "provider": "Open-Meteo Geocoding",
            "status": "live",
            "results": payload.get("results", []),
            "fallback_note": (
                "Nominatim returned no usable results or was unavailable."
            ),
        }

    except (httpx.HTTPError, ValueError) as exc:
        errors.append(f"Open-Meteo: {type(exc).__name__}")
        raise LiveDataError(
            "Could not resolve the location. " + "; ".join(errors)
        ) from exc


def _hint_matches(item: dict[str, Any], hint: str) -> bool:
    """Match a supplied region/country hint against known location fields."""
    wanted = hint.strip().casefold()
    if not wanted:
        return True

    fields = (
        "admin1", "admin2", "admin3", "country", "country_code",
        "state", "region", "county", "province",
    )
    for field in fields:
        value = str(item.get(field) or "").strip().casefold()
        if value == wanted:
            return True

    # Country codes are commonly supplied as IN, FR, US, etc.
    if len(wanted) == 2 and str(item.get("country_code") or "").casefold() == wanted:
        return True

    return False


async def _resolve_one_city(city: str) -> dict[str, Any]:
    """Resolve the requested location without silently choosing another country."""
    if not isinstance(city, str) or not city.strip():
        raise ValueError("A valid destination is required.")

    parts = [part.strip() for part in city.split(",") if part.strip()]
    if not parts:
        raise ValueError("A valid destination is required.")

    requested_name = parts[0]
    result = await geocode_city(city)
    matches = result.get("results") or []

    if not matches:
        raise ValueError(
            f"No location found for '{city}'. Add the region and country, "
            "or check the spelling."
        )

    # Exact-name matching avoids accepting "Genoa" for "Goa".
    exact = [
        item for item in matches
        if str(item.get("name") or "").strip().casefold()
        == requested_name.casefold()
    ]

    # Some geocoders use display names / administrative units rather than
    # a simple city name. Permit a fallback only if the provider has a
    # candidate whose display name begins with the requested location.
    if not exact and result.get("provider") == "OpenStreetMap Nominatim":
        exact = [
            item for item in matches
            if str(item.get("provider_display_name") or "")
            .split(",", 1)[0].strip().casefold() == requested_name.casefold()
        ]

    if not exact:
        raise ValueError(
            f"No exact location match found for '{requested_name}'. "
            "Please check the spelling and specify a country."
        )

    # Filter against every supplied hint in order. For example:
    # Hyderabad, Telangana, India -> match Telangana AND India.
    for hint in parts[1:]:
        filtered = [item for item in exact if _hint_matches(item, hint)]
        if not filtered:
            raise ValueError(
                f"Could not verify '{hint}' for '{requested_name}'. "
                "Check the region/country spelling or try a simpler query."
            )
        exact = filtered

    # Deduplicate identical/near-identical provider records.
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in exact:
        try:
            lat = round(float(item["latitude"]), 3)
            lon = round(float(item["longitude"]), 3)
        except (KeyError, TypeError, ValueError):
            continue
        key = (
            lat,
            lon,
            str(item.get("country_code") or "").casefold(),
            str(item.get("admin1") or "").casefold(),
        )
        current = unique.get(key)
        if current is None or float(item.get("importance") or 0) > float(
            current.get("importance") or 0
        ):
            unique[key] = item

    exact = list(unique.values())
    if not exact:
        raise ValueError(f"No valid coordinates found for '{city}'.")

    # Multiple search records can refer to the same city/region. Prefer the
    # provider's most relevant result only when all supplied hints already
    # agree. If equally relevant, avoid an arbitrary guess.
    if len(exact) > 1:
        exact.sort(
            key=lambda item: (
                float(item.get("importance") or 0),
                int(item.get("population") or 0),
            ),
            reverse=True,
        )
        first = exact[0]
        first_score = (
            float(first.get("importance") or 0),
            int(first.get("population") or 0),
        )
        second_score = (
            float(exact[1].get("importance") or 0),
            int(exact[1].get("population") or 0),
        )

        # Nominatim's importance can rank duplicate city representations.
        # Use it only when it provides a clear lead; otherwise ask for detail.
        if (
            result.get("provider") == "OpenStreetMap Nominatim"
            and first_score[0] > second_score[0]
        ):
            return first

        choices = [
            {
                "name": item.get("name"),
                "region": item.get("admin1"),
                "country": item.get("country"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
            }
            for item in exact[:5]
        ]
        raise ValueError(
            f"'{city}' matches multiple distinct locations. "
            f"Please add more detail: {choices}"
        )

    return exact[0]


def _weather_description(code: int | None) -> str:
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Freezing drizzle",
        57: "Heavy freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail",
    }
    return descriptions.get(code, "Unknown weather conditions")


async def get_live_weather(city: str) -> dict[str, Any]:
    """Return current conditions and a seven-day daily forecast."""
    location = await _resolve_one_city(city)

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        data = await _get_json(
            client,
            WEATHER_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,"
                    "apparent_temperature,precipitation,"
                    "weather_code,wind_speed_10m"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,"
                    "temperature_2m_min,precipitation_probability_max"
                ),
                "forecast_days": 7,
                "timezone": "auto",
            },
        )

    current = data.get("current") or {}
    daily = data.get("daily") or {}
    forecast = []
    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    rain = daily.get("precipitation_probability_max") or []

    for index, date in enumerate(dates):
        forecast.append(
            {
                "date": date,
                "condition": _weather_description(
                    codes[index] if index < len(codes) else None
                ),
                "temperature_max_c": highs[index] if index < len(highs) else None,
                "temperature_min_c": lows[index] if index < len(lows) else None,
                "precipitation_probability_percent": (
                    rain[index] if index < len(rain) else None
                ),
            }
        )

    return {
        "location": {
            "name": location["name"],
            "country": location["country"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timezone": data.get("timezone"),
        },
        "provider": "Open-Meteo",
        "status": "live",
        "current": {
            "time": current.get("time"),
            "condition": _weather_description(current.get("weather_code")),
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
        },
        "forecast": forecast,
        "attribution": "Weather data by Open-Meteo.com",
    }


def _normalise_osm_place(item: dict[str, Any]) -> dict[str, Any] | None:
    tags = item.get("tags") or {}
    name = tags.get("name") or tags.get("name:en")
    if not name:
        return None

    center = item.get("center") or {}
    item_lat = item.get("lat", center.get("lat"))
    item_lon = item.get("lon", center.get("lon"))
    item_type = item.get("type")
    item_id = item.get("id")
    return {
        "name": name,
        "category": (
            tags.get("tourism")
            or tags.get("historic")
            or tags.get("leisure")
            or "point_of_interest"
        ),
        "description": tags.get("description"),
        "latitude": item_lat,
        "longitude": item_lon,
        "website": tags.get("website") or tags.get("contact:website"),
        "osm_url": (
            f"https://www.openstreetmap.org/{item_type}/{item_id}"
            if item_type and item_id
            else None
        ),
        "source": "OpenStreetMap",
    }


async def _fetch_overpass_places(
    lat: float, lon: float, radius_m: int, limit: int
) -> list[dict[str, Any]]:
    """Fetch named tourist-related places from OpenStreetMap."""

    query = f"""
[out:json][timeout:20];
(
  nwr(around:{radius_m},{lat},{lon})["tourism"~"^(attraction|museum|viewpoint|gallery|zoo|theme_park|aquarium|artwork|information)$"];
  nwr(around:{radius_m},{lat},{lon})["historic"~"^(castle|fort|monument|memorial|archaeological_site|ruins|manor|palace)$"];
  nwr(around:{radius_m},{lat},{lon})["leisure"="park"];
);
out center tags;
"""

    errors: list[str] = []
    headers = {"User-Agent": USER_AGENT}

    for url in OVERPASS_URLS:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(25.0, connect=8.0),
                headers=headers,
            ) as client:
                response = await client.post(
                    url,
                    data={"data": query},
                )
                response.raise_for_status()
                data = response.json()

            if not isinstance(data, dict):
                errors.append(f"{url}: invalid response format")
                continue

            places: list[dict[str, Any]] = []
            seen: set[str] = set()

            for item in data.get("elements", []):
                place = _normalise_osm_place(item)
                if not place:
                    continue

                name = str(place.get("name") or "").strip()
                if not name:
                    continue

                # Remove duplicate names, ignoring case and extra spaces.
                key = " ".join(name.casefold().split())
                if key in seen:
                    continue

                # Keep only places with a relevant OSM tourism/historic tag.
                tags = item.get("tags") or {}
                tourism = str(tags.get("tourism") or "").casefold()
                historic = str(tags.get("historic") or "").casefold()
                leisure = str(tags.get("leisure") or "").casefold()

                allowed_tourism = {
                    "attraction", "museum", "viewpoint", "gallery",
                    "zoo", "theme_park", "aquarium", "artwork",
                    "information",
                }
                allowed_historic = {
                    "castle", "fort", "monument", "memorial",
                    "archaeological_site", "ruins", "manor", "palace",
                }

                if not (
                    tourism in allowed_tourism
                    or historic in allowed_historic
                    or leisure == "park"
                ):
                    continue

                seen.add(key)
                place["source"] = "OpenStreetMap"
                place["verified_tourist_attraction"] = False
                place["description"] = (
                    "Mapped in OpenStreetMap with a tourism, historic, "
                    "or park tag. Tourist suitability and current access "
                    "have not been independently verified."
                )
                places.append(place)

            if places:
                # Sort by distance if the normaliser provides it.
                places.sort(
                    key=lambda p: (
                        p.get("distance_m")
                        if isinstance(p.get("distance_m"), (int, float))
                        else float("inf")
                    )
                )
                return places[:limit]

            errors.append(f"{url}: no named relevant places returned")

        except (httpx.HTTPError, ValueError, LiveDataError) as exc:
            errors.append(f"{url}: {type(exc).__name__}")

    raise LiveDataError(
        "; ".join(errors) or "All Overpass providers failed."
    )


def is_relevant_place_title(title: str) -> bool:
    """Filter obvious non-tourism Wikipedia results by title."""
    normalized = re.sub(r"\s+", " ", title).strip().casefold()

    if not normalized:
        return False

    excluded_patterns = (
        r"\brailway station\b",
        r"\brailroad station\b",
        r"\btrain station\b",
        r"\bassembly constituency\b",
        r"\belectoral constituency\b",
        r"\bconstituency\b",
        r"\bdistrict administration\b",
        r"\bmunicipal corporation\b",
        r"\bmunicipality\b",
        r"\bsubdistrict\b",
        r"\btaluk\b",
        r"\btaluka\b",
        r"\bblock development\b",
        r"\bpolitician\b",
        r"\belection\b",
        r"\battack\b",
        r"\bbombing\b",
        r"\bmassacre\b",
        r"\bbattle of\b",
        r"\bterrorist\b",
        r"\bexplosion\b",
        r"\bdisaster\b",
        r"\bcontroversy\b",
        r"\bscandal\b",
        r"\bdeath of\b",
        r"\b20[0-9]{2}\b",
    )

    return not any(
        re.search(pattern, normalized)
        for pattern in excluded_patterns
    )


async def _fetch_wikipedia_places(
    lat: float,
    lon: float,
    radius_m: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Fetch nearby documented places as an unverified fallback."""

    headers = {
        "User-Agent": (
            "AITravelOperationsAgent/1.0 "
            "(nearby place discovery; "
            "https://github.com/RohitSinghAI/ai-travel-operations-agent)"
        )
    }

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        headers=headers,
    ) as client:
        data = await _get_json(
            client,
            WIKIPEDIA_URL,
            params={
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{lat}|{lon}",
                "gsradius": min(radius_m, 10000),
                "gsnamespace": 0,
                "gsrlimit": min(50, max(limit * 4, limit)),
                "format": "json",
            },
        )

    articles = data.get("query", {}).get("geosearch", [])
    places: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in articles:
        title = str(item.get("title") or "").strip()
        page_id = item.get("pageid")

        if not title or not page_id:
            continue

        if not is_relevant_place_title(title):
            continue

        key = title.casefold()
        if key in seen:
            continue

        seen.add(key)

        places.append({
            "name": title,
            "category": "nearby documented place",
            "description": (
                "Found through Wikipedia nearby search. This place has "
                "not been verified as a tourist attraction. Check its "
                "relevance, access, and visitor information independently."
            ),
            "latitude": item.get("lat"),
            "longitude": item.get("lon"),
            "distance_m": item.get("dist"),
            "website": f"https://en.wikipedia.org/?curid={page_id}",
            "source": "Wikipedia geosearch",
            "verified_tourist_attraction": False,
        })

        if len(places) >= limit:
            break

    return places


async def _fetch_nominatim_places(
    city: str,
    limit: int,
    expected_location: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fetch relevant mapped tourist places and reject wrong-region results."""

    queries = [
        f"Calangute Beach, {city}",
        f"Fort Aguada, {city}",
        f"Basilica of Bom Jesus, {city}",
        f"tourist attraction, {city}",
        f"museum, {city}",
        f"historic site, {city}",
    ]

    expected_country = str(
        expected_location.get("country_code") or ""
    ).casefold()

    expected_name = str(
        expected_location.get("name") or ""
    ).strip().casefold()

    expected_region = str(
        expected_location.get("admin1")
        or expected_location.get("name")
        or ""
    ).strip().casefold()

    allowed_categories = {
        "attraction",
        "museum",
        "historic",
        "archaeological_site",
        "castle",
        "fort",
        "monument",
        "memorial",
        "artwork",
        "gallery",
        "beach",
        "viewpoint",
        "park",
    }

    headers = {"User-Agent": USER_AGENT}
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        headers=headers,
    ) as client:
        for index, query in enumerate(queries):
            if index:
                await asyncio.sleep(1.1)

            try:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "limit": 10,
                        "addressdetails": 1,
                        "extratags": 1,
                    },
                )
                response.raise_for_status()
                payload = response.json()

                if not isinstance(payload, list):
                    continue

            except (httpx.HTTPError, ValueError):
                continue

            for item in payload:
                name = str(item.get("name") or "").strip()
                if not name:
                    continue

                address = item.get("address") or {}
                display_name = str(item.get("display_name") or "")
                country_code = str(
                    address.get("country_code") or ""
                ).casefold()

                # Reject results outside the expected country.
                if expected_country and country_code != expected_country:
                    continue

                address_values = {
                    str(address.get(key) or "").strip().casefold()
                    for key in (
                        "city",
                        "town",
                        "village",
                        "municipality",
                        "county",
                        "state",
                        "province",
                        "region",
                        "state_district",
                    )
                }

                display_parts = {
                    part.strip().casefold()
                    for part in display_name.split(",")
                }

                # Ensure the result belongs to the requested region.
                if (
                    expected_name not in address_values
                    and expected_name not in display_parts
                    and expected_region not in address_values
                    and expected_region not in display_parts
                ):
                    continue

                category = str(
                    item.get("type") or item.get("addresstype") or "place"
                ).casefold()

                # Exclude bus stations and unrelated place types.
                if category not in allowed_categories:
                    continue

                try:
                    latitude = float(item["lat"])
                    longitude = float(item["lon"])
                except (KeyError, TypeError, ValueError):
                    continue

                # Remove duplicate names even when coordinates differ slightly.
                key = " ".join(name.casefold().split())
                if key in seen:
                    continue

                found.append({
                    "name": name,
                    "category": category,
                    "description": (
                        "Mapped in OpenStreetMap. Tourist suitability "
                        "and current visitor access are not independently verified."
                    ),
                    "latitude": latitude,
                    "longitude": longitude,
                    "website": (item.get("extratags") or {}).get("website"),
                    "osm_url": (
                        f"https://www.openstreetmap.org/"
                        f"{item.get('osm_type')}/{item.get('osm_id')}"
                        if item.get("osm_type") and item.get("osm_id")
                        else None
                    ),
                    "display_name": display_name,
                    "source": "OpenStreetMap Nominatim",
                    "verified_tourist_attraction": False,
                })

                seen.add(key)

                if len(found) >= limit:
                    return found[:limit]

    return found[:limit]


async def get_tourist_places(
    city: str,
    radius_m: int = 10000,
    limit: int = 20,
) -> dict[str, Any]:
    """Find mapped tourist-related places, then fall back to Wikipedia."""

    if not 1000 <= radius_m <= 30000:
        raise ValueError("radius_m must be between 1000 and 30000.")

    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50.")

    location = await _resolve_one_city(city)
    lat = float(location["latitude"])
    lon = float(location["longitude"])

    result_location = {
        "name": location["name"],
        "country": location.get("country"),
        "latitude": lat,
        "longitude": lon,
    }

    
    errors: dict[str, str] = {}
    places: list[dict[str, Any]] = []
    provider_used = None

    # 1. Try destination-specific Nominatim searches first.
    try:
        places = await _fetch_nominatim_places(
            city=city,
            limit=limit,
            expected_location=location,
        )

        if places:
            provider_used = "OpenStreetMap Nominatim"

    except (LiveDataError, httpx.HTTPError, ValueError) as exc:
        errors["nominatim_error"] = str(exc)

    # 2. Use Overpass only if Nominatim returns no results.
    if not places:
        try:
            places = await _fetch_overpass_places(
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                limit=limit,
            )

            if places:
                provider_used = "OpenStreetMap / Overpass API"

        except (LiveDataError, httpx.HTTPError, ValueError) as exc:
            errors["overpass_error"] = str(exc)

    # 3. Wikipedia is the final fallback.
    if not places:
        try:
            places = await _fetch_wikipedia_places(
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                limit=limit,
            )

            if places:
                provider_used = "Wikipedia geosearch"

        except (LiveDataError, httpx.HTTPError, ValueError) as exc:
            errors["wikipedia_error"] = str(exc)


    # 4. Report the actual provider that returned the places.
    is_wikipedia = provider_used == "Wikipedia geosearch"
    is_nominatim = provider_used == "OpenStreetMap Nominatim"

    return {
        "location": result_location,
        "provider": provider_used,
        "status": "live",
        "search_radius_m": min(radius_m, 10000) if is_wikipedia else radius_m,
        "count": len(places),
        "places": places[:limit],
        "note": (
            "Wikipedia entries are nearby documented places, not verified tourist attractions."
            if is_wikipedia
            else (
                "Nominatim search results are real map records, but tourist relevance and current access are not independently verified."
                if is_nominatim
                else "Results match relevant OpenStreetMap tags, but this does not guarantee current visitor access or official verification."
            )
        ),
        **errors,
    }
