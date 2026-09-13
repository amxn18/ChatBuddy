import os

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP


load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


mcp = FastMCP(name="Weather Server")


@mcp.tool()
def get_weather_details(city: str) -> dict:
    """
    Get the current weather details for a city.

    Args:
        city: Name of the city, for example Delhi, Mumbai, or London.
    """

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}"
        "&units=metric"
        f"&appid={WEATHER_API_KEY}"
    )

    try:

        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return {"error": "City not found"}
        data = response.json()

        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "weather": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
        }

    except Exception as e:

        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()