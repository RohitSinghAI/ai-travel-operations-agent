
import httpx

url = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

query = """
[out:json][timeout:15];
node["tourism"="attraction"](around:5000,28.65195,77.23149);
out 10;
"""

try:
    response = httpx.post(
        url,
        data={"data": query},
        headers={"User-Agent": "AITravelOperationsAgent/1.0"},
        timeout=25,
    )

    print("HTTP:", response.status_code)
    print(response.text[:1200])

except httpx.TimeoutException:
    print("ERROR: Request timed out")

except httpx.HTTPError as error:
    print("HTTP ERROR:", error)
